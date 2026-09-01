import unittest

from pydantic import ValidationError

from backend.auth import ChangePasswordRequest, CreateAccountRequest, ROLE_ADMIN, ROLE_ENGINEER, _insert_operation_log, normalize_role, validate_numeric_password


class CapturingCursor:
    def __init__(self) -> None:
        self.statement = ""
        self.parameters = ()

    def execute(self, statement, parameters) -> None:
        self.statement = statement
        self.parameters = parameters


class AuthContractTests(unittest.TestCase):
    def test_existing_admin_role_is_migrated_to_admin(self) -> None:
        self.assertEqual(normalize_role("系统管理员"), ROLE_ADMIN)
        self.assertEqual(normalize_role("unrecognized"), ROLE_ENGINEER)

    def test_password_must_be_at_least_five_digits(self) -> None:
        self.assertEqual(validate_numeric_password("12345"), "12345")
        with self.assertRaises(ValueError):
            validate_numeric_password("1234")
        with self.assertRaises(ValueError):
            validate_numeric_password("12ab5")

    def test_password_requests_enforce_numeric_rule(self) -> None:
        ChangePasswordRequest(current_password="old", new_password="12345")
        CreateAccountRequest(username="engineer.01", display_name="工程师", password="98765")
        with self.assertRaises(ValidationError):
            ChangePasswordRequest(current_password="old", new_password="abcd5")

    def test_operation_log_is_bound_to_account_and_excludes_credentials(self) -> None:
        cursor = CapturingCursor()
        _insert_operation_log(cursor, 42, "DEVICE_COMMAND_QUEUED", target_type="device", target_id="CHAMBER-01", details={"command": "Run"})
        self.assertIn("operation_logs", cursor.statement)
        self.assertEqual(cursor.parameters[0], 42)
        self.assertEqual(cursor.parameters[1], "DEVICE_COMMAND_QUEUED")
        self.assertNotIn("password", str(cursor.parameters).lower())


if __name__ == "__main__":
    unittest.main()
