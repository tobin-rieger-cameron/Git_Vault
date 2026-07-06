---
summary: Notes on the most ChatUI-relevant items from clig.dev's Further Reading list — researched independently, not just summarized from clig.dev itself.
---

# CLIG further reading — notes

Companion to `clig_notes.md`. clig.dev's own "Further Reading" section lists ~20 sources; the five
below are the ones that actually bear on ChatUI's design (a persistent TUI, not a one-shot flag-driven
CLI). The rest (POSIX Utility Conventions, GNU Coding Standards, XDG spec, environment-variable
references, analytics/metrics guides) are written for exactly the kind of run-once CLI ChatUI isn't,
so they're skipped here rather than padded out.

## The Poetics of CLI Command Names (smallstep.com)

The depth clig.dev's own "Naming" section is missing. Concrete do/don't list:

- **Never use:** `tool`, `kit`, `util`, `easy` — filler words that describe nothing.
- **Type-ability matters as much as meaning.** Their example: `sha256sum` is awkward to type;
  `capinfos` flows. Avoid names that force awkward finger travel or shift-key gymnastics.
- **No version numbers in the name** (`python3.7m` is their cautionary example) — a name that encodes
  a version is a name you can't cleanly evolve.
- **Length should scale with frequency of use**, not with how important the feature feels — `cd`/`ls`
  earn their two letters by being typed constantly; a niche command can afford to be longer and more
  descriptive.
- **Don't name a command after a protocol/format.** `openssl` is stuck with a name it can never
  outgrow because the name *is* the standard it implements.
- **Don't describe your own implementation in the name** — `cfdisk` broadcasting "this one uses
  Curses" is information the user never needed.
- **Don't claim an overly generic verb.** ImageMagick's `convert` collided with the OS's own `convert`
  utility on Windows and they eventually had to give the name up.
- **What good looks like:** `curl` — a real verb, globally pronounceable, and it puns on "see URL."
  `vim` works for similar reasons (visceral, reads as "an improvement").
- **Closing line, worth keeping in view:** "None of the above matters if your command doesn't
  actually do something useful."

**For ChatUI:** the four verb command words (`/ask` implicit, `/draft`, `/classify`, `/review`) already
pass this test — they're plain verbs, no filler words, no protocol/implementation leakage, and their
length already scales with how often each gets typed (bare Ask needs no prefix at all since it's the
default action).

## Crash-Only Software (lwn.net, summarizing Candea & Fox)

The idea clig.dev's "Signal Handling" section gestures at without explaining: a program designed so
the *only* way to stop it is to crash it, and the *only* way to start it is to recover — no separate,
special "graceful shutdown" code path at all.

- **Why this is more robust, not less:** if recovery is the *only* start path, it runs on every single
  startup, in normal operation — so bugs in recovery logic get caught immediately instead of lying
  dormant until the one real crash that needs them. A graceful-shutdown path that's rarely exercised
  is exactly the code most likely to be broken when it's actually needed.
- **Measured, not just theoretical:** their cited benchmark had a crash-recovery cycle *faster* than a
  normal clean shutdown-and-restart (75s vs. 104s on the systems they measured).
- **The trap to avoid:** this is not "delete your cleanup code and call it robust." It requires *more*
  discipline — external, crash-safe state storage, retryable requests with timeouts, components that
  restart cleanly from whatever state they were left in.

**For ChatUI:** directly relevant to the crash that just happened — a Textual app dying from an
unhandled exception in a button handler and taking the whole tmux server down with it is the opposite
failure mode (a crash with no recovery path at all, and blast radius well beyond the process). It also
bears on `Retriever`'s manifest-based incremental ingest (`retrieval.py`) and `Vault.save_file()`
writing frontmatter — both already lean toward "state lives in a durable, external place (the
manifest file, the vault file itself) that a restart can just re-read," which is the right instinct;
worth keeping in mind once `app.py` needs to handle a mid-draft crash without corrupting a file.

## Writing Helpful Error Messages (Google) + Error-Message Guidelines (NN/g)

These two cover the same ground from technical-writing and UX-research angles respectively; combined
notes since they don't conflict.

- Every error should answer exactly two questions: **what went wrong**, and **how do I fix it**. An
  error that only states the first half is incomplete by definition, not just unfriendly.
- Bad error messages cluster around five failure modes: unactionable, vague, imprecise, confusing,
  inaccurate. Useful as a checklist for reviewing any error string before it ships.
- Write for the actual audience of the message — a stack trace for a developer log is not the same
  document as a message a session's end user will read.
- Consistent terminology matters — don't call the same concept a "file" in one message and a
  "document" in another.

**For ChatUI:** this is the concrete content behind `errors.py`'s existing "provide context in the
message" rule in `style_guide.md` — it says *what* to say, where the style guide only said to say
something. Once `app.py` catches `VaultWriteError`/`ModelUnavailableError`/etc. and shows them to the
user, each surfaced message should pass the two-question test (what happened, what to do about it),
not just relay the exception's `str()`.

## 12-Factor CLI Apps (Jeff Dickey)

A practical, opinionated checklist — the ones not already covered by clig.dev/style_guide.md:

1. Great help is essential — in-CLI, plus web docs, plus every help-invocation spelling actually works.
2. Prefer flags to positional args once there's more than one parameter.
3. Multiple ways to check version, with diagnostic info attached.
4. **Stdout is for output, stderr is for messaging** — keep them genuinely separate so redirection works.
5. Errors need a code, a description, a suggested fix, and a docs link — not a bare failure.
6. Be fancy (color, spinners, progress) but respect `NO_COLOR` and non-tty contexts.
7. Prompt when you can, but every prompt needs a flag/argument escape hatch for scripts.
8. Tabular output without decorative borders, so it's still grep/awk-friendly.
9. Startup under 500ms; show progress for anything slower.
10. Open, documented, contribution-friendly if it's going to have contributors at all.
11. Subcommand syntax should be consistent and unambiguous.
12. Follow the XDG spec for config/data/cache locations.

**For ChatUI:** most directly relevant is #4 (not literally applicable since ChatUI has no piping use
case as a persistent TUI, but the underlying principle — keep conversational output and system/status
messaging visually distinct — is exactly what the statusbar-vs-chatlog split in the visual comps
already does) and #12 (already followed: `config/` lives under the project directory rather than
scattering dotfiles, though it doesn't yet follow XDG's `~/.config` convention since ChatUI is
currently a single-vault, run-from-source tool rather than an installed system command).

## The Anti-Mac Interface (Gentner & Nielsen, 1996) — read for contrast, not adoption

Cited by clig.dev as a counterpoint to "GUI conventions are just correct" — worth reading because it
argues *against* several defaults, not because ChatUI should adopt all of it.

- Challenges the Mac's core assumptions (desktop metaphor, direct manipulation, strict visual
  consistency, WYSIWYG) as suited to naive users on simple tasks, not to expert users on large,
  networked, information-dense workloads.
- Its proposed alternative leans on **language over pointing** ("language lets us refer to things not
  immediately present, reason about potential actions, and use conditionals") and **rich metadata
  enabling automation** over manual direct manipulation of every object.
- Argues visual **uniformity stops helping past a certain scale** — enough near-identical objects and
  sameness becomes a navigation cost, not a comfort.

**For ChatUI:** this is closer to a justification for the whole project's shape than a UI-polish tip —
a typed conversational interface over a large personal knowledge base *is* the "language over
pointing" and "expert user over naive user" case this piece argues for. It's a reason a TUI/CLI
interaction model is a legitimate design choice for this specific tool, not just a legacy one.
