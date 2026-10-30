"""Tests for the deployment startup guard (G6 / A2) and endpoint auth wiring (P0-1)."""

import contextlib
import io
import unittest

from device_edge.config import EdgeConfig
from device_edge.deployment_guard import (
    COOKIE_MODE_AUTO,
    COOKIE_MODE_SECURE,
    COOKIE_MODE_STRICT_HTTP,
    Deployment,
    PROFILE_LOCAL,
    PROFILE_MULTI_DEVICE,
    ensure_deployable,
    format_deployment_report,
    is_loopback_host,
    is_wildcard_host,
    parse_trusted_proxies,
    resolve_deployment,
    validate_deployment,
)


class HostClassifierTests(unittest.TestCase):
    def test_loopback_hosts(self):
        for host in ("127.0.0.1", "localhost", "::1", "[::1]", " 127.0.0.1 "):
            self.assertTrue(is_loopback_host(host), host)
        for host in ("192.168.1.2", "0.0.0.0", "", None):
            self.assertFalse(is_loopback_host(host), host)

    def test_wildcard_hosts(self):
        for host in ("0.0.0.0", "::", "", "*", None):
            self.assertTrue(is_wildcard_host(host), host)
        for host in ("127.0.0.1", "192.168.1.2"):
            self.assertFalse(is_wildcard_host(host), host)

    def test_parse_trusted_proxies(self):
        self.assertEqual(parse_trusted_proxies("10.0.0.1, 10.0.0.2"), ("10.0.0.1", "10.0.0.2"))
        self.assertEqual(parse_trusted_proxies("10.0.0.1;10.0.0.2"), ("10.0.0.1", "10.0.0.2"))
        self.assertEqual(parse_trusted_proxies(""), ())
        self.assertEqual(parse_trusted_proxies(None), ())


class ResolveTests(unittest.TestCase):
    def test_defaults_are_local_and_secure(self):
        deployment = resolve_deployment("127.0.0.1", env={})
        self.assertEqual(deployment.profile, PROFILE_LOCAL)
        self.assertEqual(deployment.cookie_mode, COOKIE_MODE_SECURE)
        self.assertEqual(deployment.trusted_proxies, ())

    def test_env_overrides(self):
        deployment = resolve_deployment(
            "192.168.1.2",
            env={
                "DEPLOYMENT_PROFILE": "MULTI-DEVICE",
                "SESSION_COOKIE_MODE": "strict-http",
                "TRUSTED_PROXY_IPS": "10.0.0.1",
            },
        )
        self.assertEqual(deployment.profile, PROFILE_MULTI_DEVICE)
        self.assertEqual(deployment.cookie_mode, COOKIE_MODE_STRICT_HTTP)
        self.assertEqual(deployment.trusted_proxies, ("10.0.0.1",))


class ValidateTests(unittest.TestCase):
    def test_local_loopback_secure_is_clean(self):
        check = validate_deployment(Deployment(host="127.0.0.1"))
        self.assertTrue(check.ok)
        self.assertEqual(check.errors, [])

    def test_wildcard_is_rejected(self):
        for host in ("0.0.0.0", "::"):
            check = validate_deployment(Deployment(host=host))
            self.assertFalse(check.ok, host)
            self.assertIn("0.0.0.0", check.errors[0])

    def test_local_profile_must_bind_loopback(self):
        check = validate_deployment(Deployment(host="192.168.1.2", profile=PROFILE_LOCAL, cookie_mode=COOKIE_MODE_STRICT_HTTP))
        self.assertFalse(check.ok)
        self.assertTrue(any("回环地址" in error for error in check.errors))

    def test_multi_device_strict_http_is_allowed_with_warning(self):
        check = validate_deployment(
            Deployment(host="192.168.1.2", profile=PROFILE_MULTI_DEVICE, cookie_mode=COOKIE_MODE_STRICT_HTTP)
        )
        self.assertTrue(check.ok)
        self.assertTrue(any("未加密传输" in warning for warning in check.warnings))
        self.assertTrue(any("风险接受" in warning for warning in check.warnings))

    def test_multi_device_secure_without_proxy_is_rejected(self):
        check = validate_deployment(Deployment(host="192.168.1.2", profile=PROFILE_MULTI_DEVICE))
        self.assertFalse(check.ok)
        self.assertTrue(any("TRUSTED_PROXY_IPS" in error for error in check.errors))

    def test_multi_device_secure_with_proxy_is_allowed(self):
        check = validate_deployment(
            Deployment(
                host="192.168.1.2",
                profile=PROFILE_MULTI_DEVICE,
                cookie_mode=COOKIE_MODE_SECURE,
                trusted_proxies=("10.0.0.1",),
            )
        )
        self.assertTrue(check.ok)
        self.assertTrue(any("反向代理" in warning for warning in check.warnings))

    def test_multi_device_loopback_warns(self):
        check = validate_deployment(
            Deployment(host="127.0.0.1", profile=PROFILE_MULTI_DEVICE, cookie_mode=COOKIE_MODE_STRICT_HTTP)
        )
        self.assertTrue(check.ok)
        self.assertTrue(any("局域网" in warning for warning in check.warnings))

    def test_invalid_profile_and_cookie_mode(self):
        self.assertFalse(validate_deployment(Deployment(host="127.0.0.1", profile="desktop")).ok)
        self.assertFalse(validate_deployment(Deployment(host="127.0.0.1", cookie_mode="http")).ok)

    def test_auto_mode_warns_off_loopback(self):
        check = validate_deployment(
            Deployment(host="192.168.1.2", profile=PROFILE_MULTI_DEVICE, cookie_mode=COOKIE_MODE_AUTO)
        )
        self.assertTrue(check.ok)
        self.assertTrue(any("auto" in warning for warning in check.warnings))

    def test_ensure_deployable_raises_on_error(self):
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit):
                ensure_deployable(Deployment(host="0.0.0.0"))

    def test_report_contains_conclusion(self):
        deployment = Deployment(host="0.0.0.0")
        text = format_deployment_report(deployment, validate_deployment(deployment))
        self.assertIn("部署自检", text)
        self.assertIn("拒绝启动", text)


def _protected_paths(app):
    paths = {}
    for route in app.routes:
        dependant = getattr(route, "dependant", None)
        path = getattr(route, "path", None)
        if dependant is None or path is None:
            continue
        paths[path] = len(dependant.dependencies)
    return paths


class EndpointAuthTests(unittest.TestCase):
    def setUp(self):
        from device_edge.local_service import create_app

        config = EdgeConfig(edge_id="EDGE-TEST", device_ip="127.0.0.1", agent_version="test", database_enabled=False)
        self.paths = _protected_paths(create_app(config))

    def test_anonymous_endpoints_have_no_dependencies(self):
        for path in ("/healthz", "/api/status"):
            self.assertIn(path, self.paths)
            self.assertEqual(self.paths[path], 0, path)

    def test_device_data_endpoints_require_auth(self):
        for path in ("/api/memory/snapshot", "/api/memory/devices", "/api/diagnostics"):
            self.assertIn(path, self.paths)
            self.assertGreaterEqual(self.paths[path], 1, path)


if __name__ == "__main__":
    unittest.main()
