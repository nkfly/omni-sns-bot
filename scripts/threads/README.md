# Threads helpers

Optional. A bot that can run Python 3.9+ and make HTTPS requests can use these instead of assembling requests by hand. A bot that cannot run them follows [`platforms/threads/api.md`](../../platforms/threads/api.md) with whatever HTTP it has. No third-party packages.

Secrets are environment variables or a mode-600 file outside the git root. Both scripts refuse `--token`, `--secret`, `--code`, and the same flags with a value. Shell history would keep them.

## OAuth

```bash
export THREADS_APP_ID="your-threads-app-id"
export THREADS_REDIRECT_URI="https://example.com/auth/"
python3 scripts/threads/oauth_exchange.py authorize-url
```

Open the printed URL, approve it, and put the `code` (without `#_`) in the environment. The app secret never goes in the chat:

```bash
export THREADS_APP_SECRET="..."
export THREADS_CODE="..."
export THREADS_TOKEN_FILE="$HOME/omni-sns-workspace/saltypages/secrets/threads-token"
python3 scripts/threads/oauth_exchange.py exchange
```

The command prints `user_id` and `expires_in` only. Refresh later (token must be at least 24 hours old and unexpired):

```bash
python3 scripts/threads/oauth_exchange.py refresh
```

## Publish text

```bash
export THREADS_ACCESS_TOKEN="$(cat "$THREADS_TOKEN_FILE")"
export THREADS_USER_ID="the-user-id-from-exchange"
python3 scripts/threads/publish_text.py --check-limit
python3 scripts/threads/publish_text.py --dry-run --text-file ./caption.txt
python3 scripts/threads/publish_text.py --text-file ./caption.txt --disclose-ai
```

`--dry-run` does not read the token and does not touch the network. A real run checks `threads_publishing_limit`, creates a text container, waits about 30 seconds, polls container status at most once a minute for up to five minutes, then calls `threads_publish` when the status is `FINISHED`. `--auto-publish` sends `auto_publish_text=true` and skips the second call. It is rejected together with `--reply-to`. The id from that create call is the container id; confirm the live post before creating another.

Pass `--disclose-ai` when the calendar item says `disclose_ai: true`. That sets `is_made_with_ai` on the container.

## Tests

```bash
python3 scripts/threads/publish_text.py --self-test
python3 scripts/threads/oauth_exchange.py --self-test
```

Both run offline.
