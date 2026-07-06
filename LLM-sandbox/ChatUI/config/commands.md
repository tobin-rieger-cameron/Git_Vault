---
summary: >
  Defines every command chatui/app.py exposes. There is no self-update
  pipeline — this file is documentation only; command changes are made by
  hand-editing chatui/app.py and its verb modules, not by editing this file
  and running a directive.
commands:
  draft:
    description: start or resume drafting a paper on a subject; enters a back-and-forth revise loop
  classify:
    description: suggest folder/tags/wikilinks for the file most recently drafted or saved this session
  review:
    description: generate recall questions for a paper, or list papers due for review
  ingest:
    description: rebuild the vector database from all vault markdown files
  web:
    description: toggle web search fallback on/off for Ask
  model:
    description: switch the chat model at runtime
---

# Commands

Mapped onto the four verbs — Ask, Draft a paper, Classify inline, Review (see `Knowledge/conversations/claude_transcript.md` / memory `project_chatui_redefinition`). This replaces the old ~15-command sprawl (`/organize`, `/distill`, `/harvest`, `/daily`, `/export`, `/edit`, `/status`, `/stats`, `/readme`, `/version`, `/update`, `/apply`, ...) — none of that machinery maps to a verb, so none of it came back.

| Input | Verb | Behavior |
|---|---|---|
| plain text, no `/` | **Ask** | `ask.ask()` — RAG loop, default interaction. Vault path if top score ≥ `similarity_threshold`; weak-match path (model knowledge, vault notes only if relevant) if chunks exist but score too low; model-knowledge path (with web supplement if `/web` is on) if no chunks at all |
| `/draft <subject>` | **Draft a paper** | `draft.start_draft()` if no matching paper exists, else loads it; enters a revise loop (`draft.revise_draft()`) until the user ends the session; stays inline in the same scrolling conversation as Ask — no separate screen/mode |
| `/classify` | **Classify inline** | Auto-suggested immediately after `draft.save_draft()`, but can also be run explicitly. Runs `classify.suggest_classification()` against the file most recently drafted/saved this session; shows the suggestion for accept/edit (single-item, not a batch) — nothing is written to the vault until explicitly accepted or edited |
| `/review [subject]` | **Review** | With a subject: `review.generate_review_questions()` for that paper — plain free-text Q + answer-hint, no multiple-choice/cloze. Without one: shows `review.files_due_for_review()` and lets the user pick |
| `/ingest` | (support) | `Retriever.ingest()` — rebuilds `local_db/` from the vault. Required after `chunk_size`/`chunk_overlap` changes in `settings.md` |
| `/web` | (support) | Toggles web-supplement on/off for `ask()` |
| `/model [name]` | (support) | `ModelClient.switch_chat_model()` — switches the chat model at runtime; see `models.md` for available models |

## Notes

- Command words are `/draft`, `/classify`, `/review` — chosen deliberately, not placeholders.
- Editing this file has no effect on the running app — there is no `/update`/`/apply` self-update pipeline. To change command behavior, edit `chatui/app.py` and the relevant verb module directly.
- Applied command/behavior changes are logged in `config/changelog.md`, same as any other code change.
