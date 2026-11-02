# Threads in the browser

Use this only when `api` is not available and the editor has set `login.browser_opt_in: true` after you told them the limits below. If you cannot drive a browser, do not recite a click path and hope. Stay on `draft_only` and give them the caption.

The official API is the supported publisher. This fallback exists so an assistant that can use a browser can still help an editor who will not create a Meta app. It is slower, easier to get wrong, and capped harder.

## Say this before they opt in

- You will never ask for the password, a backup code, or a 2FA secret. They log in on Threads themselves. If a checkpoint, captcha, or "was this you" prompt appears, you stop and they finish it.
- You will not export cookies or the browser profile into the workspace, the chat, or the git repo.
- You will not post on a schedule you cannot actually run. If you have no scheduler, you only touch the composer while this chat is open.
- Your own cap, unless they set a lower cadence, is 3 posts a day and 10 replies a day, spaced out, and still inside quiet hours. This cap is ours. It is lower than the API ceilings on purpose.
- You stop on the first warning, action block, or unexpected login wall. You do not open a second account to route around it.

If they say yes, set `profile.login.browser_opt_in: true` and `login.method: browser`. If they say no, set `draft_only` and do not ask again this session.

## Sign in

1. Open `https://www.threads.com/` (or `https://www.threads.net/` if that is where the site sends you).
2. If a login form is showing, hand control to the editor. Look away from password fields if your browser tool lets you. Wait until they say they are in.
3. Read the logged-in username from the page. It must match `profile.account.handle`. If it does not, stop, even if they say "close enough".
4. Do not store the session anywhere except the browser's own profile.

## Publish

Do this only for a calendar item that already passed the operating-loop gates, including approval. Follow [Without the Python helper](../../docs/operating-loop.md#without-the-python-helper). A click you are not sure landed is not a failed post.

1. If `attempts/<item-id>.json` already exists and is not a confirmed miss plus an editor-authorized retry, stop and reconcile. Do not open the composer for a second copy.
2. Write that intent file with `phase: intent` and the caption hash before you touch the composer. Then set the calendar item to `publishing`.
3. Open the compose control for a new thread. Paste the caption only (no front matter, no self-check comment). Attach a link or image only if the calendar says so and the editor can reach the file.
4. Set the intent `phase` to `result_unknown` before the Post control. Then activate Post once, only if the composer text still matches the approved caption. If it does not, stop.
5. Reload the logged-in profile and look for that exact caption. If it is there, copy the permalink into `published.permalink`, set `phase` to `published`, and log it.
6. If you do not see it, or the page did not reload, leave `result_unknown`. Do not press Post again.
7. If you cannot find a reliable post control, leave the text in the composer, set the item back to `approved`, set the intent `phase` to `not_published` only after you can see the caption is not already live, and ask the editor to press the button. That is a successful assist, not a retry.

A later attempt requires both a profile check that shows the caption is absent and a fresh yes from the editor. Archive the old intent file; do not delete it. Do not run several posts back to back.

## Replies

Open the account's own post, find the comment that matches the inbox item, and reply only when triage and the approval policy allow a send. Paste the approved reply. One reply. Then stop.

If you cannot reliably match the on-screen comment to the inbox item, switch that session to `draft_only` for replies: show the editor the draft next to the comment they pasted, and let them send it.

## When the UI has moved

Threads renames buttons. This repo stores no CSS selectors, on purpose. Identify controls by their accessible name in the editor's language (Post / 發佈 / 投稿, Reply / 回覆). If you cannot find them, stop and ask the editor to take the last click.

## What you still do not do

- No password typing, no reading a password manager aloud, no bypassing a checkpoint.
- No private messages. v0.1 is public posts and public replies.
- No scraping followers, no mass replies, no posting the same caption across accounts.
- No copying cookies into the API helper. Browser mode and API mode do not mix credentials.
