import unittest
import os
import sys
from types import SimpleNamespace
from unittest.mock import patch

from pydantic import ValidationError

from backend import auth
from backend.auth import (
    ChangePasswordRequest,
    CreateAccountRequest,
    PERMISSION_DEVICE_COMMAND,
    ROLE_ADMIN,
    ROLE_ENGINEER,
    ROLE_SALES,
    ROLE_PERMISSIONS,
    _insert_operation_log,
    normalize_role,
    require_permission,
    validate_numeric_password,
)


class CapturingCursor:
    def __init__(self) -> None:
        self.statement = ""
        self.parameters = ()

    def execute(self, statement, parameters) -> None:
        self.statement = statement
        self.parameters = parameters


class AuthContractTests(unittest.TestCase):
    def test_control_center_database_settings_take_precedence(self) -> None:
        connector = SimpleNamespace(connect=lambda **kwargs: kwargs)
        mysql_module = SimpleNamespace(connector=connector)
        with patch.dict(
            sys.modules,
            {"mysql": mysql_module, "mysql.connector": connector},
        ), patch.dict(
            os.environ,
            {
                "MYSQL_HOST": "edge-db",
                "MYSQL_PORT": "3307",
                "MYSQL_DATABASE": "HDQC",
                "MYSQL_USER": "edge-user",
                "MYSQL_PWD": "edge-password",
                "CONTROL_CENTER_MYSQL_HOST": "control-db",
                "CONTROL_CENTER_MYSQL_PORT": "3308",
                "CONTROL_CENTER_MYSQL_DATABASE": "industrial_chamber_control_center",
                "CONTROL_CENTER_MYSQL_USER": "control-user",
                "CONTROL_CENTER_MYSQL_PASSWORD": "control-password",
            },
            clear=False,
        ):
            connection_args = auth._connection()

        self.assertEqual(connection_args["host"], "control-db")
        self.assertEqual(connection_args["port"], 3308)
        self.assertEqual(connection_args["database"], "industrial_chamber_control_center")
        self.assertEqual(connection_args["user"], "control-user")
        self.assertEqual(connection_args["password"], "control-password")

    def test_control_center_password_env_reference_is_supported(self) -> None:
        connector = SimpleNamespace(connect=lambda **kwargs: kwargs)
        mysql_module = SimpleNamespace(connector=connector)
        with patch.dict(
            sys.modules,
            {"mysql": mysql_module, "mysql.connector": connector},
        ), patch.dict(
            os.environ,
            {
                "CONTROL_CENTER_MYSQL_PASSWORD_ENV": "CONTROL_DB_SECRET",
                "CONTROL_DB_SECRET": "secret-from-env",
            },
            clear=False,
        ):
            connection_args = auth._connection()

        self.assertEqual(connection_args["password"], "secret-from-env")

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
        self.assertEqual(cursor.parameters[3], "DEVICE_COMMAND_QUEUED")
        self.assertEqual(cursor.parameters[4], "DEVICE")
        self.assertEqual(cursor.parameters[5], "下发设备命令：CHAMBER-01")
        self.assertNotIn("password", str(cursor.parameters).lower())

    def test_all_roles_temporarily_share_administrator_permissions(self) -> None:
        account = {"username": "engineer", "role": ROLE_ENGINEER}
        self.assertIs(require_permission(PERMISSION_DEVICE_COMMAND)(account), account)
        sales_account = {"username": "sales", "role": ROLE_SALES}
        self.assertIs(require_permission(PERMISSION_DEVICE_COMMAND)(sales_account), sales_account)
        self.assertEqual(ROLE_PERMISSIONS[ROLE_SALES], ROLE_PERMISSIONS[ROLE_ADMIN])


if __name__ == "__main__":
    unittest.main()
