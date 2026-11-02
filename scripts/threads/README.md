# Threads helpers

Optional. A bot that can run Python 3.9+ and make HTTPS requests can use these instead of assembling requests by hand. A bot that cannot run them follows [`platforms/threads/api.md`](../../platforms/threads/api.md) with whatever HTTP it has. No third-party packages.

Secrets are environment variables or a mode-600 file outside the git root. The helpers never accept credential values as command-line arguments; the OAuth helper also explicitly rejects `--code`. Shell history would keep literal values even in an `export` command, so use the hidden-input example below.

## OAuth

```bash
export THREADS_APP_ID="your-threads-app-id"
export THREADS_REDIRECT_URI="https://example.com/auth/"
python3 scripts/threads/oauth_exchange.py authorize-url
```

Open the printed URL, approve it, and verify the redirect's `state` against the printed value before using the `code` (without `#_`). The helper does not receive the redirect or perform that comparison for you. On a mismatch, stop. The app secret and code never go in the chat or a literal shell assignment. In an interactive Bash terminal with command tracing off, read them without echoing or recording their values in history:

```bash
set +x
read -r -s -p 'Threads app secret: ' THREADS_APP_SECRET
printf '\n'
read -r -s -p 'Authorization code: ' THREADS_CODE
printf '\n'
export THREADS_APP_SECRET THREADS_CODE
export THREADS_TOKEN_FILE="$HOME/omni-sns-workspace/saltypages/secrets/threads-token"
python3 scripts/threads/oauth_exchange.py exchange
unset THREADS_APP_SECRET THREADS_CODE
```

The command prints non-secret metadata, including `user_id`, `expires_in`, and the token-file path. The token is written atomically. On macOS and Linux the file is mode `600` before it replaces the previous one, and both helpers reject a token file whose mode is not `600` or whose owner is someone else. On Windows those Unix bits are not meaningful (`os.fchmod` is absent before Python 3.13, and `stat.S_IMODE` does not come back as `600`), so the helpers skip the mode and owner checks, skip the directory fsync, and still refuse a path inside a git repo. Put the Windows file under `%APPDATA%\omni-sns-bot\`, which is outside the clone. The scripts do not call Windows Credential Manager. If the editor already uses it, they can load the secret into the process environment without printing it; do not paste it into the chat.

The same hidden-input rule in PowerShell. `Read-Host -AsSecureString` does not echo and does not put the secret on the command line, so history stores the command rather than the value:

```powershell
$env:THREADS_APP_ID = "your-threads-app-id"
$env:THREADS_REDIRECT_URI = "https://example.com/auth/"
python scripts/threads/oauth_exchange.py authorize-url

$secret = Read-Host -AsSecureString 'Threads app secret'
$code = Read-Host -AsSecureString 'Authorization code'
$env:THREADS_APP_SECRET = [System.Net.NetworkCredential]::new('', $secret).Password
$env:THREADS_CODE = [System.Net.NetworkCredential]::new('', $code).Password
$env:THREADS_TOKEN_FILE = Join-Path $env:APPDATA 'omni-sns-bot\saltypages\secrets\threads-token'
python scripts/threads/oauth_exchange.py exchange
Remove-Item Env:THREADS_APP_SECRET, Env:THREADS_CODE
$secret = $null
$code = $null
```

Refresh later (token must be at least 24 hours old and unexpired):

```bash
python3 scripts/threads/oauth_exchange.py refresh
```

## Publish text

```bash
unset THREADS_ACCESS_TOKEN
export THREADS_USER_ID="the-user-id-from-exchange"
python3 scripts/threads/publish_text.py --check-limit
python3 scripts/threads/publish_text.py --dry-run --text-file ./caption.txt
python3 scripts/threads/publish_text.py --text-file ./caption.txt --disclose-ai --state-file "$HOME/omni-sns-workspace/saltypages/attempts/item-id.json"
```

`--dry-run` does not read the token and does not touch the network. A real run checks `threads_publishing_limit`, creates a text container, waits about 30 seconds, polls container status at most once a minute for up to five minutes, then calls `threads_publish` when the status is `FINISHED`. `--auto-publish` sends `auto_publish_text=true` and skips the second call. It is rejected together with `--reply-to`. The id from that create call is the container id; confirm the live post before creating another.

Using `THREADS_TOKEN_FILE` directly avoids retaining an old token in `THREADS_ACCESS_TOKEN` after a refresh. If you supply an environment token instead, replace or unset it after refresh; child commands cannot update your shell.

PowerShell equivalent. This does not place the token text in the command, so it is not written to history:

```powershell
Remove-Item Env:THREADS_ACCESS_TOKEN -ErrorAction SilentlyContinue
$env:THREADS_USER_ID = "the-user-id-from-exchange"
$env:THREADS_TOKEN_FILE = Join-Path $env:APPDATA 'omni-sns-bot\saltypages\secrets\threads-token'
python scripts/threads/publish_text.py --check-limit
python scripts/threads/publish_text.py --text-file .\caption.txt --disclose-ai --state-file (Join-Path $env:APPDATA 'omni-sns-bot\saltypages\attempts\item-id.json')
```

Pass `--disclose-ai` when the calendar item says `disclose_ai: true`. That sets `is_made_with_ai` on the container. For `editor_decides`, ask until this item has an explicit true or false; `null` is not a decision. The helper does not read the workspace or grant approval.

Each real publish or reply requires one stable `--state-file` for that calendar/inbox item. It is reserved before create and records the container id before polling. Reusing it refuses a second create, even after success. Keep it in the private workspace. Read status after interruption or an unknown result:

```bash
python3 scripts/threads/publish_text.py --recover --state-file "$HOME/omni-sns-workspace/saltypages/attempts/item-id.json"
```

Recovery is read-only. Never delete the journal or choose another path just to rerun create. Follow [Publishing mechanics](../../docs/operating-loop.md#publishing-mechanics) to reconcile the outcome and obtain authorization for any new attempt. A gap between remote create and saving its response is still possible; the pre-create journal blocks blind retries even when no id was saved.

`--check-limit --reply-to MEDIA_ID` checks both post and reply quotas. Plain `--check-limit` checks the post quota. Missing, malformed or exhausted required quotas block publishing.

## Tests

```bash
python3 scripts/threads/publish_text.py --self-test
python3 scripts/threads/oauth_exchange.py --self-test
```

Both run offline.

Regression tests (PyYAML is needed for workspace cases):

```bash
python3 -m unittest discover -s tests -v
```
