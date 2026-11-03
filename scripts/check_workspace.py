#!/usr/bin/env python3
"""Check a workspace (or the example) for required keys and leaked secrets.

Needs PyYAML. Does not call Threads. Exit 0 when the tree matches the v0.1
contract. Pass --allow-empty for the blank templates, where strings may be
blank and login may still be undecided.
"""

from __future__ import annotations

import argparse
import re
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
STORAGE_VALUES = {"local_files", "memory_card", "external"}
REPLY_HOLDS = {
    "sensitive_triage",
    "dont_list_borderline",
    "delete_or_hide",
    "reply_to_someone_elses_post",
    "brand_new_idea_same_turn",
}
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


def clock_minutes(value) -> int | None:
    """Strict HH:MM; normalize a user's 24:00 to next-day 00:00 before saving."""
    if not isinstance(value, str) or not re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", value):
        return None
    hour, minute = map(int, value.split(":"))
    return 60 * hour + minute


def check_cadence(profile, report: Report, allow_empty: bool) -> None:
    cadence, exists = dig(profile, "cadence")
    if not exists or not isinstance(cadence, dict):
        report.add("cadence must be a mapping")
        return
    for key in ("posts_per_week", "min_posts_per_week", "max_posts_per_day", "max_replies_per_day", "buffer_min"):
        if key not in cadence:
            continue  # Optional additions remain compatible with older workspaces.
        value = cadence[key]
        if key == "max_replies_per_day" and value is None:
            continue  # No editor-defined cap; adapter/platform ceilings still apply.
        if type(value) is not int or value < 0:
            report.add(f"cadence.{key} must be a non-negative integer" + (" or null" if key == "max_replies_per_day" else ""))
    minimum = cadence.get("min_posts_per_week", 0)
    weekly = cadence.get("posts_per_week")
    daily = cadence.get("max_posts_per_day")
    if type(minimum) is int and minimum >= 0:
        ceilings = [x for x in (weekly, daily * 7 if type(daily) is int else None) if type(x) is int and x >= 0]
        if ceilings and minimum > min(ceilings):
            report.add("cadence.min_posts_per_week exceeds the weekly or daily ceiling")
    windows = cadence.get("windows", [])
    if not isinstance(windows, list):
        report.add("cadence.windows must be a list")
        return
    method, _ = dig(profile, "login.method")
    if not allow_empty and not windows and method in {"api", "browser"} and daily != 0:
        report.add("cadence.windows must define posting hours before live publishing")
    days = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
    for index, window in enumerate(windows):
        trail = f"cadence.windows[{index}]"
        if not isinstance(window, dict):
            report.add(f"{trail} must be a mapping")
            continue
        selected_days = window.get("days")
        if (not isinstance(selected_days, list) or not selected_days
                or any(not isinstance(day, str) or day not in days for day in selected_days)):
            report.add(f"{trail}.days must list weekdays mon through sun")
        start, end = clock_minutes(window.get("start")), clock_minutes(window.get("end"))
        if start is None or end is None:
            report.add(f"{trail} needs HH:MM times; save 24:00 as 00:00 with end_next_day: true")
            continue
        next_day = window.get("end_next_day", False)
        if type(next_day) is not bool:
            report.add(f"{trail}.end_next_day must be boolean")
        elif start == end or (end < start) != next_day:
            report.add(f"{trail} must be non-empty and cross midnight only with end_next_day: true")
    quiet = cadence.get("quiet_hours")
    if quiet is not None:
        if not isinstance(quiet, dict):
            report.add("cadence.quiet_hours must be a mapping")
        elif not (allow_empty and not quiet.get("start") and not quiet.get("end")):
            if clock_minutes(quiet.get("start")) is None or clock_minutes(quiet.get("end")) is None:
                report.add("cadence.quiet_hours needs HH:MM start and end")


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
    avoid, exists = dig(profile, "topics.avoid")
    confirmed, _ = dig(profile, "topics.avoid_confirmed")
    if exists and (not isinstance(avoid, list) or any(not isinstance(topic, str) or not topic.strip() for topic in avoid)):
        report.add("topics.avoid must be a list of non-empty topic names; [] means none")
    elif exists and not avoid and not allow_empty and confirmed is not True:
        report.add("confirm topics.avoid_confirmed: true when the editor explicitly has no excluded topics")
    if confirmed is not None and type(confirmed) is not bool:
        report.add("topics.avoid_confirmed must be boolean")
    check_cadence(profile, report, allow_empty)
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
    opted_in, _ = dig(profile, "login.browser_opt_in")
    if not allow_empty and method == "browser" and opted_in is not True:
        report.add("login.browser_opt_in must be true for browser mode")
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


def faq_reply_bypasses_first_ten(
    policy: dict,
    *,
    triage: str,
    source: str,
    sensitivity: str,
    risk: str,
    holds: list | None = None,
) -> bool:
    """Mirror the reply exception in docs/operating-loop.md. Posts never use it.

    Quotas, cadence and disclosure are still enforced by the operating loop.
    `first_ten_posts` is a post gate, so it is not a hold on this exception.
    """
    if not isinstance(policy, dict) or policy.get("auto_approve_faq_replies_before_ten_posts") is not True:
        return False
    if triage != "answer_from_faq" or source != "editor":
        return False
    if sensitivity != "low" or risk != "low":
        return False
    blocked = set(holds or [])
    blocked.discard("first_ten_posts")
    return not bool(blocked & REPLY_HOLDS)


def check_capabilities(data, report: Report) -> None:
    if not isinstance(data, dict):
        report.add("capabilities.yaml must be a mapping")
        return
    storage = data.get("storage")
    if storage not in STORAGE_VALUES:
        report.add("capabilities.storage must be local_files, memory_card, or external")


def check_setup_state(data, report: Report) -> None:
    if not isinstance(data, dict):
        report.add("setup-state.yaml must be a mapping")
        return
    for field, choices in (
        ("phase", {"capabilities", "profile", "voice", "connection", "faq", "handoff"}),
        ("status", {"in_progress", "ready", "paused"}),
        ("session_intent", {"setup_only", "drafting", "publishing_review"}),
    ):
        value = data.get(field)
        if not isinstance(value, str) or value not in choices:
            report.add(f"setup-state.{field} must be one of {', '.join(sorted(choices))}")
    for field in ("confirmed_fields", "pending_questions", "deferred_fields", "decisions"):
        if not isinstance(data.get(field), list):
            report.add(f"setup-state.{field} must be a list")
    decisions = data.get("decisions")
    if isinstance(decisions, list):
        for index, decision in enumerate(decisions):
            if (not isinstance(decision, dict) or not isinstance(decision.get("scope"), str)
                    or decision["scope"] not in {"style", "reply_template", "public_action"}
                    or not isinstance(decision.get("item_id"), str) or not decision["item_id"].strip()):
                report.add(f"setup-state.decisions[{index}] needs an item_id and style|reply_template|public_action scope")


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
    flag, ok = dig(policy, "auto_approve_faq_replies_before_ten_posts")
    if not ok:
        report.add("missing auto_approve_faq_replies_before_ten_posts")
    elif type(flag) is not bool:
        report.add("auto_approve_faq_replies_before_ten_posts must be false unless the editor explicitly enables it")


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
    capabilities = root / "capabilities.yaml"
    if capabilities.is_file():
        try:
            check_capabilities(load(capabilities), report)
        except yaml.YAMLError as exc:
            report.add(f"capabilities.yaml is not valid YAML: {exc}")
    for extra in sorted(root.glob("*.yaml")):
        if extra.name in required or extra.name == "credentials.example.yaml":
            continue
        try:
            data = load(extra)
            if extra.name == "setup-state.yaml":
                check_setup_state(data, report)
            report.walk_secrets(data, extra.name)
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
