import unittest

from backend.snapshot_normalizer import PRODUCTION_SCHEMA, normalize_snapshot
from backend.production_payload import build_production_payload
from device_memory_writer import build_device


class SnapshotNormalizerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.production_json = {
            "DUT": {"DUT0": -200, "DUT_SEL": 2},
            "compressor": {"A1_Cool": 1},
            "device_id": "SIM-TEST-DEVICE-001",
            "device_ip": "192.168.1.101",
            "event": {"event0": "\u7528\u6237\u4e8b\u4ef61=OFF"},
            "mainData": {
                "HUMI_PV": 48.5,
                "HUMI_SP": 50,
                "TEMP_PV": -19.8,
                "TEMP_SP": -20,
                "pressure_Out": 35,
                "pressure_PV": 1.2,
                "pressure_SP": 1.5,
                "runMode": 1,
                "status": 2,
            },
            "other": 0,
            "program": {
                "download": "#1:GB2423.4",
                "fullCycle": "1/3",
                "innerLoop": "1/2",
                "innerLoopNo": "\u5185\u90e8\u5faa\u73af1",
                "link": "#0:---",
                "run": 1,
                "step": 4,
            },
            "status": {"alarm": [], "state": "\u8fd0\u884c\u4e2d"},
            "time": "2026-07-14 11:10:32",
            "timeData": {"runTime": "00:10:00"},
        }

    def test_normalizes_production_controller_json(self) -> None:
        snapshot = normalize_snapshot(self.production_json)

        self.assertEqual(snapshot["schema"], PRODUCTION_SCHEMA)
        self.assertEqual(len(snapshot["devices"]), 1)
        device = snapshot["devices"][0]
        self.assertEqual(device["device_id"], "SIM-TEST-DEVICE-001")
        self.assertEqual(device["device_ip"], "192.168.1.101")
        self.assertEqual(device["run_state"], "RUNNING")
        self.assertTrue(device["online"])
        self.assertEqual(device["current_temperature"], -19.8)
        self.assertEqual(device["target_temperature"], -20.0)
        self.assertEqual(device["current_humidity"], 48.5)
        self.assertEqual(device["target_humidity"], 50.0)
        self.assertEqual(device["current_pressure"], 1.2)
        self.assertEqual(device["current_step"], 4)
        self.assertEqual(device["dut_selected"], 2)
        self.assertEqual(device["compressor"], {"A1_Cool": 1})
        self.assertEqual(device["timeData"], {"runTime": "00:10:00"})

    def test_communication_fault_is_offline_and_keeps_alarms(self) -> None:
        self.production_json["status"] = {
            "alarm": ["\u8d85\u6e29\u4fdd\u62a4", "\u98ce\u673a\u8fc7\u8f7d"],
            "state": "\u901a\u8baf\u6545\u969c",
        }

        device = normalize_snapshot(self.production_json)["devices"][0]

        self.assertFalse(device["online"])
        self.assertEqual(device["run_state"], "OFFLINE")
        self.assertEqual(
            device["alarm"],
            "\u8d85\u6e29\u4fdd\u62a4\uff1b\u98ce\u673a\u8fc7\u8f7d",
        )
        self.assertEqual(
            device["alarms"],
            ["\u8d85\u6e29\u4fdd\u62a4", "\u98ce\u673a\u8fc7\u8f7d"],
        )

    def test_keeps_legacy_snapshot_compatible(self) -> None:
        legacy = {
            "source": "legacy_writer",
            "sequence": 9,
            "written_at": 123.0,
            "devices": [{"device_id": "CH-001", "current_temperature": 25.0}],
        }

        self.assertEqual(normalize_snapshot(legacy), legacy)

    def test_simulator_emits_the_production_root_shape(self) -> None:
        payload = build_production_payload(
            device_id="SIM-TEST-001",
            current_temperature=25,
            current_humidity=60,
            target_temperature=25,
            target_humidity=60,
            running=1,
            step=1,
            device_ip="192.168.1.102",
        )

        self.assertEqual(payload["device_id"], "SIM-TEST-001")
        self.assertNotIn("devices", payload)
        self.assertEqual(
            set(payload),
            {"DUT", "compressor", "device_id", "device_ip", "event", "mainData", "other", "program", "status", "time", "timeData"},
        )
        self.assertEqual(payload["mainData"]["TEMP_PV"], 25)
        self.assertEqual(payload["program"]["run"], 1)

    def test_python_memory_writer_uses_a_non_document_example_device_id(self) -> None:
        payload = build_device(0)

        self.assertEqual(payload["device_id"], "SIM-PY-001")
        self.assertNotEqual(payload["device_id"], "SIM-TEST-DEVICE-001")
        self.assertNotIn("devices", payload)


if __name__ == "__main__":
    unittest.main()
