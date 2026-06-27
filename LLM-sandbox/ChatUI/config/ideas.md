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
- cleaner text writing to the console, current version clunkily cuts off the active text
## Commands

- **`/organize` should clean up conversation logs** — condense single-command sessions and testing noise to 1-2 line summaries, the same way Claude Code did manually on 2026-06-24.
- **`/rename` file action** — `/savefile` and `/organize` let you type a new name, but there's no way to rename an existing vault file from inside chatui. Would fix the `individual-sized-cakes.md` problem (user tried to request a rename via the tags field).
- **Action mode** — chatui makes guided edits to vault files on request, not just saves new ones. E.g. "append a summary section to kinematics.md".
- **`/find` or `/search` command** — raw semantic search without the LLM answer, showing chunk scores and source lines. Useful for debugging retrieval.

## Retrieval

- **🔴 CRITICAL: ChromaDB persistence broken** — ChromaDB 1.5.9 (installed) changed the persistence API. `Chroma.from_documents(persist_directory=...)` and `Chroma(persist_directory=...)` no longer write to disk in v1.x. `local_db/` is never created; vault is in-memory only and lost on every restart. Fix: update `ingest_vault()` and `load_existing_db()` to use `chromadb.PersistentClient(path=DB_PATH)` directly, passing the client to the LangChain Chroma constructor. Confirmed 2026-06-25 — `find /home/tizz -name "chroma.sqlite3"` returns nothing.
- **Note-to-file deduplication** — before saving a new note, check for semantically similar existing files (score > 0.8) and offer to append instead of creating a new file. Fixes the "training offline LLMs" answer going to `machinelearning.md` when `language-models.md` already exists.
- **Re-ingest on change** — watch vault with `watchdog`, re-embed only changed files.
- **Smarter chunking** — chunk by markdown heading rather than character count.
- **Inject vault file listing into prompts** — add a `--- VAULT FILES ---` section to every prompt built by ChatUI so the model always knows what files exist. Pros: model can reason about actual vault contents for any organisation/structure question, no extra retrieval step, works even for files with low embedding scores. Cons: adds ~500–1000 tokens to every prompt (scales with vault size), increases latency and token cost, potentially crowds out retrieved chunk context on models with small context windows. Alternative already implemented: `Knowledge/INDEX.md` embedded as a regular vault file — cheaper per-query but only surfaces when retrieval scores it highly enough.

## Multi-instance

- **Running multiple ChatUI instances simultaneously** — currently blocked by a PID file lock. Consider whether multi-instance is a desirable pattern: one instance per vault (different `--vault` paths), or a server mode where one background process serves multiple front-ends. Key challenges: shared `local_db/` writes would corrupt ChromaDB (it's not concurrent-write-safe), and two watchdog observers on the same vault directory would double-ingest. If multi-instance is wanted, the DB would need to move to a read-only mode for secondary instances, or ChromaDB would need to be replaced with something that supports concurrent writers (e.g. Qdrant, Weaviate).

- **Watching the tmux session while Claude Code drives it** — root cause of the TUI locking up: Claude Code drives ChatUI via `tmux send-keys` to an existing session. When the user is simultaneously attached (`tmux attach -t chatui`), both are writing to the same pseudo-terminal — input races are possible but not the core issue. The real problem is that Claude Code's polling loops (`until condition; do sleep N; done`) require explicit user approval and get rejected mid-run, leaving the pane in an indeterminate state (partial command sent, ingest or LLM call still in progress, no one consuming output). The TUI appears frozen because Textual is waiting on async work that has no one driving its event loop cleanly. **Fix when this pattern is needed:** open a second tmux window (`Ctrl+b c`) for read-only observation (`tmux attach -t chatui:1`), and keep the driving window separate. Alternatively, Claude Code should use `run_in_background: true` for any wait loops so approval prompts don't interrupt mid-flight.

## Self-update

- **`/update` function needs fine-tuning / improvement** — really, this function exists to make the iteration process easier
- perhaps the method should suggest ways of implamenting changes, basic code structure, which I can take into free online LLM models to implament by hand.
- should pass through README and 

## Vault hygiene

- `taxonomy.md` — missing YAML frontmatter; `/organize` didn't tag it.

---

## Testing notes — 2026-06-25 (25-prompt taxonomy + LLM session)

**Setup:** 48 chunks ingested (vault + conversations). 25 prompts across taxonomy and LLM self-improvement topics. Session file: `2026-06-24_23-52-49.md`.

### Retrieval behaviour

- **16/24 unique prompts** hit vault (score ≥ 0.5 threshold); 9 fell back to model knowledge
- Vault scores ranged 0.41–0.77; topics already in vault (kinematics, ML basics) scored highest (0.69–0.77); new topics (Dewey Decimal, constitutional AI, knowledge graphs) scored 0.41–0.48
- **Tag scoping fired 12 times**, always correctly on `ai, machinelearning` or `physics, motion` — working as intended
- **Web search never triggered** even when model knowledge was the source. Model isn't flagging uncertainty (`"i'm not certain"` prefix) reliably on topics outside its confident range. Either the trigger phrase check is too narrow, or llama3.2:3b rarely hedges even when it should.

### Answer quality

- Vault-sourced answers were accurate but shallow — the existing notes are brief Q&A fragments, not rich reference content. The model fills in gaps but sometimes hallucinates structure (e.g. inventing Dewey class names).
- Model-knowledge answers on LLM topics (LoRA, RLHF, RAG) were solid and detailed — llama3.2:3b is well-trained on this domain.
- Cross-domain questions (kinematics → physics taxonomy, ML → CS taxonomy) produced the best answers: vault gave specific context, model connected it to the broader framework.

### Issues found

- **Web fallback not firing when it should** — `_UNCERTAIN_PREFIX = "i'm not certain"` is the only trigger. llama3.2:3b almost never produces this exact phrase. Should expand to a list of uncertainty signals: "i don't know", "i'm not sure", "i cannot", "i'm unable", "my knowledge may be", "i don't have information", or check if vault score was below threshold (fallback to model knowledge path) as a proxy for "the vault doesn't know either".
- **Duplicate prompts sent** — polling condition `grep -q "Ask anything"` matches the input placeholder which is always visible. Need to poll on session file growth + "Source:" appearing instead. (Bug in testing harness, not in chatui.)
- **`/savefile` not prompted after 25 model-knowledge answers** — all answers that used model knowledge queued as pending notes, but no `/savefile` was run. These would be lost when the session ends. Consider auto-prompting `/savefile` reminder when pending count exceeds a threshold (e.g. 5).
- **Conversation chunks in DB are large and noisy** — ✅ fixed 2026-06-27: conversations excluded from ingest entirely. They dominated retrieval for repeated questions (scoring 0.91 vs 0.48 for actual vault articles). Conversations earn their way into the knowledge base via `/distill` → vault articles instead. Long-term: two-collection design (separate `vault` and `conversations` collections) would allow conversations as a low-priority supplementary source without dominating.
- **48 chunks for 7 vault files + 2 conversation files is surprisingly low** — with chunk_size=500 and the rich answers generated today, more content should exist. Suggests answers generated in this session aren't yet in the DB (session file was written after ingestion).

### Recommendations

- Run `/ingest` again at end of any testing session so newly written conversation content is embedded for future queries.
- Expand uncertainty detection beyond exact prefix match.
- Consider a `/savefile` auto-reminder after N pending notes.
- Evaluate whether conversation files should be a separate lower-weight collection in ChromaDB rather than mixed with vault notes.

---

## Testing notes — 2026-06-27 (knowledge organisation session)

**Setup:** 368 chunks. Topics: faceted classification, polyhierarchy, controlled vocabularies. New articles written: `faceted-classification.md`, `polyhierarchy.md`, `controlled-vocabularies.md`. Vault INDEX.md added.

### Retrieval quality progression on "suggest a folder structure for Knowledge/"

| State | Score | Source | Answer quality |
|---|---|---|---|
| Before tag parser fix | 0.48 | untagged articles | Generic business structure |
| After tag fix | 0.91 | conversation logs | Echoed previous session answer |
| With conversations excluded | 0.53 | humanities-spectrum.md | Taxonomy-aware but doesn't know vault files |
| With INDEX.md + new articles | 0.62 | INDEX.md + taxonomy articles | References real vault topics, reasonable structure |

### Issues found

- **`/savefile` doesn't capture vault-grounded answers** — notes only queue when score < threshold (pure model knowledge path). Answers grounded in vault context are never queued, so you can't use `/savefile` to save conversational Q&A sessions as articles. Workaround: write articles directly or use `/distill`. The two approaches serve different purposes but this distinction isn't obvious to new users.
- **Watchdog auto-reingest of conversations** — ✅ fixed 2026-06-27: added `"conversations"` to `_VaultEventHandler._SKIP`. Previously, every chat turn re-ingested the session file into ChromaDB, silently re-adding conversation chunks after a clean `/ingest`.
- **Model conflates LCC/Dewey with faceted classification** — llama3.2:3b incorrectly attributed faceted classification to hierarchical library systems. The model's training data may conflate "library classification" as a category. Manually corrected in `faceted-classification.md`. Suggests model-generated vault articles need a human review pass before ingestion.
- **Polyhierarchy blocked by vault context** — when the vault (via conversation log) said "I don't know about polyhierarchy," the model refused to use its own knowledge even when the question defined the term explicitly. Resolved by fixing watchdog `_SKIP` and restarting, but reveals that model over-anchors to retrieved context saying "I don't know".
- **INDEX.md helps domain but not file-level** — the model correctly scoped to taxonomy/index tags and referenced vault topics, but didn't read the actual file table to suggest structure based on real filenames. llama3.2:3b appears to synthesise themes rather than parse tables. Larger model or injected file listing would close this gap.

### Recommendations

- Add a human review / quality note field to `/distill`-generated articles flagging uncertain attributions.
- Investigate whether a system-prompt file listing (option 2 from ideas.md) would let the model name actual vault files in organisation answers.
- The "model knowledge anchoring" problem (over-deferring to "I don't know" in retrieved context) may warrant a retrieval filter: if the top chunk's content explicitly says it lacks the requested information, fall through to the grounded or pure-model path instead.

