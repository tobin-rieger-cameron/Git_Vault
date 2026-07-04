# ChatUI — Local RAG Study Assistant

## Status: mid-rebuild

The app is being rebuilt from scratch around a redefined purpose (see below). The old single-file `chatui.py` was deliberately wiped; a new `chatui/` package skeleton exists (module/class/function signatures, no logic yet — everything raises `NotImplementedError`). Nothing in this README is runnable yet. This file will be updated as real behavior lands module by module.

## Overview

ChatUI is a local-first tool for building and maintaining a growing library of living, stylized papers on subjects you're studying. It runs entirely on-device via Ollama, stores vectors in ChromaDB, and provides a terminal UI via Textual. It's organized around four verbs:

1. **Ask** — vault-first RAG: retrieve from your notes, fall back to grounded/model knowledge, optionally supplement with a web search.
2. **Draft a paper** — back-and-forth authoring of a long-form, living document on a subject, not one-shot generation.
3. **Classify inline** — right after a paper is drafted or substantially revised, suggest where it belongs and what it should link to, in the same session — not a separate batch review queue.
4. **Review** — generate lightweight recall questions from a paper and track when it was last reviewed.

## Setup (once the rebuild lands)

```bash
# Install dependencies
pip install langchain langchain-ollama langchain-community chromadb \
            ddgs textual pyyaml

# Models are pulled automatically on first launch from ChatUI/config/models.md.
# To pull manually:
ollama pull nomic-embed-text
ollama pull llama3.1:8b
ollama pull qwen2.5-coder:7b

# Run (from LLM-sandbox/ChatUI)
source .chat_venv/bin/activate
python -m chatui --vault ../Knowledge
# Then /ingest to build the vector database on first launch
```

## Stack

| Layer | Tool |
|---|---|
| Chat model | `llama3.1:8b` via Ollama (switch at runtime with `/model`) |
| Coding model | `qwen2.5-coder:7b` — classification suggestions, review-question generation |
| Embedding model | `nomic-embed-text` |
| Vector database | ChromaDB (persistent, local) |
| LLM framework | LangChain (`langchain-ollama`, `langchain-community`) |
| Web search | `ddgs` (no API key required) |
| Terminal UI | Textual + Rich |

## Command surface (planned — see `ChatUI/config/commands.md` once rewritten)

| Input | Verb |
|---|---|
| plain text, no `/` | Ask |
| `/draft <subject>` | Draft a paper |
| `/classify` | Classify the paper just drafted/saved |
| `/review [subject]` | Generate review questions, or list papers due for review |
| `/ingest` | Rebuild the vector database from vault files |
| `/web` | Toggle web-search supplement on/off |
| `/model [name]` | Show or switch the active chat model |

The old app's much larger command list (`/organize`, `/distill`, `/harvest`, `/update`/`/apply`, `/export`, etc.) is not being carried forward as-is — `/organize`'s batch-classification model is replaced by inline classification (verb 3 above), and the `/update`/`/apply` self-modifying-code pipeline has been dropped entirely (didn't serve the app's actual purpose).

## Retrieval pipeline

Questions are answered from the best available source, tried in order:

1. **Vault notes** — top similarity score ≥ 0.65 against ChromaDB
2. **Model knowledge + vault context** — score < 0.65; vault chunks included only if on-topic
3. **Web search** — supplement when `/web` is on and vault retrieval didn't produce chunks (or, for broad-topic questions, when the vault hit doesn't actually cover the topic asked)

Tag-aware retrieval: if the top chunk has frontmatter tags, a second scoped search runs filtered to those tags. If it scores within 10% of the baseline, its results replace the unfiltered ones.

## Vault layout

```
Knowledge/          ← vault articles (Title Case with Spaces filenames)
└── *.md            ← YAML frontmatter with tags; [[wikilinks]] to related articles
```

Config lives in `ChatUI/config/` — see `settings.md` for architecture documentation and `style_guide.md` for the coding standards the rebuild follows.
