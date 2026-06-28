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
