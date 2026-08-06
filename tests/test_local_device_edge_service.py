import asyncio
import uuid

from device_edge.config import EdgeConfig
from device_edge.production_payload import build_production_payload
from device_edge.runtime import DeviceEdgeRuntime
from device_edge.shared_memory_store import attach_existing, create_or_attach, read_snapshot, write_snapshot


def test_local_service_reads_cxx_data_and_bridges_command(tmp_path):
    asyncio.run(_exercise_runtime(tmp_path))


async def _exercise_runtime(tmp_path):
    suffix = uuid.uuid4().hex[:8]
    config = EdgeConfig(
        edge_id="EDGE-LOCAL-001",
        device_ip="127.0.0.1",
        agent_version="test",
        shared_memory_name=f"BE_W_{suffix}",
        command_request_memory_name=f"FE_W_{suffix}",
        command_status_memory_name=f"BE_R_{suffix}",
        shared_memory_size=65536,
        command_request_memory_size=65536,
        command_status_memory_size=65536,
        realtime_poll_interval_seconds=0.05,
        command_status_idle_poll_interval_seconds=0.05,
        command_status_active_poll_interval_seconds=0.05,
        sqlite_path=str(tmp_path / "edge.db"),
    )
    realtime = create_or_attach(config.shared_memory_name, config.shared_memory_size)
    status = create_or_attach(config.command_status_memory_name, config.command_status_memory_size)
    request = None
    runtime = DeviceEdgeRuntime(config)
    snapshot = None
    try:
        write_snapshot(
            realtime,
            build_production_payload(
                device_id="CH-LOCAL-001",
                current_temperature=25,
                current_humidity=60,
                target_temperature=25,
                target_humidity=60,
            ),
            config.shared_memory_size,
        )
        await runtime.start()
        for _ in range(20):
            try:
                snapshot = runtime.snapshot()
                break
            except RuntimeError:
                await asyncio.sleep(0.05)
        assert snapshot is not None
        assert snapshot["devices"][0]["device_id"] == "CH-LOCAL-001"

        runtime.submit_command({"command": "Run", "operator_id": "web-admin", "device_id": "CH-LOCAL-001"})
        command = runtime.submit_command({"command": "Stop", "operator_id": "web-admin", "device_id": "CH-LOCAL-001"})
        request = attach_existing(config.command_request_memory_name)
        assert read_snapshot(request)["command"] == "Stop"
        assert "command_id" not in read_snapshot(request)

        write_snapshot(
            status,
            {"successMessage": "Stop"},
            config.command_status_memory_size,
        )
        for _ in range(20):
            if runtime.health()["pending_command"] is None:
                break
            await asyncio.sleep(0.05)
        assert runtime.health()["pending_command"] is None
    finally:
        await runtime.stop()
        if request is not None:
            request.close()
        for memory in (realtime, status):
            memory.close()
            memory.unlink()
        try:
            command_memory = attach_existing(config.command_request_memory_name)
        except Exception:
            command_memory = None
        if command_memory is not None:
            command_memory.close()
            command_memory.unlink()
