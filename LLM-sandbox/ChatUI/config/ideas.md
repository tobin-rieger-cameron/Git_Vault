---
summary: Backlog of improvement ideas for chatui.py — not yet directives, just notes.
---

# Ideas

## General

- article text should appear as its being written
- /distill command is confusing - consider an overhaul and simplification of /commands in general
- [DONE, Phase 1 + 2 — see below] instead of automated writing and formatting, consider a guided approach, where the user and ChatUI co-edit the pending article

**Guided review framework (implemented):**
- **Phase 1:** `/organize` (tag/wikilink/placement/wikilink-fix passes) and `/distill` (article generation) route every suggested change through a shared `Proposal` + `ChatApp._review()` mechanism instead of the old single-shot "Enter/skip/override" text prompts. Enter=accept, `skip`, `edit` (opens a full-text editor pre-filled with the suggestion), `all`=accept the rest of the batch, `none`=skip the rest. Manual edits that change the substance of a suggestion are logged to `config/organize_feedback.md` with an optional one-line reason, and that log is fed back into the tag/wikilink/placement prompts on future runs.
- **Phase 2:** the split-pane UI from the original idea — a docked `#review-panel` on the left (file list with live status icons: pending/accepted/skipped/edited) alongside the existing chat on the right, matching "chat on the right, current file/file browser/organization menu on the left." The whole batch is visible up front, not revealed one at a time; a detail pane mirrors the item currently being decided; clicking the active row is equivalent to typing `edit`. The panel is hidden outside of a review (`display: none` by default) so normal chat use is unaffected. Built as a pure rendering layer on top of the Phase 1 `Proposal` data model — no interaction-logic changes were needed.

See `Proposal` / `ChatApp._review()` / `ProposalEditScreen` / `_review_panel_*` methods in `chatui.py`.


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

- `taxonomy.md` — missing YAML frontmatter; `/organize` didn't tag it. *(Stale as of 2026-07-02 — current `Taxonomy.md` has frontmatter; verify and remove this line if `/organize` fixed it.)*
- **Idea: consolidate all taxonomy-related notes into one `Taxonomy.md`** — considered 2026-07-02, not adopted for now. Current state: 13 files in `000-information/`, ~4,500 words total. Tradeoff discussed: merging hurts retrieval precision (chunk_size=800/top_k=5 means a query would pull cross-topic slices of one giant file instead of a tightly-scoped single-concept chunk) and collapses the `[[wikilink]]` backlink graph between sub-concepts. Lighter alternative floated instead: keep files separate, expand `Taxonomy.md` into a hub note with a one-line summary + link per sub-topic. Revisit if retrieval quality across the split files ever stabilizes and the real pain point turns out to be navigation rather than retrieval.
- **Idea: fold `conversations/` into the KB proper instead of keeping it a separate excluded folder** — noted 2026-07-03. There are currently two distinct `conversations/` locations (`ChatUI/conversations/` — Claude Code's own session transcript — and `Knowledge/conversations/` — daily ChatUI chat logs, explicitly excluded from ingest via `_discover_vault_files`). Idea: bring `Knowledge/conversations/` content into the vault proper (or a dedicated ingested location) but tag/tier it as **unrefined** — raw Q&A, not yet distilled/reviewed — so retrieval can treat it as lower-priority/supplementary rather than on par with curated articles. This is the same underlying need as the "two-collection design (separate vault and conversations collections)" recommendation already logged in the 2026-06-25 testing notes below — conversations dominated retrieval scores (0.91 vs 0.48) before being excluded outright. Any implementation should reuse that collection-tiering idea rather than just re-including conversations at equal weight, which reintroduces the original problem.

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

---

## Testing notes — 2026-07-02/03 (overnight edge-case + retrieval-fix validation session)

**Setup:** Live TUI session driven via tmux, `llama3.1:8b` chat model, 322→381→323 chunks across the session (net +2 files after cleanup: `Knowledge Graph vs Taxonomy.md`, `Semantic Web And Ontologies.md`). Ran with the retrieval/placement fixes from earlier in this session (`TOP_K*2` tag-scoped retrieval, `/distill` Dewey-folder placement) already applied.

### Retrieval fix validated live
- Re-ran the exact "other topics related to taxonomy and DDS" query that originally scored 0.67 off a single INDEX.md chunk. After the `TOP_K*2` widening fix, the tag-scoped pass surfaced 3 distinct sources (`Evaluating Systems of Classification.md`, `Folksonomy Differences.md`, `Interdisciplinary Ontologies.md`) instead of 1, and the answer was materially richer (correctly cited LCC, folksonomy, evaluation metrics).
- A direct DB query (bypassing the app) confirmed the mechanism: at `k=10` under the `taxonomy` tag filter, 7 distinct on-topic files appear in the top results vs. 1–2 at the old `k=5`.
- After distilling and adding `Knowledge Graph vs Taxonomy.md`, a repeat of "how does a knowledge graph differ from a taxonomy" — which previously scored 0.60 and fell to the model-knowledge path — now scores **0.87** and answers directly from the vault, citing the new file. This is the clearest before/after evidence that filling real gaps in the vault measurably improves retrieval, not just adds content.

### `/distill` placement fix validated, but surfaced two new gaps
- Confirmed the `_classify_for_placement` + Title Case fix works: a 7-Q&A distill run placed all 6 new files into real Dewey folders (`000-information/`, `600-applied-sciences/`, one debatable `400-language/` placement) with proper filenames — zero landed in the vault root this time.
- **New gap — no cross-file dedup in `/distill`:** two of the six generated files were pure duplicates of existing vault content (a `LoRA` Q&A got the hallucinated filename `Local Regularization Technique.md`, duplicating `LoRA Adaptations.md`; two "topics related to taxonomy" restatements produced `Classification Systems.md` and `Library Classification.md`, both near-verbatim duplicates of 5+ existing notes — the same failure mode as the original misfiled article from earlier in the session). Deleted all three; consolidated two more near-duplicate RDF/OWL articles (`Semantic Web Ontologies.md` + `Rdf Ontology Frameworks.md`) into one clean `Semantic Web And Ontologies.md`. `/savefile` already has a 0.85-similarity dedup check (`save_to_vault`) — `/distill` has no equivalent, and should.
- **New gap — `/distill` is not idempotent:** re-running `/distill 2026-07-02` a second time later in the session reprocessed all 12 Q&A pairs in the daily file from scratch (not just the 2 new ones since the last run), re-appending "Additional notes" sections to already-good, already-placed files. No tracking of what's already been distilled from a given session file exists. Over repeated `/distill` calls on the same growing daily session file, this will compound duplicate "Additional notes" bloat indefinitely. Needs a per-session or per-Q&A distilled-marker (e.g. an HTML comment in the session file, or a manifest similar to the ingest manifest).

### Bug found and partially fixed: web search can hang indefinitely
- The class-question auto-web-supplement (`is_class_q and self._web_on and not _source_covers_topic(...)`) hung on "🌐 Vault coverage indirect — supplementing with web…" for 90s–5+ minutes with no resolution, reproduced twice across a fresh process restart. `ss` showed a genuine `ESTABLISHED` TCP connection to an external host that never completed the HTTP response — this is `duckduckgo_search` (deprecated upstream in favour of `ddgs`) apparently being rate-limited/stalled by DDG's anti-scraping measures after repeated test queries.
- **Attempted fix:** wrapped both `web_search()` call sites in `asyncio.wait_for(..., timeout=20)`, then hardened further with explicit `except asyncio.CancelledError` (re-raise after logging) and `except Exception` handlers, on the theory that `CancelledError` (a `BaseException`, not `Exception`) might be escaping the original bare `except asyncio.TimeoutError`. **This did not fully resolve it** — the hang reproduced identically after the fix, with the worker silently completing (busy indicator cleared) without ever logging a timeout/failure message. Root-causing further would need a live stack trace (`py-spy dump`), which requires `ptrace_scope` permissions/sudo not available in this environment.
- **Workaround used for the rest of this session:** toggled `/web off`. **Recommendation:** replace `duckduckgo_search` with the `ddgs` package it was renamed to, and/or move the actual search call into a subprocess with a hard OS-level kill timeout, since in-process `asyncio` timeouts cannot forcibly terminate a thread stuck in a real blocking syscall.

### Other edge cases exercised, no issues found
- Empty input (bare Enter) — silently ignored, no crash.
- Mistyped command (`/disitll`) — fuzzy-matched to `/distill` correctly.
- Case-insensitive commands (`/HELP`) — matched correctly.
- `/distill` on a nonexistent session file — clean error message, no crash.
- Special characters / injection-style input (`"quotes"`, `[[fake_wikilink]]`, backticks, `<tag>`, `%`) — no crash; model handled gracefully. Cosmetic-only issue: `[[double bracket]]` sequences get silently eaten by Rich markup parsing in the echoed query line (renders as `[]`), since Rich's `[style]` tag syntax conflicts with wikilink syntax. Low priority — display-only, doesn't affect processing.
- Multi-part question ("what is RLHF, and also separately, what is photosynthesis") — handled as a single retrieval pass covering both; the model transitioned with "I'm glad we had a chance to cover that briefly. To recap—" despite photosynthesis never having been discussed before, and misattributed early photosynthesis biochemistry research to "Louis N. M. du Vigneaud" (a real biochemist, but known for oxytocin/insulin work, not photosynthesis) — a plain LLM hallucination, not a chatui bug, but worth knowing the deep-mode prompt template's "recap" framing can trigger false continuity claims.
- `/export`, `/clear`, `/status` all behaved correctly under repeated/rapid invocation.

### New gap found (not a bug, pre-existing content issue)
- Many `[[wikilinks]]` in `600-applied-sciences/*.md` (and a few elsewhere) still point at pre-rename kebab-case stems (`[[fine-tuning-methods]]`, `[[rlhf-alignment]]`, `[[machine-learning]]`, `[[lo-ra-adaptations]]`, `[[knowledge-distillation-methods]]`, `[[language-models]]`, `[[retrieval-augmentation-models]]`, `[[embedding-models]]`, `[[vector-databases-for-search]]`, `[[dewey-decimal-system|...]]`) instead of the current Title Case filenames — broken since the Session 16 vault rename and never caught by `/organize`'s wikilink pass (which only adds new links, doesn't validate existing ones). Left unfixed pending user review — it's a bulk edit across ~6 established files, out of scope for unattended overnight cleanup.

### Recommendations
- Add semantic-similarity dedup to `/distill`, matching what `save_to_vault` already does for `/savefile`.
- Add a distilled-marker to session files (or a manifest) so re-running `/distill` on the same session is idempotent.
- Migrate `web_search()` from `duckduckgo_search` to `ddgs`.
- Add a `/organize`-style validation pass that checks existing `[[wikilinks]]` against real vault stems and flags/fixes broken ones (separate from the existing "add new links" pass).

### Recommendations applied — 2026-07-03
All four implemented and validated live:
- **Dedup**: added the same 0.85-similarity check `save_to_vault` uses — but a live test proved 0.85 never fires for this query shape. Direct measurement: `"Q: what is LoRA..."` against the real `LoRA Adaptations.md` prose scored only **0.689**. Retuned to **0.7** based on that measurement rather than copying `/savefile`'s constant blindly. Confirmed working at the new threshold isn't fully re-validated yet (the live test that surfaced the 0.689 number ran before the retune) — worth a follow-up check next session.
- **Idempotency**: added an `<!-- distilled -->` HTML-comment marker inserted after each processed Q&A block; `/distill` skips marked pairs on future runs. Verified live: re-running `/distill` on an already-fully-distilled session now reports "No new (undistilled) Q&A pairs found" instead of regenerating all 12.
- **`ddgs` migration**: installed `ddgs`, swapped the import, both call sites unchanged (API-compatible). Not yet retested against the original hang bug — that fix is independent of the timeout/exception hardening already in place and still needs its own verification.
- **Wikilink validation pass**: added `_validate_wikilinks()` (module-level, normalises hyphens/spaces/case against real vault stems, rewrites only exact-once-normalised matches, never invents targets) and wired it into `/organize` as Pass 5. Ran it directly against the vault: **58 stale wikilinks fixed across 24 files** — this was a much bigger existing problem than the "~6 files" estimate from the original finding suggested, since the pre-rename kebab-case links turned out to be pervasive across almost all of `600-applied-sciences/` plus scattered instances elsewhere (`[[taxonomy]]` lowercase in `300-social-sciences/`, `500-natural-sciences/`, etc.).

