---
summary: Backlog of improvement ideas for chatui.py — not yet directives, just notes.
---

# Ideas

## General

- article text should appear as its being written
- /distill command is confusing - consider an overhaul and simplification of /commands in general
- ✅ done (Phase 1+2 — see `config/changelog.md` 2026-07-03): guided co-edit review framework for `/organize` and `/distill` — `Proposal` + `ChatApp._review()` + split-pane review panel in `chatui.py`. Split-pane UI, per-item accept/skip/edit/all/none, and override-reason feedback loop are all live.

## UX

- background should be transparent / adhere to the terminal colorscheme
- user experience: ![[Pasted image 20260703171556.png]]
	this is pretty confusing
![[Pasted image 20260703171752.png]]
	✅ done 2026-07-03: after running /organize, I have to just sit and wait with no visual feedback of what the program is doing while it's *generating* suggestions — root cause was `_run_organize` never calling `_set_busy(True, ...)`, so the busy-bar (already used everywhere else in the app) stayed invisible for the whole run. Fixed by turning the busy-bar on for the duration of `/organize`, adding a `_await_with_progress()` helper that ticks an elapsed-time counter onto it during any single long LLM call, and showing which file/session is currently being processed in Pass 2 ("Checking X.md for wikilinks… (i/N)"), Pass 3, and Pass 4. Same helper wired into `/distill`'s article-generation call for consistency.

	✅ done 2026-07-03: running /organize should put the user right into the left/right
	screen, the user should be able to select files and folders,
	presenting a checkbox next to selected items. then tags and/or
	wikilinks can be generated for the selected items. unorganized
	items should be highlighted, but user should be able to re-
	organize all files in the working directory at their leisure —
	`/organize` now opens a checkbox picker in the review panel before
	Pass 1 runs (`ChatApp._pick_files_to_organize()` in `chatui.py`),
	pre-checking files missing frontmatter or not yet placed (tagged
	`[unorganized]`) while leaving already-organized files selectable
	too. `all`/`none`/`unorganized` bulk commands plus per-row click
	toggling, Enter to start. Only Pass 1/2/4 (tag/wikilink/placement
	generation) are scoped to the selection — Pass 2 still treats the
	full vault as valid wikilink-target context so a selected file can
	still link to an unselected one, and Pass 3/5 (conversation
	condensing, wikilink validation) are vault-wide housekeeping
	unrelated to the selection and run unconditionally. No folder-level
	bulk selection yet (flat file list, naturally grouped by the
	existing path sort) — a reasonable v2 if it's ever needed.

- cleaner text writing to the console, current version clunkily cuts off the active text

## Commands

- **`/rename` file action** — `/savefile` and `/organize` let you type a new name, but there's no way to rename an existing vault file from inside chatui. Would fix the `individual-sized-cakes.md` problem (user tried to request a rename via the tags field).
- **`/find` or `/search` command** — raw semantic search without the LLM answer, showing chunk scores and source lines. Useful for debugging retrieval.
- **`/savefile` doesn't capture vault-grounded answers** — confirmed still true: `_queue_note` is only called from the model-knowledge and web-search/supplement paths in `_process()`, never from the vault (`top_score >= SIMILARITY_THRESHOLD`) branch. So a vault-grounded Q&A can't be queued via `/savefile` — `/distill` is the only route to turn one into an article. Worth deciding if that split is intentional or should be unified.

## Retrieval

- **Inject vault file listing into prompts** — add a `--- VAULT FILES ---` section to every prompt built by ChatUI so the model always knows what files exist. Pros: model can reason about actual vault contents for any organisation/structure question, no extra retrieval step, works even for files with low embedding scores. Cons: adds ~500–1000 tokens to every prompt (scales with vault size), increases latency and token cost, potentially crowds out retrieved chunk context on models with small context windows. Alternative already implemented: `Knowledge/INDEX.md` embedded as a regular vault file — cheaper per-query but only surfaces when retrieval scores it highly enough.
- **Web search hang — fix not fully verified** — the original hang (a stalled `duckduckgo_search` connection blocking a class-question web supplement) got an `asyncio.wait_for` timeout wrapper that didn't fully resolve it, then a migration to the `ddgs` package as the real fix. The `ddgs` migration itself has never been retested against the original hang scenario. Needs a live repro to actually confirm it's fixed rather than just assumed.

## Multi-instance

- **Running multiple ChatUI instances simultaneously** — currently blocked by a PID file lock. Consider whether multi-instance is a desirable pattern: one instance per vault (different `--vault` paths), or a server mode where one background process serves multiple front-ends. Key challenges: shared `local_db/` writes would corrupt ChromaDB (it's not concurrent-write-safe), and two watchdog observers on the same vault directory would double-ingest. If multi-instance is wanted, the DB would need to move to a read-only mode for secondary instances, or ChromaDB would need to be replaced with something that supports concurrent writers (e.g. Qdrant, Weaviate).

- **Watching the tmux session while Claude Code drives it** — root cause of the TUI locking up: Claude Code drives ChatUI via `tmux send-keys` to an existing session. When the user is simultaneously attached (`tmux attach -t chatui`), both are writing to the same pseudo-terminal — input races are possible but not the core issue. The real problem is that Claude Code's polling loops (`until condition; do sleep N; done`) require explicit user approval and get rejected mid-run, leaving the pane in an indeterminate state (partial command sent, ingest or LLM call still in progress, no one consuming output). The TUI appears frozen because Textual is waiting on async work that has no one driving its event loop cleanly. **Fix when this pattern is needed:** open a second tmux window (`Ctrl+b c`) for read-only observation (`tmux attach -t chatui:1`), and keep the driving window separate. Alternatively, Claude Code should use `run_in_background: true` for any wait loops so approval prompts don't interrupt mid-flight.

## Self-update

- **`/update` function needs fine-tuning / improvement** — really, this function exists to make the iteration process easier
- perhaps the method should suggest ways of implementing changes, basic code structure, which the user can take into free online LLM models to implement by hand.

## Vault hygiene

- **Idea: consolidate all taxonomy-related notes into one `Taxonomy.md`** — considered 2026-07-02, not adopted for now. Current state: 13 files in `000-information/`, ~4,500 words total. Tradeoff discussed: merging hurts retrieval precision (chunk_size=800/top_k=5 means a query would pull cross-topic slices of one giant file instead of a tightly-scoped single-concept chunk) and collapses the `[[wikilink]]` backlink graph between sub-concepts. Lighter alternative floated instead: keep files separate, expand `Taxonomy.md` into a hub note with a one-line summary + link per sub-topic. Revisit if retrieval quality across the split files ever stabilizes and the real pain point turns out to be navigation rather than retrieval.
- **Idea: fold `conversations/` into the KB proper instead of keeping it a separate excluded folder** — noted 2026-07-03. There are currently two distinct `conversations/` locations (`ChatUI/conversations/` — Claude Code's own session transcript — and `Knowledge/conversations/` — daily ChatUI chat logs, explicitly excluded from ingest via `_discover_vault_files`). Idea: bring `Knowledge/conversations/` content into the vault proper (or a dedicated ingested location) but tag/tier it as **unrefined** — raw Q&A, not yet distilled/reviewed — so retrieval can treat it as lower-priority/supplementary rather than on par with curated articles. This is the same underlying need as a two-collection design (separate vault and conversations collections) — conversations dominated retrieval scores (0.91 vs 0.48) before being excluded outright. Any implementation should reuse that collection-tiering idea rather than just re-including conversations at equal weight, which reintroduces the original problem.
