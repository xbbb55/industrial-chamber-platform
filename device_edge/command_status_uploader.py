"""Upload command-execution records written by the local controller process."""

from __future__ import annotations

import json
import time
import urllib.request
from typing import Any

from .config import EdgeConfig
from .shared_memory_store import SharedMemoryNotReady, attach_existing, read_snapshot


class CommandStatusUploader:
    """Forward each unseen command-status event to the central service once."""

    def __init__(self, config: EdgeConfig) -> None:
        self._config = config
        self._uploaded_event_ids: set[str] = set()

    def run_forever(self) -> None:
        print(
            "command status uploader started: "
            f"edge_id={self._config.edge_id}, endpoint={self._config.command_status_endpoint}"
        )
        while True:
            try:
                for event in self._read_pending_events():
                    self._post_event(event)
                    self._uploaded_event_ids.add(str(event["event_id"]))
                    print(
                        "command status uploaded "
                        f"command_id={event.get('command_id')} "
                        f"status={event.get('status')}"
                    )
            except SharedMemoryNotReady:
                pass
            except Exception as exc:
                print(f"command status uploader failed: {exc}")
            time.sleep(self._config.stream_interval_seconds)

    def _read_pending_events(self) -> list[dict[str, Any]]:
        shm = attach_existing(self._config.command_status_memory_name)
        try:
            status_memory = read_snapshot(shm)
        finally:
            shm.close()

        events = status_memory.get("events") or []
        return [
            event
            for event in events
            if isinstance(event, dict)
            and event.get("event_id")
            and str(event["event_id"]) not in self._uploaded_event_ids
        ]

    def _post_event(self, event: dict[str, Any]) -> None:
        payload = {
            "event_id": event["event_id"],
            "edge_id": self._config.edge_id,
            "command_id": event.get("command_id", ""),
            "device_id": event.get("device_id", ""),
            "status": event.get("status", "EXECUTED"),
            "message": event.get("message", ""),
            "reported_at": event.get("completed_at", time.time()),
            "payload": event.get("payload", {}),
            "successMessage": event.get("success_message", event.get("command", "")),
            "time": event.get("completed_time", ""),
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json; charset=utf-8"}
        if self._config.auth_token:
            headers["Authorization"] = f"Bearer {self._config.auth_token}"
        request = urllib.request.Request(
            self._config.command_status_endpoint,
            data=data,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            response.read()
