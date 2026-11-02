# Contributing

omni-sns-bot is a manual for assistants, plus a few optional scripts. A good change is one an editor's bot can follow without guessing.

## Ground rules

- Keep the license MIT. New files do not need a copyright header.
- Write specs as instructions to the bot: ordered steps, the fallback when a capability is missing, and when to stop and ask the editor.
- Do not assume a specific vendor's tools, memory product, or browser automation API. Describe the capability, then the fallback. See [`docs/capabilities.md`](docs/capabilities.md).
- Account data stays out of git. Do not add real profiles, tokens, cookies, inboxes, or "anonymized" dumps that are still someone's customers. The only filled account in the repo is the fictional one in `examples/salty-pages/`.
- v0.1 publishes to Threads only. A stub platform must say `status: not_implemented` and must not grow unofficial posting steps. Build a real adapter with [`docs/adding-a-platform.md`](docs/adding-a-platform.md).
- English is the language of the spec. Examples may be multilingual. The README keeps a Traditional Chinese section; update it when the quick start or the roadmap changes.

## Threads API facts

If you change a limit, endpoint, parameter, or permission:

1. Read the current page under <https://developers.facebook.com/docs/threads>.
2. Update [`platforms/threads/`](platforms/threads/) and the date at the top of `api.md` and `limits.md`.
3. Name the source URL in the pull request.
4. If Meta's pages disagree with each other, quote both and tell the bot what to do (usually: stop and re-authorize, or trust the endpoint reference for that call).

Do not copy large passages of Meta's docs into the repo. Link, and write the steps our bot needs.

## Scripts

`scripts/threads/` uses the Python standard library only. Keep it that way.

- Tokens and app secrets come from the environment or a mode-600 file outside the git root. Never from argv.
- `--self-test` must pass without network access and without secrets.
- A change to the publisher needs a self-test that fails before the fix and passes after it.

```bash
python3 scripts/threads/publish_text.py --self-test
python3 scripts/threads/oauth_exchange.py --self-test
python3 scripts/check_workspace.py examples/salty-pages
python3 scripts/check_workspace.py templates --allow-empty
```

`check_workspace.py` needs PyYAML (`pip install pyyaml`). The posting scripts do not.

## Docs style

- Second person, imperative, aimed at the assistant.
- Name files and field names as they are on disk.
- Prefer one canonical description and a link over repeating a quota in five places. [`platforms/threads/limits.md`](platforms/threads/limits.md) owns the numbers.
- When you add a template field, update the template, the module doc, the example, and `scripts/check_workspace.py` if the field is required.

## Pull requests

Say what the editor's bot can do after the change that it could not do before. If you are adding a platform, use the checklist in the adding-a-platform guide and wait until publish, replies, limits, and safety are all real before flipping `status` to `implemented`.
