import json
from dataclasses import dataclass
from pathlib import Path
from typing import Union


@dataclass(frozen=True)
class EdgeConfig:
    edge_id: str
    device_ip: str
    agent_version: str
    server_url: str = ""
    upload_interval_seconds: float = 1.0
    stream_interval_seconds: float = 1.0
    shared_memory_name: str = "BE_W"
    shared_memory_size: int = 1024 * 256
    command_status_memory_name: str = "BE_R"
    command_status_memory_size: int = 1024 * 64
    auth_token: str = ""
    command_request_memory_name: str = "FE_W"
    command_request_memory_size: int = 1024 * 64
    realtime_poll_interval_seconds: float = 1.0
    command_status_idle_poll_interval_seconds: float = 1.0
    command_status_active_poll_interval_seconds: float = 0.2
    sqlite_path: str = "device-edge.db"
    control_center_enabled: bool = False
    allowed_operator_ids: tuple[str, ...] = ("web-admin",)

    @property
    def websocket_endpoint(self) -> str:
        """Central-service endpoint used by the persistent edge connection."""
        base = self.server_url.rstrip("/")
        if base.startswith("https://"):
            base = "wss://" + base[len("https://"):]
        elif base.startswith("http://"):
            base = "ws://" + base[len("http://"):]
        elif not base.startswith(("ws://", "wss://")):
            base = "ws://" + base
        return base + "/api/edge/ws"


def load_config(path: Union[str, Path]) -> EdgeConfig:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    auth = data.get("auth", {})
    control_center = data.get("control_center", {})
    local_api = data.get("local_api", {})
    allowed_operator_ids = auth.get("allowed_operator_ids", ["web-admin"])
    return EdgeConfig(
        edge_id=data["edge_id"],
        device_ip=str(data.get("device_ip", "")).strip(),
        agent_version=data.get("agent_version", "0.1.0"),
        server_url=control_center.get("server_url", data.get("server_url", "")),
        upload_interval_seconds=float(data.get("upload_interval_seconds", 0.5)),
        stream_interval_seconds=float(data.get("stream_interval_seconds", data.get("upload_interval_seconds", 0.5))),
        shared_memory_name=data.get("shared_memory_name", "BE_W"),
        shared_memory_size=int(data.get("shared_memory_size", 1024 * 256)),
        command_status_memory_name=data.get("command_status_memory_name", "BE_R"),
        command_status_memory_size=int(data.get("command_status_memory_size", 1024 * 64)),
        auth_token=auth.get("token", ""),
        command_request_memory_name=data.get("command_request_memory_name", "FE_W"),
        command_request_memory_size=int(data.get("command_request_memory_size", 1024 * 64)),
        realtime_poll_interval_seconds=float(local_api.get("realtime_poll_interval_seconds", 1.0)),
        command_status_idle_poll_interval_seconds=float(local_api.get("command_status_idle_poll_interval_seconds", 1.0)),
        command_status_active_poll_interval_seconds=float(local_api.get("command_status_active_poll_interval_seconds", 0.2)),
        sqlite_path=str(data.get("sqlite_path", "device-edge.db")),
        control_center_enabled=bool(control_center.get("enabled", False)),
        allowed_operator_ids=tuple(str(item) for item in allowed_operator_ids if str(item).strip()),
    )


def copy_example_config(target: Union[str, Path]) -> None:
    source = Path(__file__).with_name("config.example.json")
    Path(target).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
