import json
import math
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

from .production_payload import build_production_payload

from .command_client import CommandClient
from .config import EdgeConfig
from .control_protocol import normalize_command, protocol_time
from .shared_memory_store import create_or_attach, read_snapshot, write_snapshot
from .uploader import SnapshotUploader


class ManualInputState:
    def __init__(self, config: EdgeConfig) -> None:
        self.config = config
        self.sequence = 0
        self.last_snapshot: Optional[dict[str, Any]] = None
        self.last_write_error: Optional[str] = None
        self.received_commands: list[dict[str, Any]] = []
        self.command_results: list[dict[str, Any]] = []
        self.stream_active = False
        self.upload_enabled = False
        self.stream_thread: Optional[threading.Thread] = None
        self.stream_device_id = "SIM-MANUAL-001"
        self.stream_device_name = "Manual Input Chamber"
        self.stream_temperature = 25.0
        self.stream_humidity = 60.0
        self.stream_started_at = 0.0
        self.lock = threading.Lock()
        self.shm = create_or_attach(config.shared_memory_name, config.shared_memory_size)

    def write_values(self, temperature: float, humidity: float, device_id: str, device_name: str) -> dict[str, Any]:
        return self.start_stream(temperature, humidity, device_id, device_name)

    def start_stream(self, temperature: float, humidity: float, device_id: str, device_name: str) -> dict[str, Any]:
        with self.lock:
            return self._start_stream_unlocked(temperature, humidity, device_id, device_name)

    def _start_stream_unlocked(
        self,
        temperature: float,
        humidity: float,
        device_id: str,
        device_name: str,
    ) -> dict[str, Any]:
        self.stream_device_id = device_id
        self.stream_device_name = device_name
        self.stream_temperature = temperature
        self.stream_humidity = humidity
        self.stream_started_at = time.time()
        self.stream_active = True
        self.upload_enabled = True
        snapshot = self._write_stream_snapshot_unlocked(0.0)
        if not self.stream_thread or not self.stream_thread.is_alive():
            self.stream_thread = threading.Thread(target=self._stream_loop, daemon=True)
            self.stream_thread.start()
        return snapshot

    def _stream_loop(self) -> None:
        while True:
            with self.lock:
                if not self.stream_active:
                    return
                elapsed = max(0.0, time.time() - self.stream_started_at)
                self._write_stream_snapshot_unlocked(elapsed)
            time.sleep(self.config.stream_interval_seconds)

    def _write_stream_snapshot_unlocked(self, elapsed: float) -> dict[str, Any]:
        temperature = self.stream_temperature + math.sin(elapsed / 5.0) * 0.35
        humidity = self.stream_humidity + math.cos(elapsed / 7.0) * 0.8
        snapshot = build_production_payload(
            device_id=self.stream_device_id,
            device_ip=self.config.device_ip,
            current_temperature=temperature,
            current_humidity=humidity,
            target_temperature=self.stream_temperature,
            target_humidity=self.stream_humidity,
            step=1,
            running=1,
            elapsed_seconds=elapsed,
            sequence=self.sequence,
        )
        write_snapshot(self.shm, snapshot, self.config.shared_memory_size)
        self.sequence += 1
        self.last_snapshot = snapshot
        self.last_write_error = None
        return snapshot

    def _record_command_result(self, command: dict[str, Any], result: dict[str, Any], now: float) -> dict[str, Any]:
        result.setdefault("successMessage", command.get("command", ""))
        result.setdefault("time", protocol_time())
        self.command_results.insert(0, {**result, "reported_at": now})
        self.command_results = self.command_results[:20]
        return result

    def handle_command(self, command: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            now = time.time()
            self.received_commands.insert(0, {**command, "received_at": now})
            self.received_commands = self.received_commands[:20]

            wire_command, protocol_command_type = normalize_command(command.get("command"))
            command_type = command.get("command_type") or protocol_command_type
            device_id = command.get("device_id") or self.stream_device_id
            if command_type == "START_TEST":
                snapshot = self._read_snapshot_unlocked()
                device = self._find_device(snapshot, device_id)
                if not device:
                    result = {
                        "status": "FAILED",
                        "message": f"device not found in local snapshot: {device_id}",
                        "payload": {},
                    }
                else:
                    payload = command.get("payload", {})
                    target_temperature = float(payload.get("target_temperature", device.get("target_temperature", device.get("mainData", {}).get("TEMP_SP", 25))))
                    target_humidity = float(payload.get("target_humidity", device.get("target_humidity", device.get("mainData", {}).get("HUMI_SP", 60))))
                    self._start_stream_unlocked(
                        target_temperature,
                        target_humidity,
                        device_id,
                        str(device.get("name") or self.stream_device_name),
                    )
                    result = {
                        "status": "EXECUTED",
                        "message": "START_TEST received and realtime stream resumed",
                        "payload": {"run_state": "RUNNING"},
                    }
                return self._record_command_result({**command, "command": wire_command}, result, now)

            if command_type in {"KEEP_TEST", "BUZZER_ON", "BUZZER_OFF", "RESET_ALARM", "SET_RUN_MODE", "DOWNLOAD_PROGRAM", "FIXED_VALUE", "OPERATION_SETTING", "BASIC_INFO", "CORRECTION", "PID_SET", "FACTORY_PARAMS"}:
                result = {
                    "status": "EXECUTED",
                    "message": f"{wire_command} received",
                    "payload": {},
                }
                return self._record_command_result({**command, "command": wire_command}, result, now)

            if command_type not in {"STOP_TEST", "HOLD_TEST", "SKIP_STEP"}:
                result = {
                    "status": "REJECTED",
                    "message": f"unsupported command type: {command.get('command_type')}",
                    "payload": {},
                }
                return self._record_command_result({**command, "command": wire_command}, result, now)

            snapshot = self._read_snapshot_unlocked()
            matched = False
            device = self._find_device(snapshot, device_id)
            if device:
                program = device.setdefault("program", {})
                status = device.setdefault("status", {})
                if command_type == "STOP_TEST":
                    program["run"] = 0
                    program["step"] = 0
                    status["state"] = "\u505c\u6b62"
                elif command_type == "HOLD_TEST":
                    program["run"] = 0
                    status["state"] = "\u4fdd\u6301"
                elif command_type == "SKIP_STEP":
                    program["run"] = 1
                    program["step"] = int(program.get("step") or 0) + 1
                    status["state"] = "\u8fd0\u884c\u4e2d"
                status["alarm"] = []
                matched = True

            if not matched:
                result = {
                    "status": "FAILED",
                    "message": f"device not found in local snapshot: {device_id}",
                    "payload": {},
                }
            else:
                snapshot["source"] = "manual_input_ui_command_result"
                snapshot["sequence"] = int(snapshot.get("sequence") or 0) + 1
                snapshot["written_at"] = now
                write_snapshot(self.shm, snapshot, self.config.shared_memory_size)
                self.last_snapshot = snapshot
                if command_type == "STOP_TEST":
                    self.stream_active = False
                    # Stop ends the test stream, but the edge must keep uploading
                    # the stopped snapshot so the server can distinguish STOPPED
                    # from a lost connection.
                self.upload_enabled = True
                result_payload = {
                    "run_state": "STOPPED" if command_type == "STOP_TEST" else "HOLDING" if command_type == "HOLD_TEST" else "RUNNING",
                }
                result = {
                    "status": "EXECUTED",
                    "message": f"{command_type} received and local snapshot updated",
                    "payload": result_payload,
                }

            return self._record_command_result({**command, "command": wire_command}, result, now)

    def should_upload(self) -> bool:
        with self.lock:
            return self.upload_enabled

    def on_uploaded(self, snapshot: dict[str, Any]) -> None:
        # Uploading is also the device heartbeat.  A STOP_TEST command changes
        # the test state only; it must not disable heartbeat uploads.
        return

    def get_status(self) -> dict[str, Any]:
        with self.lock:
            memory_snapshot = None
            memory_error = None
            try:
                memory_snapshot = self._read_snapshot_unlocked()
            except Exception as exc:
                memory_error = str(exc)
            return {
                "edge_id": self.config.edge_id,
                "server_url": self.config.server_url,
                "shared_memory_name": self.config.shared_memory_name,
                "last_snapshot": self.last_snapshot,
                "last_write_error": self.last_write_error,
                "received_commands": self.received_commands,
                "command_results": self.command_results,
                "stream_active": self.stream_active,
                "upload_enabled": self.upload_enabled,
                "memory_snapshot": memory_snapshot,
                "memory_error": memory_error,
            }

    def _read_snapshot_unlocked(self) -> dict[str, Any]:
        return read_snapshot(self.shm)

    @staticmethod
    def _find_device(snapshot: dict[str, Any], device_id: Any) -> Optional[dict[str, Any]]:
        if snapshot.get("device_id") == device_id:
            return snapshot
        return next((item for item in snapshot.get("devices", []) if item.get("device_id") == device_id), None)


def run_manual_input_server(config: EdgeConfig, host: str = "127.0.0.1", port: int = 8765) -> None:
    state = ManualInputState(config)
    uploader = SnapshotUploader(config, should_upload=state.should_upload, on_uploaded=state.on_uploaded)
    uploader_thread = threading.Thread(target=uploader.run_forever, daemon=True)
    uploader_thread.start()
    command_thread = threading.Thread(target=CommandClient(config, state.handle_command).run_forever, daemon=True)
    command_thread.start()

    handler = _build_handler(state)
    server = ThreadingHTTPServer((host, port), handler)
    print(f"manual input UI started: http://{host}:{port}")
    print(f"upload endpoint: {config.ingest_endpoint}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("manual input UI stopped")
    finally:
        server.server_close()
        state.shm.close()


def _build_handler(state: ManualInputState):
    class ManualInputHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self._send_html()
                return
            if parsed.path == "/api/status":
                self._send_json(200, state.get_status())
                return
            self._send_json(404, {"error": "not found"})

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path != "/api/write":
                self._send_json(404, {"error": "not found"})
                return
            try:
                payload = self._read_json_or_form()
                temperature, humidity = _parse_temperature_humidity(payload)
                device_id = str(payload.get("device_id") or "SIM-MANUAL-001")
                device_name = str(payload.get("device_name") or "Manual Input Chamber")
                snapshot = state.write_values(temperature, humidity, device_id, device_name)
                self._send_json(200, {"status": "written", "snapshot": snapshot})
            except Exception as exc:
                self._send_json(400, {"error": str(exc)})

        def log_message(self, format: str, *args: Any) -> None:
            print(f"{self.address_string()} - {format % args}")

        def _read_json_or_form(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8") if length else ""
            content_type = self.headers.get("Content-Type", "")
            if "application/json" in content_type:
                return json.loads(body or "{}")
            form = parse_qs(body)
            return {key: values[-1] for key, values in form.items()}

        def _send_json(self, status: int, payload: dict[str, Any]) -> None:
            data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _send_html(self) -> None:
            data = _HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return ManualInputHandler


def _parse_temperature_humidity(payload: dict[str, Any]) -> tuple[float, float]:
    raw = str(payload.get("raw") or "").strip()
    if raw and ("temperature" not in payload and "humidity" not in payload):
        payload = {**payload, **_parse_raw_input(raw)}

    if "temperature" not in payload or "humidity" not in payload:
        raise ValueError("temperature and humidity are required")

    temperature = float(payload["temperature"])
    humidity = float(payload["humidity"])
    if not -100 <= temperature <= 200:
        raise ValueError("temperature must be between -100 and 200")
    if not 0 <= humidity <= 100:
        raise ValueError("humidity must be between 0 and 100")
    return temperature, humidity


def _parse_raw_input(raw: str) -> dict[str, float]:
    if raw.startswith("{"):
        parsed = json.loads(raw)
        return {
            "temperature": float(parsed["temperature"]),
            "humidity": float(parsed["humidity"]),
        }

    normalized = raw.replace("，", ",").replace("；", ";").replace(";", ",")
    parts = [part.strip() for part in normalized.split(",") if part.strip()]
    values: dict[str, float] = {}
    if len(parts) == 2 and all("=" not in part for part in parts):
        values["temperature"] = float(parts[0])
        values["humidity"] = float(parts[1])
        return values

    key_map = {
        "temperature": "temperature",
        "temp": "temperature",
        "t": "temperature",
        "温度": "temperature",
        "humidity": "humidity",
        "hum": "humidity",
        "h": "humidity",
        "湿度": "humidity",
    }
    for part in parts:
        if "=" not in part:
            continue
        key, value = [item.strip() for item in part.split("=", 1)]
        mapped_key = key_map.get(key.lower()) or key_map.get(key)
        if mapped_key:
            values[mapped_key] = float(value)
    return values


_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>工控机手动数据输入</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f4f6f8;
      --panel: #ffffff;
      --text: #172033;
      --muted: #637083;
      --line: #d9e0ea;
      --primary: #2563eb;
      --ok: #047857;
      --bad: #b42318;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Microsoft YaHei", Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    header {
      padding: 22px 28px;
      background: #111827;
      color: white;
    }
    header h1 {
      margin: 0;
      font-size: 22px;
      font-weight: 700;
    }
    header p {
      margin: 6px 0 0;
      color: #cbd5e1;
      font-size: 13px;
    }
    .stream-banner {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      margin-top: 16px;
      padding: 14px 16px;
      border: 1px solid rgba(255,255,255,.16);
      border-left: 5px solid #94a3b8;
      border-radius: 8px;
      background: rgba(15,23,42,.72);
    }
    .stream-banner strong { display: block; font-size: 16px; }
    .stream-banner span { display: block; margin-top: 4px; color: #cbd5e1; font-size: 12px; }
    .stream-banner.running { border-left-color: #22c55e; background: rgba(20,83,45,.42); }
    .stream-banner.stopped { border-left-color: #ef4444; background: rgba(127,29,29,.42); }
    .stream-banner.waiting { border-left-color: #f59e0b; background: rgba(120,53,15,.38); }
    .stream-badge { flex: 0 0 auto; padding: 6px 10px; border-radius: 999px; color: white; background: #64748b; font-size: 12px; font-weight: 700; }
    .running .stream-badge { background: #16a34a; }
    .stopped .stream-badge { background: #dc2626; }
    .waiting .stream-badge { background: #d97706; }
    main {
      max-width: 1100px;
      margin: 0 auto;
      padding: 24px;
      display: grid;
      grid-template-columns: 380px 1fr;
      gap: 18px;
    }
    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
      min-width: 0;
    }
    h2 {
      margin: 0 0 14px;
      font-size: 16px;
    }
    label {
      display: block;
      margin: 12px 0 6px;
      font-size: 13px;
      color: var(--muted);
    }
    input, textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px 12px;
      font-size: 15px;
      color: var(--text);
      background: white;
    }
    textarea {
      min-height: 86px;
      resize: vertical;
      font-family: Consolas, monospace;
    }
    button {
      width: 100%;
      margin-top: 16px;
      border: 0;
      border-radius: 6px;
      padding: 11px 14px;
      background: var(--primary);
      color: white;
      font-size: 15px;
      font-weight: 700;
      cursor: pointer;
    }
    button:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
    .hint {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.7;
      margin-top: 10px;
    }
    .status {
      min-height: 28px;
      margin-top: 12px;
      font-size: 13px;
      color: var(--muted);
    }
    .status.ok { color: var(--ok); }
    .status.bad { color: var(--bad); }
    pre {
      margin: 0;
      min-height: 460px;
      max-height: 640px;
      overflow: auto;
      background: #0b1020;
      color: #dbeafe;
      border-radius: 8px;
      padding: 14px;
      font-size: 12px;
      line-height: 1.6;
    }
    .command-log {
      min-height: 140px;
      max-height: 240px;
      margin-top: 12px;
    }
    .meta {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 10px;
      margin-bottom: 14px;
    }
    .meta div {
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      background: #f8fafc;
    }
    .meta span {
      display: block;
      color: var(--muted);
      font-size: 12px;
    }
    .meta strong {
      display: block;
      margin-top: 4px;
      font-size: 13px;
      word-break: break-all;
    }
    @media (max-width: 860px) {
      main { grid-template-columns: 1fr; padding: 14px; }
    }
  </style>
</head>
<body>
  <header>
    <h1>工控机手动数据输入</h1>
    <p>输入温度、湿度，写入本机共享内存，并由后台上传线程发送到总服务端。</p>
  </header>
  <div id="streamBanner" class="stream-banner waiting">
    <div>
      <strong id="streamTitle">等待启动实时数据流</strong>
      <span id="streamDetail">尚未开始发送数据</span>
    </div>
    <span id="streamBadge" class="stream-badge">未启动</span>
  </div>
  <main>
    <section>
      <h2>写入数据</h2>
      <label for="deviceId">设备编号</label>
      <input id="deviceId" value="SIM-MANUAL-001" />
      <label for="deviceName">设备名称</label>
      <input id="deviceName" value="Manual Input Chamber" />
      <label for="temperature">温度</label>
      <input id="temperature" type="number" step="0.1" value="25.0" />
      <label for="humidity">湿度</label>
      <input id="humidity" type="number" step="0.1" value="60.0" />
      <label for="raw">串数据输入</label>
      <textarea id="raw" placeholder="支持：25,60 或 温度=25,湿度=60 或 JSON"></textarea>
      <div class="hint">如果填写了串数据，会优先按串数据解析；空着则使用上面的温度、湿度输入框。</div>
      <button id="writeBtn" type="button">启动实时数据流</button>
      <div id="message" class="status"></div>
    </section>
    <section>
      <h2>当前状态</h2>
      <div class="meta">
        <div><span>共享内存</span><strong id="memoryName">-</strong></div>
        <div><span>工控机编号</span><strong id="edgeId">-</strong></div>
        <div><span>总服务端</span><strong id="serverUrl">-</strong></div>
      </div>
      <pre id="snapshot">{}</pre>
      <h2 style="margin-top:16px;">收到的总控命令</h2>
      <pre id="commands" class="command-log">[]</pre>
    </section>
  </main>
  <script>
    const message = document.querySelector("#message");
    const snapshot = document.querySelector("#snapshot");
    const commands = document.querySelector("#commands");
    const writeBtn = document.querySelector("#writeBtn");
    const streamBanner = document.querySelector("#streamBanner");
    const streamTitle = document.querySelector("#streamTitle");
    const streamDetail = document.querySelector("#streamDetail");
    const streamBadge = document.querySelector("#streamBadge");

    function setMessage(text, tone) {
      message.textContent = text;
      message.className = "status " + (tone || "");
    }

    async function refreshStatus() {
      const response = await fetch("/api/status");
      const data = await response.json();
      document.querySelector("#memoryName").textContent = data.shared_memory_name || "-";
      document.querySelector("#edgeId").textContent = data.edge_id || "-";
      document.querySelector("#serverUrl").textContent = data.server_url || "-";
      snapshot.textContent = JSON.stringify(data.memory_snapshot || data.last_snapshot || data, null, 2);
      commands.textContent = JSON.stringify({
        received_commands: data.received_commands || [],
        command_results: data.command_results || []
      }, null, 2);
      updateStreamBanner(data);
    }

    function updateStreamBanner(data) {
      const latestCommand = (data.received_commands || [])[0];
      const latestResult = (data.command_results || [])[0];
      const snapshot = data.memory_snapshot || data.last_snapshot || {};
      const isRunning = Boolean(data.stream_active);
      const isStopped = !isRunning && Boolean(
        latestCommand?.command_type === "STOP_TEST" ||
        snapshot?.status?.state === "停止" ||
        snapshot?.run_state === "STOPPED"
      );
      if (isRunning) {
        streamBanner.className = "stream-banner running";
        streamTitle.textContent = "实时数据流运行中";
        streamDetail.textContent = `正在持续发送数据，最近序号 ${data.memory_snapshot?.sequence ?? "--"}`;
        streamBadge.textContent = "发送中";
        return;
      }
      if (isStopped) {
        streamBanner.className = "stream-banner stopped";
        streamTitle.textContent = "数据发送已停止";
        streamDetail.textContent = latestResult?.message || "已完成最后一帧 STOPPED 状态回传";
        streamBadge.textContent = "已停止";
        return;
      }
      streamBanner.className = "stream-banner waiting";
      streamTitle.textContent = "等待启动实时数据流";
      streamDetail.textContent = latestCommand ? `最近命令：${latestCommand.command_type}` : "尚未开始发送数据";
      streamBadge.textContent = "未启动";
    }

    async function writeValues() {
      writeBtn.disabled = true;
      setMessage("正在写入共享内存...", "");
      const raw = document.querySelector("#raw").value.trim();
      const payload = {
        device_id: document.querySelector("#deviceId").value.trim(),
        device_name: document.querySelector("#deviceName").value.trim()
      };
      if (raw) {
        payload.raw = raw;
      } else {
        payload.temperature = document.querySelector("#temperature").value;
        payload.humidity = document.querySelector("#humidity").value;
      }
      try {
        const response = await fetch("/api/write", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "写入失败");
        setMessage("实时数据流已启动，温湿度会持续变化并上传。", "ok");
        snapshot.textContent = JSON.stringify(data.snapshot, null, 2);
      } catch (error) {
        setMessage(error.message, "bad");
      } finally {
        writeBtn.disabled = false;
        refreshStatus().catch(() => {});
      }
    }

    writeBtn.addEventListener("click", writeValues);
    refreshStatus().catch(error => setMessage(error.message, "bad"));
    setInterval(() => refreshStatus().catch(() => {}), 2000);
  </script>
</body>
</html>"""
