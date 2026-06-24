# ChatUI

A fully local, privacy-first knowledge assistant built on top of your Obsidian vault. It combines vector-based semantic search, locally-running LLMs via Ollama, and an optional DuckDuckGo web fallback — all inside a terminal UI. Every function is accessible as a `/command` within the chat.

---

## Usage

```bash
python chatui.py
```

That's it. No flags needed. If the vector database doesn't exist yet, type `/ingest` once you're inside.

---

## Commands

| Command | Description |
|---|---|
| `/help` | List all available commands |
| `/browse` | Open a TUI file browser to load any file as context |
| `/ingest` | Rebuild the vector database from vault markdown files |
| `/organize` | Add YAML frontmatter tags and `[[wikilinks]]` to vault notes |
| `/savefile` | Review and save pending notes to the vault |
| `/clear` | Reset conversation history and unload any open file |
| `/web` | Toggle the DuckDuckGo web search fallback on / off |
| `/update` | Detect config drift and propose code patches via coding model |

**Keyboard shortcuts**

| Key | Action |
|---|---|
| `Ctrl+S` | Shortcut for `/savefile` |
| `Ctrl+B` | Shortcut for `/browse` |
| `Ctrl+Q` | Quit |
| `Esc` | Clear the input field |

---

## Configuration

All settings live in `config/` as markdown files with YAML frontmatter. Each file is self-documenting — open it to see every key, its default, and what it does.

| File | Controls |
|---|---|
| `config/models.md` | Model assignments per role; `models:` list is auto-pulled on launch |
| `config/settings.md` | Thresholds, chunk sizes, history window, vault path |
| `config/commands.md` | Command spec — edit here, run `/update` to get a code patch |

---

## How It Works

### 1. Ingestion (`/ingest`)

Reads every `.md` file in the vault using LangChain's `DirectoryLoader` (skipping `conversations/`, `config/`, and `local_db/`). Each file is split into overlapping chunks by `RecursiveCharacterTextSplitter`, then each chunk is embedded by `nomic-embed-text` into a dense vector and written to a persistent ChromaDB database (`local_db/`).

YAML frontmatter tags are parsed and stored as boolean metadata fields on each chunk (e.g. `tag_ai: true`) so they can be used to filter searches later.

Re-run `/ingest` whenever you add notes manually outside the app.

### 2. Tag-Aware Retrieval

When you ask a question, it is embedded and compared against all stored chunks. The top result's tags (if any) are used to run a second, topic-scoped search. If the scoped search scores within 10% of the baseline, its results replace the unfiltered ones — keeping context focused on the relevant topic as the vault grows. The UI shows which tags were active (`🏷 Scoped to: ai, machinelearning`) and the best match score (`🔍 Best vault match: 0.78`).

### 3. Generation

Answers are drawn from the best available source, tried in order:

| Source | Condition |
|---|---|
| **Vault notes** | Top similarity score ≥ threshold |
| **Model knowledge** | Vault score too low — always shown, even when the model flags uncertainty |
| **Web search** | Model flags uncertainty and `/web` is on — DuckDuckGo result shown alongside |

All prompts include the last `history_window` conversation exchanges so the model can refer to earlier context. Responses stream token-by-token as they are generated.

### 4. Conversation & Session Saving

The app keeps a full in-session history for multi-turn conversations. Every session is also automatically saved to `conversations/YYYY-MM-DD_HH-MM-SS.md` in the vault the moment it starts, with each message appended in real time — so nothing is lost if the app closes unexpectedly.

### 5. File Browser (`/browse`)

Opens a TUI file browser rooted at the vault directory. Navigate with arrow keys, Enter to open a folder or select a file, Esc to go up one level (or close at the root). Selecting any file loads its full content as context — it is injected into every subsequent prompt alongside vault chunks so the model can answer questions about it. The active filename is shown in the header subtitle. `/clear` unloads it.

### 6. Learning (`/savefile`)

When an answer comes from model knowledge or web search it is queued as a `PendingNote` rather than saved immediately. The header subtitle shows the pending count. Type `/savefile` (or `Ctrl+S`) at any time to open the review screen. For each pending note you can:

- Preview the full Q/A content in a scrollable panel
- Accept the model-suggested filename (Enter)
- Type your own filename
- Skip the note entirely

Confirmed notes are written to `.md` files in the vault and added to the live ChromaDB index — immediately searchable without re-ingesting.

### 7. Vault Organisation (`/organize`)

Runs two passes over all vault notes using the coding model (for better instruction-following):

- **Tags pass** — analyses all notes together and suggests shared YAML frontmatter tags to group related notes. You confirm or override each suggestion before anything is written.
- **Wikilinks pass** — for each note identifies phrases that refer to another note and proposes `[[wikilinks]]`. You confirm per note.

### 8. Config-Driven Self-Update (`/update`)

Compares the live config files against the snapshot taken at startup:

- **Setting / model drift** — reports any changed values; restart to apply.
- **Command spec drift** — if `config/commands.md` has new or removed commands, calls the coding model to stream a unified diff that implements the change. Review the proposed patch, then apply manually or via a future `/apply` command.

---

## Architecture

```
config/
├── models.md    — chat_model, coding_model, embed_model
├── settings.md  — vault_path, thresholds, chunk params, history window
└── commands.md  — command spec; /update watches this for additions/removals

chatui.py
│
├── Config
│   ├── _load_config_file()  — parse YAML frontmatter from a config/*.md file
│   ├── _load_all_config()   — merge settings.md + models.md into one dict
│   └── _startup_cfg         — snapshot for drift detection
│
├── Database
│   ├── ingest_vault()       — load, chunk, embed, persist to ChromaDB
│   └── load_existing_db()   — load persisted ChromaDB from disk
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
│   ├── get_concept_suggestion() — coding model suggests a filename stem
│   └── save_to_vault()          — writes .md file + adds doc to live ChromaDB
│
├── Prompts
│   ├── _file_ctx_section()      — shared open-file block injected into prompts
│   ├── build_vault_prompt()     — vault context + open file + history → answer
│   ├── build_knowledge_prompt() — open file + history → model answer
│   ├── build_web_prompt()       — web results + history → answer
│   └── _format_history()        — trims history to last HISTORY_WINDOW exchanges
│
└── TUI
    ├── ChatApp                  — unified chat + command interface
    │   ├── /browse              — pushes FileBrowserScreen, loads file as context
    │   ├── /ingest              — @work coroutine, non-blocking
    │   ├── /organize            — async worker, uses coding_llm
    │   ├── /savefile            — triggers NoteReviewScreen modal
    │   ├── /update              — config drift check + coding model patch proposal
    │   ├── /clear, /web, /help
    │   ├── _stream_llm()        — streams tokens (chat or coding model), writes Markdown when done
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

## Setup

```bash
# Install dependencies
pip install langchain langchain-ollama langchain-community chromadb \
            duckduckgo-search textual pyyaml

# Pull Ollama models (once)
ollama pull nomic-embed-text
ollama pull llama3.2:3b
ollama pull qwen2.5-coder:7b

# Run
python chatui.py
# Then type /ingest to build the database on first launch
```

---

## Suggested Improvements

- **`/apply`** — parse the unified diff produced by `/update` and write it to `chatui.py` with a line-by-line confirmation step, then prompt to restart
- **Re-ingest on change** — watch the vault with `watchdog` and automatically re-embed changed files
- **Smarter chunking** — chunk by markdown heading rather than character count so each chunk stays semantically coherent
- **Note deduplication** — before saving, check if a semantically similar entry already exists and offer to append instead
- **Multi-vault support** — accept `vault_path` as a CLI argument, overriding `config/settings.md`
