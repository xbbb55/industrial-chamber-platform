import json
import time
import urllib.request
from typing import Any, Callable, Optional

from .config import EdgeConfig
from .shared_memory_store import SharedMemoryNotReady, attach_existing, read_snapshot


class SnapshotUploader:
    def __init__(
        self,
        config: EdgeConfig,
        should_upload: Optional[Callable[[], bool]] = None,
        on_uploaded: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> None:
        self._config = config
        self._should_upload = should_upload or (lambda: True)
        self._on_uploaded = on_uploaded

    def run_forever(self) -> None:
        print(f"uploader started: edge_id={self._config.edge_id}, endpoint={self._config.ingest_endpoint}")
        while True:
            try:
                if not self._should_upload():
                    time.sleep(self._config.upload_interval_seconds)
                    continue
                snapshot = self._read_local_snapshot()
                result = self._post_snapshot(snapshot)
                if self._on_uploaded:
                    self._on_uploaded(snapshot)
                print(
                    "uploaded "
                    f"edge_id={self._config.edge_id} "
                    f"sequence={result.get('sequence')} "
                    f"devices={result.get('device_count')}"
                )
            except SharedMemoryNotReady as exc:
                print(f"shared memory not ready: {exc}")
            except Exception as exc:
                print(f"uploader loop failed: {exc}")
            time.sleep(self._config.upload_interval_seconds)

    def _read_local_snapshot(self) -> dict[str, Any]:
        shm = attach_existing(self._config.shared_memory_name)
        try:
            return read_snapshot(shm)
        finally:
            shm.close()

    def _post_snapshot(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "edge_id": self._config.edge_id,
            "device_ip": self._config.device_ip,
            "agent_version": self._config.agent_version,
            "uploaded_at": time.time(),
            "snapshot": snapshot,
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json; charset=utf-8"}
        if self._config.auth_token:
            headers["Authorization"] = f"Bearer {self._config.auth_token}"

        request = urllib.request.Request(
            self._config.ingest_endpoint,
            data=data,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
