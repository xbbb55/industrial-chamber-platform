from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any


PRODUCTION_SCHEMA = "industrial-controller-json-v1"
CHINA_STANDARD_TIME = timezone(timedelta(hours=8))
COMMUNICATION_FAILURE_KEYWORDS = (
    "\u901a\u8baf\u6545\u969c",
    "\u901a\u4fe1\u6545\u969c",
    "\u79bb\u7ebf",
    "\u65ad\u7ebf",
)


def normalize_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Convert controller JSON or a legacy snapshot into the platform schema.

    The controller writes one device object with grouped fields (``mainData``,
    ``program``, ``status`` and so on). The platform API historically consumes
    a snapshot containing a ``devices`` list. Normalizing at the backend
    boundary keeps the rest of the application stable while retaining every
    production field on the normalized device.
    """
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
        normalize_production_device(device) if _is_production_device(device) else device
        for device in devices
        if isinstance(device, dict)
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

    device_id = str(payload.get("device_id") or "").strip()
    updated_at = _parse_controller_time(payload.get("time"))
    alarm_text = "\uff1b".join(alarms) if alarms else None

    # Keep the grouped production fields unchanged so future features can use
    # them without another lossy schema migration.
    device = deepcopy(payload)
    device.update({
        "device_id": device_id,
        "name": str(payload.get("name") or device_id),
        "online": online,
        "run_state": _normalize_run_state(status_text, program.get("run"), alarms, online),
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
        "alarm": alarm_text,
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
    return (
        isinstance(value, dict)
        and isinstance(value.get("mainData"), dict)
        and isinstance(value.get("program"), dict)
        and isinstance(value.get("status"), dict)
        and "device_id" in value
    )


def _normalize_run_state(
    status_text: str,
    program_running: Any,
    alarms: list[str],
    online: bool,
) -> str:
    if not online:
        return "OFFLINE"
    if alarms or _contains_any(
        status_text,
        ("\u62a5\u8b66", "\u6545\u969c", "\u4fdd\u62a4", "\u5f02\u5e38"),
    ):
        return "ALARM"
    state_keywords = (
        (("\u8fd0\u884c",), "RUNNING"),
        (("\u6682\u505c", "\u4fdd\u6301"), "HOLDING"),
        (("\u505c\u6b62", "\u505c\u673a"), "STOPPED"),
        (("\u5b8c\u6210", "\u7ed3\u675f"), "COMPLETED"),
        (("\u5c31\u7eea",), "READY"),
        (("\u7a7a\u95f2", "\u5f85\u673a"), "IDLE"),
    )
    for keywords, state in state_keywords:
        if _contains_any(status_text, keywords):
            return state
    if _truthy_number(program_running):
        return "RUNNING"
    return "IDLE"


def _parse_controller_time(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            parsed = datetime.strptime(value.strip(), "%Y-%m-%d %H:%M:%S")
            return parsed.replace(tzinfo=CHINA_STANDARD_TIME).timestamp()
        except ValueError:
            pass
    return datetime.now(tz=CHINA_STANDARD_TIME).timestamp()


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value is None or value == "":
        return []
    return [str(value).strip()]


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _integer(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _truthy_number(value: Any) -> bool:
    try:
        return float(value) != 0
    except (TypeError, ValueError):
        return False


def _contains_any(value: str, candidates: tuple[str, ...]) -> bool:
    return any(candidate in value for candidate in candidates)
