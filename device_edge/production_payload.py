from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Iterable


CHINA_STANDARD_TIME = timezone(timedelta(hours=8))


def build_production_payload(
    *,
    device_id: str,
    current_temperature: float,
    current_humidity: float,
    target_temperature: float,
    target_humidity: float,
    step: int = 0,
    running: int = 0,
    state: str = "\u8fd0\u884c\u4e2d",
    alarms: Iterable[str] = (),
    elapsed_seconds: float = 0.0,
    sequence: int = 0,
) -> dict[str, Any]:
    """Build the single-device JSON object written by a production controller."""
    now = datetime.now(tz=CHINA_STANDARD_TIME)
    now_text = now.strftime("%Y-%m-%d %H:%M:%S")
    alarms = [str(alarm) for alarm in alarms if str(alarm).strip()]
    return {
        "DUT": {**{f"DUT{index}": 0 for index in range(24)}, "DUT0": round(current_temperature, 2), "DUT_SEL": 0},
        "compressor": {key: 0 for key in (
            "A1_Cool", "A1_DP", "A1_DT", "A1_RP", "A2_Cool", "A2_DP", "A2_DT", "A2_RP", "A_Water",
            "B1_Cool", "B1_DP", "B1_DT", "B1_RP", "B2_Cool", "B2_DP", "B2_DT", "B2_RP", "B_Water",
            "C1_Cool", "C1_DP", "C1_DT", "C1_RP", "C2_Cool", "C2_DP", "C2_DT", "C2_RP", "C_Water",
        )},
        "device_id": str(device_id),
        "event": {f"event{index}": "---=OFF" for index in range(16)},
        "mainData": {
            "HUMI_Cool": 0, "HUMI_Hot": 0, "HUMI_HotG": 0, "HUMI_HotW": 0,
            "HUMI_Out": round(current_humidity, 2), "HUMI_PV": round(current_humidity, 2), "HUMI_SP": round(target_humidity, 2),
            "TEMP_Cool": 0, "TEMP_Hot": 0, "TEMP_Out": round(current_temperature, 2),
            "TEMP_PV": round(current_temperature, 2), "TEMP_SP": round(target_temperature, 2),
            "pressure_Out": 0, "pressure_PV": 0, "pressure_SP": 0,
            "runMode": 1 if running else 0, "status": 1 if running else 0,
        },
        "other": 0,
        "program": {
            "download": "#1:SIMULATION", "fullCycle": "0/0", "innerLoop": "0/0",
            "innerLoopNo": "\u5185\u90e8\u5faa\u73af1", "link": "#0:---", "run": int(running), "step": int(step),
        },
        "status": {"alarm": alarms, "state": state},
        "time": now_text,
        "timeData": {
            "endTime": "", "runTime": _format_duration(elapsed_seconds),
            "setTime": "00:00:00", "startTime": now_text, "totalTime": "00:00:00",
        },
    }


def _format_duration(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
