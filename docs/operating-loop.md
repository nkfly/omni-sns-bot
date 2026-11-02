# Operating loop

Run this after setup, once per session, and once per scheduled wake. If a step does not apply to your mode, skip it and say nothing about it to the public.

Do not post during the loop unless an item is `approved`, due, inside cadence, inside platform limits, and allowed by [`safety.md`](safety.md).

## 0. Load

Read `capabilities.yaml`, `profile.yaml`, `style-guide.yaml`, `approval-policy.yaml`, `faq.yaml`, `calendar.yaml`, and the last 30 lines of `logs/activity.jsonl`.

If files are missing, stop and return to [`BOT_START_HERE.md`](../BOT_START_HERE.md). Do not rebuild them from imagination.

## 1. Token and quota (mode `api` only)

- If the long-lived token expires within 7 days, refresh it ([`platforms/threads/api.md`](../platforms/threads/api.md)). Refresh only works when the token is at least 24 hours old and not expired. If refresh fails, tell the editor; do not keep posting.
- Read `threads_publishing_limit` before any publish or reply. If the post quota or reply quota is exhausted, defer and log `blocked`.
- If a call returns an auth error, stop the loop. Ask the editor to run the authorization window again.

## 2. Inbox (mode `api`, or `browser` if you can see notifications)

Fetch new replies on the account's own recent posts. For each new reply, follow [`core/04-faq-and-replies.md`](../core/04-faq-and-replies.md):

1. Triage: `answer_from_faq`, `draft_reply`, `escalate`, `ignore`, or `sensitive_hold`.
2. Draft only when triage allows it, in the account's voice, after the self-check.
3. Send only if the approval policy allows this kind of reply. Otherwise show the editor the draft.
4. If the editor supplies a new fact, write it into `faq.yaml` with `source: editor`.

Cap sends at `profile.cadence.max_replies_per_day` and at the platform reply ceiling. Prefer fewer good replies over clearing the inbox.

`draft_only`: list the comments you were given, or ask the editor to paste new ones. Do not claim you checked Threads.

## 3. Calendar

Timezone is `profile.cadence.timezone`. "Due" means `publish_at` is in the past or within the next 10 minutes, and the current local time is inside a posting window and outside quiet hours.

For each item, in `publish_at` order:

| Status | Action |
| --- | --- |
| `idea` | If you have the facts, write a draft and move to `pending_approval` or `draft`. |
| `needs_facts` | Ask the editor, or skip if you already asked today. |
| `draft` | Run the self-check. If it passes, move to `pending_approval` and show the editor when the policy requires it. |
| `pending_approval` | Wait. Do not nag more than once per session. |
| `approved` | If due and gates pass, publish and move to `publishing`, then `published` or `failed`. If not due, leave it. |
| `publishing` | A previous attempt stalled. Check container status before creating another container. Do not double-post. |
| `published` | Record permalink if missing. Do not edit the public text in the calendar after the fact except to add the permalink and media id. |
| `failed` | Show the error once. Wait for the editor. |
| `rejected`, `killed` | Leave them. Do not revive a `killed` item. A `rejected` item may be redrafted only if the editor asks, as a new id. |

Gates before a real publish:

1. Self-check passed on the exact text you are sending.
2. Approval policy returns yes for this item.
3. Cadence: fewer than `max_posts_per_day` already published today, and this week is under `posts_per_week`.
4. Platform quota has room.
5. Every link is on `profile.links.allowed`, and there are 5 or fewer unique links.
6. The text is within the platform length limit.
7. `facts_used` all resolve to the workspace.

If a gate fails, leave the item `approved` (it is still wanted) and log `blocked` with the gate name. Do not silently downgrade it.

## 4. Refill the queue

Count items in `idea`, `draft`, `pending_approval`, or `approved` whose `publish_at` is still in the future. If that count is below `profile.cadence.buffer_min` (default 3):

- Propose ideas grounded in `topics.cover`, recent FAQ questions, and `sources/`.
- Do not turn an idea into a factual claim you cannot cite.
- Add them as `idea` or, if the editor is here and answers, as `pending_approval`.
- Do not auto-publish a brand-new idea in the same turn you invented it, even on `full_auto`. It waits until the next loop, so a bad idea is not instant.

## 5. Close

Append log lines for what you did. If you have no scheduler, tell the editor when to come back. If you have files, you do not need to repeat the whole profile in the chat.

## Approval decision

Read `approval-policy.yaml`.

`always_ask` — no public action without a yes in this session or a recorded `approval.state: approved` from the editor. A yes applies to the exact text shown. If you edit the text, the yes expires.

`auto_low_risk` — you may publish without a fresh yes only when every box in `low_risk_requires` is true and the item's `risk` is `low`. Replies need triage `answer_from_faq` and a FAQ entry with `source: editor` or `source: imported`. `draft_reply` waits for the editor.

`full_auto` — you may publish posts and `answer_from_faq` replies that pass the gates. You still wait for everything in `always_ask_even_on_full_auto`. Until `profile.approval.posts_approved_count` is at least 10, treat `full_auto` as `auto_low_risk` and say so when you do.

The editor can change the level by saying so. Update the file, log `action: mode`, and confirm.

## Publishing mechanics

Follow the adapter. For Threads API text posts, the optional helper is:

```bash
python3 scripts/threads/publish_text.py --text-file ./draft.txt
```

Run it only from a machine where `THREADS_ACCESS_TOKEN` is set or `THREADS_TOKEN_FILE` points at the secret file. Pass the caption only, with front matter and the self-check comment stripped.

On success, store `media_id` and, if you can read it back, `permalink`. If you used `auto_publish_text`, the create call returns a container id and `media_id` may be empty; confirm the new post on the profile before you create another container. On failure, store the error string with tokens redacted, set `failed`, and do not immediately retry more than once.
