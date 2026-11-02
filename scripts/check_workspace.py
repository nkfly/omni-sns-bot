#!/usr/bin/env python3
"""Check a workspace (or the example) for required keys and leaked secrets.

Needs PyYAML. Does not call Threads. Exit 0 when the tree matches the v0.1
contract. Pass --allow-empty for the blank templates, where strings may be
blank and login may still be undecided.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write("PyYAML is required for this checker: pip install pyyaml\n")
    sys.exit(2)

POST_STATUSES = {
    "idea",
    "needs_facts",
    "draft",
    "pending_approval",
    "approved",
    "publishing",
    "published",
    "failed",
    "rejected",
    "killed",
}
TEXT_REQUIRED = {
    "draft",
    "pending_approval",
    "approved",
    "publishing",
    "published",
    "rejected",
}
APPROVAL_LEVELS = {"always_ask", "auto_low_risk", "full_auto"}
VOICE_SOURCES = {"extract", "preset", "both"}
LOGIN_METHODS = {"api", "browser", "draft_only"}
FAQ_SOURCES = {"editor", "imported", "unconfirmed"}
SENSITIVITY = {"low", "medium", "high"}
TRIAGE = {"answer_from_faq", "draft_reply", "escalate", "ignore", "sensitive_hold"}
FORBIDDEN_KEYS = {
    "password",
    "passwd",
    "secret",
    "access_token",
    "client_secret",
    "app_secret",
    "cookie",
    "session",
    "sessionid",
    "authorization",
}


def load(path: Path):
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def is_blank(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    if isinstance(value, (list, dict)) and len(value) == 0:
        return True
    return False


def dig(tree, dotted: str):
    current = tree
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return None, False
        current = current[part]
    return current, True


class Report:
    def __init__(self) -> None:
        self.problems: list[str] = []

    def add(self, message: str) -> None:
        self.problems.append(message)

    def need(self, tree, dotted: str, *, non_empty: bool) -> None:
        value, ok = dig(tree, dotted)
        if not ok:
            self.add(f"missing {dotted}")
            return
        if non_empty and is_blank(value):
            self.add(f"empty {dotted}")

    def walk_secrets(self, node, trail: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                here = f"{trail}.{key}" if trail else str(key)
                if str(key).lower() in FORBIDDEN_KEYS and isinstance(value, str) and value.strip():
                    if not _env_pointer(value):
                        self.add(f"secret-like value at {here}")
                self.walk_secrets(value, here)
        elif isinstance(node, list):
            for index, value in enumerate(node):
                self.walk_secrets(value, f"{trail}[{index}]")
        elif isinstance(node, str) and "access_token=" in node:
            self.add(f"access_token query in {trail or 'document'}")


def _env_pointer(value: str) -> bool:
    text = value.strip()
    return text.startswith("THREADS_") or text.isupper() and "_" in text and text.replace("_", "").isalnum()


def check_profile(profile, report: Report, allow_empty: bool) -> None:
    for key in (
        "version",
        "editor.name",
        "account.brand_name",
        "account.handle",
        "account.platform",
        "account.owned_by_editor",
        "purpose.statement",
        "audience.who",
        "topics.cover",
        "topics.avoid",
        "languages.primary",
        "cadence.timezone",
        "cadence.posts_per_week",
        "cadence.max_posts_per_day",
        "cadence.buffer_min",
        "approval.level",
        "voice.source",
        "ai_disclosure.policy",
        "login.method",
        "login.browser_opt_in",
    ):
        report.need(profile, key, non_empty=not allow_empty and key != "topics.avoid")
    # topics.avoid may be a non-empty list in strict mode; the key must exist.
    if not allow_empty:
        report.need(profile, "topics.avoid", non_empty=True)
    level, ok = dig(profile, "approval.level")
    if ok and level not in APPROVAL_LEVELS and not (allow_empty and level in APPROVAL_LEVELS | {None, ""}):
        if level not in APPROVAL_LEVELS:
            report.add(f"approval.level {level!r} is not a known level")
    source, ok = dig(profile, "voice.source")
    if ok and not allow_empty and source not in VOICE_SOURCES:
        report.add(f"voice.source {source!r} must be extract, preset, or both")
    method, ok = dig(profile, "login.method")
    if ok and not allow_empty and method not in LOGIN_METHODS:
        report.add(f"login.method {method!r} must be api, browser, or draft_only")
    owned, ok = dig(profile, "account.owned_by_editor")
    if ok and not allow_empty and owned is not True:
        report.add("account.owned_by_editor must be true before the account is usable")
    policy, ok = dig(profile, "ai_disclosure.policy")
    if ok and policy not in {"always", "editor_decides", "never"} and not allow_empty:
        report.add(f"ai_disclosure.policy {policy!r} is not valid")
    if not allow_empty:
        chosen, ok = dig(profile, "ai_disclosure.chosen")
        if not ok or chosen is not True:
            report.add("ai_disclosure.chosen must be true once the editor has answered; do not publish before that")
    count, ok = dig(profile, "approval.posts_approved_count")
    if not ok or type(count) is not int or count < 0:
        report.add("approval.posts_approved_count must be a non-negative integer; missing or invalid counts require always_ask")


def check_style(style, report: Report, allow_empty: bool) -> None:
    for key in (
        "version",
        "language.primary",
        "tone.adjectives",
        "sentence.typical_length",
        "emoji.max_per_post",
        "hashtags.max_per_post",
        "gold_posts",
        "replies.typical_length",
        "replies.answer_in_first_line",
        "replies.banned_openers",
    ):
        report.need(style, key, non_empty=not allow_empty)
    posts, ok = dig(style, "gold_posts")
    if ok and not allow_empty:
        if not isinstance(posts, list) or not posts:
            report.add("gold_posts needs at least one verbatim sample")
        else:
            for index, post in enumerate(posts):
                if not isinstance(post, dict) or is_blank(post.get("text")):
                    report.add(f"gold_posts[{index}].text is empty")


def check_policy(policy, profile, report: Report, allow_empty: bool) -> None:
    report.need(policy, "level", non_empty=True)
    report.need(policy, "reply_to_others", non_empty=False)
    report.need(policy, "low_risk_requires", non_empty=not allow_empty)
    report.need(policy, "always_ask_even_on_full_auto", non_empty=not allow_empty)
    level, _ = dig(policy, "level")
    if level not in APPROVAL_LEVELS:
        report.add(f"policy level {level!r} is not valid")
    profile_level, ok = dig(profile, "approval.level")
    if ok and profile_level != level:
        report.add(f"profile approval.level {profile_level!r} != policy level {level!r}")
    holds, ok = dig(policy, "always_ask_even_on_full_auto")
    if ok and isinstance(holds, list) and "sensitive_triage" not in holds:
        report.add("always_ask_even_on_full_auto must include sensitive_triage")


def check_faq(faq, report: Report, allow_empty: bool) -> None:
    report.need(faq, "entries", non_empty=False)
    report.need(faq, "inbox", non_empty=False)
    entries, ok = dig(faq, "entries")
    if not ok or not isinstance(entries, list):
        return
    if not allow_empty and len(entries) == 0:
        report.add("faq.entries is empty; seed it before going live")
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            report.add(f"entries[{index}] is not a mapping")
            continue
        for field in ("id", "questions", "answer", "source", "sensitivity"):
            if is_blank(entry.get(field)):
                report.add(f"entries[{index}].{field} is empty")
        if entry.get("source") not in FAQ_SOURCES:
            report.add(f"entries[{index}].source is not editor|imported|unconfirmed")
        if entry.get("sensitivity") not in SENSITIVITY:
            report.add(f"entries[{index}].sensitivity is not low|medium|high")
    inbox, ok = dig(faq, "inbox")
    if ok and isinstance(inbox, list):
        for index, item in enumerate(inbox):
            if not isinstance(item, dict):
                report.add(f"inbox[{index}] is not a mapping")
                continue
            triage = item.get("triage")
            if triage not in TRIAGE:
                report.add(f"inbox[{index}].triage {triage!r} is not a known label")
            if triage == "sensitive_hold" and str(item.get("draft") or "").strip():
                report.add(f"inbox[{index}] is sensitive_hold but has a public draft")


def check_calendar(calendar, profile, report: Report, allow_empty: bool) -> None:
    report.need(calendar, "timezone", non_empty=not allow_empty)
    report.need(calendar, "items", non_empty=False)
    tz, ok = dig(calendar, "timezone")
    profile_tz, profile_ok = dig(profile, "cadence.timezone")
    if ok and profile_ok and tz and profile_tz and tz != profile_tz:
        report.add(f"calendar timezone {tz} != profile {profile_tz}")
    items, ok = dig(calendar, "items")
    if not ok or not isinstance(items, list):
        return
    seen = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            report.add(f"items[{index}] is not a mapping")
            continue
        item_id = item.get("id")
        if is_blank(item_id):
            report.add(f"items[{index}].id is empty")
        elif item_id in seen:
            report.add(f"duplicate calendar id {item_id}")
        else:
            seen.add(item_id)
        status = item.get("status")
        if status not in POST_STATUSES:
            report.add(f"items[{index}].status {status!r} is not valid")
        if is_blank(item.get("platform")):
            report.add(f"items[{index}].platform is empty")
        if status in TEXT_REQUIRED and is_blank(item.get("text")):
            report.add(f"items[{index}] status {status} needs text")
        if item.get("risk") not in {"low", "medium", "high"}:
            report.add(f"items[{index}].risk is missing")
        approval = item.get("approval") or {}
        if not isinstance(approval, dict) or approval.get("state") not in {"pending", "approved", "rejected"}:
            report.add(f"items[{index}].approval.state is missing")
        # Current policy gates queued actions, never rewrites historical decisions.
        if status in {"approved", "publishing"}:
            if item.get("practice") is True:
                report.add(f"items[{index}] is practice and must not be approved for publishing")
            if type(item.get("disclose_ai")) is not bool:
                report.add(f"items[{index}].disclose_ai needs an explicit boolean before publishing")
            policy, _ = dig(profile, "ai_disclosure.policy")
            if policy == "never" and item.get("disclose_ai") is not False:
                report.add(f"items[{index}].disclose_ai conflicts with never policy")
            if policy == "always" and item.get("disclose_ai") is not True:
                report.add(f"items[{index}].disclose_ai conflicts with always policy")
            if not isinstance(approval, dict) or approval.get("state") != "approved":
                report.add(f"items[{index}] status {status} requires approval.state approved")
            count, _ = dig(profile, "approval.posts_approved_count")
            level, _ = dig(profile, "approval.level")
            requires_editor = level == "always_ask" or type(count) is not int or count < 10
            if requires_editor and (not isinstance(approval, dict) or approval.get("by") != "editor"):
                report.add(f"items[{index}] requires editor approval under the first-ten/always_ask rule")
        if status == "published":
            published = item.get("published") or {}
            if is_blank(published.get("permalink")) and is_blank(published.get("media_id")):
                report.add(f"items[{index}] is published without permalink or media_id")


def check_tree(root: Path, allow_empty: bool) -> list[str]:
    report = Report()
    required = {
        "profile.yaml": check_profile,
        "style-guide.yaml": check_style,
        "approval-policy.yaml": None,
        "faq.yaml": check_faq,
        "calendar.yaml": check_calendar,
    }
    loaded = {}
    for name in required:
        path = root / name
        if not path.is_file():
            report.add(f"missing file {name}")
            continue
        try:
            loaded[name] = load(path)
        except yaml.YAMLError as exc:
            report.add(f"{name} is not valid YAML: {exc}")
    if "profile.yaml" in loaded:
        check_profile(loaded["profile.yaml"], report, allow_empty)
        report.walk_secrets(loaded["profile.yaml"], "profile")
    if "style-guide.yaml" in loaded:
        check_style(loaded["style-guide.yaml"], report, allow_empty)
        report.walk_secrets(loaded["style-guide.yaml"], "style-guide")
    if "approval-policy.yaml" in loaded and "profile.yaml" in loaded:
        check_policy(loaded["approval-policy.yaml"], loaded["profile.yaml"], report, allow_empty)
        report.walk_secrets(loaded["approval-policy.yaml"], "approval-policy")
    if "faq.yaml" in loaded:
        check_faq(loaded["faq.yaml"], report, allow_empty)
        report.walk_secrets(loaded["faq.yaml"], "faq")
    if "calendar.yaml" in loaded and "profile.yaml" in loaded:
        check_calendar(loaded["calendar.yaml"], loaded["profile.yaml"], report, allow_empty)
        report.walk_secrets(loaded["calendar.yaml"], "calendar")
    for extra in sorted(root.glob("*.yaml")):
        if extra.name in required or extra.name == "credentials.example.yaml":
            continue
        try:
            report.walk_secrets(load(extra), extra.name)
        except yaml.YAMLError as exc:
            report.add(f"{extra.name} is not valid YAML: {exc}")
    return report.problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate an omni-sns-bot workspace.")
    parser.add_argument("workspace", type=Path, help="Directory with profile.yaml and the rest.")
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="Accept blank template values and an undecided login.",
    )
    args = parser.parse_args(argv)
    root = args.workspace
    if not root.is_dir():
        sys.stderr.write(f"not a directory: {root}\n")
        return 2
    problems = check_tree(root, args.allow_empty)
    if problems:
        for problem in problems:
            sys.stderr.write(f"- {problem}\n")
        return 1
    sys.stdout.write(f"ok {root}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
