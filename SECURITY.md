# Security

omni-sns-bot stores no accounts. You run it locally by having your own assistant read the repo.

- Do not open a public issue, pull request, or chat that contains an access token, app secret, password, session cookie, or a dump of a private inbox.
- If a token leaked, revoke it in the Meta app dashboard and complete the authorization window again. Refreshing a leaked token is not enough if someone else may have copied it.
- Passwords are never part of this workflow. The editor signs in to Threads or Meta themselves.
- Report a problem in the docs or scripts by opening an issue that describes the behavior without pasting secrets. If the report needs a log line, delete any `access_token`, `code`, `client_secret`, and `cookie` fields first.

The threat model is a careful editor and their assistant, not a multi-tenant host. See [`docs/safety.md`](docs/safety.md).
