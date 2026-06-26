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
| claude | **Fix ChromaDB persistence** — swap to `chromadb.PersistentClient` + `collection_name="vault"` | ChromaDB v1.x dropped `persist_directory=` API; local_db/ was never written to disk, vault lost on every restart | _(this session)_ |
| claude | Rename `Machine Learning.md` → `machine-learning.md` | Spaces in filenames break shell tools and wikilinks | _(this session)_ |
| claude | Delete obsidian_brain.py, ChatUI.md, test.txt, "first file!.md" | Dead code and junk files cluttering vault root | _(this session)_ |
| claude | Clean settings.md — move applied directives to changelog.md; fix stale Architecture section | settings.md had 16 applied directives buried in it; Architecture section described old patch-based pipeline | _(this session)_ |
| claude | Add /distill command — extract Q&A pairs from a session file, bootstrap `_article-guide.md` if missing, generate structured articles with taxonomy-aware YAML tags and [[wikilinks]], append to existing vault files | Core workflow: conversation logs → rich vault articles that expand over time | _(this session)_ |
