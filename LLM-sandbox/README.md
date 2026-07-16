# ChatUI — Local RAG Study Assistant

## Status: functional

The rebuild described below is implemented and running: `chatui/app.py` wires a real Textual UI (fuzzy file search, command autocomplete, a live-diff draft view, in-preview wikilink highlighting with click-to-navigate) to the four real verb modules. Verified against actual Ollama models and a real ChromaDB instance, plus the full unit test suite. The `chatui.py` single-file predecessor was deliberately wiped as part of this rebuild; its full history is still in git if anything from it is ever needed.

## Overview

ChatUI is a local-first tool for building and maintaining a growing library of living, stylized papers on subjects you're studying. It runs entirely on-device via Ollama, stores vectors in ChromaDB, and provides a terminal UI via Textual. It's organized around four verbs:

1. **Ask** — vault-first RAG: retrieve from your notes, fall back to grounded/model knowledge, optionally supplement with a web search.
2. **Draft a paper** — back-and-forth authoring of a long-form, living document on a subject, not one-shot generation.
3. **Classify inline** — right after a paper is drafted or substantially revised, suggest where it belongs and what it should link to, in the same session — not a separate batch review queue.
4. **Review** — generate lightweight recall questions from a paper and track when it was last reviewed.

## Setup

```bash
# Install dependencies
pip install langchain langchain-ollama langchain-community chromadb \
            ddgs textual pyyaml

# Models are pulled automatically on first launch from ChatUI/config/models.md.
# To pull manually:
ollama pull nomic-embed-text
ollama pull llama3.1:8b
ollama pull qwen2.5-coder:7b

# Run (from LLM-sandbox/)
source .venv/bin/activate
cd ChatUI
python -m chatui --vault ../Knowledge
# Then /ingest to build the vector database on first launch
```

Debug logging: every run writes `ChatUI/chatui_debug.log` (gitignored) — prompts/responses to both models, retrieval scores, and any error that's only otherwise shown in the UI.

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

## Command surface

Click a file in the tree, or fuzzy-search for one (`ctrl+f`), to make it the *active file* — every per-file command below acts on whichever one is currently active, so there's no separate lookup step and no way to accidentally target something other than what's on screen. Autocomplete (Tab or →) completes any command below as you type it.

| Input | Verb |
|---|---|
| plain text, no `/` | Ask |
| `/draft` | Revise the active file — write an instruction next, `/done` saves |
| `/draft <subject>` | Start a brand-new paper titled subject, then revise as above |
| `/tags`, `/wikilinks`, `/folder` (or just mentioning one) | Classify: suggest tags / wikilinks / folder for the active file |
| `/review` | Generate recall questions for the active file, or list papers due for review if none is active |
| `/ingest` | Rebuild the vector database from vault files |
| `/web` | Toggle web-search supplement on/off |
| `/model [name]` | Show or switch the active chat model |
| `/explorer` (or `f2`) | Toggle the file tree |
| `/palette` (or `ctrl+p`) | Open the command palette |

The old app's much larger command list (`/organize`, `/distill`, `/harvest`, `/update`/`/apply`, `/export`, etc.) was not carried forward as-is — `/organize`'s batch-classification model is replaced by inline, per-file classification (`/tags`/`/wikilinks`/`/folder` above), and the `/update`/`/apply` self-modifying-code pipeline was dropped entirely (didn't serve the app's actual purpose).

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
