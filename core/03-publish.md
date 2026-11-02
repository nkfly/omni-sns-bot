# Publish

Goal: a calendar the bot can run every session, and a publish action that only fires when the gates in [`docs/operating-loop.md`](../docs/operating-loop.md) pass.

This module does not contain Threads endpoints. When an item is ready, open `platforms/<platform>/README.md` and follow it. If that adapter's status is not `implemented`, tell the editor and leave the item unsent.

## Calendar

Copy [`templates/calendar.yaml`](../templates/calendar.yaml). One item per post. Status is a single field:

| Status | Meaning |
| --- | --- |
| `idea` | Topic only. May lack text. |
| `needs_facts` | Cannot be drafted until the editor supplies a fact. |
| `draft` | Has text. Self-check not yet passed, or not yet shown. |
| `pending_approval` | Self-check passed. Waiting for the editor, unless the policy will auto-approve on a later loop. |
| `approved` | Editor said yes to this exact text, or the policy allowed it and you recorded why. |
| `publishing` | A container was created, or the browser composer is open. Do not start a second copy. |
| `published` | Live. Fill `published.media_id` and `published.permalink` when you have them. |
| `failed` | The platform refused or the network failed. Store the redacted error. |
| `rejected` | Editor said no. Keep it so you do not propose the same angle tomorrow. |
| `killed` | Editor said to drop it forever. |

`publish_at` is ISO 8601 with an offset. Use the profile timezone. If you do not know a good time, propose one inside `cadence.windows` and outside `quiet_hours`, and leave status `pending_approval` until the time is accepted.

`risk` is `low`, `medium`, or `high`.

- `high` if the post mentions price, health, law, politics, a real person who is not the brand, a new link host, or a topic next to `topics.avoid`.
- `medium` if you are unsure, or the post makes a promise (shipping, stock, "see you there").
- `low` only when it is on `topics.cover`, cites facts, and matches posts they have approved before.

High is never auto-published.

`facts_used` lists FAQ ids or profile fields. If you cannot fill it and the post states a fact, the status is `needs_facts`, not `draft`.

`disclose_ai` follows `profile.ai_disclosure.policy` once the editor has chosen. For `editor_decides`, start at `null` and ask for an explicit true or false on this item before approval or publication. The adapter turns that boolean into the platform's flag. For Threads that is `is_made_with_ai` on container creation, not on the publish call.

## Draft file

When the text is more than a few lines, also write `drafts/<id>.md`:

```markdown
---
id: 2026-11-04-window
status: pending_approval
risk: low
---

Caption text only.

<!--
self-check: pass
- voice: pass
-->
```

The string you publish is the caption, nothing else. No front matter, no checklist, no "draft:" prefix.

## Approval file

Copy [`templates/approval-policy.yaml`](../templates/approval-policy.yaml). `level` must match `profile.approval.level`. If they disagree, stop and ask which one the editor meant. The policy file wins once they answer; update the profile to match.

Behavior of each level, including the first ten editor-approved posts, is defined in [Approval decision](../docs/operating-loop.md#approval-decision). Do not loosen a level because the queue is backing up. Ask.

Record an approval on the item:

```yaml
approval:
  required: true
  state: approved
  by: editor
  at: 2026-11-02T20:01:00+08:00
  note: "yes, post thursday"
```

A later edit to `text` sets `approval.state` back to `pending` and status to `pending_approval`.

## Proactive ideas

"Proactive" means you arrive with a draft, not that you post unattended on day one.

When the future queue is below `cadence.buffer_min`:

1. Pick a topic from `topics.cover` that you have not used in the last six published items.
2. Attach a fact you can cite, or mark `needs_facts` and ask one question ("Any new books this week, or should I stay with the lamp and the candy?").
3. Draft in the style guide. Vary the shape if the last two posts opened the same way.
4. Put it on the calendar. Let the policy decide whether it waits.

Do not create a week's worth of posts in one session unless the editor asks. Three ahead is enough. Stale specifics ("today the candy sold out") go bad if you write them four days early. Prefer evergreen specifics, and schedule time-bound posts only when the editor confirms the timing.

Quiet hours and the weekly cap are hard stops. If the editor asks you to post at 02:00 and quiet hours say no, point at the profile and ask if they want quiet hours changed. Do not quietly "make an exception" and also do not lecture. One question.

## Manual posting (`draft_only`)

Give the editor the caption, the suggested local time, and the link attachment if any. After they say it is live, ask for the permalink and mark `published`. If they forget, leave `approved` and ask once next session.

## Browser and API

Both are described under `platforms/threads/`. Use a stable attempt journal for each calendar item as described in [Publishing mechanics](../docs/operating-loop.md#publishing-mechanics). Unknown outcomes stay `publishing`; never rerun create until recovery establishes the result. This module's extra rule: the calendar status moves to `publishing` before you fire the request or click the final control, so a crash does not cause a second post. Without the Python helper, write the intent file in [Without the Python helper](../docs/operating-loop.md#without-the-python-helper) first, then verify the caption on the profile. Do not retry until that check shows it is absent and the editor authorizes another attempt.

## Images and video

v0.1's helper script publishes text. The Threads API docs in the adapter cover image, video, and carousel well enough for a bot with HTTP to do them when the editor supplies a public media URL. Do not upload a file by inventing a host. If the media is only on the editor's machine and you have no public URL, use `draft_only` for that item or the browser path if they opted in and can attach the file themselves.

Alt text: if the platform has a field (`alt_text` on Threads) and the post includes an image, ask the editor for a description or write one they approve. Do not skip it and do not stuff keywords into it.

## After publish

Log `action: publish`. Increment nothing fictional. If this was an editor-approved post, increment `profile.approval.posts_approved_count` exactly once when the item actually publishes. Replies, practice items and policy-approved posts do not increment it. On recovery, consult the publication log before counting it again. See the canonical [Approval decision](../docs/operating-loop.md#approval-decision).
