import json
import struct
import time
import zlib
from multiprocessing import shared_memory
from typing import Any


DEFAULT_SHM_NAME = "industrial_chamber_realtime_v1"
DEFAULT_SHM_SIZE = 1024 * 256
VERSIONED_JSON_PROTOCOL = "versioned_json_v1"
LENGTH_PREFIXED_JSON_PROTOCOL = "length_prefixed_json_v1"
HEADER = struct.Struct("<QI")
LENGTH_HEADER = struct.Struct("<I")


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


def write_snapshot(
    shm: shared_memory.SharedMemory,
    snapshot: dict[str, Any],
    size: int = DEFAULT_SHM_SIZE,
    protocol: str = VERSIONED_JSON_PROTOCOL,
) -> None:
    payload = json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    header = _header_for(protocol)
    _ensure_payload_fits(payload, shm, size, header)

    if protocol == VERSIONED_JSON_PROTOCOL:
        current_version, _ = HEADER.unpack_from(shm.buf, 0)
        write_version = current_version + 1
        if write_version % 2 == 0:
            write_version += 1
        HEADER.pack_into(shm.buf, 0, write_version, 0)
        shm.buf[HEADER.size:HEADER.size + len(payload)] = payload
        HEADER.pack_into(shm.buf, 0, write_version + 1, len(payload))
        return

    LENGTH_HEADER.pack_into(shm.buf, 0, 0)
    shm.buf[LENGTH_HEADER.size:LENGTH_HEADER.size + len(payload)] = payload
    LENGTH_HEADER.pack_into(shm.buf, 0, len(payload))


def read_snapshot(
    shm: shared_memory.SharedMemory,
    retries: int = 5,
    protocol: str = VERSIONED_JSON_PROTOCOL,
) -> dict[str, Any]:
    _, snapshot = read_snapshot_with_version(shm, retries, protocol)
    return snapshot


def read_snapshot_with_version(
    shm: shared_memory.SharedMemory,
    retries: int = 5,
    protocol: str = VERSIONED_JSON_PROTOCOL,
) -> tuple[int, dict[str, Any]]:
    _header_for(protocol)
    if protocol == VERSIONED_JSON_PROTOCOL:
        return _read_versioned_snapshot(shm, retries)
    return _read_length_prefixed_snapshot(shm, retries)


def _read_versioned_snapshot(shm: shared_memory.SharedMemory, retries: int) -> tuple[int, dict[str, Any]]:
    for _ in range(retries):
        version_before, length = HEADER.unpack_from(shm.buf, 0)
        if version_before == 0 or length == 0:
            raise SharedMemoryNotReady("Shared memory exists but does not contain data yet.")
        _ensure_length_is_valid(length, shm, HEADER)
        if version_before % 2 == 1:
            time.sleep(0.002)
            continue

        raw = bytes(shm.buf[HEADER.size:HEADER.size + length])
        version_after, _ = HEADER.unpack_from(shm.buf, 0)
        if version_before == version_after and version_after % 2 == 0:
            return version_after, json.loads(raw.decode("utf-8"))

        time.sleep(0.002)

    raise RuntimeError("Could not read a stable shared-memory snapshot.")


def _read_length_prefixed_snapshot(shm: shared_memory.SharedMemory, retries: int) -> tuple[int, dict[str, Any]]:
    for _ in range(retries):
        length_before = LENGTH_HEADER.unpack_from(shm.buf, 0)[0]
        if length_before == 0:
            raise SharedMemoryNotReady("Shared memory exists but does not contain data yet.")
        _ensure_length_is_valid(length_before, shm, LENGTH_HEADER)

        raw = bytes(shm.buf[LENGTH_HEADER.size:LENGTH_HEADER.size + length_before])
        length_after = LENGTH_HEADER.unpack_from(shm.buf, 0)[0]
        if length_before != length_after:
            time.sleep(0.002)
            continue
        try:
            snapshot = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            time.sleep(0.002)
            continue
        return zlib.crc32(raw), snapshot

    raise RuntimeError("Could not read a stable length-prefixed shared-memory snapshot.")


def _header_for(protocol: str) -> struct.Struct:
    if protocol == VERSIONED_JSON_PROTOCOL:
        return HEADER
    if protocol == LENGTH_PREFIXED_JSON_PROTOCOL:
        return LENGTH_HEADER
    raise ValueError(f"Unsupported shared-memory protocol: {protocol}")


def _ensure_payload_fits(payload: bytes, shm: shared_memory.SharedMemory, size: int, header: struct.Struct) -> None:
    capacity = len(shm.buf)
    if size != capacity:
        raise ValueError(f"Configured shared-memory size {size} does not match actual size {capacity}")
    if len(payload) > capacity - header.size:
        raise ValueError(f"Snapshot is too large for shared memory: {len(payload)} bytes")


def _ensure_length_is_valid(length: int, shm: shared_memory.SharedMemory, header: struct.Struct) -> None:
    if length > len(shm.buf) - header.size:
        raise RuntimeError(f"Shared-memory payload length is invalid: {length}")
