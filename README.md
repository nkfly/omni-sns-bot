# omni-sns-bot

An open-source manual that turns **any** AI assistant into a social-media editor (小編) for one account. v0.1 speaks Threads fluently. The same layout can grow adapters for other platforms. MIT licensed.

The bot reads this repository, interviews the editor, and keeps the account's profile, voice, FAQ, calendar, and secrets in the editor's own workspace. Nothing about a real account is stored here.

## Tell your bot this

> Download https://github.com/nkfly/omni-sns-bot, read the whole repo starting at `BOT_START_HERE.md`, then set me up as a Threads editor.

The bot should follow [`BOT_START_HERE.md`](BOT_START_HERE.md). Humans can read this README and then the same file.

Setup follows the [conversation contract](docs/setup-flow.md): reuse answers,
accept explicit "none"/"later", check authorized existing browser access before
requesting a large paste, and keep style/template preferences separate from
permission to send. You can finish setup without writing or publishing a post.

## What you get

- **Account profile.** A guided interview: brand, handle, purpose, audience, topics, do/don't list, cadence, languages, links, and an approval policy.
- **Voice and style.** Extract a style guide from past posts, or preset one. Includes a concrete "don't sound like a language model" guide for English, Traditional Chinese, and Japanese, plus a self-check the bot runs before it shows a draft.
- **Proactive posting on Threads.** Official Threads API (Meta) and a browser fallback for assistants that can drive a browser. Content calendar, draft → approval → publish, and three approval levels. If the bot cannot log in, it still produces a queue the editor can post by hand (`draft_only`).
- **FAQ and replies.** A knowledge base grounded in what the editor actually said. Triage incoming comments: answer from the FAQ, escalate, ignore spam, or hold sensitive ones. New confirmed questions get written back into the FAQ.

The bot does not need a special plugin. Instructions are written against capabilities ("if you can make HTTP requests", "if you can keep a file", "if you can run something every morning") and each one has a fallback.

## Repository map

| Path | What it is |
| --- | --- |
| [`BOT_START_HERE.md`](BOT_START_HERE.md) | The procedure the bot executes |
| [`docs/setup-flow.md`](docs/setup-flow.md) | Setup progress, browser discovery, cadence and scoped decisions |
| [`AGENTS.md`](AGENTS.md) | Short override list and read order |
| [`core/`](core/) | Profile, voice, publishing, FAQ |
| [`platforms/threads/`](platforms/threads/) | Threads API, browser path, quotas |
| [`platforms/`](platforms/) | Stubs for Reddit, Instagram, Facebook, X |
| [`templates/`](templates/) | Empty files the bot copies into a private workspace |
| [`examples/salty-pages/`](examples/salty-pages/) | A fictional bookstore, filled in end to end |
| [`scripts/threads/`](scripts/threads/) | Optional stdlib helpers for the official API |
| [`docs/`](docs/) | Architecture, safety, workspace, operating loop |

## How a session works

1. The editor clones or downloads the repo and asks their assistant to read `BOT_START_HERE.md`.
2. The assistant opens a private workspace **outside** the clone and interviews the editor.
3. It writes a profile, a style guide, an approval policy, and a starter FAQ.
4. It drafts in that voice, runs the self-check, and waits for approval according to the policy.
5. It publishes to Threads only through the official API or the opt-in browser path, and only inside the account's cadence and Meta's quotas.
6. It reads replies, answers from the FAQ, and escalates the rest.

`examples/salty-pages/` is fiction (a Tainan bookstore that does not exist). It shows what a finished workspace looks like. Do not post it.

## Approval, in one screen

| Level | Behavior |
| --- | --- |
| `always_ask` | Every public post and reply waits for the editor. **Start here.** |
| `auto_low_risk` | Publishes only when the item is on-topic, fact-checked against the workspace, inside cadence, and low risk. Everything else waits. |
| `full_auto` | Posts and routine replies inside the written rules. Sensitive items, deletions, and replies on other people's posts still wait. The first ten posts require editor approval. |

The canonical [approval decision](docs/operating-loop.md#approval-decision) requires `always_ask` for posts until ten editor-approved posts have actually published, followed by an explicit request to loosen the level. Replies follow that gate too, unless the editor explicitly enables auto-approval of editor-sourced FAQ answers. Without persistent files, use the [memory-card loop](docs/operating-loop.md#memory-card-loop): manual drafting in the current conversation with `always_ask`. `capabilities.yaml` records `storage` as `local_files`, `memory_card`, or `external`.

Safety rules (no passwords in the repo, no invented facts, no spam, respect Threads' limits) apply at every level. See [`docs/safety.md`](docs/safety.md).

## Threads, specifically

v0.1 targets the official Threads API:

- Hosts `graph.threads.com` or `graph.threads.net`
- Create a container with `POST /{threads-user-id}/threads`, then publish with `POST /{threads-user-id}/threads_publish`
- Text posts up to 500 characters (emoji count as UTF-8 bytes)
- 250 API-published posts and 1,000 API-published replies per rolling 24 hours

Details, OAuth, and the sources those numbers came from are in [`platforms/threads/`](platforms/threads/). They were checked on 2026-11-02. The API changes; the bot is told to trust the current Meta docs when a call disagrees with this repo.

A personal editor can use a Meta app in development with themselves as a Threads Tester. App Review matters when people who are not testers on the app will connect. The browser path is a fallback, with the editor present for login, and it is not the supported automation API.

## Roadmap

| Version | Platforms |
| --- | --- |
| **0.1 (this release)** | Threads, fully specified |
| Next | Reddit, Instagram, Facebook, as adapters that follow [`docs/adding-a-platform.md`](docs/adding-a-platform.md) |
| Later | X, tighter inbox tooling (webhooks) once a platform adapter needs them, and external storage connectors such as Google Drive. A connector would sync the same workspace files. The operating loop stays as it is. |

Stubs under `platforms/` are intentional. They record the slot and the rule: do not invent an unofficial publisher and call it done.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Bugs in the Threads instructions should cite the official doc and the date you checked it. Do not send account dumps or tokens.

## License

[MIT](LICENSE) © 2026 nkfly.

---

## 繁體中文

**omni-sns-bot** 是一份給 AI 助理看的開源操作手冊（MIT）。它把任何助手變成一個社群小編：先訪問你、建立聲線、再依你的審核規則在 Threads 發文與回覆。帳號資料、FAQ、行事曆和憑證只放在你自己的工作區，不會進這個公開 repo。

### 叫你的 bot 這句話

> 下載 https://github.com/nkfly/omni-sns-bot，從 `BOT_START_HERE.md` 開始把整個 repo 讀完，然後幫我當 Threads 小編把帳號設定好。

### 你會得到什麼

設定時會保留已回答的內容，「沒有」與「之後再說」也會記下；先確認能否使用你授權的已登入瀏覽器，再請你大量貼上舊文。「每週至少」與「最多」分開保存，風格範例或回覆範本的認可也不等於同意發送。你可以只完成設定，今天不寫、不發布貼文。

- **帳號設定。** 品牌名稱、帳號、目的、受眾、主題、要做／不要做、發文節奏、語言、連結、審核政策。bot 會分批問，不會一次丟三頁問卷。
- **聲線。** 從舊貼文學，或由你先描述風格。內建「不要寫得像 AI」的檢查，涵蓋英文、繁體中文、日文，每則草稿公開前都要過自檢。
- **登入並主動發文。** 走 Threads 官方 API，或（你明確同意後）用瀏覽器協助。有內容日曆，以及「每次都問／低風險可自動／規則內自動」三級審核。bot 如果不能登入，仍然可以產出草稿讓你自己貼（`draft_only`），這也算完成設定。
- **FAQ 與留言。** 只用你提供的事實回答。留言會分流：FAQ 答得了、要問你、垃圾訊息略過、敏感內容先暫停。你確認過的新問題才寫回 FAQ。

無法保存檔案時，使用 memory card，在當次對話產生草稿，由你手動發布；不會啟動 API、瀏覽器發文或排程。已確認發布、而且比最近 5 則更舊的貼文只留編號、連結和日期。前十篇已發布貼文必須逐篇經你批准。留言在那之前也不自動送出，除非你明確打開「用你確認過的 FAQ 回答」。之後也只有你明確要求才能放寬審核。工作區的 `storage` 可以是本機檔案、memory card，或未來的外部儲存。

### 路線圖

v0.1 只完整支援 **Threads**。接下來依序補 Reddit、Instagram、Facebook，之後是 X。外部儲存（例如 Google Drive）也在路線圖上：接上後只同步同一套工作區檔案，操作迴圈不用改。新平台要照 [`docs/adding-a-platform.md`](docs/adding-a-platform.md) 加接頭，不能在 stub 裡隨便寫一個發文步驟就算完成。

`examples/salty-pages/` 是虛構的台南書店，用來示範一份填好的工作區長什麼樣子，不要拿去發文。

### 參與

請看 [`CONTRIBUTING.md`](CONTRIBUTING.md)。修正 Threads API 說明時，附上 Meta 官方文件連結和你查證的日期。不要把 token、密碼或真實留言紀錄貼進 issue 或 PR。
