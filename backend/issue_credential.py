"""Offline CLI for edge device credentials (decision G1).

Run this on the host that can reach the control-center authentication database
(usually the control-center machine), then copy the printed token into the edge
device-edge.config.json under auth.token.

    python -m backend.issue_credential issue  --edge-id EDGE-CHAMBER-001 --label "1号箱"
    python -m backend.issue_credential rotate --edge-id EDGE-CHAMBER-001
    python -m backend.issue_credential revoke --edge-id EDGE-CHAMBER-001 --version 1
    python -m backend.issue_credential list   --edge-id EDGE-CHAMBER-001

The plaintext token is printed exactly once; the database keeps only its hash.
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

from .edge_credentials import (
    CredentialError,
    connect,
    issue,
    list_credentials,
    revoke,
    rotate,
)
from .auth import record_system_operation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m backend.issue_credential",
        description="管理边缘设备接入凭据（总控认证库）",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    issue_parser = subparsers.add_parser("issue", help="签发一条新的启用凭据")
    issue_parser.add_argument("--edge-id", required=True)
    issue_parser.add_argument("--label", default=None)

    rotate_parser = subparsers.add_parser("rotate", help="签发新版本（旧版本保留，验证后再撤销）")
    rotate_parser.add_argument("--edge-id", required=True)
    rotate_parser.add_argument("--label", default=None)

    revoke_parser = subparsers.add_parser("revoke", help="撤销指定版本")
    revoke_parser.add_argument("--edge-id", required=True)
    revoke_parser.add_argument("--version", required=True, type=int)

    list_parser = subparsers.add_parser("list", help="查看凭据版本与启用状态")
    list_parser.add_argument("--edge-id", default=None)

    return parser


def _print_token(edge_id: str, version: int, token: str) -> None:
    print("凭据已签发，明文只显示这一次：")
    print("  edge_id :", edge_id)
    print("  version :", version)
    print("  token   :", token)
    print("请写入边缘端 device-edge.config.json 的 auth.token，并妥善保管。")


def _run_issue(args: argparse.Namespace, connection) -> int:
    token, version = issue(connection, args.edge_id, label=args.label)
    record_system_operation(
        "EDGE_CREDENTIAL_ISSUED",
        target_type="edge",
        target_id=args.edge_id,
        details={"version": version, "label": args.label},
    )
    _print_token(args.edge_id, version, token)
    return 0


def _run_rotate(args: argparse.Namespace, connection) -> int:
    token, version = rotate(connection, args.edge_id, label=args.label)
    record_system_operation(
        "EDGE_CREDENTIAL_ROTATED",
        target_type="edge",
        target_id=args.edge_id,
        details={"version": version, "label": args.label},
    )
    print("已签发新版本，旧版本仍启用，验证通过后请执行 revoke 撤销旧版本。")
    _print_token(args.edge_id, version, token)
    return 0


def _run_revoke(args: argparse.Namespace, connection) -> int:
    changed = revoke(connection, args.edge_id, args.version)
    if not changed:
        print(f"未找到可撤销的凭据：edge_id={args.edge_id} version={args.version}", file=sys.stderr)
        return 1
    record_system_operation(
        "EDGE_CREDENTIAL_REVOKED",
        target_type="edge",
        target_id=args.edge_id,
        details={"version": args.version},
    )
    print(f"已撤销凭据：edge_id={args.edge_id} version={args.version}")
    return 0


def _run_list(args: argparse.Namespace, connection) -> int:
    rows = list_credentials(connection, args.edge_id)
    if not rows:
        print("没有匹配的凭据。")
        return 0
    header = f"{'edge_id':<20} {'ver':>4} {'state':<8} {'label':<16} {'created_at':<20}"
    print(header)
    print("-" * len(header))
    for row in rows:
        state = "启用" if row["enabled"] else "已撤销"
        created = f"{row['created_at']:.0f}" if row["created_at"] else "-"
        print(f"{row['edge_id']:<20} {row['version']:>4} {state:<8} {str(row['label'] or '-'):<16} {created:<20}")
    return 0


HANDLERS = {
    "issue": _run_issue,
    "rotate": _run_rotate,
    "revoke": _run_revoke,
    "list": _run_list,
}


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = HANDLERS[args.command]
    try:
        connection = connect()
    except Exception as exc:  # noqa: BLE001 - surfaced to the operator
        print(f"无法连接总控认证库：{exc}", file=sys.stderr)
        return 2
    try:
        return handler(args, connection)
    except CredentialError as exc:
        print(f"操作失败：{exc}", file=sys.stderr)
        return 1
    finally:
        close = getattr(connection, "close", None)
        if callable(close):
            close()


if __name__ == "__main__":
    raise SystemExit(main())
