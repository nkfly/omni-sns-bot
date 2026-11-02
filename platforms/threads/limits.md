# Threads limits

Checked **2026-11-02** against:

- <https://developers.facebook.com/docs/threads/overview>
- <https://developers.facebook.com/docs/threads/posts>
- <https://developers.facebook.com/documentation/threads/retrieve-and-manage-replies>
- <https://developers.facebook.com/docs/threads/troubleshooting>

The bot enforces the account cadence first. These are the platform ceilings. Exceeding them is a failed publish, not a goal to approach.

## Publishing ceilings

| Action | Ceiling | Window | How to read usage |
| --- | --- | --- | --- |
| API-published posts | 250 (`quota_total`) | rolling 24h (`quota_duration` 86400 seconds) | `quota_usage` |
| API-published replies | 1,000 | rolling 24h | `reply_quota_usage` |
| Deletions | 100 | rolling 24h | `delete_quota_usage` |
| Location searches | 500 | rolling 24h | `location_search_quota_usage` |

A carousel counts as one post. The `POST /{threads-user-id}/threads_publish` endpoint enforces the post ceiling.

```http
GET https://graph.threads.com/v1.0/{threads-user-id}/threads_publishing_limit
  ?fields=quota_usage,config,reply_quota_usage,reply_config,delete_quota_usage,delete_config
  &access_token={token}
```

Post fields need `threads_basic` and `threads_content_publish`. Reply fields also need `threads_manage_replies`. Deletion fields need `threads_delete`. The response wraps the object in `data: [ ... ]`.

Call this before publishing and before replying. If `quota_usage >= quota_total`, do not create another container. If the call itself fails, do not publish (fail closed).

## Request rate

Meta counts calls per app and app user over a rolling 24 hours:

```text
Calls within 24 hours = 4800 * Number of Impressions
```

Impressions are how often any content from that Threads account entered a person's screen in the last 24 hours. If impressions are under 10, Meta uses 10. There is a separate CPU-time budget in the same overview (`720000 * impressions` for `total_cputime`, `2880000 * impressions` for `total_time`).

Practical consequence: do not poll in a tight loop. Container status: at most once a minute, for at most 5 minutes. Inbox: once per operating-loop wake, not continuously.

## Text, links, media

| Rule | Value |
| --- | --- |
| Text length | 500. Emoji count as their UTF-8 byte length, not as one character. |
| Links | At most 5 unique URLs in the text plus a distinct `link_attachment`. Over the cap, container creation fails with `THREADS_API__LINK_LIMIT_EXCEEDED` (Meta: in force from 22 Dec 2025). |
| `link_attachment` | Text posts only. |
| Topic tag | 1–50 characters. Period and ampersand are not allowed. One topic per post. |
| Carousel | 2 to 20 children. Images and video, not text children. |
| Alt text | Up to 1,000 characters. |
| Image | JPEG or PNG, max 8 MB, aspect ratio limit 10:1, width 320–1440, sRGB. |
| Video | MOV or MP4, max 300 seconds, max 1 GB. Further codec rules are on the overview page. |
| Container life | Unpublished containers expire after 24 hours (`EXPIRED`). |

`auto_publish_text=true` publishes a **text** container in the create call and skips `threads_publish`. It does not apply to image, video, or carousel.

## Browser-path cap (ours, not Meta's)

The API ceilings above are for the official API. A browser session is easier to mistake for spam and is not the supported automation path. Unless the editor writes a lower number into the profile, the bot's own cap on the browser path is **3 posts per day** and **10 replies per day**, and never higher than `profile.cadence`. Space actions out. If Threads shows a challenge, stop.

## What a normal editor account should do

A cadence of a few posts a week and a handful of replies a day sits far under 250 and 1,000. If you are anywhere near those ceilings, you are not following the profile. Stop and talk to the editor.
