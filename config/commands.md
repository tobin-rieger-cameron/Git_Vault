---
summary: >
  Defines every command that chatui.py exposes. Edit any file in config/ —
  frontmatter or body text — then run /update inside ChatUI: it diffs all
  config/*.md files against their startup state, sends every change to
  qwen2.5-coder:7b, and proposes a unified diff for chatui.py. Run /apply to
  write the patch after reviewing it. This file is also the best place to
  describe new features in prose — the model will read those descriptions and
  propose an implementation.
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
    description: diff all config files against startup state and ask the coding model to propose code changes
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
| `/update` | Diff all config files against startup state; coding model proposes code changes | — |
| `/apply` | Apply the diff proposed by `/update` to `chatui.py` (yes/no first), then prompt to restart | — |

## Self-update workflow

Make any change to any file in `config/` — frontmatter values, body text, new sections, new commands — then run `/update`.

### What triggers a code change proposal

`/update` reads every `config/*.md` file and diffs it against the snapshot captured at startup. If anything changed — in frontmatter or in the body — the full diff is sent to `qwen2.5-coder:7b` alongside the relevant sections of `chatui.py`. The model decides what code changes (if any) are implied:

| What you changed | What the model does |
|---|---|
| New entry in `commands:` frontmatter | Adds handler, `_cmd_*` method, `_HELP_TEXT` entry |
| Removed entry from `commands:` frontmatter | Removes handler, method, help text |
| Changed a command description | Updates `_HELP_TEXT` |
| New feature described in markdown prose | Implements or stubs it |
| Numeric setting value (e.g. `top_k`) | Says "no code change needed" — restart applies it |
| Documentation / wording only | Says "no code change needed" |

### Step-by-step

**1. Edit any config file** while ChatUI is running (in another terminal or editor). Changes to any of `models.md`, `settings.md`, `commands.md` — or any new `.md` file added to `config/` — are all detected.

**2. Run `/update`** in ChatUI. It will:
- Show a structured summary of frontmatter value changes
- List which files changed and how many lines
- Call `qwen2.5-coder:7b` with the full unified diffs + relevant `chatui.py` sections
- Stream the model's response (a unified diff, or "No code changes required")

**3. Review the response.** If the model proposes a diff, scroll up and read it. Check:
- Does it patch the right sections (`handlers`, `_HELP_TEXT`, `_cmd_*` methods)?
- Does the implementation make sense?

If it looks wrong, edit `chatui.py` manually instead.

**4. Run `/apply`** to write the patch. Type `yes` to confirm. ChatUI dry-runs `patch` first; if the dry-run passes it applies for real. Reports the exact `patch` output on failure.

**5. Restart** (`Ctrl+Q`, then `python chatui.py`). Changes are live.

## Limitations

- The coding model's output is a first draft — always read it before applying.
- `/apply` calls the system `patch` binary. If the model wraps the diff in markdown fences or produces bad headers, the dry-run fails gracefully with the error shown.
- Running `/update` again overwrites the stored pending patch. Apply first if you want to keep it.
- `patch` must be installed (`/usr/bin/patch` on most Linux systems — it is on Arch).
- Settings and model changes (frontmatter values) apply on restart without any patch; the model will correctly say "no code changes required" for those.
