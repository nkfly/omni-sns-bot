# Threads official API

Checked **2026-11-02**. Hosts in Meta's examples are `graph.threads.com`. The overview also allows `graph.threads.net`. Use `https://graph.threads.com` unless `THREADS_GRAPH_HOST` is set. Version prefix: `/v1.0/`.

This path is for the editor's own account. You need HTTP and a secret store ([`docs/capabilities.md`](../../docs/capabilities.md)). If either is missing, do not collect a token; use `draft_only` or the browser path.

Optional helpers (stdlib Python, secrets from the environment only):

- [`scripts/threads/oauth_exchange.py`](../../scripts/threads/oauth_exchange.py) — build the authorize URL, exchange a code, refresh a long-lived token.
- [`scripts/threads/publish_text.py`](../../scripts/threads/publish_text.py) — quota check and text publish.

A bot with a different HTTP tool follows the requests below instead. Do not put the token in a command-line argument; shell history is a log.

## 1. Create the app (the editor does this)

Meta's guide: <https://developers.facebook.com/docs/threads/get-started> and <https://developers.facebook.com/docs/threads/get-started/create-an-app>.

Walk them through it. Do not ask them to share the screen with a password on it if you can avoid seeing the password. You never type the password.

1. Create a Meta app and add the **Threads** use case. The dashboard shows two app ids and two secrets. Every call in this file uses the **Threads App ID** and the **Threads App secret**, not the other pair.
2. Add permissions for v0.1: `threads_basic` (required, cannot be removed), `threads_content_publish`, `threads_read_replies`, `threads_manage_replies`. Add `threads_delete` only if they later ask for deletion. Skip insights, keyword search, mentions, and location tagging until a written task needs them.
3. Under Threads settings, set a valid OAuth redirect URI. The redirect you send later must match that value character for character, including a trailing slash.
4. The same settings page asks for a deauthorize callback URL and a data deletion request URL. Use URLs the editor controls. If they have nowhere to put those and the form will not save, pause the API path and offer `draft_only` or `browser`. Do not invent a public endpoint for them.
5. Add the editor as a **Threads Tester** (App roles → Roles → Add People → Threads Tester). They accept in Threads under Settings → Account → Website permissions. The official note points at <https://www.threads.com/settings/account>.
6. While the app is in development, only people with a role on the app (including Threads Testers) can grant these permissions. App Review and a published app are required before other people can connect. A solo editor posting as themselves does not need App Review on day one. Say that so they do not disappear into review before their first post.

Permission grants for public profiles are valid for 90 days. Refreshing a long-lived token extends that grant another 90 days for a public profile. Meta's get-started page says a private profile's grant is not extended by refresh and must be granted again. The long-lived token page, as checked the same day, says private-profile long-lived tokens can be refreshed and that private-profile grants last 90 days. If a call returns an authorization error, stop and redo the authorization window. Do not burn retries.

## 2. Authorization window

Official page: <https://developers.facebook.com/docs/threads/get-started/get-access-tokens-and-permissions>.

Send the editor this URL (line breaks are spaces):

```text
https://threads.com/oauth/authorize
  ?client_id={THREADS_APP_ID}
  &redirect_uri={REDIRECT_URI}
  &scope=threads_basic,threads_content_publish,threads_read_replies,threads_manage_replies
  &response_type=code
  &state={random}
```

`state` is optional and recommended. Remember it and check it on the way back. Scopes may be comma-separated or spaces (URL-encoded). `threads_basic` is required.

On success, Meta redirects to `redirect_uri` with `?code=...`. A `#_` is appended and is **not** part of the code. Strip it. The code lasts one hour and works once.

On cancel, the redirect carries `error=access_denied`, `error_reason=user_denied`, and `error_description=The+user+denied+your+request`. Meta's parameter table typesets the error as `acceess_denied`; the sample redirect on the same page uses `access_denied`. Trust the sample, and treat either spelling as a no. Do not retry in a loop. Ask whether they want to try again later.

The editor can paste the full redirected URL. Take the `code`. Do not ask them to paste the app secret into the chat. The secret belongs in `THREADS_APP_SECRET`.

## 3. Exchange the code

`POST https://graph.threads.com/oauth/access_token` as form fields:

| Field | Value |
| --- | --- |
| `client_id` | Threads App ID |
| `client_secret` | Threads App secret |
| `grant_type` | `authorization_code` |
| `redirect_uri` | The same URI as in the authorize URL |
| `code` | The code, without `#_` |

Success:

```json
{"access_token": "THQVJ...", "token_type": "bearer", "user_id": 17841405793187218}
```

That token is **short-lived (one hour)**. A rejected exchange looks like `{"error_type":"OAuthException","code":400,"error_message":"Matching code was not found or was already used"}`. Get a new code. Do not retry the same one.

Immediately exchange for a long-lived token. Official page: <https://developers.facebook.com/docs/threads/get-started/long-lived-tokens>.

```http
GET https://graph.threads.com/access_token
  ?grant_type=th_exchange_token
  &client_secret={THREADS_APP_SECRET}
  &access_token={SHORT_LIVED}
```

This call includes the app secret, so it stays on the editor's machine. Success includes `access_token`, `token_type`, and `expires_in` (seconds, about 60 days; the sample shows `5183944`). Store the long-lived token in the secret store. Forget the short-lived one. Do not print either token in the chat summary. Say "stored, user id …, expires in N days" and then call the profile endpoint to show the username.

`scripts/threads/oauth_exchange.py exchange` does both steps and writes the long-lived token to `THREADS_TOKEN_FILE` with mode `600`. It refuses a path inside the git root.

## 4. Refresh

Long-lived tokens last 60 days. Refresh when the token is at least 24 hours old and not yet expired. A refreshed token lasts 60 days from the refresh. A token that was not refreshed within 60 days is dead; only a new authorization fixes it. An expired short-lived token cannot be upgraded.

```http
GET https://graph.threads.com/refresh_access_token
  ?grant_type=th_refresh_token
  &access_token={LONG_LIVED}
```

Replace the stored token with the new value. Log `token_refresh` without the token. The helper command is `oauth_exchange.py refresh`.

During the operating loop, refresh when expiry is inside 7 days.

## 5. Confirm the account

```http
GET https://graph.threads.com/v1.0/{user_id}?fields=id,username,name,threads_profile_picture_url,threads_biography&access_token={token}
```

`user_id` may be `me`. Compare `username` to `profile.account.handle`. On a mismatch, stop.

Profile fields documented on the user reference: `id`, `username`, `name`, `threads_profile_picture_url`, `threads_biography`, `is_verified`.

## 6. Read posts (voice extraction)

```http
GET https://graph.threads.com/v1.0/{user_id}/threads
  ?fields=id,text,timestamp,permalink,media_type,username
  &limit=50
  &access_token={token}
```

`limit` default 25, maximum 100. Page with `after` from the paging cursor. `since` / `until` are Unix timestamps or strtotime-compatible dates; `since` must be `>= 1688540400`. Save the export in the workspace `sources/` directory.

## 7. Publish text

Publishing is two steps. Official guide: <https://developers.facebook.com/docs/threads/posts>. Reference: <https://developers.facebook.com/docs/threads/reference/publishing>.

### Step A — container

`POST https://graph.threads.com/v1.0/{user_id}/threads`

| Field | Text post |
| --- | --- |
| `media_type` | `TEXT` |
| `text` | Required. UTF-8. 500 limit; emoji count as UTF-8 bytes. |
| `access_token` | User token |
| `link_attachment` | Optional URL. Text only. Counts toward the 5-link cap. |
| `topic_tag` | Optional, 1–50 chars, no `.` or `&`. |
| `reply_control` | Optional: `everyone`, `accounts_you_follow`, `mentioned_only`, `parent_post_author_only`, `followers_only`. |
| `is_made_with_ai` | `true` or `false`. Set it here, not on publish. See disclosure policy. |
| `auto_publish_text` | Optional `true`. Text only. Skips step B. |

The first URL inside `text` becomes the link preview when `link_attachment` is omitted. Prefer an explicit `link_attachment` from `profile.links.allowed` so you know what preview you asked for.

Response: `{"id":"<CONTAINER_ID>"}`.

### Step B — publish

Wait about 30 seconds so the container can finish. Then:

`POST https://graph.threads.com/v1.0/{user_id}/threads_publish` with `creation_id` and `access_token`.

Response: `{"id":"<THREADS_MEDIA_ID>"}`. Store that as `published.media_id`.

If publish does not return an id, read container status (below). Do not create a second container until you know the first one did not go out.

`publish_text.py` waits 30 seconds, then polls status no more than once a minute for up to 5 minutes, then publishes when the status is `FINISHED`. Pass `--auto-publish` to use `auto_publish_text` instead. That shortcut returns the container id from the create call; confirm the post is actually on the profile before you create another one.

### Container status

`GET https://graph.threads.com/v1.0/{container_id}?fields=status,error_message&access_token={token}`

| Status | Meaning |
| --- | --- |
| `IN_PROGRESS` | Not ready. Poll at most once a minute, at most 5 minutes. |
| `FINISHED` | Safe to call `threads_publish`. |
| `PUBLISHED` | Already live. Do not publish again. Fetch the media id from your last response or the user's posts. |
| `ERROR` | Read `error_message`. Video failures include `FAILED_DOWNLOADING_VIDEO`, `FAILED_PROCESSING_AUDIO`, `FAILED_PROCESSING_VIDEO`, `INVALID_ASPEC_RATIO` (Meta's spelling), bit rate, duration, frame rate, audio channel errors, or `UNKNOWN`. |
| `EXPIRED` | Not published within 24 hours. Create a new container only after the editor still wants the post. |

## 8. Image, video, carousel

Same two steps. Media URLs must be public; Meta's servers download them. JPEG or PNG for images. See [`limits.md`](limits.md) for size and duration.

Image container: `media_type=IMAGE`, `image_url`, optional `text`, optional `alt_text`.

Video container: `media_type=VIDEO`, `video_url`, optional `text`, optional `alt_text`. Always poll status; video processing is why the 30-second wait exists.

Carousel:

1. Create each child with `is_carousel_item=true` and `IMAGE` or `VIDEO`. No caption required on children.
2. Create the parent with `media_type=CAROUSEL`, `children` as a comma-separated list of container ids (minimum 2, maximum 20), and the caption on the parent.
3. Set `is_made_with_ai` on the parent only. Setting it true on a child returns an error.
4. Publish the parent id. A carousel counts as one post against the 250.

There is no media upload endpoint in this flow. If the file is only on disk, do not pretend you can pass a local path. Use `draft_only` or an opted-in browser session where the editor attaches the file.

## 9. Replies

Read: `threads_basic` + `threads_read_replies`. Send: those plus `threads_content_publish` and `threads_manage_replies`.

List top-level replies:

```http
GET https://graph.threads.com/v1.0/{media_id}/replies
  ?fields=id,text,username,timestamp,permalink,has_replies,is_reply,hide_status,replied_to
  &reverse=false
  &access_token={token}
```

`GET /{media_id}/conversation` returns the whole tree. `reverse` defaults to true (newest first). `username` and `permalink` are returned for public users and for yourself.

`has_replies: true` means you may fetch `/{reply_id}/replies` for the next depth. v0.1 can stop at top-level replies unless the editor asks you to follow a thread.

Create a reply (same two-step publish, with `reply_to_id`):

```http
POST https://graph.threads.com/v1.0/me/threads
  media_type=TEXT
  text=...
  reply_to_id={PARENT_MEDIA_ID}
  access_token=...
```

Then `threads_publish` with that container id. The reply quota is 1,000 per rolling 24 hours, which is not permission to use them. Your cap is `profile.cadence.max_replies_per_day`.

You can reply through the API if you own the root post, or if the app has `threads_keyword_search` or `threads_manage_mentions`. v0.1 does not request those extra permissions and does not reply on other people's posts unless `approval-policy.reply_to_others` is true **and** the editor has approved that change. Default is false.

Hide a top-level reply (ask first; hiding also hides nested replies):

`POST https://graph.threads.com/v1.0/{reply_id}/manage_reply` with `hide=true` or `hide=false`. This is a deletion-adjacent moderation act. The approval policy defaults to ask.

## 10. Map from the calendar

| Calendar | API |
| --- | --- |
| `text` | `text` |
| `link_attachment` | `link_attachment` |
| `topic_tag` | `topic_tag` |
| `reply_control` | `reply_control` |
| `disclose_ai` | `is_made_with_ai` |
| `alt_text` | `alt_text` |
| `kind: text` | `media_type=TEXT` |
| `published.creation_id` | container id from step A |
| `published.media_id` | id from step B |
| reply inbox `comment_id` | `reply_to_id` |

Move calendar status to `publishing` before step A. Persist create intent, then the container id before step B; use the helper's required `--state-file` when available. On confirmed success, `published` and clear `error`. Unknown results stay `publishing`; confirmed rejections become `failed`. Never immediately create another container. Follow the canonical [recovery procedure](../../docs/operating-loop.md#publishing-mechanics) before any retry.

## 11. Errors you will actually see

| Situation | What you do |
| --- | --- |
| `Matching code was not found or was already used` | New authorization. Codes are single-use. |
| Auth / permission error on an otherwise valid call | Token expired, grant expired, or the tester invite was not accepted. Stop. Re-authorize. |
| `THREADS_API__LINK_LIMIT_EXCEEDED` | More than 5 unique links. Cut links. Do not retry unchanged. |
| Publish quota | `quota_usage` at `quota_total`. Wait for the rolling window. Do not create containers you cannot publish. |
| `EXPIRED` | The container sat for 24 hours. Ask before making a new one. |
| Status `ERROR` | Fix the media (it must be publicly fetchable) or the text, then a new container. |
| Username mismatch | Wrong account. Stop. |

Redact `access_token`, `client_secret`, and `code` from anything you show the editor or write to `logs/activity.jsonl`.

## 12. Permissions quick list

| Permission | v0.1 |
| --- | --- |
| `threads_basic` | Required for every call. |
| `threads_content_publish` | Publish posts and the publish half of replies. |
| `threads_read_replies` | `GET` replies. |
| `threads_manage_replies` | `POST` replies and reply-quota fields. |
| `threads_delete` | Only if they later ask to delete. Quota 100/24h. |
| `threads_manage_insights` | Not used. |
| `threads_keyword_search`, `threads_manage_mentions` | Not used. Needed only to reply to posts the account does not own. |
| `threads_location_tagging` | Not used. |

Without advanced access to `threads_content_publish`, the app can publish only for Threads Testers. That is the expected v0.1 solo setup.
