# Self-check

Run this on the exact string you are about to show the editor or publish. Checking an earlier draft does not count. Strip nothing before the check except the YAML front matter and HTML comments you added; those never go out.

Write the result as an HTML comment at the bottom of the draft file, or hold it in the chat when you show the draft. Do not include the comment in the published caption.

```text
self-check: pass|fail
- voice: pass|fail — one line
- specific: pass|fail
- banned: pass|fail
- shape: pass|fail
- length: pass|fail — estimated units, limit
- emoji_hashtag: pass|fail
- facts: pass|fail — cite faq or profile keys
- safety: pass|fail
- language: pass|fail
```

## Hard fails

Any one of these means `fail`. Rewrite once using [`avoid-ai-voice.md`](avoid-ai-voice.md). If the rewrite still has a hard fail, show the editor the checklist and do not publish.

| Check | Fail when |
| --- | --- |
| `voice` | A regular customer of this account would not recognize it. Compare to `gold_posts`, sentence length, and `replies` rules. |
| `specific` | No concrete detail from this brand. The post still works if you rename the account. |
| `banned` | A phrase or structure from `avoid-ai-voice.md`, or from `style-guide.rejected_patterns`, unless it is in `allowed_exceptions`. |
| `shape` | Hook + three beats + CTA, bullets, or a closer the guide forbids. |
| `length` | Over the platform limit, or far outside the guide (more than about twice the usual post) without a reason in the calendar note. Threads text: 500, with emoji counted as UTF-8 bytes. See the limits doc. |
| `emoji_hashtag` | Count outside `style-guide.emoji` or `hashtags`. A hashtag the guide does not allow. |
| `facts` | A price, hour, policy, stock level, or event that is not in the workspace. A link whose host is not on `profile.links.allowed`. |
| `safety` | Hits [`docs/safety.md`](../docs/safety.md): medical/legal/financial advice, a real person's private matter, hate, a minor, a don't-list topic, quiet hours ignored, or a sensitive triage that should have stopped. |
| `language` | Wrong language, or a mix the guide does not allow. |

## Publishing rule

- `self-check: fail` — do not publish, do not hand the text to the browser composer as the final caption.
- `self-check: pass` — eligible to show the editor, or to publish if the approval policy already allows this item.
- Practice drafts follow the same rubric.

## Length estimate

For Threads, count each ordinary character as 1. Count emoji and related joiners as their UTF-8 byte length. The optional script does this estimate:

```bash
python3 scripts/threads/publish_text.py --dry-run --text-file ./caption.txt
```

`--dry-run` does not need a token and does not call the network. If the estimate and the API ever disagree, the API wins. Stay under the limit on the estimate so you are not surprised.

## Do not grade your own excuses

"It's a bit generic but the emoji makes it friendly" is a fail on `specific` and maybe on `emoji_hashtag`. Do not mark `pass` with a note that admits the fail.
