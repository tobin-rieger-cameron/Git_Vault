---
summary: Coding standards for the ChatUI rebuild, distilled from PEP8, Effective Python (3rd ed.), and Clean Code (Martin). Naming conventions are the current focus.
---

# Style Guide

Sources: `Example Database/Python_PEP8_TheStyleGuideForPythonCode.pdf`, `Effective-Python_Third-Edition.pdf`, `Clean Code_ A Handbook of Agile Software Craftsmanship - Robert C. Martin.pdf`, `_OceanofPDF.com_Clean_Code_in_Python...pdf`.

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

## Open

Formatting/comments/error-handling/objects-and-data-structures chapters of Clean Code, and most of Clean Code in Python (SOLID, decorators, descriptors, design patterns), haven't been distilled into this doc yet — added as they become relevant to actual rebuild decisions, not all at once up front.
