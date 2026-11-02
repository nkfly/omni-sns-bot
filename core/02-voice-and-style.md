# Voice and style

Goal: `style-guide.yaml` plus a handful of real sentences the editor recognizes as theirs. Every later draft is measured against this file and against [`avoid-ai-voice.md`](avoid-ai-voice.md).

Do not publish while you are still learning the voice.

## Choose a path

Use `profile.voice.source`.

| Source | Do this |
| --- | --- |
| `extract` | Collect past posts, then derive the guide. |
| `preset` | Run the preset interview. There is no corpus. |
| `both` | Extract, then run only the preset questions that correct a mistake. |

If they have fewer than 8 posts, say the sample is thin, lean on the preset, and mark `style-guide.evidence.thin_sample: true`.

## Collecting posts for extraction

Prefer the account's own top-level posts, not replies. Replies go in a separate note because people write differently in replies.

**API, once `login.method` is `api` and a token works.** `GET /{threads-user-id}/threads` with `fields=id,text,timestamp,permalink,media_type` and `limit=50`. Page with `after` until you have about 30 text posts or the posts run out. See [`platforms/threads/api.md`](../platforms/threads/api.md). Store the export in `sources/past-posts.md` or `.json` in the workspace, not in this repo.

**No API yet.** Ask the editor to paste 15–30 posts. Tell them replies are optional and to skip posts they do not want the voice to imitate (ads they regret, arguments).

**Browser.** Only if they already opted in. Scroll their profile and copy text they confirm is theirs. Do not scrape other people.

Stop at 50 posts. More than that rarely changes the guide and invites you to overfit one weird week.

## What to measure

Compute these from the corpus and write the numbers into the guide, not just adjectives:

- Typical sentence length, in characters for Chinese or Japanese and in words for English.
- Whether fragments and one-line posts are normal.
- Emoji per post: median, and the actual characters used.
- Hashtags per post, which tags recur, and whether a bare `#1` style number shows up (Threads will not treat a bare number as a topic).
- How often a post ends in a question.
- Line breaks: none, single, or a blank line between beats.
- Language mix: which language leads, and the exact situation for a second language.
- Openings they actually use, and openings they never use ("大家好" every time is a habit; never using it is also a habit).
- Words or phrases that recur. Words you expected from a generic brand account that never appear.
- Topics in the corpus versus `profile.topics`. Note the difference. The profile wins if they conflict; mention the conflict to the editor.

## Write the guide

Fill [`templates/style-guide.yaml`](../templates/style-guide.yaml). Rules must be testable.

Weak: "Be friendly and authentic."

Strong: "Sentences usually under 20 Chinese characters. No emoji. At most one exclamation mark in ten posts. Address the reader as 你, never 大家. English only for book titles."

Include 4–8 `gold_posts`: verbatim posts from the corpus that the editor would be happy to repeat. These are the standard. Paraphrasing them into cleaner prose destroys the evidence. If a gold post has a typo they like, keep the typo and note it.

Add `banned_from_corpus`: phrases that never occur and should stay absent. Merge that list with the language section of [`avoid-ai-voice.md`](avoid-ai-voice.md). The anti-AI list always applies, even if you somehow find one of those phrases in an old post. If the editor truly wants a phrase from the ban list, they must put it in `allowed_exceptions` in their own words.

`style-notes.md` can hold the longer commentary and the editor's corrections ("the lamp post was a joke, don't make lamps our whole personality"). The YAML remains the checklist.

## Preset interview

Ask, and wait between clusters:

1. Three adjectives for the voice, and one adjective it must not be.
2. Formal speech, or the way you talk in a group chat?
3. A person or account to lean toward, and what you must not copy from them.
4. Emoji: never, rarely, or which specific ones?
5. Hashtags: never, or a short allowlist?
6. Do you want line breaks, or a single block?
7. Paste one paragraph you wrote (a post, a LINE message, a product note) that sounds right.
8. Words you hate seeing on your account.

Write their paragraph into `gold_posts` with `source: editor_sample`. Invent nothing around it.

## Agree the guide before real posts

1. Show a short summary in their language (half a screen, not the raw YAML, unless they ask).
2. Draft two posts on topics they approved. Mark them as practice in the calendar with `status: pending_approval` and a note `practice: true`, or keep them out of the calendar and in `drafts/practice-1.md` if you do not want them scheduled.
3. Run [`self-check.md`](self-check.md) on each. Show the draft and the failed lines. Do not show a draft that still has a hard fail; rewrite once first.
4. Ask "where does this not sound like you?" Apply their answer to the guide, then rewrite. Two rounds is enough. If it is still wrong, the guide is wrong; do not keep generating until something slips through.

## Replies have a tighter voice

Replies are shorter than posts. Add `replies:` in the style guide:

- typical length
- whether you answer the question in the first line
- whether you thank people (default: only when they did something specific)
- a ban on "Great question" / 「好問題」/ 「いい質問ですね」as an opener

## When the editor corrects a published style miss

Update the guide the same day. Add the bad sentence under `rejected_patterns` with one line on why. Do not argue from the gold posts if they say the gold posts are outdated; replace the gold.
