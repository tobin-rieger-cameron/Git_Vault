---
summary: Distilled notes from clig.dev (Command Line Interface Guidelines) — the CLI-specific analog to style_guide.md's PEP8/Clean Code material. Read for ChatUI's terminal UI direction.
---

# CLI Guidelines (clig.dev) — notes

Source: [clig.dev](https://clig.dev/), full text fetched 2026-07-06. This is the terminal-specific
counterpart to `style_guide.md`'s code-quality sources — same idea, applied to interaction design
instead of code structure. Companion doc: `clig_further_reading_notes.md` covers the sources clig.dev
itself cites.

## Philosophy

- **Human-first.** Traditional UNIX tools assumed machine-to-machine use. A tool used primarily by a
  human should be designed for that human first, machine composability second — not the reverse.
- **Small parts that work together.** Programs become components in larger systems (automation, CI,
  piping). Composability comes from standard mechanisms: stdin/stdout/stderr, exit codes, structured
  output (JSON) — not from any one program trying to do everything.
- **Consistency, deliberately broken when it matters.** Terminal conventions are deeply learned
  patterns; consistency makes an interface guessable. Deviating from convention is fine, but should be
  a deliberate choice with a reason, not an accident.
- **Say just enough.** Silent hangs and debug-log floods are both failures of information design —
  the same "say enough, no more" balance style_guide.md already applies to code comments applies here
  to program output.
- **Ease of discovery.** A GUI exposes its own functionality by being visible; a CLI/TUI has to build
  discovery in deliberately — help text, examples, error-driven suggestions, contextual hints.
- **Conversation is the native metaphor.** Multi-step CLI use (try something, get corrected, retry) is
  already dialogue-shaped. Error-correction suggestions, visible intermediate state, and confirmation
  before destructive actions all follow from taking that metaphor seriously.
- **Robustness, objective and subjective.** Objective: handles bad input gracefully, idempotent.
  Subjective: *feels* solid — no scary stack traces, common errors explained, user kept informed.
  Simplicity is often what buys robustness, not extra defensive code.
- **Empathy.** A CLI is a creative tool the user chose to pick up; it should feel like it's on their
  side, not fighting them.
- **Chaos.** Terminal environments are inconsistent by nature — that inconsistency is also where
  invention happens. Break a pattern only with real intent (Raskin: "abandon a standard when it is
  demonstrably harmful to productivity or user satisfaction").

## Concrete guidelines (the parts most relevant to ChatUI)

**Output formatting**
- Humans first, machines second — detect whether output is going to a human or being piped, and
  render differently if it matters.
- Keep success output brief; state-changing operations should announce the result and the new state
  (their example: `git status` after any operation).
- Suggest the next likely command in context.
- Color used intentionally, never load-bearing alone; respect `NO_COLOR` / non-interactive contexts.
- Suppress debug/internal output by default; no bare `ERR`/`WARN` labels unless verbose mode is on.

**Errors**
- An error is a documentation opportunity — catch the expected ones and rewrite them for a human,
  as a suggestion toward the fix, not a dump of what broke internally. Their example:
  *"Can't write to file.txt. You might need to make it writable by running 'chmod +w file.txt'."*
- Group repeated/similar errors under one explanatory header rather than repeating the same line.
- Genuinely unexpected errors: show a traceback and how to report it — but to a log file, not
  the terminal, so it doesn't bury the actionable part.

**Interactivity**
- Prompt only when input is actually interactive (a real terminal on the other end); never make a
  prompt the *only* path — always provide a flag/argument alternative for scripting.
- Confirmations should scale with danger: mild changes need none, bulk changes need a yes/no, total
  deletions should require something harder to do by accident (typing the resource's name back).
- Escape routes must always work — Ctrl-C should always do something, and do it immediately.

**Robustness**
- Responsiveness matters more than raw speed — get *something* on screen within 100ms even if the
  real work is still running.
- Show progress for anything long-running.
- Design for recovery: hitting up-arrow and re-running after a failure should be able to resume, not
  restart from zero.
- On Ctrl-C: exit immediately, say something first, cap cleanup time, and be honest that cleanup may
  not finish (their phrase: "crash-only software" as a design stance, not just a fallback — see
  `clig_further_reading_notes.md`).

**Naming**
- Short, memorable, easy to type repeatedly — length should scale with how often the command gets
  typed, not with how important the feature feels.
- (Their reasoning here is thin on the main page; the "Poetics of CLI Command Names" piece in further
  reading has the real depth — see companion notes.)

## Where this actually lands on ChatUI

Most of clig.dev is written for argument/flag/subcommand CLIs (`myapp --foo bar`), which isn't quite
ChatUI's shape (a persistent TUI session with typed `/commands`, not a program that runs once and
exits) — so a lot of the flag-naming/exit-code/environment-variable material doesn't transfer
directly. What does transfer, directly and usefully:

- **Say just enough** → this is the whole reason draft revision went from a full-pane overwrite to
  an additive diff. Overwriting was saying too little (the old content) and hiding it under new
  content the user hadn't asked to lose.
- **Confirmations scale with danger** → `apply_classification()` moves a file and rewrites its
  frontmatter; that's a "moderate" action per their scale (bulk-ish, reversible via Obsidian/git, but
  not nothing) — worth an explicit accept step in `app.py`, which the four-verb decisions already
  call for.
- **An error is a documentation opportunity** → directly informs how `app.py` should surface
  `ModelUnavailableError`/`VaultWriteError`/etc. to the user: not a raw exception message, but "here's
  what happened, here's what to try."
- **Escape routes must always work** → `/done` ending a draft/review loop, and Ctrl-C always quitting
  immediately, both already match this.
- **Progress within 100ms / show progress for long operations** → the whole reason `StreamingText`
  exists — token-by-token streaming *is* this principle, applied to LLM latency specifically.
