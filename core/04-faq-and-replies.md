# FAQ and replies

Goal: answer repeating questions in the account's voice, and never answer a question the editor has not already answered in substance.

The FAQ is a fact store with a few phrasings attached. It is not a dump of everything the model knows about the topic.

## Shape

Copy [`templates/faq.yaml`](../templates/faq.yaml).

An entry:

```yaml
- id: hours
  questions:
    - 今天有開嗎
    - 幾點關
    - opening hours
  answer: 週二到週日 12:00–21:00，週一公休。
  language: zh-Hant
  sensitivity: low
  source: editor
  updated: 2026-11-02
  expires: ""
```

| Field | Rule |
| --- | --- |
| `answer` | The fact, in the editor's wording when you have it. You may shorten a reply, but you may not add a claim that is not in `answer`. |
| `sensitivity` | `low` for hours and directions. `medium` for prices and policies that change. `high` for health, legal, money advice, personal data. `high` is never auto-sent. |
| `source` | `editor` (they said this), `imported` (it was written on their site or in a past post they told you to trust), `unconfirmed` (you drafted a possible answer and they have not said yes). |
| `expires` | Optional date. After it, treat the entry as `unconfirmed` until they reaffirm it. Use this for prices and seasonal hours. |

`unconfirmed` entries are notes, not ammunition. Do not quote them in public.

## Seeding

During setup, write an entry for every operational fact they already told you: hours, location, what you sell, what you refuse, how to book, language of service. Then ask:

"What do people ask every week that I should answer the same way each time?"

Add those in their words. If they say "just look it up", refuse. Looking it up is how you invent a policy.

Aim for 5–15 entries, not 100. A huge FAQ of guesses is worse than a small one.

## Inbox item

When a comment arrives, append to `faq.inbox` (or a monthly split file `faq-inbox.yaml` if one file becomes unwieldy; start with one file):

```yaml
- id: q-20261102-001
  received: 2026-11-02T18:02:00+08:00
  platform: threads
  on_post_id: "18000000000000000"
  comment_id: "18000000000000001"
  from_username: someone
  text: 今天有開嗎
  triage: answer_from_faq
  faq_id: hours
  draft: 今天有開，九點關。週一才休。
  disclose_ai: null
  action_taken: pending
  new_faq: false
```

Keep `text` so you do not answer twice. You may redact phone numbers or addresses from the stored text and keep them only in the escalation message to the editor.

## Triage

Do these in order. The first match wins.

1. **`sensitive_hold`** — safety list in [`docs/safety.md`](../docs/safety.md), or the matched FAQ entry is `sensitivity: high`, or the commenter seems to be a minor, or they sent personal data. Do not draft a public answer. Tell the editor what arrived and what you did not answer.
2. **`ignore`** — spam, phishing, pure emoji with no question, a commercial link, or abuse. Do not reply. Do not click the link. Log `skip`. If the editor has a written rule to hide commercial links, you may hide, once, and log it.
3. **`answer_from_faq`** — a `source: editor` or `source: imported` entry covers the question, is not expired, and is `low` sensitivity. Draft a reply that states the answer and nothing extra.
4. **`escalate`** — a real question you cannot cover, a `medium` entry that is expired or ambiguous, a complaint, a journalist, a collaboration, or anything where being wrong costs the account. Draft nothing, or draft a holding line only if the style guide has one and the policy allows it. Default is no holding line.
5. **`draft_reply`** — you think you can answer from the profile's purpose without a new fact (a thank-you with a specific detail, a pointer to a post permalink that is already in the calendar). It still waits for the editor unless the policy says otherwise. `auto_low_risk` does **not** auto-send `draft_reply`.

If two FAQ entries could match, escalate. Do not pick the more convenient one.

## Drafting the reply

- Voice: `style-guide.replies`, then the rest of the guide.
- First line contains the answer.
- No "Great question" / 「好問題」/ 「いい質問ですね」.
- No new facts, no new links, no apology for the brand's existence.
- Run [`self-check.md`](self-check.md) with the reply length rules, which are tighter.
- Apply the [approval decision](../docs/operating-loop.md#approval-decision). Posts stay on the first-ten gate. A reply may skip that gate only when `auto_approve_faq_replies_before_ten_posts` is true because the editor explicitly asked, triage is `answer_from_faq`, the FAQ `source` is `editor`, sensitivity and risk are both `low`, and no safety hold applies. `imported` answers and `draft_reply` still wait. Quotas still apply. Resolve `disclose_ai` under the profile policy. For `editor_decides`, ask for this reply's true/false choice; `null` blocks sending.
- One public reply per comment. If they reply again, triage the new message. Do not hold a long debate. Two rounds, then escalate if it is still going.

Threads send path: [`platforms/threads/api.md`](../platforms/threads/api.md) (`reply_to_id`, then publish). Browser: [`platforms/threads/browser.md`](../platforms/threads/browser.md). Both count toward `max_replies_per_day`.

Default scope is replies on the account's own posts. `approval-policy.reply_to_others` defaults to false. Leaving it false means you do not reply under strangers' posts, even if the API would allow it with extra permissions.

## Writing back into the FAQ

When the editor answers an escalation with a fact that will recur:

1. Read the fact back in one sentence and ask "should I save this for next time?"
2. On yes, add an entry with `source: editor` and their wording.
3. Log `faq_add`.
4. Only then send the public reply, still through the approval rule.

If you learned something from a web search or from memory, it does not enter the FAQ and it does not enter the reply.

When an entry is wrong, update `answer` and `updated`. Do not leave the old fact in a second entry.

## What you tell the editor

Batch the inbox summary: how many ignored, how many waiting, the drafts that need a yes. Do not paste a dozen spam comments in full. Do paste sensitive ones, because they need a human.
