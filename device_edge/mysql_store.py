"""MySQL persistence for local device settings."""

from __future__ import annotations

import os
from decimal import Decimal
from typing import Any

from .config import EdgeConfig


FIXED_VALUE_COLUMNS = (
    "temperature_target",
    "temperature_slope",
    "humidity_target",
    "humidity_slope",
    "runtime_hours",
    "runtime_minutes",
    "runtime_seconds",
)


class FixedValueStore:
    def __init__(self, config: EdgeConfig) -> None:
        self.config = config

    def _connect(self):
        try:
            import mysql.connector
        except ImportError as exc:
            raise RuntimeError("未安装 MySQL Python 驱动，请执行 python -m pip install -r device_edge/requirements.txt") from exc

        password = os.environ.get(self.config.database_password_env)
        if password is None:
            raise RuntimeError(f"未设置数据库密码环境变量：{self.config.database_password_env}")
        return mysql.connector.connect(
            host=self.config.database_host,
            port=self.config.database_port,
            database=self.config.database_name,
            user=self.config.database_user,
            password=password,
        )

    @staticmethod
    def _as_value(row: tuple[Any, ...] | None) -> dict[str, Any] | None:
        if row is None:
            return None
        value = dict(zip(("id", *FIXED_VALUE_COLUMNS, "created_at", "updated_at"), row))
        for key, item in value.items():
            if isinstance(item, Decimal):
                value[key] = float(item)
        for key in ("created_at", "updated_at"):
            if value[key] is not None:
                value[key] = value[key].isoformat(sep=" ")
        return value

    def get_fixed_value(self) -> dict[str, Any] | None:
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT id, temperature_target, temperature_slope, humidity_target, "
                "humidity_slope, runtime_hours, runtime_minutes, runtime_seconds, "
                "created_at, updated_at FROM fixed_value WHERE id = 1"
            )
            return self._as_value(cursor.fetchone())
        finally:
            connection.close()

    def save_fixed_value(self, value: dict[str, Any]) -> dict[str, Any]:
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO fixed_value (id, temperature_target, temperature_slope, "
                "humidity_target, humidity_slope, runtime_hours, runtime_minutes, runtime_seconds) "
                "VALUES (1, %s, %s, %s, %s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE temperature_target = VALUES(temperature_target), "
                "temperature_slope = VALUES(temperature_slope), humidity_target = VALUES(humidity_target), "
                "humidity_slope = VALUES(humidity_slope), runtime_hours = VALUES(runtime_hours), "
                "runtime_minutes = VALUES(runtime_minutes), runtime_seconds = VALUES(runtime_seconds)",
                tuple(value[column] for column in FIXED_VALUE_COLUMNS),
            )
            connection.commit()
        finally:
            connection.close()
        saved = self.get_fixed_value()
        if saved is None:
            raise RuntimeError("保存定值参数后未能读取记录")
        return saved
