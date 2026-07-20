
This document defines every command that can be used in the ChatUI program:

| Input               | Behavior                                         |
| ------------------- | ------------------------------------------------ |
| prompt              | Get answers from the vault                       |
| `/draft`            | Start or resume drafting a paper                 |
| `/classify`         | Suggest location, tags, and wikilinks for a file |
| `/review [subject]` | Guided study session on a given topic            |
| `/ingest`           | Rebuild the vector database from the vault       |
| `/web`              | Toggle the web-search supplement                 |
| `/model [name]`     | Show or switch the active chat model             |

## Notes
---
- `/tags` on a file always folds in a deterministic tag for every ancestor folder it sits in (e.g. a file under `000 - Information Science/Ontology/` picks up both `ontology` and `information-science`), alongside whatever the LLM suggests for content — no model call needed for that part, and a tag the file already carries (any case) is skipped.
- Selecting a folder (rather than a file) in the sidebar tree and running `/tags` syncs every file inside it to the current folder structure in one pass: adds whatever folder-derived tags are missing, and removes any tag that used to name a real vault folder but isn't one of that file's current ancestors anymore (e.g. after the folder itself was moved or renamed) — a genuine topic tag that never matched any folder name is never touched. Shown as `+add`/`-remove` in the usual review checklist before `/done`.
- The sidebar file tree polls the vault on disk every couple of seconds and always reflects it, whether or not `/ingest` has run — a file dropped in by another editor or Obsidian shows up on its own, colored green to mean "on disk, not embedded yet." A path still in the ingest index but with no file on disk anymore shows in red as a `[stale index]` entry; selecting it prompts to run `/ingest` to clean it up. The poll skips rebuilding while a search filter is active, and only actually redraws the tree when something changed, so it doesn't reset your expand/cursor state on every tick.
- Applied command/behavior changes are logged in `config/changelog.md`, same as any other code change. 
