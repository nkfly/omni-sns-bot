#!/usr/bin/env python3
"""Threads OAuth helper. Secrets stay in the environment.

  authorize-url   Print the authorization-window URL. Needs the app id and
                  redirect URI. Does not need the app secret.
  exchange        Trade THREADS_CODE for a long-lived token and write it to
                  THREADS_TOKEN_FILE (mode 600, outside any git root).
  refresh         Refresh a long-lived token that is at least 24 hours old.

The token is never printed. Exit 0 on success, 1 on an API or file error,
2 on usage.
"""

from __future__ import annotations

import json
import os
import secrets
import http.client
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from token_store import atomic_write, read_token

VERSION = "0.1.0"
DEFAULT_HOST = "https://graph.threads.com"
AUTHORIZE = "https://threads.com/oauth/authorize"
DEFAULT_SCOPES = (
    "threads_basic,threads_content_publish,threads_read_replies,threads_manage_replies"
)
SECRET_FLAGS = (
    "--token",
    "--access-token",
    "--secret",
    "--app-secret",
    "--password",
    "--client-secret",
    "--code",
)


def emit(payload: dict, code: int) -> int:
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return code


def git_root(start: Path) -> Path | None:
    for parent in [start, *start.parents]:
        if (parent / ".git").exists():
            return parent
    return None


def token_destination_problem(path: Path) -> str | None:
    try:
        resolved = path.expanduser().resolve()
    except OSError as exc:
        return f"cannot resolve token path: {exc}"
    if resolved.is_dir():
        return "token path is a directory"
    root = git_root(resolved.parent)
    if root is not None and (resolved == root or root in resolved.parents):
        return f"refusing to write a token inside a git repo ({root})"
    name = resolved.name.lower()
    if name in {"credentials.yaml", "credentials.json"}:
        return "refusing a credentials.yaml name; use a dedicated token file outside git"
    return None


def authorize_url(app_id: str, redirect_uri: str, scopes: str, state: str) -> str:
    query = urllib.parse.urlencode(
        {
            "client_id": app_id,
            "redirect_uri": redirect_uri,
            "scope": scopes,
            "response_type": "code",
            "state": state,
        }
    )
    return f"{AUTHORIZE}?{query}"


def redact(text: str, secrets_list: list[str]) -> str:
    out = text
    for secret in secrets_list:
        if secret and len(secret) > 4:
            out = out.replace(secret, "[redacted]")
    return out


def http_json(method: str, url: str, form: dict | None, secrets_list: list[str]) -> tuple[int, dict | str]:
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
        return 0, redact(str(exc), secrets_list)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return status, redact(raw, secrets_list)
    if status != 200:
        return status, redact(json.dumps(parsed), secrets_list)
    return status, parsed


def write_token(path: Path, token: str) -> None:
    atomic_write(path, token + "\n")


def env(name: str) -> str:
    return os.environ.get(name, "").strip()


def graph_host() -> str:
    return env("THREADS_GRAPH_HOST") or DEFAULT_HOST


def reject_secret_args(argv: list[str]) -> str | None:
    for arg in argv[1:]:
        name = arg.split("=", 1)[0]
        if name in SECRET_FLAGS:
            return f"refusing {name}: put the secret in the environment, not argv"
    return None


def cmd_authorize_url() -> int:
    app_id = env("THREADS_APP_ID")
    redirect = env("THREADS_REDIRECT_URI")
    if not app_id or not redirect:
        return emit({"ok": False, "error": "set THREADS_APP_ID and THREADS_REDIRECT_URI"}, 2)
    scopes = env("THREADS_SCOPES") or DEFAULT_SCOPES
    state = env("THREADS_STATE") or secrets.token_urlsafe(16)
    url = authorize_url(app_id, redirect, scopes, state)
    return emit({"ok": True, "url": url, "state": state}, 0)


def _require_destination() -> tuple[Path | None, str | None]:
    raw = env("THREADS_TOKEN_FILE")
    if not raw:
        return None, "set THREADS_TOKEN_FILE to a path outside the git repo"
    path = Path(raw).expanduser().resolve()
    problem = token_destination_problem(path)
    if problem:
        return None, problem
    return path, None


def cmd_exchange() -> int:
    needed = {
        "THREADS_APP_ID": env("THREADS_APP_ID"),
        "THREADS_APP_SECRET": env("THREADS_APP_SECRET"),
        "THREADS_REDIRECT_URI": env("THREADS_REDIRECT_URI"),
        "THREADS_CODE": env("THREADS_CODE"),
    }
    missing = [key for key, value in needed.items() if not value]
    if missing:
        return emit({"ok": False, "error": "missing " + ", ".join(missing)}, 2)
    path, problem = _require_destination()
    if problem or path is None:
        return emit({"ok": False, "error": problem}, 2)
    code = needed["THREADS_CODE"]
    if code.endswith("#_"):
        code = code[: -len("#_")]
    secret = needed["THREADS_APP_SECRET"]
    host = graph_host().rstrip("/")
    status, body = http_json(
        "POST",
        f"{host}/oauth/access_token",
        {
            "client_id": needed["THREADS_APP_ID"],
            "client_secret": secret,
            "grant_type": "authorization_code",
            "redirect_uri": needed["THREADS_REDIRECT_URI"],
            "code": code,
        },
        [secret, code],
    )
    if status != 200 or not isinstance(body, dict) or "access_token" not in body:
        message = body.get("error_message") if isinstance(body, dict) else body
        return emit({"ok": False, "error": redact(f"code exchange failed ({status}): {message}", [secret, code])}, 1)
    short = str(body["access_token"])
    user_id = body.get("user_id")
    query = urllib.parse.urlencode(
        {
            "grant_type": "th_exchange_token",
            "client_secret": secret,
            "access_token": short,
        }
    )
    status, long_body = http_json(
        "GET",
        f"{host}/access_token?{query}",
        None,
        [secret, code, short],
    )
    if status != 200 or not isinstance(long_body, dict) or "access_token" not in long_body:
        message = long_body.get("error_message") if isinstance(long_body, dict) else long_body
        return emit({"ok": False, "error": redact(f"long-lived exchange failed ({status}): {message}", [secret, code, short])}, 1)
    try:
        write_token(path, str(long_body["access_token"]))
    except OSError as exc:
        return emit({"ok": False, "error": f"cannot save token: {exc}"}, 1)
    return emit(
        {
            "ok": True,
            "user_id": user_id,
            "expires_in": long_body.get("expires_in"),
            "token_file": str(path),
            "token_written": True,
        },
        0,
    )


def cmd_refresh() -> int:
    token = env("THREADS_ACCESS_TOKEN")
    path, problem = _require_destination()
    if problem or path is None:
        return emit({"ok": False, "error": problem}, 2)
    if not token:
        if not path.is_file():
            return emit({"ok": False, "error": "no THREADS_ACCESS_TOKEN and token file is missing"}, 1)
        try:
            token = read_token(path)
        except (OSError, ValueError) as exc:
            return emit({"ok": False, "error": str(exc)}, 1)
    if not token:
        return emit({"ok": False, "error": "token is empty"}, 1)
    query = urllib.parse.urlencode({"grant_type": "th_refresh_token", "access_token": token})
    status, body = http_json(
        "GET",
        f"{graph_host().rstrip('/')}/refresh_access_token?{query}",
        None,
        [token],
    )
    if status != 200 or not isinstance(body, dict) or "access_token" not in body:
        message = body.get("error_message") if isinstance(body, dict) else body
        return emit(
            {
                "ok": False,
                "error": redact(f"refresh failed ({status}): {message}", [token]),
                "hint": "Refresh only works when the long-lived token is at least 24 hours old and not expired.",
            },
            1,
        )
    try:
        write_token(path, str(body["access_token"]))
    except OSError as exc:
        return emit({"ok": False, "error": f"cannot save token: {exc}"}, 1)
    return emit(
        {
            "ok": True,
            "expires_in": body.get("expires_in"),
            "token_file": str(path),
            "token_written": True,
        },
        0,
    )


def run_self_test() -> int:
    failures: list[str] = []

    def check(cond: bool, label: str) -> None:
        if not cond:
            failures.append(label)

    url = authorize_url("123", "https://example.com/auth/", DEFAULT_SCOPES, "state1")
    check(url.startswith("https://threads.com/oauth/authorize?"), "authorize host")
    check("response_type=code" in url, "response type")
    check("client_id=123" in url, "client id")
    check("client_secret" not in url, "secret not in url")
    check("threads_content_publish" in url, "scope")
    inside = Path(__file__).resolve().parent / "threads-token"
    check(token_destination_problem(inside) is not None, "inside repo blocked")
    check(token_destination_problem(Path("/tmp/omni-sns-token-self-test")) is None, "outside allowed")
    check(
        token_destination_problem(Path("/tmp/credentials.yaml")) is not None,
        "credentials name blocked",
    )
    check(reject_secret_args(["prog", "--code", "abc"]) is not None, "argv code")
    check(reject_secret_args(["prog", "exchange"]) is None, "command ok")

    import io
    from unittest.mock import patch

    # A refresh may return the input token; parsing must not redact that value.
    response = io.BytesIO(b'{"access_token":"DUMMY_SAME_TOKEN"}')
    response.status = 200
    with patch.object(urllib.request, "urlopen", return_value=response):
        status, body = http_json("GET", "https://example.invalid", None, ["DUMMY_SAME_TOKEN"])
    check(status == 200 and body.get("access_token") == "DUMMY_SAME_TOKEN", "refresh preserves token")

    # A code ending in the Meta redirect suffix is stripped. Unit-test the slice.
    code = "AQBx-hBsH3#_"
    check(code.endswith("#_") and code[: -len("#_")] == "AQBx-hBsH3", "strip hash")

    if failures:
        return emit({"ok": False, "failures": failures}, 1)
    return emit({"ok": True, "self_test": True, "version": VERSION}, 0)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    problem = reject_secret_args(argv)
    if problem:
        return emit({"ok": False, "error": problem}, 2)
    if len(argv) < 2 or argv[1] in {"-h", "--help"}:
        return emit(
            {
                "ok": False,
                "error": "usage: oauth_exchange.py authorize-url|exchange|refresh|--self-test",
            },
            2,
        )
    command = argv[1]
    if command == "--self-test":
        return run_self_test()
    if command == "authorize-url":
        return cmd_authorize_url()
    if command == "exchange":
        return cmd_exchange()
    if command == "refresh":
        return cmd_refresh()
    return emit({"ok": False, "error": f"unknown command {command}"}, 2)


if __name__ == "__main__":
    sys.exit(main())
