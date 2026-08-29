"""MySQL-backed account service shared by the HTTP entrypoints."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

SEED_USERNAME = os.getenv("AUTH_SEED_USERNAME", "admin")
SEED_PASSWORD = os.getenv("AUTH_SEED_PASSWORD", "admin123")
_tokens: dict[str, dict[str, Any]] = {}


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


def _connection():
    try:
        import mysql.connector
    except ImportError as exc:
        raise RuntimeError("未安装 MySQL Python 驱动，请执行 python -m pip install -r device_edge/requirements.txt") from exc
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        database=os.getenv("MYSQL_DATABASE", "HDQC"),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PWD", ""),
    )


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 240_000)
    return f"pbkdf2_sha256$240000${salt.hex()}${digest.hex()}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt_hex, digest_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds))
        return hmac.compare_digest(candidate.hex(), digest_hex)
    except (TypeError, ValueError):
        return False


def init_auth_db() -> None:
    connection = _connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS accounts (
                id INT PRIMARY KEY AUTO_INCREMENT,
                username VARCHAR(64) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                display_name VARCHAR(128) NOT NULL,
                role VARCHAR(64) NOT NULL,
                created_at DOUBLE NOT NULL
            )"""
        )
        exists_cursor = connection.cursor()
        exists_cursor.execute("SELECT 1 FROM accounts WHERE username = %s LIMIT 1", (SEED_USERNAME,))
        exists = exists_cursor.fetchone()
        if not exists:
            cursor.execute(
                "INSERT INTO accounts (username, password_hash, display_name, role, created_at) VALUES (%s, %s, %s, %s, %s)",
                (SEED_USERNAME, _hash_password(SEED_PASSWORD), "Admin User", "系统管理员", time.time()),
            )
        connection.commit()
    finally:
        connection.close()


def _public_account(row: dict[str, Any] | tuple[Any, ...]) -> dict[str, Any]:
    if not isinstance(row, dict):
        row = dict(zip(("username", "display_name", "role"), row))
    return {"username": row["username"], "display_name": row["display_name"], "role": row["role"]}


def build_auth_router() -> APIRouter:
    router = APIRouter(prefix="/api/auth", tags=["auth"])

    @router.post("/login")
    def login(request: LoginRequest) -> dict[str, Any]:
        init_auth_db()
        connection = _connection()
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM accounts WHERE username = %s LIMIT 1", (request.username.strip(),))
            row = cursor.fetchone()
        finally:
            connection.close()
        if not row or not _verify_password(request.password, row["password_hash"]):
            raise HTTPException(status_code=401, detail="账号名或密码错误")
        account = _public_account(row)
        token = secrets.token_urlsafe(32)
        _tokens[token] = account
        return {"access_token": token, "token_type": "bearer", "user": account}

    @router.get("/me")
    def me(token: Optional[str] = None) -> dict[str, Any]:
        if not token or token not in _tokens:
            raise HTTPException(status_code=401, detail="登录已失效")
        return {"user": _tokens[token]}

    return router
