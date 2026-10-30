"""Startup guard for the deployment profile and session transport (G6 / A2).

Two product editions exist and they need different binding and cookie settings:

* local        - Web UI and Electron both run on the machine itself; the service
                 binds to loopback and keeps Secure cookies (loopback is a
                 browser-trustworthy origin).
* multi-device - other hosts on the same LAN open the dashboard; the service must
                 bind a concrete NIC address.  Without HTTPS the session cookie
                 travels in cleartext, so a written risk acceptance is required
                 (see the remediation plan, section 3.1).

Mismatching the profile with the listening address either breaks login (Secure
cookie dropped over plain HTTP) or silently downgrades security, so the service
refuses to start instead of limping along.

This module is intentionally free of FastAPI/uvicorn imports so it can be unit
tested and reused by the Electron launcher path.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Iterable, Optional

PROFILE_LOCAL = "local"
PROFILE_MULTI_DEVICE = "multi-device"
PROFILES = (PROFILE_LOCAL, PROFILE_MULTI_DEVICE)

COOKIE_MODE_SECURE = "secure"
COOKIE_MODE_STRICT_HTTP = "strict-http"
COOKIE_MODE_AUTO = "auto"
COOKIE_MODES = (COOKIE_MODE_SECURE, COOKIE_MODE_STRICT_HTTP, COOKIE_MODE_AUTO)

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost", "0:0:0:0:0:0:0:1", "[::1]"})
WILDCARD_HOSTS = frozenset({"0.0.0.0", "::", "", "*"})

ENV_PROFILE = "DEPLOYMENT_PROFILE"
ENV_COOKIE_MODE = "SESSION_COOKIE_MODE"
ENV_TRUSTED_PROXIES = "TRUSTED_PROXY_IPS"

DEFAULT_PROFILE = PROFILE_LOCAL
DEFAULT_COOKIE_MODE = COOKIE_MODE_SECURE


@dataclass(frozen=True)
class Deployment:
    host: str
    profile: str = DEFAULT_PROFILE
    cookie_mode: str = DEFAULT_COOKIE_MODE
    trusted_proxies: tuple[str, ...] = ()

    @property
    def is_loopback(self) -> bool:
        return is_loopback_host(self.host)

    @property
    def is_wildcard(self) -> bool:
        return is_wildcard_host(self.host)

    @property
    def has_trusted_proxy(self) -> bool:
        return bool(self.trusted_proxies)


@dataclass
class DeploymentCheck:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def is_loopback_host(host: Optional[str]) -> bool:
    return str(host or "").strip().lower() in LOOPBACK_HOSTS


def is_wildcard_host(host: Optional[str]) -> bool:
    return str(host or "").strip().lower() in WILDCARD_HOSTS


def parse_trusted_proxies(value: Optional[str]) -> tuple[str, ...]:
    """Parse a comma/space separated allow-list of proxy addresses."""
    text = str(value or "").replace(";", ",").replace(" ", ",")
    return tuple(part.strip() for part in text.split(",") if part.strip())


def resolve_deployment(host: str, env: Optional[dict] = None) -> Deployment:
    source = os.environ if env is None else env
    profile = str(source.get(ENV_PROFILE) or DEFAULT_PROFILE).strip().lower()
    cookie_mode = str(source.get(ENV_COOKIE_MODE) or DEFAULT_COOKIE_MODE).strip().lower()
    return Deployment(
        host=str(host or "").strip(),
        profile=profile,
        cookie_mode=cookie_mode,
        trusted_proxies=parse_trusted_proxies(source.get(ENV_TRUSTED_PROXIES)),
    )


def validate_deployment(deployment: Deployment) -> DeploymentCheck:
    """Return the blocking errors and the standing warnings for one deployment."""
    check = DeploymentCheck()

    if deployment.profile not in PROFILES:
        check.errors.append(
            f"{ENV_PROFILE}={deployment.profile!r} 无效，可选值：{', '.join(PROFILES)}"
        )
    if deployment.cookie_mode not in COOKIE_MODES:
        check.errors.append(
            f"{ENV_COOKIE_MODE}={deployment.cookie_mode!r} 无效，可选值：{', '.join(COOKIE_MODES)}"
        )

    if deployment.is_wildcard:
        check.errors.append(
            "拒绝以 0.0.0.0 / :: 监听：必须显式指定回环地址（本机版）或具体网卡地址（多设备版）"
        )
        return check

    if deployment.profile == PROFILE_LOCAL and not deployment.is_loopback:
        check.errors.append(
            f"本机版（{ENV_PROFILE}=local）必须监听回环地址，当前为 {deployment.host}"
        )

    if deployment.profile == PROFILE_MULTI_DEVICE and deployment.is_loopback:
        check.warnings.append(
            "多设备版监听了回环地址，局域网内其它设备将无法访问；现场部署时应改为具体网卡地址"
        )

    if deployment.cookie_mode == COOKIE_MODE_SECURE and not deployment.is_loopback:
        if deployment.has_trusted_proxy:
            check.warnings.append(
                "已按 HTTPS 反向代理形态运行，代理地址："
                + ", ".join(deployment.trusted_proxies)
                + "；仅信任上述来源的 X-Forwarded-Proto"
            )
        else:
            check.errors.append(
                "非回环监听 + Secure Cookie 会导致浏览器丢弃会话 Cookie（登录成功后立即 401）。"
                "请改用 SESSION_COOKIE_MODE=strict-http，或部署 HTTPS 反向代理并配置 TRUSTED_PROXY_IPS"
            )

    if deployment.cookie_mode == COOKIE_MODE_STRICT_HTTP:
        if deployment.is_loopback:
            check.warnings.append(
                "回环监听下可以改用 SESSION_COOKIE_MODE=secure 获得更严格的安全属性"
            )
        else:
            check.warnings.append(
                "当前会话未加密传输：局域网内可被抓包嗅探，COOKIE 为明文传输。"
                "本形态必须持有书面风险接受（有效期/复审期限不超过 6 个月），"
                "并落实防火墙白名单与缩短的会话 TTL"
            )

    if deployment.cookie_mode == COOKIE_MODE_AUTO and not deployment.is_loopback:
        check.warnings.append(
            "auto 模式会按请求协议动态决定 Secure 属性，同一服务不同入口的安全属性可能不一致，排查成本较高"
        )

    return check


def format_deployment_report(deployment: Deployment, check: DeploymentCheck) -> str:
    lines = [
        "部署自检：",
        f"  profile         = {deployment.profile}",
        f"  listen host     = {deployment.host or '(未指定)'}",
        f"  cookie mode     = {deployment.cookie_mode}",
        f"  trusted proxies = {', '.join(deployment.trusted_proxies) or '(空，不信任任何代理头)'}",
    ]
    for warning in check.warnings:
        lines.append(f"  [WARN] {warning}")
    for error in check.errors:
        lines.append(f"  [ERROR] {error}")
    lines.append("  结论：" + ("通过" if check.ok else "拒绝启动，请先修正上述配置"))
    return "\n".join(lines)


def ensure_deployable(deployment: Deployment) -> DeploymentCheck:
    """Raise SystemExit(2) when the deployment cannot start safely."""
    check = validate_deployment(deployment)
    print(format_deployment_report(deployment, check), flush=True)
    if not check.ok:
        raise SystemExit(2)
    return check
