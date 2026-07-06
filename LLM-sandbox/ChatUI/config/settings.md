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
---

# Settings

| Key | Default | Description |
|---|---|---|
| `vault_path` | _(ChatUI/../Knowledge)_ | Absolute path to the vault root; overrides the computed default |
| `similarity_threshold` | `0.65` | Minimum score to answer from the vault; below this falls back to the weak-match/model-knowledge path |
| `top_k` | `5` | Vault chunks retrieved per query |
| `chunk_size` | `800` | Characters per chunk during ingestion |
| `chunk_overlap` | `100` | Overlap between adjacent chunks |
| `history_window` | `2` | Conversation exchanges kept in prompt context |
| `web_search_results` | `3` | Web results fetched per query (via `ddgs`) |

## Notes

- All changes take effect on next launch — there is no self-update pipeline; edit this file directly.
- After changing `chunk_size` or `chunk_overlap`, run `/ingest` to rebuild the database.

---

## How It Works

ChatUI is organized around four verbs — Ask, Draft a paper, Classify inline, Review (see `Knowledge/conversations/claude_transcript.md` / memory `project_chatui_redefinition` for the full rationale). Every verb is a plain async function in its own module (`ask.py`, `draft.py`, `classify.py`, `review.py`) operating on `Vault`/`Retriever`/`ModelClient`/`File` — `app.py`'s `ChatApp` just wires user input to these functions; no business logic lives on the App class.

### 1. Ingestion (`/ingest` → `Retriever.ingest()`)

Reads every `.md` file in the vault via `Vault.list_files()` (skipping `conversations/`, `config/`, and `local_db/`). Each file is split into overlapping chunks by `chunk_file()` (`chunk_size`/`chunk_overlap`), then embedded and written to a persistent ChromaDB database (`local_db/`) via `chromadb.PersistentClient` — the old `chromadb.Client(persist_directory=...)` form is gone and must never be reintroduced (CLAUDE.md hard constraint).

YAML frontmatter tags are parsed and stamped onto each chunk's metadata so they can be used to filter searches later.

### 2. Ask — retrieval path selection

`ask.choose_retrieval_path()` picks one of three `RetrievalPath` values based on the top chunk score:

| Path | Condition | Behavior |
|---|---|---|
| `VAULT` | top score ≥ `similarity_threshold` | Answer from vault chunks; tag-rescope to a second, topic-scoped search; supplement with web search only if the topic isn't covered by the sources |
| `WEAK_MATCH` | chunks exist but below `similarity_threshold` | Answer primarily from the model's own training knowledge; use vault notes only if directly relevant |
| `MODEL_KNOWLEDGE` | no chunks retrieved at all | Own knowledge only, with an unconditional web supplement if `/web` is on |

All prompts include the last `history_window` exchanges. Responses stream token-by-token via `ModelClient.stream()`.

### 3. Draft a paper (`/draft <subject>`)

`draft.start_draft()` creates a new `File` (or loads an existing one matching the subject), then `draft.revise_draft()` runs a back-and-forth authoring loop until the user ends the session. `draft.save_draft()` writes it via `Vault.save_file()`. Papers are long-form and living — the user returns to expand/restructure them over time, not a one-shot generation.

### 4. Classify inline (`/classify`)

Immediately after a draft is saved, `classify.suggest_classification()` proposes a folder/tags/wikilinks for that file (single suggestion, not a batch), shown for accept/edit before anything is applied. This directly replaces the old `/organize`'s vault-wide batch-review model — classification happens inline, in the same session a paper is drafted or substantially revised.

### 5. Review (`/review [subject]`)

`review.generate_review_questions()` produces a small number of plain free-text Q + answer-hint pairs for a file. `review.mark_reviewed()` stamps `last_reviewed`; `review.files_due_for_review()` surfaces anything stale. Lightweight — not a full spaced-repetition engine.

### 6. Web Search (`/web`)

Toggles a web supplement (via `ddgs`, no API key required) on/off for the Ask path.

---

## Architecture

```
ChatUI/                     ← run `python -m chatui --vault ../Knowledge` from here
├── chatui/
│   ├── __main__.py     — entrypoint: builds Settings/Vault/Retriever/ModelClient, runs ChatApp
│   ├── config.py       — Settings dataclass + load_settings()
│   ├── models.py       — File, Chunk, AskResult, RetrievalPath, ClassificationSuggestion, ReviewQuestion, Override, IngestStats
│   ├── vault.py        — Vault class + parse_frontmatter/render_frontmatter/extract_wikilinks/normalize_link_target
│   ├── retrieval.py    — Retriever class + chunk_file()
│   ├── llm.py          — ModelClient class (chat + coding models, streaming)
│   ├── web.py          — search_web() + WebResult
│   ├── feedback.py     — log_override()/load_recent_overrides()
│   ├── errors.py       — ChatUIError hierarchy
│   ├── ask.py          — verb 1
│   ├── draft.py        — verb 2
│   ├── classify.py     — verb 3
│   ├── review.py        — verb 4
│   ├── app.py           — ChatApp(App), thin, delegates to the verb modules
│   └── ui/
│       ├── streaming.py — live token/line streaming widget
│       └── picker.py    — Tree-based file picker widget
├── config/
│   ├── models.md    — model registry + auto-pull list
│   ├── settings.md  — runtime params + full technical reference (this file)
│   └── commands.md  — command spec for the 4-verb surface
└── local_db/        — ChromaDB vector store (gitignored)

Knowledge/           ← vault articles (vault_path default)
└── *.md
```

No module-level globals — `Vault`, `Retriever`, `ModelClient`, `Settings` are constructed once in `__main__.py` and owned by `ChatApp` (`self.vault`, `self.retriever`, `self.model`, `self.settings`), passed as explicit arguments to verb functions.

There is no self-update pipeline (`/update`/`/apply`, the `CHANGE:`/`FIX:` directive format, and `apply_update.py` were all retired, not reimplemented) — config changes go back to plain hand-editing.

---

## Stack

| Layer | Tool |
|---|---|
| Chat model | see `models.md` `chat_model` |
| Coding model | see `models.md` `coding_model` — used by `classify.py`'s structured suggestions |
| Embedding model | see `models.md` `embed_model` |
| Vector database | ChromaDB (persistent, local) via `chromadb.PersistentClient` |
| Terminal UI | Textual + Rich |
| Web search | `ddgs` |
