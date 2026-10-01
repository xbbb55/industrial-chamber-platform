"""FastAPI application served by the production device-edge process."""

from __future__ import annotations

import os
import sys
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, create_model, model_validator

from .config import EdgeConfig
from .mysql_store import HISTORY_RETENTION_OPTIONS, PID_SETTING_COLUMNS, EnvironmentalHistoryStore, FixedValueStore, OperationSettingStore, ProgramStore, setting_changes
from .runtime import DeviceEdgeRuntime
from .websocket_client import WebSocketEdgeClient
from backend.auth import (
    PERMISSION_DEVICE_COMMAND,
    PERMISSION_DEVICE_VIEW,
    PERMISSION_SETTINGS_WRITE,
    account_for_token,
    build_auth_router,
    build_operation_log_router,
    has_permission,
    record_operation,
    require_permission,
)


class LocalCommandRequest(BaseModel):
    command: str
    time: str | None = None
    reason: str = "command from local Vue dashboard"
    payload: dict[str, Any] = Field(default_factory=dict)


class FixedValueRequest(BaseModel):
    temperature_target: float
    temperature_slope: float
    humidity_target: float
    humidity_slope: float
    runtime_hours: int = Field(ge=0, le=65535)
    runtime_minutes: int = Field(ge=0, le=59)
    runtime_seconds: int = Field(ge=0, le=59)


class OperationSettingRequest(BaseModel):
    airTEMP_H: float
    airTEMP_L: float
    dutTEMP_H: float
    dutTEMP_L: float
    dutModeAir_H: float
    dutModeAir_L: float
    dutControl: int = Field(ge=0, le=1)
    dutSel: int = Field(ge=0, le=7)
    DM9: float | None = None
    waitTEMP: float
    waitHUMI: float
    event: int = Field(ge=0, le=65535)
    powerRestoration: int = Field(ge=0, le=2)
    afterShutdow: int = Field(ge=0, le=1)


class OtherSettingRequest(BaseModel):
    dutControl: int = Field(ge=0, le=1)
    dutSel: int = Field(ge=0, le=7)
    DM9: float | None = None
    waitTEMP: float
    waitHUMI: float
    event: int = Field(ge=0, le=65535)
    powerRestoration: int = Field(ge=0, le=2)
    afterShutdow: int = Field(ge=0, le=1)
    history_retention_days: int = Field(default=90)


class HistoryRetentionRequest(BaseModel):
    retention_days: int = Field(default=90)


class SystemBasicSettingRequest(BaseModel):
    TEMP_OP_H: float
    TEMP_OP_L: float
    HUMI_OP_H: float
    HUMI_OP_L: float
    HUMI_AirOP_H: float
    HUMI_AirOP_L: float
    heatingUpDownHz: float
    constantTEMPHz: float
    HumiHeatHz: float
    otherHz: float


class CorrectionSettingRequest(BaseModel):
    TEMP_Area1: float
    TEMP_Area2: float
    TEMP_Area3: float
    TEMP_Area4: float
    TEMP_Corrected1: float
    TEMP_Corrected2: float
    TEMP_Corrected3: float
    TEMP_Corrected4: float
    TEMP_Correction: float
    HUMI_Area1: float
    HUMI_Area2: float
    HUMI_Area3: float
    HUMI_Area4: float
    HUMI_Corrected1: float
    HUMI_Corrected2: float
    HUMI_Corrected3: float
    HUMI_Corrected4: float
    HUMI_Correction: float
    DUT1_Collected: float
    DUT1_Corrected: float
    DUT1_Final: float
    DUT2_Collected: float
    DUT2_Corrected: float
    DUT2_Final: float
    DUT3_Collected: float
    DUT3_Corrected: float
    DUT3_Final: float
    DUT4_Collected: float
    DUT4_Corrected: float
    DUT4_Final: float
    DUT5_Collected: float
    DUT5_Corrected: float
    DUT5_Final: float
    DUT6_Collected: float
    DUT6_Corrected: float
    DUT6_Final: float
    DUT7_Collected: float
    DUT7_Corrected: float
    DUT7_Final: float
    DUT8_Collected: float
    DUT8_Corrected: float
    DUT8_Final: float
    DUT9_Collected: float
    DUT9_Corrected: float
    DUT9_Final: float
    DUT10_Collected: float
    DUT10_Corrected: float
    DUT10_Final: float
    TEMP_Collected: float
    TEMP_Corrected: float
    TEMP_Final: float
    HUMI_Collected: float
    HUMI_Corrected: float
    HUMI_Final: float


PidSettingRequest = create_model(
    "PidSettingRequest",
    **{column: (float, ...) for column in PID_SETTING_COLUMNS},
)


class ProgramStepRequest(BaseModel):
    step_no: str | None = Field(default=None, max_length=16)
    time: float = Field(ge=0)
    temp: float
    humi: float
    pressure: float
    event_bits: int = Field(ge=0, le=65535)
    space: float = 0


class ProgramGroupRequest(BaseModel):
    pro_no: int | None = Field(default=None, ge=1, le=65535)
    name: str = Field(min_length=1, max_length=128)
    total_time: float | None = Field(default=None, ge=0)
    loop1_start: int | None = Field(default=None, ge=0)
    loop1_end: int | None = Field(default=None, ge=0)
    loop1_times: int | None = Field(default=None, ge=0)
    loop2_start: int | None = Field(default=None, ge=0)
    loop2_end: int | None = Field(default=None, ge=0)
    loop2_times: int | None = Field(default=None, ge=0)
    loop3_start: int | None = Field(default=None, ge=0)
    loop3_end: int | None = Field(default=None, ge=0)
    loop3_times: int | None = Field(default=None, ge=0)
    loop4_start: int | None = Field(default=None, ge=0)
    loop4_end: int | None = Field(default=None, ge=0)
    loop4_times: int | None = Field(default=None, ge=0)
    full_cycle: int | None = Field(default=None, ge=0)
    link_no: int | None = Field(default=None, ge=0)
    steps: list[ProgramStepRequest] = Field(min_length=1)

    @model_validator(mode="after")
    def assign_step_numbers(self) -> "ProgramGroupRequest":
        for index, step in enumerate(self.steps, start=1):
            step.step_no = str(index)
        return self


def create_app(config: EdgeConfig) -> FastAPI:
    runtime = DeviceEdgeRuntime(config)
    fixed_value_store = FixedValueStore(config) if config.database_enabled else None
    operation_setting_store = OperationSettingStore(config) if config.database_enabled else None
    program_store = ProgramStore(config) if config.database_enabled else None
    history_store = EnvironmentalHistoryStore(config) if config.database_enabled else None

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await runtime.start()
        if history_store is not None:
            try:
                history_store.ensure_tables()
            except Exception:
                # Database availability must not prevent the realtime service from starting.
                pass
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
    app.include_router(build_auth_router())
    app.include_router(build_operation_log_router())
    app.state.runtime = runtime
    # In a PyInstaller build the Vue assets live under ``_MEIPASS``.  Keep
    # the source-tree path for development and allow an explicit override for
    # diagnostics or custom deployments.
    configured_web_root = os.environ.get("DEVICE_EDGE_WEB_ROOT", "").strip()
    if configured_web_root:
        dist_dir = Path(configured_web_root).resolve()
    elif getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        dist_dir = Path(sys._MEIPASS) / "frontend-vue" / "dist"
    else:
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

    @app.get("/api/settings/fixed-value")
    async def get_fixed_value(_: dict[str, Any] = Depends(require_permission(PERMISSION_DEVICE_VIEW))) -> dict[str, Any]:
        if fixed_value_store is None:
            raise HTTPException(status_code=503, detail="数据库存储未启用")
        try:
            return {"value": fixed_value_store.get_fixed_value()}
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.put("/api/settings/fixed-value")
    async def save_fixed_value(request: FixedValueRequest, account: dict[str, Any] = Depends(require_permission(PERMISSION_SETTINGS_WRITE)), notify_memory: bool = Query(default=True)) -> dict[str, Any]:
        if fixed_value_store is None:
            raise HTTPException(status_code=503, detail="数据库存储未启用")
        try:
            previous_value = fixed_value_store.get_fixed_value()
            value = fixed_value_store.save_fixed_value(request.model_dump())
            command = None
            if notify_memory:
                # Publish only after commit and read-back confirmation so HDNet
                # never receives a notification for an uncommitted value.
                try:
                    command = runtime.submit_command({
                        "command": "fixed_value",
                        "device_id": config.edge_id,
                        "operator_id": account["username"],
                        "reason": "fixed value settings saved",
                    })
                except (RuntimeError, ValueError) as exc:
                    raise HTTPException(status_code=503, detail=f"数据库已保存，但内存通知失败：{exc}") from exc
            record_operation(account, "FIXED_VALUE_SETTINGS_UPDATED", target_type="settings", target_id="fixed-value", details={"changes": setting_changes(previous_value, value)})
            return {"value": value, "command": command}
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/api/settings/operation")
    async def get_operation_setting(_: dict[str, Any] = Depends(require_permission(PERMISSION_DEVICE_VIEW))) -> dict[str, Any]:
        if operation_setting_store is None:
            raise HTTPException(status_code=503, detail="数据库存储未启用")
        try:
            return {"value": operation_setting_store.get_operation_setting()}
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.put("/api/settings/operation")
    async def save_operation_setting(request: OperationSettingRequest, account: dict[str, Any] = Depends(require_permission(PERMISSION_SETTINGS_WRITE)), notify_memory: bool = Query(default=True)) -> dict[str, Any]:
        if operation_setting_store is None:
            raise HTTPException(status_code=503, detail="数据库存储未启用")
        try:
            previous_value = operation_setting_store.get_operation_setting()
            value = operation_setting_store.save_operation_setting(request.model_dump())
            command = None
            if notify_memory:
                # Only publish to FE_W after the database transaction has been
                # committed and the saved row has been read back successfully.
                try:
                    command = runtime.submit_command({
                        "command": "operation_setting",
                        "device_id": config.edge_id,
                        "operator_id": account["username"],
                        "reason": "operation settings saved",
                    })
                except (RuntimeError, ValueError) as exc:
                    raise HTTPException(status_code=503, detail=f"数据库已保存，但内存通知失败：{exc}") from exc
            record_operation(account, "OPERATION_SETTINGS_UPDATED", target_type="settings", target_id="operation", details={"changes": setting_changes(previous_value, value)})
            return {"value": value, "command": command}
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.put("/api/settings/operation/other")
    async def save_other_setting(request: OtherSettingRequest, account: dict[str, Any] = Depends(require_permission(PERMISSION_SETTINGS_WRITE)), notify_memory: bool = Query(default=True)) -> dict[str, Any]:
        if operation_setting_store is None:
            raise HTTPException(status_code=503, detail="数据库存储未启用")
        try:
            previous_value = operation_setting_store.get_other_setting()
            if history_store is not None:
                previous_value = {**(previous_value or {}), "history_retention_days": history_store.get_retention_days()}
            value = operation_setting_store.save_other_setting(request.model_dump(exclude={"history_retention_days"}))
            if history_store is not None:
                value["history_retention_days"] = history_store.save_retention_days(request.history_retention_days)
            command = None
            if notify_memory:
                try:
                    command = runtime.submit_command({
                        "command": "operation_setting",
                        "device_id": config.edge_id,
                        "operator_id": account["username"],
                        "reason": "other operation settings saved",
                    })
                except (RuntimeError, ValueError) as exc:
                    raise HTTPException(status_code=503, detail=f"数据库已保存，但内存通知失败：{exc}") from exc
            record_operation(account, "OTHER_OPERATION_SETTINGS_UPDATED", target_type="settings", target_id="operation-other", details={"changes": setting_changes(previous_value, value)})
            return {"value": value, "command": command}
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/api/settings/history-retention")
    async def get_history_retention(_: dict[str, Any] = Depends(require_permission(PERMISSION_DEVICE_VIEW))) -> dict[str, Any]:
        if history_store is None:
            raise HTTPException(status_code=503, detail="数据库存储未启用")
        try:
            return {"retention_days": history_store.get_retention_days(), "options": list(HISTORY_RETENTION_OPTIONS)}
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.put("/api/settings/history-retention")
    async def save_history_retention(request: HistoryRetentionRequest, account: dict[str, Any] = Depends(require_permission(PERMISSION_SETTINGS_WRITE))) -> dict[str, Any]:
        if history_store is None:
            raise HTTPException(status_code=503, detail="数据库存储未启用")
        try:
            previous = history_store.get_retention_days()
            value = history_store.save_retention_days(request.retention_days)
            record_operation(account, "HISTORY_RETENTION_UPDATED", target_type="settings", target_id="environmental-history", details={"before": previous, "after": value})
            return {"retention_days": value, "options": list(HISTORY_RETENTION_OPTIONS)}
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/api/environmental-history")
    async def get_environmental_history(
        device_id: str,
        start_time: float | None = None,
        end_time: float | None = None,
        run_state: str | None = None,
        limit: int = Query(default=5000, ge=1, le=20000),
        _: dict[str, Any] = Depends(require_permission(PERMISSION_DEVICE_VIEW)),
    ) -> dict[str, Any]:
        if history_store is None:
            raise HTTPException(status_code=503, detail="数据库存储未启用")
        try:
            return {"device_id": device_id, "items": history_store.list_history(device_id, start_time, end_time, run_state, limit)}
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/api/settings/system-basic")
    async def get_system_basic_setting(_: dict[str, Any] = Depends(require_permission(PERMISSION_DEVICE_VIEW))) -> dict[str, Any]:
        if operation_setting_store is None:
            raise HTTPException(status_code=503, detail="数据库存储未启用")
        try:
            return {"value": operation_setting_store.get_system_basic_setting()}
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.put("/api/settings/system-basic")
    async def save_system_basic_setting(request: SystemBasicSettingRequest, account: dict[str, Any] = Depends(require_permission(PERMISSION_SETTINGS_WRITE)), notify_memory: bool = Query(default=True)) -> dict[str, Any]:
        if operation_setting_store is None:
            raise HTTPException(status_code=503, detail="数据库存储未启用")
        try:
            previous_value = operation_setting_store.get_system_basic_setting()
            value = operation_setting_store.save_system_basic_setting(request.model_dump())
            command = None
            if notify_memory:
                try:
                    command = runtime.submit_command({
                        "command": "operation_setting",
                        "device_id": config.edge_id,
                        "operator_id": account["username"],
                        "reason": "system basic settings saved",
                    })
                except (RuntimeError, ValueError) as exc:
                    raise HTTPException(status_code=503, detail=f"数据库已保存，但内存通知失败：{exc}") from exc
            record_operation(account, "SYSTEM_BASIC_SETTINGS_UPDATED", target_type="settings", target_id="system-basic", details={"changes": setting_changes(previous_value, value)})
            return {"value": value, "command": command}
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/api/settings/correction")
    async def get_correction_setting(_: dict[str, Any] = Depends(require_permission(PERMISSION_DEVICE_VIEW))) -> dict[str, Any]:
        if operation_setting_store is None:
            raise HTTPException(status_code=503, detail="数据库存储未启用")
        try:
            return {"value": operation_setting_store.get_correction_setting()}
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.put("/api/settings/correction")
    async def save_correction_setting(request: CorrectionSettingRequest, account: dict[str, Any] = Depends(require_permission(PERMISSION_SETTINGS_WRITE)), notify_memory: bool = Query(default=True)) -> dict[str, Any]:
        if operation_setting_store is None:
            raise HTTPException(status_code=503, detail="数据库存储未启用")
        try:
            previous_value = operation_setting_store.get_correction_setting()
            value = operation_setting_store.save_correction_setting(request.model_dump())
            command = None
            if notify_memory:
                try:
                    command = runtime.submit_command({
                        "command": "correction",
                        "device_id": config.edge_id,
                        "operator_id": account["username"],
                        "reason": "measurement correction settings saved",
                    })
                except (RuntimeError, ValueError) as exc:
                    raise HTTPException(status_code=503, detail=f"数据库已保存，但内存通知失败：{exc}") from exc
            record_operation(account, "CORRECTION_SETTINGS_UPDATED", target_type="settings", target_id="correction", details={"changes": setting_changes(previous_value, value)})
            return {"value": value, "command": command}
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/api/settings/pid")
    async def get_pid_setting(_: dict[str, Any] = Depends(require_permission(PERMISSION_DEVICE_VIEW))) -> dict[str, Any]:
        if operation_setting_store is None:
            raise HTTPException(status_code=503, detail="数据库存储未启用")
        try:
            return {"value": operation_setting_store.get_pid_setting()}
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.put("/api/settings/pid")
    async def save_pid_setting(request: PidSettingRequest, account: dict[str, Any] = Depends(require_permission(PERMISSION_SETTINGS_WRITE)), notify_memory: bool = Query(default=True)) -> dict[str, Any]:
        if operation_setting_store is None:
            raise HTTPException(status_code=503, detail="数据库存储未启用")
        try:
            previous_value = operation_setting_store.get_pid_setting()
            value = operation_setting_store.save_pid_setting(request.model_dump())
            command = None
            if notify_memory:
                try:
                    command = runtime.submit_command({
                        "command": "pid_set",
                        "device_id": config.edge_id,
                        "operator_id": account["username"],
                        "reason": "PID settings saved",
                    })
                except (RuntimeError, ValueError) as exc:
                    raise HTTPException(status_code=503, detail=f"数据库已保存，但内存通知失败：{exc}") from exc
            record_operation(account, "PID_SETTINGS_UPDATED", target_type="settings", target_id="pid", details={"changes": setting_changes(previous_value, value)})
            return {"value": value, "command": command}
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/api/programs")
    async def list_programs(_: dict[str, Any] = Depends(require_permission(PERMISSION_DEVICE_VIEW))) -> dict[str, Any]:
        if program_store is None:
            raise HTTPException(status_code=503, detail="数据库存储未启用")
        try:
            return {"programs": program_store.list_program_groups()}
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/api/programs/{pro_no}")
    async def get_program(pro_no: int, _: dict[str, Any] = Depends(require_permission(PERMISSION_DEVICE_VIEW))) -> dict[str, Any]:
        if program_store is None:
            raise HTTPException(status_code=503, detail="数据库存储未启用")
        try:
            value = program_store.get_program(pro_no)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        if value is None:
            raise HTTPException(status_code=404, detail="程序组不存在")
        return {"program": value}

    @app.post("/api/programs", status_code=201)
    async def create_program(request: ProgramGroupRequest, account: dict[str, Any] = Depends(require_permission(PERMISSION_SETTINGS_WRITE))) -> dict[str, Any]:
        if program_store is not None:
            request.pro_no = program_store.next_program_number()
        return await _save_program(request, account, creating=True)

    @app.put("/api/programs/{pro_no}")
    async def update_program(pro_no: int, request: ProgramGroupRequest, account: dict[str, Any] = Depends(require_permission(PERMISSION_SETTINGS_WRITE))) -> dict[str, Any]:
        if request.pro_no is not None and request.pro_no != pro_no:
            raise HTTPException(status_code=422, detail="路径中的程序组号与请求体不一致")
        request.pro_no = pro_no
        return await _save_program(request, account, creating=False)

    async def _save_program(request: ProgramGroupRequest, account: dict[str, Any], *, creating: bool) -> dict[str, Any]:
        if program_store is None:
            raise HTTPException(status_code=503, detail="数据库存储未启用")
        try:
            if creating and program_store.get_program(request.pro_no) is not None:
                raise HTTPException(status_code=409, detail="程序组号已存在")
            value = program_store.save_program(request.model_dump())
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        record_operation(account, "PROGRAM_CREATED" if creating else "PROGRAM_UPDATED", target_type="program", target_id=str(request.pro_no), details={"step_count": len(request.steps)})
        return {"program": value}

    @app.delete("/api/programs/{pro_no}")
    async def delete_program(pro_no: int, account: dict[str, Any] = Depends(require_permission(PERMISSION_SETTINGS_WRITE))) -> dict[str, str]:
        if program_store is None:
            raise HTTPException(status_code=503, detail="数据库存储未启用")
        try:
            program_store.delete_program(pro_no)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        record_operation(account, "PROGRAM_DELETED", target_type="program", target_id=str(pro_no))
        return {"message": "程序已删除"}

    @app.post("/api/devices/{device_id}/commands")
    async def submit_command(device_id: str, request: LocalCommandRequest, account: dict[str, Any] = Depends(require_permission(PERMISSION_DEVICE_COMMAND))) -> dict[str, Any]:
        try:
            record_operation(account, "DEVICE_COMMAND_REQUESTED", target_type="device", target_id=device_id, details={"command": request.command})
            command = runtime.submit_command({**request.model_dump(), "operator_id": account["username"], "device_id": device_id})
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
        try:
            account = account_for_token(websocket.query_params.get("access_token", ""))
        except HTTPException:
            await websocket.close(code=1008, reason="请先登录")
            return
        if not has_permission(account, PERMISSION_DEVICE_VIEW):
            await websocket.close(code=1008, reason="当前权限组无权查看设备数据")
            return
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
