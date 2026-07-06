---
summary: Coding standards for the ChatUI rebuild, distilled from PEP8, Effective Python (3rd ed.), Clean Code (Martin), and Clean Code in Python (Anaya). Covers naming, function/class design, async/concurrency, data modeling, and comments so far.
---

# Style Guide

Sources: `Example Database/Python_PEP8_TheStyleGuideForPythonCode.pdf`, `Effective-Python_Third-Edition.pdf`, `Clean Code_ A Handbook of Agile Software Craftsmanship - Robert C. Martin.pdf`, `_OceanofPDF.com_Clean_Code_in_Python_-_Second_Edition_-_Mariano_Anaya.pdf`.

## Naming conventions

### Mechanical case rules (PEP8)

- Functions, methods, variables, modules: `lower_case_with_underscores`.
- Classes and exceptions: `CapWords`. Exception classes additionally get an `Error` suffix if they represent an error (`InvalidFileTypeError`, not `InvalidFileType`).
- Constants: `UPPER_CASE_WITH_UNDERSCORES`, defined at module level.
- Non-public: single leading underscore (`_helper`). Double leading underscore only to invoke name-mangling on a class attribute you specifically don't want subclasses to collide with — not as a general-purpose "private" marker.
- Never use `l`, `O`, or `I` as identifiers — indistinguishable from `1`/`0` in some fonts.
- `self` for instance methods, `cls` for classmethods, always.

### Function names: say what it does, not what it touches

A function name should answer *why it exists, what it does, and how it's used* without needing a comment next to it. If you have to explain a function in a comment, the function's name failed at its one job.

- **Verb or verb phrase**, since a function *does* something: `parse_frontmatter`, `render_paper`, `classify_subject`. Not `frontmatter` or `paper_data` — those are noun phrases and read like they return a value with no work implied.
- **One word per concept, used consistently everywhere.** If the codebase already uses `fetch` for "get something from the vault," don't later introduce `retrieve` or `get` for the same kind of operation elsewhere — pick one and hold the line across the whole codebase. Mixing `fetch_notes` / `get_papers` / `retrieve_subjects` for structurally identical operations forces the reader to memorize which verb belongs to which corner of the code, for no benefit.
- **Don't pun.** If `add_tag` merges a tag into an existing set and `add_paper` inserts a brand-new file, they're doing semantically different things and shouldn't share the verb `add` just for surface consistency — that's the same problem as the previous point in reverse: same word, different behavior. Use `add_tag` / `create_paper`, or whatever distinguishes them.
- **Avoid disinformation.** Don't name something `_paper_list` unless it's an actual `list` — if it's a generator, a dict, or a custom collection, a misleading name creates false expectations at every call site. Don't call a function `get_summary` if it also writes to disk — the name has to cover everything the function visibly does.
- **Boolean-returning functions read like yes/no questions**: `is_classified(paper)`, `has_frontmatter(path)`, `needs_review(paper)`. Never bury a boolean question inside a vaguer verb like `check_frontmatter` — "check" doesn't tell the reader whether it returns something, raises, or mutates state.
- **Consistent phraseology across a family of related functions**, so the sequence reads like a story. If `_draft_paper` calls `_classify_paper` which calls `_suggest_wikilinks`, related helper names should share vocabulary and word order rather than each reaching for a different structure. This is the single biggest thing that made the old `chatui.py` easy to get lost in — inconsistent naming between sibling functions doing parallel jobs.
- **Length should match scope.** A one-line list comprehension's loop variable can be `p` for "paper." A module-level function called from five other files needs a name descriptive enough to stand alone without the reader opening the file to check what it does.
- **Don't be clever or cute.** No inside jokes, no slang standing in for a plain verb. `delete_stale_notes`, not `sweep_the_cobwebs`. Clarity beats memorability-through-humor every time; the joke stops being funny the moment someone new has to maintain it.

### Class names: nouns, not verbs, not vague suffixes

- **Noun or noun phrase**, since a class *is* a thing: `Paper`, `ReviewSession`, `SubjectIndex`. Never name a class after an action it performs.
- **Avoid vague, do-everything suffixes** — `Manager`, `Processor`, `Handler`, `Data`, `Info` — unless the word actually distinguishes this class's behavior from a sibling class. A `PaperManager` next to a `PaperProcessor` next to a `PaperHandler` forces the reader to memorize which one does which job instead of the names doing that work.
- **No Hungarian-notation-style prefixes** (`IPaper`, `CPaperFactory`). If a Python "interface" (a Protocol, or an ABC with no other implementation yet) and a concrete implementation both need names, keep the abstract name plain and suffix the concrete one instead (`PaperStore` / `PaperStoreImpl` or, better, a name for what makes that implementation specific — `SqlitePaperStore`).
- **Pick one word per concept here too.** If `Paper` is the vault-wide term for a subject document, don't introduce `Article` or `Note` elsewhere in the same codebase to mean the same thing.

### A poorly named function is usually a poorly scoped one

Most naming trouble doesn't start with a bad vocabulary choice — it starts with a function trying to name something that's actually two or three things stitched together, so no single verb phrase can honestly describe it. Before renaming, check the shape first:

- **Small, and one thing, at one level of abstraction.** If you can extract another function out of it whose name is not just a restatement of the code you pulled out, the original was doing more than one thing.
- **Argument count**: 0 ideal, 1 (monadic) fine, 2 (dyadic) fine, 3 (triadic) needs real justification, 4+ is almost always a sign the arguments belong in a small `dataclass` instead of a flat parameter list.
- **A boolean/flag argument is a naming smell in disguise** — it means the function does two different things depending on the flag's value (`render(is_suite: bool)`). Split it into two clearly-named functions (`render_for_suite()` / `render_for_single()`) rather than trying to find one name that covers both branches.
- **No hidden side effects.** If `check_password` also silently initializes a session, the name is lying to every caller who trusts it. Either the side effect belongs in the name (`check_password_and_start_session`) or it shouldn't be there.
- **Command/query separation.** A function either *does* something (a command — mutates state, returns `None`) or *answers* something (a query — returns a value, no visible mutation). A function trying to be both (`set(attr, val) -> bool`) can't be named well because it's not one thing.

## Comments (PEP8 + Clean Code Ch.4)

The default is not to write one. A comment is what you reach for only after you've tried and failed to make the code say it. Every comment in this codebase should be able to answer "why did I need this instead of a better name/function?"

### The Clean Code framing

- **A comment is a failure, not a virtue.** It exists because we couldn't express the intent in code — never a reason to feel good about "documenting" something. If you're about to write one, first ask whether a renamed function/variable, an extracted helper, or a dataclass field would make the comment unnecessary.
- **Comments rot; code doesn't.** They live apart from the code they describe, so nothing enforces that they stay true when the code changes. An inaccurate comment is worse than none — it actively misleads. Treat every existing comment you encounter with suspicion: check it's still true before trusting it.
- **Never comment instead of cleaning up.** "This is confusing, I'd better comment it" is the wrong move — fix the confusion instead. A short, well-named function beats a long one with a header explaining what it does.
- **Don't restate what the code already says** (`i += 1  # increment i`). If removing the comment loses zero information, delete it.
- **Don't leave commented-out code.** Git remembers it; a comment claiming to "explain" a dead code block just invites the next reader to wonder if it's safe to delete. Delete it — it's in history if it's ever needed.
- **No banner/section-divider comments, no closing-brace comments, no attribution/byline comments, no changelog-in-a-docstring.** Source control already owns authorship and history; this repo's own `config/changelog.md` already owns the changelog, so it especially shouldn't be duplicated in-file.
- **Never document what a stub will do — only what it does.** A `raise NotImplementedError` body has no behavior yet; a docstring describing the intended implementation ("calls X, streams to Y") is describing code that isn't there, which is the same lie-in-waiting as an outdated comment, just pre-dated instead of stale. Skeleton methods get a docstring only once they have a real body to describe.
- **Comments that earn their place** (rare, and all of these still need to be short and directly attached to the code they describe): a non-obvious *why* behind a decision (a workaround for a specific external bug, a deliberately-unusual choice made for a reason that isn't visible locally); a warning of a real consequence (a slow/dangerous test, a thread-safety constraint); a `# TODO:` marking known-incomplete work that's actually tracked, not a permanent excuse.
- **A comment must be local.** If understanding it requires jumping to another module or a design doc, it isn't doing its job — put that context in `config/` docs, not scattered inline.

### PEP8's mechanical rules, when a comment is warranted

- Comments should be complete sentences; capitalize the first word (unless it's an identifier that starts lowercase — never alter identifier case). Short comments can drop the trailing period; block comments should punctuate every sentence.
- **Block comments**: same indentation as the code they describe, each line starts with `# ` (one space after `#`). Separate paragraphs within a block comment with a bare `#` line.
- **Inline comments** (on the same line as a statement): use sparingly. Separate from the statement by at least two spaces, then `# ` (one space). Never state the obvious (`x += 1  # increment x`) — only worth it when it explains something not visible in the line itself (`x += 1  # compensate for border`).
- Keep comments in English unless certain no one who lacks that language will ever read the code.

### Docstrings (PEP8 → PEP257)

- Every **public** module, function, class, and method gets a docstring. Non-public (`_`-prefixed) functions don't need one, but per this codebase's "no comments unless the why is non-obvious" rule, they also don't get a comment by default — only if there's a genuine non-obvious why.
- For a multi-line docstring, the closing `"""` goes on its own line. For a one-liner, keep the closing `"""` on the same line as the opening.
- This project's own rule (from the top of this doc) still governs docstring *content*: no multi-paragraph docstrings, one line describing intent, not restating the signature. A public function's docstring should say what it does at a level the name doesn't already cover — not a repeat of the parameter list.
- **Function/method docstrings: imperative mood, not descriptive.** PEP257 is explicit: "It prescribes the function or method's effect as a command ("Do this", "Return that"), not as a description ("Returns the pathname...")." Write `"""Return the pathname of the KOS root directory."""`, never `"""Returns the pathname..."""`. This applies to every function/method docstring in this codebase — a docstring that answers "what does this do" as a command reads as a fixed spec; one that answers it as a description of behavior reads like an aside pulled from a conversation about the code, which is exactly the tone to avoid. Class/enum/module docstrings are the one exception — they describe *what a thing is*, not an effect, so a noun phrase is correct there (`"""A retrieved passage; ..."""`, not `"""Represents a retrieved passage..."""`).
- **Pick one voice per file and hold it.** Google's style guide allows either imperative or descriptive style but requires "the style should be consistent within a file" — this codebase standardizes on imperative for all function/method docstrings, full stop, so there's no per-file judgment call to make.

## Formatting and layout (PEP8, brief — expand later as needed)

- 4-space indentation, never tabs. Max line length 79 (99 is acceptable for a team that agrees on it and keeps docstrings/comments at 72).
- Two blank lines around top-level defs/classes, one blank line between methods.
- Imports: stdlib, then third-party, then local — each group separated by a blank line, one import per line, no wildcard imports.
- No space before `(` in a call or `[` in an index; always one space around binary operators and after commas; no space around `=` for keyword args/defaults unless also annotated.
- `is`/`is not` for `None` and other singleton comparisons, never `==`/`!=`.
- One `except <SpecificError>:` per case, never bare `except:`; keep `try` blocks as short as possible.

## From Effective Python (3rd ed.), directly relevant to this rebuild

- Prefer raising a specific exception over returning `None`/a sentinel for an error case (Item 32) — callers forget to check falsy-but-valid results like `0` or `""`.
- Prefer `@dataclass` over a long positional-return tuple once a function would need to return more than ~3 values (Item 31, Item 51) — this is likely how "paper" and "proposal"-like records should be modeled in the rebuild.
- Keyword-only arguments (`*,` in the signature) for anything where argument order at the call site could be confused; positional-only (`/`) for parameter names that are implementation detail, not public API.
- `None` + docstring for any default argument value that needs to be computed fresh per call (a timestamp, a new list) — a literal mutable default is shared across every call.

## Async and concurrency (Clean Code in Python, Ch.7)

The rebuild is a Textual app — `async def`/`await`, workers, and the event loop are load-bearing, not incidental. This is the exact bug class that bit the old `chatui.py` (`NoActiveWorker` from calling `push_screen_wait` outside worker context), so get the mental model right before writing more async code.

- **Generators vs. coroutines are the same mechanism, different intent.** Both use `yield`/are driven by `__next__`-like advancement, but a generator exists for lazy iteration; a coroutine exists to suspend a piece of work and resume it later (I/O, event-loop scheduling). Don't let the syntactic overlap blur the purpose — code that *iterates* (produces a stream of values for a `for` loop) should be a plain generator; code that *waits on something* (a model call, a file read, a subprocess) should be `async def`.
- **`async def` + `await` replaced hand-rolled coroutines (`yield from` + `.send()`/`.throw()`/`.close()`) on purpose.** Never write the old PEP-342-style manual coroutine plumbing in new code — `await` only works with `awaitable` objects and raises immediately if you hand it something that isn't one, which is exactly the fail-fast behavior you want instead of a runtime surprise deep in a callback.
- **An event loop (here: Textual's, built on asyncio) owns every coroutine.** `await <coroutine>` doesn't block — it hands control back to the loop, which resumes something else, then resumes you when your result is ready. A blocking call inside an `async def` (a synchronous `requests.get`, a tight CPU loop, a plain `time.sleep`) stalls the *entire* app, not just that one task — this is almost certainly what "the program just looks frozen completely" during Pass 1/2 boiled down to when a genuinely-async step got mixed with something synchronous.
- **`push_screen_wait`, and anything else that suspends waiting on the app, must run inside worker context.** Textual workers are the sanctioned place to `await` UI-suspending calls; a plain message handler is not a coroutine driven by the same scheduling guarantee. If a handler needs to `await` something that can block, route it into a worker (`self.run_worker(...)`) rather than awaiting it directly from the handler.
- **Async context managers (`async with`, `__aenter__`/`__aexit__`) and async iteration (`async for`, `__aiter__`/`__anext__`) exist for the same reason their sync counterparts do — resource setup/teardown and streaming — just for resources that need to `await` during enter/exit/each step.** Prefer an async generator (`async def f(): ... yield x`) over hand-writing a class with `__aiter__`/`__anext__` — same reason plain generators beat hand-written iterators: less boilerplate, same capability, per the book's own explicit recommendation.
- **Don't put a coroutine where a magic method expects a plain function**, e.g. `__init__`, `__getattr__`. Object construction and attribute access should stay synchronous and side-effect-light; if initialization needs an awaited call, that belongs in an explicit async factory/setup step the caller awaits, not hidden inside `__init__`.

## Classes and data modeling (Clean Code, Ch.6 — Objects and Data Structures)

- **Objects and data structures are opposites, and a class should commit to being one or the other, not both.** An *object* hides its data behind an abstraction and exposes behavior (`Paper.reclassify()`); a *data structure* exposes its data plainly and has no meaningful behavior (`ParsedFrontmatter` with public fields, no methods). Adding getters/setters over private fields doesn't turn a data structure into an object — it's still just exposing implementation through an extra layer of indirection. Decide, per class, which one it is.
- **This split has a real payoff, not just a style preference.** Data-structure code (procedures operating on plain data) makes it easy to add new *operations* without touching existing data shapes. Object code (behavior hidden behind an interface) makes it easy to add new *data shapes/implementations* without touching existing callers. In the rebuild: things like `Paper`/`ReviewProposal` that gain new kinds of operations over time (draft, classify, review, export) should probably be data structures operated on by functions; things where new *variants* are the likely growth axis (multiple retrieval backends, multiple paper-source formats) should be objects behind a shared interface.
- **Law of Demeter: a method should only call methods on itself, its own fields, objects it created, or objects passed to it as arguments — not on objects returned by those calls.** `ctxt.getOptions().getScratchDir().getAbsolutePath()` ("train wreck" chaining) is the smell; it only actually violates Demeter if `ctxt`/`options`/`scratchDir` are *objects* hiding behavior — if they're plain data structures, chaining through their public fields (`ctxt.options.scratch_dir.absolute_path`) is fine, because data structures are supposed to expose their shape. Don't apply Demeter to attribute access on dataclasses; do apply it to method-chaining on things with real behavior.
- **Don't fix a train wreck by asking an object about its internals just to do something with the answer** (`ctxt.getAbsolutePathOfScratchDirectoryOption()` and its ilk explode into a combinatorial pile of accessor methods). If the caller's actual goal is "get `ctxt` to do X," tell it to do X directly (`ctxt.create_scratch_file_stream(name)`) instead of extracting pieces to do X yourself.
- **Avoid hybrids** — a class with both real behavior *and* public fields/bean-style accessors that let outside code bypass that behavior. Hybrids are the worst of both worlds: hard to add new operations to (because behavior is baked in) and hard to add new data shapes to (because callers already depend on the exposed fields). If a class is accumulating both, split it into a plain data structure plus a separate object that holds the business logic and references it.
- **Data Transfer Objects (DTOs)** — a class with public fields and no functions — are the right shape for boundary data: parsed frontmatter, a row from ChromaDB, a raw model response before it's interpreted. In Python, this is exactly what `@dataclass` is for (ties back to Effective Python's dataclass recommendation already in this doc). Don't add business-rule methods onto a DTO "for convenience" — that's how a DTO turns into a hybrid.
- **Active Record** (a DTO with `save()`/`find()`-style navigational methods bolted on, common in ORM-backed models) is fine as long as it stays a data structure with persistence methods — the moment business rules get added to it, split those rules into a separate object that holds/wraps the record rather than growing the record into a hybrid.

## Error handling (Clean Code, Ch.7 — Error Handling; Ch.8 opening — Boundaries)

- **Raise, don't return a sentinel or flag.** A function that returns `None`/`-1`/`False` to signal failure forces every caller to remember to check — one missed check and the bad value propagates silently. Python has no checked-exception debate to referee (there's no `throws` clause), so there's no cost/benefit trade-off to weigh here the way the book has to for Java: just always raise for an actual failure.
- **Write the `try`/`except` first when a function needs one.** A `try` block defines a transaction-like scope — decide what the caller can rely on afterward (either it fully succeeded, or a specific exception was raised) before filling in the body. This is a "structure the failure path before the happy path" habit, not a "test-first" mandate.
- **Catch the exact exception type that can actually be raised**, never a bare `except Exception`/`except:` (already in this doc's PEP8 section — Ch.7 is the *why*: broad catches hide which failure you actually planned for and swallow ones you didn't).
- **Wrap third-party/boundary APIs and translate their exceptions into your own types at the boundary** — directly relevant to this rebuild's `Retriever` (wraps `chromadb`) and `ModelClient` (wraps `ChatOllama`/Ollama). A caller of `Retriever.search()` shouldn't need to know or catch a `chromadb`-specific exception; `Retriever` catches it internally and raises a `RetrievalError` (or lets a `PaperNotFoundError` bubble from `Vault` instead of a raw `KeyError`). This is the same "wrap third-party code, don't let its interface leak" idea Ch.8 opens with for `java.util.Map` — never pass a `chromadb.Document` or a raw Ollama response object past the module that wraps that library; translate to this codebase's own dataclasses (`Chunk`, plain `str`) at the boundary.
- **Exception classes should be defined by how they're caught, not by their source.** One `IngestError` covering "anything that went wrong turning vault files into embeddings" is more useful than a different exception per underlying cause, unless a caller actually needs to handle two causes differently — don't over-split.
- **Provide context in the message**: name the operation and what failed (`f"Failed to ingest {path}: {cause}"`), not just a bare re-raise — a caller catching this three frames up shouldn't have to guess what was being attempted.
- **Don't return `None` for "nothing here."** For a single expected item that's missing, raise (`PaperNotFoundError`) rather than returning `None` and pushing a null-check onto every caller. For a *collection* that's legitimately empty, return an empty list/dict — never `None` standing in for "empty" (the Special Case Pattern: make the empty/default case a normal, valid value instead of a condition callers must special-case with an `if`).
- **Don't pass `None` into a function as an implicit "skip this" signal** unless the parameter's type is explicitly `X | None` and the docstring/annotation says so. An accidental `None` should fail fast and loud (a `TypeError`/an assertion) rather than being silently tolerated three layers deep.

## Backlog — chapters not yet distilled, by source

Notes for future sessions on what's still available in each source PDF but hasn't been turned into style-guide content yet. Pull from this list when a rebuild decision actually needs the material — don't distill ahead of need.

**Clean Code (Martin), full 462pp — chapters read so far: 1 (skim), 2 (full), 3 (full), 4 (full), 6 (full), 7 (full). Ch.8 read only its opening ("Using Third-Party Code").**
- Ch.5 Formatting — team-level layout conventions beyond PEP8's mechanical rules (vertical density, conceptual affinity between nearby lines).
- Ch.8 Boundaries — only the opening ("Using Third-Party Code" — wrap boundary APIs, don't let their types leak, already applied to the Error Handling section above) has been read. The rest of the chapter (learning boundaries via tests, using code that doesn't exist yet, clean boundaries) is still unread — relevant once the rebuild actually integrates ChromaDB/Ollama and needs a concrete wrapping pattern, not just the principle.
- Ch.9 Unit Tests — the "F.I.R.S.T." properties; relevant once the rebuild has enough surface area to need a real test suite rather than the ad hoc pilot scripts used this session.
- Ch.10 Classes — class organization/encapsulation/cohesion, Single Responsibility, Open-Closed; the class-design half of what Ch.6 covers from the data-shape half.
- Ch.11 Systems, Ch.12 Emergence, Ch.13 Concurrency (Java-specific — cross-reference against Ch.7 of Clean Code in Python instead, which is Python-native), Ch.14 Successive Refinement, Ch.15–16 (case-study chapters, lowest priority), Ch.17 Smells and Heuristics — a checklist worth a pass near the end of the rebuild as a self-review tool, not up front.

**Clean Code in Python (Anaya), full 504pp — chapter read so far: 7 (full, async guide above).**
- Ch.1 Introduction, Formatting, and Tools — linters/formatters/type-checking tooling for Python specifically (mypy, pylint, black-equivalents); worth a pass when setting up the rebuild's project scaffolding.
- Ch.2 Pythonic Code — indexing/slicing protocols, context managers, comprehensions, properties vs. getters/setters — likely the single highest-value untouched chapter given how much of the rebuild will be idiomatic Python over a TUI.
- Ch.3 General Traits of Good Code — design by contract, defensive programming, DRY/YAGNI/KIS, EAFP vs. LBYL, inheritance, function arguments — overlaps but doesn't duplicate the Clean Code (Martin) function guide already written; EAFP vs. LBYL specifically isn't covered yet anywhere in this doc.
- Ch.4 SOLID Principles — as applied in Python specifically (duck typing changes how Liskov/Interface-Segregation show up); relevant once the rebuild has more than one implementation of something (e.g. multiple retrieval backends).
- Ch.5 Decorators — relevant if the rebuild ends up with repeated cross-cutting concerns (logging, retry-on-model-timeout) worth factoring out.
- Ch.6 Descriptors — lower priority; niche unless the rebuild needs custom attribute validation/computed properties at scale.
- Ch.8 Unit Testing and Refactoring — Python-specific pytest/mock guidance, pairs with Clean Code (Martin) Ch.9.
- Ch.9 Common Design Patterns — worth a pass once the rebuild's actual architecture (Ask/Draft/Classify/Review) reveals which patterns it's already informally using.
- Ch.10 Clean Architecture — layering/boundaries at the whole-application level; most useful once the four-verb structure has enough code to organize.

**Effective Python (3rd ed.) — only an 80-page free-sample PDF (front matter + full Ch.5 Functions, already distilled above, + full index). Chapters 1–4 and 6–14 are NOT available in full prose, only as item titles via the index/TOC.** No further distillation possible from this source until (if) a full edition is obtained. Known-relevant item titles worth sourcing prose for later, from the index: Ch.9's asyncio items (Item 67ish "Achieve Highly Concurrent I/O with Coroutines," "Know How to Port Threaded I/O to asyncio," "Maximize Responsiveness of asyncio Event Loops with async-Friendly Worker Threads," "Consider concurrent.futures for True Parallelism") and Item 51 "Prefer dataclasses for Defining Lightweight Classes."

**PEP8 — fully read and distilled (25pp, no backlog).**
