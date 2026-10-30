"""Unit tests for the control-center edge credential store (P0-3 / A1).

These tests use a fake DB-API connection so no MySQL instance is required.
"""

import contextlib
import io
import unittest

from backend import edge_credentials as creds
from backend import issue_credential
from backend.issue_credential import build_parser


class FakeCursor:
    def __init__(self, one=None, all_rows=None, rowcount=1):
        self._one = list(one or [])
        self._all = list(all_rows or [])
        self.statements = []
        self.parameters = []
        self.rowcount = rowcount
        self.closed = False

    def execute(self, sql, params=None):
        self.statements.append(sql)
        self.parameters.append(params)

    def fetchone(self):
        return self._one.pop(0) if self._one else None

    def fetchall(self):
        return list(self._all)

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, cursors):
        self._cursors = list(cursors)
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def cursor(self, dictionary=False):
        if not self._cursors:
            raise AssertionError("no scripted cursor left")
        return self._cursors.pop(0)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


class TokenHelperTests(unittest.TestCase):
    def test_hash_token_is_sha256_hexdigest(self):
        hashed = creds.hash_token("EC-EDGE-1-v1-abc")
        self.assertEqual(len(hashed), 64)
        self.assertEqual(hashed, creds.hash_token("  EC-EDGE-1-v1-abc  "))
        self.assertNotEqual(hashed, creds.hash_token("EC-EDGE-1-v1-abd"))

    def test_generate_token_carries_edge_and_version(self):
        token = creds.generate_token("EDGE-CHAMBER-001", 3)
        self.assertTrue(token.startswith("EC-EDGE-CHAMBER-001-v3-"))
        self.assertNotEqual(token, creds.generate_token("EDGE-CHAMBER-001", 3))

    def test_generate_token_sanitizes_edge_id(self):
        token = creds.generate_token("../etc/pass wd", 1)
        self.assertTrue(token.startswith("EC-etcpasswd-v1-") or token.startswith("EC-etcpasswd"))

    def test_extract_bearer_variants(self):
        self.assertEqual(creds.extract_bearer("Bearer abc123"), "abc123")
        self.assertEqual(creds.extract_bearer("bearer   abc123  "), "abc123")
        self.assertEqual(creds.extract_bearer("Basic abc123"), "")
        self.assertEqual(creds.extract_bearer(""), "")
        self.assertEqual(creds.extract_bearer(None), "")


class IssueTests(unittest.TestCase):
    def test_issue_persists_only_the_hash(self):
        ddl_cursor = FakeCursor()
        work_cursor = FakeCursor(one=[(0,)])
        connection = FakeConnection([ddl_cursor, work_cursor])

        token, version = creds.issue(connection, "EDGE-CHAMBER-001", label="1号箱")

        self.assertEqual(version, 1)
        self.assertIn("edge_credentials", work_cursor.statements[-1])
        inserted = work_cursor.parameters[-1]
        self.assertIn(creds.hash_token(token), inserted)
        self.assertNotIn(token, str(inserted))
        self.assertEqual(connection.commits, 1)
        self.assertIn("CREATE TABLE IF NOT EXISTS edge_credentials", ddl_cursor.statements[0])

    def test_issue_increments_version(self):
        connection = FakeConnection([FakeCursor(), FakeCursor(one=[(7,)])])
        _, version = creds.issue(connection, "EDGE-1")
        self.assertEqual(version, 8)

    def test_issue_rejects_empty_edge_id(self):
        connection = FakeConnection([])
        with self.assertRaises(creds.CredentialError):
            creds.issue(connection, "   ")

    def test_issue_truncates_overlong_label(self):
        work_cursor = FakeCursor(one=[(0,)])
        connection = FakeConnection([FakeCursor(), work_cursor])
        creds.issue(connection, "EDGE-1", label="x" * 500)
        self.assertEqual(len(work_cursor.parameters[-1][3]), creds.MAX_LABEL_LENGTH)


class RevokeTests(unittest.TestCase):
    def test_revoke_reports_success(self):
        work_cursor = FakeCursor(rowcount=1)
        connection = FakeConnection([FakeCursor(), work_cursor])
        self.assertTrue(creds.revoke(connection, "EDGE-1", 2))
        self.assertIn("UPDATE edge_credentials", work_cursor.statements[-1])
        self.assertEqual(work_cursor.parameters[-1][1:], ("EDGE-1", 2))

    def test_revoke_reports_missing_version(self):
        connection = FakeConnection([FakeCursor(), FakeCursor(rowcount=0)])
        self.assertFalse(creds.revoke(connection, "EDGE-1", 9))


class VerifyTests(unittest.TestCase):
    def test_verify_accepts_enabled_bound_token(self):
        connection = FakeConnection([FakeCursor(), FakeCursor(one=[("EDGE-1", 1)])])
        self.assertTrue(creds.verify(connection, "EDGE-1", "EC-EDGE-1-v1-token"))

    def test_verify_rejects_revoked_token(self):
        connection = FakeConnection([FakeCursor(), FakeCursor(one=[("EDGE-1", 0)])])
        self.assertFalse(creds.verify(connection, "EDGE-1", "EC-EDGE-1-v1-token"))

    def test_verify_rejects_other_edge_id(self):
        connection = FakeConnection([FakeCursor(), FakeCursor(one=[("EDGE-2", 1)])])
        self.assertFalse(creds.verify(connection, "EDGE-1", "EC-EDGE-1-v1-token"))

    def test_verify_rejects_unknown_token(self):
        connection = FakeConnection([FakeCursor(), FakeCursor(one=[])])
        self.assertFalse(creds.verify(connection, "EDGE-1", "nope"))

    def test_verify_rejects_empty_inputs_without_touching_db(self):
        connection = FakeConnection([])
        self.assertFalse(creds.verify(connection, "", "token"))
        self.assertFalse(creds.verify(connection, "EDGE-1", "  "))


class ListTests(unittest.TestCase):
    def test_list_never_exposes_token_material(self):
        rows = [("EDGE-1", 2, "1号箱", 1, 100.0, None, None)]
        connection = FakeConnection([FakeCursor(), FakeCursor(all_rows=rows)])
        result = creds.list_credentials(connection, "EDGE-1")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["version"], 2)
        self.assertTrue(result[0]["enabled"])
        for key in result[0]:
            self.assertNotIn("token", key)
            self.assertNotIn("hash", key)


class CliParserTests(unittest.TestCase):
    def test_parser_accepts_all_documented_commands(self):
        parser = build_parser()
        self.assertEqual(parser.parse_args(["issue", "--edge-id", "E1"]).command, "issue")
        self.assertEqual(parser.parse_args(["rotate", "--edge-id", "E1"]).command, "rotate")
        revoked = parser.parse_args(["revoke", "--edge-id", "E1", "--version", "3"])
        self.assertEqual(revoked.version, 3)
        self.assertEqual(parser.parse_args(["list"]).command, "list")

    def test_parser_requires_edge_id_for_issue(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                build_parser().parse_args(["issue"])


class CliAuditTests(unittest.TestCase):
    def setUp(self):
        self._record = issue_credential.record_system_operation
        self._issue = issue_credential.issue
        self._rotate = issue_credential.rotate
        self._revoke = issue_credential.revoke
        self.events = []
        issue_credential.record_system_operation = lambda action, **kwargs: self.events.append((action, kwargs))

    def tearDown(self):
        issue_credential.record_system_operation = self._record
        issue_credential.issue = self._issue
        issue_credential.rotate = self._rotate
        issue_credential.revoke = self._revoke

    def test_issue_and_rotate_write_audit_without_token_material(self):
        args = type("Args", (), {"edge_id": "EDGE-1", "label": "box"})()
        connection = object()
        issue_credential.issue = lambda *_args, **_kwargs: ("secret-token", 2)
        issue_credential.rotate = lambda *_args, **_kwargs: ("new-secret-token", 3)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(issue_credential._run_issue(args, connection), 0)
            self.assertEqual(issue_credential._run_rotate(args, connection), 0)
        self.assertEqual([event[0] for event in self.events], ["EDGE_CREDENTIAL_ISSUED", "EDGE_CREDENTIAL_ROTATED"])
        self.assertNotIn("secret-token", str(self.events))

    def test_revoke_writes_audit_only_when_a_credential_was_revoked(self):
        args = type("Args", (), {"edge_id": "EDGE-1", "version": 4})()
        issue_credential.revoke = lambda *_args, **_kwargs: True
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(issue_credential._run_revoke(args, object()), 0)
        self.assertEqual(self.events[0][0], "EDGE_CREDENTIAL_REVOKED")
        self.events.clear()
        issue_credential.revoke = lambda *_args, **_kwargs: False
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(issue_credential._run_revoke(args, object()), 1)
        self.assertEqual(self.events, [])


if __name__ == "__main__":
    unittest.main()
