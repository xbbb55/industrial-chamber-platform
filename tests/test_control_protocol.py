import unittest
import asyncio

from backend.memory_router import CommandResultUpload, command_results, upload_command_result
from device_edge.control_protocol import build_be_r, build_fe_w, normalize_command


class ControlProtocolTests(unittest.TestCase):
    def test_direct_commands_match_controller_spec(self) -> None:
        expected = {
            "Run": "START_TEST",
            "Stop": "STOP_TEST",
            "Hold": "HOLD_TEST",
            "Keep": "KEEP_TEST",
            "Jnmp": "SKIP_STEP",
            "BuzzerON": "BUZZER_ON",
            "BuzzerOFF": "BUZZER_OFF",
            "Reset": "RESET_ALARM",
        }
        for wire, internal in expected.items():
            self.assertEqual(normalize_command(wire), (wire, internal))

    def test_parameter_commands_and_prefix_commands_are_supported(self) -> None:
        self.assertEqual(normalize_command("RunMode=1")[1], "SET_RUN_MODE")
        self.assertEqual(normalize_command("DownloadProgram=3")[1], "DOWNLOAD_PROGRAM")
        self.assertEqual(normalize_command("fixed_value")[1], "FIXED_VALUE")

    def test_fe_w_and_be_r_shapes(self) -> None:
        when = "2026-07-22 15:30:53"
        self.assertEqual(build_fe_w("Run", when), {"command": "Run", "time": when})
        self.assertEqual(build_be_r("Run", when), {"successMessage": "Run", "time": when})

    def test_legacy_result_endpoint_returns_acceptance(self) -> None:
        command_results.clear()
        response = asyncio.run(upload_command_result(CommandResultUpload(
            edge_id="EDGE-TEST",
            command_id="CMD-TEST",
            device_id="CH-TEST",
            successMessage="Run",
        )))
        self.assertEqual(response["status"], "accepted")
        self.assertEqual(response["command_id"], "CMD-TEST")
        self.assertEqual(command_results["CMD-TEST"]["be_r"]["successMessage"], "Run")


if __name__ == "__main__":
    unittest.main()
