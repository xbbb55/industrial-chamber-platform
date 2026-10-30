"""Tests for edge device WebSocket authorization (P0-2 / A3)."""

import asyncio
import contextlib
import io
import unittest

from backend import memory_router


class FakeConnection:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class EdgeAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self._connect = memory_router.edge_credentials.connect
        self._verify = memory_router.edge_credentials.verify
        self._touch = memory_router.edge_credentials.touch
        self._compat = memory_router.EDGE_AUTH_COMPAT_MODE
        self.calls = []
        self.touches = []

    def tearDown(self):
        memory_router.edge_credentials.connect = self._connect
        memory_router.edge_credentials.verify = self._verify
        memory_router.edge_credentials.touch = self._touch
        memory_router.EDGE_AUTH_COMPAT_MODE = self._compat

    def _patch(self, *, verify_result=None, verify_error=None, connect_error=None):
        connection = FakeConnection()

        def _connect():
            if connect_error:
                raise connect_error
            return connection

        def _verify(conn, edge_id, token):
            self.calls.append((edge_id, token))
            if verify_error:
                raise verify_error
            return bool(verify_result)

        def _touch(conn, edge_id, token):
            self.touches.append((edge_id, token))

        memory_router.edge_credentials.connect = _connect
        memory_router.edge_credentials.verify = _verify
        memory_router.edge_credentials.touch = _touch
        return connection

    def test_missing_credential_is_rejected_by_default(self):
        memory_router.EDGE_AUTH_COMPAT_MODE = False
        self._patch(verify_result=True)
        allowed, reason = asyncio.run(memory_router._authorize_edge("EDGE-1", ""))
        self.assertFalse(allowed)
        self.assertEqual(reason, "missing_credential")
        self.assertEqual(self.calls, [])

    def test_missing_credential_is_allowed_in_compat_mode_with_warning(self):
        memory_router.EDGE_AUTH_COMPAT_MODE = True
        self._patch(verify_result=True)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            allowed, reason = asyncio.run(memory_router._authorize_edge("EDGE-1", ""))
        self.assertTrue(allowed)
        self.assertEqual(reason, "compat_mode_without_credential")
        self.assertIn("WARNING", buffer.getvalue())
        self.assertEqual(self.calls, [])

    def test_valid_credential_is_accepted(self):
        memory_router.EDGE_AUTH_COMPAT_MODE = False
        self._patch(verify_result=True)
        allowed, reason = asyncio.run(memory_router._authorize_edge("EDGE-1", "EC-EDGE-1-v1-token"))
        self.assertTrue(allowed)
        self.assertEqual(reason, "ok")
        self.assertEqual(self.calls, [("EDGE-1", "EC-EDGE-1-v1-token")])
        self.assertEqual(self.touches, [("EDGE-1", "EC-EDGE-1-v1-token")])

    def test_wrong_credential_is_rejected(self):
        memory_router.EDGE_AUTH_COMPAT_MODE = False
        self._patch(verify_result=False)
        allowed, reason = asyncio.run(memory_router._authorize_edge("EDGE-1", "bogus"))
        self.assertFalse(allowed)
        self.assertEqual(reason, "invalid_credential")
        self.assertEqual(self.touches, [])

    def test_unreachable_store_fails_closed(self):
        memory_router.EDGE_AUTH_COMPAT_MODE = False
        self._patch(connect_error=RuntimeError("db down"))
        allowed, reason = asyncio.run(memory_router._authorize_edge("EDGE-1", "token"))
        self.assertFalse(allowed)
        self.assertTrue(reason.startswith("credential_store_unavailable"))

    def test_verify_error_fails_closed(self):
        memory_router.EDGE_AUTH_COMPAT_MODE = False
        self._patch(verify_error=RuntimeError("query failed"))
        allowed, reason = asyncio.run(memory_router._authorize_edge("EDGE-1", "token"))
        self.assertFalse(allowed)
        self.assertIn("credential_store_unavailable", reason)

    def test_connection_is_closed(self):
        memory_router.EDGE_AUTH_COMPAT_MODE = False
        connection = self._patch(verify_result=True)
        asyncio.run(memory_router._authorize_edge("EDGE-1", "token"))
        self.assertTrue(connection.closed)


class CommandResultsEndpointTests(unittest.TestCase):
    def test_results_endpoint_requires_permission(self):
        found = False
        for route in memory_router.app.routes:
            dependant = getattr(route, "dependant", None)
            if getattr(route, "path", None) == "/api/commands/results" and dependant is not None:
                found = True
                self.assertGreaterEqual(len(dependant.dependencies), 1)
        self.assertTrue(found, "route /api/commands/results not found")

    def test_edge_socket_route_exists(self):
        paths = {getattr(route, "path", None) for route in memory_router.app.routes}
        self.assertIn("/api/edge/ws", paths)


if __name__ == "__main__":
    unittest.main()
