"""FE_W/BE_R control protocol from the industrial-controller interface spec."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional, Tuple


DIRECT_COMMANDS = {
    "Run": "START_TEST",
    "Stop": "STOP_TEST",
    "Hold": "HOLD_TEST",
    "Keep": "KEEP_TEST",
    "Jnmp": "SKIP_STEP",
    "BuzzerON": "BUZZER_ON",
    "BuzzerOFF": "BUZZER_OFF",
    "Reset": "RESET_ALARM",
}

SETTING_COMMANDS = {
    "fixed_value",
    "operation_setting",
    "basic_info",
    "correction",
    "pid_set",
    "factory_params",
}


def protocol_time() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")


def normalize_command(command: Any) -> Tuple[str, str]:
    wire = str(command or "").strip()
    if wire in DIRECT_COMMANDS:
        return wire, DIRECT_COMMANDS[wire]
    if wire.startswith("RunMode="):
        return wire, "SET_RUN_MODE"
    if wire.startswith("DownloadProgram="):
        return wire, "DOWNLOAD_PROGRAM"
    if wire in SETTING_COMMANDS:
        return wire, wire.upper()
    return wire, "UNKNOWN"


def build_fe_w(command: str, when: Optional[str] = None) -> Dict[str, str]:
    wire, internal = normalize_command(command)
    if internal == "UNKNOWN":
        raise ValueError(f"Unsupported FE_W command: {command}")
    return {"command": wire, "time": when or protocol_time()}


def build_be_r(command: str, when: Optional[str] = None) -> Dict[str, str]:
    wire, internal = normalize_command(command)
    if internal == "UNKNOWN":
        raise ValueError(f"Unsupported BE_R command: {command}")
    return {"successMessage": wire, "time": when or protocol_time()}
