import time

from backend import memory_router


def test_stale_edge_is_marked_offline_and_cannot_receive_commands(monkeypatch):
    edge_id = "EDGE-TIMEOUT-001"
    monkeypatch.setattr(memory_router, "EDGE_SNAPSHOT_TTL_SECONDS", 5.0)
    monkeypatch.setattr(
        memory_router,
        "uploaded_edge_snapshots",
        {
            edge_id: {
                "edge_id": edge_id,
                "edge_ip": "192.168.1.10",
                "received_at": time.time() - 8,
                "snapshot": {
                    "sequence": 10,
                    "written_at": time.time() - 8,
                    "devices": [
                        {
                            "device_id": "SIM-TIMEOUT-001",
                            "run_state": "RUNNING",
                            "online": True,
                            "alarm": None,
                            "alarms": [],
                        }
                    ],
                },
            }
        },
    )

    snapshot = memory_router.get_uploaded_snapshot()
    device = snapshot["devices"][0]

    assert device["run_state"] == "OFFLINE"
    assert device["online"] is False
    assert device["edge_stale"] is True
    assert snapshot["stale_edge_count"] == 1
    assert memory_router.find_edge_id_for_device("SIM-TIMEOUT-001") is None


def test_recent_edge_remains_online(monkeypatch):
    edge_id = "EDGE-FRESH-001"
    monkeypatch.setattr(memory_router, "EDGE_SNAPSHOT_TTL_SECONDS", 5.0)
    monkeypatch.setattr(
        memory_router,
        "uploaded_edge_snapshots",
        {
            edge_id: {
                "edge_id": edge_id,
                "edge_ip": "192.168.1.11",
                "received_at": time.time(),
                "snapshot": {
                    "sequence": 11,
                    "written_at": time.time(),
                    "devices": [
                        {
                            "device_id": "SIM-FRESH-001",
                            "run_state": "RUNNING",
                            "online": True,
                            "alarm": None,
                            "alarms": [],
                        }
                    ],
                },
            }
        },
    )

    snapshot = memory_router.get_uploaded_snapshot()
    device = snapshot["devices"][0]

    assert device["run_state"] == "RUNNING"
    assert device["online"] is True
    assert device["edge_stale"] is False
    assert snapshot["stale_edge_count"] == 0
