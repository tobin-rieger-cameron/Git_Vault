# ChatUI - Local-First Vault RAG Assistant

## Overview
ChatUI is a local-first vault assistant that leverages Retrieval-Augmented Generation (RAG) to provide intelligent responses based on your personal knowledge vault. It uses Ollama LLMs for conversational capabilities, ChromaDB as the vector database, and Textual TUI for an interactive interface.

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
| `/harvest` | Promote INDEX topics into vault notes with ] |

## Configuration
Configure ChatUI by editing the `config.yaml` file. Key settings include:
- `vault_path`: Path to your personal knowledge vault.
- `llama_model`: LLM model for conversational responses.
- `chromadb_path`: Path to ChromaDB vector store.

## Architecture
ChatUI is built on a local architecture using:
- Ollama LLMs for conversational capabilities.
- ChromaDB as the vector database for efficient retrieval of context.
- Textual TUI for an interactive and user-friendly interface.

## Stack
The technology stack includes:
- `llama3.2:3b` (for chat)
- `qwen2.5-coder:7b` (for organizing vault notes)
- `nomic-embed-text`
- ChromaDB
- LangChain
- Textual

For more detailed information, refer to the [ChatUI GitHub repository](https://github.com/your-repo/chatui).