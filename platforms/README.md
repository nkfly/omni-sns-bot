# Platforms

| Id | Status | Folder |
| --- | --- | --- |
| `threads` | implemented in v0.1 | [`threads/`](threads/) |
| `reddit` | not implemented | [`reddit/`](reddit/) |
| `instagram` | not implemented | [`instagram/`](instagram/) |
| `facebook` | not implemented | [`facebook/`](facebook/) |
| `x` | not implemented | [`x/`](x/) |

Core modules decide what to say. The adapter decides how that text leaves the machine. If `capabilities.yaml` says `not_implemented`, record the editor's interest and do not post.

To add one, follow [`docs/adding-a-platform.md`](../docs/adding-a-platform.md). The empty shape is [`_template/`](_template/).
