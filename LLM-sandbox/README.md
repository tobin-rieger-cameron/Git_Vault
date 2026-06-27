# ChatUI - Local Vault

## Overview

ChatUI is a local-first vault assistant that leverages Retrieval-Augmented-
Generation to provide intelligent responses based on your personal
knowledge vault. It uses Ollama LLMs for conversational capabilities,
ChromaDB as the vector database, and Textual TUI for an interactive interface.

## Setup

```bash
# Install dependencies
pip install langchain langchain-ollama langchain-community chromadb \
            duckduckgo-search textual pyyaml

# Models are pulled automatically on first launch from config/models.md.
# To pull manually:
ollama pull nomic-embed-text
ollama pull llama3.2:3b
ollama pull qwen2.5-coder:7b

# Run
python chatui.py
# Then type /ingest to build the database on first launch
```

## Commands

| Command | Description |
|---|---|
| `/help` | Show this message |
| `/browse` | Open file browser to load a file as context |
| `/ingest` | Rebuild the vector database from vault files |
| `/organize` | Add YAML tags and wikilinks to vault notes |
| `/savefile` | Review and save pending notes to the vault |
| `/clear` | Reset conversation history and open file |
| `/web` | Toggle web search fallback on/off |
| `/update` | Detect config directives and propose code changes |
| `/apply` | Apply the diff proposed by /update (asks yes/no first) |
| `/edit` | LLM-guided edit of a vault file (or the open file) |
| `/daily` | Summarize today's chat sessions; optionally save |
| `/export` | Export Q&A pairs as fine-tuning data (jsonl/alpaca/csv) |
| `/version` | Print the ChatUI.py version string |
| `/status` | Show current session state (web, file, history, vault) |
| `/stats` | Show vault chunk count and DB size on disk |
| `/readme` | Regenerate README.md from current source + config |
| `/harvest` | Promote INDEX topics into vault stubs with wikilinks |
| `/distill <session>` | Distil a session file into structured vault articles |
