# Session log — 2026-07-20 — Agent + tools rebuild

## How this session started

Coming off a run of work on `/draft` and `/review`, the question was: what does `/ask` need to become to be a genuinely personal, Claude-Code-like foundation to lean on? Comparing against what Claude Code actually has, `ask()` was missing the core thing — agentic tool use. It pre-fetches a fixed top-k of vault chunks, embeds them into one prompt, and makes a single model call; the model never gets to decide it needs a different search, the full text of a note, or a web lookup.

## Decision 1 — give `ask()` a toolbox

First plan: add a `ToolSpec`/tool-registry layer, teach `ModelClient` a `stream_with_tools` loop (bind tools, let the model call `search_vault`/`read_vault_file`/`web_search`, feed results back, repeat), and wire `ask()` onto it — keeping the existing VAULT/WEAK_MATCH/MODEL_KNOWLEDGE retrieval-path tuning as the initial context, with tools available for the model to go further. Tool activity would show as `tool: search_vault(...)` status lines in the chat log, reusing the existing `_write_status` pattern (confirmed `ask()` doesn't token-stream into the UI today either, so this isn't a UX regression).

This plan was approved, then reopened before implementation.

## Decision 2 — the loop as the whole program's structure, not just ask's

Before writing code, a step back: the four-verb structure (`ask`/`draft`/`classify`/`review`) was useful early on but now feels arbitrary. The proposed replacement mental model — **retrieve → refine → act → observe → refine → memorize → repeat** — was floated as the load-bearing structure for the whole app, not just `/ask`.

Mapping worked out cleanly without inventing new machinery for every word:
- **retrieve** — command-specific context gathering before a run starts.
- **refine / act / observe** — *is* the tool-calling loop itself; every extra round the model spends calling a tool with adjusted arguments is a refine step, no separate function needed.
- **memorize** — an optional post-loop hook (genuinely new — no persistence exists today beyond vault files and in-memory `history`; deliberately scoped out of this rebuild as a follow-up).
- **repeat** — already exists at the app/command-dispatch level.

## Decision 3 — every capability becomes a tool; commands stay put

Key clarification: the four slash commands (`/draft`, `/classify`/`/tags`/`/folder`/`/wikilinks`, `/review`, plain-prompt `/ask`) keep their exact current user-facing behavior. What changes is the *internal shape*: every capability — `search_vault`, `read_vault_file`, `web_search`, and also `draft_note`, `classify_note`, `review_note` — becomes the same `ToolSpec` (name/description/parameters/handler) registered in one `ToolRegistry`. Some tools are model-facing (called by an agent loop mid-conversation, return plain strings); some are command-facing (called directly by the UI when a slash command fires, return typed objects like `File`/`ClassificationSuggestion`). `classify`/`review` don't get forced into a retrieval loop — they already have their one input file in hand and don't need to search anything; that's a deliberate distinction, not an oversight.

## Decision 4 — clean rebuild, not incremental patching

Rather than layer the toolbox onto the existing four-verb files, the call was to delete and rebuild the **app layer** from scratch: `ask.py`, `draft.py`, `classify.py`, `review.py`, and `app.py`'s dispatch logic. Scope explicitly excludes the infrastructure/boundary layer (`utils/vault.py`, `retrieval.py`, `config.py`, `errors.py`, `web.py`, `feedback.py`, `debug_log.py`, `models.py`, `ModelClient` in `llm.py`) — none of that embodies the verb structure, it's just file I/O / ChromaDB / Ollama plumbing, and it stays as-is.

The old four-verb pipeline model isn't being erased from memory, though — it's being documented as the vault's prior architecture (in `config/changelog.md`) rather than silently dropped, per the user's explicit wish not to just throw it away.

## Target structure landed on

```
program_files/
  app.py                    — thin Textual shell; dispatch commands via the tool registry
  utils/
    tools/
      __init__.py            — ToolSpec, ToolRegistry, build_registry(vault, retriever, model, settings)
      vault_tools.py          — search_vault, read_vault_file        (model-facing, str results)
      web_tools.py             — web_search                          (model-facing, str results)
      ask_tools.py              — answer_question                    (runs agent.run() internally)
      draft_tools.py             — draft_note, save_draft            (ported from draft.py)
      classify_tools.py           — classify_note, sync_folder_tags,
                                     suggest_wikilinks, apply_*       (ported from classify.py)
      review_tools.py              — generate_review_questions,
                                      mark_reviewed, files_due_for_review (ported from review.py)
    agent.py                  — run(model, instructions, tools, on_tool_call) -> AgentResult;
                                 the retrieve/act/observe tool-calling loop
    llm.py                    — ModelClient; add stream_with_tools (mechanical bind_tools loop)
    vault.py, retrieval.py, config.py, errors.py, web.py,
    feedback.py, debug_log.py, models.py                        — UNCHANGED
```

Full detail — `ToolSpec`/`ToolRegistry` shape, per-tool porting notes, phase breakdown, file list, and verification steps — is in the approved plan this session executed against. See `config/changelog.md` for what actually landed.

## Why this is worth keeping

This was the session that turned "add tool-calling to ask" into "restructure the whole program around one consistent capability model." The reasoning chain (verb fatigue → loop-as-structure → tools-not-verbs → clean rebuild, scoped to the app layer only) is the kind of context that's easy to lose and expensive to reconstruct later — hence saving it here rather than letting it live only in an approved-plan file that gets overwritten by the next `/plan` session.
