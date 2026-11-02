# Capabilities and fallbacks

Do this before the interview. Score yourself honestly. "Unknown" means you try once, and if it fails you mark it false.

Write the result to `capabilities.yaml` in the workspace (or into the memory card):

```yaml
persistent_files: false
persistent_memory: false
http: false
browser: false
schedule: false
secret_store: false
human_channel: true
```

## What each one means

### `persistent_files`

You can write a directory that is still there in a later session.

- **If yes:** use the workspace layout. Re-read the files at the start of each session instead of trusting recollection.
- **If no:** keep the memory card from `templates/memory-card.md`. At the end of every session, show the editor the updated card and ask them to keep it. On the next session, ask them to paste it back if you cannot see it.

### `persistent_memory`

You remember facts across chats even without files.

- **If yes, but no files:** memory holds the card. Still offer the editor a copy, because memory can be edited or dropped.
- **If no memory and no files:** you can set up during this chat only. Say that clearly. Deliver the card at the end so the editor can bring it next time.

### `http`

You can send HTTPS requests to `graph.threads.com` (or `graph.threads.net`).

- **If yes:** the Threads API path is available once the editor finishes app setup.
- **If no:** you cannot run `scripts/threads/` either, unless the editor runs those commands. You may hand them the exact command and let them run it. You do not ask them to paste a token back into the chat.

### `browser`

You can open a site, see the page, click, and type.

- **If yes:** you may offer the browser path later. You do not use it until the editor opts in.
- **If no:** skip every browser step. Do not give click-by-click instructions that you cannot see fail.

### `schedule`

You can run the operating loop without the editor opening a chat (a cron, a reminder tool, a platform job).

- **If yes:** schedule a check shortly before each posting window, and one inbox check on days the account posts. Do not poll more than the limits doc allows.
- **If no:** during setup, tell the editor which mornings or evenings to open the chat. The first thing you do in that chat is one pass of the operating loop. Never claim you are watching the account while you are not running.

### `secret_store`

You can keep a string somewhere that is not the chat transcript and not a git repo. Acceptable stores: an environment variable the editor sets, a file mode `600` outside the git root, or the host's keychain or secret manager.

- **If yes:** Threads tokens and the app secret go there.
- **If the only option is the chat:** you do not have a secret store. Do not request an access token. Use `browser` (cookies stay in the browser profile; you do not export them) or `draft_only`.

### `human_channel`

You can ask the editor a question and receive an answer before publishing.

- **If no:** stay in `draft_only`, write drafts into the workspace, and do not publish. An unattended bot with no way to escalate must not speak as the account.

## Choosing a mode

Do this after you know the capabilities. Say the choice to the editor before Phase 4 locks it.

1. If `http` and `secret_store` and the editor is willing to create a Meta app, recommend `api`.
2. Else if `browser` and the editor, after hearing the browser-path limits, sets `browser_opt_in: true`, use `browser`.
3. Else use `draft_only`.

`draft_only` still runs profile, voice, FAQ, calendar, and self-check. It is the fallback, not a failure.

## Do not

- Do not invent a tool name and hope it exists. Try the capability, then take the fallback.
- Do not ask the editor to install a specific vendor plugin as a requirement. You may mention `scripts/threads/` if they, or you, can run Python 3.
- Do not store the capability answers in this public repo.
