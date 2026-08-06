import json
import struct
import time
from multiprocessing import shared_memory
from typing import Any


DEFAULT_SHM_NAME = "industrial_chamber_realtime_v1"
DEFAULT_SHM_SIZE = 1024 * 256
HEADER = struct.Struct("<QI")


class SharedMemoryNotReady(RuntimeError):
    pass


def create_or_attach(name: str = DEFAULT_SHM_NAME, size: int = DEFAULT_SHM_SIZE) -> shared_memory.SharedMemory:
    try:
        return shared_memory.SharedMemory(name=name, create=True, size=size)
    except FileExistsError:
        return shared_memory.SharedMemory(name=name, create=False)


def attach_existing(name: str = DEFAULT_SHM_NAME) -> shared_memory.SharedMemory:
    try:
        return shared_memory.SharedMemory(name=name, create=False)
    except FileNotFoundError as exc:
        raise SharedMemoryNotReady(f"Shared memory {name!r} has not been created yet.") from exc


def write_snapshot(shm: shared_memory.SharedMemory, snapshot: dict[str, Any], size: int = DEFAULT_SHM_SIZE) -> None:
    payload = json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(payload) > size - HEADER.size:
        raise ValueError(f"Snapshot is too large for shared memory: {len(payload)} bytes")

    current_version, _ = HEADER.unpack_from(shm.buf, 0)
    write_version = current_version + 1
    if write_version % 2 == 0:
        write_version += 1

    HEADER.pack_into(shm.buf, 0, write_version, 0)
    shm.buf[HEADER.size:HEADER.size + len(payload)] = payload
    HEADER.pack_into(shm.buf, 0, write_version + 1, len(payload))


def read_snapshot(shm: shared_memory.SharedMemory, retries: int = 5) -> dict[str, Any]:
    _, snapshot = read_snapshot_with_version(shm, retries)
    return snapshot


def read_snapshot_with_version(
    shm: shared_memory.SharedMemory,
    retries: int = 5,
) -> tuple[int, dict[str, Any]]:
    for _ in range(retries):
        version_before, length = HEADER.unpack_from(shm.buf, 0)
        if version_before == 0 or length == 0:
            raise SharedMemoryNotReady("Shared memory exists but does not contain data yet.")
        if length > len(shm.buf) - HEADER.size:
            raise RuntimeError(f"Shared-memory payload length is invalid: {length}")
        if version_before % 2 == 1:
            time.sleep(0.002)
            continue

        raw = bytes(shm.buf[HEADER.size:HEADER.size + length])
        version_after, _ = HEADER.unpack_from(shm.buf, 0)
        if version_before == version_after and version_after % 2 == 0:
            return version_after, json.loads(raw.decode("utf-8"))

        time.sleep(0.002)

    raise RuntimeError("Could not read a stable shared-memory snapshot.")
