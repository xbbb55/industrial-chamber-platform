"""Production runtime for one local device-edge process."""

from __future__ import annotations

import asyncio
import threading
import time
import uuid
from contextlib import suppress
from multiprocessing import shared_memory
from typing import Any

from .config import EdgeConfig
from .control_protocol import normalize_command, protocol_time
from .shared_memory_store import SharedMemoryNotReady, attach_existing, create_or_attach, read_snapshot_with_version, write_snapshot
from .snapshot_normalizer import normalize_snapshot
from .sqlite_store import SqliteStore


TERMINAL_COMMAND_STATES = {"EXECUTED", "SUCCESS", "SUCCEEDED", "COMPLETED", "FAILED", "ERROR", "REJECTED", "TIMEOUT"}


class DeviceEdgeRuntime:
    def __init__(self, config: EdgeConfig) -> None:
        self.config = config
        self._lock = threading.RLock()
        self._realtime_memory: shared_memory.SharedMemory | None = None
        self._status_memory: shared_memory.SharedMemory | None = None
        self._request_memory: shared_memory.SharedMemory | None = None
        self._store: SqliteStore | None = None
        self._latest_snapshot: dict[str, Any] | None = None
        self._latest_realtime_version: int | None = None
        self._latest_status_version: int | None = None
        self._last_realtime_error: str | None = None
        self._last_status_error: str | None = None
        self._pending_command: dict[str, Any] | None = None
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._tasks: list[asyncio.Task[None]] = []
        self._loop: asyncio.AbstractEventLoop | None = None

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._request_memory = create_or_attach(
            self.config.command_request_memory_name,
            self.config.command_request_memory_size,
        )
        self._store = SqliteStore(self.config.sqlite_path)
        self._tasks = [
            asyncio.create_task(self._realtime_loop(), name="device-edge-realtime"),
            asyncio.create_task(self._command_status_loop(), name="device-edge-command-status"),
        ]

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            with suppress(asyncio.CancelledError):
                await task
        self._tasks.clear()
        for memory in (self._realtime_memory, self._status_memory, self._request_memory):
            if memory is not None:
                memory.close()
        self._realtime_memory = self._status_memory = self._request_memory = None
        if self._store is not None:
            self._store.close()
            self._store = None

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            if self._latest_snapshot is None:
                raise SharedMemoryNotReady(self._last_realtime_error or "Realtime shared memory is not ready.")
            return self._latest_snapshot

    def upload_snapshot(self) -> dict[str, Any]:
        with self._lock:
            if self._latest_snapshot is not None:
                return self._latest_snapshot
        return {
            "source": "device_edge_health",
            "written_at": time.time(),
            "devices": [],
            "health": {"status": "degraded", "message": self._last_realtime_error or "Realtime data is unavailable."},
        }

    def health(self) -> dict[str, Any]:
        with self._lock:
            return {
                "edge_id": self.config.edge_id,
                "realtime_memory_name": self.config.shared_memory_name,
                "command_request_memory_name": self.config.command_request_memory_name,
                "command_status_memory_name": self.config.command_status_memory_name,
                "realtime_memory_version": self._latest_realtime_version,
                "command_status_memory_version": self._latest_status_version,
                "realtime_error": self._last_realtime_error,
                "command_status_error": self._last_status_error,
                "pending_command": self._pending_command,
                "control_center_enabled": self.config.control_center_enabled,
            }

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=20)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self._subscribers.discard(queue)

    def submit_command(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            if self._request_memory is None:
                raise RuntimeError("Command request memory is not initialized.")
            operator_id = str(payload.get("operator_id") or "").strip()
            if not operator_id or (self.config.allowed_operator_ids and operator_id not in self.config.allowed_operator_ids):
                raise PermissionError("Operator is not authorized for local device commands.")
            wire_command, command_type = normalize_command(payload.get("command"))
            if command_type == "UNKNOWN":
                raise ValueError(f"Unsupported FE_W command: {payload.get('command')}")
            device_id = str(payload.get("device_id") or "").strip()
            if not device_id:
                raise ValueError("device_id is required")
            command = {
                "command_id": str(payload.get("command_id") or f"CMD-{uuid.uuid4().hex[:12].upper()}"),
                "device_id": device_id,
                "command": wire_command,
                "command_type": command_type,
                "time": str(payload.get("time") or protocol_time()),
                "operator_id": operator_id,
                "reason": str(payload.get("reason") or ""),
                "payload": payload.get("payload") if isinstance(payload.get("payload"), dict) else {},
                "status": "PENDING",
            }
            # FE_W follows the controller's existing, minimal wire contract.
            # C++ consumes and clears this mailbox before executing the command.
            write_snapshot(
                self._request_memory,
                {"command": wire_command, "time": command["time"]},
                self.config.command_request_memory_size,
            )
            self._pending_command = command
            if self._store is not None:
                self._store.create_command(command)
        self._publish_threadsafe({"type": "command_status", **command})
        return command

    def receive_remote_command(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Entry point used by the control-center WebSocket client thread."""
        return self.submit_command(payload)

    async def _realtime_loop(self) -> None:
        while True:
            self._poll_realtime()
            await asyncio.sleep(max(self.config.realtime_poll_interval_seconds, 0.05))

    async def _command_status_loop(self) -> None:
        while True:
            self._poll_command_status()
            with self._lock:
                interval = self.config.command_status_active_poll_interval_seconds if self._pending_command else self.config.command_status_idle_poll_interval_seconds
            await asyncio.sleep(max(interval, 0.05))

    def _poll_realtime(self) -> None:
        try:
            if self._realtime_memory is None:
                self._realtime_memory = attach_existing(self.config.shared_memory_name)
            version, raw_snapshot = read_snapshot_with_version(self._realtime_memory)
            with self._lock:
                if version == self._latest_realtime_version:
                    return
            snapshot = normalize_snapshot(raw_snapshot)
            snapshot["memory_version"] = version
            with self._lock:
                self._latest_realtime_version = version
                self._latest_snapshot = snapshot
                self._last_realtime_error = None
            if self._store is not None:
                self._store.record_snapshot(version, snapshot)
            self._publish_threadsafe({"type": "snapshot", "snapshot": snapshot, "router_read_at": time.time()})
        except Exception as exc:
            with self._lock:
                self._last_realtime_error = str(exc)
            self._publish_threadsafe({"type": "memory_not_ready", "detail": str(exc)})
            self._close_memory("_realtime_memory")

    def _poll_command_status(self) -> None:
        try:
            if self._status_memory is None:
                self._status_memory = attach_existing(self.config.command_status_memory_name)
            version, result = read_snapshot_with_version(self._status_memory)
            with self._lock:
                if version == self._latest_status_version:
                    return
                self._latest_status_version = version
                self._last_status_error = None
            self._handle_command_result(result, version)
        except Exception as exc:
            with self._lock:
                self._last_status_error = str(exc)
            self._close_memory("_status_memory")

    def _handle_command_result(self, result: dict[str, Any], version: int) -> None:
        with self._lock:
            pending = self._pending_command
            status = str(result.get("status") or "EXECUTED").upper()
            reported_command = str(result.get("successMessage") or result.get("command") or "")
            matches_pending = pending is not None and reported_command == pending["command"]
            command_id = str(result.get("command_id") or (pending or {}).get("command_id") if matches_pending else result.get("command_id") or "")
            event = {
                "event_id": str(result.get("event_id") or f"BER-{version}"),
                "memory_version": version,
                "command_id": command_id,
                "device_id": str(result.get("device_id") or (pending or {}).get("device_id") or ""),
                "status": status,
                "message": str(result.get("message") or reported_command),
                "successMessage": reported_command,
                "time": str(result.get("time") or protocol_time()),
                "payload": result.get("payload") if isinstance(result.get("payload"), dict) else {},
            }
            if matches_pending and status in TERMINAL_COMMAND_STATES:
                self._pending_command = None
            elif matches_pending and status in {"RECEIVED", "ACCEPTED", "EXECUTING"}:
                pending["status"] = status
            if command_id and self._store is not None:
                self._store.update_command(command_id, status, event)
        self._publish_threadsafe({"type": "command_status", **event})

    def _close_memory(self, attribute: str) -> None:
        memory = getattr(self, attribute)
        if memory is not None:
            memory.close()
            setattr(self, attribute, None)

    def _publish_threadsafe(self, message: dict[str, Any]) -> None:
        loop = self._loop
        if loop is None or loop.is_closed():
            return
        asyncio.run_coroutine_threadsafe(self._broadcast(message), loop)

    async def _broadcast(self, message: dict[str, Any]) -> None:
        for queue in tuple(self._subscribers):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                with suppress(asyncio.QueueEmpty):
                    queue.get_nowait()
                with suppress(asyncio.QueueFull):
                    queue.put_nowait(message)
