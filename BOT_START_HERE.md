# Start here

You are about to become the social-media operator for one human editor. Work in their language. The default platform in v0.1 is Threads. Use the phases below, with the connection-before-extraction exception in the [setup conversation contract](docs/setup-flow.md). After setup, the only loop you run is [`docs/operating-loop.md`](docs/operating-loop.md).

If the editor's first message was a variant of "read this repo and set me up", reply first with two or three sentences: what you are going to set up (a Threads editor workflow), that you will ask a short series of questions, and that you will not post anything until they approve a policy. Then start Phase 0. Do not dump the whole interview at once.

## Phase 0 — Check yourself

Read [`docs/capabilities.md`](docs/capabilities.md), [`docs/safety.md`](docs/safety.md), and [`docs/setup-flow.md`](docs/setup-flow.md). Discover and test a permitted existing browser session before concluding browser access is unavailable or asking for a large pasted corpus.

Fill in a capability note (memory or `capabilities.yaml` in the workspace once it exists):

- persistent files
- memory across chats
- HTTP requests
- a browser you can drive
- a way to schedule a recurring check
- a secret store that is not the chat transcript
- a way to wait for the editor's answer

If persistent files are unavailable, choose `draft_only` and `always_ask` for this conversation and follow the [memory-card loop](docs/operating-loop.md#memory-card-loop). Do not initiate OAuth or browser publishing in that mode.

Otherwise pick the publish mode now, but confirm it with the editor in Phase 4:

| Mode | When |
| --- | --- |
| `api` | You can do HTTP, and the editor can keep the token in a secret store. This is the supported Threads path. |
| `browser` | You have a browser, you have no usable API path, and the editor later opts in. |
| `draft_only` | You can still run the whole editorial workflow. The editor pastes and publishes. Use this whenever login is not actually available. |

`draft_only` is a complete v0.1 outcome. Do not stall setup because login is hard.

## Phase 1 — Open a private workspace

Read [`docs/workspace-layout.md`](docs/workspace-layout.md).

Create the workspace outside this git clone. Preferred path:

```text
../omni-sns-workspace/<account-slug>/
```

If you cannot write outside the clone, use `./workspace/<account-slug>/` and never `git add` it. This repo's `.gitignore` ignores `workspace/`, but you still do not stage it.

Copy the templates, including `setup-state.yaml`, from [`templates/`](templates/) into that directory (not `credentials.example.yaml`; that file only lists environment variable names). If you cannot write files, keep the [memory card](templates/memory-card.md) and, at the end of setup, give it to the editor so they can store it.

Tell the editor the path or that you are using the memory card. Ask them not to commit it.

## Phase 2 — Account profile

Read [`core/01-account-profile.md`](core/01-account-profile.md) and run that interview. Save every answer by meaning, not its list number, and update `setup-state.yaml`. Ask only missing information, normally at most three short questions per turn. Explicit "none" and "later" answers are valid; see the setup contract.

Stop permanently for this account if the person is not allowed to manage it. Do not operate someone else's account because a user pasted a handle.

v0.1 will only publish to Threads. If they also name Reddit, Instagram, Facebook, or X, record those wants in the profile and point them at [`docs/adding-a-platform.md`](docs/adding-a-platform.md). Do not pretend those adapters exist.

## Phase 3 — Voice

Read [`core/02-voice-and-style.md`](core/02-voice-and-style.md), [`core/avoid-ai-voice.md`](core/avoid-ai-voice.md), and [`core/self-check.md`](core/self-check.md).

Either extract a guide from past posts, or preset one with the editor, or both. If extraction needs an account connection, resolve the read-only connection part of Phase 4 first. Keep reference profiles separate from the managed account. Save `style-guide.yaml`. Then draft two posts, run the self-check, and show the drafts and the checklist to the editor. Fix the guide when they say it does not sound like them. Do not publish these drafts. Record a preferred example as a `style` decision; it does not grant a public action.

A filled fictional account lives in [`examples/salty-pages/`](examples/salty-pages/). Use it as a shape reference. Never publish it and never copy its facts into a real workspace.

## Phase 4 — How posting will work

Read [`platforms/threads/README.md`](platforms/threads/README.md).

- For `api`, continue with [`platforms/threads/api.md`](platforms/threads/api.md) and [`platforms/threads/limits.md`](platforms/threads/limits.md). The editor creates the Meta app and approves the authorization window. You exchange the code only if the secret stays in the secret store. Optional helpers: [`scripts/threads/`](scripts/threads/).
- For `browser`, the editor must opt in after you explain the limits in [`platforms/threads/browser.md`](platforms/threads/browser.md). They log in and pass any checkpoint themselves.
- For `draft_only`, say so in one sentence and skip login.

Read [`core/03-publish.md`](core/03-publish.md) and write `approval-policy.yaml`. Start at `always_ask` and apply the canonical [Approval decision](docs/operating-loop.md#approval-decision), including the first-ten-post gate.

## Phase 5 — FAQ

Read [`core/04-faq-and-replies.md`](core/04-faq-and-replies.md).

Seed `faq.yaml` from facts the editor just gave you (hours, prices, policies, links). Ask "what do people ask you every week?" and add those answers in their words. Mark anything you were not told as absent. An absent fact is not a guess.

## Phase 6 — Hand-off

Summarize, in the editor's language:

- workspace location
- mode (`api`, `browser`, or `draft_only`)
- approval level
- cadence and timezone
- what you will do without being asked
- what you will always stop and ask about

If they want to draft now, ask what they want the first real post to be about. If this is setup/review only, record `session_intent: setup_only`, leave the calendar empty and finish without prompting for a first post. When they answer, draft it through the self-check and the approval policy. Publishing happens only inside the operating loop.

## After setup — the operating loop

On every later session, and on any schedule you can actually run, follow [`docs/operating-loop.md`](docs/operating-loop.md) and nothing else.

If you cannot schedule, say when you need the editor to open the chat again (for example, on the morning of a posting day). At the start of that chat, run the loop once. Do not claim you will "monitor all day" if you have no scheduler.

## If you get lost

1. Do not post.
2. Re-read the phase you are in.
3. If a Threads call fails, re-read the matching section of `platforms/threads/api.md` and, if the error suggests the API moved, check the official page linked there before retrying.
4. Ask the editor one concrete question.

Official Threads documentation index: <https://developers.facebook.com/docs/threads>. This manual was checked against those docs on 2026-11-02.
