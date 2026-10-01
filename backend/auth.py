"""MySQL-backed account, password, and role management APIs."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
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
# Authorization is derived from the authenticated account's permission group.
# Keep this matrix in one place so every API enforces the same policy.
PERMISSION_DEVICE_VIEW = "device.view"
PERMISSION_DEVICE_COMMAND = "device.command"
PERMISSION_SETTINGS_WRITE = "settings.write"
PERMISSION_USER_MANAGE = "user.manage"
ADMIN_PERMISSIONS = frozenset({
    PERMISSION_DEVICE_VIEW,
    PERMISSION_DEVICE_COMMAND,
    PERMISSION_SETTINGS_WRITE,
    PERMISSION_USER_MANAGE,
})
# 当前阶段所有权限组沿用管理员业务权限；保留独立角色，便于后续收紧矩阵。
ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    role: ADMIN_PERMISSIONS for role in ROLE_LABELS
}
_tokens: dict[str, dict[str, Any]] = {}
_auth_schema_ready = False
_auth_schema_lock = threading.Lock()

ACTION_METADATA: dict[str, tuple[str, str]] = {
    "AUTH_LOGIN": ("AUTH", "登录系统"),
    "AUTH_LOGOUT": ("AUTH", "退出系统"),
    "AUTH_PASSWORD_CHANGED": ("AUTH", "修改登录密码"),
    "DEVICE_COMMAND_QUEUED": ("DEVICE", "下发设备命令"),
    "DEVICE_COMMAND_REQUESTED": ("DEVICE", "请求设备命令"),
    "DEVICE_START_REQUESTED": ("DEVICE", "启动设备"),
    "DEVICE_STOP_REQUESTED": ("DEVICE", "停止设备"),
    "DEVICE_HOLD_REQUESTED": ("DEVICE", "保持设备运行"),
    "DEVICE_SKIP_STEP_REQUESTED": ("DEVICE", "跳过当前步骤"),
    "FIXED_VALUE_SETTINGS_UPDATED": ("SETTINGS", "修改定值参数"),
    "OPERATION_SETTINGS_UPDATED": ("SETTINGS", "修改操作设定"),
    "OTHER_OPERATION_SETTINGS_UPDATED": ("SETTINGS", "修改其他操作设定"),
    "SYSTEM_BASIC_SETTINGS_UPDATED": ("SETTINGS", "修改基础参数"),
    "CORRECTION_SETTINGS_UPDATED": ("SETTINGS", "修改测量校正参数"),
    "PID_SETTINGS_UPDATED": ("SETTINGS", "修改 PID 参数"),
    "PROGRAM_CREATED": ("PROGRAM", "新建程序"),
    "PROGRAM_UPDATED": ("PROGRAM", "修改程序"),
    "PROGRAM_DELETED": ("PROGRAM", "删除程序"),
    "PROGRAM_DOWNLOADED": ("DOWNLOAD", "下载程序"),
    "HISTORY_EXPORTED": ("DOWNLOAD", "导出历史数据"),
    "OPERATION_LOG_EXPORTED": ("DOWNLOAD", "导出操作日志"),
    "ACCOUNT_CREATED": ("ACCOUNT", "创建账户"),
    "ACCOUNT_PERMISSION_GROUP_UPDATED": ("ACCOUNT", "修改账户权限"),
}
ACTION_CATEGORY_LABELS = {
    "AUTH": "登录认证",
    "DEVICE": "设备控制",
    "SETTINGS": "参数设置",
    "PROGRAM": "程序管理",
    "DOWNLOAD": "下载导出",
    "ACCOUNT": "账户管理",
    "OTHER": "其他操作",
}


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
        # PyInstaller does not reliably load mysql-connector's native C
        # extension from a portable bundle.  Pure Python mode uses the same
        # wire protocol and keeps source and frozen deployments consistent.
        use_pure=True,
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
    global _auth_schema_ready
    if _auth_schema_ready:
        return
    with _auth_schema_lock:
        if _auth_schema_ready:
            return
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
                    username VARCHAR(64) NULL,
                    display_name VARCHAR(128) NULL,
                    action_type VARCHAR(64) NOT NULL,
                    action_category VARCHAR(32) NULL,
                    action_summary VARCHAR(255) NULL,
                    target_type VARCHAR(64) NULL,
                    target_id VARCHAR(128) NULL,
                    device_id VARCHAR(128) NULL,
                    module_code VARCHAR(64) NULL,
                    result_status VARCHAR(16) NOT NULL DEFAULT 'SUCCESS',
                    details TEXT NULL,
                    request_id VARCHAR(64) NULL,
                    ip_address VARCHAR(45) NULL,
                    user_agent VARCHAR(512) NULL,
                    created_at DOUBLE NOT NULL,
                    occurred_at DATETIME(3) NULL,
                    INDEX idx_operation_logs_account_created_at (account_id, created_at),
                    INDEX idx_operation_logs_created_at (created_at),
                    INDEX idx_operation_logs_action_created_at (action_type, created_at),
                    CONSTRAINT fk_operation_logs_account
                        FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE RESTRICT
                ) ENGINE=InnoDB"""
            )

            cursor.execute("SHOW COLUMNS FROM operation_logs")
            existing_columns = {row["Field"] for row in cursor.fetchall()}
            added_columns = {
                "username": "VARCHAR(64) NULL AFTER account_id",
                "display_name": "VARCHAR(128) NULL AFTER username",
                "action_category": "VARCHAR(32) NULL AFTER action_type",
                "action_summary": "VARCHAR(255) NULL AFTER action_category",
                "device_id": "VARCHAR(128) NULL AFTER target_id",
                "module_code": "VARCHAR(64) NULL AFTER device_id",
                "result_status": "VARCHAR(16) NOT NULL DEFAULT 'SUCCESS' AFTER module_code",
                "request_id": "VARCHAR(64) NULL AFTER details",
                "ip_address": "VARCHAR(45) NULL AFTER request_id",
                "user_agent": "VARCHAR(512) NULL AFTER ip_address",
                "occurred_at": "DATETIME(3) NULL AFTER created_at",
            }
            for column, definition in added_columns.items():
                if column not in existing_columns:
                    cursor.execute(f"ALTER TABLE operation_logs ADD COLUMN `{column}` {definition}")

            cursor.execute("SHOW INDEX FROM operation_logs")
            existing_indexes = {row["Key_name"] for row in cursor.fetchall()}
            indexes = {
                "idx_operation_logs_created_at": "created_at",
                "idx_operation_logs_action_created_at": "action_type, created_at",
                "idx_operation_logs_device_created_at": "device_id, created_at",
                "idx_operation_logs_module_created_at": "module_code, created_at",
            }
            for index_name, columns in indexes.items():
                if index_name not in existing_indexes:
                    cursor.execute(f"CREATE INDEX `{index_name}` ON operation_logs ({columns})")

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
            cursor.execute(
                """UPDATE operation_logs logs
                   JOIN accounts account ON account.id = logs.account_id
                   SET logs.username = COALESCE(logs.username, account.username),
                       logs.display_name = COALESCE(logs.display_name, account.display_name),
                       logs.result_status = COALESCE(logs.result_status, 'SUCCESS'),
                       logs.occurred_at = COALESCE(logs.occurred_at, FROM_UNIXTIME(logs.created_at))"""
            )
            cursor.execute("UPDATE operation_logs SET action_category = 'OTHER' WHERE action_category IS NULL OR action_category = ''")
            cursor.execute("UPDATE operation_logs SET action_summary = action_type WHERE action_summary IS NULL OR action_summary = ''")
            for action_type, (category, summary) in ACTION_METADATA.items():
                cursor.execute(
                    "UPDATE operation_logs SET action_category = %s, action_summary = %s WHERE action_type = %s",
                    (category, summary, action_type),
                )
            connection.commit()
            _auth_schema_ready = True
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
        "permissions": sorted(ROLE_PERMISSIONS[role]),
        "created_at": row.get("created_at"),
    }


def _insert_operation_log(
    cursor: Any,
    account_id: int,
    action_type: str,
    *,
    username: str = "",
    display_name: str = "",
    target_type: str | None = None,
    target_id: str | None = None,
    details: dict[str, Any] | None = None,
    result_status: str = "SUCCESS",
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    category, summary = ACTION_METADATA.get(action_type, ("OTHER", action_type))
    if target_id and target_type in {"device", "program"}:
        summary = f"{summary}：{target_id}"
    device_id = target_id if target_type == "device" else None
    module_code = target_id if target_type == "settings" else None
    cursor.execute(
        """INSERT INTO operation_logs (
               account_id, username, display_name, action_type, action_category, action_summary,
               target_type, target_id, device_id, module_code, result_status, details,
               request_id, ip_address, user_agent, created_at, occurred_at
           ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, UTC_TIMESTAMP(3))""",
        (
            account_id,
            username,
            display_name,
            action_type,
            category,
            summary,
            target_type,
            target_id,
            device_id,
            module_code,
            result_status,
            json.dumps(details, ensure_ascii=False, separators=(",", ":")) if details else None,
            request_id,
            ip_address,
            user_agent,
            time.time(),
        ),
    )


def record_operation(
    account: dict[str, Any],
    action_type: str,
    *,
    target_type: str | None = None,
    target_id: str | None = None,
    details: dict[str, Any] | None = None,
    result_status: str = "SUCCESS",
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Write an auditable operation record without exposing credentials or tokens."""
    init_auth_db()
    connection = _connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT id, username, display_name FROM accounts WHERE username = %s LIMIT 1", (account["username"],))
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("操作账户不存在，无法写入操作日志")
        _insert_operation_log(
            cursor,
            row["id"],
            action_type,
            username=row["username"],
            display_name=row["display_name"],
            target_type=target_type,
            target_id=target_id,
            details=details,
            result_status=result_status,
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        connection.commit()
    finally:
        connection.close()


def _token_from_authorization(authorization: Optional[str]) -> str:
    scheme, _, token = str(authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="请先登录")
    return token


def account_for_token(token: str) -> dict[str, Any]:
    account = _tokens.get(token)
    if account is None:
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录")
    return account


def has_permission(account: dict[str, Any], permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(account.get("role"), set())


def current_account(authorization: Optional[str] = Header(default=None)) -> dict[str, Any]:
    return account_for_token(_token_from_authorization(authorization))


def require_permission(permission: str):
    """Create a FastAPI dependency enforcing the logged-in account's role."""
    def dependency(account: dict[str, Any] = Depends(current_account)) -> dict[str, Any]:
        if not has_permission(account, permission):
            raise HTTPException(status_code=403, detail="当前权限组无权执行此操作")
        return account

    return dependency


def _require_admin(account: dict[str, Any] = Depends(current_account)) -> dict[str, Any]:
    return require_permission(PERMISSION_USER_MANAGE)(account)


def _invalidate_user_tokens(username: str) -> None:
    for token, account in list(_tokens.items()):
        if account["username"] == username:
            del _tokens[token]


def build_auth_router() -> APIRouter:
    router = APIRouter(prefix="/api/auth", tags=["auth"])

    @router.post("/login")
    def login(request: LoginRequest, http_request: Request) -> dict[str, Any]:
        init_auth_db()
        connection = _connection()
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT id, username, password_hash, display_name, role, permission_group, created_at FROM accounts WHERE username = %s LIMIT 1", (request.username.strip(),))
            row = cursor.fetchone()
            if not row or not _verify_password(request.password, row["password_hash"]):
                raise HTTPException(status_code=401, detail="账号名或密码错误")
            _insert_operation_log(
                cursor,
                row["id"],
                "AUTH_LOGIN",
                username=row["username"],
                display_name=row["display_name"],
                target_type="account",
                target_id=row["username"],
                ip_address=http_request.client.host if http_request.client else None,
                user_agent=http_request.headers.get("user-agent"),
            )
            connection.commit()
        finally:
            connection.close()
        account = _public_account(row)
        token = secrets.token_urlsafe(32)
        _tokens[token] = account
        return {"access_token": token, "token_type": "bearer", "user": account}

    @router.post("/logout")
    def logout(http_request: Request, authorization: Optional[str] = Header(default=None), account: dict[str, Any] = Depends(current_account)) -> dict[str, str]:
        token = _token_from_authorization(authorization)
        record_operation(
            account,
            "AUTH_LOGOUT",
            target_type="account",
            target_id=account["username"],
            ip_address=http_request.client.host if http_request.client else None,
            user_agent=http_request.headers.get("user-agent"),
        )
        _tokens.pop(token, None)
        return {"message": "已退出登录"}

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
            _insert_operation_log(cursor, row["id"], "AUTH_PASSWORD_CHANGED", username=account["username"], display_name=account.get("display_name", ""), target_type="account", target_id=account["username"])
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
                cursor.execute("SELECT id, username, display_name FROM accounts WHERE username = %s LIMIT 1", (actor["username"],))
                actor_row = cursor.fetchone()
                if actor_row is None:
                    raise RuntimeError("操作账户不存在，无法写入操作日志")
                cursor.execute(
                    "INSERT INTO accounts (username, password_hash, display_name, role, permission_group, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
                    (request.username, _hash_password(request.password), request.display_name, request.role, request.role, created_at),
                )
                _insert_operation_log(cursor, actor_row["id"], "ACCOUNT_CREATED", username=actor_row["username"], display_name=actor_row["display_name"], target_type="account", target_id=request.username, details={"permission_group": request.role})
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
            cursor.execute("SELECT id, username, display_name FROM accounts WHERE username = %s LIMIT 1", (actor["username"],))
            actor_row = cursor.fetchone()
            if actor_row is None:
                raise RuntimeError("操作账户不存在，无法写入操作日志")
            cursor.execute("UPDATE accounts SET role = %s, permission_group = %s WHERE username = %s", (request.role, request.role, username))
            cursor.execute("SELECT id, username, display_name, role, permission_group, created_at FROM accounts WHERE username = %s", (username,))
            row = cursor.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="用户不存在")
            _insert_operation_log(cursor, actor_row["id"], "ACCOUNT_PERMISSION_GROUP_UPDATED", username=actor_row["username"], display_name=actor_row["display_name"], target_type="account", target_id=username, details={"permission_group": request.role})
            connection.commit()
        finally:
            connection.close()
        _invalidate_user_tokens(username)
        return {"user": _public_account(row)}

    return router


def build_operation_log_router() -> APIRouter:
    router = APIRouter(prefix="/api", tags=["operation-logs"])

    @router.get("/operation-logs")
    def list_operation_logs(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        username: Optional[str] = Query(default=None, max_length=64),
        category: Optional[str] = Query(default=None, max_length=32),
        status: Optional[str] = Query(default=None, max_length=16),
        start_time: Optional[float] = Query(default=None),
        end_time: Optional[float] = Query(default=None),
        account: dict[str, Any] = Depends(current_account),
    ) -> dict[str, Any]:
        init_auth_db()
        conditions: list[str] = []
        parameters: list[Any] = []
        if account.get("role") != ROLE_ADMIN:
            conditions.append("logs.username = %s")
            parameters.append(account["username"])
        elif username:
            conditions.append("logs.username = %s")
            parameters.append(username)
        if category:
            conditions.append("logs.action_category = %s")
            parameters.append(category.upper())
        if status:
            conditions.append("logs.result_status = %s")
            parameters.append(status.upper())
        if start_time is not None:
            conditions.append("logs.created_at >= %s")
            parameters.append(start_time)
        if end_time is not None:
            conditions.append("logs.created_at <= %s")
            parameters.append(end_time)
        where_clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""

        connection = _connection()
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(f"SELECT COUNT(*) AS total FROM operation_logs logs{where_clause}", tuple(parameters))
            total = int(cursor.fetchone()["total"])
            cursor.execute(
                f"""SELECT logs.id, logs.username, logs.display_name, logs.action_type,
                           logs.action_category, logs.action_summary, logs.target_type,
                           logs.target_id, logs.device_id, logs.module_code,
                           logs.result_status, logs.details, logs.created_at
                    FROM operation_logs logs{where_clause}
                    ORDER BY logs.created_at DESC, logs.id DESC
                    LIMIT %s OFFSET %s""",
                (*parameters, page_size, (page - 1) * page_size),
            )
            rows = cursor.fetchall()
        finally:
            connection.close()

        items = []
        for row in rows:
            details = None
            if row.get("details"):
                try:
                    details = json.loads(row["details"])
                except (TypeError, json.JSONDecodeError):
                    details = {"content": str(row["details"])}
            category_code = row.get("action_category") or "OTHER"
            items.append({
                "id": row["id"],
                "username": row.get("username") or "",
                "display_name": row.get("display_name") or row.get("username") or "未知用户",
                "action_code": row["action_type"],
                "action_category": category_code,
                "action_category_label": ACTION_CATEGORY_LABELS.get(category_code, ACTION_CATEGORY_LABELS["OTHER"]),
                "action_summary": row.get("action_summary") or row["action_type"],
                "target_type": row.get("target_type"),
                "target_id": row.get("target_id"),
                "device_id": row.get("device_id"),
                "module_code": row.get("module_code"),
                "result_status": row.get("result_status") or "SUCCESS",
                "details": details,
                "created_at": float(row["created_at"]),
            })
        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": max(1, (total + page_size - 1) // page_size),
            "categories": [
                {"value": value, "label": label}
                for value, label in ACTION_CATEGORY_LABELS.items()
                if value != "OTHER"
            ],
        }

    return router
