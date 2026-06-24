# Obsidian Brain

A fully local, privacy-first knowledge assistant built on top of your Obsidian vault. It combines vector-based semantic search, a locally-running LLM via Ollama, and an optional DuckDuckGo web fallback — all inside a Claude Code-styled terminal UI.

---

## How It Works

### 1. Ingestion (`--ingest`)

When you run the program with `--ingest`, it reads every `.md` file in the vault using LangChain's `DirectoryLoader`. Each file is split into 500-character overlapping chunks by `RecursiveCharacterTextSplitter`, then each chunk is passed through `nomic-embed-text` (running locally via Ollama) to produce a dense numerical vector. All vectors are written to a persistent ChromaDB database on disk (`local_db/`).

This only needs to happen once, or again whenever you add notes manually outside the app.

### 2. Retrieval

When you ask a question, the question text is embedded into a vector using the same `nomic-embed-text` model. ChromaDB performs an approximate nearest-neighbour search across all stored chunk vectors and returns the top 3 (`TOP_K`) most semantically similar chunks — along with a relevance score between 0 and 1.

If the best chunk scores **≥ 0.5** (`SIMILARITY_THRESHOLD`), the vault is considered sufficient and those chunks are used as context for the answer. The threshold is configurable and the live score is shown in the UI (`🔍 Best vault match: 0.78`) so you can tune it.

### 3. Generation

Answers are drawn from the best available source, tried in order:

| Source | Condition |
|---|---|
| **Vault notes** | Top similarity score ≥ threshold |
| **Model knowledge** | Vault score too low — always shown, even if the model flags uncertainty |
| **Web search (supplement)** | Model flags uncertainty — DuckDuckGo result shown alongside the model answer |

All three generation prompts include the last `HISTORY_WINDOW = 4` exchanges from the conversation so the model can refer to earlier context.

### 4. Conversation

The app maintains a full conversation history (`self._history`) across the session. Each question and answer is appended to the history list and included in subsequent prompts. This allows genuine back-and-forth — you can ask follow-up questions, request clarifications, or refer to something said earlier without restating it.

### 5. Learning

When an answer comes from model knowledge or web search, it is not saved immediately. Instead it is queued as a `PendingNote` (question, answer, source, suggested filename). The header subtitle shows the pending count.

Press **Ctrl+S** at any time to open the note review screen. For each pending note you can:
- Preview the full Q/A content in a scrollable panel
- Accept the model-suggested filename (Enter)
- Type your own filename
- Skip the note entirely

Confirmed notes are written to `.md` files in the vault and added to the live ChromaDB index, so they are immediately searchable without re-ingesting.

### 6. Vault Organisation (`--organize`)

A separate TUI mode that runs two passes over all vault notes:

- **Tags pass** — the LLM analyses all notes together and suggests shared YAML frontmatter tags to group related notes (e.g. both `machinelearning.md` and `language-models.md` get an `ai` tag). You confirm or override each suggestion before anything is written.
- **Wikilinks pass** — for each note the LLM identifies phrases in the body that refer to another note and proposes `[[wikilinks]]`. You confirm per note.

---

## Architecture

```
obsidian_brain.py
│
├── Ingestion
│   ├── ingest_vault()          — load, chunk, embed, persist to ChromaDB
│   └── load_existing_db()      — load persisted ChromaDB from disk
│
├── Web Search
│   └── web_search()            — DuckDuckGo via DDGS, no API key required
│
├── Learning
│   ├── PendingNote             — dataclass: question, answer, source, suggestion
│   ├── get_concept_suggestion()— LLM suggests a filename stem
│   └── save_to_vault()         — writes .md file + adds doc to live ChromaDB
│
├── Generation
│   ├── build_vault_prompt()    — vault context + history → answer
│   ├── build_knowledge_prompt()— history → model answer
│   ├── build_web_prompt()      — web results + history → answer
│   └── _format_history()       — trims history to last HISTORY_WINDOW exchanges
│
└── TUI
    ├── ChatApp                 — main chat interface (Ctrl+S, Ctrl+Q)
    │   └── NoteReviewScreen    — modal: preview + rename + save pending notes
    └── OrganizeApp             — standalone vault organiser (--organize)
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

## Usage

```bash
python obsidian_brain.py             # start chat TUI
python obsidian_brain.py --ingest    # rebuild vector DB from vault, then start
python obsidian_brain.py --organize  # tag notes + add wikilinks, then exit
```

**In-app shortcuts**

| Key | Action |
|---|---|
| `Ctrl+S` | Review and save pending notes |
| `Ctrl+Q` | Quit |
| `Esc` | Clear the input field |

---

## Suggested Improvements

- **Streaming responses** — pipe LLM tokens to the `RichLog` as they arrive rather than waiting for the full response, so the UI feels more interactive
- **Larger chat model** — swap `llama3.2:3b` for a 7B+ model (e.g. `mistral`, `llama3.1:8b`) for noticeably better reasoning and fewer uncertain fallbacks
- **Re-ingest on change** — watch the vault directory with `watchdog` and automatically re-embed changed files so the DB stays in sync without a manual `--ingest`
- **Smarter chunking** — chunk by markdown heading rather than character count so each chunk stays semantically coherent; heading-aware splits tend to improve retrieval precision
- **Note deduplication** — before saving a new note, check whether a semantically similar entry already exists in the vault (via similarity search) and offer to append rather than create a duplicate
- **Conversation export** — add a `Ctrl+E` shortcut to export the current session as a dated `.md` file in the vault
- **Tag-aware retrieval** — filter the ChromaDB search by YAML frontmatter tags so a question tagged `physics` only searches physics notes, reducing noise from unrelated topics
- **Web search toggle** — let the user enable or disable the DuckDuckGo fallback at runtime without editing the source file
- **Multi-vault support** — accept `VAULT_PATH` as a CLI argument so the same script can serve multiple vaults without editing the config block
