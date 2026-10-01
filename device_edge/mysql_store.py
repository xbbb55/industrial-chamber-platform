"""MySQL persistence for local device settings."""

from __future__ import annotations

import os
import json
from datetime import datetime, timezone
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
    "TEMP_Collected",
    "TEMP_Corrected",
    "TEMP_Final",
    "HUMI_Collected",
    "HUMI_Corrected",
    "HUMI_Final",
)

PID_SETTING_COLUMNS = (
    *(f"HUMI_T{index}" for index in range(1, 4)),
    *(f"HUMI_H{index}" for index in range(1, 5)),
    *(f"TEMP_T{index}" for index in range(1, 5)),
    *(
        f"TEMP{group}_{metric}"
        for group in range(1, 5)
        for metric in ("P", "I", "D", "LBL", "MQ")
    ),
    *(
        f"HUMI{group}_{category}_{metric}"
        for group in range(1, 8)
        for category in ("T", "H")
        for metric in ("P", "I", "D", "LBL", "MQ")
    ),
)


def setting_changes(before: dict[str, Any] | None, after: dict[str, Any]) -> dict[str, Any]:
    previous = before or {}
    return {
        key: {"before": previous.get(key), "after": value}
        for key, value in after.items()
        if previous.get(key) != value
    }

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

HISTORY_RETENTION_OPTIONS = (30, 60, 90, 200, 300)


class EnvironmentalHistoryStore:
    """MySQL persistence for one-second environmental telemetry history."""

    def __init__(self, config: EdgeConfig) -> None:
        self.config = config
        self._last_retention_read = 0.0
        self._retention_days = 90

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
            use_pure=True,
        )

    @staticmethod
    def _ensure_tables(connection: Any) -> None:
        cursor = connection.cursor()
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS environmental_history (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                device_id VARCHAR(64) NOT NULL,
                edge_id VARCHAR(64) DEFAULT NULL,
                recorded_at DATETIME(3) NOT NULL,
                received_at DATETIME(3) NOT NULL,
                temperature DECIMAL(10,3) DEFAULT NULL,
                humidity DECIMAL(10,3) DEFAULT NULL,
                temperature_target DECIMAL(10,3) DEFAULT NULL,
                humidity_target DECIMAL(10,3) DEFAULT NULL,
                run_state VARCHAR(32) DEFAULT NULL,
                run_mode VARCHAR(32) DEFAULT NULL,
                communication_status VARCHAR(32) DEFAULT NULL,
                source VARCHAR(32) NOT NULL DEFAULT 'EDGE',
                quality VARCHAR(16) NOT NULL DEFAULT 'GOOD',
                raw_payload JSON DEFAULT NULL,
                PRIMARY KEY (id),
                UNIQUE KEY uq_environmental_history_device_time (device_id, recorded_at),
                KEY idx_environmental_history_recorded_at (recorded_at),
                KEY idx_environmental_history_device_received (device_id, received_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"""
        )
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS environmental_history_settings (
                id TINYINT UNSIGNED NOT NULL,
                retention_days SMALLINT UNSIGNED NOT NULL DEFAULT 90,
                updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
                PRIMARY KEY (id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"""
        )
        cursor.execute(
            "INSERT INTO environmental_history_settings (id, retention_days) VALUES (1, 90) ON DUPLICATE KEY UPDATE id = id"
        )

    def ensure_tables(self) -> None:
        connection = self._connect()
        try:
            self._ensure_tables(connection)
            connection.commit()
        finally:
            connection.close()

    def get_retention_days(self) -> int:
        connection = self._connect()
        try:
            self._ensure_tables(connection)
            cursor = connection.cursor()
            cursor.execute("SELECT retention_days FROM environmental_history_settings WHERE id = 1")
            row = cursor.fetchone()
            connection.commit()
            value = int(row[0]) if row else 90
            if value not in HISTORY_RETENTION_OPTIONS:
                value = 90
            self._retention_days = value
            self._last_retention_read = datetime.now().timestamp()
            return value
        finally:
            connection.close()

    def save_retention_days(self, retention_days: int) -> int:
        if retention_days not in HISTORY_RETENTION_OPTIONS:
            raise ValueError(f"数据保存时间必须是：{', '.join(map(str, HISTORY_RETENTION_OPTIONS))}天")
        connection = self._connect()
        try:
            self._ensure_tables(connection)
            cursor = connection.cursor()
            cursor.execute("UPDATE environmental_history_settings SET retention_days = %s WHERE id = 1", (retention_days,))
            connection.commit()
        finally:
            connection.close()
        self._retention_days = retention_days
        self._last_retention_read = datetime.now().timestamp()
        return retention_days

    def record_snapshot(self, snapshot: dict[str, Any], edge_id: str) -> None:
        devices = snapshot.get("devices") if isinstance(snapshot, dict) else None
        if not isinstance(devices, list):
            return
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        rows = []
        for device in devices:
            if not isinstance(device, dict):
                continue
            device_id = str(device.get("device_id") or "").strip()
            temperature = device.get("current_temperature")
            humidity = device.get("current_humidity")
            if not device_id or (temperature is None and humidity is None):
                continue
            try:
                recorded = datetime.fromtimestamp(float(device.get("updated_at") or snapshot.get("written_at") or datetime.now().timestamp()), timezone.utc).replace(tzinfo=None)
            except (TypeError, ValueError, OSError):
                recorded = now
            recorded = recorded.replace(microsecond=(recorded.microsecond // 1000000) * 1000000)
            rows.append((
                device_id, edge_id or None, recorded, now,
                temperature, humidity, device.get("target_temperature"), device.get("target_humidity"),
                device.get("run_state"), device.get("run_mode"),
                "ONLINE" if device.get("online", True) else "OFFLINE", "EDGE", "GOOD",
                json.dumps(device, ensure_ascii=False, separators=(",", ":"), default=str),
            ))
        if not rows:
            return
        connection = self._connect()
        try:
            self._ensure_tables(connection)
            cursor = connection.cursor()
            cursor.executemany(
                """INSERT INTO environmental_history
                (device_id, edge_id, recorded_at, received_at, temperature, humidity,
                 temperature_target, humidity_target, run_state, run_mode,
                 communication_status, source, quality, raw_payload)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE received_at = VALUES(received_at), temperature = VALUES(temperature),
                    humidity = VALUES(humidity), temperature_target = VALUES(temperature_target),
                    humidity_target = VALUES(humidity_target), run_state = VALUES(run_state),
                    run_mode = VALUES(run_mode), communication_status = VALUES(communication_status),
                    raw_payload = VALUES(raw_payload)""",
                rows,
            )
            retention_days = self._retention_days
            if datetime.now().timestamp() - self._last_retention_read >= 60:
                cursor.execute("SELECT retention_days FROM environmental_history_settings WHERE id = 1")
                configured = cursor.fetchone()
                retention_days = int(configured[0]) if configured else 90
                if retention_days not in HISTORY_RETENTION_OPTIONS:
                    retention_days = 90
                self._retention_days = retention_days
                self._last_retention_read = datetime.now().timestamp()
            cursor.execute(f"DELETE FROM environmental_history WHERE recorded_at < UTC_TIMESTAMP(3) - INTERVAL {int(retention_days)} DAY")
            connection.commit()
        finally:
            connection.close()

    def list_history(self, device_id: str, start_time: float | None = None, end_time: float | None = None, run_state: str | None = None, limit: int = 5000) -> list[dict[str, Any]]:
        connection = self._connect()
        try:
            self._ensure_tables(connection)
            cursor = connection.cursor(dictionary=True)
            clauses = ["device_id = %s"]
            values: list[Any] = [device_id]
            if start_time is not None:
                clauses.append("recorded_at >= FROM_UNIXTIME(%s)")
                values.append(start_time)
            if end_time is not None:
                clauses.append("recorded_at <= FROM_UNIXTIME(%s)")
                values.append(end_time)
            if run_state:
                clauses.append("run_state = %s")
                values.append(run_state)
            values.append(max(1, min(limit, 20000)))
            cursor.execute(
                "SELECT device_id, edge_id, recorded_at, received_at, temperature, humidity, temperature_target, humidity_target, run_state, run_mode, communication_status, quality FROM environmental_history WHERE "
                + " AND ".join(clauses) + " ORDER BY recorded_at ASC LIMIT %s",
                tuple(values),
            )
            items = cursor.fetchall()
            for item in items:
                for key in ("recorded_at", "received_at"):
                    if item.get(key) is not None:
                        item[key] = item[key].isoformat(sep=" ")
                for key in ("temperature", "humidity", "temperature_target", "humidity_target"):
                    if isinstance(item.get(key), Decimal):
                        item[key] = float(item[key])
            return items
        finally:
            connection.close()


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
            use_pure=True,
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
            use_pure=True,
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

    def get_other_setting(self) -> dict[str, Any] | None:
        return self._get_fields(OTHER_SETTING_COLUMNS)

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

    def get_pid_setting(self) -> dict[str, Any] | None:
        return self._get_fields(PID_SETTING_COLUMNS, "pid_set")

    def save_pid_setting(self, value: dict[str, Any]) -> dict[str, Any]:
        return self._save_fields(value, PID_SETTING_COLUMNS, "PID 参数", "pid_set")


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
            use_pure=True,
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
