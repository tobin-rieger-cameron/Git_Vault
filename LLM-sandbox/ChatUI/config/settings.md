---
summary: >
  Tuneable runtime parameters for the chatui/ package. All keys are read at
  startup by chatui.config.load_settings() into a Settings dataclass and passed
  to Vault/Retriever/ModelClient/ChatApp — there is no self-update pipeline;
  changing a value here just takes effect on next launch. Also contains full
  technical documentation (How It Works, Architecture, Stack) so an LLM reading
  this file has complete context before proposing changes.
similarity_threshold: 0.65
top_k: 5
chunk_size: 800
chunk_overlap: 100
history_window: 2
web_search_results: 3
review_staleness_days: 30
---

# Settings

| Key | Default | Description |
|---|---|---|
| `vault_path` | _(repo working directory, i.e. `ChatUI/..`)_ | Absolute path to the vault root; overrides the computed default. Also overridable per-run via `--vault` |
| `similarity_threshold` | `0.65` | Minimum score to answer from the vault; below this falls back to the weak-match/model-knowledge path |
| `top_k` | `5` | Vault chunks retrieved per query |
| `chunk_size` | `800` | Characters per chunk during ingestion |
| `chunk_overlap` | `100` | Overlap between adjacent chunks |
| `history_window` | `2` | Conversation exchanges kept in prompt context |
| `web_search_results` | `3` | Web results fetched per query (via `ddgs`) |
| `review_staleness_days` | `30` | Days after a note's last review before `/review` (with no file selected) lists it as due again; never-reviewed notes are always due |

## Notes

- All changes take effect on next launch — there is no self-update pipeline; edit this file directly.
- After changing `chunk_size` or `chunk_overlap`, run `/ingest` to rebuild the database.

---

## How It Works

ChatUI is organized around a tool registry and an agent loop, not a fixed set of pipelines — every capability (vault search, web search, drafting, classifying, reviewing) is a `ToolSpec` (name/description/parameters/handler) in `utils/tools/`, built once by `build_registry()` and owned by `ChatApp` as `self.tools`. `app.py`'s `ChatApp` just dispatches slash commands to the registry; no business logic lives on the App class. See `LLM-sandbox/CLAUDE.md`'s "Architecture: tools, not verbs" section for the model-facing/command-facing split, and `LLM-sandbox/conversations/2026-07-20_agent-tools-rebuild.md` for the design rationale (this replaced an earlier structure of four separate `ask.py`/`draft.py`/`classify.py`/`review.py` pipeline modules).

### 1. Ingestion (`/ingest` → `Retriever.ingest()`)

Reads every `.md` file in the vault via `Vault.list_files()`, skipping hidden/`__`-prefixed directories and anything matching a pattern in the vault root's `.vaultignore` (currently `conversations/`, `config/`, `local_db/` — edit that file, not code, when the tree reshapes). Each file is split into overlapping chunks by `chunk_file()` (`chunk_size`/`chunk_overlap`), then embedded and written to a persistent ChromaDB database (`local_db/`) via `chromadb.PersistentClient` — the old `chromadb.Client(persist_directory=...)` form is gone and must never be reintroduced (CLAUDE.md hard constraint).

YAML frontmatter tags are parsed and stamped onto each chunk's metadata so they can be used to filter searches later.

### 2. Ask — retrieval path selection, then an agentic loop

`ask_tools.choose_retrieval_path()` picks one of three `RetrievalPath` values based on the top chunk score, which shapes the initial prompt; the model then runs through `utils.agent.run()`, free to call `search_vault`/`read_vault_file` (and `web_search`, when `/web` is on) as many times as it needs before answering:

| Path | Condition | Behavior |
|---|---|---|
| `VAULT` | top score ≥ `similarity_threshold` | Answer from vault chunks; tag-rescope to a second, topic-scoped search; tools available for more detail |
| `WEAK_MATCH` | chunks exist but below `similarity_threshold` | Answer primarily from the model's own training knowledge; use vault notes only if directly relevant; tools available to try a different search |
| `MODEL_KNOWLEDGE` | no chunks retrieved at all | Own knowledge, but nudged to double-check with `search_vault` first |

All prompts include the last `history_window` exchanges. `ModelClient.stream_with_tools()` drives the tool-calling loop (max 4 rounds before a forced final answer).

### 3. Draft a paper (`/draft <subject>`)

`draft_tools.edit_draft()` creates a new `File` (or loads an existing one matching the subject), then `draft_tools.revise_draft()` runs a back-and-forth authoring loop until the user ends the session. `draft_tools.save_draft()` writes it via `Vault.save_file()`. Papers are long-form and living — the user returns to expand/restructure them over time, not a one-shot generation.

### 4. Classify inline (`/classify`, `/tags`, `/folder`, `/wikilinks`)

Immediately after a draft is saved, `classify_tools.suggest_classification()` proposes a folder/tags for that file (single suggestion, not a batch), shown for accept/edit before anything is applied; `classify_tools.suggest_wikilinks()` does the same for inline/see-also links. No retrieval loop here — the file is already in hand.

### 5. Review (`/review [subject]`)

`review_tools.generate_review_questions()` produces a small number of plain free-text Q + answer-hint pairs for a file. `review_tools.mark_reviewed()` stamps `last_reviewed`; `review_tools.files_due_for_review()` surfaces anything stale. Lightweight — not a full spaced-repetition engine.

### 6. Web Search (`/web`)

Toggles whether the `web_search` tool (via `ddgs`, no API key required) is offered to the model at all — the model itself decides when to call it.

---

## Architecture

```
ChatUI/                     ← run `python -m program_files` from here (vault defaults to repo root, or pass --vault)
├── program_files/
│   ├── __main__.py     — entrypoint: builds Settings/Vault/Retriever/ModelClient, runs ChatApp
│   ├── app.py           — ChatApp(App), thin, dispatches via the tool registry
│   ├── ui/
│   │   ├── streaming.py — live token/line streaming widget
│   │   └── picker.py    — Tree-based file picker widget
│   └── utils/
│       ├── tools/
│       │   ├── __init__.py       — ToolSpec, ToolRegistry, build_registry()
│       │   ├── vault_tools.py    — search_vault, read_vault_file (model-facing)
│       │   ├── web_tools.py      — web_search (model-facing)
│       │   ├── ask_tools.py      — answer_question + retrieval-path logic
│       │   ├── draft_tools.py    — draft_note, edit_draft/revise_draft/save_draft
│       │   ├── classify_tools.py — classify_note, suggest_wikilinks, apply_*
│       │   └── review_tools.py   — review_note, mark_reviewed, files_due_for_review
│       ├── agent.py    — run() — the retrieve/act/observe tool-calling loop
│       ├── config.py       — Settings dataclass + load_settings()
│       ├── models.py       — File, Chunk, AskResult, RetrievalPath, ClassificationSuggestion, ReviewQuestion, Override, IngestStats
│       ├── vault.py        — Vault class + parse_frontmatter/render_frontmatter/extract_wikilinks/normalize_link_target
│       ├── retrieval.py    — Retriever class + chunk_file()
│       ├── llm.py          — ModelClient class (chat + coding models, streaming, stream_with_tools)
│       ├── web.py          — search_web() + WebResult
│       ├── feedback.py     — log_override()/load_recent_overrides()
│       └── errors.py       — ChatUIError hierarchy
├── config/
│   ├── models.md    — model registry + auto-pull list
│   ├── settings.md  — runtime params + full technical reference (this file)
│   └── Commands.md  — command spec for the 4-command surface
└── local_db/        — ChromaDB vector store (gitignored)

Formal Notes/        ← classified vault articles
Study Notes/         ← intake — unclassified until shaped up via ChatUI
└── *.md             (vault_path default is the repo root containing both)
```

No module-level globals — `Vault`, `Retriever`, `ModelClient`, `Settings` are constructed once in `__main__.py` and owned by `ChatApp` (`self.vault`, `self.retriever`, `self.model`, `self.settings`, `self.tools`), passed as explicit arguments/closures rather than accessed globally.

There is no self-update pipeline (`/update`/`/apply`, the `CHANGE:`/`FIX:` directive format, and `apply_update.py` were all retired, not reimplemented) — config changes go back to plain hand-editing.

---

## Stack

| Layer | Tool |
|---|---|
| Chat model | see `models.md` `chat_model` |
| Coding model | see `models.md` `coding_model` — used by `classify_tools.py`'s structured suggestions |
| Embedding model | see `models.md` `embed_model` |
| Vector database | ChromaDB (persistent, local) via `chromadb.PersistentClient` |
| Terminal UI | Textual + Rich |
| Web search | `ddgs` |
