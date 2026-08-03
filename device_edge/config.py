import json
from dataclasses import dataclass
from pathlib import Path
from typing import Union


@dataclass(frozen=True)
class EdgeConfig:
    edge_id: str
    device_ip: str
    agent_version: str
    server_url: str
    upload_interval_seconds: float
    stream_interval_seconds: float
    shared_memory_name: str
    shared_memory_size: int
    command_status_memory_name: str
    command_status_memory_size: int
    auth_token: str = ""

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
    return EdgeConfig(
        edge_id=data["edge_id"],
        device_ip=str(data.get("device_ip", "")).strip(),
        agent_version=data.get("agent_version", "0.1.0"),
        server_url=data["server_url"],
        upload_interval_seconds=float(data.get("upload_interval_seconds", 0.5)),
        stream_interval_seconds=float(data.get("stream_interval_seconds", data.get("upload_interval_seconds", 0.5))),
        shared_memory_name=data.get("shared_memory_name", "industrial_chamber_realtime_v1"),
        shared_memory_size=int(data.get("shared_memory_size", 1024 * 256)),
        command_status_memory_name=data.get("command_status_memory_name", "industrial_chamber_command_status_v1"),
        command_status_memory_size=int(data.get("command_status_memory_size", 1024 * 64)),
        auth_token=auth.get("token", ""),
    )


def copy_example_config(target: Union[str, Path]) -> None:
    source = Path(__file__).with_name("config.example.json")
    Path(target).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
