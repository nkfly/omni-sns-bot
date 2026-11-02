# Adding a platform

v0.1 ships a finished Threads adapter and empty slots for Reddit, Instagram, Facebook, and X. Add the next one by filling a slot, not by scattering `if reddit` through `core/`.

## What "done" means

An adapter is `implemented` only when a bot can, from the docs alone:

1. Authenticate the editor's own account without asking for a password.
2. Publish the post kinds you claim, inside written rate limits.
3. Read and create replies, or explicitly say replies are `draft_only` for that platform.
4. Refuse to spam, and name the platform's own rules that justify the refusal.
5. Pass a worked example that is clearly fictional.

Until then, `capabilities.yaml` stays `status: not_implemented`. A README that says "use the unofficial API" or "drive the website however you like" is not an adapter.

## Steps

1. Copy `platforms/_template/` to `platforms/<id>/`. Use a short lowercase id: `reddit`, `instagram`, `facebook`, `x`.
2. Fill `capabilities.yaml`. List auth methods and the capabilities each one needs (`http`, `browser`, `secret_store`).
3. Write, as separate files so a bot can open only what it needs:
   - `README.md` — status, modes, and which file to open next
   - `auth.md` — official login, token lifetimes, where secrets go
   - `publish.md` — create and publish, with the fields that map from `calendar.yaml`
   - `replies.md` — read, triage hooks, send
   - `limits.md` — numbers, windows, and the official URL they came from, plus the date you checked
   - `safety.md` — platform-specific rules (for example Reddit's self-promotion norms, or a network's ban on automated browser actions if that is the current term)
4. Map calendar fields. Reuse `text`, `link_attachment`, `publish_at`, `approval`, and `published`. Add optional fields on the item rather than forking the schema. Document them in `publish.md`.
5. If an official HTTP API exists, prefer it, and add a stdlib script only when curl would be easy to get wrong (token handling, two-step publish). Scripts follow the same secret rules as `scripts/threads/`.
6. A browser path, if you document one, requires editor opt-in, human login, no password handling, no checkpoint bypass, and a cadence far under any API ceiling.
7. Extend `examples/` only with fiction.
8. Update the root README roadmap table and the Traditional Chinese roadmap paragraph in the same change.
9. Flip `status` to `implemented` in the same commit that adds the docs, not before.

## Core files you should not need to fork

- `core/01-account-profile.md` — record extra platforms in `profile.account.also_platforms` (add that optional list if it is missing).
- `core/02-voice-and-style.md` and the anti-AI guide — shared. Add platform length limits to the adapter, and let the self-check call them.
- `core/03-publish.md` — already says "open `platforms/<id>/`".
- `core/04-faq-and-replies.md` — triage labels stay the same. The adapter only defines how a reply is fetched and sent.

## Review questions

- Could a bot post to the wrong account if it followed a step literally?
- Is every limit sourced, dated, and enforced in the procedure (not just mentioned)?
- What happens with no HTTP, no browser, and no scheduler? The answer should be `draft_only`, not a dead end.
- Did any secret land in the diff?

## Suggested order after Threads

The roadmap in the README is Reddit, then Instagram, then Facebook, then X. Instagram and Facebook are Meta products with their own APIs; do not reuse a Threads user token or the Threads host for them. Reddit's norms around disclosure and community rules need their own `safety.md` before any publish helper exists.
