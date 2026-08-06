"""Small SQLite persistence layer owned by the local device-edge service."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any


class SqliteStore:
    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(self._path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA busy_timeout=5000")
        self._initialize()

    def _initialize(self) -> None:
        with self._lock:
            self._connection.executescript("""
                CREATE TABLE IF NOT EXISTS telemetry_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_version INTEGER NOT NULL,
                    observed_at REAL NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS telemetry_snapshots_version
                    ON telemetry_snapshots(memory_version);
                CREATE TABLE IF NOT EXISTS command_records (
                    command_id TEXT PRIMARY KEY,
                    device_id TEXT NOT NULL,
                    command TEXT NOT NULL,
                    status TEXT NOT NULL,
                    operator_id TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    request_json TEXT NOT NULL,
                    result_json TEXT
                );
            """)
            self._connection.commit()

    def record_snapshot(self, memory_version: int, snapshot: dict[str, Any]) -> None:
        with self._lock:
            self._connection.execute(
                "INSERT OR IGNORE INTO telemetry_snapshots(memory_version, observed_at, payload_json) VALUES (?, ?, ?)",
                (memory_version, time.time(), json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"))),
            )
            self._connection.commit()

    def create_command(self, command: dict[str, Any]) -> None:
        now = time.time()
        with self._lock:
            self._connection.execute(
                """INSERT INTO command_records(command_id, device_id, command, status, operator_id, created_at, updated_at, request_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (command["command_id"], command["device_id"], command["command"], command["status"], command["operator_id"], now, now, json.dumps(command, ensure_ascii=False, separators=(",", ":"))),
            )
            self._connection.commit()

    def update_command(self, command_id: str, status: str, result: dict[str, Any]) -> None:
        with self._lock:
            self._connection.execute(
                "UPDATE command_records SET status = ?, updated_at = ?, result_json = ? WHERE command_id = ?",
                (status, time.time(), json.dumps(result, ensure_ascii=False, separators=(",", ":")), command_id),
            )
            self._connection.commit()

    def close(self) -> None:
        with self._lock:
            self._connection.close()
