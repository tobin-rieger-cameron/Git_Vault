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

^f67b29

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
| `/apply` | Apply the diff proposed by `/update` (yes/no confirmation, then restart) |

**Keyboard shortcuts**

| Key | Action |
|---|---|
| `Ctrl+S` | Shortcut for `/savefile` |
| `Ctrl+B` | Shortcut for `/browse` |
| `Ctrl+Q` | Quit |
| `Esc` | Clear the input field |

---

## Self-updating via config

Add a command to `config/commands.md` → run `/update` → review the diff → `/apply` → restart. The coding model (`qwen2.5-coder:7b`) generates the patch; `/apply` dry-runs it before writing.

See `config/commands.md` for the full step-by-step workflow and limitations.

---

## Configuration

All settings live in `config/` as markdown files with YAML frontmatter. Each file is self-documenting — open it to see every key, its default, and what it does.

| File | Controls |
|---|---|
| `config/models.md` | Model assignments per role; `models:` list is auto-pulled on launch |
| `config/settings.md` | Thresholds, chunk sizes, history window, vault path; full technical reference |
| `config/commands.md` | Command spec + self-update workflow — edit here, run `/update` to get a code patch |

---

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

---

## Suggested Improvements

- **Re-ingest on change** — watch the vault with `watchdog` and automatically re-embed changed files
- **Smarter chunking** — chunk by markdown heading rather than character count so each chunk stays semantically coherent
- **Note deduplication** — before saving, check if a semantically similar entry already exists and offer to append instead
- **Multi-vault support** — accept `vault_path` as a CLI argument, overriding `config/settings.md`
