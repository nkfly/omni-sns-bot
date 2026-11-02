# Threads

Status: **implemented** for v0.1. This is the only platform the bot may publish to.

Docs checked against Meta's Threads documentation on **2026-11-02**. Source index: <https://developers.facebook.com/docs/threads>. If a live response disagrees with this folder, trust the live official doc for that call, tell the editor, and do not keep retrying a broken request.

## Pick a mode

| Mode | Open next |
| --- | --- |
| `api` | [`api.md`](api.md), then [`limits.md`](limits.md) |
| `browser` | [`browser.md`](browser.md) after the editor opts in |
| `draft_only` | No file here. Hand the editor the caption. See `core/03-publish.md`. |

Recommend `api` when the bot can do HTTP and has a secret store. The API is the path Meta documents for publishing on someone's behalf.

## What v0.1 covers

- App setup for the editor's own account (Threads Tester is enough while the app is in development).
- Authorization window, short-lived token, 60-day token, refresh.
- Text publish (two-step, and the text-only `auto_publish_text` shortcut).
- Image, video, and carousel described so a bot with HTTP can do them; the helper script is text-only.
- Read the account's posts (for voice) and read replies.
- Reply to a reply on the account's own post.
- Quotas, container status, AI self-disclosure flag, link cap, topic tag.

## What it does not cover

- Webhooks. Poll when the operating loop runs. A scheduler makes that prompt; without one, the editor opens the chat.
- Replying under other people's posts. Leave `reply_to_others` false. The API asks for extra permissions (`threads_keyword_search` or `threads_manage_mentions`) and the default policy still says no.
- Analytics. `threads_manage_insights` exists; v0.1 does not need it.
- Deleting posts, except the rule "ask first". The deletion quota is in `limits.md`.

## Identity check

After any login, the username you see must match `profile.account.handle` (no `@`). If it does not, stop. You are on the wrong account.

Quotas and character rules: [`limits.md`](limits.md). Those numbers are ceilings. The profile cadence is what you actually post.
