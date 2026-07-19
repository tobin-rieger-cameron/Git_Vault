# LLM-sandbox — Claude Code project context

## Repo layout

```
Git_Vault/                    ← git root (branch: llm-sandbox)
└── LLM-sandbox/              ← working directory (git subtree) — also the vault root
    ├── ChatUI/               ← canonical app code
    │   ├── program_files/    ← app package, run as `python -m program_files` from ChatUI/
    │   │   ├── __main__.py   ← entrypoint: builds Settings/Vault/Retriever/ModelClient, runs ChatApp
    │   │   ├── ask.py, draft.py, classify.py, review.py  ← the four verbs, kept at the surface
    │   │   ├── app.py        ← ChatApp(App), thin — delegates to the verb modules
    │   │   ├── utils/        ← domain layer, no Textual dependency: config.py, models.py,
    │   │   │   vault.py, retrieval.py, llm.py, web.py, feedback.py, errors.py, debug_log.py
    │   │   ├── ui/           ← Textual-specific widgets (streaming.py, picker.py)
    │   │   └── tests/        ← unit + integration test suite
    │   ├── config/
    │   │   ├── settings.md      ← runtime config (YAML frontmatter, parsed by utils/config.py) + architecture docs
    │   │   ├── models.md        ← model role assignments + registry (YAML frontmatter, parsed by utils/config.py)
    │   │   ├── Commands.md      ← command spec for the 4-verb surface (documentation only, not parsed)
    │   │   ├── changelog.md     ← full session history; update after every session
    │   │   ├── style_guide.md   ← coding standards distilled from PEP8/Effective Python/Clean Code
    │   │   ├── ui_style_guide.md ← TUI design standards, distilled from 4 UX/design books + clig.dev
    │   │   ├── ideas.md          ← open backlog; done items point to changelog.md instead of recapping
    │   │   ├── vault-structure-plan.md ← Dewey-based folder taxonomy (status: revising)
    │   │   └── Wikipedia Format Guide.md ← house style for vault articles and config docs alike
    │   └── local_db/         ← ChromaDB vector store (gitignored)
    ├── Formal Notes/         ← classified vault articles (Title Case with Spaces filenames)
    └── Study Notes/          ← intake — unclassified until shaped up via ChatUI
```

The repo root is `Git_Vault/` — always commit from there or use absolute paths. Never treat `LLM-sandbox/` as the git root.

The vault root is `LLM-sandbox/` itself (the repo working directory) — every `.md` file under it is vault content unless excluded via `.vaultignore` (currently `conversations`, `config`, `local_db`) or a hidden/`__`-prefixed directory. Pass `--vault <path>` to point at a different root.

## How to run ChatUI

```bash
source .venv/bin/activate
cd ChatUI
python -m program_files
# vault defaults to the repo working directory; then /ingest on first launch
```

Testing pattern: launch in tmux, wait for the input prompt, send `/ingest`, then test queries. Unit tests run with `python -m pytest program_files/tests/ --ignore-glob='*integration*'`; the integration tests need a local Ollama and are skipped when it's unreachable.

## Critical constraints

**ChromaDB API (v1.x):** Use `chromadb.PersistentClient(path=...)`. The old `chromadb.Client(persist_directory=...)` form must never be reintroduced — data silently vanishes on restart if you use it.

**No module-level globals.** `Vault`, `Retriever`, `ModelClient`, `Settings` are constructed once in `program_files/__main__.py` and owned by `ChatApp` (`self.vault`, `self.retriever`, `self.model`, `self.settings`), passed as explicit arguments to verb functions. This is a deliberate style-guide decision (`config/style_guide.md`), not an oversight.

**Files with spaces** — vault files use Title Case with Spaces. When removing untracked files: use `rm -f`, not `git rm` (git rm fails on untracked paths). Always quote paths.

**After `chunk_size`/`chunk_overlap`/`embed_model` changes** — run `/ingest` to rebuild ChromaDB. Current settings: `chunk_size=800`, `chunk_overlap=100`, `top_k=5`, `similarity_threshold=0.65` (see `config/settings.md`).

No self-update pipeline — `/update`/`/apply` and the `CHANGE:`/`FIX:` directive format do not exist in this app. Config and code changes are made by hand-editing the relevant file directly.

## Code style — apply while writing, not in a later pass

`ChatUI/config/style_guide.md` is the full standard (naming, functions, async, data modeling, error handling, comments, docstrings). Write and edit code to it as you go — every new function, comment, and docstring should land already conforming, so no formatting pass is needed afterward. The load-bearing comment/docstring rules, in-context:

- **Docstrings are one line.** Imperative mood for functions/methods (`"""Return …"""`, `"""Route …"""`, never `"""Returns …"""`); a noun phrase for modules and classes. One-liner → closing `"""` on the same line. No multi-paragraph docstrings.
- **Docstring only where it earns it.** Public functions/methods get one. A `_`-private function gets one only for a non-obvious return contract (a multi-value tuple, a sentinel); otherwise the name carries it. A trivial marker class (a bare exception subclass) or a self-describing `@dataclass` DTO is exempt — docstring it only to add a unit, invariant, or allowed-value set the fields don't already state.
- **Comments are for the non-obvious *why*, and are rare.** Never restate what the code does. If a rename or an extracted helper removes the need for the comment, do that instead.
- **Comments and docstrings stand on their own.** No author/book/methodology/design-doc provenance — no `per Norman`, `(CLIG)`, `matching the artifact`, `see ui_style_guide.md`. State the reasoning inline. A short pointer to an authoritative in-repo spec (`per CLAUDE.md's retrieval table`) is the only allowed reference.
- **No commented-out code, no banner/section-divider comments, no changelog-in-a-docstring** — git and `config/changelog.md` own that history.
- **The house style already lives in the domain modules** — match `program_files/ask.py`, `utils/vault.py`, `utils/retrieval.py` (sparse local why-comments, one-line imperative docstrings, bare private helpers).

## Documentation style

Config docs under `ChatUI/config/` follow `config/Wikipedia Format Guide.md` (H1 title, H2 sections each followed by `---`, sentence-case headings, en/em dash discipline). Write docs to state what *is*, not what *used to be* — historical narrative (retired commands, old file paths, past bugs) belongs in `config/changelog.md`, not in the live doc. Don't duplicate a table's content into that file's YAML frontmatter or vice versa.

## End-of-session checklist (do this before stopping, unprompted)

1. **Changelog** — add a row to the current date section in `ChatUI/config/changelog.md` for every meaningful change. Replace any `_(this commit)_` placeholders with real hashes.
2. **README** — check `LLM-sandbox/ChatUI/README.md` (or repo-root `README.md`, whichever documents the running app) is accurate: model names, command list, run instructions. If anything drifted, update it now.
3. **Git status** — run `git status` from the repo root (`Git_Vault/`). If anything is unstaged, stage and commit it — but only what the session actually touched; leave unrelated pre-existing changes for the user to handle separately.
4. **Commit** — include every file the session modified in a final tidy-up commit.

Session-log location (`Knowledge/conversations/claude_transcript.md`) is currently unresolved — the `Knowledge/` vault was folded into `LLM-sandbox/` directly and the old transcript file is sitting under `Study Notes/OLD_STRUCTURE_MOVE_ME/conversations/`, not an active path. Ask where session transcripts should land before assuming this step still applies.

## Retrieval behaviour (current tuning)

| Path | Condition | Prompt instruction |
|------|-----------|--------------------|
| Vault | score ≥ 0.65 | Use context; supplement with training knowledge if needed; attribute it |
| Weak match | score < 0.65 (chunks exist) | Answer from training knowledge first; use vault notes only if directly relevant |
| Model knowledge | no chunks | Own knowledge only |
| Web | model-knowledge path + `/web` on | DuckDuckGo (`ddgs`) supplement |

`history_window=2` — keep small to prevent the 8b model from anchoring on prior Q&A in unrelated follow-ups.

## Common pitfalls from past sessions

- Obsidian sync creates `File 1.md` duplicates — safe to delete; they're untracked
- `tmux capture-pane` output includes stale scroll buffer; grep carefully or scroll with `-S`
- `find ... | xargs basename` breaks on space-containing filenames — use `find -maxdepth 1 -name "*.md"` and iterate directly
- `git rm` with spaces needs quoting AND the file must be tracked; use `rm -f` for untracked
- `/ingest` output "N chunks — N unchanged" is the success signal; a model pull (4.9 GB for 8b) can take 10+ min on first run
