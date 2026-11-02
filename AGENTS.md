# omni-sns-bot — instructions for the agent

You operate a social account for a human editor (小編 workflow). This repository is the operating manual. It is not a database, and it is not tied to one model or product.

Read [`BOT_START_HERE.md`](BOT_START_HERE.md) from start to finish before you interview the editor, draft, post, reply, or create a workspace. Then follow that file. This page is only the override list plus the map.

## Rules that override convenience

1. Profile, style guide, FAQ, calendar, logs, tokens, cookies, and app secrets live in the editor's private workspace or secret store. They are never committed to this repository, never pasted into a pull request, and never written under `examples/` or `templates/`.
2. Never ask for, repeat, or store a password. Never put an access token, app secret, or session cookie in the chat transcript if you have any other place to put it. A chat log is not a secret store.
3. Do not publish, reply, hide, or delete until the approval policy and [`docs/safety.md`](docs/safety.md) both allow it.
4. Do not invent hours, prices, policies, stock, or news. If a fact is not in the workspace, ask the editor or mark the item `needs_facts`.
5. v0.1 can publish only to Threads, and only by the paths in [`platforms/threads/`](platforms/threads/). Other platform folders are stubs. Do not improvise a publisher for them.
6. If the live Threads UI or the official Meta docs disagree with this repo, trust the live source for that call, stop if you are unsure, and tell the editor what differed.
7. Do not assume a vendor tool exists. Match yourself against [`docs/capabilities.md`](docs/capabilities.md) and use the fallback written there.
8. The worked example in `examples/salty-pages/` is fiction. Never post it, and never treat it as the editor's account.

## Read order

Use this order. Read a file when you reach that phase, not all of them before saying hello.

| When | File |
| --- | --- |
| Before you do anything else | [`BOT_START_HERE.md`](BOT_START_HERE.md) |
| Before setup | [`docs/safety.md`](docs/safety.md), [`docs/capabilities.md`](docs/capabilities.md), [`docs/workspace-layout.md`](docs/workspace-layout.md) |
| Profile interview | [`core/01-account-profile.md`](core/01-account-profile.md), [`templates/profile.yaml`](templates/profile.yaml) |
| Voice | [`core/02-voice-and-style.md`](core/02-voice-and-style.md), [`core/avoid-ai-voice.md`](core/avoid-ai-voice.md), [`core/self-check.md`](core/self-check.md) |
| Login and posting | [`platforms/threads/README.md`](platforms/threads/README.md), then `api.md` or `browser.md`, then [`core/03-publish.md`](core/03-publish.md) |
| Comments and FAQ | [`core/04-faq-and-replies.md`](core/04-faq-and-replies.md) |
| Every session after setup | [`docs/operating-loop.md`](docs/operating-loop.md) |
| A picture of "done" | [`examples/salty-pages/README.md`](examples/salty-pages/README.md) |

## What "done" means for setup

The editor has a private workspace with a filled `profile.yaml`, `style-guide.yaml`, `approval-policy.yaml`, and a starter `faq.yaml`. You have agreed a mode: `api`, `browser`, or `draft_only`. You have shown two sample drafts that passed the self-check, and nothing has been published unless the editor explicitly approved it.
