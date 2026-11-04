"""Workspace checks reject unresolved publication decisions."""

import copy
import importlib.util
from pathlib import Path
import unittest
import tempfile
import shutil

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("checker", ROOT / "scripts/check_workspace.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class WorkspaceTest(unittest.TestCase):
    def setUp(self):
        example = ROOT / "examples/salty-pages"
        self.profile = checker.load(example / "profile.yaml")
        self.profile["ai_disclosure"]["policy"] = "editor_decides"
        self.calendar = checker.load(example / "calendar.yaml")
        self.calendar["items"] = [copy.deepcopy(self.calendar["items"][1])]

    def problems(self):
        report = checker.Report()
        checker.check_calendar(self.calendar, self.profile, report, False)
        return report.problems

    def test_existing_example_and_templates(self):
        self.assertEqual(checker.check_tree(ROOT / "examples/salty-pages", False), [])
        self.assertEqual(checker.check_tree(ROOT / "templates", True), [])

    def test_unresolved_or_non_boolean_disclosure_blocks_approved_item(self):
        for value in (None, "false", 0):
            self.calendar["items"][0]["disclose_ai"] = value
            with self.subTest(value=value):
                self.assertTrue(any("explicit boolean" in x for x in self.problems()))

    def test_explicit_false_is_a_valid_per_item_decision(self):
        self.calendar["items"][0]["disclose_ai"] = False
        self.assertEqual(self.problems(), [])

    def test_undecided_draft_can_wait(self):
        item = self.calendar["items"][0]
        item.update(status="pending_approval", disclose_ai=None)
        item["approval"]["state"] = "pending"
        self.assertEqual(self.problems(), [])

    def test_disclosure_must_match_fixed_policy(self):
        for policy, value in (("always", False), ("never", True)):
            self.profile["ai_disclosure"]["policy"] = policy
            self.calendar["items"][0]["disclose_ai"] = value
            with self.subTest(policy=policy):
                self.assertTrue(any("conflicts" in x for x in self.problems()))

    def test_practice_cannot_enter_publish_queue(self):
        self.calendar["items"][0]["practice"] = True
        self.assertTrue(any("practice" in x for x in self.problems()))

    def test_first_ten_posts_cannot_be_approved_by_policy(self):
        for level in ("auto_low_risk", "full_auto"):
            self.profile["approval"].update(level=level, posts_approved_count=9)
            self.calendar["items"][0]["approval"]["by"] = "policy"
            with self.subTest(level=level):
                self.assertTrue(any("requires editor approval" in x for x in self.problems()))
        self.profile["approval"]["posts_approved_count"] = 10
        self.assertEqual(self.problems(), [])

    def test_faq_reply_opt_in_is_off_and_boolean(self):
        policy = checker.load(ROOT / "examples/salty-pages/approval-policy.yaml")
        self.assertIs(policy["auto_approve_faq_replies_before_ten_posts"], False)
        policy["auto_approve_faq_replies_before_ten_posts"] = "yes"
        report = checker.Report()
        checker.check_policy(policy, self.profile, report, False)
        self.assertTrue(any("auto_approve_faq_replies_before_ten_posts" in x for x in report.problems))

    def test_faq_reply_opt_in_does_not_cover_posts_or_loose_matches(self):
        policy = {"auto_approve_faq_replies_before_ten_posts": False}
        self.assertFalse(checker.faq_reply_bypasses_first_ten(
            policy, triage="answer_from_faq", source="editor", sensitivity="low", risk="low"))
        policy["auto_approve_faq_replies_before_ten_posts"] = True
        allowed = dict(triage="answer_from_faq", source="editor", sensitivity="low", risk="low")
        self.assertTrue(checker.faq_reply_bypasses_first_ten(policy, **allowed))
        self.assertTrue(checker.faq_reply_bypasses_first_ten(policy, holds=["first_ten_posts"], **allowed))
        for bad in (
            dict(allowed, source="imported"),
            dict(allowed, triage="draft_reply"),
            dict(allowed, sensitivity="high"),
            dict(allowed, risk="medium"),
        ):
            with self.subTest(bad=bad):
                self.assertFalse(checker.faq_reply_bypasses_first_ten(policy, **bad))
        self.assertFalse(checker.faq_reply_bypasses_first_ten(
            policy, holds=["sensitive_triage"], **allowed))

    def test_storage_value_is_one_of_three(self):
        report = checker.Report()
        checker.check_capabilities({"storage": "google_drive"}, report)
        self.assertTrue(any("storage" in x for x in report.problems))
        report = checker.Report()
        checker.check_capabilities({"storage": "external"}, report)
        self.assertEqual(report.problems, [])

    def test_counter_must_be_a_non_negative_integer(self):
        for count in (None, -1, "10", True):
            self.profile["approval"]["posts_approved_count"] = count
            report = checker.Report()
            checker.check_profile(self.profile, report, False)
            with self.subTest(count=count):
                self.assertTrue(any("posts_approved_count" in x for x in report.problems))

    def profile_problems(self):
        report = checker.Report()
        checker.check_profile(self.profile, report, False)
        return report.problems

    def test_confirmed_no_exclusions_is_valid_but_unanswered_is_not(self):
        self.profile["topics"]["avoid"] = []
        self.assertTrue(any("avoid_confirmed" in x for x in self.profile_problems()))
        self.profile["topics"]["avoid_confirmed"] = True
        self.assertEqual(self.profile_problems(), [])

    def test_exclusions_keep_their_list_contract(self):
        for value in ("none", None, [""], [True]):
            self.profile["topics"]["avoid"] = value
            with self.subTest(value=value):
                self.assertTrue(any("topics.avoid" in x for x in self.profile_problems()))

    def test_minimum_is_separate_from_weekly_ceiling(self):
        self.profile["cadence"].update(min_posts_per_week=3, posts_per_week=7, max_posts_per_day=1)
        self.assertEqual(self.profile_problems(), [])
        self.profile["cadence"]["posts_per_week"] = 2
        self.assertTrue(any("min_posts_per_week exceeds" in x for x in self.profile_problems()))
        self.profile["cadence"].update(posts_per_week=20, min_posts_per_week=8)
        self.assertTrue(any("min_posts_per_week exceeds" in x for x in self.profile_problems()))

    def test_no_editor_reply_limit_does_not_require_fake_integer(self):
        self.profile["cadence"]["max_replies_per_day"] = None
        self.assertEqual(self.profile_problems(), [])
        for value in (True, -1, "unlimited", 1.5):
            self.profile["cadence"]["max_replies_per_day"] = value
            with self.subTest(value=value):
                self.assertTrue(any("max_replies_per_day" in x for x in self.profile_problems()))

    def test_midnight_window_requires_explicit_day_boundary(self):
        self.profile["cadence"]["windows"] = [{"days": ["fri"], "start": "19:00", "end": "00:00", "end_next_day": True}]
        self.assertEqual(self.profile_problems(), [])
        self.profile["cadence"]["windows"][0]["end_next_day"] = False
        self.assertTrue(any("cross midnight" in x for x in self.profile_problems()))

    def test_bad_clock_values_and_window_types_are_reported(self):
        for window in (None, {"days": ["funday"], "start": "19:00", "end": "21:00"},
                       {"days": ["fri"], "start": "19:00", "end": "24:00"},
                       {"days": ["fri"], "start": "19:00", "end": "19:00"},
                       {"days": ["fri"], "start": "19:00", "end": "21:00", "end_next_day": "false"}):
            self.profile["cadence"]["windows"] = [window]
            with self.subTest(window=window):
                self.assertTrue(any("cadence.windows" in x for x in self.profile_problems()))

    def test_browser_mode_requires_explicit_opt_in(self):
        self.profile["login"].update(method="browser", browser_opt_in=False)
        self.assertTrue(any("browser_opt_in" in x for x in self.profile_problems()))
        self.profile["login"]["browser_opt_in"] = True
        self.assertEqual(self.profile_problems(), [])

    def test_full_workspace_with_confirmed_none_and_midnight_is_valid(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "fictional"
            shutil.copytree(ROOT / "examples/salty-pages", root)
            self.profile["topics"].update(avoid=[], avoid_confirmed=True)
            self.profile["cadence"].update(min_posts_per_week=3, posts_per_week=7, max_replies_per_day=None)
            self.profile["cadence"]["windows"] = [{"days": ["mon", "wed", "fri"], "start": "19:00", "end": "00:00", "end_next_day": True}]
            self.profile["cadence"]["quiet_hours"] = {"start": "00:00", "end": "19:00"}
            self.profile["login"].update(method="browser", browser_opt_in=True)
            (root / "profile.yaml").write_text(checker.yaml.safe_dump(self.profile, allow_unicode=True), encoding="utf-8")
            self.assertEqual(checker.check_tree(root, False), [])

    def test_setup_state_does_not_accept_ambiguous_send_scope(self):
        state = checker.load(ROOT / "templates/setup-state.yaml")
        for scope in ("style", "reply_template", "public_action"):
            state["decisions"] = [{"item_id": "fictional-practice", "scope": scope}]
            report = checker.Report()
            checker.check_setup_state(state, report)
            self.assertEqual(report.problems, [])
        state["decisions"] = [{"item_id": "fictional-practice", "scope": "approved"}]
        report = checker.Report()
        checker.check_setup_state(state, report)
        self.assertTrue(any("scope" in x for x in report.problems))

    def test_optional_setup_state_is_validated_in_full_tree(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "fictional"
            shutil.copytree(ROOT / "examples/salty-pages", root)
            state = checker.load(ROOT / "templates/setup-state.yaml")
            state["session_intent"] = "start_posting"
            (root / "setup-state.yaml").write_text(checker.yaml.safe_dump(state), encoding="utf-8")
            self.assertTrue(any("setup-state.session_intent" in x for x in checker.check_tree(root, False)))


if __name__ == "__main__":
    unittest.main()
