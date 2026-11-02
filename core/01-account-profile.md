# Account profile

Goal: fill `profile.yaml` from the template until you could explain the account to a new colleague without guessing. Ask in the editor's language. Groups below are in English so the spec stays stable; translate the questions, not the YAML keys.

Save after every group. If the chat dies, the workspace should still hold the answers you have.

Do not ask the whole list in one message. One group, then wait.

## Before the questions

Confirm you will not post during this interview. Confirm the workspace path or the memory card.

If they already have a filled profile and want to edit it, read it back in a short summary and ask what changed. Do not re-run empty questions.

## Group A — identity

Ask:

1. What should I call you?
2. What is the brand or account name, and the Threads handle?
3. Are you allowed to manage this account? (You own it, or the owner told you to run it and you can log in.)
4. Any other platforms you care about later? I will write them down. v0.1 can post only to Threads.

If they are not allowed to manage it, stop. Do not continue to voice or login.

Write `account.owned_by_editor: true` only after a clear yes. Write `account.also_platforms` as a list of ids (`reddit`, `instagram`, `facebook`, `x`) or leave it empty.

## Group B — purpose

Ask:

1. In one or two sentences, why does this account exist?
2. Who is it for, and who is it not for?
3. What should a reader feel after a post?
4. Which topics do you want, and which topics should never appear?
5. What language do you post in? When, if ever, do you mix in another?

Push for specifics. "Young people who like life" is not an audience. "People in Tainan who already read a book a month" is.

## Group C — cadence and boundaries

Ask:

1. Timezone, and how many posts per week?
2. Which days and local times are good? When must the account stay quiet?
3. Maximum posts per day, and maximum public replies per day? If they have no opinion, suggest 1 post per day and 8 replies per day, and let them change it.
4. Which links may appear (site, map, menu, shop)? Anything else is high risk.
5. A do list and a don't list. Offer the starters below and let them edit. Do not silently adopt starters they did not accept.

Starters you may offer:

- Do: specific details, facts that are in the FAQ, the cadence we just set.
- Don't: invent prices or hours, argue with strangers, topics on the avoid list, more than one hashtag unless the style guide says so, posting during quiet hours, mentioning a real person's private business.

Write `cadence.buffer_min` as `3` unless they want a deeper queue.

## Group D — approval and disclosure

Explain the three levels in one short message ([`docs/safety.md`](../docs/safety.md) still applies to all three):

- `always_ask` — you see every post and every public reply first. Required for posts during the first ten editor-approved publications. FAQ replies stay manual then too, unless the editor explicitly turns on `auto_approve_faq_replies_before_ten_posts`. See [Approval decision](../docs/operating-loop.md#approval-decision). Do not turn that flag on during this interview unless they ask.
- `auto_low_risk` — routine, low-risk, fact-checked items can go out; everything else waits.
- `full_auto` — inside the written rules, with sensitive items still waiting.

Default them to `always_ask` if they shrug. Set `approval.posts_approved_count` to `0` for a new setup.

Ask how they want the Meta AI-info label handled.

- `always` — set `disclose_ai: true` on posts you drafted.
- `never` — leave the flag off. Meta may still label on its own. Do not write "as an AI" into the caption unless they ask for that sentence.
- `editor_decides` — they want to choose per post. Leave each item's `disclose_ai` unset until they say, and do not assume `true`.

If they have not answered, keep `policy: editor_decides` and `chosen: false`. Do not publish. When they answer, set `chosen: true` and set `policy` to the option they picked. `editor_decides` with `chosen: true` is a finished answer (decide per post), not a pending question.

Explain that the label is Meta's flag (`is_made_with_ai` on container creation), not a sentence in the caption.

## Group E — voice path

Ask which they want:

- `extract` — you read past posts (API later, or they paste 15–50 posts now)
- `preset` — they describe the voice, useful for a new account
- `both` — extract, then they correct it

Write `voice.source`. The next module does the actual work. If they choose `extract` and you do not have posts yet, ask them to paste a batch before you invent a voice.

## Group F — login mode

Do this only after [`docs/capabilities.md`](../docs/capabilities.md) scored you.

Recommend a mode. Record their choice in `login.method`: `api`, `browser`, or `draft_only`. `login.browser_opt_in` stays false until they accept the browser path after reading its limits. Details of login are Phase 4, not this interview. Do not open OAuth in the middle of the purpose questions.

## Required fields

A profile is usable when these are non-empty and `owned_by_editor` is true:

- `editor.name`
- `account.brand_name`, `account.handle`, `account.platform`
- `purpose.statement`, `audience.who`
- `topics.cover`, `topics.avoid` (lists, may contain one honest item)
- `languages.primary`
- `cadence.timezone`, `cadence.posts_per_week`, `cadence.max_posts_per_day`
- `approval.level`
- `voice.source`
- `login.method`

`scripts/check_workspace.py` checks this shape.

## Handle normalization

Store the handle without `@`. Compare it later to the username the API returns. If they differ, stop and ask. Do not post to a different username than the profile.
