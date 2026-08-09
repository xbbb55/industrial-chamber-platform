import struct
import uuid

from device_edge.shared_memory_store import (
    LENGTH_PREFIXED_JSON_PROTOCOL,
    create_or_attach,
    read_snapshot_with_version,
    write_snapshot,
)


def test_length_prefixed_json_protocol_matches_cxx_layout() -> None:
    name = f"test_length_prefixed_{uuid.uuid4().hex}"
    memory = create_or_attach(name, 4096)
    snapshot = {"device_id": "CH-CXX-001", "mainData": {"TEMP_PV": 25.5}}
    try:
        write_snapshot(memory, snapshot, 4096, LENGTH_PREFIXED_JSON_PROTOCOL)

        payload_length = struct.unpack_from("<I", memory.buf, 0)[0]
        assert payload_length > 0
        assert bytes(memory.buf[4:5]) == b"{"

        version, actual = read_snapshot_with_version(memory, protocol=LENGTH_PREFIXED_JSON_PROTOCOL)
        assert version > 0
        assert actual == snapshot
    finally:
        memory.close()
        memory.unlink()
