---
summary: Full history of changes to chatui.py — both Claude Code direct edits and self-update pipeline directives.
---

# Changelog

Two sources of change, both recorded here:
- **claude** — direct edits made by Claude Code in a session
- **pipeline** — CHANGE:/FIX: directives applied via `/update`+`/apply` or `apply_update.py`

See `conversations/claude_transcript.md` for the full session context behind each entry.

---

## 2026-06-24

| Source | What | Why | Commit(s) |
|--------|------|-----|-----------|
| claude | Initial chatui.py rewrite — Textual TUI, /command interface, session auto-save | Replace the script-style obsidian_brain.py with a full terminal app | `ed43ff2` |
| claude | Add /browse, streaming responses | UX — navigate vault files as context; responses feel instant | `2ae50cf` |
| claude | Add config/ system, model separation, /update groundwork | Separate tuneable params from code; foundation for self-update | `6434e08` |
| claude | /update pipeline v1 (unified diff approach) | Let the app modify itself from config changes | `02956ea`→`f5a6725` |
| claude | **Rewrite /update pipeline** — git diff + surgical AST edits + ast.parse validation | v1 used line-numbered unified diffs which OOM'd on 14b model and broke on any mis-numbering; new approach sends only the relevant function block (~30 lines) to a 7b model | `0edbf91` |
| claude | /version command generated end-to-end via /update + /apply | First live test of new pipeline | `8bd14b4` |
| claude | Update README; clean up models.md (remove qwen2.5-coder:14b) | README was stale; 14b model caused the OOM crash | `875d844` |
| claude | /web state in header; fuzzy command matching; /status command; fix /version help line | UX issues spotted from reviewing 40 session logs | `0001e59` |
| pipeline | All `/command` output appended to session log files | Commands left no trace in conversation history | `1b8502c` |
| claude | Include `conversations/` in ChromaDB ingestion | Session logs contain useful context for retrieval | `23db904` |

## 2026-06-25

| Source | What | Why | Commit(s) |
|--------|------|-----|-----------|
| claude | UI overhaul: busy-bar loading indicator, wider margins, /stats command | Users couldn't tell if app was processing; layout ran wall-to-wall | `7fe0492` |
| claude | Smarter chunking (MarkdownHeaderTextSplitter); note deduplication (similarity ≥ 0.85 → append); --vault CLI arg; fix /organize + /apply not saving to log | Chunking by character boundary split mid-sentence; duplicate notes accumulated | `fca3189` |
| claude | Granular status labels ("Searching vault…" etc.); vault answers show source file attribution | Generic "📓 Source: vault notes" gave no useful signal | `35be41e` |
| claude | /edit command (guided file edits via LLM diff); /daily command (session summary → daily.md) | Pipeline for improving vault notes from inside the app | `9243236` |
| claude | Watchdog auto-reingest on vault file change; /export training data (jsonl/alpaca/csv) | Avoid manual /ingest after every edit; enable model fine-tuning | `a200842` |

## 2026-06-26

| Source | What | Why | Commit(s) |
|--------|------|-----|-----------|
| claude | LLM-efficient session format: YAML frontmatter, HTML comment audit trail, INDEX.md | Scanning conversations/ was token-heavy; needed a compact one-line-per-session index | `2e663aa` |
| pipeline | Add /readme command | Regenerate README from live source so it stays accurate as commands evolve | `39d9fdb` |
| pipeline | Add /harvest command | Promote conversation topics into vault stubs automatically | `39d9fdb` |
| pipeline | FIX _cmd_harvest — strip interrogative starters; add fuzzy vault matching | Harvest creating topics like "What is fine-tuning" instead of "fine-tuning" | `61a22b1` |
| claude | Fix two micro-bugs in harvest (direct): leading-space broke ^ anchor; comma-split fragmented compound topics | Pipeline applied the fix but model missed these edge cases | `9af06a4` |
| pipeline | FIX _cmd_harvest — 2-word concept name extraction; strip articles + trailing connectors | Slugs like "fine-tuning-in-the-context-of-large-lang.md" were useless filenames | `33d9d30` `5c0f604` |
| claude | Add self-review pass to apply_update.py; improve decorator/indent handling | First-pass fixes had ~20% error rate (dropped decorators, wrong indentation) | `940ae25` `e54064e` |
| pipeline | FIX _directive_model_guided — broaden context regex to any `_func_name` | FIX directives for non-`_cmd_*` functions (e.g. _finalize_session) had no context | `7c9fd72` |
| pipeline | FIX _generate_new_method — add self-review pass to TUI pipeline | Self-review existed in apply_update.py but not in the TUI /update+/apply flow | `7c9fd72` |
| pipeline | FIX _cmd_harvest — add `slug in stem` substring fallback | "math" (4 chars, below fuzzy threshold) wasn't matching Mathematics.md | `7c9fd72` |
| pipeline | FIX ingest_vault — exclude conversations/INDEX.md from ChromaDB | INDEX is navigation metadata, not knowledge; was polluting retrieval results | `7c9fd72` |
| pipeline | FIX _finalize_session — LLM keyword extraction for topics field | Regex strip still produced low-quality topic strings | `1b6d28c` |
| claude | Fix _finalize_session [:4] slice bug in pipeline-generated code | Model wrote `"; ".join(...)[:4]` (string slice) instead of `items[:4]` (list slice) | `1b6d28c` |
| claude | apply_update.py: race guard (skip if block already replaced); broaden fn-name regex to snake_case; flush=True on all prints | Two parallel runs could both apply same FIX; non-`_` functions had no context; output was invisible during long LLM calls | `7c9fd72` `1b6d28c` |
| claude | Track conversations/ in git; add .chatui_sync to .gitignore | Session logs and transcript should be versioned; sync hash is machine-local state | `ab4eec3` |
| claude | **Fix ChromaDB persistence** — swap to `chromadb.PersistentClient` + `collection_name="vault"` | ChromaDB v1.x dropped `persist_directory=` API; local_db/ was never written to disk, vault lost on every restart | `bac2cce` |
| claude | Rename `Machine Learning.md` → `machine-learning.md` | Spaces in filenames break shell tools and wikilinks | `bac2cce` |
| claude | Delete obsidian_brain.py, ChatUI.md, test.txt, "first file!.md" | Dead code and junk files cluttering vault root | `bac2cce` |
| claude | Clean settings.md — move applied directives to changelog.md; fix stale Architecture section | settings.md had 16 applied directives buried in it; Architecture section described old patch-based pipeline | `bac2cce` |
| claude | Add /distill command — extract Q&A pairs from a session file, bootstrap `_article-guide.md` if missing, generate structured articles with taxonomy-aware YAML tags and [[wikilinks]], append to existing vault files | Core workflow: conversation logs → rich vault articles that expand over time | `ef3094c` |
| claude | /distill first run — 24 vault articles generated from session `2026-06-24_23-52-49`; fix prompt bugs: strip raw Q&A artifact lines from source, tighten wikilink constraint to vault-only stems, add frontmatter fallback | First live run exposed prompt contamination and broken wikilinks | `42aca01` |
| claude | Fix /distill frontmatter — strip model-generated `---` blocks, generate title + tags programmatically from slug + keyword map; add `_distill_tags()` helper; retag all 22 existing articles | llama3.2:3b consistently produced unclosed frontmatter; hyphen-vs-space mismatch in keyword map caused most articles to fall through to `[general]` | `95a7340` |
| pipeline | Add FIX directives to settings.md — wikilink post-filter in /distill; RAG grounding for article generation | Articles linked to non-existent vault pages; content drifted from source material | `61f0b43` |
| claude | Vault pre-seeding: 6 reference files (`_ref-lora.md`, `_ref-rlhf.md`, `_ref-fine-tuning.md`, `_ref-rag.md`, `language-models.md`, `machine-learning.md`); quality fixes to 7 articles (corrected LoRA mechanism, RLHF pipeline, frontmatter); /distill wikilink post-filter — strip `[[X]]` where X doesn't match any vault stem | Articles had factual errors (e.g. LoRA description was backwards); wikilinks pointed to non-existent pages | `ba0202d` |

## 2026-06-27

| Source | What | Why | Commit(s) |
|--------|------|-----|-----------|
| claude | `_cmd_ingest` updated for new `ingest_vault(force) -> tuple[Chroma, dict]` return signature; displays granular stats (new/updated/removed/unchanged counts) | Signature change from prior session caused a crash on /ingest | `4a40d3f` |
| claude | `vault-structure-plan.md` created — full Dewey hierarchy, current file placement, tag→folder mapping table, deviation rationale, `_ref-*` special case | Living document for vault organisation; ingestible so the model can answer structure questions | `4a40d3f` |
| claude | Pass 4 added to `_run_organize()` — file placement using Dewey-based folder structure; `_needs_placement()`, `_classify_for_placement()` helpers; `_TAG_TO_FOLDER`, `_DEWEY_FOLDERS`, `_PLACEMENT_SKIP_TAGS` constants | Vault files were accumulating at root with no folder structure | `780530f` |
| claude | `_run_organize()` scan fixed — changed from `glob.glob(VAULT_PATH/*.md)` to `_discover_vault_files()` so subdirectory files are included | Pass 1 was skipping all files that had already been moved into subfolders | `780530f` |
| claude | Merge 15 per-minute session files into 2 daily files (`2026-06-24.md`, `2026-06-27.md`); ChatUI `on_mount` updated to append to a single `YYYY-MM-DD.md` per day | Session files were split by the minute; hard to navigate and redundant | `bb13670` |
| claude | `_finalize_session` recognises `YYYY-MM-DD.md` pattern; `_rebuild_conversation_index` counts sessions per daily file; `_cmd_daily` reads single daily file | Supporting changes for daily-file format | `bb13670` |
| claude | Update claude_transcript through Session 9; delete stale duplicates (`claude_transcript 1.md`, `INDEX 1.md`) | Transcript was out of date; duplicate files from Obsidian sync | `fdf9fd4` |

## 2026-06-28

| Source | What | Why | Commit(s) |
|--------|------|-----|-----------|
| claude | Project assessment — identified structural duplication (two chatui.py copies, two vault locations), broken `vault_path`, two pending FIX directives | Full audit of project state with three-phase remediation plan | _(no commit)_ |
| claude | Move canonical code to `ChatUI/`; delete stale root copies of `chatui.py`, `apply_update.py`, `_article-guide.md`, `docker-compose.yml` | Root copies were 262 lines behind ChatUI/ and diverging | _(this commit)_ |
| claude | Rename all 37 `Knowledge/*.md` files from kebab-case to Title Case with Spaces; `_ref-*` → `_Ref Title Case` | Consistent naming convention matching Obsidian display style | _(this commit)_ |
| claude | Update `chatui.py` line 1653: `"taxonomy.md"` → `"Taxonomy.md"` | Hardcoded filename reference broke after vault rename | _(this commit)_ |
| claude | Delete `ChatUI/config/` duplicates: `Changelog 1.md`, `Commands 1.md`, `Models 1.md`, `Settings 1.md`, `Improvement Notes.md` | Obsidian sync created versioned duplicates; `ideas.md` was already the superset | _(this commit)_ |
| claude | Merge all 17 divergent root `.md` files into `Knowledge/` counterparts (append unique content), then delete root copies | Root was the old flat vault; `Knowledge/` is now the single canonical vault location | `d04811c` |
| claude | Add `llama3.1:8b` as default `chat_model`; both models in auto-pull registry; `/model [name]` runtime switcher — swaps `llm` globally, updates header subtitle via `self._chat_model` | 8b gives ~3× capacity over 3b for same disk footprint as coding model | `39a1c21` |
| claude | Retrieval config: `top_k 3→5`, `chunk_size 500→800`, `chunk_overlap 50→100` | Larger Knowledge/ articles split mid-section at 500 chars; 3 chunks allowed crowding-out | `39a1c21` |
| claude | Fix web fallback — remove `uncertain` phrase gate; web now fires whenever in model-knowledge path and web is on | `llama3.2:3b` almost never emits `"i'm not certain"` so fallback never triggered | `39a1c21` |
| claude | Raise `similarity_threshold` 0.5→0.65; lower `history_window` 4→2; update `build_vault_prompt` to allow training-knowledge supplement | 8b model was false-positive matching AI-adjacent questions at 0.55–0.63 (vault path fired, bypassing web); history_window=4 caused RLHF answer to contaminate next EU-regulation query; vault prompt said "say so clearly" when context insufficient, causing model refusal | `a877541` |
| claude | Fix `build_grounded_prompt`: answer-first from training knowledge; include vault notes only if directly relevant | Grounded path was blending off-topic vault chunks (EU regulation answer got Constitutional AI tail from `Agential Patterns.md` at score 0.60) | `4344119` |
| claude | Create `CLAUDE.md` — repo layout, constraints, self-update docs, end-of-session checklist, retrieval table, common pitfalls | No project context file existed; each session re-derived structure from git log | `3aafc44` |
| claude | Rewrite `README.md` — update default model to llama3.1:8b, add `--vault` flag, full command list, retrieval pipeline, stack table | README was stale: wrong default model, missing /model and /distill, no retrieval docs | `3aafc44` |
| claude | Add `Stop` hook to `~/.claude/settings.json` — warns at session end if transcript/changelog/README not updated | Prevent checklist items from being forgotten across sessions | `3aafc44` |
| claude | Fix 9 command bugs found during audit: `/help` markup (`[name]`/`[[links]]` stripped by Rich); `_apply_queue` swallowing `/commands`; `/readme` destructive overwrite; `/model` silent bad-name accept; `/status`+`/stats` merged; `/export` duplicate line; `/distill` lists sessions; `/harvest` clearer error; `/daily` acknowledges existing file | Full command audit identified rendering bugs, silent failures, and UX gaps | `21c9e4a` |
| claude | Apply pending `/distill` directive: RAG grounding — query vault per Q&A pair before building `art_prompt`, inject top-2 chunks (score ≥ 0.45) as "REFERENCE MATERIAL" block; directive 1 (wikilink filter) was already implemented in Session 7 | Directive had been in `settings.md` since `61f0b43`; bypassed git-diff pipeline since commit predated any usable sync hash | `4ee93fd` |
| claude | Fix two bugs blocking vault folder structure: (1) `_cmd_distill` `os.listdir` → `_discover_vault_files()` for post-move wikilink resolution; (2) `_is_ref()` helper to detect `_Ref Title Case` filenames (not just `_ref-`) | Both would have silently broken after files moved to subfolders | `00cf05d` |
| claude | Run `/organize`: wikilinks added to `Natural Sciences.md`, `Social Science Subfields.md`; all 42 files placed into Dewey subfolders; 4 `_Ref` files to `600-applied-sciences/_ref/`; Cupcakes corrected to `misc/`; Pass 3 bug fixed (INDEX.md excluded from condense candidates); ChromaDB rebuilt at 309 chunks | vault-structure-plan.md implemented | `46f87ad` |

## 2026-07-02

| Source | What | Why | Commit(s) |
|--------|------|-----|-----------|
| claude | Fix `/distill`: articles now routed through `_classify_for_placement` into the correct Dewey folder instead of always landing in `VAULT_PATH` root; filename and frontmatter `title` now derived from the topic slug in Title Case With Spaces instead of `slug + ".md"` and the raw question text | `/distill` produced `classification-standards--library-systems--subject.md` in the vault root with the raw question as its title — violated both the vault's filing convention and `_article-guide.md` rule 5 | _(this commit)_ |
| claude | Widen tag-scoped retrieval pass from `k=TOP_K` to `k=TOP_K * 2` (chatui.py:2870) | Once a query narrows to one tag, a 12+ file topic cluster (e.g. taxonomy) could still only surface ~5 files at the old `k`; direct DB query confirmed relevant files (Faceted Classification, Polyhierarchy, Taxonomy Mappings) were losing the retrieval lottery to less relevant chunks purely on count | _(this commit)_ |
| claude | Add See Also specificity instruction to `/distill` article prompt — prefer notes on the same specific subtopic over notes sharing only a broad field | Distilled articles were linking weakly-related notes over more specific existing ones | _(this commit)_ |
| claude | Delete misfiled `classification-standards--library-systems--subject.md` | Content was a near-total duplicate of `Library of Congress Classification System.md` and `Folksonomy Differences.md`; relocating it would have kept the duplication, not fixed it | _(this commit)_ |
| claude | Rewrite `000-information/INDEX.md` — reflect actual `000/300/500/600/misc` folder split and current Title Case filenames | Previous INDEX.md still listed pre-reorg lowercase-dash filenames from before the Session 16 vault restructure; gets embedded and retrieved, so it was feeding stale context into answers | _(this commit)_ |
| claude | Log consolidate-all-taxonomy-into-one-file idea in `config/ideas.md` (not adopted) | User proposed it; recommended against due to retrieval/backlink tradeoffs, kept for later reconsideration | _(this commit)_ |
| claude | Fix stale venv path in `CLAUDE.md` run instructions (`../.venv` → `.chat_venv`) | Actual venv is `ChatUI/.chat_venv`; the documented path no longer existed | _(this commit)_ |
| claude | Harden `web_search()` call sites with `asyncio.wait_for(timeout=20)` plus explicit `CancelledError`/`Exception` handling | Class-question auto-web-supplement hung indefinitely on a stalled DDG connection; fix did not fully resolve the hang (see testing notes in `ideas.md`) but improves failure visibility | _(this commit)_ |
| claude | Delete 3 duplicate/mis-named `/distill` articles (`Local Regularization Technique.md`, `Classification Systems.md`, `Library Classification.md`) and consolidate 2 near-duplicate RDF/OWL articles into one `Semantic Web And Ontologies.md`; rename `Graph Vs Taxonomy.md` → `Knowledge Graph vs Taxonomy.md` | `/distill` has no cross-file dedup (unlike `/savefile`'s 0.85-similarity check) and is not idempotent across repeated runs on the same session file — see `ideas.md` testing notes | _(this commit)_ |
| claude | Add `Knowledge Graph vs Taxonomy.md` and `Semantic Web And Ontologies.md` to `000-information/INDEX.md` | New genuinely-new-topic articles from overnight testing session | _(this commit)_ |

## 2026-07-03

| Source | What | Why | Commit(s) |
|--------|------|-----|-----------|
| claude | Add semantic-similarity dedup to `/distill` (same pattern as `save_to_vault`'s dedup for `/savefile`), threshold tuned to 0.7 from a direct measurement rather than copying `/savefile`'s 0.85 (which never fired for this query shape — true duplicates measured ~0.69) | `/distill` had no dedup at all, unlike `/savefile` | `832c65c` |
| claude | Add `<!-- distilled -->` marker insertion so `/distill` is idempotent across repeated runs on a growing session file | Re-running `/distill` on the same file reprocessed all Q&A pairs from scratch every time, regenerating duplicate articles under new hallucinated names each run | `832c65c` |
| claude | Migrate `web_search()` from `duckduckgo_search` (deprecated upstream) to `ddgs` | Package renamed upstream; `ddgs` is the maintained successor with a compatible `DDGS` API | `832c65c` |
| claude | Add `_validate_wikilinks()` — normalises `[[wikilinks]]` against real vault stems (hyphens/spaces/case) and rewrites stale ones; wired into `/organize` as Pass 5 | No existing mechanism validated existing wikilinks, only added new ones | `832c65c` |
| claude | Ran `_validate_wikilinks()` directly against the vault: fixed 58 stale wikilinks across 24 files | Pre-rename kebab-case links (`[[fine-tuning-methods]]`, `[[taxonomy]]`, etc.) were broken since the Session 16 Title Case migration — far more widespread than the ~6-file estimate from the prior session's finding | `832c65c` |
| claude | Cleaned up 9 duplicate `/distill` articles generated while validating the dedup fix; trimmed two redundant "Additional notes" appendices from `Knowledge Graph vs Taxonomy.md` | Live validation run confirmed the threshold-tuning finding before the code fix was live | `832c65c` |
| claude | Research session: 8 Q&A pairs on browsable databases (Wikipedia category graph, Google crawl/index/rank, faceted search, B-trees, inverted indexes); distilled into 8 vault articles in `000-information/` and `600-applied-sciences/`; exported 39 Q&A pairs to `training_data.jsonl` | Grow vault coverage on information retrieval fundamentals | `c8d89e6` |
| claude | Fix `/distill` article quality: increase `guide_ctx` read cap `[:700]`→`[:2000]`; inject `guide_ctx` into `art_prompt` as leading "ARTICLE WRITING GUIDE" block; replace vague FORMAT line | `guide_ctx` was loaded but never used — the article guide had zero effect on generated output | _(this commit)_ |
| claude | Add four anti-patterns to `_article-guide.md`: no Q&A format output, no "I couldn't find" responses, no verbatim source reproduction, no invented facts | These are the failure modes visible in broken articles like `Taxonomy.md` | _(this commit)_ |
| claude | Add shared guided-review framework: `Proposal` dataclass, `ChatApp._review()` controller, `ProposalEditScreen` modal (Textual `TextArea`); wire into `/organize` Passes 1/2/4/5 (tags, wikilinks, placement, wikilink-fix) and `/distill`'s article-write step | Implements the `ideas.md` General-section proposal to replace hard-coded automated passes with a guided accept/skip/edit/all/none review; `/distill` previously wrote articles with no review step at all, a root cause of inconsistent article quality | _(this commit)_ |
| claude | Add `config/organize_feedback.md` log + `_log_organize_feedback()`/`_load_organize_feedback()`; inject past-correction context into the tag, wikilink, and placement suggestion prompts | Closes the loop the idea asked for: manual overrides during review should improve future suggestions, not just be silently accepted | _(this commit)_ |
| claude | Phase 2: split-pane review UI — `compose()` restructured into `#main-body` (`Horizontal`) with a docked `#review-panel` (`ListView` + detail `Static`, hidden by default) on the left and the existing chat in `#chat-pane` on the right; `_review()` now populates the panel with the whole batch up front and updates per-row status icons (pending/accepted/skipped/edited) live; clicking the active row is equivalent to typing `edit` | Delivers the "chat on the right, file/organization menu on the left" layout from the original idea; a pure rendering layer on top of the Phase 1 `Proposal` model, no interaction-logic changes needed | _(this commit)_ |
| claude | UI refinement pass on Phase 2: fix `MissingStyle` crash (any `proposal.kind`/`[[wikilink]]` text read as an invalid Rich style tag by `Static.update`'s markup parser — every review-panel row was affected); fix phantom horizontal scrollbar on `#log` once the review panel narrows it (`RichLog`'s 78-col `min_width` floor, plus `overflow-x: hidden` as a second line of defense); fix `ProposalEditScreen`'s help line being clipped off-screen (fixed-height `TextArea` overran the modal box once header/help margins were counted — switched to `height: 1fr`); fix silent corruption of `[[wikilink]]` text in the existing chat-log display (same markup-parsing issue, present before Phase 1/2 but only now caught) | Found by actually rendering the UI (Textual `export_screenshot()` → SVG → PNG) instead of only driving it with assertion-based pilot tests, which never forced a real paint and so never triggered the crash | _(this commit)_ |
| claude | Tidied `config/ideas.md` — removed ~130 lines of resolved/stale content (superseded by `changelog.md`/`claude_transcript.md`), pulled the still-genuinely-open threads forward (verified each against the current code rather than assumed) | User asked for a cleanup pass; the file had accumulated a full session-testing history alongside the actual backlog, most of it already resolved | _(this commit)_ |
| claude | Fix `/organize` looking frozen during LLM generation — `_cmd_organize` never called `_set_busy(True, ...)`, so the busy-bar (used everywhere else in the app) stayed invisible for the entire run; add `ChatApp._await_with_progress()` helper that ticks an elapsed-time counter onto the busy-bar during any single long `await`, wired into Pass 1's batched tag call, Pass 2/4's per-item loops (with "(i/N)" + filename), Pass 3's per-session summary, and `/distill`'s article-generation call | User watched a live `/organize` run sit at "Scanning for wikilink opportunities…" for minutes with zero feedback and flagged it as the same complaint already logged in `ideas.md`'s UX section | _(this commit)_ |
| claude | Add upfront checkbox file picker to `/organize` — `ChatApp._pick_files_to_organize()` shows a checkbox list in the review panel before Pass 1, pre-checking files missing frontmatter or unplaced (`[unorganized]` tag), `all`/`none`/`unorganized` bulk commands plus per-row click toggling; `selected_stems` gates Pass 1/2/4's iteration while `notes`/Pass 2's wikilink-target pool stays built from the full vault (avoids narrowing valid link targets down to just the selection) | Closes the other half of the `ideas.md` guided-`/organize` idea — Phase 1+2 shipped the review step but `/organize` still unconditionally processed every vault file with no way to scope a run | _(this commit)_ |
