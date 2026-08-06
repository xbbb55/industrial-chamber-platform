"""FastAPI application served by the production device-edge process."""

from __future__ import annotations

import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import EdgeConfig
from .runtime import DeviceEdgeRuntime
from .websocket_client import WebSocketEdgeClient


class LocalCommandRequest(BaseModel):
    command: str
    time: str | None = None
    operator_id: str = "web-admin"
    reason: str = "command from local Vue dashboard"
    payload: dict[str, Any] = Field(default_factory=dict)


def create_app(config: EdgeConfig) -> FastAPI:
    runtime = DeviceEdgeRuntime(config)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await runtime.start()
        if config.control_center_enabled:
            if not config.server_url:
                raise RuntimeError("control_center.server_url is required when control_center.enabled is true")
            client = WebSocketEdgeClient(
                config,
                command_handler=runtime.receive_remote_command,
                snapshot_provider=runtime.upload_snapshot,
            )
            threading.Thread(target=client.run_forever, daemon=True, name="device-edge-control-center").start()
        try:
            yield
        finally:
            await runtime.stop()

    app = FastAPI(title="Industrial Chamber Device Edge", lifespan=lifespan)
    app.state.runtime = runtime
    dist_dir = Path(__file__).resolve().parents[1] / "frontend-vue" / "dist"

    @app.get("/api/memory/snapshot")
    async def memory_snapshot() -> dict[str, Any]:
        try:
            return runtime.snapshot()
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/api/memory/devices")
    async def memory_devices() -> list[dict[str, Any]]:
        return (await memory_snapshot()).get("devices", [])

    @app.get("/api/status")
    async def status() -> dict[str, Any]:
        return runtime.health()

    @app.post("/api/devices/{device_id}/commands")
    async def submit_command(device_id: str, request: LocalCommandRequest) -> dict[str, Any]:
        try:
            command = runtime.submit_command({**request.model_dump(), "device_id": device_id})
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except (RuntimeError, ValueError) as exc:
            raise HTTPException(status_code=409 if isinstance(exc, RuntimeError) else 400, detail=str(exc)) from exc
        return {
            "status": "QUEUED",
            "command_id": command["command_id"],
            "device_id": command["device_id"],
            "command": command["command"],
            "time": command["time"],
        }

    @app.websocket("/ws/memory")
    async def memory_socket(websocket: WebSocket) -> None:
        await websocket.accept()
        queue = runtime.subscribe()
        try:
            try:
                await websocket.send_json({"type": "snapshot", "snapshot": runtime.snapshot()})
            except RuntimeError as exc:
                await websocket.send_json({"type": "memory_not_ready", "detail": str(exc)})
            while True:
                await websocket.send_json(await queue.get())
        except WebSocketDisconnect:
            return
        finally:
            runtime.unsubscribe(queue)

    if dist_dir.is_dir():
        @app.get("/")
        async def index() -> FileResponse:
            return FileResponse(dist_dir / "index.html")

        app.mount("/", StaticFiles(directory=dist_dir, html=True), name="web")
    else:
        @app.get("/")
        async def index() -> dict[str, str]:
            return {"message": "device_edge is running; build frontend-vue to serve the local web UI."}

    return app
