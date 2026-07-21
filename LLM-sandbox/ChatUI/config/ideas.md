---
summary: Backlog of improvement ideas for ChatUI — not yet directives, just notes.
---

# Ideas

## General

- article text should appear as its being written
- /distill command is confusing - consider an overhaul and simplification of /commands in general
- ✅ done — guided co-edit review framework for `/organize` and `/distill` (see [[changelog#2026-07-03|changelog]])

## UX

- ✅ done — resizable split-pane divider, hidden scrollbars (see [[changelog#2026-07-03|changelog]])
- ✅ done — full front-end refactor: theme, resizable divider, folder tree, default-accepted review model (see [[changelog#2026-07-03|changelog]])
- ✅ done — transparent/ANSI-adaptive background (see [[changelog#2026-07-03|changelog]])
- ✅ done — folder tree file picker replacing flat list (see [[changelog#2026-07-03|changelog]])
- ✅ done — token-level streaming for tag/wikilink suggestion generation (see [[changelog#2026-07-04|changelog]])
- ✅ done — `/wikilinks` status text + inline preview highlighting instead of chat-log walkthrough (see [[changelog#2026-07-16|changelog]])
- **Open for next time: refine `/wikilinks` visual feedback** — the pending-vs-committed highlight styles (bold-on-accent vs underline) work but haven't been tuned against the rest of the theme; and there's no in-preview indicator of *how many* candidates are pending or which one is focused beyond the statusbar text. Worth a pass once there's been more real usage to see what's actually confusing.
- **Bug: can't scroll `#log` while the agent is "thinking…"** — noticed 2026-07-20 during real usage. Something about the in-flight response (or the streaming/status updates leading up to it) appears to steal or block scroll input on the chat log until the answer finishes. Needs a live repro to pin down whether it's a Textual focus issue, a `RichLog` auto-scroll-to-bottom fighting the user, or a worker blocking the event loop.
- **Bug: `#cmd` input doesn't wrap long text** — typing a prompt long enough to exceed the input bar's width scrolls characters off the right edge instead of wrapping to a second visual line, so you can't see what you've already typed. `Input` widgets are single-line by default in Textual; fixing this likely means switching to a `TextArea`-based input or finding Textual's equivalent of soft-wrap for `Input`.

## Commands

Note: `/organize`, `/savefile`, `/distill`, and `/update`/`/apply` no longer exist — the app was rebuilt from scratch around four verbs (Ask/Draft/Classify/Review, see `project_chatui_redefinition` memory). Ideas below are re-evaluated against that surface rather than dropped outright, since the underlying need may still apply to `/classify` or `/draft`.

- **`/rename` file action** — no command in the new surface lets you rename an existing vault file either; `Vault.save_file()` doesn't cover renames. Still an open gap, now against `vault.py`/`app.py` rather than the old `/savefile`/`/organize`.
- **`/find` or `/search` command** — raw semantic search without the LLM answer, showing chunk scores and source lines. Useful for debugging retrieval; would sit alongside `Retriever.search()` as a thin support command, same idea as before.
- **Ask doesn't have a save-to-vault action** — the old `/savefile` queued model-knowledge/web answers for review and writing to the vault, but only from non-vault-grounded paths. That whole flow is gone; `/draft` is now the only route from a conversation to a saved paper. Worth deciding whether Ask should be able to hand a good answer straight to `/draft` as a starting point, rather than requiring the user to re-type the subject.

## Retrieval

- **Inject vault file listing into prompts** — add a `--- VAULT FILES ---` section to every prompt built by ChatUI so the model always knows what files exist. Pros: model can reason about actual vault contents for any organisation/structure question, no extra retrieval step, works even for files with low embedding scores. Cons: adds ~500–1000 tokens to every prompt (scales with vault size), increases latency and token cost, potentially crowds out retrieved chunk context on models with small context windows. Alternative already implemented: `Knowledge/INDEX.md` embedded as a regular vault file — cheaper per-query but only surfaces when retrieval scores it highly enough.
- **Web search hang — fix not fully verified** — the original hang (a stalled `duckduckgo_search` connection blocking a class-question web supplement) got an `asyncio.wait_for` timeout wrapper that didn't fully resolve it, then a migration to the `ddgs` package as the real fix. The `ddgs` migration itself has never been retested against the original hang scenario. Needs a live repro to actually confirm it's fixed rather than just assumed.

## Multi-instance

- **Running multiple ChatUI instances simultaneously** — currently blocked by a PID file lock. Consider whether multi-instance is a desirable pattern: one instance per vault (different `--vault` paths), or a server mode where one background process serves multiple front-ends. Key challenges: shared `local_db/` writes would corrupt ChromaDB (it's not concurrent-write-safe), and two watchdog observers on the same vault directory would double-ingest. If multi-instance is wanted, the DB would need to move to a read-only mode for secondary instances, or ChromaDB would need to be replaced with something that supports concurrent writers (e.g. Qdrant, Weaviate).

- **Watching the tmux session while Claude Code drives it** — root cause of the TUI locking up: Claude Code drives ChatUI via `tmux send-keys` to an existing session. When the user is simultaneously attached (`tmux attach -t chatui`), both are writing to the same pseudo-terminal — input races are possible but not the core issue. The real problem is that Claude Code's polling loops (`until condition; do sleep N; done`) require explicit user approval and get rejected mid-run, leaving the pane in an indeterminate state (partial command sent, ingest or LLM call still in progress, no one consuming output). The TUI appears frozen because Textual is waiting on async work that has no one driving its event loop cleanly. **Fix when this pattern is needed:** open a second tmux window (`Ctrl+b c`) for read-only observation (`tmux attach -t chatui:1`), and keep the driving window separate. Alternatively, Claude Code should use `run_in_background: true` for any wait loops so approval prompts don't interrupt mid-flight.

## Vault hygiene

- **Idea: consolidate all taxonomy-related notes into one `Taxonomy.md`** — considered 2026-07-02, not adopted for now. Current state: 13 files in `000-information/`, ~4,500 words total. Tradeoff discussed: merging hurts retrieval precision (chunk_size=800/top_k=5 means a query would pull cross-topic slices of one giant file instead of a tightly-scoped single-concept chunk) and collapses the `[[wikilink]]` backlink graph between sub-concepts. Lighter alternative floated instead: keep files separate, expand `Taxonomy.md` into a hub note with a one-line summary + link per sub-topic. Revisit if retrieval quality across the split files ever stabilizes and the real pain point turns out to be navigation rather than retrieval.
- **Idea: fold `conversations/` into the KB proper instead of keeping it a separate excluded folder** — noted 2026-07-03. There are currently two distinct `conversations/` locations (`ChatUI/conversations/` — Claude Code's own session transcript — and `Knowledge/conversations/` — daily ChatUI chat logs, explicitly excluded from ingest via `_discover_vault_files`). Idea: bring `Knowledge/conversations/` content into the vault proper (or a dedicated ingested location) but tag/tier it as **unrefined** — raw Q&A, not yet distilled/reviewed — so retrieval can treat it as lower-priority/supplementary rather than on par with curated articles. This is the same underlying need as a two-collection design (separate vault and conversations collections) — conversations dominated retrieval scores (0.91 vs 0.48) before being excluded outright. Any implementation should reuse that collection-tiering idea rather than just re-including conversations at equal weight, which reintroduces the original problem.
- **Re-raised 2026-07-20: ChatUI has no built-in way to save an `/ask` conversation at all right now** — the only record is the gitignored debug log, which truncates every response to ~400 characters (see `LLM-sandbox/conversations/2026-07-20_agent-tools-rebuild.md` for how that surfaced). Two-part request: (1) a way to save a full conversation — simplest version is "save every conversation, untruncated, to disk" (a real analogue of the `Knowledge/conversations/` idea above, minus the truncation bug); (2) a `/distill`-style command or workflow that turns a saved conversation into a proper vault article via `draft_note`/`classify_note` — reusing the tiering idea above (unrefined conversation vs. distilled article) rather than treating raw Q&A logs as equal to curated notes. This is also the natural home for the "memorize" stage of the retrieve/act/observe/memorize loop that the 2026-07-20 rebuild deliberately left unimplemented.
