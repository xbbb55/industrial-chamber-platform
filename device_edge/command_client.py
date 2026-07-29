import json
import time
import urllib.parse
import urllib.request
from typing import Any, Callable

from .config import EdgeConfig
from .control_protocol import build_be_r


CommandHandler = Callable[[dict[str, Any]], dict[str, Any]]


class CommandClient:
    def __init__(self, config: EdgeConfig, handler: CommandHandler) -> None:
        self._config = config
        self._handler = handler

    def run_forever(self) -> None:
        print(f"command client started: edge_id={self._config.edge_id}")
        while True:
            try:
                commands = self._fetch_pending_commands()
                for command in commands:
                    print(
                        "received command "
                        f"command={command.get('command')} "
                        f"device_id={command.get('device_id')}"
                    )
                    result = self._handler(command)
                    self._post_result(command, result)
            except Exception as exc:
                print(f"command client failed: {exc}")
            time.sleep(self._config.stream_interval_seconds)

    def _fetch_pending_commands(self) -> list[dict[str, Any]]:
        query = urllib.parse.urlencode({"edge_id": self._config.edge_id})
        url = self._config.server_url.rstrip("/") + f"/api/device-commands/fe-w?{query}"
        request = urllib.request.Request(url, headers=self._headers(), method="GET")
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return list(payload.get("commands", []))

    def _post_result(self, command: dict[str, Any], result: dict[str, Any]) -> None:
        query = urllib.parse.urlencode({"edge_id": self._config.edge_id})
        url = self._config.server_url.rstrip("/") + f"/api/device-commands/be-r?{query}"
        payload = build_be_r(
            result.get("successMessage") or command.get("command", ""),
            result.get("time"),
        )
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers={**self._headers(), "Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            response.read()

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self._config.auth_token:
            headers["Authorization"] = f"Bearer {self._config.auth_token}"
        return headers
