import json
import struct
import time
from multiprocessing import shared_memory
from typing import Any


SHM_NAME = "industrial_chamber_realtime_v1"
SHM_SIZE = 1024 * 256
HEADER = struct.Struct("<QI")


class SharedMemoryNotReady(RuntimeError):
    pass


def create_or_attach() -> shared_memory.SharedMemory:
    try:
        return shared_memory.SharedMemory(name=SHM_NAME, create=True, size=SHM_SIZE)
    except FileExistsError:
        return shared_memory.SharedMemory(name=SHM_NAME, create=False)


def attach_existing() -> shared_memory.SharedMemory:
    try:
        return shared_memory.SharedMemory(name=SHM_NAME, create=False)
    except FileNotFoundError as exc:
        raise SharedMemoryNotReady(
            f"Shared memory {SHM_NAME!r} is not created yet. Start device_memory_writer.py first."
        ) from exc


def write_snapshot(shm: shared_memory.SharedMemory, snapshot: dict[str, Any]) -> None:
    payload = json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(payload) > SHM_SIZE - HEADER.size:
        raise ValueError(f"Snapshot is too large for shared memory: {len(payload)} bytes")

    current_version, _ = HEADER.unpack_from(shm.buf, 0)
    write_version = current_version + 1
    if write_version % 2 == 0:
        write_version += 1

    # Odd version means a writer is in progress. Even version means stable data.
    HEADER.pack_into(shm.buf, 0, write_version, 0)
    shm.buf[HEADER.size:HEADER.size + len(payload)] = payload
    HEADER.pack_into(shm.buf, 0, write_version + 1, len(payload))


def read_snapshot(shm: shared_memory.SharedMemory, retries: int = 5) -> dict[str, Any]:
    for _ in range(retries):
        version_before, length = HEADER.unpack_from(shm.buf, 0)
        if version_before == 0 or length == 0:
            raise SharedMemoryNotReady("Shared memory exists but does not contain data yet.")
        if version_before % 2 == 1:
            time.sleep(0.002)
            continue

        raw = bytes(shm.buf[HEADER.size:HEADER.size + length])
        version_after, _ = HEADER.unpack_from(shm.buf, 0)
        if version_before == version_after and version_after % 2 == 0:
            return json.loads(raw.decode("utf-8"))

        time.sleep(0.002)

    raise RuntimeError("Could not read a stable shared-memory snapshot.")


def inspect_memory(shm: shared_memory.SharedMemory) -> dict[str, Any]:
    version, length = HEADER.unpack_from(shm.buf, 0)
    capacity = SHM_SIZE - HEADER.size
    payload = bytes(shm.buf[HEADER.size:HEADER.size + length]) if length else b""
    preview_length = min(length, 1200)
    preview = bytes(shm.buf[HEADER.size:HEADER.size + preview_length]).decode("utf-8", errors="replace")
    return {
        "name": SHM_NAME,
        "total_size_bytes": SHM_SIZE,
        "header_size_bytes": HEADER.size,
        "payload_capacity_bytes": capacity,
        "version": version,
        "is_write_in_progress": bool(version % 2),
        "payload_length_bytes": length,
        "payload_usage_percent": round((length / capacity) * 100, 3) if capacity else 0,
        "free_payload_bytes": max(capacity - length, 0),
        "payload_preview": preview,
        "raw_header_hex": bytes(shm.buf[:HEADER.size]).hex(" "),
    }
