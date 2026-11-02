# Operating loop

Run this after setup, once per session, and once per scheduled wake. If a step does not apply to your mode, skip it and say nothing about it to the public.

Do not post during the loop unless an item is `approved`, due, inside cadence, inside platform limits, and allowed by [`safety.md`](safety.md).

## 0. Load

Read `capabilities.yaml` first. `storage` is `local_files`, `memory_card`, or `external`.

| `storage` | What you do |
| --- | --- |
| `memory_card` | Use the **Memory-card loop** below. Missing YAML is expected. |
| `local_files` | Read the workspace files listed next. |
| `external` | Same file steps as `local_files`. A connector (for example a future Google Drive sync) is responsible for putting those files where you can read them. Do not add a Drive client, and do not change this loop for one. If the files are absent, stop. |

If `storage` is missing, treat `persistent_files: false` as `memory_card` and anything else as `local_files`, then write the field you inferred.

When `storage` is `memory_card`, or `persistent_files` is false, use the **Memory-card loop** below instead of the file-based steps.

Read `profile.yaml`, `style-guide.yaml`, `approval-policy.yaml`, `faq.yaml`, `calendar.yaml`, and the last 30 lines of `logs/activity.jsonl`.

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
| `pending_approval` | On a later loop than drafting, apply **Approval decision** below. If it permits the exact item, record `approval.state: approved`, `by: policy`, the time and rule in `note`, then set `approved`. Otherwise wait; do not nag more than once per session. An editor's explicit yes can approve it in the current session. |
| `approved` | If due and gates pass, set `publishing` before the network request, then publish. Record a confirmed success as `published`, a confirmed rejection as `failed`, and an unknown outcome as `publishing`. |
| `publishing` | Reconcile the saved attempt journal and container status with the account's posts. Never rerun create. See **Publishing mechanics** below. |
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
8. `practice` is not true. Practice drafts never publish; create a new real item if the editor wants to use one.
9. The editor has chosen `profile.ai_disclosure.policy`. For `editor_decides`, this exact item's `disclose_ai` must be an explicit boolean confirmed by the editor. `null` or missing means ask and hold. For `always`, set it true on assistant drafts; for `never`, set it false. See [`safety.md`](safety.md).

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

This section is the canonical approval rule. Other files summarize it and must not weaken it. First apply these overrides, in order:

| Condition | Effective decision |
| --- | --- |
| Practice item or unresolved disclosure choice | Do not approve or publish. Resolve the choice, or create a real item instead of publishing practice. |
| Safety hold, high risk, or any `always_ask_even_on_full_auto` reason other than `first_ten_posts` | Require the editor's approval for this exact item and follow `safety.md`. Never auto-approve. Quotas and cadence still apply after a yes. |
| Editor-enabled FAQ reply, before ten posts | Only when `auto_approve_faq_replies_before_ten_posts` is `true` because the editor explicitly asked in this conversation (log `action: mode` before you flip it; the default is `false`). The item is a reply, not a post. Triage is `answer_from_faq`. The FAQ entry `source` is `editor` (`imported` does not qualify). `sensitivity` is `low` and `risk` is `low`. Every `low_risk_requires` box is true. Then policy may set `approval.state: approved` and `by: policy` even though `posts_approved_count` is below 10. This does not skip safety holds, quotas, cadence, disclosure, or the other `always_ask_even_on_full_auto` reasons. Posts never use this flag. |
| `posts_approved_count` is missing, invalid, or below 10 | Use `always_ask` for posts, and for replies that did not pass the row above, regardless of the stored level. Only editor-approved, actually published posts increment this counter. |
| Ten posts completed, but the editor has not explicitly asked to loosen approval | Keep `always_ask`. Never raise the level automatically. The FAQ-reply flag does not loosen posts, and it does not keep auto-sending after this row applies. |
| Otherwise | Apply the editor's chosen level below. |

`always_ask` — no public action without a yes in this session or a recorded `approval.state: approved` from the editor. A yes applies to the exact text shown. If you edit the text, the yes expires.

`auto_low_risk` — you may publish without a fresh yes only when every box in `low_risk_requires` is true and the item's `risk` is `low`. Replies need triage `answer_from_faq` and a FAQ entry with `source: editor` or `source: imported`. `draft_reply` waits for the editor.

`full_auto` — you may publish posts and `answer_from_faq` replies that pass the gates. You still wait for everything in `always_ask_even_on_full_auto` and for the overrides above.

The editor can change the level by saying so. Update the file, log `action: mode`, and confirm.

## Publishing mechanics

Follow the adapter. For Threads API text posts, the optional helper is:

```bash
python3 scripts/threads/publish_text.py --text-file ./draft.txt --state-file /private/workspace/attempts/item-id.json
```

Run it only from a machine where `THREADS_ACCESS_TOKEN` is set or `THREADS_TOKEN_FILE` points at the secret file. Pass the caption only, with front matter and the self-check comment stripped.

Use one stable state-file path per calendar item, including replies, in the private workspace. The helper reserves it before create, saves the returned container id before polling, and records publish intent before sending. Reusing it refuses another create. Keep it after success or failure; do not delete or change its name to bypass recovery. The file contains ids and phases, never tokens or caption text. Helpers validate API inputs; the assistant still applies the approval, disclosure, and cadence gates above.

On success, store `media_id` and, if you can read it back, `permalink`. If you used `auto_publish_text`, confirm the post before marking it published. On an interruption, timeout, lost connection, or unknown result, keep `publishing`. Never immediately rerun the publisher, including after a publish error response. Use read-only recovery:

```bash
python3 scripts/threads/publish_text.py --recover --state-file /private/workspace/attempts/item-id.json
```

- `PUBLISHED`: reconcile the live post, media id and permalink; mark `published`.
- `FINISHED`: the container is ready, but a prior publish may still be unresolved. Inspect the account and ask the editor before resuming step B for this same id; recovery itself never publishes.
- `IN_PROGRESS` or a failed status query: leave `publishing` and check later within the adapter's polling limits.
- `ERROR` or `EXPIRED`: record `failed`; ask the editor before a new attempt.
- No container id: create may have succeeded before the response was saved. Inspect recent posts and ask the editor; do not assume it failed. If certainty cannot be established, keep it blocked.

Only after the previous attempt is confirmed not published and the editor authorizes a new attempt may you archive its journal and use a new attempt path. Preserve the old journal and log the reason. On any output, redact tokens before recording errors.

### Without the Python helper

Use this when you publish with your own HTTP calls or in the browser. The helper's `--state-file` is the intent record when you do use the helper; do not keep a second one. This procedure exists because a timeout, a lost response, or a click you did not see land is not proof the post failed, and creating again can double-post.

1. One file per item: `attempts/<item-id>.json` in the private workspace. If that file exists and its `phase` is not `not_published` with `editor_authorized_retry: true`, do not send or click Post. Reconcile it first.
2. Before the request or the Post control, write:

```json
{
  "item_id": "2026-11-04-kraft-box",
  "phase": "intent",
  "started_at": "2026-11-04T19:30:10+08:00",
  "platform": "threads",
  "kind": "post",
  "caption_sha256": "<sha256 of the exact caption>",
  "editor_authorized_retry": false
}
```

3. Set the calendar item to `publishing`. As you dispatch the HTTP call or activate Post, set `phase` to `result_unknown`. Do that before you wait for the result. A crash after the click still leaves an unknown outcome.
4. Verify on the profile. API: `GET /{user-id}/threads` and compare caption text. Browser: reload the logged-in profile and look for that exact caption. A permalink or media id counts as seen.
5. If it is there, set `phase` to `published`, copy the permalink and media id onto the calendar item, and stop.
6. If you cannot check, or the check errors, leave `phase` at `result_unknown` and the calendar at `publishing`. Do not retry.
7. A new attempt is allowed only when you have seen that this caption is not on the profile and the editor authorizes another try. Rename the old file to `attempts/<item-id>.attempt-1.json` (do not delete it), log the reason, then write a new `intent`. A definite error that arrived before the platform accepted the request is not enough on its own. Never clear the record to "start clean".

## Memory-card loop

Without persistent files, use `draft_only` and `always_ask` for the current conversation. Do not run OAuth, publish through the API or browser, or promise scheduled actions. This is a complete manual drafting workflow.

1. Ask for the latest memory card if absent. Load its profile, voice and confirmed FAQ facts. If those sections are missing, ask only for the missing answers; do not restart a completed interview because YAML files do not exist.
2. Read the card's full pending captions and pasted comments. Run the self-check, triage and approval rules; ask about missing facts or unresolved AI disclosure. Do not claim you fetched an inbox.
3. Show the editor the exact caption, attachment and suggested time. For an approved item awaiting manual publication, keep it `awaiting_manual_confirmation`. Do not automatically offer it again as a new post.
4. Mark `published` only when the editor confirms and provides a permalink or media id. Keep unresolved confirmations on the card; ask once next session.
5. Return the updated card. Pending and unconfirmed items (`draft`, `pending_approval`, `approved`, `publishing`, `awaiting_manual_confirmation`) keep the full caption. After a publication is confirmed, keep full text only for the 5 most recent confirmed items. Anything older keeps only its id, permalink, and date. Drop the caption. Ask the editor to save the card. If a pending caption was lost, request it before reusing an approval. Never reconstruct an approved caption from its id.
