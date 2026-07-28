import math
import os
import random
import time

from backend.production_payload import build_production_payload
from backend.shared_memory_store import SHM_NAME, create_or_attach, write_snapshot


def build_device(tick: int, device_id: str = "SIM-PY-CN-001") -> dict:
    wave = math.sin(tick / 12)
    target_temperature, target_humidity = -20, 40
    temperature = target_temperature + wave * 2.2 + random.uniform(-0.15, 0.15)
    humidity = target_humidity + math.cos(tick / 14) * 1.8 + random.uniform(-0.2, 0.2)
    alarmed = tick % 70 > 55
    return build_production_payload(
        device_id=device_id,
        current_temperature=temperature,
        current_humidity=humidity,
        target_temperature=target_temperature,
        target_humidity=target_humidity,
        step=0 if alarmed else 1 + (tick // 40) % 3,
        running=0 if alarmed else 1,
        state="\u8d85\u6e29\u4fdd\u62a4" if alarmed else "\u8fd0\u884c\u4e2d",
        alarms=("\u8d85\u6e29\u4fdd\u62a4",) if alarmed else (),
        sequence=tick,
    )


def main() -> None:
    shm = create_or_attach()
    device_id = os.getenv("CHAMBER_DEVICE_ID", "SIM-PY-CN-001")
    print(f"shared memory writer started: {SHM_NAME}, device_id={device_id}")
    print("press Ctrl+C to stop")
    tick = 0
    try:
        while True:
            write_snapshot(shm, build_device(tick, device_id))
            tick += 1
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("writer stopped")
    finally:
        shm.close()


if __name__ == "__main__":
    main()
