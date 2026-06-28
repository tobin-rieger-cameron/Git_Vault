---
summary: >
  Tuneable runtime parameters for chatui.py. All keys are read at startup via
  _load_all_config() and override the hardcoded defaults in the source. Changing
  a value here and running /update will produce "no code changes required" — just
  restart to apply. Also contains full technical documentation (How It Works,
  Architecture, Stack) so an LLM reading this file has complete context before
  proposing changes.
similarity_threshold: 0.65
top_k: 5
chunk_size: 800
chunk_overlap: 100
history_window: 2
web_search_results: 3
---

# Changes

## Directive format

Add directives anywhere in the body of any `config/*.md` file (not in frontmatter).
`/update` picks them up via `git diff` against `.chatui_sync` and applies each one as a
targeted surgical edit — handler entry, help line, and method body are handled separately,
then the result is validated with `ast.parse` + `py_compile` before being shown to you.

| Prefix | Effect |
|---|---|
| `CHANGE: add /X …` | Add new command X (handler entry + _cmd_X method + help line) |
| `REMOVE: /X command` | Remove command X and its method |
| `RENAME: /X → /Y` | Rename command X to Y everywhere |
| `FIX: description` | Model-guided targeted fix (extracts relevant method, splices result) |

After `/apply` writes the file, `.chatui_sync` advances to the current `HEAD` so each
directive is only processed once.

---

# Settings

| Key | Default | Description |
|---|---|---|
| `vault_path` | _(ChatUI/../Knowledge)_ | Absolute path to the vault root; overrides the computed default |
| `similarity_threshold` | `0.5` | Minimum score to answer from vault; below this falls back to model knowledge |
| `top_k` | `3` | Vault chunks retrieved per query |
| `chunk_size` | `500` | Characters per chunk during ingestion |
| `chunk_overlap` | `50` | Overlap between adjacent chunks |
| `history_window` | `4` | Conversation exchanges kept in prompt context |
| `web_search_results` | `3` | DuckDuckGo results fetched per web query |

## Notes

- All changes take effect on next launch.
- After changing `chunk_size` or `chunk_overlap`, run `/ingest` to rebuild the database.

---

## How It Works

### 1. Ingestion (`/ingest`)

Reads every `.md` file in the vault using LangChain's `DirectoryLoader` (skipping `conversations/`, `config/`, and `local_db/`). Each file is split into overlapping chunks by `RecursiveCharacterTextSplitter`, then each chunk is embedded by `nomic-embed-text` into a dense vector and written to a persistent ChromaDB database (`local_db/`).

YAML frontmatter tags are parsed and stored as boolean metadata fields on each chunk (e.g. `tag_ai: true`) so they can be used to filter searches later.

### 2. Tag-Aware Retrieval

When a question is asked, it is embedded and compared against all stored chunks. The top result's tags (if any) are used to run a second, topic-scoped search. If the scoped search scores within 10% of the baseline, its results replace the unfiltered ones. The UI shows which tags were active (`🏷 Scoped to: ai, machinelearning`) and the best match score (`🔍 Best vault match: 0.78`).

### 3. Generation

Answers are drawn from the best available source, tried in order:

| Source | Condition |
|---|---|
| **Vault notes** | Top similarity score ≥ `similarity_threshold` |
| **Model knowledge** | Vault score too low — always shown, even when the model flags uncertainty |
| **Web search** | Model flags uncertainty and `/web` is on — DuckDuckGo result shown alongside |

All prompts include the last `history_window` exchanges. Responses stream token-by-token via `llm.astream()` into a `Static` widget, then finalize as Markdown in the `RichLog`.

### 4. Conversation & Session Saving

Every session is saved to `conversations/YYYY-MM-DD_HH-MM-SS.md` in the vault the moment it starts, with each message appended in real time.

### 5. File Browser (`/browse`)

TUI file browser rooted at the vault directory. Selecting a file loads its full content as context, injected into every subsequent prompt alongside vault chunks. `/clear` unloads it.



### 6. Learning (`/savefile`)

Answers from model knowledge or web search are queued as `PendingNote` objects. `/savefile` opens a review screen where each note can be previewed, renamed, or skipped. Confirmed notes are written to `.md` files and added to the live ChromaDB index immediately.

### 7. Vault Organisation (`/organize`)

Two-pass worker using `coding_llm`:

- **Tags pass** — suggests shared YAML frontmatter tags across all notes; user confirms per note.
- **Wikilinks pass** — suggests `[[wikilinks]]` for phrases that refer to other notes; user confirms per note.

### 8. Config-Driven Self-Update (`/update` + `/apply`)

Write `CHANGE:` or `FIX:` directives anywhere in any `config/*.md` file body. `/update` picks them up via `git diff` against `.chatui_sync` (the last-applied commit hash stored in the project root). Each directive is classified and applied as a targeted surgical edit:

- `CHANGE: add /X …` — inserts handler entry, help line, and generates a `_cmd_X` method body via `qwen2.5-coder:7b`
- `FIX: description` — extracts the relevant function block by name, sends it + the instruction to the model, applies the result, then runs a **self-review pass** (second LLM call checks for dropped decorators, wrong variable names, regex mistakes)

The result is validated with `ast.parse` + `py_compile` before being shown as a diff. `/apply` writes atomically via `os.replace` and advances `.chatui_sync` to `HEAD` so each directive is only applied once.

`apply_update.py` is a headless version of the same pipeline (no TUI required) — useful for bulk directive runs from Claude Code.

Applied directives are logged in `config/changelog.md`.

---

## Architecture

```
ChatUI/                  ← run chatui.py from here
├── chatui.py
├── apply_update.py
├── config/
│   ├── models.md    — model roles, auto-pull registry
│   ├── settings.md  — runtime params + full technical reference (this file)
│   └── commands.md  — command spec; /update watches for additions/removals
├── conversations/   — session logs, INDEX.md
└── local_db/        — ChromaDB vector store

Knowledge/             ← vault articles (VAULT_PATH default)
└── *.md

chatui.py
│
├── Config
│   ├── _load_config_file()  — parse YAML frontmatter from a config/*.md file
│   ├── _load_all_config()   — merge settings.md + models.md into one dict
│   └── _ensure_models()     — pull any model in models: list not yet installed
│
├── Database
│   ├── ingest_vault()       — load, chunk, embed, persist via chromadb.PersistentClient
│   ├── load_existing_db()   — open existing PersistentClient DB from disk
│   └── _reingest_file()     — incremental re-embed of a single changed file (used by watchdog)
│
├── Tag Helpers
│   ├── _extract_frontmatter_tags()
│   ├── _tags_to_metadata()  — store tags as ChromaDB boolean fields
│   ├── _get_chunk_tags()    — read tags back from a retrieved chunk
│   └── _make_tag_filter()   — build ChromaDB where-clause for tag filtering
│
├── Web Search
│   └── web_search()         — DuckDuckGo via DDGS, no API key required
│
├── Learning
│   ├── PendingNote              — dataclass: question, answer, source, suggestion
│   ├── get_concept_suggestion() — coding_llm suggests a filename stem
│   └── save_to_vault()          — writes .md file + adds doc to live ChromaDB
│
├── Prompts
│   ├── _file_ctx_section()      — shared open-file block injected into prompts
│   ├── build_vault_prompt()     — vault context + open file + history → answer
│   ├── build_knowledge_prompt() — open file + history → model answer
│   ├── build_web_prompt()       — web results + history → answer
│   └── _format_history()        — trims history to last history_window exchanges
│
└── TUI
    ├── ChatApp                  — unified chat + command interface
    │   ├── /browse              — pushes FileBrowserScreen, loads file as context
    │   ├── /ingest              — @work coroutine, non-blocking
    │   ├── /organize            — async worker, uses coding_llm
    │   ├── /savefile            — triggers NoteReviewScreen modal
    │   ├── /update              — collect git diff of config/, apply CHANGE:/FIX: directives
    │   ├── /apply               — write validated patch atomically, advance .chatui_sync
    │   ├── /readme, /harvest, /distill, /edit, /daily, /export, /stats
    │   ├── /clear, /web, /help, /version, /status
    │   ├── _stream_llm()        — streams tokens (llm or coding_llm), writes Markdown when done
    │   └── _process()           — RAG pipeline with tag-aware second pass + open file injection
    ├── FileBrowserScreen        — modal: navigate vault files, select to load as context
    └── NoteReviewScreen         — modal: preview + rename + save pending notes
```

---

## Stack

| Layer | Tool |
|---|---|
| Chat model | `llama3.2:3b` via Ollama — fast streaming responses |
| Coding model | `qwen2.5-coder:7b` via Ollama — `/organize`, `/update`, concept suggestions |
| Embedding model | `nomic-embed-text` via Ollama |
| Vector database | ChromaDB (persistent, local) |
| LLM framework | LangChain (`langchain-ollama`, `langchain-community`) |
| Web search | DuckDuckGo Search (`duckduckgo-search`) |
| Terminal UI | Textual + Rich |

---

## Pending Directives

_(none)_
