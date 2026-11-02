"""Offline regressions for credential handling and interrupted publishing."""

import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "threads"))
import oauth_exchange as oauth
import publish_text as publisher
import token_store


TOKEN = "DUMMY_REVIEW_TOKEN"


class Response:
    status = 200

    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self):
        return json.dumps(self.body).encode()


class HelpersTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="omni-helpers-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.state = self.root / "attempt.json"
        self.token_file = self.root / "token"
        self.env = patch.dict(os.environ, {
            "THREADS_ACCESS_TOKEN": TOKEN,
            "THREADS_TOKEN_FILE": str(self.token_file),
            "THREADS_USER_ID": "123",
            "THREADS_GRAPH_HOST": publisher.DEFAULT_HOST,
        })
        self.env.start()
        self.addCleanup(self.env.stop)

    def run_publisher(self, *args):
        with redirect_stdout(io.StringIO()) as output:
            code = publisher.main(["publish_text.py", *args])
        return code, json.loads(output.getvalue())

    def arguments(self):
        return ["--text", "A test caption", "--state-file", str(self.state)]

    def quota(self, **changes):
        row = {"quota_usage": 1, "config": {"quota_total": 250},
               "reply_quota_usage": 2, "reply_config": {"quota_total": 1000}}
        row.update(changes)
        return row

    def test_refresh_preserves_same_token_without_printing_it(self):
        oauth.write_token(self.token_file, TOKEN)
        for returned in (TOKEN, "A_ROTATED_DUMMY_TOKEN"):
            with self.subTest(returned=returned), patch.object(oauth.urllib.request, "urlopen", return_value=Response({"access_token": returned, "expires_in": 5184000})), redirect_stdout(io.StringIO()) as output:
                self.assertEqual(oauth.cmd_refresh(), 0)
                self.assertTrue(json.loads(output.getvalue())["ok"])
                self.assertNotIn(returned, output.getvalue())
                self.assertEqual(token_store.read_token(self.token_file), returned)

    def test_oauth_errors_redact_secrets(self):
        with patch.object(oauth.urllib.request, "urlopen", side_effect=TimeoutError(TOKEN)):
            status, body = oauth.http_json("GET", "https://example.invalid", None, [TOKEN])
        self.assertEqual(status, 0)
        self.assertNotIn(TOKEN, str(body))

    def test_token_replacement_is_private_before_replace(self):
        self.token_file.write_text("old value")
        self.token_file.chmod(0o644)
        original_replace = os.replace

        def observe(source, destination):
            if token_store.private_mode_enforced():
                self.assertEqual(stat.S_IMODE(Path(source).stat().st_mode), 0o600)
            self.assertEqual(self.token_file.read_text(), "old value")
            return original_replace(source, destination)

        with patch.object(token_store.os, "replace", side_effect=observe):
            oauth.write_token(self.token_file, TOKEN)
        if token_store.private_mode_enforced():
            self.assertEqual(stat.S_IMODE(self.token_file.stat().st_mode), 0o600)
        self.assertEqual(token_store.read_token(self.token_file), TOKEN)

    def test_failed_token_write_preserves_previous_value(self):
        oauth.write_token(self.token_file, "old value")
        with patch.object(token_store.os, "replace", side_effect=OSError("disk failure")):
            with self.assertRaises(OSError):
                oauth.write_token(self.token_file, TOKEN)
        self.assertEqual(token_store.read_token(self.token_file), "old value")
        self.assertEqual(list(self.root.glob(".omni-*")), [])

    def test_both_helpers_reject_public_token_file(self):
        if not token_store.private_mode_enforced():
            self.skipTest("Windows mode bits cannot represent Unix 600")
        self.token_file.write_text(TOKEN)
        self.token_file.chmod(0o644)
        with patch.dict(os.environ, {"THREADS_ACCESS_TOKEN": ""}):
            self.assertIsNotNone(publisher.load_token()[1])
            with patch.object(oauth, "http_json") as http, redirect_stdout(io.StringIO()):
                self.assertEqual(oauth.cmd_refresh(), 1)
                http.assert_not_called()

    def test_publish_quota_does_not_require_reply_permissions(self):
        row = {"quota_usage": 0, "config": {"quota_total": 250}}
        with patch.object(publisher, "request", return_value=(200, {"data": [row]})) as request:
            self.assertIsInstance(publisher.check_quota("123", TOKEN), dict)
            self.assertNotIn("reply_config", request.call_args.args[1])

    def test_reply_quota_full_blocks_before_create(self):
        row = self.quota(reply_quota_usage=1000)
        with patch.object(publisher, "request", return_value=(200, {"data": [row]})) as request:
            code, result = self.run_publisher(*self.arguments(), "--reply-to", "456")
        self.assertEqual(code, 1)
        self.assertIn("reply quota full", result["error"])
        self.assertEqual(request.call_count, 1)
        self.assertFalse(self.state.exists())

    def test_invalid_quota_fails_closed(self):
        for row in ({}, self.quota(config={}), self.quota(quota_usage=True),
                    self.quota(reply_config={}), self.quota(reply_quota_usage=-1),
                    self.quota(reply_config={"quota_total": "1000"})):
            with self.subTest(row=row), patch.object(publisher, "request", return_value=(200, {"data": [row]})):
                self.assertIsInstance(publisher.check_quota("123", TOKEN, reply=True), str)

    def test_state_file_required_before_network(self):
        with patch.object(publisher, "request") as request:
            code, _ = self.run_publisher("--text", "hello")
        self.assertEqual(code, 2)
        request.assert_not_called()

    def test_success_records_ids_and_blocks_second_create(self):
        def request(method, url, form, secrets):
            saved = json.loads(self.state.read_text())
            self.assertNotIn(TOKEN, self.state.read_text())
            if url.endswith("/threads"):
                self.assertEqual(saved["phase"], "create_result_unknown")
                return 200, {"id": "container-1"}
            self.assertEqual(saved["phase"], "publish_result_unknown")
            self.assertEqual(saved["creation_id"], "container-1")
            return 200, {"id": "media-1"}

        with patch.object(publisher, "check_quota", return_value={"quota_usage": 1}), patch.object(publisher, "poll_until_ready", return_value=("FINISHED", "")), patch.object(publisher, "request", side_effect=request) as http:
            code, result = self.run_publisher(*self.arguments())
            self.assertEqual(code, 0)
            self.assertEqual(result["media_id"], "media-1")
            self.assertEqual(json.loads(self.state.read_text())["phase"], "published")
            http.reset_mock()
            code, result = self.run_publisher(*self.arguments())
            self.assertEqual(code, 1)
            self.assertTrue(result["recovery_required"])
            http.assert_not_called()

    def test_interruption_after_create_keeps_id(self):
        with patch.object(publisher, "check_quota", return_value={"quota_usage": 1}), patch.object(publisher, "request", return_value=(200, {"id": "container-1"})), patch.object(publisher, "poll_until_ready", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.run_publisher(*self.arguments())
        self.assertEqual(json.loads(self.state.read_text())["creation_id"], "container-1")

    def test_unknown_create_result_blocks_retry(self):
        with patch.object(publisher, "check_quota", return_value={"quota_usage": 1}), patch.object(publisher, "request", return_value=(0, "timeout")) as http:
            code, result = self.run_publisher(*self.arguments(), "--auto-publish")
            self.assertEqual(code, 1)
            self.assertTrue(result["recovery_required"])
            self.assertEqual(json.loads(self.state.read_text())["phase"], "create_result_unknown")
            http.reset_mock()
            self.run_publisher(*self.arguments())
            http.assert_not_called()

    def test_publish_timeout_can_be_recovered_without_post(self):
        with patch.object(publisher, "check_quota", return_value={"quota_usage": 1}), patch.object(publisher, "poll_until_ready", return_value=("FINISHED", "")), patch.object(publisher, "request", side_effect=[(200, {"id": "container-1"}), (0, "timeout")]):
            code, result = self.run_publisher(*self.arguments())
        self.assertEqual(code, 1)
        self.assertTrue(result["recovery_required"])
        with patch.object(publisher, "request", return_value=(200, {"status": "PUBLISHED"})) as http:
            code, result = self.run_publisher("--recover", "--state-file", str(self.state))
        self.assertEqual(code, 0)
        self.assertEqual(result["container_status"], "PUBLISHED")
        self.assertEqual(http.call_count, 1)
        self.assertEqual(http.call_args.args[0], "GET")

    def test_recovery_without_id_or_wrong_account_does_not_call_network(self):
        for attempt in ({"user_id": "123", "host": publisher.graph_host()},
                        {"user_id": "other", "host": publisher.graph_host(), "creation_id": "c1"}):
            self.state.write_text(json.dumps(attempt))
            with patch.object(publisher, "request") as http:
                code, _ = self.run_publisher("--recover", "--state-file", str(self.state))
            self.assertEqual(code, 1)
            http.assert_not_called()

    def test_ready_recovery_is_read_only_and_not_success(self):
        self.state.write_text(json.dumps({"user_id": "123", "host": publisher.graph_host(), "creation_id": "container-1"}))
        with patch.object(publisher, "request", return_value=(200, {"status": "FINISHED"})) as http:
            code, result = self.run_publisher("--recover", "--state-file", str(self.state))
        self.assertEqual(code, 1)
        self.assertTrue(result["recovery_required"])
        self.assertEqual(http.call_args.args[0], "GET")

    def test_auto_publish_only_creates_once_and_saves_container(self):
        with patch.object(publisher, "check_quota", return_value={"quota_usage": 1}), patch.object(publisher, "request", return_value=(200, {"id": "container-1"})) as http, patch.object(publisher, "poll_until_ready") as poll:
            code, result = self.run_publisher(*self.arguments(), "--auto-publish")
        self.assertEqual(code, 0)
        self.assertTrue(result["auto_publish_text"])
        self.assertEqual(json.loads(self.state.read_text())["creation_id"], "container-1")
        self.assertEqual(http.call_count, 1)
        poll.assert_not_called()

    def test_state_reservation_race_blocks_network_create(self):
        def quota(*args, **kwargs):
            self.state.write_text("another running attempt")
            return {"quota_usage": 1}

        with patch.object(publisher, "check_quota", side_effect=quota), patch.object(publisher, "request") as http:
            code, _ = self.run_publisher(*self.arguments())
        self.assertEqual(code, 1)
        self.assertEqual(self.state.read_text(), "another running attempt")
        http.assert_not_called()

    def test_dry_run_cannot_be_combined_with_network_quota_check(self):
        with patch.object(publisher, "request") as http:
            code, _ = self.run_publisher("--dry-run", "--check-limit")
        self.assertEqual(code, 2)
        http.assert_not_called()

    def test_timeout_exception_is_redacted(self):
        with patch.object(publisher.urllib.request, "urlopen", side_effect=TimeoutError(TOKEN)):
            status, body = publisher.request("POST", "https://example.invalid", {}, [TOKEN])
        self.assertEqual(status, 0)
        self.assertNotIn(TOKEN, body)

    def test_non_posix_skips_mode_owner_and_directory_fsync(self):
        self.token_file.write_text("old value\n")
        self.token_file.chmod(0o644)

        def refuse_fchmod(*args, **kwargs):
            raise AssertionError("fchmod is not used when Unix modes are unavailable")

        with patch.object(token_store, "private_mode_enforced", return_value=False), patch.object(token_store, "directory_sync_supported", return_value=False), patch.object(token_store.os, "fchmod", side_effect=refuse_fchmod, create=True):
            token_store.sync_directory(self.root)
            oauth.write_token(self.token_file, TOKEN)
            self.assertEqual(token_store.read_token(self.token_file), TOKEN)
        with patch.object(token_store, "directory_sync_supported", return_value=False), patch.object(token_store.os, "open", side_effect=AssertionError("directory fsync")) as opened:
            token_store.sync_directory(self.root)
            opened.assert_not_called()

    def test_non_posix_still_rejects_a_token_inside_git(self):
        inside = Path(__file__).resolve()
        with patch.object(token_store, "private_mode_enforced", return_value=False):
            with self.assertRaises(ValueError) as caught:
                token_store.read_token(inside)
        self.assertIn("git", str(caught.exception))

    def test_dry_run_never_reads_token_or_touches_network_or_state(self):
        with patch.object(publisher, "load_token") as load, patch.object(publisher, "request") as http:
            code, result = self.run_publisher(*self.arguments(), "--dry-run")
        self.assertEqual(code, 0)
        self.assertNotIn(TOKEN, json.dumps(result))
        load.assert_not_called()
        http.assert_not_called()
        self.assertFalse(self.state.exists())


if __name__ == "__main__":
    unittest.main()
