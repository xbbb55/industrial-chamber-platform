import json
import math
import threading
import time
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

from .production_payload import CHINA_STANDARD_TIME, build_production_payload

from .config import EdgeConfig
from .control_protocol import normalize_command, protocol_time
from .shared_memory_store import create_or_attach, read_snapshot, write_snapshot
from .websocket_client import WebSocketEdgeClient

SIM_TEMPERATURE_MIN = -200.0
SIM_TEMPERATURE_MAX = 500.0
SIM_HUMIDITY_MIN = 0.0
SIM_HUMIDITY_MAX = 100.0


class ManualInputState:
    def __init__(self, config: EdgeConfig) -> None:
        self.config = config
        self.sequence = 0
        self.last_snapshot: Optional[dict[str, Any]] = None
        self.last_write_error: Optional[str] = None
        self.received_commands: list[dict[str, Any]] = []
        self.command_results: list[dict[str, Any]] = []
        self.upload_events: list[dict[str, Any]] = []
        self.command_status_events: list[dict[str, Any]] = []
        self.command_status_sequence = 0
        self.stream_active = False
        self.upload_enabled = False
        self.stream_thread: Optional[threading.Thread] = None
        self.stream_device_id = "SIM-MANUAL-001"
        self.stream_device_name = "Manual Input Chamber"
        self.stream_temperature = 25.0
        self.stream_humidity = 60.0
        self.stream_started_at = 0.0
        self.stream_start_time = ""
        self.lock = threading.Lock()
        self.shm = create_or_attach(config.shared_memory_name, config.shared_memory_size)
        self.command_status_shm = create_or_attach(
            config.command_status_memory_name,
            config.command_status_memory_size,
        )

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
        self.stream_start_time = datetime.now(tz=CHINA_STANDARD_TIME).strftime("%Y-%m-%d %H:%M:%S")
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
        temperature = _clamp(self.stream_temperature + math.sin(elapsed / 5.0) * 5.0, SIM_TEMPERATURE_MIN, SIM_TEMPERATURE_MAX)
        humidity = _clamp(self.stream_humidity + math.cos(elapsed / 7.0) * 8.0, SIM_HUMIDITY_MIN, SIM_HUMIDITY_MAX)
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
            start_time=self.stream_start_time,
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
        self.command_results.append({**result, "reported_at": now})
        self.command_results = self.command_results[-20:]
        self._write_command_status_unlocked(command, result, now)
        return result

    def _write_command_status_unlocked(
        self,
        command: dict[str, Any],
        result: dict[str, Any],
        now: float,
    ) -> None:
        """Persist the local controller acknowledgement in its dedicated memory."""
        self.command_status_sequence += 1
        event = {
            "event_id": f"CSE-{uuid.uuid4().hex.upper()}",
            "sequence": self.command_status_sequence,
            "edge_id": self.config.edge_id,
            "command_id": str(command.get("command_id") or ""),
            "device_id": str(command.get("device_id") or self.stream_device_id),
            "command": str(command.get("command") or ""),
            "command_type": str(command.get("command_type") or "UNKNOWN"),
            "status": str(result.get("status") or "EXECUTED"),
            "message": str(result.get("message") or ""),
            "payload": result.get("payload") or {},
            "received_at": command.get("received_at", now),
            "completed_at": now,
            "completed_time": result["time"],
            "success_message": result["successMessage"],
        }
        self.command_status_events.append(event)
        self.command_status_events = self.command_status_events[-20:]
        write_snapshot(
            self.command_status_shm,
            {
                "schema_version": 1,
                "edge_id": self.config.edge_id,
                "sequence": self.command_status_sequence,
                "written_at": now,
                "latest": event,
                "events": self.command_status_events,
            },
            self.config.command_status_memory_size,
        )

    def handle_command(self, command: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            now = time.time()
            self.received_commands.append({**command, "received_at": now})
            self.received_commands = self.received_commands[-20:]

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
                main_data = device.setdefault("mainData", {})
                if command_type in {"STOP_TEST", "HOLD_TEST"}:
                    # Keep every run indicator aligned with the command result.
                    # Otherwise downstream consumers can interpret the same
                    # snapshot as both stopped and running.
                    main_data["runMode"] = 0
                    main_data["status"] = 0
                elif command_type == "SKIP_STEP":
                    main_data["runMode"] = 1
                    main_data["status"] = 1
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
                # Keep the production payload timestamp current as well. The
                # backend uses this controller time to determine data staleness.
                snapshot["time"] = protocol_time()
                write_snapshot(self.shm, snapshot, self.config.shared_memory_size)
                self.last_snapshot = snapshot
                if command_type in {"STOP_TEST", "HOLD_TEST"}:
                    self.stream_active = False
                    # Pausing the test stream preserves the command state in
                    # shared memory. Telemetry uploads stay enabled so the
                    # control center can distinguish a stopped/held test from
                    # an offline controller.
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
        # Uploading is also the device heartbeat. STOP_TEST and HOLD_TEST
        # change the test state only; neither must disable heartbeat uploads.
        with self.lock:
            devices = snapshot.get("devices") or []
            self.upload_events.append({
                "uploaded_at": time.time(),
                "sequence": snapshot.get("sequence"),
                "device_count": len(devices) or (1 if snapshot.get("device_id") else 0),
                "device_id": snapshot.get("device_id") or (devices[0].get("device_id") if devices else ""),
            })
            self.upload_events = self.upload_events[-40:]

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
                "upload_events": self.upload_events,
                "command_status_memory_name": self.config.command_status_memory_name,
                "command_status_events": self.command_status_events,
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
    if config.control_center_enabled:
        edge_client = WebSocketEdgeClient(
            config,
            command_handler=state.handle_command,
            should_upload=state.should_upload,
            on_uploaded=state.on_uploaded,
        )
        threading.Thread(target=edge_client.run_forever, daemon=True, name="edge-websocket-client").start()

    handler = _build_handler(state)
    server = ThreadingHTTPServer((host, port), handler)
    print(f"manual input UI started: http://{host}:{port}")
    if config.control_center_enabled:
        print(f"control-center websocket: {config.websocket_endpoint}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("manual input UI stopped")
    finally:
        server.server_close()
        state.shm.close()
        state.command_status_shm.close()


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
    if not SIM_TEMPERATURE_MIN <= temperature <= SIM_TEMPERATURE_MAX:
        raise ValueError(f"temperature must be between {SIM_TEMPERATURE_MIN:g} and {SIM_TEMPERATURE_MAX:g}")
    if not SIM_HUMIDITY_MIN <= humidity <= SIM_HUMIDITY_MAX:
        raise ValueError(f"humidity must be between {SIM_HUMIDITY_MIN:g} and {SIM_HUMIDITY_MAX:g}")
    return temperature, humidity


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


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
    .state-section { display: flex; flex-direction: column; gap: 18px; }
    .panel-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
    .panel-heading h2 { margin-bottom: 4px; }
    .panel-heading p { margin: 0; color: var(--muted); font-size: 12px; line-height: 1.5; }
    .panel-count { flex: 0 0 auto; padding: 6px 10px; border-radius: 999px; background: #eff6ff; color: #1d4ed8; font-size: 12px; font-weight: 700; }
    .snapshot-shell { overflow: hidden; border: 1px solid #1e293b; border-radius: 8px; background: #0b1020; }
    .snapshot-label { padding: 9px 12px; border-bottom: 1px solid #25324a; color: #93c5fd; font-size: 12px; font-weight: 700; }
    .snapshot-shell pre { min-height: 120px; max-height: 180px; border-radius: 0; font-size: 11px; }
    .command-panel { min-height: 0; }
    .write-launcher { display: grid; place-items: center; min-height: 220px; padding: 24px; border: 1px dashed #bfdbfe; border-radius: 10px; background: linear-gradient(145deg, #eff6ff, #f8fafc); text-align: center; }
    .write-launcher strong { display: block; color: #1e3a8a; font-size: 18px; }
    .write-launcher p { margin: 8px 0 18px; color: var(--muted); font-size: 13px; line-height: 1.6; }
    .write-launcher button { width: auto; min-width: 180px; margin: 0; }
    main > section:first-child > label,
    main > section:first-child > input,
    main > section:first-child > textarea,
    main > section:first-child > .hint,
    main > section:first-child > #legacyWriteBtn { display: none; }
    .modal-backdrop { position: fixed; inset: 0; z-index: 10; display: grid; place-items: center; padding: 20px; background: rgba(15,23,42,.58); }
    .modal-backdrop[hidden] { display: none; }
    .write-modal { width: min(520px, 100%); max-height: min(720px, 92vh); overflow: auto; padding: 22px; border: 1px solid #cbd5e1; border-radius: 12px; background: #fff; box-shadow: 0 24px 64px rgba(15,23,42,.28); }
    .modal-actions { display: flex; gap: 10px; }
    .modal-actions button { margin-top: 16px; }
    .modal-actions .secondary-button { background: #e2e8f0; color: #334155; }
    .panel-heading > .secondary-button { width: 36px; margin: 0; padding: 6px; background: #e2e8f0; color: #334155; font-size: 20px; line-height: 1; }
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
    .command-list {
      display: grid;
      gap: 8px;
      min-height: 180px;
      max-height: 520px;
      margin-top: 14px;
      overflow: auto;
      padding-right: 4px;
    }
    .command-item {
      display: grid;
      gap: 10px;
      padding: 10px 12px;
      border: 1px solid #cbd5e1;
      border-left: 3px solid #2563eb;
      border-radius: 6px;
      background: #f8fafc;
    }
    .command-item.result-failed { border-left-color: #dc2626; }
    .command-item.result-executed { border-left-color: #16a34a; }
    .command-item-head {
      display: grid;
      grid-template-columns: minmax(110px, .8fr) minmax(100px, .7fr) minmax(130px, 1fr);
      gap: 10px;
      align-items: center;
    }
    .command-item:first-child { box-shadow: 0 0 0 2px rgba(37,99,235,.12); }
    .command-item strong { color: #0f172a; font-size: 14px; }
    .command-item span, .command-item small { display: block; color: #64748b; font-size: 12px; }
    .command-item small { margin-top: 3px; }
    .command-raw {
      margin: 0;
      max-height: 180px;
      overflow: auto;
      padding: 10px;
      border: 1px solid #dbe3ee;
      border-radius: 6px;
      background: #0b1020;
      color: #dbeafe;
      font: 12px/1.55 Consolas, monospace;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .command-raw-label { color: #64748b; font-size: 11px; letter-spacing: .04em; }
    .command-empty { padding: 22px 12px; border: 1px dashed #cbd5e1; border-radius: 6px; color: #64748b; text-align: center; }
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
      .command-item-head { grid-template-columns: 1fr; gap: 5px; }
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
      <h2>模拟数据控制</h2>
      <div class="write-launcher">
        <div>
          <strong>写入实时数据</strong>
          <p>设置设备信息、温湿度和可选原始输入，启动或更新本机模拟数据流。</p>
          <button id="openWriteBtn" type="button">打开写入窗口</button>
        </div>
      </div>
      <label for="deviceId">设备编号</label>
      <input id="deviceId" value="SIM-MANUAL-001" />
      <label for="deviceName">设备名称</label>
      <input id="deviceName" value="Manual Input Chamber" />
      <label for="temperature">温度</label>
      <input id="temperature" type="number" min="-200" max="500" step="0.1" value="25.0" />
      <label for="humidity">湿度</label>
      <input id="humidity" type="number" min="0" max="100" step="0.1" value="60.0" />
      <label for="raw">串数据输入</label>
      <textarea id="raw" placeholder="支持：25,60 或 温度=25,湿度=60 或 JSON"></textarea>
      <div class="hint">温度范围 -200～500°C；湿度范围 0～100%RH。模拟流会在设定值附近产生更明显的动态波动。</div>
      <button id="legacyWriteBtn" type="button">启动实时数据流</button>
      <div id="message" class="status"></div>
    </section>
    <section class="state-section">
      <div class="panel-heading">
        <div>
          <h2>实时状态</h2>
          <p>共享内存中的最新快照与当前连接信息</p>
        </div>
        <span class="panel-count">实时</span>
      </div>
      <div class="meta">
        <div><span>共享内存</span><strong id="memoryName">-</strong></div>
        <div><span>工控机编号</span><strong id="edgeId">-</strong></div>
        <div><span>总服务端</span><strong id="serverUrl">-</strong></div>
      </div>
      <div class="snapshot-shell">
        <div class="snapshot-label">最新快照 JSON</div>
        <pre id="snapshot">{}</pre>
      </div>
      <h2 style="margin-top:16px;">总控命令监视</h2>
      <div class="command-panel">
        <div class="panel-heading">
          <div>
            <h2>总控命令时间线</h2>
            <p>按接收顺序排列，最新命令显示在底部</p>
          </div>
          <span id="commandCount" class="panel-count">0 条</span>
        </div>
        <div id="commands" class="command-list" aria-live="polite"><div class="command-empty">暂无收到的命令</div></div>
      </div>
    </section>
  </main>
  <div id="writeModal" class="modal-backdrop" hidden>
    <section class="write-modal" role="dialog" aria-modal="true" aria-labelledby="writeModalTitle">
      <div class="panel-heading">
        <div>
          <h2 id="writeModalTitle">写入实时数据</h2>
          <p>填写参数后启动或更新模拟数据流</p>
        </div>
        <button id="closeWriteBtn" class="secondary-button" type="button" aria-label="关闭">×</button>
      </div>
      <label for="modalDeviceId">设备编号</label>
      <input id="modalDeviceId" value="SIM-MANUAL-001" />
      <label for="modalDeviceName">设备名称</label>
      <input id="modalDeviceName" value="Manual Input Chamber" />
      <label for="modalTemperature">温度</label>
      <input id="modalTemperature" type="number" min="-200" max="500" step="0.1" value="25.0" />
      <label for="modalHumidity">湿度</label>
      <input id="modalHumidity" type="number" min="0" max="100" step="0.1" value="60.0" />
      <label for="modalRaw">原始输入（可选）</label>
      <textarea id="modalRaw" placeholder="支持：25,60 或 温度=25,湿度=60 或 JSON"></textarea>
      <div class="hint">温度范围 -200~500°C；湿度范围 0~100%RH。</div>
      <div class="modal-actions">
        <button id="writeBtn" type="button">启动实时数据流</button>
        <button id="cancelWriteBtn" class="secondary-button" type="button">取消</button>
      </div>
    </section>
  </div>
  <script>
    const message = document.querySelector("#message");
    const snapshot = document.querySelector("#snapshot");
    const commands = document.querySelector("#commands");
    const commandCount = document.querySelector("#commandCount");
    const writeBtn = document.querySelector("#writeBtn");
    const writeModal = document.querySelector("#writeModal");
    const openWriteBtn = document.querySelector("#openWriteBtn");
    const closeWriteBtn = document.querySelector("#closeWriteBtn");
    const cancelWriteBtn = document.querySelector("#cancelWriteBtn");
    const streamBanner = document.querySelector("#streamBanner");
    const streamTitle = document.querySelector("#streamTitle");
    const streamDetail = document.querySelector("#streamDetail");
    const streamBadge = document.querySelector("#streamBadge");

    function setMessage(text, tone) {
      message.textContent = text;
      message.className = "status " + (tone || "");
    }

    function closeWriteModal() {
      writeModal.hidden = true;
    }

    async function refreshStatus() {
      const response = await fetch("/api/status");
      const data = await response.json();
      document.querySelector("#memoryName").textContent = data.shared_memory_name || "-";
      document.querySelector("#edgeId").textContent = data.edge_id || "-";
      document.querySelector("#serverUrl").textContent = data.server_url || "-";
      snapshot.textContent = JSON.stringify(data.memory_snapshot || data.last_snapshot || data, null, 2);
      renderCommands(data.received_commands || [], data.command_results || []);
      updateStreamBanner(data);
    }

    function renderCommands(receivedCommands, commandResults) {
      commands.replaceChildren();
      commandCount.textContent = `${receivedCommands.length} 条`;
      if (!receivedCommands.length) {
        const empty = document.createElement("div");
        empty.className = "command-empty";
        empty.textContent = "暂无收到的命令";
        commands.append(empty);
        return;
      }
      receivedCommands.forEach((command, index) => {
        const result = commandResults[index] || {};
        const item = document.createElement("article");
        item.className = `command-item result-${String(result.status || "pending").toLowerCase()}`;
        const head = document.createElement("div");
        head.className = "command-item-head";
        const commandCell = document.createElement("div");
        const commandName = document.createElement("strong");
        commandName.textContent = command.command || command.command_type || "未知命令";
        commandCell.append(commandName);
        const type = document.createElement("small");
        type.textContent = command.command_type || "未分类";
        commandCell.append(type);
        const timeCell = document.createElement("div");
        const time = document.createElement("span");
        time.textContent = command.time || formatTimestamp(command.received_at);
        timeCell.append(time);
        const resultCell = document.createElement("div");
        const resultText = document.createElement("strong");
        resultText.textContent = result.status || "已接收";
        resultCell.append(resultText);
        const messageText = document.createElement("small");
        messageText.textContent = result.message || "等待执行结果";
        resultCell.append(messageText);
        head.append(commandCell, timeCell, resultCell);
        const rawLabel = document.createElement("div");
        rawLabel.className = "command-raw-label";
        rawLabel.textContent = "接收原始 JSON";
        const raw = document.createElement("pre");
        raw.className = "command-raw";
        const rawCommand = { ...command };
        delete rawCommand.received_at;
        raw.textContent = JSON.stringify(rawCommand, null, 2);
        item.append(head, rawLabel, raw);
        commands.append(item);
      });
    }

    function formatTimestamp(value) {
      if (!value) return "时间未知";
      return new Date(Number(value) * 1000).toLocaleString("zh-CN", { hour12: false });
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
      const raw = document.querySelector("#modalRaw").value.trim();
      const payload = {
        device_id: document.querySelector("#modalDeviceId").value.trim(),
        device_name: document.querySelector("#modalDeviceName").value.trim()
      };
      if (raw) {
        payload.raw = raw;
      } else {
        payload.temperature = document.querySelector("#modalTemperature").value;
        payload.humidity = document.querySelector("#modalHumidity").value;
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
        closeWriteModal();
      } catch (error) {
        setMessage(error.message, "bad");
      } finally {
        writeBtn.disabled = false;
        refreshStatus().catch(() => {});
      }
    }

    openWriteBtn.addEventListener("click", () => { writeModal.hidden = false; });
    closeWriteBtn.addEventListener("click", closeWriteModal);
    cancelWriteBtn.addEventListener("click", closeWriteModal);
    writeModal.addEventListener("click", event => { if (event.target === writeModal) closeWriteModal(); });
    writeBtn.addEventListener("click", writeValues);
    refreshStatus().catch(error => setMessage(error.message, "bad"));
    setInterval(() => refreshStatus().catch(() => {}), 2000);
  </script>
</body>
</html>"""


# Dedicated operations-console UI. This assignment intentionally replaces the
# legacy form page above so the running edge has a single, log-first interface.
_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>工控机运行控制台</title>
  <style>
    :root { --bg:#07111f; --panel:#0c1b2e; --panel-2:#10253d; --line:#233a55; --text:#e5effc; --muted:#8da3bd; --blue:#44a5ff; --green:#46d6a0; --amber:#ffbf5b; --red:#ff7676; }
    * { box-sizing:border-box; }
    body { margin:0; min-height:100vh; color:var(--text); background:radial-gradient(circle at 85% 0%,#12375a 0,#07111f 38%); font:14px/1.45 "Microsoft YaHei",Arial,sans-serif; }
    button,input,textarea { font:inherit; }
    .topbar { display:flex; justify-content:space-between; align-items:center; gap:20px; padding:16px 28px; border-bottom:1px solid var(--line); background:rgba(7,17,31,.82); }
    .brand { display:flex; align-items:center; gap:12px; }
    .mark { display:grid; place-items:center; width:38px; height:38px; border:1px solid #387bb5; border-radius:9px; color:#bce0ff; background:#102d4a; font-weight:800; letter-spacing:.06em; }
    h1 { margin:0; font-size:17px; letter-spacing:.04em; } .sub { margin:2px 0 0; color:var(--muted); font-size:12px; }
    .connection { display:flex; align-items:center; gap:8px; color:#c7d9ed; font-size:12px; } .dot { width:8px; height:8px; border-radius:50%; background:var(--amber); box-shadow:0 0 12px currentColor; } .dot.live { background:var(--green); }
    .shell { max-width:1500px; margin:0 auto; padding:24px; display:grid; grid-template-columns:250px minmax(0,1fr) 300px; gap:16px; }
    .panel { min-width:0; border:1px solid var(--line); border-radius:12px; background:linear-gradient(160deg,rgba(16,37,61,.96),rgba(9,25,43,.96)); box-shadow:0 16px 34px rgba(0,0,0,.14); }
    .rail { padding:18px; } .eyebrow { margin:0 0 8px; color:#6faee7; font-size:11px; font-weight:700; letter-spacing:.12em; text-transform:uppercase; }
    .edge-id { margin:0; font:700 20px/1.25 Consolas,monospace; word-break:break-all; } .endpoint { margin:10px 0 20px; color:var(--muted); font:12px/1.6 Consolas,monospace; word-break:break-all; }
    .control { width:100%; padding:12px 14px; border:0; border-radius:8px; color:#041220; background:linear-gradient(135deg,#63bcff,#52d5ff); font-weight:800; cursor:pointer; } .control:hover { filter:brightness(1.08); } .control:focus-visible,button:focus-visible,summary:focus-visible { outline:2px solid white; outline-offset:2px; }
    .rail-section { margin-top:24px; padding-top:18px; border-top:1px solid var(--line); } .rail-row { display:flex; justify-content:space-between; gap:12px; padding:8px 0; color:var(--muted); font-size:12px; } .rail-row strong { color:var(--text); font-weight:600; text-align:right; }
    .device-run-card { margin-top:18px; padding:16px; border:1px solid #315271; border-radius:10px; background:linear-gradient(145deg,#112f4b,#0b1d31); text-align:center; } .device-run-card.running { border-color:#2dbb87; box-shadow:inset 0 0 0 1px rgba(70,214,160,.18); } .device-run-card.stopped { border-color:#ff8b8b; } .device-run-card.holding { border-color:#f2b95c; } .device-run-label { color:#a8bed5; font-size:11px; letter-spacing:.08em; } .device-run-value { margin-top:8px; font-size:26px; font-weight:900; letter-spacing:.08em; color:var(--amber); } .device-run-card.running .device-run-value { color:var(--green); } .device-run-card.stopped .device-run-value { color:var(--red); } .device-run-card.holding .device-run-value { color:var(--amber); } .device-run-detail { margin-top:6px; color:var(--muted); font-size:11px; }
    .command-state-card { margin-top:18px; padding:12px; border:1px solid #315271; border-left:3px solid var(--amber); border-radius:8px; background:rgba(6,18,32,.48); } .command-state-card.executed { border-left-color:var(--green); } .command-state-card.failed,.command-state-card.rejected { border-left-color:var(--red); } .command-state-label { color:var(--muted); font-size:11px; } .command-state-name { margin-top:5px; color:var(--text); font-size:16px; font-weight:800; } .command-state-result { margin-top:5px; color:var(--amber); font:700 12px Consolas,monospace; } .command-state-card.executed .command-state-result { color:var(--green); } .command-state-card.failed .command-state-result,.command-state-card.rejected .command-state-result { color:var(--red); } .command-state-time { margin-top:7px; color:var(--muted); font-size:11px; }
    .traffic { display:grid; gap:16px; } .stream { padding:18px; } .stream-head { display:flex; justify-content:space-between; align-items:flex-start; gap:12px; margin-bottom:14px; } h2 { margin:0; font-size:15px; } .stream-head p { margin:4px 0 0; color:var(--muted); font-size:12px; } .counter { padding:4px 8px; border:1px solid #315271; border-radius:999px; color:#aed8ff; font:12px Consolas,monospace; white-space:nowrap; }
    .feed { display:grid; gap:8px; min-height:120px; max-height:260px; overflow:auto; padding-right:4px; } .command-feed { max-height:540px; }
    .history-toggle { width:100%; margin-top:12px; padding:9px 12px; border:1px dashed #3b668b; border-radius:7px; color:#9ccfff; background:transparent; cursor:pointer; font-size:12px; } .history-toggle:hover { border-style:solid; background:#0b2037; }
    .event { display:grid; grid-template-columns:12px minmax(0,1fr) auto; gap:12px; align-items:start; padding:12px; border:1px solid #213b57; border-radius:8px; background:rgba(6,18,32,.46); } .event:hover { border-color:#3973a7; background:#0b2037; }
    .event-bar { width:3px; height:100%; min-height:42px; border-radius:9px; background:var(--blue); } .event.upload .event-bar { background:var(--green); } .event.failed .event-bar { background:var(--red); } .event.pending .event-bar { background:var(--amber); }
    .event-title { color:#f1f7ff; font-weight:700; } .event-detail { margin-top:3px; color:var(--muted); font-size:12px; } time { color:#8da3bd; font:11px Consolas,monospace; white-space:nowrap; }
    details { grid-column:2 / -1; } summary { color:#79bbf2; cursor:pointer; font-size:12px; } .raw { max-height:180px; overflow:auto; margin:8px 0 0; padding:10px; border-radius:6px; color:#c8e3ff; background:#040b14; font:11px/1.55 Consolas,monospace; white-space:pre-wrap; word-break:break-word; }
    .command-details { grid-column:1 / -1; } .command-details summary { display:grid; grid-template-columns:12px minmax(0,1fr) auto; gap:12px; align-items:center; padding:12px; border:1px solid #213b57; border-radius:8px; color:var(--text); background:rgba(6,18,32,.46); cursor:pointer; list-style:none; } .command-details summary::-webkit-details-marker { display:none; } .command-details summary::before { content:""; width:3px; height:32px; border-radius:8px; background:var(--blue); } .command-details summary:hover { border-color:#3973a7; background:#0b2037; } .command-details[open] summary { border-color:#4b9cde; border-radius:8px 8px 0 0; } .command-details .raw { margin:0; border-radius:0 0 8px 8px; border:1px solid #315271; border-top:0; }
    .command-open { display:grid; grid-template-columns:12px minmax(0,1fr) auto; gap:12px; align-items:center; width:100%; padding:12px; border:1px solid #213b57; border-radius:8px; color:var(--text); background:rgba(6,18,32,.46); text-align:left; cursor:pointer; } .command-open::before { content:""; width:3px; height:32px; border-radius:8px; background:var(--blue); } .command-open:hover { border-color:#3973a7; background:#0b2037; } .command-open time { justify-self:end; }
    .empty { padding:24px; border:1px dashed #315271; border-radius:8px; color:var(--muted); text-align:center; }
    .inspector { padding:18px; } .inspector pre { min-height:320px; max-height:calc(100vh - 220px); overflow:auto; margin:14px 0 0; padding:12px; border:1px solid #203952; border-radius:8px; color:#bcdcff; background:#040b14; font:11px/1.55 Consolas,monospace; white-space:pre-wrap; word-break:break-word; }
    .modal { position:fixed; inset:0; z-index:10; display:grid; place-items:center; padding:20px; background:rgba(0,0,0,.66); } .modal[hidden] { display:none; } .dialog { width:min(520px,100%); padding:22px; border:1px solid #3f668b; border-radius:12px; background:#0d2036; box-shadow:0 30px 80px rgba(0,0,0,.55); }
    .dialog-head { display:flex; justify-content:space-between; gap:16px; align-items:flex-start; } .close { width:32px; height:32px; border:1px solid #355573; border-radius:6px; color:#c9d9eb; background:#112b45; cursor:pointer; font-size:20px; }
    label { display:block; margin:15px 0 6px; color:#a9bdd2; font-size:12px; } input,textarea { width:100%; padding:10px 11px; border:1px solid #355573; border-radius:7px; color:var(--text); background:#08182a; } textarea { min-height:78px; resize:vertical; font-family:Consolas,monospace; }
    .actions { display:flex; gap:10px; margin-top:18px; } .actions button { flex:1; padding:11px; border:0; border-radius:7px; cursor:pointer; font-weight:800; } .submit { color:#041220; background:#63bcff; } .cancel { color:#c9d9eb; background:#213b57; } .message { min-height:20px; margin-top:12px; color:var(--muted); font-size:12px; } .message.ok { color:var(--green); } .message.bad { color:var(--red); }
    @media (max-width:1080px) { .shell { grid-template-columns:220px minmax(0,1fr); } .inspector { grid-column:1 / -1; } .inspector pre { max-height:200px; } }
    @media (max-width:720px) { .topbar { padding:14px 16px; } .connection span { display:none; } .shell { grid-template-columns:1fr; padding:14px; } .inspector { grid-column:auto; } .event { grid-template-columns:8px minmax(0,1fr); } .event time { grid-column:2; } details { grid-column:2; } }
  </style>
</head>
<body>
  <header class="topbar">
    <div class="brand"><div class="mark">EDGE</div><div><h1>工控机运行控制台</h1><p class="sub">命令与数据传输监视</p></div></div>
    <div class="connection"><i id="connectionDot" class="dot"></i><span id="connectionText">正在读取本机状态</span></div>
  </header>
  <main class="shell">
    <aside class="panel rail">
      <p class="eyebrow">本机节点</p><p id="edgeId" class="edge-id">--</p><p id="serverUrl" class="endpoint">--</p>
      <button id="openWrite" class="control" type="button">写入模拟数据</button>
      <div class="rail-section"><p class="eyebrow">传输概览</p><div class="rail-row"><span>数据流</span><strong id="streamState">--</strong></div><div class="rail-row"><span>已上报</span><strong id="uploadTotal">0</strong></div><div class="rail-row"><span>已接收命令</span><strong id="commandTotal">0</strong></div></div>
      <div id="deviceRunCard" class="device-run-card"><div class="device-run-label">当前设备运行状态</div><div id="deviceRunValue" class="device-run-value">待命</div><div id="deviceRunDetail" class="device-run-detail">等待设备快照</div></div>
      <div id="commandStateCard" class="command-state-card"><div class="command-state-label">最新命令运行状态</div><div id="commandStateName" class="command-state-name">等待命令</div><div id="commandStateResult" class="command-state-result">--</div><div id="commandStateTime" class="command-state-time">尚无执行状态回传</div></div>
    </aside>
    <section class="traffic">
      <section class="panel stream"><div class="stream-head"><div><h2>上发快照日志</h2><p>本机成功提交到总服务端的数据记录</p></div><span id="uploadCount" class="counter">0 条</span></div><div id="uploads" class="feed"><div class="empty">等待首次快照上报</div></div></section>
      <section class="panel stream"><div class="stream-head"><div><h2>下行命令日志</h2><p>仅显示最新命令；历史记录可按需展开</p></div><span id="commandCount" class="counter">0 条</span></div><div id="latestCommand" class="feed"><div class="empty">尚未接收到总控命令</div></div><button id="toggleHistory" class="history-toggle" type="button" hidden>展开历史命令</button><div id="commands" class="feed command-feed" hidden></div></section>
    </section>
    <aside class="panel inspector"><p class="eyebrow">快照检查器</p><h2>当前共享内存</h2><pre id="snapshot">{}</pre></aside>
  </main>
  <div id="modal" class="modal" hidden><section class="dialog" role="dialog" aria-modal="true" aria-labelledby="dialogTitle"><div class="dialog-head"><div><h2 id="dialogTitle">写入模拟数据</h2><p class="sub">启动或更新本机模拟数据流</p></div><button id="closeModal" class="close" type="button" aria-label="关闭">×</button></div><label>设备编号<input id="deviceId" value="SIM-MANUAL-001" /></label><label>设备名称<input id="deviceName" value="Manual Input Chamber" /></label><label>温度（°C）<input id="temperature" type="number" min="-200" max="500" step="0.1" value="25" /></label><label>湿度（%RH）<input id="humidity" type="number" min="0" max="100" step="0.1" value="60" /></label><label>原始输入（可选）<textarea id="raw" placeholder="例如：25,60 或 JSON"></textarea></label><div class="actions"><button id="submitWrite" class="submit" type="button">写入并启动</button><button id="cancelWrite" class="cancel" type="button">取消</button></div><div id="message" class="message" aria-live="polite"></div></section></div>
  <div id="jsonModal" class="modal" hidden><section class="dialog" role="dialog" aria-modal="true" aria-labelledby="jsonTitle"><div class="dialog-head"><div><h2 id="jsonTitle">接收原始 JSON</h2><p class="sub">工控机接收到的总控命令</p></div><button id="closeJsonModal" class="close" type="button" aria-label="关闭">×</button></div><pre id="jsonContent" class="raw" style="max-height:60vh; margin-top:16px;"></pre></section></div>
  <script>
    const $ = selector => document.querySelector(selector);
    const modal = $('#modal'); const jsonModal = $('#jsonModal'); const message = $('#message'); let historyExpanded = false; let latestCommandRecords = [];
    const timeText = value => value ? new Date(Number(value) * 1000).toLocaleString('zh-CN',{hour12:false}) : '--';
    function setMessage(text,tone='') { message.textContent=text; message.className=`message ${tone}`; }
    function empty(container,text) { container.replaceChildren(); const node=document.createElement('div'); node.className='empty'; node.textContent=text; container.append(node); }
    function makeEvent(kind,title,detail,when,raw,status='') { const row=document.createElement('article'); row.className=`event ${kind} ${String(status).toLowerCase()}`; const bar=document.createElement('i'); bar.className='event-bar'; const body=document.createElement('div'); const name=document.createElement('div'); name.className='event-title'; name.textContent=title; const info=document.createElement('div'); info.className='event-detail'; info.textContent=detail; body.append(name,info); const clock=document.createElement('time'); clock.textContent=timeText(when); row.append(bar,body,clock); if(raw) { const details=document.createElement('details'); const summary=document.createElement('summary'); summary.textContent='查看接收原始 JSON'; const pre=document.createElement('pre'); pre.className='raw'; pre.textContent=JSON.stringify(raw,null,2); details.append(summary,pre); row.append(details); } return row; }
    function makeCommandEvent(title, when, raw) { const button=document.createElement('button'); button.type='button'; button.className='command-open'; const name=document.createElement('strong'); name.textContent=title; const clock=document.createElement('time'); clock.textContent=timeText(when); button.append(name,clock); button.addEventListener('click',()=>{ $('#jsonContent').textContent=JSON.stringify(raw,null,2); jsonModal.hidden=false; $('#closeJsonModal').focus(); }); return button; }
    function scrollToLatest(box) { requestAnimationFrame(() => { box.scrollTop = box.scrollHeight; }); }
    function renderUploads(events) { const box=$('#uploads'); $('#uploadCount').textContent=`${events.length} 条`; $('#uploadTotal').textContent=events.length; if(!events.length) return empty(box,'等待首次快照上报'); box.replaceChildren(); events.forEach(event=>box.append(makeEvent('upload','快照上传成功',`设备 ${event.device_id || '--'} · 序列 ${event.sequence ?? '--'} · ${event.device_count ?? 0} 台设备`,event.uploaded_at,null))); scrollToLatest(box); }
    function renderCommands(commands,results) { const history=$('#commands'); const latestBox=$('#latestCommand'); const toggle=$('#toggleHistory'); latestCommandRecords=commands; $('#commandCount').textContent=`${commands.length} 条`; $('#commandTotal').textContent=commands.length; if(!commands.length) { empty(latestBox,'尚未接收到总控命令'); history.hidden=true; toggle.hidden=true; return; } const latest=commands[commands.length - 1]; const latestRaw={...latest}; delete latestRaw.received_at; latestBox.replaceChildren(makeCommandEvent(latest.command || latest.command_type || '未知命令',latest.received_at,latestRaw)); const historyCommands=commands.slice(0,-1); toggle.hidden=!historyCommands.length; if(!historyCommands.length) { history.hidden=true; return; } toggle.textContent=historyExpanded ? `收起历史命令（${historyCommands.length} 条）` : `展开历史命令（${historyCommands.length} 条）`; history.hidden=!historyExpanded; if(!historyExpanded) return; history.replaceChildren(); historyCommands.forEach(command=>{ const raw={...command}; delete raw.received_at; history.append(makeCommandEvent(command.command || command.command_type || '未知命令',command.received_at,raw)); }); scrollToLatest(history); }
    function renderDeviceRunState(snapshot) { const card=$('#deviceRunCard'); const value=$('#deviceRunValue'); const detail=$('#deviceRunDetail'); if(!snapshot || !Object.keys(snapshot).length) { card.className='device-run-card'; value.textContent='待命'; detail.textContent='等待设备快照'; return; } const state=String(snapshot.status?.state || snapshot.run_state || '').trim(); const running=Number(snapshot.program?.run ?? snapshot.mainData?.runMode ?? snapshot.running ?? 0) === 1; let tone=''; let label='待命'; if(/停止|STOP/i.test(state)) { tone='stopped'; label='已停止'; } else if(/保持|HOLD/i.test(state)) { tone='holding'; label='保持中'; } else if(running || /运行|RUN/i.test(state)) { tone='running'; label='运行中'; } card.className=`device-run-card ${tone}`; value.textContent=label; const runTime=snapshot.timeData?.runTime; detail.textContent=runTime ? `运行时间：${runTime}` : (state || '本机实时状态'); }
    function renderCommandState(events) { const card=$('#commandStateCard'); const latest=events.at(-1); if(!latest) { card.className='command-state-card'; $('#commandStateName').textContent='等待命令'; $('#commandStateResult').textContent='--'; $('#commandStateTime').textContent='尚无执行状态回传'; return; } const status=String(latest.status || 'PENDING').toLowerCase(); card.className=`command-state-card ${status}`; $('#commandStateName').textContent=latest.command || latest.command_type || '未知命令'; $('#commandStateResult').textContent=latest.status || 'PENDING'; $('#commandStateTime').textContent=`完成时间：${timeText(latest.completed_at)}`; }
    function update(data) { $('#edgeId').textContent=data.edge_id || '--'; $('#serverUrl').textContent=data.server_url || '--'; const streaming=Boolean(data.stream_active); $('#streamState').textContent=streaming ? '运行中' : '待命'; $('#streamState').style.color=streaming ? 'var(--green)' : 'var(--amber)'; $('#connectionDot').className=`dot ${data.last_write_error ? '' : 'live'}`; $('#connectionText').textContent=data.last_write_error ? '本机写入异常' : '本机服务运行中'; const snapshot=data.memory_snapshot || data.last_snapshot || {}; $('#snapshot').textContent=JSON.stringify(snapshot,null,2); renderUploads(data.upload_events || []); renderCommands(data.received_commands || [],data.command_results || []); renderDeviceRunState(snapshot); renderCommandState(data.command_status_events || []); }
    async function refresh() { const response=await fetch('/api/status'); if(!response.ok) throw new Error('状态读取失败'); update(await response.json()); }
    async function submitWrite() { const button=$('#submitWrite'); button.disabled=true; setMessage('正在写入本机共享内存…'); const raw=$('#raw').value.trim(); const payload={device_id:$('#deviceId').value.trim(),device_name:$('#deviceName').value.trim()}; if(raw) payload.raw=raw; else { payload.temperature=$('#temperature').value; payload.humidity=$('#humidity').value; } try { const response=await fetch('/api/write',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}); const data=await response.json(); if(!response.ok) throw new Error(data.error || '写入失败'); setMessage('模拟数据流已启动','ok'); setTimeout(()=>modal.hidden=true,350); refresh(); } catch(error) { setMessage(error.message,'bad'); } finally { button.disabled=false; } }
    const close=()=>modal.hidden=true; $('#openWrite').addEventListener('click',()=>{ modal.hidden=false; $('#deviceId').focus(); }); $('#closeModal').addEventListener('click',close); $('#cancelWrite').addEventListener('click',close); $('#closeJsonModal').addEventListener('click',()=>{ jsonModal.hidden=true; }); $('#toggleHistory').addEventListener('click',()=>{ historyExpanded=!historyExpanded; renderCommands(latestCommandRecords,[]); }); modal.addEventListener('click',event=>{if(event.target===modal)close();}); $('#submitWrite').addEventListener('click',submitWrite); document.addEventListener('keydown',event=>{if(event.key==='Escape')close();}); refresh().catch(error=>{ $('#connectionText').textContent=error.message; }); setInterval(()=>refresh().catch(()=>{}),1200);
  </script>
</body>
</html>"""
