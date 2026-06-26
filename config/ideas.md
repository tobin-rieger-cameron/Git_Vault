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
- **Conversation chunks in DB are large and noisy** — daily log and claude-code transcript are now embedded alongside vault notes. They score as "vault matches" for almost any query due to broad vocabulary coverage, potentially pushing out more relevant dedicated notes. May want to exclude certain conversation files from ingestion, or weight them differently.
- **48 chunks for 7 vault files + 2 conversation files is surprisingly low** — with chunk_size=500 and the rich answers generated today, more content should exist. Suggests answers generated in this session aren't yet in the DB (session file was written after ingestion).

### Recommendations

- Run `/ingest` again at end of any testing session so newly written conversation content is embedded for future queries.
- Expand uncertainty detection beyond exact prefix match.
- Consider a `/savefile` auto-reminder after N pending notes.
- Evaluate whether conversation files should be a separate lower-weight collection in ChromaDB rather than mixed with vault notes.

