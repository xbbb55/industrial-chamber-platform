import argparse
import math
import os
import random
import threading
import time
from pathlib import Path
from typing import Any, Optional

from backend.production_payload import build_production_payload
from backend.shared_memory_store import SHM_NAME, create_or_attach, write_snapshot
from device_edge.command_client import CommandClient
from device_edge.config import load_config
from device_edge.control_protocol import normalize_command, protocol_time


def build_device(
    tick: int,
    device_id: str = "SIM-PY-CN-001",
    *,
    running: int = 1,
    state: str = "运行中",
    step: int = 1,
    alarms: tuple[str, ...] = (),
) -> dict[str, Any]:
    wave = math.sin(tick / 12)
    target_temperature, target_humidity = -20, 40
    temperature = target_temperature + wave * 2.2 + random.uniform(-0.15, 0.15)
    humidity = target_humidity + math.cos(tick / 14) * 1.8 + random.uniform(-0.2, 0.2)
    return build_production_payload(
        device_id=device_id,
        current_temperature=temperature,
        current_humidity=humidity,
        target_temperature=target_temperature,
        target_humidity=target_humidity,
        step=step,
        running=running,
        state=state,
        alarms=alarms,
        sequence=tick,
    )


class DeviceRuntime:
    """Own the simulated controller state and apply commands between writes."""

    def __init__(self, device_id: str) -> None:
        self._device_id = device_id
        self._mode = "RUNNING"
        self._step_offset = 0
        self._lock = threading.Lock()

    def snapshot(self, tick: int) -> dict[str, Any]:
        with self._lock:
            if self._mode == "STOPPED":
                return build_device(tick, self._device_id, running=0, state="停止", step=0)
            if self._mode == "HOLDING":
                return build_device(tick, self._device_id, running=0, state="保持", step=1 + self._step_offset)

            alarmed = tick % 70 > 55
            return build_device(
                tick,
                self._device_id,
                running=0 if alarmed else 1,
                state="超温保护" if alarmed else "运行中",
                step=0 if alarmed else 1 + (tick // 40) % 3 + self._step_offset,
                alarms=("超温保护",) if alarmed else (),
            )

    def handle_command(self, command: dict[str, Any]) -> dict[str, str]:
        wire_command, command_type = normalize_command(command.get("command"))
        with self._lock:
            if command_type == "START_TEST":
                self._mode = "RUNNING"
            elif command_type == "STOP_TEST":
                self._mode = "STOPPED"
            elif command_type == "HOLD_TEST":
                self._mode = "HOLDING"
            elif command_type == "SKIP_STEP":
                self._mode = "RUNNING"
                self._step_offset += 1
            elif command_type != "KEEP_TEST":
                return {"successMessage": wire_command, "time": protocol_time()}

        print(f"controller command applied: {wire_command}, state={self._mode}")
        return {"successMessage": wire_command, "time": protocol_time()}


def start_command_client(config_path: str, runtime: DeviceRuntime) -> Optional[threading.Thread]:
    if not Path(config_path).is_file():
        print(f"command client disabled: config not found: {config_path}")
        return None

    config = load_config(config_path)
    thread = threading.Thread(
        target=CommandClient(config, runtime.handle_command).run_forever,
        daemon=True,
        name="device-command-client",
    )
    thread.start()
    return thread


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulated Chinese industrial-controller shared-memory writer.")
    parser.add_argument("--config", default="device-edge.config.json", help="Edge config used to receive controller commands.")
    parser.add_argument("--without-command-client", action="store_true", help="Write telemetry only without polling commands.")
    args = parser.parse_args()

    shm = create_or_attach()
    device_id = os.getenv("CHAMBER_DEVICE_ID", "SIM-PY-CN-001")
    runtime = DeviceRuntime(device_id)
    print(f"shared memory writer started: {SHM_NAME}, device_id={device_id}")
    if not args.without_command_client:
        start_command_client(args.config, runtime)
    print("press Ctrl+C to stop")
    tick = 0
    try:
        while True:
            write_snapshot(shm, runtime.snapshot(tick))
            tick += 1
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("writer stopped")
    finally:
        shm.close()


if __name__ == "__main__":
    main()
