"""Synthetic, offline checks for the optional read-only Chrome adapter."""

import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "browser_read", Path(__file__).resolve().parents[1] / "scripts/threads/browser_read.py")
browser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(browser)
PROFILE = "https://www.threads.com/@fictional_editor"


class BrowserReadTest(unittest.TestCase):
    def test_only_exact_profile_and_post_urls(self):
        self.assertEqual(browser.threads_url(PROFILE + "/"), PROFILE)
        self.assertEqual(browser.threads_url(PROFILE + "/post/fixture_1"), PROFILE + "/post/fixture_1")
        for url in ("http://www.threads.com/@fixture", "https://www.threads.com.evil/@fixture",
                    "https://www.threads.com@evil.test/@fixture", PROFILE + "?access_token=dummy",
                    PROFILE + "#fragment", PROFILE + "/replies", PROFILE + "/post/x/media",
                    "https://www.threads.com/messages", "https://evil.test/@fixture"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                browser.threads_url(url)

    def test_probe_does_not_launch_or_read_browser(self):
        with patch.object(browser, "run_script") as script, redirect_stdout(io.StringIO()) as output:
            self.assertEqual(browser.main(["probe"]), 0)
        self.assertFalse(json.loads(output.getvalue())["browser_verified"])
        script.assert_not_called()

    def test_consent_required_for_every_read_scope(self):
        for action in ("open", "read", "scroll"):
            with self.subTest(action=action), patch.object(browser, "run_script") as script, redirect_stdout(io.StringIO()):
                self.assertEqual(browser.main([action, "--url", PROFILE, "--tab-id", "42"]), 1)
                script.assert_not_called()

    def test_open_returns_only_numeric_id(self):
        with patch.object(browser, "run_script", return_value="42") as script:
            self.assertEqual(browser.open_page(PROFILE), "42")
            self.assertEqual(script.call_args.args[1], PROFILE)
        with patch.object(browser, "run_script", return_value="not a tab"):
            with self.assertRaises(ValueError):
                browser.open_page(PROFILE)

    def test_selected_tab_cannot_be_replaced_by_another_profile(self):
        payload = {"page_url": PROFILE + "_other", "visible_text": "fixture"}
        with patch.object(browser, "run_script", return_value=json.dumps(payload)):
            with self.assertRaises(ValueError):
                browser.read_page(PROFILE, "42")

    def test_login_or_checkpoint_stops_without_body_output(self):
        for reason in ("login", "checkpoint"):
            with self.subTest(reason=reason), patch.object(browser, "run_script", return_value=json.dumps({"blocked": reason, "page_url": PROFILE})):
                with self.assertRaises(ValueError):
                    browser.read_page(PROFILE, "42")

    def test_invalid_snapshot_or_tab_id_fails(self):
        with patch.object(browser, "run_script", return_value="undefined"):
            with self.assertRaises(ValueError):
                browser.read_page(PROFILE, "42")
        with patch.object(browser, "run_script") as script:
            with self.assertRaises(ValueError):
                browser.read_page(PROFILE, "42;anything")
            script.assert_not_called()

    def test_unsupported_platform_fails_without_starting_process(self):
        with patch.object(browser.sys, "platform", "win32"), patch.object(browser.subprocess, "run") as run:
            with self.assertRaises(ValueError):
                browser.open_page(PROFILE)
            run.assert_not_called()

    def test_automation_uses_argv_and_handles_permission_failure(self):
        denied = subprocess.CompletedProcess([], 1, stdout="", stderr="permission denied")
        with patch.object(browser.sys, "platform", "darwin"), patch.object(browser.subprocess, "run", return_value=denied) as run:
            with self.assertRaisesRegex(ValueError, "Chrome refused"):
                browser.open_page(PROFILE)
            self.assertEqual(run.call_args.args[0][0], "/usr/bin/osascript")
            self.assertNotIn("shell", run.call_args.kwargs)

    def test_automation_timeout_is_not_reported_as_success(self):
        with patch.object(browser.sys, "platform", "darwin"), patch.object(browser.subprocess, "run", side_effect=subprocess.TimeoutExpired("osascript", 20)):
            with self.assertRaisesRegex(ValueError, "timed out"):
                browser.open_page(PROFILE)

    @unittest.skipUnless(shutil.which("node"), "Node is optional; needed for the synthetic DOM check")
    def test_generated_javascript_is_read_only_and_guards_navigation(self):
        for scroll in (False, True):
            script = browser.PAGE_SCRIPT.replace("EXPECTED_URL", json.dumps(PROFILE)).replace("SHOULD_SCROLL", str(scroll).lower())
            fixture = '''let scrolls=0;
global.location={origin:'https://www.threads.com',pathname:'/@fictional_editor',href:'https://www.threads.com/@fictional_editor'};
const body={innerText:'fictional page',querySelectorAll:()=>[]};
global.document={body,readyState:'complete',querySelector:()=>null,querySelectorAll:()=>[]};
global.window={innerHeight:100,scrollBy:()=>scrolls++};
'''
            fixture += "const result=" + script + ";\nconst data=JSON.parse(result);\n"
            fixture += "if(data.visible_text!=='fictional page'||scrolls!==" + str(int(scroll)) + ")throw Error('wrong read/scroll');\n"
            fixture += "location.pathname='/@someone_else';\nlet blocked=false;try{" + script + ";}catch(e){blocked=true;}if(!blocked)throw Error('navigation was not blocked');"
            result = subprocess.run([shutil.which("node"), "-e", fixture], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
