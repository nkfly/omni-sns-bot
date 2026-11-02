# Platform adapter template

Copy this folder to `platforms/<id>/` and replace every placeholder. Leave `status: not_implemented` until the checklist in [`docs/adding-a-platform.md`](../../docs/adding-a-platform.md) is done.

## Files you owe

| File | Contents |
| --- | --- |
| `README.md` | Status, which mode to pick, pointer to the next file. |
| `capabilities.yaml` | Machine-readable status and auth methods. Start from the copy beside this file. |
| `auth.md` | Official authorization. Token lifetime. Where the secret goes. No passwords. |
| `publish.md` | Map `calendar.yaml` fields to API fields. Include the failure cases. |
| `replies.md` | How to list comments and how to send one reply. |
| `limits.md` | Numbers, the official URL, and the date you checked. |
| `safety.md` | Rules that are specific to this network. |

## Calendar fields you should honor

`text`, `link_attachment`, `publish_at`, `language`, `risk`, `approval`, `published.media_id`, `published.permalink`, `disclose_ai`.

Add a new key only if this platform needs it, and document the default so Threads workspaces stay valid.

## Modes

Always describe `api` (if an official API exists), `browser` (only with opt-in and a human at login), and `draft_only`.
