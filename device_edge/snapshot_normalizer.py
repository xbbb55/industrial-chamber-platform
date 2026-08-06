"""Normalize controller snapshots before they reach local or central clients."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any


PRODUCTION_SCHEMA = "industrial-controller-json-v1"
CHINA_STANDARD_TIME = timezone(timedelta(hours=8))
COMMUNICATION_FAILURE_KEYWORDS = ("通讯故障", "通信故障", "离线", "断线")


def normalize_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    if _is_production_device(snapshot):
        device = normalize_production_device(snapshot)
        return {
            "source": "industrial_controller",
            "schema": PRODUCTION_SCHEMA,
            "sequence": 0,
            "written_at": device["updated_at"],
            "devices": [device],
        }

    normalized = deepcopy(snapshot)
    devices = normalized.get("devices")
    if not isinstance(devices, list):
        normalized["devices"] = []
        return normalized
    normalized["devices"] = [
        normalize_production_device(item) if _is_production_device(item) else item
        for item in devices
        if isinstance(item, dict)
    ]
    return normalized


def normalize_production_device(payload: dict[str, Any]) -> dict[str, Any]:
    main_data = _mapping(payload.get("mainData"))
    program = _mapping(payload.get("program"))
    status = _mapping(payload.get("status"))
    dut = _mapping(payload.get("DUT"))
    alarms = _string_list(status.get("alarm"))
    status_text = str(status.get("state") or "").strip()
    online = not _contains_any(status_text, COMMUNICATION_FAILURE_KEYWORDS)
    updated_at = _parse_controller_time(payload.get("time"))

    device = deepcopy(payload)
    device.update({
        "device_id": str(payload.get("device_id") or "").strip(),
        "name": str(payload.get("name") or payload.get("device_id") or "").strip(),
        "device_online": online,
        "device_last_success_at": updated_at if online else None,
        "consecutive_read_failures": 0 if online else 1,
        "communication_error": None if online else (status_text or "控制器通讯故障"),
        "data_updated_at": updated_at,
        "online": online,
        "run_state": _run_state(status_text, program.get("run"), alarms, online),
        "status_text": status_text,
        "current_temperature": _number(main_data.get("TEMP_PV")),
        "target_temperature": _number(main_data.get("TEMP_SP")),
        "current_humidity": _number(main_data.get("HUMI_PV")),
        "target_humidity": _number(main_data.get("HUMI_SP")),
        "current_pressure": _number(main_data.get("pressure_PV")),
        "target_pressure": _number(main_data.get("pressure_SP")),
        "pressure_output": _number(main_data.get("pressure_Out")),
        "current_step": _integer(program.get("step")),
        "total_steps": 0,
        "alarm": "；".join(alarms) if alarms else None,
        "alarms": alarms,
        "updated_at": updated_at,
        "data_time": payload.get("time"),
        "run_mode": main_data.get("runMode"),
        "main_status": main_data.get("status"),
        "program_running": program.get("run"),
        "dut_selected": dut.get("DUT_SEL"),
        "schema": PRODUCTION_SCHEMA,
    })
    return device


def _is_production_device(value: Any) -> bool:
    return isinstance(value, dict) and all(isinstance(value.get(key), dict) for key in ("mainData", "program", "status")) and "device_id" in value


def _run_state(status_text: str, running: Any, alarms: list[str], online: bool) -> str:
    if not online:
        return "OFFLINE"
    if alarms or _contains_any(status_text, ("报警", "故障", "保护", "异常")):
        return "ALARM"
    for keywords, value in (("运行", "RUNNING"), ("暂停", "HOLDING"), ("保持", "HOLDING"), ("停止", "STOPPED"), ("完成", "COMPLETED"), ("就绪", "READY"), ("空闲", "IDLE"), ("待机", "IDLE")):
        if keywords in status_text:
            return value
    return "RUNNING" if _number(running) else "IDLE"


def _parse_controller_time(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return datetime.strptime(value.strip(), "%Y-%m-%d %H:%M:%S").replace(tzinfo=CHINA_STANDARD_TIME).timestamp()
        except ValueError:
            pass
    return datetime.now(tz=CHINA_STANDARD_TIME).timestamp()


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if value not in (None, "") else []


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _integer(value: Any) -> int:
    return int(_number(value))


def _contains_any(value: str, candidates: tuple[str, ...]) -> bool:
    return any(candidate in value for candidate in candidates)
