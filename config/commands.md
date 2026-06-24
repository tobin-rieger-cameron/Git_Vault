---
summary: >
  Defines every command that chatui.py exposes. The YAML spec under commands:
  is the source of truth — /update reads it to detect additions or removals and
  calls the coding model to propose the corresponding Python implementation.
  Edit descriptions freely; add or remove entries to trigger a code patch.
commands:
  help:
    description: list all available commands
  browse:
    description: open TUI file browser; load a file as chat context
    shortcut: Ctrl+B
  ingest:
    description: rebuild the vector database from all vault markdown files
  organize:
    description: add YAML frontmatter tags and wikilinks to vault notes
  savefile:
    description: review and save pending LLM-generated notes to the vault
    shortcut: Ctrl+S
  clear:
    description: reset conversation history and unload any open file
  web:
    description: toggle DuckDuckGo web search fallback on/off
  update:
    description: detect config drift and propose code patches via coding model
  apply:
    description: apply the unified diff proposed by /update to chatui.py with line-by-line confirmation, then prompt to restart
---

# Commands

| Command | Description | Shortcut |
|---|---|---|
| `/help` | List all available commands | — |
| `/browse` | Open TUI file browser; load a file as chat context | `Ctrl+B` |
| `/ingest` | Rebuild the vector database from all vault markdown files | — |
| `/organize` | Add YAML frontmatter tags and `[[wikilinks]]` to vault notes | — |
| `/savefile` | Review and save pending LLM-generated notes to the vault | `Ctrl+S` |
| `/clear` | Reset conversation history and unload any open file | — |
| `/web` | Toggle DuckDuckGo web search fallback on/off | — |
| `/update` | Detect config drift and propose code patches via coding model | — |
| `/apply` | Apply the diff proposed by `/update` to `chatui.py`, hunk-by-hunk, then prompt to restart | — |

## Adding or removing commands

**Add:** create an entry under `commands:` in the frontmatter with at least a `description` (and optionally a `shortcut`), add a matching row to the table above, then run `/update` — the coding model will propose the Python implementation.

**Remove:** delete the frontmatter entry and the table row, then run `/update`.

**Change a description:** edit both the frontmatter and the table row; `/update` will patch `_HELP_TEXT` in `chatui.py`.
