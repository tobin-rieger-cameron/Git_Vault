# LLM-sandbox — Claude Code project context

## Repo layout

```
Git_Vault/                    ← git root (branch: llm-sandbox)
└── LLM-sandbox/              ← working directory (git subtree)
    ├── ChatUI/               ← canonical app code
    │   ├── chatui/           ← app package (rebuild in progress — see config/style_guide.md)
    │   │   ├── __main__.py   ← entrypoint: `python -m chatui --vault ../Knowledge`
    │   │   ├── config.py, models.py, vault.py, retrieval.py, llm.py, web.py,
    │   │   │   feedback.py, errors.py — domain layer, no Textual dependency
    │   │   ├── ask.py, draft.py, classify.py, review.py  ← the four verbs
    │   │   ├── app.py        ← ChatApp(App), thin — delegates to the verb modules
    │   │   └── ui/           ← Textual-specific widgets (streaming.py, picker.py)
    │   ├── config/
    │   │   ├── settings.md      ← runtime config (YAML frontmatter) + architecture docs
    │   │   ├── models.md        ← model registry + auto-pull list
    │   │   ├── changelog.md     ← full session history; update after every session
    │   │   ├── commands.md      ← command spec (pending rewrite for the 4-verb surface)
    │   │   └── style_guide.md   ← coding standards distilled from PEP8/Effective Python/Clean Code
    │   └── local_db/         ← ChromaDB vector store (gitignored; wiped and reingested for the rebuild)
    └── Knowledge/            ← vault articles (canonical location)
        ├── conversations/
        │   ├── claude_transcript.md  ← this project's Claude Code session log
        │   └── YYYY-MM-DD.md         ← daily ChatUI session files
        └── *.md              ← Title Case with Spaces filenames
```

The repo root is `Git_Vault/` — always commit from there or use absolute paths. Never treat `LLM-sandbox/` as the git root.

`chatui.py`/`apply_update.py` (the old single-file app) were deliberately wiped (commit `1fb5c9b`) and are being rebuilt as the `chatui/` package above, organized around four verbs — Ask, Draft a paper, Classify inline, Review (see memory `project_chatui_redefinition` / `ChatUI/config/style_guide.md`). The domain modules, the four verbs, `app.py`, and the `ui/` widgets are all implemented, with a passing unit + integration test suite under `ChatUI/tests/`.

`conversations/` moved from `ChatUI/` to `Knowledge/` in commit `eb9a0f5` — always use the `Knowledge/conversations/` path, not `ChatUI/conversations/`.

## How to run ChatUI

```bash
cd ChatUI
source .chat_venv/bin/activate
python -m chatui --vault ../Knowledge
```

Testing pattern: launch in tmux, wait for the input prompt, send `/ingest`, then test queries. Unit tests run with `python -m pytest tests/ --ignore-glob='*integration*'`; the integration tests need a local Ollama and are skipped when it's unreachable.

## Critical constraints

**ChromaDB API (v1.x):** Use `chromadb.PersistentClient(path=...)`. The old `chromadb.Client(persist_directory=...)` is gone — data silently vanishes on restart if you use it.

**No module-level globals in the rebuild.** The old `llm`/`coding_llm`/`VAULT_PATH`/`CONVERSATIONS_DIR` globals are gone. Their replacements — a `Vault`, a `ModelClient`, a `Settings` — are constructed once in `chatui/__main__.py` and owned by `ChatApp` (`self.vault`, `self.model`, `self.settings`); pass them as explicit arguments to verb functions rather than reaching for global state. This is a deliberate style-guide decision (`config/style_guide.md`), not an oversight — don't reintroduce globals to match the old shape.

**Hardcoded filename** — `_article-guide.md` (`ChatUI/_article-guide.md`) is referenced by name by the article-formatting guidance the old `/distill`/classification logic used. Do not rename it even if renaming other vault files; whatever replaces that logic in `chatui/classify.py`/`draft.py` should keep referencing this same file.

**Files with spaces** — Knowledge/ files use Title Case with Spaces. When removing untracked files: use `rm -f`, not `git rm` (git rm fails on untracked paths). Always quote paths.

**After chunk_size changes** — run `/ingest` to rebuild ChromaDB. Current settings: chunk_size=800, overlap=100, top_k=5, threshold=0.65.

No self-update pipeline in the rebuild — `/update`/`/apply` and the `CHANGE:`/`FIX:` directive format were deliberately dropped (didn't map to any of the four verbs). Config changes go back to plain hand-editing.

## Code style — apply while writing, not in a later pass

`ChatUI/config/style_guide.md` is the full standard (naming, functions, async, data modeling, error handling, comments, docstrings). Write and edit code to it as you go — every new function, comment, and docstring should land already conforming, so no formatting pass is needed afterward. The load-bearing comment/docstring rules, in-context:

- **Docstrings are one line.** Imperative mood for functions/methods (`"""Return …"""`, `"""Route …"""`, never `"""Returns …"""`); a noun phrase for modules and classes. One-liner → closing `"""` on the same line. No multi-paragraph docstrings.
- **Docstring only where it earns it.** Public functions/methods get one. A `_`-private function gets one only for a non-obvious return contract (a multi-value tuple, a sentinel); otherwise the name carries it. A trivial marker class (a bare exception subclass) or a self-describing `@dataclass` DTO is exempt — docstring it only to add a unit, invariant, or allowed-value set the fields don't already state.
- **Comments are for the non-obvious *why*, and are rare.** Never restate what the code does. If a rename or an extracted helper removes the need for the comment, do that instead.
- **Comments and docstrings stand on their own.** No author/book/methodology/design-doc provenance — no `per Norman`, `(CLIG)`, `matching the artifact`, `see ui_style_guide.md`. State the reasoning inline. A short pointer to an authoritative in-repo spec (`per CLAUDE.md's retrieval table`) is the only allowed reference.
- **No commented-out code, no banner/section-divider comments, no changelog-in-a-docstring** — git and `config/changelog.md` own that history.
- **The house style already lives in the domain modules** — match `chatui/ask.py`, `vault.py`, `retrieval.py` (sparse local why-comments, one-line imperative docstrings, bare private helpers), not the pre-cleanup shape `app.py` had.

## End-of-session checklist (do this before stopping, unprompted)

1. **Transcript** — append a new session block to `Knowledge/conversations/claude_transcript.md`. Match the existing format: session number, date, focus line, commits, and the full Q&A exchange.
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
