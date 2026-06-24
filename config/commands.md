---
summary: >
  Defines every command that chatui.py exposes. The YAML spec under commands:
  is the source of truth — /update reads it to detect additions or removals and
  calls the coding model to propose the corresponding Python implementation.
  Edit descriptions freely; add or remove entries to trigger a code patch.
  The /apply command then writes the patch to chatui.py after confirmation.
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
    description: apply the unified diff proposed by /update to chatui.py with yes/no confirmation, then prompt to restart
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
| `/apply` | Apply the diff proposed by `/update` to `chatui.py` (yes/no first), then prompt to restart | — |

## Self-update workflow

This is the full loop for adding or changing commands:

### 1. Edit this file

Add an entry under `commands:` in the frontmatter and a matching row in the table above. At minimum, provide a `description`; optionally add a `shortcut`.

```yaml
  mycommand:
    description: a short description of what it does
    shortcut: Ctrl+M   # optional
```

To remove a command: delete the frontmatter entry and the table row.

### 2. Run `/update` inside ChatUI

ChatUI will:
- Compare this file against the command handlers registered in `chatui.py`
- Show a diff between spec and implementation
- Ask `qwen2.5-coder:7b` to generate a unified diff with the necessary Python changes
- Stream the diff into the chat log and store it as a pending patch

### 3. Review the proposed diff

Scroll up to read what the coding model produced. The model is given the three most relevant source sections — `_HELP_TEXT`, the `handlers` dict, and a `_cmd_*` example — so its output should be targeted. Check:
- Is the new command registered in `handlers`?
- Is it in `_HELP_TEXT`?
- Does the placeholder method make sense?

If the diff looks wrong, edit `chatui.py` manually instead.

### 4. Run `/apply`

Type `/apply`, then `yes` to confirm. ChatUI will:
- Dry-run `patch` (trying `-p1` then `-p0` header styles)
- Apply if the dry-run succeeds
- Report the patch output if it fails (apply manually in that case)

### 5. Restart

`Ctrl+Q`, then `python chatui.py`. The new command is live.

## What /update does and doesn't do

| Change type | /update detects? | How to apply |
|---|---|---|
| New command in spec | Yes | `/update` → `/apply` → restart |
| Removed command from spec | Yes | `/update` → `/apply` → restart |
| Settings / model values changed | Yes (reports drift) | Restart (no patch needed) |
| Behavior change to an existing command | No | Edit `chatui.py` manually |

## Limitations

- The coding model's diff is a first draft — always review it before `/apply`.
- `/apply` runs `patch` against `chatui.py`. If the diff has markdown fences or bad headers, the dry-run will catch it and fail gracefully.
- A second `/update` overwrites the stored patch. Apply before running `/update` again.
- `patch` must be installed (`/usr/bin/patch` on most Linux systems).
