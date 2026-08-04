import uuid

from device_edge.config import EdgeConfig
from device_edge.manual_input_server import ManualInputState
from device_edge.shared_memory_store import read_snapshot


def test_command_execution_status_is_written_to_dedicated_memory() -> None:
    suffix = uuid.uuid4().hex
    config = EdgeConfig(
        edge_id="EDGE-TEST-001",
        device_ip="192.168.10.22",
        agent_version="test",
        server_url="http://127.0.0.1:8010",
        upload_interval_seconds=1,
        stream_interval_seconds=1,
        shared_memory_name=f"test_realtime_{suffix}",
        shared_memory_size=65536,
        command_status_memory_name=f"test_command_status_{suffix}",
        command_status_memory_size=65536,
    )
    state = ManualInputState(config)
    try:
        state.start_stream(25, 60, "SIM-TEST-001", "Test Chamber")
        result = state.handle_command({
            "command_id": "CMD-TEST-001",
            "command": "Stop",
            "device_id": "SIM-TEST-001",
        })

        status_memory = read_snapshot(state.command_status_shm)
        latest = status_memory["latest"]
        assert result["status"] == "EXECUTED"
        assert latest["command_id"] == "CMD-TEST-001"
        assert latest["command"] == "Stop"
        assert latest["status"] == "EXECUTED"
        assert latest["device_id"] == "SIM-TEST-001"
        stopped_snapshot = read_snapshot(state.shm)
        assert stopped_snapshot["program"]["run"] == 0
        assert stopped_snapshot["mainData"]["runMode"] == 0
        assert stopped_snapshot["status"]["state"] == "\u505c\u6b62"
        assert not state.stream_active
        assert state.should_upload()

        state.handle_command({
            "command_id": "CMD-TEST-002",
            "command": "Run",
            "device_id": "SIM-TEST-001",
        })
        assert state.stream_active

        state.handle_command({
            "command_id": "CMD-TEST-003",
            "command": "Hold",
            "device_id": "SIM-TEST-001",
        })
        held_snapshot = read_snapshot(state.shm)
        assert held_snapshot["program"]["run"] == 0
        assert held_snapshot["mainData"]["runMode"] == 0
        assert held_snapshot["status"]["state"] == "\u4fdd\u6301"
        assert not state.stream_active
        assert state.should_upload()

        # A paused stream must not generate a new running snapshot.
        sequence_before = state.sequence
        state._stream_loop()
        assert state.sequence == sequence_before
    finally:
        state.shm.close()
        state.shm.unlink()
        state.command_status_shm.close()
        state.command_status_shm.unlink()
