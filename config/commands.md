---
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
---

# Commands

This file holds commands that [[ChatUI]] exposes.

**Adding a command:** add an entry under `commands:` with at least a `description`.
Run `/update` inside the app — the coding model will propose the implementation.

**Removing a command:** delete the entry and run `/update`.

**Changing a description:** edit freely; `/update` will patch `_HELP_TEXT` in chatui.py.
