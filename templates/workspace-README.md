# Private workspace

This directory is the editor's account. It was copied from the omni-sns-bot templates.

- Do not commit it, zip it into a public issue, or paste tokens into chat.
- `profile.yaml` is who the account is. `style-guide.yaml` is how it sounds.
- `approval-policy.yaml` decides what may be published without a fresh yes.
- `faq.yaml` is the only fact store replies may quote.
- `calendar.yaml` is the queue. Status values are defined in `core/03-publish.md` of the manual.
- `logs/activity.jsonl` is append-only.
- Secrets, if you have no better store, go in `secrets/` with mode `600`, and only when this directory is outside the omni-sns-bot git clone. Prefer environment variables.

The manual lives in the omni-sns-bot clone. Start at `BOT_START_HERE.md`.
