#!/usr/bin/env python3
"""Publish one Threads text post, or preview it without the network.

Secrets come from the environment (THREADS_ACCESS_TOKEN) or from
THREADS_TOKEN_FILE (a file outside the git root). They are never accepted
as command-line arguments.

Exit codes: 0 ok, 1 validation or API failure, 2 bad usage.
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from token_store import atomic_write, read_token, sync_directory

VERSION = "0.1.0"
DEFAULT_HOST = "https://graph.threads.com"
MAX_UNITS = 500
MAX_LINKS = 5
REPLY_CONTROLS = {
    "everyone",
    "accounts_you_follow",
    "mentioned_only",
    "parent_post_author_only",
    "followers_only",
}
URL_RE = re.compile(r"(?i)\b((?:https?://|www\.)[^\s<>\[\]{}]+)")
TRAILING_PUNCT = ".,);:!?\"'"
SECRET_FLAGS = (
    "--token",
    "--access-token",
    "--secret",
    "--app-secret",
    "--password",
    "--client-secret",
)


def estimate_threads_length(text: str) -> int:
    """Conservative stand-in for Meta's rule: emoji count as UTF-8 bytes.

    Ordinary characters (including CJK) count as 1. Non-BMP characters, the
    zero-width joiner, variation selectors, the keycap combiner, and a few
    BMP symbol blocks count as their UTF-8 byte length. The API remains the
    authority; this estimate is biased long so a passing draft is unlikely
    to be rejected for length.
    """
    total = 0
    for ch in text:
        cp = ord(ch)
        if _emoji_like(cp):
            total += len(ch.encode("utf-8"))
        else:
            total += 1
    return total


def _emoji_like(cp: int) -> bool:
    if cp > 0xFFFF:
        return True
    if cp in (0x200D, 0xFE0E, 0xFE0F, 0x20E3):
        return True
    if 0x2600 <= cp <= 0x27BF or 0x2B00 <= cp <= 0x2BFF:
        return True
    return False


def extract_links(text: str) -> list[str]:
    found: list[str] = []
    for match in URL_RE.finditer(text):
        raw = match.group(1).rstrip(TRAILING_PUNCT)
        if raw and raw not in found:
            found.append(raw)
    return found


def link_count(text: str, link_attachment: str) -> int:
    links = extract_links(text)
    extra = link_attachment.strip()
    if extra and extra not in links:
        return len(links) + 1
    return len(links)


def validate_topic_tag(tag: str) -> str | None:
    if tag == "":
        return None
    if "." in tag or "&" in tag:
        return "topic tag cannot contain '.' or '&'"
    if not 1 <= len(tag) <= 50:
        return "topic tag must be 1 to 50 characters"
    return None


def validate_post(
    text: str,
    link_attachment: str = "",
    topic_tag: str = "",
    reply_control: str = "",
    reply_to: str = "",
    auto_publish: bool = False,
) -> list[str]:
    errors: list[str] = []
    if text.strip() == "":
        errors.append("text is empty")
    units = estimate_threads_length(text)
    if units > MAX_UNITS:
        errors.append(f"text is {units} units; Threads allows {MAX_UNITS}")
    if link_count(text, link_attachment) > MAX_LINKS:
        errors.append(f"more than {MAX_LINKS} unique links")
    tag_error = validate_topic_tag(topic_tag)
    if tag_error:
        errors.append(tag_error)
    if reply_control and reply_control not in REPLY_CONTROLS:
        errors.append(f"reply_control must be one of {sorted(REPLY_CONTROLS)}")
    if auto_publish and reply_to:
        errors.append("auto_publish_text is not used for replies; publish in two steps")
    if link_attachment and not (
        link_attachment.startswith("http://") or link_attachment.startswith("https://")
    ):
        errors.append("link_attachment must be an http(s) URL")
    return errors


def git_root(start: Path) -> Path | None:
    for parent in [start, *start.parents]:
        if (parent / ".git").exists():
            return parent
    return None


def token_file_problem(path: Path) -> str | None:
    try:
        resolved = path.expanduser().resolve()
    except OSError as exc:
        return f"cannot resolve token file: {exc}"
    root = git_root(resolved.parent)
    if root is not None and (resolved == root or root in resolved.parents):
        return f"refusing to read a token file inside a git repo ({root})"
    return None


def load_token() -> tuple[str, str | None]:
    env = os.environ.get("THREADS_ACCESS_TOKEN", "").strip()
    if env:
        return env, None
    raw = os.environ.get("THREADS_TOKEN_FILE", "").strip()
    if not raw:
        return "", "set THREADS_ACCESS_TOKEN or THREADS_TOKEN_FILE"
    path = Path(raw).expanduser().resolve()
    problem = token_file_problem(path)
    if problem:
        return "", problem
    if not path.is_file():
        return "", f"token file not found: {path}"
    try:
        token = read_token(path)
    except (OSError, ValueError) as exc:
        return "", str(exc)
    return token, None


def redact(text: str, secrets: list[str]) -> str:
    out = text
    for secret in secrets:
        if secret and len(secret) > 4:
            out = out.replace(secret, "[redacted]")
    return out


def emit(payload: dict, code: int) -> int:
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return code


def graph_host() -> str:
    return os.environ.get("THREADS_GRAPH_HOST", DEFAULT_HOST).rstrip("/")


def user_id_from(args: argparse.Namespace) -> str:
    if args.user_id:
        return args.user_id
    return os.environ.get("THREADS_USER_ID", "me").strip() or "me"


def form_body(text: str, args: argparse.Namespace, token: str | None) -> dict[str, str]:
    form = {"media_type": "TEXT", "text": text}
    if args.link:
        form["link_attachment"] = args.link
    if args.topic_tag:
        form["topic_tag"] = args.topic_tag
    if args.reply_control:
        form["reply_control"] = args.reply_control
    if args.reply_to:
        form["reply_to_id"] = args.reply_to
    if args.disclose_ai:
        form["is_made_with_ai"] = "true"
    if args.auto_publish:
        form["auto_publish_text"] = "true"
    form["access_token"] = "[from environment]" if token is None else token
    return form


def request(method: str, url: str, form: dict | None, secrets: list[str]) -> tuple[int, dict | str]:
    data = None
    if form is not None:
        data = urllib.parse.urlencode(form).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"User-Agent": f"omni-sns-bot/{VERSION}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            raw = response.read().decode("utf-8", errors="replace")
            status = response.status
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        status = exc.code
    except (OSError, http.client.HTTPException) as exc:
        return 0, redact(str(exc), secrets)
    raw = redact(raw, secrets)
    try:
        return status, json.loads(raw)
    except json.JSONDecodeError:
        return status, raw


def error_message(body: dict | str) -> str:
    if isinstance(body, dict):
        if "error_message" in body:
            return str(body["error_message"])
        err = body.get("error")
        if isinstance(err, dict) and "message" in err:
            return str(err["message"])
        if isinstance(err, str):
            return err
    return str(body)


def check_quota(uid: str, token: str, reply: bool = False) -> dict | str:
    query = urllib.parse.urlencode(
        {
            "fields": "quota_usage,config,reply_quota_usage,reply_config" if reply else "quota_usage,config",
            "access_token": token,
        }
    )
    url = f"{graph_host()}/v1.0/{urllib.parse.quote(uid)}/threads_publishing_limit?{query}"
    status, body = request("GET", url, None, [token])
    if status != 200 or not isinstance(body, dict):
        return f"quota check failed ({status}): {error_message(body)}"
    data = body.get("data")
    if not isinstance(data, list) or not data or not isinstance(data[0], dict):
        return "quota check returned no data; not publishing"
    row = data[0]
    required = [("post", "quota_usage", "config")]
    if reply:
        required.append(("reply", "reply_quota_usage", "reply_config"))
    for label, usage_key, config_key in required:
        config = row.get(config_key)
        usage = row.get(usage_key)
        total = config.get("quota_total") if isinstance(config, dict) else None
        if type(usage) is not int or type(total) is not int or usage < 0 or total <= 0:
            return f"quota check returned missing or invalid {label} quota; not publishing"
        if usage >= total:
            return f"{label} quota full ({usage}/{total})"
    return {"quota_usage": row["quota_usage"], "quota_total": row["config"]["quota_total"], "raw": row}


def save_attempt(path: Path, attempt: dict, initial: bool = False) -> None:
    """Reserve one attempt per calendar item before any create request."""
    text = json.dumps(attempt, ensure_ascii=False, indent=2) + "\n"
    if not initial:
        atomic_write(path, text)
        return
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    sync_directory(path.parent)


def recover_attempt(path: Path, uid: str, token: str) -> int:
    """Read status only. Recovery never creates or publishes a container."""
    try:
        attempt = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(attempt, dict):
            raise ValueError("invalid state file")
        if attempt.get("user_id") != uid or attempt.get("host") != graph_host():
            raise ValueError("state file belongs to a different account or host")
        creation_id = attempt.get("creation_id")
        if not isinstance(creation_id, str) or not creation_id:
            raise ValueError("create result unknown; inspect the account's posts before any new attempt")
    except (OSError, ValueError) as exc:
        return emit({"ok": False, "recovery_required": True, "error": str(exc)}, 1)
    query = urllib.parse.urlencode({"fields": "status,error_message", "access_token": token})
    status, body = request("GET", f"{graph_host()}/v1.0/{urllib.parse.quote(creation_id, safe='')}?{query}", None, [token])
    if status != 200 or not isinstance(body, dict):
        return emit({"ok": False, "recovery_required": True, "creation_id": creation_id,
                     "error": f"status check failed ({status}): {error_message(body)}"}, 1)
    state = body.get("status")
    return emit({"ok": state == "PUBLISHED", "creation_id": creation_id,
                 "container_status": state, "recovery_required": state != "PUBLISHED",
                 "note": "Read-only recovery. Reconcile with the calendar and account; do not rerun create."},
                0 if state == "PUBLISHED" else 1)


def poll_until_ready(container_id: str, token: str, sleep) -> tuple[str, str]:
    """Return (status, error_message). Poll at most once a minute, <= 5 minutes."""
    url_query = urllib.parse.urlencode(
        {"fields": "status,error_message", "access_token": token}
    )
    url = f"{graph_host()}/v1.0/{urllib.parse.quote(container_id)}?{url_query}"
    sleep(30)
    last_error = ""
    for attempt in range(5):
        status_code, body = request("GET", url, None, [token])
        if status_code == 200 and isinstance(body, dict):
            state = str(body.get("status", ""))
            last_error = str(body.get("error_message", "") or "")
            if state in {"FINISHED", "PUBLISHED", "ERROR", "EXPIRED"}:
                return state, last_error
        if attempt < 4:
            sleep(60)
    return "TIMEOUT", last_error


def read_text(args: argparse.Namespace) -> str:
    if args.text_file:
        return Path(args.text_file).read_text(encoding="utf-8")
    return args.text or ""


def reject_secret_args(argv: list[str]) -> str | None:
    for arg in argv[1:]:
        name = arg.split("=", 1)[0]
        if name in SECRET_FLAGS:
            return f"refusing {name}: put the secret in the environment, not argv"
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Publish a Threads text post (v0.1).")
    parser.add_argument("--text", help="Caption. Prefer --text-file for multiline text.")
    parser.add_argument("--text-file", help="UTF-8 file containing the caption only.")
    parser.add_argument("--link", default="", help="link_attachment URL (text posts).")
    parser.add_argument("--topic-tag", default="")
    parser.add_argument("--reply-to", default="", help="Media id to reply to.")
    parser.add_argument("--reply-control", default="")
    parser.add_argument("--disclose-ai", action="store_true", help="Set is_made_with_ai=true.")
    parser.add_argument(
        "--auto-publish",
        action="store_true",
        help="Text-only shortcut. Not valid together with --reply-to.",
    )
    parser.add_argument("--user-id", default="", help="Defaults to THREADS_USER_ID or me.")
    parser.add_argument("--state-file", type=Path, help="Private attempt journal for this calendar item; required for real publishing.")
    parser.add_argument("--recover", action="store_true", help="Read container status from --state-file. Never publishes.")
    parser.add_argument("--dry-run", action="store_true", help="Validate locally. No network, no token.")
    parser.add_argument("--check-limit", action="store_true", help="Print the publishing quota and exit.")
    parser.add_argument("--self-test", action="store_true", help="Run local checks. No network.")
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    problem = reject_secret_args(argv)
    if problem:
        return emit({"ok": False, "error": problem}, 2)
    args = build_parser().parse_args(argv[1:])
    if args.self_test:
        return run_self_test()

    if args.recover:
        if not args.state_file or args.dry_run or args.check_limit:
            return emit({"ok": False, "error": "--recover requires --state-file and cannot combine with --dry-run or --check-limit"}, 2)
        token, err = load_token()
        if err:
            return emit({"ok": False, "error": err}, 1)
        return recover_attempt(args.state_file.expanduser().absolute(), user_id_from(args), token)

    if args.dry_run and args.check_limit:
        return emit({"ok": False, "error": "--dry-run cannot combine with --check-limit"}, 2)

    if args.check_limit:
        token, err = load_token()
        if err:
            return emit({"ok": False, "error": err}, 1)
        uid = user_id_from(args)
        quota = check_quota(uid, token, reply=bool(args.reply_to))
        if isinstance(quota, str):
            return emit({"ok": False, "error": quota}, 1)
        return emit({"ok": True, "quota": quota}, 0)

    if not args.text and not args.text_file:
        return emit({"ok": False, "error": "pass --text or --text-file"}, 2)
    text = read_text(args)
    errors = validate_post(
        text,
        link_attachment=args.link,
        topic_tag=args.topic_tag,
        reply_control=args.reply_control,
        reply_to=args.reply_to,
        auto_publish=args.auto_publish,
    )
    if errors:
        return emit({"ok": False, "error": "; ".join(errors), "length": estimate_threads_length(text)}, 1)

    preview = {
        "method": "POST",
        "path": f"/v1.0/{user_id_from(args)}/threads",
        "form": form_body(text, args, token=None),
    }
    if args.dry_run:
        return emit(
            {
                "ok": True,
                "dry_run": True,
                "length": estimate_threads_length(text),
                "links": extract_links(text),
                "link_count": link_count(text, args.link),
                "request": preview,
            },
            0,
        )

    if not args.state_file:
        return emit({"ok": False, "error": "pass --state-file for this calendar item so interruptions can be recovered"}, 2)
    state_path = args.state_file.expanduser().absolute()
    if state_path.exists() or state_path.is_symlink():
        return emit({"ok": False, "recovery_required": True,
                     "error": "state file already exists; use --recover, never rerun create"}, 1)
    token, err = load_token()
    if err:
        return emit({"ok": False, "error": err}, 1)
    uid = user_id_from(args)
    quota = check_quota(uid, token, reply=bool(args.reply_to))
    if isinstance(quota, str):
        return emit({"ok": False, "error": quota}, 1)

    attempt = {"user_id": uid, "host": graph_host(), "phase": "create_result_unknown"}
    try:
        save_attempt(state_path, attempt, initial=True)
    except OSError as exc:
        return emit({"ok": False, "error": f"cannot reserve state file: {exc}"}, 1)
    create_url = f"{graph_host()}/v1.0/{urllib.parse.quote(uid)}/threads"
    status, body = request("POST", create_url, form_body(text, args, token), [token])
    if status != 200 or not isinstance(body, dict) or "id" not in body:
        return emit({"ok": False, "recovery_required": True, "error": f"container failed ({status}): {error_message(body)}"}, 1)
    creation_id = str(body["id"])
    attempt.update(creation_id=creation_id, phase="container_created")
    try:
        save_attempt(state_path, attempt)
    except OSError as exc:
        return emit({"ok": False, "creation_id": creation_id, "recovery_required": True,
                     "error": f"cannot save container id; record it in the calendar: {exc}"}, 1)
    if args.auto_publish:
        return emit(
            {
                "ok": True,
                "dry_run": False,
                "creation_id": creation_id,
                "media_id": None,
                "auto_publish_text": True,
                "length": estimate_threads_length(text),
                "quota_usage": quota["quota_usage"],
                "note": "Create returned a container id. Confirm the post on the profile before creating another.",
            },
            0,
        )

    state, detail = poll_until_ready(creation_id, token, time.sleep)
    if state == "PUBLISHED":
        return emit(
            {
                "ok": True,
                "dry_run": False,
                "creation_id": creation_id,
                "media_id": None,
                "container_status": state,
                "note": "container already published; not calling threads_publish again",
            },
            0,
        )
    if state != "FINISHED":
        return emit(
            {
                "ok": False,
                "error": f"container status {state}: {detail}".strip(),
                "creation_id": creation_id,
            },
            1,
        )
    publish_url = f"{graph_host()}/v1.0/{urllib.parse.quote(uid)}/threads_publish"
    attempt["phase"] = "publish_result_unknown"
    try:
        save_attempt(state_path, attempt)
    except OSError as exc:
        return emit({"ok": False, "creation_id": creation_id, "error": f"cannot save publish intent: {exc}"}, 1)
    status, body = request(
        "POST",
        publish_url,
        {"creation_id": creation_id, "access_token": token},
        [token],
    )
    if status != 200 or not isinstance(body, dict) or "id" not in body:
        return emit(
            {
                "ok": False,
                "error": f"publish failed ({status}): {error_message(body)}",
                "creation_id": creation_id,
                "recovery_required": True,
            },
            1,
        )
    attempt.update(phase="published", media_id=str(body["id"]))
    try:
        save_attempt(state_path, attempt)
    except OSError as exc:
        return emit({"ok": True, "creation_id": creation_id, "media_id": str(body["id"]),
                     "note": f"Published, but state update failed; record ids in the calendar: {exc}"}, 0)
    return emit(
        {
            "ok": True,
            "dry_run": False,
            "creation_id": creation_id,
            "media_id": str(body["id"]),
            "length": estimate_threads_length(text),
            "quota_usage": quota["quota_usage"],
        },
        0,
    )


def run_self_test() -> int:
    failures: list[str] = []

    def check(cond: bool, label: str) -> None:
        if not cond:
            failures.append(label)

    check(estimate_threads_length("hello") == 5, "ascii length")
    check(estimate_threads_length("你好") == 2, "cjk length")
    check(estimate_threads_length("😀") == 4, "emoji bytes")
    heart = "\u2764\ufe0f"
    check(estimate_threads_length(heart) == 6, f"heart+vs16 counted {estimate_threads_length(heart)}")
    check(validate_post("a" * 500) == [], "500 ok")
    check(any("500" in err or "units" in err for err in validate_post("a" * 501)), "501 blocked")
    check(validate_post("  \n") != [], "blank blocked")
    six = " ".join(f"https://example.com/{i}" for i in range(6))
    check(any("links" in err for err in validate_post(six)), "6 links blocked")
    five = " ".join(f"https://example.com/{i}" for i in range(5))
    check(validate_post(five) == [], "5 links ok")
    check(link_count("see https://example.com/a and https://example.com/a", "") == 1, "dedupe")
    check(link_count("https://example.com/a", "https://example.com/a") == 1, "attachment dedupe")
    check(link_count("https://example.com/a", "https://example.com/b") == 2, "attachment adds")
    check(validate_topic_tag("fine") is None, "tag ok")
    check(validate_topic_tag("no.periods") is not None, "tag period")
    check(validate_topic_tag("a" * 51) is not None, "tag length")
    check(any("reply_control" in err for err in validate_post("hi", reply_control="nope")), "bad control")
    check(
        any("auto_publish" in err for err in validate_post("hi", reply_to="1", auto_publish=True)),
        "auto reply blocked",
    )
    check(reject_secret_args(["prog", "--token", "abc"]) is not None, "argv token")
    check(reject_secret_args(["prog", "--text", "hi"]) is None, "argv text")

    from unittest.mock import patch

    row = {"quota_usage": 0, "config": {"quota_total": 250},
           "reply_quota_usage": 1000, "reply_config": {"quota_total": 1000}}
    with patch.dict(check_quota.__globals__, request=lambda *a: (200, {"data": [row]})):
        check(isinstance(check_quota("me", "dummy", reply=True), str), "exhausted reply quota blocked")
    with patch.dict(check_quota.__globals__, request=lambda *a: (200, {"data": [{}]})):
        check(isinstance(check_quota("me", "dummy"), str), "missing quota blocked")

    repo_file = Path(__file__).resolve()
    check(token_file_problem(repo_file) is not None, "token in repo blocked")
    outside = Path("/tmp/omni-sns-bot-not-a-real-token")
    check(token_file_problem(outside) is None, "token outside repo allowed")

    # dry-run must not echo a token that happens to be in the environment
    previous = os.environ.get("THREADS_ACCESS_TOKEN")
    os.environ["THREADS_ACCESS_TOKEN"] = "SUPERSECRETTOKENVALUE"
    try:
        import io
        from contextlib import redirect_stdout

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["publish_text.py", "--dry-run", "--text", "hello from self test"])
        output = buffer.getvalue()
    finally:
        if previous is None:
            os.environ.pop("THREADS_ACCESS_TOKEN", None)
        else:
            os.environ["THREADS_ACCESS_TOKEN"] = previous
    check(code == 0, "dry-run exit")
    check("SUPERSECRETTOKENVALUE" not in output, "dry-run leaked token")
    check("[from environment]" in output, "dry-run placeholder")
    check("SUPERSECRET" not in output, "dry-run leaked prefix")

    if failures:
        return emit({"ok": False, "failures": failures}, 1)
    return emit({"ok": True, "self_test": True, "version": VERSION}, 0)


if __name__ == "__main__":
    sys.exit(main())
