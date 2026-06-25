---
summary: Backlog of improvement ideas for chatui.py — not yet directives, just notes.
---

# Ideas

## UX

- **`/status` command** — show web state, open file, history length, vault status, pending notes, patch pending. ✅ done 2026-06-24
- **`/web` state in subtitle** — header always shows `web: on` / `web: off` so you never have to guess. ✅ done 2026-06-24
- **Fuzzy match on unknown commands** — `difflib.get_close_matches` suggests the nearest known command when you mistype. ✅ done 2026-06-24
- **Loading indicator** — show a spinner or progress bar in the header while a worker is running (ingest, update, LLM call). Users couldn't tell if the app was working or frozen.
- **Text wrapping and margins** — add left/right padding to the RichLog so long answers don't run wall-to-wall. Textual CSS `padding: 0 4` on the log widget.

## Commands

- **`/organize` should clean up conversation logs** — condense single-command sessions and testing noise to 1-2 line summaries, the same way Claude Code did manually on 2026-06-24.
- **`/rename` file action** — `/savefile` and `/organize` let you type a new name, but there's no way to rename an existing vault file from inside chatui. Would fix the `individual-sized-cakes.md` problem (user tried to request a rename via the tags field).
- **Action mode** — chatui makes guided edits to vault files on request, not just saves new ones. E.g. "append a summary section to kinematics.md".
- **`/find` or `/search` command** — raw semantic search without the LLM answer, showing chunk scores and source lines. Useful for debugging retrieval.

## Retrieval

- **Note-to-file deduplication** — before saving a new note, check for semantically similar existing files (score > 0.8) and offer to append instead of creating a new file. Fixes the "training offline LLMs" answer going to `machinelearning.md` when `language-models.md` already exists.
- **Re-ingest on change** — watch vault with `watchdog`, re-embed only changed files.
- **Smarter chunking** — chunk by markdown heading rather than character count.

## Self-update

- **`/update` — model fine-tuning / improvement** — explore ways to fine-tune or distil the local chat model on vault content. Probably out of scope for chatui directly, but worth tracking.

## Vault hygiene

- `individual-sized-cakes.md` — rename to `cupcakes.md`; fix the YAML tags field which contains a rename request instead of actual tags.
- `taxonomy.md` — missing YAML frontmatter; `/organize` didn't tag it.
- `ChatUI.md` — empty file, delete or fill.
