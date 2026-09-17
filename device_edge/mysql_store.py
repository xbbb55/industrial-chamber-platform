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

OPERATION_SETTING_COLUMNS = (
    "airTEMP_H",
    "airTEMP_L",
    "dutTEMP_H",
    "dutTEMP_L",
    "dutModeAir_H",
    "dutModeAir_L",
)

OTHER_SETTING_COLUMNS = (
    "dutControl",
    "dutSel",
    "DM9",
    "waitTEMP",
    "waitHUMI",
    "event",
    "powerRestoration",
    "afterShutdow",
)

SYSTEM_BASIC_SETTING_COLUMNS = (
    "TEMP_OP_H",
    "TEMP_OP_L",
    "HUMI_OP_H",
    "HUMI_OP_L",
    "HUMI_AirOP_H",
    "HUMI_AirOP_L",
    "heatingUpDownHz",
    "constantTEMPHz",
    "HumiHeatHz",
    "otherHz",
)

CORRECTION_SETTING_COLUMNS = (
    "TEMP_Area1",
    "TEMP_Area2",
    "TEMP_Area3",
    "TEMP_Area4",
    "TEMP_Corrected1",
    "TEMP_Corrected2",
    "TEMP_Corrected3",
    "TEMP_Corrected4",
    "TEMP_Correction",
    "HUMI_Area1",
    "HUMI_Area2",
    "HUMI_Area3",
    "HUMI_Area4",
    "HUMI_Corrected1",
    "HUMI_Corrected2",
    "HUMI_Corrected3",
    "HUMI_Corrected4",
    "HUMI_Correction",
    *(
        f"DUT{channel}_{stage}"
        for channel in range(1, 11)
        for stage in ("Collected", "Corrected", "Final")
    ),
)

PROGRAM_GROUP_COLUMNS = (
    "pro_no",
    "name",
    "total_time",
    "loop1_start",
    "loop1_end",
    "loop1_times",
    "loop2_start",
    "loop2_end",
    "loop2_times",
    "loop3_start",
    "loop3_end",
    "loop3_times",
    "loop4_start",
    "loop4_end",
    "loop4_times",
    "full_cycle",
    "link_no",
)

PROGRAM_STEP_COLUMNS = (
    "pro_no",
    "step_no",
    "time",
    "temp",
    "humi",
    "pressure",
    "event_bits",
    "space",
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
            if key in value and value[key] is not None:
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


class OperationSettingStore:
    """Persistence for the operation settings shown in 操作设定.

    ``operationsetting`` is an existing aggregate table owned by the device
    software. The store updates only the explicitly supplied mapped columns;
    unrelated operation-setting columns remain unchanged.
    """

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
    def _as_value(row: tuple[Any, ...] | None, columns: tuple[str, ...] = OPERATION_SETTING_COLUMNS) -> dict[str, Any] | None:
        if row is None:
            return None
        value = dict(zip(columns, row))
        for key, item in value.items():
            if isinstance(item, Decimal):
                value[key] = float(item)
        for key in ("created_at", "updated_at"):
            if key in value and value[key] is not None:
                value[key] = value[key].isoformat(sep=" ")
        return value

    @staticmethod
    def _ensure_table(connection: Any, required_columns: tuple[str, ...], table: str = "operationsetting") -> set[str]:
        cursor = connection.cursor()
        try:
            cursor.execute(f"SHOW COLUMNS FROM {table}")
        except Exception as exc:
            raise RuntimeError(f"数据库中不存在 {table} 表，请先由设备数据库脚本创建") from exc
        existing = {str(row[0]).lower() for row in cursor.fetchall()}
        required = {column.lower() for column in required_columns}
        missing = sorted(required - existing)
        if missing:
            raise RuntimeError(f"{table} 表缺少字段：{', '.join(missing)}")
        return existing

    def _get_fields(self, columns: tuple[str, ...], table: str = "operationsetting") -> dict[str, Any] | None:
        connection = self._connect()
        try:
            self._ensure_table(connection, columns, table)
            cursor = connection.cursor()
            cursor.execute(f"SELECT {', '.join(columns)} FROM {table} LIMIT 1")
            return self._as_value(cursor.fetchone(), columns)
        finally:
            connection.close()

    def _save_fields(self, value: dict[str, Any], allowed_columns: tuple[str, ...], label: str, table: str = "operationsetting") -> dict[str, Any]:
        connection = self._connect()
        try:
            self._ensure_table(connection, allowed_columns, table)
            cursor = connection.cursor()
            columns_to_save = tuple(column for column in allowed_columns if column in value and value[column] is not None)
            if not columns_to_save:
                raise ValueError(f"未提供可保存的{label}字段")
            values = tuple(value[column] for column in columns_to_save)
            columns = ", ".join(columns_to_save)
            placeholders = ", ".join(["%s"] * len(columns_to_save))
            cursor.execute(f"SELECT 1 FROM {table} LIMIT 1")
            if cursor.fetchone() is None:
                cursor.execute(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", values)
            else:
                assignments = ", ".join(f"{column} = %s" for column in columns_to_save)
                cursor.execute(f"UPDATE {table} SET {assignments} LIMIT 1", values)
            connection.commit()
        finally:
            connection.close()
        saved = self._get_fields(allowed_columns, table)
        if saved is None:
            raise RuntimeError(f"保存{label}后未能读取记录")
        return saved

    def get_operation_setting(self) -> dict[str, Any] | None:
        return self._get_fields((*OPERATION_SETTING_COLUMNS, *OTHER_SETTING_COLUMNS))

    def save_operation_setting(self, value: dict[str, Any]) -> dict[str, Any]:
        return self._save_fields(value, (*OPERATION_SETTING_COLUMNS, *OTHER_SETTING_COLUMNS), "操作设定")

    def save_other_setting(self, value: dict[str, Any]) -> dict[str, Any]:
        return self._save_fields(value, OTHER_SETTING_COLUMNS, "其他设定")

    def get_system_basic_setting(self) -> dict[str, Any] | None:
        return self._get_fields(SYSTEM_BASIC_SETTING_COLUMNS)

    def save_system_basic_setting(self, value: dict[str, Any]) -> dict[str, Any]:
        return self._save_fields(value, SYSTEM_BASIC_SETTING_COLUMNS, "系统基础参数")

    def get_correction_setting(self) -> dict[str, Any] | None:
        return self._get_fields(CORRECTION_SETTING_COLUMNS, "correction")

    def save_correction_setting(self, value: dict[str, Any]) -> dict[str, Any]:
        return self._save_fields(value, CORRECTION_SETTING_COLUMNS, "测量校正参数", "correction")


class ProgramStore:
    """Persistence for program groups and their ordered step definitions."""

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
    def _normalize_row(row: tuple[Any, ...] | None, columns: tuple[str, ...]) -> dict[str, Any] | None:
        if row is None:
            return None
        value = dict(zip(columns, row))
        for key, item in value.items():
            if isinstance(item, Decimal):
                value[key] = float(item)
        return value

    @staticmethod
    def _ensure_tables(connection: Any) -> None:
        cursor = connection.cursor()
        for table, required in (("program_group", PROGRAM_GROUP_COLUMNS), ("program_step", PROGRAM_STEP_COLUMNS)):
            try:
                cursor.execute(f"SHOW COLUMNS FROM {table}")
            except Exception as exc:
                raise RuntimeError(f"数据库中不存在 {table} 表，请先由设备数据库脚本创建") from exc
            existing = {str(row[0]).lower() for row in cursor.fetchall()}
            missing = sorted(set(column.lower() for column in required) - existing)
            if missing:
                raise RuntimeError(f"{table} 表缺少字段：{', '.join(missing)}")

    def list_program_groups(self) -> list[dict[str, Any]]:
        connection = self._connect()
        try:
            self._ensure_tables(connection)
            cursor = connection.cursor()
            cursor.execute(
                "SELECT g.pro_no, g.name, g.total_time, g.loop1_start, g.loop1_end, g.loop1_times, "
                "g.loop2_start, g.loop2_end, g.loop2_times, g.loop3_start, g.loop3_end, g.loop3_times, "
                "g.loop4_start, g.loop4_end, g.loop4_times, g.full_cycle, g.link_no, COUNT(s.step_no) "
                "FROM program_group g LEFT JOIN program_step s ON s.pro_no = g.pro_no "
                "GROUP BY g.pro_no, g.name, g.total_time, g.loop1_start, g.loop1_end, g.loop1_times, "
                "g.loop2_start, g.loop2_end, g.loop2_times, g.loop3_start, g.loop3_end, g.loop3_times, "
                "g.loop4_start, g.loop4_end, g.loop4_times, g.full_cycle, g.link_no ORDER BY g.pro_no"
            )
            groups: list[dict[str, Any]] = []
            for row in cursor.fetchall():
                value = self._normalize_row(row[:-1], PROGRAM_GROUP_COLUMNS) or {}
                value["step_count"] = int(row[-1] or 0)
                groups.append(value)
            return groups
        finally:
            connection.close()

    def next_program_number(self) -> int:
        connection = self._connect()
        try:
            self._ensure_tables(connection)
            cursor = connection.cursor()
            cursor.execute("SELECT COALESCE(MAX(pro_no), 0) + 1 FROM program_group")
            return int(cursor.fetchone()[0])
        finally:
            connection.close()

    def get_program(self, pro_no: int) -> dict[str, Any] | None:
        connection = self._connect()
        try:
            self._ensure_tables(connection)
            cursor = connection.cursor()
            cursor.execute(
                "SELECT " + ", ".join(PROGRAM_GROUP_COLUMNS) + " FROM program_group WHERE pro_no = %s LIMIT 1",
                (pro_no,),
            )
            group = self._normalize_row(cursor.fetchone(), PROGRAM_GROUP_COLUMNS)
            if group is None:
                return None
            cursor.execute(
                "SELECT " + ", ".join(PROGRAM_STEP_COLUMNS) + " FROM program_step "
                "WHERE pro_no = %s ORDER BY CAST(step_no AS UNSIGNED), step_no",
                (pro_no,),
            )
            group["steps"] = [self._normalize_row(row, PROGRAM_STEP_COLUMNS) for row in cursor.fetchall()]
            group["step_count"] = len(group["steps"])
            return group
        finally:
            connection.close()

    def save_program(self, value: dict[str, Any]) -> dict[str, Any]:
        if value.get("pro_no") is None:
            raise ValueError("程序组号必须由服务分配")
        pro_no = int(value["pro_no"])
        steps = value.get("steps") or []
        connection = self._connect()
        try:
            self._ensure_tables(connection)
            cursor = connection.cursor()
            cursor.execute("SELECT 1 FROM program_group WHERE pro_no = %s LIMIT 1", (pro_no,))
            exists = cursor.fetchone() is not None
            existing_group = None
            if exists:
                cursor.execute(
                    "SELECT " + ", ".join(PROGRAM_GROUP_COLUMNS) + " FROM program_group WHERE pro_no = %s LIMIT 1",
                    (pro_no,),
                )
                existing_group = self._normalize_row(cursor.fetchone(), PROGRAM_GROUP_COLUMNS) or {}
            group_value = {
                column: (value.get(column) if value.get(column) is not None else (existing_group.get(column, 0) if existing_group else 0))
                for column in PROGRAM_GROUP_COLUMNS
            }
            group_value["pro_no"] = pro_no
            if not exists:
                placeholders = ", ".join(["%s"] * len(PROGRAM_GROUP_COLUMNS))
                cursor.execute(
                    f"INSERT INTO program_group ({', '.join(PROGRAM_GROUP_COLUMNS)}) VALUES ({placeholders})",
                    tuple(group_value[column] for column in PROGRAM_GROUP_COLUMNS),
                )
            else:
                assignments = ", ".join(f"{column} = %s" for column in PROGRAM_GROUP_COLUMNS if column != "pro_no")
                cursor.execute(
                    f"UPDATE program_group SET {assignments} WHERE pro_no = %s",
                    tuple(group_value[column] for column in PROGRAM_GROUP_COLUMNS if column != "pro_no") + (pro_no,),
                )
            cursor.execute("DELETE FROM program_step WHERE pro_no = %s", (pro_no,))
            if steps:
                placeholders = ", ".join(["%s"] * len(PROGRAM_STEP_COLUMNS))
                cursor.executemany(
                    f"INSERT INTO program_step ({', '.join(PROGRAM_STEP_COLUMNS)}) VALUES ({placeholders})",
                    [tuple(pro_no if column == "pro_no" else step[column] for column in PROGRAM_STEP_COLUMNS) for step in steps],
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        saved = self.get_program(pro_no)
        if saved is None:
            raise RuntimeError("保存程序后未能读取记录")
        return saved

    def delete_program(self, pro_no: int) -> None:
        connection = self._connect()
        try:
            self._ensure_tables(connection)
            cursor = connection.cursor()
            cursor.execute("DELETE FROM program_step WHERE pro_no = %s", (pro_no,))
            cursor.execute("DELETE FROM program_group WHERE pro_no = %s", (pro_no,))
            if cursor.rowcount == 0:
                raise KeyError(f"程序组 {pro_no} 不存在")
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
