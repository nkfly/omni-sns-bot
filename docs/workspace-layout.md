# Workspace layout

The workspace belongs to the editor. It is not part of the omni-sns-bot git history.

## Where to put it

Use the first option that works:

1. `$OMNI_SNS_WORKSPACE/<account-slug>/` if that variable is set.
2. `../omni-sns-workspace/<account-slug>/` next to the clone.
3. `./workspace/<account-slug>/` inside the clone only if you cannot write outside it. It is gitignored. Do not `git add -f` it.

`<account-slug>` is the handle without `@`, lowercase, or a short brand slug if there is no handle yet (`saltypages`).

Create the directory before writing personal answers into the chat's only copy.

## Tree

```text
<account-slug>/
  README.md                 # from templates/workspace-README.md
  capabilities.yaml
  profile.yaml
  style-guide.yaml
  style-notes.md            # optional quotes and editor corrections
  approval-policy.yaml
  faq.yaml
  calendar.yaml
  drafts/                   # one markdown file per item id, when the text is long
  sources/                  # past posts and notes the editor supplied
  logs/activity.jsonl
  secrets/README.md         # points at env vars; do not put the token here if the workspace is inside the clone
```

Copy from [`templates/`](../templates/). Leave `credentials.example.yaml` in the repo; it is documentation of variable names, not a file to fill in.

If the workspace is outside the git root and you have no keychain, a token file may live at:

```text
<account-slug>/secrets/threads-token
```

with mode `600`. The OAuth helper will refuse to write that file if it resolves inside a git working tree. Prefer an environment variable when the editor can set one.

## Files

| File | Written by | Read when |
| --- | --- | --- |
| `capabilities.yaml` | Bot, Phase 0 | Start of every session |
| `profile.yaml` | Interview | Every draft and publish decision |
| `style-guide.yaml` | Voice phase | Every draft |
| `approval-policy.yaml` | Phase 4, editor edits | Before any public action |
| `faq.yaml` | Phase 5 and the inbox loop | Replies and fact checks |
| `calendar.yaml` | Operating loop | Every session |
| `logs/activity.jsonl` | Append-only | When you need to avoid repeating yourself |
| `sources/` | Editor pastes, or API export the editor asked for | Voice extraction |

## Activity log

Append one JSON object per line. Never rewrite old lines. Never log tokens, authorization codes, cookies, or full message text from a stranger when a short paraphrase will do. The editor's own post text may be stored in the calendar; the log only needs the id.

```json
{"ts":"2026-11-02T19:40:00+08:00","actor":"bot","action":"draft","platform":"threads","item_id":"2026-11-04-window","result":"ok","detail":"self-check pass, waiting for editor"}
```

| Field | Values |
| --- | --- |
| `ts` | ISO 8601 with timezone offset |
| `actor` | `bot` or `editor` |
| `action` | `setup`, `idea`, `draft`, `approve`, `reject`, `schedule`, `publish`, `reply`, `faq_add`, `escalate`, `skip`, `error`, `token_refresh`, `mode` |
| `platform` | `threads` or `none` |
| `item_id` | calendar id, faq id, or `""` |
| `result` | `ok`, `blocked`, `failed` |
| `detail` | one short sentence, no secrets |

## Memory card

When you cannot keep files, fill [`templates/memory-card.md`](../templates/memory-card.md) and treat it as the workspace. It holds the same decisions in compressed form. It does not hold tokens. Say that in the card.

## Before you commit anything, anywhere

If you are working inside the clone and the editor also uses git:

- `git status` must not list the workspace or a token file.
- If it does, unstage it and confirm `.gitignore` applies.
- Do not commit `examples/` changes that contain a real account. The fictional example is the only filled account allowed in git.

## Validate

From the clone, if PyYAML is installed:

```bash
python3 scripts/check_workspace.py /absolute/path/to/account-slug
```

The checker looks for required keys and for secret-shaped values. It does not call Threads.
