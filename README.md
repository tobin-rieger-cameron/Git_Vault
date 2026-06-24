# ChatUI

A fully local, privacy-first knowledge assistant built on top of your Obsidian vault. It combines vector-based semantic search, a locally-running LLM via Ollama, and an optional DuckDuckGo web fallback — all inside a terminal UI. Every function is accessible as a `/command` within the chat.

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
| `/ingest` | Rebuild the vector database from vault markdown files |
| `/organize` | Add YAML frontmatter tags and `[[wikilinks]]` to vault notes |
| `/savefile` | Review and save pending notes to the vault |
| `/clear` | Reset conversation history |
| `/web` | Toggle the DuckDuckGo web search fallback on / off |

**Keyboard shortcuts**

| Key | Action |
|---|---|
| `Ctrl+S` | Shortcut for `/savefile` |
| `Ctrl+Q` | Quit |
| `Esc` | Clear the input field |

---

## How It Works

### 1. Ingestion (`/ingest`)

Reads every `.md` file in the vault using LangChain's `DirectoryLoader`. Each file is split into 500-character overlapping chunks by `RecursiveCharacterTextSplitter`, then each chunk is embedded by `nomic-embed-text` (running locally via Ollama) into a dense vector and written to a persistent ChromaDB database (`local_db/`).

YAML frontmatter tags are parsed and stored as boolean metadata fields on each chunk (e.g. `tag_ai: true`) so they can be used to filter searches later.

Re-run `/ingest` whenever you add notes manually outside the app.

### 2. Tag-Aware Retrieval

When you ask a question, it is embedded and compared against all stored chunks. The top result's tags (if any) are used to run a second, topic-scoped search. If the scoped search scores within 10% of the baseline, its results replace the unfiltered ones — keeping context focused on the relevant topic as the vault grows. The UI shows which tags were active (`🏷 Scoped to: ai, machinelearning`) and the best match score (`🔍 Best vault match: 0.78`).

### 3. Generation

Answers are drawn from the best available source, tried in order:

| Source | Condition |
|---|---|
| **Vault notes** | Top similarity score ≥ 0.5 |
| **Model knowledge** | Vault score too low — always shown, even when the model flags uncertainty |
| **Web search** | Model flags uncertainty and `/web` is on — DuckDuckGo result shown alongside |

All prompts include the last 4 conversation exchanges so the model can refer to earlier context.

### 4. Conversation & Session Saving

The app keeps a full in-session history for multi-turn conversations. Every session is also automatically saved to `conversations/YYYY-MM-DD_HH-MM-SS.md` in the vault the moment it starts, with each message appended in real time — so nothing is lost if the app closes unexpectedly.

### 5. Learning (`/savefile`)

When an answer comes from model knowledge or web search it is queued as a `PendingNote` rather than saved immediately. The header subtitle shows the pending count. Type `/savefile` (or `Ctrl+S`) at any time to open the review screen. For each pending note you can:

- Preview the full Q/A content in a scrollable panel
- Accept the model-suggested filename (Enter)
- Type your own filename
- Skip the note entirely

Confirmed notes are written to `.md` files in the vault and added to the live ChromaDB index — immediately searchable without re-ingesting.

### 6. Vault Organisation (`/organize`)

Runs two passes over all vault notes without leaving the chat:

- **Tags pass** — the LLM analyses all notes together and suggests shared YAML frontmatter tags to group related notes. You confirm or override each suggestion before anything is written.
- **Wikilinks pass** — for each note the LLM identifies phrases that refer to another note and proposes `[[wikilinks]]`. You confirm per note.

---

## Architecture

```
chatui.py
│
├── Database
│   ├── ingest_vault()           — load, chunk, embed, persist to ChromaDB
│   └── load_existing_db()       — load persisted ChromaDB from disk
│
├── Tag Helpers
│   ├── _extract_frontmatter_tags()
│   ├── _tags_to_metadata()      — store tags as ChromaDB boolean fields
│   ├── _get_chunk_tags()        — read tags back from a retrieved chunk
│   └── _make_tag_filter()       — build ChromaDB where-clause for tag filtering
│
├── Web Search
│   └── web_search()             — DuckDuckGo via DDGS, no API key required
│
├── Learning
│   ├── PendingNote              — dataclass: question, answer, source, suggestion
│   ├── get_concept_suggestion() — LLM suggests a filename stem
│   └── save_to_vault()          — writes .md file + adds doc to live ChromaDB
│
├── Prompts
│   ├── build_vault_prompt()     — vault context + history → answer
│   ├── build_knowledge_prompt() — history → model answer
│   ├── build_web_prompt()       — web results + history → answer
│   └── _format_history()        — trims history to last HISTORY_WINDOW exchanges
│
└── TUI
    ├── ChatApp                  — unified chat + command interface
    │   ├── /ingest              — @work coroutine, non-blocking
    │   ├── /organize            — inline async worker with queue-based prompting
    │   ├── /savefile            — triggers NoteReviewScreen modal
    │   ├── /clear, /web, /help
    │   └── _process()           — RAG pipeline with tag-aware second pass
    └── NoteReviewScreen         — modal: preview + rename + save pending notes
```

---

## Stack

| Layer | Tool |
|---|---|
| Embedding model | `nomic-embed-text` via Ollama |
| Chat model | `llama3.2:3b` via Ollama |
| Vector database | ChromaDB (persistent, local) |
| LLM framework | LangChain (`langchain-ollama`, `langchain-community`) |
| Web search | DuckDuckGo Search (`duckduckgo-search`) |
| Terminal UI | Textual + Rich |

---

## Setup

```bash
# Install dependencies
pip install langchain langchain-ollama langchain-community chromadb \
            duckduckgo-search textual

# Pull Ollama models (once)
ollama pull nomic-embed-text
ollama pull llama3.2:3b

# Run
python chatui.py
# Then type /ingest to build the database on first launch
```

---

## Suggested Improvements

- **Streaming responses** — pipe LLM tokens to the log as they arrive rather than waiting for the full response
- **Larger chat model** — swap `llama3.2:3b` for a 7B+ model (`mistral`, `llama3.1:8b`) for better reasoning and fewer uncertain fallbacks
- **Re-ingest on change** — watch the vault with `watchdog` and automatically re-embed changed files
- **Smarter chunking** — chunk by markdown heading rather than character count so each chunk stays semantically coherent
- **Note deduplication** — before saving, check if a semantically similar entry already exists and offer to append instead
- **Multi-vault support** — accept `VAULT_PATH` as a CLI argument to serve multiple vaults from the same script
