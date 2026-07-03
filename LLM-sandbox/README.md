# ChatUI — Local RAG Vault Assistant

## Overview

ChatUI is a local-first vault assistant that uses Retrieval-Augmented Generation to answer questions from your personal knowledge vault. It runs entirely on-device via Ollama, stores vectors in ChromaDB, and provides a streaming terminal UI via Textual.

## Setup

```bash
# Install dependencies
pip install langchain langchain-ollama langchain-community chromadb \
            ddgs textual pyyaml watchdog

# Models are pulled automatically on first launch from ChatUI/config/models.md.
# To pull manually:
ollama pull nomic-embed-text
ollama pull llama3.1:8b
ollama pull qwen2.5-coder:7b

# Run (from LLM-sandbox/)
cd ChatUI
source .chat_venv/bin/activate
python chatui.py --vault ../Knowledge
# Then type /ingest to build the vector database on first launch
```

## Stack

| Layer | Tool |
|---|---|
| Chat model | `llama3.1:8b` via Ollama (switch at runtime with `/model`) |
| Coding model | `qwen2.5-coder:7b` — `/organize`, `/update`, concept naming |
| Embedding model | `nomic-embed-text` |
| Vector database | ChromaDB (persistent, local) |
| LLM framework | LangChain (`langchain-ollama`, `langchain-community`) |
| Web search | DuckDuckGo Search (no API key required) |
| Terminal UI | Textual + Rich |

## Commands

| Command              | Description                                                            |
| -------------------- | ---------------------------------------------------------------------- |
| `/help`              | Show all commands                                                      |
| `/ingest`            | Rebuild the vector database from vault files                           |
| `/browse`            | Open file browser to load a vault file as context                      |
| `/organize`          | Add YAML tags and wikilinks to vault notes (4-pass LLM worker)         |
| `/savefile`          | Review and save pending notes to the vault                             |
| `/distill <session>` | Distil a session file into structured vault articles                   |
| `/harvest`           | Promote conversation topics into vault stubs                           |
| `/edit`              | LLM-guided edit of a vault file                                        |
| `/daily`             | Summarize today's chat sessions                                        |
| `/export`            | Export Q&A pairs as fine-tuning data (jsonl/alpaca/csv)                |
| `/update`            | Detect `CHANGE:`/`FIX:` directives in config/ and propose code changes |
| `/apply`             | Write the diff proposed by `/update` atomically                        |
| `/model [name]`      | Show or switch the active chat model at runtime                        |
| `/web`               | Toggle web search fallback (DuckDuckGo) on/off                         |
| `/clear`             | Reset conversation history and unload open file                        |
| `/status`            | Show current session state (model, web, file, history, vault)          |
| `/stats`             | Show vault chunk count and ChromaDB size on disk                       |
| `/readme`            | Regenerate this README from current source + config                    |
| `/version`           | Print the chatui.py version string                                     |

## Retrieval pipeline

Questions are answered from the best available source, tried in order:

1. **Vault notes** — top similarity score ≥ 0.65 against ChromaDB
2. **Model knowledge + vault context** — score < 0.65; vault chunks included only if on-topic
3. **Web search** — DuckDuckGo supplement when `/web` is on and no vault match

Tag-aware retrieval: if the top chunk has frontmatter tags, a second scoped search runs filtered to those tags. If it scores within 10% of the baseline, its results replace the unfiltered ones.

## Self-update pipeline

Write `CHANGE:` or `FIX:` directives anywhere in a `config/*.md` file body, then run `/update` → `/apply`. The pipeline extracts only the relevant function (~30 lines), sends it to `qwen2.5-coder:7b`, self-reviews the result, validates with `ast.parse`, and writes atomically. `apply_update.py` is the headless equivalent.

## Vault layout

```
Knowledge/          ← vault articles (Title Case with Spaces filenames)
└── *.md            ← YAML frontmatter with tags; [[wikilinks]] to related articles
```

Config lives in `ChatUI/config/` — see `settings.md` for full architecture documentation.
