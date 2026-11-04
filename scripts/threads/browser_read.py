#!/usr/bin/env python3
"""Bounded, read-only access to an explicitly selected Chrome Threads tab.

macOS only; stdlib only. No cookies, hidden API calls, arbitrary JavaScript,
composer actions, or sends. The editor's consent is required before opening,
reading or scrolling a page. Probe does not launch Chrome or inspect tabs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit


OPEN_SCRIPT = '''on run argv
tell application "Google Chrome"
    activate
    repeat with w in windows
        repeat with tabIndex from 1 to count of tabs of w
            set t to tab tabIndex of w
            if (URL of t) is (item 1 of argv) or (URL of t) is ((item 1 of argv) & "/") then
                set active tab index of w to tabIndex
                set index of w to 1
                return id of t as text
            end if
        end repeat
    end repeat
    if (count windows) is 0 then make new window
    set t to make new tab at end of tabs of front window with properties {URL:item 1 of argv}
    return id of t as text
end tell
end run'''

READ_SCRIPT = '''on run argv
tell application "Google Chrome"
    repeat with w in windows
        repeat with t in tabs of w
            if (id of t as text) is (item 1 of argv) then
                return execute t javascript (item 2 of argv)
            end if
        end repeat
    end repeat
    error "Selected tab no longer exists"
end tell
end run'''

PAGE_SCRIPT = r'''(() => {
  const expected = EXPECTED_URL;
  if (location.origin + location.pathname.replace(/\/$/, '') !== expected)
    throw new Error('Selected tab changed; stop and reselect the requested page');
  const visible = el => !!el.getClientRects().length;
  if ([...document.querySelectorAll('input[type="password"]')].some(visible))
    return JSON.stringify({blocked: 'login', page_url: location.href});
  const headings = [...document.querySelectorAll('h1,h2,[role="dialog"]')]
    .filter(visible).map(el => el.innerText).join('\n');
  if (/confirm your identity|unusual activity|security check|captcha/i.test(headings))
    return JSON.stringify({blocked: 'checkpoint', page_url: location.href});
  const root = document.querySelector('main,[role="main"]') || document.body;
  const text = root.innerText;
  const profileNav = [...document.querySelectorAll('a[href]')].filter(visible)
    .filter(a => [a.getAttribute('aria-label'), a.innerText,
      ...[...a.querySelectorAll('svg[aria-label],svg title')]
        .map(e => e.getAttribute('aria-label') || e.textContent)]
      .some(s => /^(Profile|個人檔案|個人資料|プロフィール)$/.test(s || '')))
    .map(a => ({url: a.href, text: a.innerText}));
  const owner = new URL(expected).pathname.split('/')[1];
  const postURL = href => {
    const u = new URL(href, location.href);
    return u.origin === location.origin && /^\/@[^/]+\/post\/[^/]+\/?$/.test(u.pathname)
      ? u.origin + u.pathname.replace(/\/$/, '') : null;
  };
  const posts = [], seen = new Set();
  for (const a of [...root.querySelectorAll('a[href]')].filter(visible)) {
    const url = postURL(a.href);
    if (!url || new URL(url).pathname.split('/')[1] !== owner || seen.has(url)) continue;
    seen.add(url);
    let block = a;
    for (let node = a.parentElement, depth = 0; node && depth < 18; node = node.parentElement, depth++) {
      if (['BODY','MAIN','HTML'].includes(node.tagName)) break;
      const ids = new Set([...node.querySelectorAll('a[href]')].map(x => postURL(x.href)).filter(Boolean));
      if (ids.size !== 1 || node.innerText.length > 14000) break;
      block = node;
    }
    const raw = block.innerText;
    posts.push({url, displayed_time: a.innerText, visible_text: raw.slice(0, 14000),
      truncated: raw.length > 14000});
    if (posts.length >= 30) break;
  }
  const result = {page_url: location.href, observed_at: new Date().toISOString(),
    document_ready: document.readyState, profile_navigation: profileNav,
    visible_text: text.slice(0, 40000), truncated: text.length > 40000, post_blocks: posts,
    coverage: 'Current visible DOM only; blocks may include UI or quotes. Not a full export or authenticated identity proof by itself.'};
  if (SHOULD_SCROLL) window.scrollBy(0, Math.round(window.innerHeight * 0.85));
  return JSON.stringify(result);
})()'''


def threads_url(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Threads URL must be a string")
    parts = urlsplit(value)
    if (parts.scheme != "https" or parts.netloc not in {"www.threads.com", "www.threads.net"}
            or parts.query or parts.fragment
            or not re.fullmatch(r"/@[A-Za-z0-9_.]+(?:/post/[A-Za-z0-9_-]+)?/?", parts.path)):
        raise ValueError("use an exact HTTPS Threads profile or post URL without query or fragment")
    return value.rstrip("/")


def run_script(script: str, *arguments: str) -> str:
    if sys.platform != "darwin":
        raise ValueError("this optional helper requires macOS Chrome; use another verified browser tool or draft_only")
    try:
        result = subprocess.run(["/usr/bin/osascript", "-e", script, *arguments],
                                capture_output=True, text=True, timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError("Chrome automation unavailable or timed out; check the editor's permission prompt") from exc
    if result.returncode:
        raise ValueError("Chrome refused the operation. Check macOS automation permission and Chrome's "
                         "Allow JavaScript from Apple Events setting. Do not bypass a restriction. "
                         + result.stderr.strip()[:600])
    return result.stdout.strip()


def open_page(url: str) -> str:
    tab_id = run_script(OPEN_SCRIPT, threads_url(url))
    if not re.fullmatch(r"[0-9]{1,20}", tab_id):
        raise ValueError("Chrome returned no valid tab id")
    return tab_id


def read_page(url: str, tab_id: str, scroll: bool = False) -> dict:
    expected = threads_url(url)
    if not re.fullmatch(r"[0-9]{1,20}", tab_id):
        raise ValueError("--tab-id must be a numeric Chrome tab id")
    script = PAGE_SCRIPT.replace("EXPECTED_URL", json.dumps(expected)).replace("SHOULD_SCROLL", str(scroll).lower())
    try:
        data = json.loads(run_script(READ_SCRIPT, tab_id, script))
    except json.JSONDecodeError as exc:
        raise ValueError("page is not readable yet; wait and retry read, never claim posts were collected") from exc
    if not isinstance(data, dict) or data.get("blocked"):
        raise ValueError("page requires login or a checkpoint; stop for the editor")
    if threads_url(data.get("page_url", "")) != expected:
        raise ValueError("selected tab changed; stop and reselect the requested page")
    return data


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["probe", "open", "read", "scroll"])
    parser.add_argument("--url")
    parser.add_argument("--tab-id")
    parser.add_argument("--consent-read", action="store_true", help="Editor explicitly authorized this read-only page scope.")
    args = parser.parse_args(argv)
    try:
        if args.action == "probe":
            result = {"ok": True, "macos": sys.platform == "darwin",
                      "chrome_installed": sys.platform == "darwin" and Path("/Applications/Google Chrome.app").is_dir(),
                      "browser_verified": False,
                      "note": "Installation is not permission or a successful read. No tabs inspected or browser launched."}
        else:
            if not args.consent_read or not args.url:
                raise ValueError("opening, reading and scrolling require --url and explicit --consent-read")
            url = threads_url(args.url)
            if args.action == "open":
                result = {"ok": True, "page_url": url, "tab_id": open_page(url)}
            else:
                if not args.tab_id:
                    raise ValueError("read/scroll require the tab id returned by open")
                result = {"ok": True, **read_page(url, args.tab_id, scroll=args.action == "scroll")}
    except ValueError as exc:
        result = {"ok": False, "error": str(exc)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
