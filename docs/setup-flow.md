# First-run setup: use answers and evidence once

This is the setup conversation contract. `BOT_START_HERE.md` names the phases;
the files under `core/` define their content. This file defines how to move
between them without repeating questions or confusing a preference with permission.

## Start from what is already known

1. Read the existing private workspace and the editor's latest message before
   asking anything. On resumption, show only what changed or is still missing.
2. Copy `templates/setup-state.yaml` into the private workspace. It records the
   current phase, confirmed field paths, deferred fields and pending questions.
   Profile values still live in `profile.yaml`; do not keep conflicting copies.
   Older workspaces can add this file without restarting the interview.
3. Map answers by meaning, even if their numbers do not match your questions.
   Save every usable answer from a partial response, then ask only for missing
   information. A preference already stated in another group is still answered.
4. Normally ask at most three short questions per turn. Use the editor's
   language. Offer a concrete default only for an unanswered choice, and label
   it as a proposal until accepted. Templates are not consent.
5. "None" and "later" are answers. Record no excluded topics as
   `topics.avoid: []` plus `avoid_confirmed: true`; no excluded audience can be
   an empty `audience.not_for`. Leave `do`/`dont` empty when no extra rules were
   requested. Do not invent a taboo to satisfy a validator. Mark deferred links
   in `setup-state.deferred_fields` and leave `links.allowed` empty. Ask about a
   link again only when a concrete post needs one.
6. Preserve explicit corrections immediately, including Traditional vs
   Simplified Chinese. Never infer a script from the generic word "Chinese".

## Discover a usable path before assigning manual work

In Phase 0, discover relevant tools and permissions. If the editor says a
browser is already logged in, investigate that route before asking them to
copy dozens of posts or set up an app. Tool absence, installation and tested
access are different observations; record the evidence and time in
`setup-state.capability_evidence`.

| Observation | Next step |
| --- | --- |
| A native browser tool can use the editor's authorized session | Request consent for the specific read scope if not already given, then test a read. |
| macOS Chrome is available but no native browser tool is exposed | `browser_read.py probe` can detect the installation without launching it. Offer the optional [read-only helper](../scripts/threads/README.md#read-an-existing-chrome-session). A successful read, not installation alone, verifies access. |
| Web search or an unauthenticated profile page yields only biography metadata | Report "no post bodies collected". This does not prove that the editor's logged-in browser is inaccessible. |
| A permitted browser read fails | Explain the actual permission/load failure. Ask the editor to finish login/checkpoints or choose API, pasted text or `draft_only`; do not bypass the restriction. |
| No read path works | Ask for a small initial batch of representative posts, then grow the corpus if needed. Do not require 30 posts before showing any progress. |

The helper is optional, macOS-specific, and read-only. Other platforms use a
verified native browser tool or the documented fallback. Do not require a
particular plugin. Reading a reference profile does not choose browser mode
for public actions and does not authorize account switching.

## Connect early when extraction needs it

If `voice.source` is `extract` and there is no corpus yet, resolve the read path
before continuing voice work. The connection portion of Phase 4 may happen
before Phase 3 when necessary; finish the voice and FAQ before any publication.
Do not collect API secrets in chat. Explain browser limits once before the
editor chooses browser management, then persist that opt-in instead of asking
again on every read. Scope-specific OS approval prompts may still be required.

`profile.account.handle` always identifies the account being managed. Store
other profiles under `profile.voice.reference_accounts`, including why the
editor owns or is allowed to use the material and whether browser reading was
authorized. Never replace the managed handle with the reference handle. Before
any public action, verify the live session's Profile navigation points to the
managed handle; visiting its URL alone is not proof of login identity. A live
display name can fill `account.brand_name`; recording it does not authorize a
rebrand.

Collect at most 50 posts, usually 15–30. Start provisionally with fewer when
that is what the interface exposes. Record the count actually obtained,
top-level vs continuation/reply status, source URLs and partial coverage.
Separate UI text, quoted authors and link previews from captions; do not claim
the whole account was exported. Keep original samples private and verbatim.
Historical activity dates, capacity, prices and news claims are style evidence,
not automatically verified facts for new posts.

## Represent cadence without changing its meaning

| Editor's answer | Store and interpret it as |
| --- | --- |
| At least N posts weekly | `cadence.min_posts_per_week: N`, a planning minimum. `posts_per_week` remains the weekly hard ceiling for compatibility. If no weekly maximum was specified but a daily maximum was, its seven-day total can be recorded as a derived ceiling. Label the derivation; never turn the minimum into a maximum. |
| No personal reply limit | `cadence.max_replies_per_day: null`. Apply the adapter/platform ceiling separately; `null` is not unlimited platform permission. For browser mode, the effective reply ceiling is the lower of a numeric editor cap and the adapter's cap, or the adapter cap alone if the editor cap is null. Never overwrite the editor's preference with the computed cap. |
| Evening through 24:00 | Save `start: "19:00"`, `end: "00:00"`, `end_next_day: true` for that example. Never save a clock value of `24:00` or allow the next day's midnight as the start of this window. |

Posting windows are half-open: start is included and end is excluded. `days`
names the day a window starts. For an overnight 22:00–02:00 Friday window,
Saturday 01:00 belongs to Friday's window; Saturday 02:00 is outside it. A
19:00–midnight window ends exactly at the next day's 00:00. Quiet hours still
override windows. A minimum never bypasses approval, daily maxima or quiet
hours and is not a promise that an inactive assistant will publish.

## Keep feedback scoped

Record each decision with an item id, time and one of these scopes in
`setup-state.decisions`:

| Scope | What it permits | What remains separate |
| --- | --- | --- |
| `style` | Use the selected draft as an editor-preferred voice example. | Practice stays practice; no post is approved to publish. Selecting one example does not approve every inferred style rule. |
| `reply_template` | Reuse the approved wording as a template for matching questions. | Each actual comment must still be matched, deduplicated and evaluated under the current approval policy. This never enables `auto_approve_faq_replies_before_ten_posts`. |
| `public_action` | Apply the approval decision to the exact identified caption/reply and destination. | Any text edit invalidates approval. Identity, cadence, safety and duplicate prevention still apply. |

An answer such as "②" selects the numbered option you just showed; it is not
a global change of approval level. A template still has no target comment.
The existing FAQ auto-reply exception requires a separate explicit request
and logged policy change as defined in [Approval decision](operating-loop.md#approval-decision).

When interest in an event requires an introduction, store the editor's actual
fields and avoid repeat requests if the person already introduced themselves.
For a public comment, ask for a voluntary introduction privately to the editor
rather than collecting personal details publicly. This is not permission for
the assistant to read/send DMs, reserve a seat or confirm admission.

## Finish setup without forcing a post

Run the workspace checker after saving the initial profile, style guide,
approval policy, FAQ and calendar. Distinguish a verified read from an untested
publish capability; do not say a post was tested if none was sent. Summarize
the managed account, mode, approval rules, schedule status and private workspace.

If the editor wants setup/review only, keep `session_intent: setup_only`, leave
the calendar empty and stop after handoff. Ask for a first post topic only when
they want to draft. A minimum cadence, approved sample or approved template
does not authorize a scheduler, a first post or an inbox send. Do not repeatedly
prompt to publish during a setup-only session.

At the next session, interpret the editor's new request before updating the
intent: an explicit drafting request can change it to `drafting`, while an
explicit request to review a real send can change it to `publishing_review`.
Drafting still does not approve publication. Do not silently clear a current
"no posts today" request because setup is complete or a schedule target is low.

Only fictional examples and synthetic tests belong in a contribution. Never
attach real profiles, handles, corpus exports, browser snapshots or private
workspace paths to a public issue or PR, even as a "sanitized" reproduction.
