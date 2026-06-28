# LLM-sandbox — Claude Code project context

## Repo layout

```
Git_Vault/                    ← git root (branch: llm-sandbox)
└── LLM-sandbox/              ← working directory (git subtree)
    ├── ChatUI/               ← canonical app code
    │   ├── chatui.py         ← main app (~2850 lines)
    │   ├── apply_update.py   ← headless self-update pipeline
    │   ├── config/
    │   │   ├── settings.md   ← runtime config (YAML frontmatter) + architecture docs
    │   │   ├── models.md     ← model registry + auto-pull list
    │   │   ├── changelog.md  ← full session history; update after every session
    │   │   └── commands.md   ← command spec watched by /update
    │   ├── conversations/
    │   │   ├── claude_transcript.md  ← this project's Claude Code session log
    │   │   └── YYYY-MM-DD.md         ← daily ChatUI session files
    │   └── local_db/         ← ChromaDB vector store (gitignored)
    └── Knowledge/            ← vault articles (canonical location)
        └── *.md              ← Title Case with Spaces filenames
```

The repo root is `Git_Vault/` — always commit from there or use absolute paths. Never treat `LLM-sandbox/` as the git root.

## How to run ChatUI

```bash
cd ChatUI
source ../.venv/bin/activate
python chatui.py --vault ../Knowledge
```

If blocked by stale PID: `rm -f ChatUI/.chatui.pid`

Testing pattern: launch in tmux, wait for "Ask anything", send `/ingest`, then test queries.

## Critical constraints

**ChromaDB API (v1.x):** Use `chromadb.PersistentClient(path=...)`. The old `chromadb.Client(persist_directory=...)` is gone — data silently vanishes on restart if you use it.

**Module-level globals** — these are intentional and must stay module-level (never `self.xxx`):
- `llm` — ChatOllama instance for chat; reassigned by `/model` at runtime via `global llm`
- `coding_llm` — ChatOllama for /organize, /update, /apply
- `VAULT_PATH`, `CONVERSATIONS_DIR` — paths set once at startup

**Hardcoded filename** — `_article-guide.md` is referenced at line 1632 as a literal string. Do not rename it even if renaming other vault files.

**Files with spaces** — Knowledge/ files use Title Case with Spaces. When removing untracked files: use `rm -f`, not `git rm` (git rm fails on untracked paths). Always quote paths.

**After chunk_size changes** — run `/ingest` to rebuild ChromaDB. Current settings: chunk_size=800, overlap=100, top_k=5, threshold=0.65.

## Self-update pipeline

Write `CHANGE:` or `FIX:` directives anywhere in a `config/*.md` body. `/update` in ChatUI (or `apply_update.py` headlessly) picks them up via `git diff HEAD -- config/` against `.chatui_sync`, applies each as a surgical AST edit, self-reviews, then shows a diff before writing.

No pending directives in `settings.md` as of Session 15.

## End-of-session checklist (do this before stopping, unprompted)

1. **Transcript** — append a new session block to `ChatUI/conversations/claude_transcript.md`. Match the existing format: session number, date, focus line, commits, and the full Q&A exchange.
2. **Changelog** — add a row to the current date section in `ChatUI/config/changelog.md` for every meaningful change. Replace any `_(this commit)_` placeholders with real hashes.
3. **README** — check `LLM-sandbox/README.md` is accurate: model names, command list, run instructions. If anything drifted, update it now.
4. **Git status** — run `git status` from the repo root (`Git_Vault/`). If ChatUI/ or Knowledge/ has unstaged changes, stage and commit them.
5. **Commit** — if any of the above files were modified, include them in a final tidy-up commit.

Do all five steps at the end of every session without being asked.

## Retrieval behaviour (current tuning)

| Path | Condition | Prompt instruction |
|------|-----------|--------------------|
| Vault | score ≥ 0.65 | Use context; supplement with training knowledge if needed; attribute it |
| Grounded | score < 0.65 (chunks exist) | Answer from training knowledge first; use vault notes only if directly relevant |
| Model knowledge | no chunks | Own knowledge only |
| Web | model-knowledge path + /web on | DuckDuckGo supplement |

history_window=2 — keep small to prevent 8b model from anchoring on prior Q&A in unrelated follow-ups.

## Common pitfalls from past sessions

- Obsidian sync creates `File 1.md` duplicates — safe to delete; they're untracked
- `tmux capture-pane` output includes stale scroll buffer; grep carefully or scroll with `-S`
- `find ... | xargs basename` breaks on space-containing filenames — use `find -maxdepth 1 -name "*.md"` and iterate directly
- `git rm` with spaces needs quoting AND the file must be tracked; use `rm -f` for untracked
- `/ingest` output "309 chunks — N unchanged" is the success signal; a model pull (4.9 GB for 8b) can take 10+ min on first run
