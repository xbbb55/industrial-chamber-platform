"""Edge device credential store owned by the control center.

The control center accepts edge telemetry over WS /api/edge/ws and pushes
control commands back on the same socket, so every edge must present a
credential that is bound to exactly one edge_id.  Credentials are stored in the
control-center authentication database; only a SHA-256 hash of the token is
persisted and the plaintext is printed once by backend.issue_credential.

All functions take an explicit DB-API connection so they can be unit tested with
a fake connection and so the eventual backend/db.py factory (P0-9 / C1) can own
connection creation.  Until C1 lands, connect() reuses the existing
authentication connection helper to avoid introducing a sixth connection entry
point.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from typing import Any, Iterable, Optional

TOKEN_PREFIX = "EC"
TOKEN_BYTES = 32
MAX_LABEL_LENGTH = 128

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS edge_credentials (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    edge_id VARCHAR(64) NOT NULL,
    version INT NOT NULL,
    token_hash CHAR(64) NOT NULL,
    label VARCHAR(128) NULL,
    enabled TINYINT NOT NULL DEFAULT 1,
    created_at DOUBLE NOT NULL,
    revoked_at DOUBLE NULL,
    last_used_at DOUBLE NULL,
    UNIQUE KEY uq_edge_credentials_edge_version (edge_id, version),
    UNIQUE KEY uq_edge_credentials_token (token_hash),
    KEY idx_edge_credentials_edge (edge_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""


class CredentialError(RuntimeError):
    """Raised when a credential operation cannot be completed."""


def connect():
    """Open the control-center authentication database.

    Reuses backend.auth so the project keeps a single connection entry point
    until the P0-9 connection factory replaces both of them.
    """
    from .auth import _connection  # local import keeps import time cheap

    return _connection()


def normalize_token(token: Any) -> str:
    return str(token or "").strip()


def hash_token(token: str) -> str:
    return hashlib.sha256(normalize_token(token).encode("utf-8")).hexdigest()


def generate_token(edge_id: str, version: int) -> str:
    """Return a fresh opaque token that also carries edge/version for auditing."""
    slug = "".join(ch for ch in str(edge_id) if ch.isalnum() or ch in "-_") or "EDGE"
    return f"{TOKEN_PREFIX}-{slug}-v{int(version)}-{secrets.token_urlsafe(TOKEN_BYTES)}"


def extract_bearer(authorization: Optional[str]) -> str:
    """Parse 'Authorization: Bearer <token>' without raising."""
    scheme, _, token = str(authorization or "").partition(" ")
    if scheme.lower() != "bearer":
        return ""
    return normalize_token(token)


def ensure_table(connection: Any) -> None:
    cursor = connection.cursor()
    try:
        cursor.execute(CREATE_TABLE_SQL)
    finally:
        _close_cursor(cursor)


def _next_version(cursor: Any, edge_id: str) -> int:
    cursor.execute("SELECT COALESCE(MAX(version), 0) FROM edge_credentials WHERE edge_id = %s", (edge_id,))
    row = cursor.fetchone()
    if row is None or row[0] is None:
        return 1
    return int(row[0]) + 1


def issue(connection: Any, edge_id: str, *, label: Optional[str] = None, commit: bool = True) -> tuple[str, int]:
    """Create a new enabled credential version for edge_id."""
    normalized_edge = normalize_token(edge_id)
    if not normalized_edge:
        raise CredentialError("edge_id 不能为空")
    ensure_table(connection)
    cursor = connection.cursor()
    try:
        version = _next_version(cursor, normalized_edge)
        token = generate_token(normalized_edge, version)
        cursor.execute(
            "INSERT INTO edge_credentials (edge_id, version, token_hash, label, enabled, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (
                normalized_edge,
                version,
                hash_token(token),
                _normalize_label(label),
                1,
                time.time(),
            ),
        )
    finally:
        _close_cursor(cursor)
    if commit:
        connection.commit()
    return token, version


def rotate(connection: Any, edge_id: str, *, label: Optional[str] = None, commit: bool = True) -> tuple[str, int]:
    """Issue a new version while keeping older versions usable until revoked."""
    return issue(connection, edge_id, label=label, commit=commit)


def revoke(connection: Any, edge_id: str, version: int, *, commit: bool = True) -> bool:
    """Disable one credential version.  Returns False when nothing matched."""
    normalized_edge = normalize_token(edge_id)
    ensure_table(connection)
    cursor = connection.cursor()
    try:
        cursor.execute(
            "UPDATE edge_credentials SET enabled = 0, revoked_at = %s "
            "WHERE edge_id = %s AND version = %s AND enabled = 1",
            (time.time(), normalized_edge, int(version)),
        )
        affected = getattr(cursor, "rowcount", 0) or 0
    finally:
        _close_cursor(cursor)
    if commit:
        connection.commit()
    return affected > 0


def list_credentials(connection: Any, edge_id: Optional[str] = None) -> list[dict[str, Any]]:
    """Return credential metadata without any token material."""
    ensure_table(connection)
    cursor = connection.cursor()
    try:
        columns = "edge_id, version, label, enabled, created_at, revoked_at, last_used_at"
        if edge_id:
            cursor.execute(
                "SELECT " + columns + " FROM edge_credentials WHERE edge_id = %s ORDER BY version DESC",
                (normalize_token(edge_id),),
            )
        else:
            cursor.execute("SELECT " + columns + " FROM edge_credentials ORDER BY edge_id, version DESC")
        rows: Iterable[Any] = cursor.fetchall() or []
    finally:
        _close_cursor(cursor)
    return [
        {
            "edge_id": str(row[0]),
            "version": int(row[1]),
            "label": row[2],
            "enabled": bool(int(row[3])),
            "created_at": float(row[4]) if row[4] is not None else None,
            "revoked_at": float(row[5]) if row[5] is not None else None,
            "last_used_at": float(row[6]) if row[6] is not None else None,
        }
        for row in rows
    ]


def verify(connection: Any, edge_id: str, token: str) -> bool:
    """Return True only when the token is enabled and bound to edge_id."""
    normalized_token = normalize_token(token)
    normalized_edge = normalize_token(edge_id)
    if not normalized_token or not normalized_edge:
        return False
    ensure_table(connection)
    cursor = connection.cursor()
    try:
        cursor.execute(
            "SELECT edge_id, enabled FROM edge_credentials WHERE token_hash = %s",
            (hash_token(normalized_token),),
        )
        row = cursor.fetchone()
    finally:
        _close_cursor(cursor)
    if row is None:
        return False
    stored_edge = str(row[0] or "")
    enabled = bool(int(row[1] or 0))
    # Constant-time edge comparison so a mismatching edge_id leaks no timing signal.
    return enabled and hmac.compare_digest(stored_edge, normalized_edge)


def touch(connection: Any, edge_id: str, token: str, *, commit: bool = True) -> None:
    """Record last use for audit; failures must never break telemetry."""
    try:
        cursor = connection.cursor()
        try:
            cursor.execute(
                "UPDATE edge_credentials SET last_used_at = %s WHERE token_hash = %s AND edge_id = %s",
                (time.time(), hash_token(token), normalize_token(edge_id)),
            )
        finally:
            _close_cursor(cursor)
        if commit:
            connection.commit()
    except Exception:  # pragma: no cover - diagnostics only
        pass


def _normalize_label(label: Optional[str]) -> Optional[str]:
    text = str(label or "").strip()
    if not text:
        return None
    return text[:MAX_LABEL_LENGTH]


def _close_cursor(cursor: Any) -> None:
    close = getattr(cursor, "close", None)
    if callable(close):
        close()
