import asyncio
import json
import math
import random
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field


app = FastAPI(title="Industrial Chamber Platform Test")

ROOT_DIR = Path(__file__).resolve().parents[1]
WEB_INDEX = ROOT_DIR / "web" / "index.html"


class RecipeStep(BaseModel):
    step_no: int
    target_temperature: float
    target_humidity: float
    ramp_seconds: int = Field(default=10, ge=1, le=3600)
    hold_seconds: int = Field(default=20, ge=1, le=86400)


class TestRequest(BaseModel):
    recipe_name: str = "High Low Temperature Cycle"
    operator_id: str = "web-admin"
    steps: list[RecipeStep] = Field(default_factory=lambda: [
        RecipeStep(step_no=1, target_temperature=-20, target_humidity=40, ramp_seconds=8, hold_seconds=10),
        RecipeStep(step_no=2, target_temperature=85, target_humidity=85, ramp_seconds=10, hold_seconds=12),
        RecipeStep(step_no=3, target_temperature=25, target_humidity=50, ramp_seconds=8, hold_seconds=8),
    ])


class StopRequest(BaseModel):
    operator_id: str = "web-admin"
    reason: str = "manual stop from dashboard"


@dataclass
class ChamberRuntime:
    device_id: str
    name: str
    command_queue: asyncio.Queue[dict[str, Any]] = field(default_factory=asyncio.Queue)
    subscriber_queues: set[asyncio.Queue[dict[str, Any]]] = field(default_factory=set)
    state: dict[str, Any] = field(default_factory=dict)
    current_task: Optional[asyncio.Task] = None

    def __post_init__(self) -> None:
        self.state = {
            "device_id": self.device_id,
            "name": self.name,
            "online": True,
            "run_state": "IDLE",
            "current_temperature": round(random.uniform(22, 28), 1),
            "current_humidity": round(random.uniform(42, 55), 1),
            "target_temperature": 25.0,
            "target_humidity": 50.0,
            "current_step": 0,
            "total_steps": 0,
            "alarm": None,
            "last_result": None,
            "updated_at": time.time(),
        }

    async def publish(self, event_type: str, payload: Optional[dict[str, Any]] = None) -> None:
        self.state["updated_at"] = time.time()
        event = {
            "type": event_type,
            "ts": self.state["updated_at"],
            "device_id": self.device_id,
            "state": self.state.copy(),
            "payload": payload or {},
        }
        stale_queues: list[asyncio.Queue[dict[str, Any]]] = []
        for queue in self.subscriber_queues:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                stale_queues.append(queue)
        for queue in stale_queues:
            self.subscriber_queues.discard(queue)

    async def telemetry_loop(self) -> None:
        while True:
            if self.state["run_state"] in {"IDLE", "COMPLETED", "STOPPED"}:
                self.state["current_temperature"] += random.uniform(-0.08, 0.08)
                self.state["current_humidity"] += random.uniform(-0.12, 0.12)
            await self.publish("telemetry")
            await asyncio.sleep(0.5)

    async def command_loop(self) -> None:
        while True:
            command = await self.command_queue.get()
            if command["command_type"] == "START_TEST":
                await self.handle_start(command)
            elif command["command_type"] == "STOP_TEST":
                await self.handle_stop(command)
            else:
                await self.publish("command_rejected", {
                    "command_id": command["command_id"],
                    "reason": f"Unsupported command: {command['command_type']}",
                })

    async def handle_start(self, command: dict[str, Any]) -> None:
        if self.state["run_state"] not in {"IDLE", "COMPLETED", "STOPPED"}:
            await self.publish("command_rejected", {
                "command_id": command["command_id"],
                "reason": f"Device is {self.state['run_state']}",
            })
            return

        steps = command["payload"]["steps"]
        self.state["run_state"] = "WAIT_LOCAL_CONFIRM"
        self.state["last_result"] = f"Request {command['request_id']} accepted, waiting local confirmation"
        await self.publish("command_accepted", {"command_id": command["command_id"]})

        # In the real device this is a Qt local confirmation dialog. Here we auto-confirm.
        await asyncio.sleep(1.0)
        self.current_task = asyncio.create_task(self.run_recipe(command, steps))

    async def handle_stop(self, command: dict[str, Any]) -> None:
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
        self.state["run_state"] = "STOPPED"
        self.state["current_step"] = 0
        self.state["last_result"] = f"Stopped by {command['operator_id']}: {command['reason']}"
        await self.publish("command_result", {
            "command_id": command["command_id"],
            "result": "STOPPED",
        })

    async def run_recipe(self, command: dict[str, Any], steps: list[dict[str, Any]]) -> None:
        self.state["run_state"] = "RUNNING"
        self.state["total_steps"] = len(steps)
        self.state["last_result"] = f"Started {command['payload']['recipe_name']}"
        await self.publish("command_result", {
            "command_id": command["command_id"],
            "result": "STARTED",
        })

        try:
            for step in steps:
                self.state["current_step"] = step["step_no"]
                self.state["target_temperature"] = step["target_temperature"]
                self.state["target_humidity"] = step["target_humidity"]

                await self.ramp_to_target(step["ramp_seconds"])
                await self.hold_target(step["hold_seconds"])

            self.state["run_state"] = "COMPLETED"
            self.state["last_result"] = "Recipe completed successfully"
            await self.publish("test_completed", {"command_id": command["command_id"]})
        except asyncio.CancelledError:
            self.state["run_state"] = "STOPPED"
            await self.publish("test_stopped", {"command_id": command["command_id"]})

    async def ramp_to_target(self, seconds: int) -> None:
        start_temp = self.state["current_temperature"]
        start_hum = self.state["current_humidity"]
        target_temp = self.state["target_temperature"]
        target_hum = self.state["target_humidity"]
        ticks = max(seconds * 2, 1)

        for index in range(ticks):
            ratio = (index + 1) / ticks
            eased = 0.5 - math.cos(ratio * math.pi) / 2
            self.state["current_temperature"] = round(start_temp + (target_temp - start_temp) * eased, 1)
            self.state["current_humidity"] = round(start_hum + (target_hum - start_hum) * eased, 1)
            await self.publish("telemetry")
            await asyncio.sleep(0.5)

    async def hold_target(self, seconds: int) -> None:
        ticks = max(seconds * 2, 1)
        for _ in range(ticks):
            self.state["current_temperature"] = round(self.state["target_temperature"] + random.uniform(-0.3, 0.3), 1)
            self.state["current_humidity"] = round(self.state["target_humidity"] + random.uniform(-0.6, 0.6), 1)
            await self.publish("telemetry")
            await asyncio.sleep(0.5)


devices: dict[str, ChamberRuntime] = {
    "CH-001": ChamberRuntime("CH-001", "温湿度试验箱 1"),
    "CH-002": ChamberRuntime("CH-002", "冷热循环试验箱 2"),
    "CH-003": ChamberRuntime("CH-003", "恒温恒湿试验箱 3"),
}


@app.on_event("startup")
async def startup() -> None:
    for device in devices.values():
        asyncio.create_task(device.telemetry_loop())
        asyncio.create_task(device.command_loop())


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(WEB_INDEX)


@app.get("/api/devices")
async def list_devices() -> list[dict[str, Any]]:
    return [device.state for device in devices.values()]


@app.get("/api/devices/{device_id}")
async def get_device(device_id: str) -> dict[str, Any]:
    return get_runtime(device_id).state


@app.post("/api/devices/{device_id}/test-requests")
async def start_test(device_id: str, request: TestRequest) -> dict[str, Any]:
    device = get_runtime(device_id)
    request_id = f"REQ-{uuid.uuid4().hex[:10].upper()}"
    command = {
        "command_id": f"CMD-{uuid.uuid4().hex[:10].upper()}",
        "request_id": request_id,
        "device_id": device_id,
        "command_type": "START_TEST",
        "operator_id": request.operator_id,
        "created_at": time.time(),
        "payload": json.loads(request.model_dump_json()),
    }
    await device.command_queue.put(command)
    return {
        "request_id": request_id,
        "command_id": command["command_id"],
        "status": "QUEUED",
        "message": "Control request queued for device-side validation",
    }


@app.post("/api/devices/{device_id}/stop-requests")
async def stop_test(device_id: str, request: StopRequest) -> dict[str, Any]:
    device = get_runtime(device_id)
    command = {
        "command_id": f"CMD-{uuid.uuid4().hex[:10].upper()}",
        "request_id": f"REQ-{uuid.uuid4().hex[:10].upper()}",
        "device_id": device_id,
        "command_type": "STOP_TEST",
        "operator_id": request.operator_id,
        "reason": request.reason,
        "created_at": time.time(),
        "payload": request.model_dump(),
    }
    await device.command_queue.put(command)
    return {
        "request_id": command["request_id"],
        "command_id": command["command_id"],
        "status": "QUEUED",
        "message": "Stop request queued",
    }


@app.websocket("/ws/overview")
async def overview_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            await websocket.send_json({
                "type": "overview",
                "devices": [device.state for device in devices.values()],
                "ts": time.time(),
            })
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return


@app.websocket("/ws/devices/{device_id}")
async def device_socket(websocket: WebSocket, device_id: str) -> None:
    device = get_runtime(device_id)
    await websocket.accept()
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=20)
    device.subscriber_queues.add(queue)
    await websocket.send_json({"type": "snapshot", "state": device.state})
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        device.subscriber_queues.discard(queue)


def get_runtime(device_id: str) -> ChamberRuntime:
    try:
        return devices[device_id]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown device: {device_id}") from exc
