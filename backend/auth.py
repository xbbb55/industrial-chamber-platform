"""MySQL-backed account, password, and role management APIs."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field, field_validator

SEED_USERNAME = os.getenv("AUTH_SEED_USERNAME", "admin")
SEED_PASSWORD = os.getenv("AUTH_SEED_PASSWORD", "12345")
ROLE_ADMIN = "ADMIN"
ROLE_ENGINEER = "ENGINEER"
ROLE_SALES = "SALES"
ROLE_LABELS = {
    ROLE_ADMIN: "管理员",
    ROLE_ENGINEER: "工程师",
    ROLE_SALES: "销售",
}
_tokens: dict[str, dict[str, Any]] = {}


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validate_numeric_password(value)


class CreateAccountRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    display_name: str = Field(min_length=1, max_length=128)
    password: str = Field(max_length=128)
    role: Literal["ADMIN", "ENGINEER", "SALES"] = ROLE_ENGINEER

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_numeric_password(value)


class UpdateAccountRoleRequest(BaseModel):
    role: Literal["ADMIN", "ENGINEER", "SALES"]


def validate_numeric_password(value: str) -> str:
    if len(value) < 5 or not value.isdigit():
        raise ValueError("密码必须至少为 5 位数字")
    return value


def normalize_role(value: Any) -> str:
    role = str(value or "").strip().upper()
    if role in ROLE_LABELS:
        return role
    if role in {"管理员", "系统管理员", "ADMINISTRATOR"}:
        return ROLE_ADMIN
    if role in {"工程师", "ENGINEER"}:
        return ROLE_ENGINEER
    if role in {"销售", "SALES"}:
        return ROLE_SALES
    return ROLE_ENGINEER


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
                permission_group VARCHAR(64) NULL,
                created_at DOUBLE NOT NULL
            )"""
        )
        cursor.execute("SHOW COLUMNS FROM accounts LIKE 'permission_group'")
        if cursor.fetchone() is None:
            cursor.execute("ALTER TABLE accounts ADD COLUMN permission_group VARCHAR(64) NULL AFTER role")
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS operation_logs (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                account_id INT NOT NULL,
                action_type VARCHAR(64) NOT NULL,
                target_type VARCHAR(64) NULL,
                target_id VARCHAR(128) NULL,
                details TEXT NULL,
                created_at DOUBLE NOT NULL,
                INDEX idx_operation_logs_account_created_at (account_id, created_at),
                CONSTRAINT fk_operation_logs_account
                    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE RESTRICT
            ) ENGINE=InnoDB"""
        )
        exists_cursor = connection.cursor()
        exists_cursor.execute("SELECT 1 FROM accounts WHERE username = %s LIMIT 1", (SEED_USERNAME,))
        if not exists_cursor.fetchone():
            cursor.execute(
                "INSERT INTO accounts (username, password_hash, display_name, role, created_at) VALUES (%s, %s, %s, %s, %s)",
                (SEED_USERNAME, _hash_password(SEED_PASSWORD), "Admin User", ROLE_ADMIN, time.time()),
            )
        cursor.execute("UPDATE accounts SET role = %s WHERE username = %s OR role IN ('系统管理员', '管理员', 'ADMINISTRATOR')", (ROLE_ADMIN, SEED_USERNAME))
        cursor.execute("UPDATE accounts SET role = %s WHERE role NOT IN (%s, %s, %s)", (ROLE_ENGINEER, ROLE_ADMIN, ROLE_ENGINEER, ROLE_SALES))
        cursor.execute("UPDATE accounts SET permission_group = role WHERE permission_group IS NULL OR permission_group = '' OR permission_group NOT IN (%s, %s, %s)", (ROLE_ADMIN, ROLE_ENGINEER, ROLE_SALES))
        connection.commit()
    finally:
        connection.close()


def _public_account(row: dict[str, Any] | tuple[Any, ...]) -> dict[str, Any]:
    if not isinstance(row, dict):
        row = dict(zip(("username", "display_name", "role", "created_at"), row))
    role = normalize_role(row.get("permission_group") or row.get("role"))
    return {
        "username": row["username"],
        "display_name": row["display_name"],
        "role": role,
        "role_label": ROLE_LABELS[role],
        "created_at": row.get("created_at"),
    }


def _insert_operation_log(
    cursor: Any,
    account_id: int,
    action_type: str,
    *,
    target_type: str | None = None,
    target_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    cursor.execute(
        "INSERT INTO operation_logs (account_id, action_type, target_type, target_id, details, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
        (account_id, action_type, target_type, target_id, json.dumps(details, ensure_ascii=False, separators=(",", ":")) if details else None, time.time()),
    )


def record_operation(
    account: dict[str, Any],
    action_type: str,
    *,
    target_type: str | None = None,
    target_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Write an auditable operation record without exposing credentials or tokens."""
    init_auth_db()
    connection = _connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT id FROM accounts WHERE username = %s LIMIT 1", (account["username"],))
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("操作账户不存在，无法写入操作日志")
        _insert_operation_log(cursor, row["id"], action_type, target_type=target_type, target_id=target_id, details=details)
        connection.commit()
    finally:
        connection.close()


def _token_from_authorization(authorization: Optional[str]) -> str:
    scheme, _, token = str(authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="请先登录")
    return token


def current_account(authorization: Optional[str] = Header(default=None)) -> dict[str, Any]:
    account = _tokens.get(_token_from_authorization(authorization))
    if account is None:
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录")
    return account


def _require_admin(account: dict[str, Any] = Depends(current_account)) -> dict[str, Any]:
    if account["role"] != ROLE_ADMIN:
        raise HTTPException(status_code=403, detail="仅管理员可以管理用户")
    return account


def _invalidate_user_tokens(username: str) -> None:
    for token, account in list(_tokens.items()):
        if account["username"] == username:
            del _tokens[token]


def build_auth_router() -> APIRouter:
    router = APIRouter(prefix="/api/auth", tags=["auth"])

    @router.post("/login")
    def login(request: LoginRequest) -> dict[str, Any]:
        init_auth_db()
        connection = _connection()
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT id, username, password_hash, display_name, role, permission_group, created_at FROM accounts WHERE username = %s LIMIT 1", (request.username.strip(),))
            row = cursor.fetchone()
            if not row or not _verify_password(request.password, row["password_hash"]):
                raise HTTPException(status_code=401, detail="账号名或密码错误")
            _insert_operation_log(cursor, row["id"], "AUTH_LOGIN", target_type="account", target_id=row["username"])
            connection.commit()
        finally:
            connection.close()
        account = _public_account(row)
        token = secrets.token_urlsafe(32)
        _tokens[token] = account
        return {"access_token": token, "token_type": "bearer", "user": account}

    @router.get("/me")
    def me(account: dict[str, Any] = Depends(current_account)) -> dict[str, Any]:
        return {"user": account}

    @router.put("/password")
    def change_password(request: ChangePasswordRequest, account: dict[str, Any] = Depends(current_account)) -> dict[str, str]:
        init_auth_db()
        connection = _connection()
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT id, password_hash FROM accounts WHERE username = %s LIMIT 1", (account["username"],))
            row = cursor.fetchone()
            if not row or not _verify_password(request.current_password, row["password_hash"]):
                raise HTTPException(status_code=400, detail="当前密码不正确")
            if request.current_password == request.new_password:
                raise HTTPException(status_code=400, detail="新密码不能与当前密码相同")
            cursor.execute("UPDATE accounts SET password_hash = %s WHERE username = %s", (_hash_password(request.new_password), account["username"]))
            _insert_operation_log(cursor, row["id"], "AUTH_PASSWORD_CHANGED", target_type="account", target_id=account["username"])
            connection.commit()
        finally:
            connection.close()
        _invalidate_user_tokens(account["username"])
        return {"message": "密码已更新，请重新登录"}

    @router.get("/users")
    def list_users(_: dict[str, Any] = Depends(_require_admin)) -> dict[str, list[dict[str, Any]]]:
        init_auth_db()
        connection = _connection()
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT username, display_name, role, permission_group, created_at FROM accounts ORDER BY created_at ASC, username ASC")
            users = [_public_account(row) for row in cursor.fetchall()]
        finally:
            connection.close()
        return {"users": users}

    @router.post("/users", status_code=201)
    def create_user(request: CreateAccountRequest, actor: dict[str, Any] = Depends(_require_admin)) -> dict[str, dict[str, Any]]:
        init_auth_db()
        connection = _connection()
        try:
            cursor = connection.cursor(dictionary=True)
            created_at = time.time()
            try:
                cursor.execute("SELECT id FROM accounts WHERE username = %s LIMIT 1", (actor["username"],))
                actor_row = cursor.fetchone()
                if actor_row is None:
                    raise RuntimeError("操作账户不存在，无法写入操作日志")
                cursor.execute(
                    "INSERT INTO accounts (username, password_hash, display_name, role, permission_group, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
                    (request.username, _hash_password(request.password), request.display_name, request.role, request.role, created_at),
                )
                _insert_operation_log(cursor, actor_row["id"], "ACCOUNT_CREATED", target_type="account", target_id=request.username, details={"permission_group": request.role})
                connection.commit()
            except Exception as exc:
                connection.rollback()
                if getattr(exc, "errno", None) == 1062:
                    raise HTTPException(status_code=409, detail="该账户名已存在") from exc
                raise
        finally:
            connection.close()
        return {"user": _public_account({"username": request.username, "display_name": request.display_name, "role": request.role, "created_at": created_at})}

    @router.put("/users/{username}/role")
    def update_user_role(username: str, request: UpdateAccountRoleRequest, actor: dict[str, Any] = Depends(_require_admin)) -> dict[str, dict[str, Any]]:
        init_auth_db()
        connection = _connection()
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT id FROM accounts WHERE username = %s LIMIT 1", (actor["username"],))
            actor_row = cursor.fetchone()
            if actor_row is None:
                raise RuntimeError("操作账户不存在，无法写入操作日志")
            cursor.execute("UPDATE accounts SET role = %s, permission_group = %s WHERE username = %s", (request.role, request.role, username))
            cursor.execute("SELECT id, username, display_name, role, permission_group, created_at FROM accounts WHERE username = %s", (username,))
            row = cursor.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="用户不存在")
            _insert_operation_log(cursor, actor_row["id"], "ACCOUNT_PERMISSION_GROUP_UPDATED", target_type="account", target_id=username, details={"permission_group": request.role})
            connection.commit()
        finally:
            connection.close()
        _invalidate_user_tokens(username)
        return {"user": _public_account(row)}

    return router
