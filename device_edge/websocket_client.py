"""Persistent WebSocket connection between one edge agent and the control center."""

from __future__ import annotations

import asyncio
import inspect
import json
import time
import uuid
from typing import Any, Callable, Optional

import websockets

from .config import EdgeConfig
from .shared_memory_store import SharedMemoryNotReady, attach_existing, read_snapshot


CommandHandler = Callable[[dict[str, Any]], dict[str, Any]]


class WebSocketEdgeClient:
    """Upload telemetry and receive commands over one reconnecting connection."""

    def __init__(
        self,
        config: EdgeConfig,
        command_handler: Optional[CommandHandler] = None,
        should_upload: Optional[Callable[[], bool]] = None,
        on_uploaded: Optional[Callable[[dict[str, Any]], None]] = None,
        snapshot_provider: Optional[Callable[[], dict[str, Any]]] = None,
    ) -> None:
        self._config = config
        self._command_handler = command_handler
        self._should_upload = should_upload or (lambda: True)
        self._on_uploaded = on_uploaded
        self._snapshot_provider = snapshot_provider

    def run_forever(self) -> None:
        asyncio.run(self._run_forever())

    async def _run_forever(self) -> None:
        retry_seconds = 1.0
        while True:
            try:
                await self._run_connection()
                retry_seconds = 1.0
            except Exception as exc:
                print(f"edge websocket disconnected: {exc}; retrying in {retry_seconds:.0f}s")
                await asyncio.sleep(retry_seconds)
                retry_seconds = min(retry_seconds * 2, 30.0)

    async def _run_connection(self) -> None:
        headers = {"Authorization": f"Bearer {self._config.auth_token}"} if self._config.auth_token else None
        connect_options: dict[str, Any] = {"ping_interval": 20, "ping_timeout": 20, "close_timeout": 5}
        header_option = "additional_headers" if "additional_headers" in inspect.signature(websockets.connect).parameters else "extra_headers"
        if headers:
            connect_options[header_option] = headers

        print(f"edge websocket connecting: edge_id={self._config.edge_id}, endpoint={self._config.websocket_endpoint}")
        async with websockets.connect(self._config.websocket_endpoint, **connect_options) as websocket:
            await self._send_json(websocket, {
                "type": "register",
                "edge_id": self._config.edge_id,
                "device_ip": self._config.device_ip,
                "agent_version": self._config.agent_version,
            })
            await self._send_telemetry(websocket)
            print(f"edge websocket connected: edge_id={self._config.edge_id}")

            while True:
                try:
                    raw = await asyncio.wait_for(websocket.recv(), timeout=self._config.upload_interval_seconds)
                except asyncio.TimeoutError:
                    await self._send_telemetry(websocket)
                    continue
                await self._handle_server_message(websocket, raw)

    async def _send_telemetry(self, websocket: Any) -> None:
        if not self._should_upload():
            await self._send_json(websocket, {"type": "heartbeat", "edge_id": self._config.edge_id, "reported_at": time.time()})
            return
        try:
            snapshot = self._read_local_snapshot()
        except SharedMemoryNotReady as exc:
            snapshot = {
                "source": "edge_health",
                "written_at": time.time(),
                "devices": [],
                "health": {"status": "degraded", "message": str(exc)},
            }
        await self._send_json(websocket, {
            "type": "telemetry",
            "edge_id": self._config.edge_id,
            "device_ip": self._config.device_ip,
            "agent_version": self._config.agent_version,
            "uploaded_at": time.time(),
            "snapshot": snapshot,
        })
        if self._on_uploaded:
            self._on_uploaded(snapshot)

    def _read_local_snapshot(self) -> dict[str, Any]:
        if self._snapshot_provider:
            return self._snapshot_provider()
        shm = attach_existing(self._config.shared_memory_name)
        try:
            return read_snapshot(shm)
        finally:
            shm.close()

    async def _handle_server_message(self, websocket: Any, raw: str | bytes) -> None:
        message = json.loads(raw)
        if message.get("type") != "command" or not self._command_handler:
            return
        command = message.get("command")
        if not isinstance(command, dict):
            return
        try:
            result = self._command_handler(command)
        except Exception as exc:
            result = {"status": "FAILED", "message": str(exc), "payload": {}}
        await self._send_json(websocket, {
            "type": "command_result",
            "event_id": f"CSE-{uuid.uuid4().hex.upper()}",
            "edge_id": self._config.edge_id,
            "command_id": command.get("command_id", ""),
            "device_id": command.get("device_id", ""),
            "status": result.get("status", "EXECUTED"),
            "message": result.get("message", ""),
            "reported_at": time.time(),
            "payload": result.get("payload", {}),
            "successMessage": result.get("successMessage", command.get("command", "")),
            "time": result.get("time", ""),
        })

    @staticmethod
    async def _send_json(websocket: Any, message: dict[str, Any]) -> None:
        await websocket.send(json.dumps(message, ensure_ascii=False))
