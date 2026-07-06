---
summary: Visual/interaction design standards for ChatUI's TUI, distilled from Refactoring UI (Wathan & Schoger), Laws of UX (Yablonski), Don't Make Me Think (Krug), and The Design of Everyday Things (Norman). Companion to style_guide.md (code) and clig_notes.md/clig_further_reading_notes.md (CLI-specific interaction principles). All four planned sources now distilled.
---

# UI Style Guide

Sources: `Example Database/refactoring-UI_adam-wathan_and_steve-schoger.pdf` (full book, 252pp,
read in full 2026-07-06); `Example Database/dokumen.pub_laws-of-ux-design-principles-for-persuasive-and-ethical-products.pdf`
(full book, 153pp, read in full 2026-07-06); `Example Database/Steve_Krug_Don't_Make_Me_Think,.pdf`
(257pp, chapters 1–9 and 11 read in full 2026-07-06; chapters 10, 12, 13 skimmed — see note at the
end of the Krug section for why); `Example Database/The-Design-of-Everyday-Things_Don-Norman.pdf`
(369pp, chapters 1–5 read in full 2026-07-06; chapters 6–7 skimmed — see note at the end of the
Norman section for why). This closes out the planned four-book UI research pass.

This doc is scoped to ChatUI's actual medium: a terminal, monospace, 24-bit-color TUI built in
Textual. Refactoring UI is a web/GUI design book, so a fair amount of it (font pairing, box shadows,
photography, border-radius personality) doesn't transfer — those sections are explicitly skipped
below, not silently ignored. What *does* transfer (hierarchy, spacing systems, color-shade systems,
avoiding ambiguous spacing, preferring background contrast over borders) turned out to be most of
the book, since those are medium-agnostic principles about how humans read visual structure.

## Design process (Ch. "Starting from Scratch")

- **Start with a feature, not a layout/shell.** Design the thing that actually does something
  (a verb's interaction) before worrying about chrome around it. Directly matches how this rebuild
  is already organized — four verbs first, `app.py` shell last.
- **Don't over-invest in low-fidelity exploration.** Sketches/demos are disposable; use them to
  decide, then move on. The `_demo_ui.py` prototype exists for exactly this reason — it's explicitly
  throwaway, not a codebase to maintain.
- **Choose a personality, then hold it.** A design's "feel" comes from a few concrete levers: color,
  and (in a GUI) font choice/border-radius. ChatUI's chosen personality is the amber-phosphor
  terminal look — a deliberate choice already recorded in the plan doc, not something to second-guess
  per-widget.
- **Limit your choices by defining systems in advance, not by hand-picking values live.** This is the
  single biggest miss so far: tonight's palette (`#d98f3b`, `#8a6229`, `#5c3a14`, `#8c8272`, `#f0e9d8`,
  `#7fae6b`, `#3a2f20`...) was hand-picked color-by-color, one hex value per new need, exactly the
  "reach for the color picker every time" anti-pattern this chapter warns against. **Action item:**
  formalize a real shade scale (see Color section below) instead of continuing to hand-pick ad-hoc
  hex values as new UI needs come up.

## Visual hierarchy (Ch. "Hierarchy is Everything")

- **Not all elements are equal — hierarchy, not styling, is what makes something look designed.**
  De-emphasizing secondary/tertiary content matters more than decorating primary content.
- **Two or three text colors is enough**: a bright color for primary content, a muted color for
  secondary, an even more muted one for tertiary. This is exactly the `_FILE_COLOR`/`_FOLDER_COLOR`
  split already implemented in `picker.py` — files (what you're looking for) bright, folders
  (structure, not content) muted. Validates that choice; the same two-tier thinking should extend
  to any future text in the app, not just the tree.
- **Balance weight and contrast.** A visually "heavy" element (bold text, a solid icon, a filled
  background) can be de-emphasized by lowering its contrast instead of shrinking it; a low-contrast
  element that needs more presence can be emphasized by increasing weight instead of raising contrast.
  Directly explains why the tree's selected-file treatment works: bright accent background + a
  *darker* amber-brown text (not black) — weight (the solid fill) is balanced by keeping the text
  color still warm/mid-tone rather than maximum contrast.
- **Primary/secondary/tertiary actions need visually distinct treatment, not just semantic
  correctness.** Primary: solid, high-contrast (obvious). Secondary: clear but not prominent (outline
  or lower-contrast fill). Tertiary: discoverable but unobtrusive (link-styled). Relevant once
  `app.py` has real accept/edit/skip actions for classify and the wikilink walkthrough — they
  shouldn't all look the same weight just because they're all "things you can do."
- **Destructive doesn't automatically mean loud.** A destructive action that isn't the primary
  action on screen should get secondary/tertiary treatment, with the loud treatment reserved for
  an actual confirmation step where it briefly *becomes* the primary action. Relevant to
  `apply_classification()`'s file-move (real filesystem side effect) once it has a UI.
- **Emphasize by de-emphasizing.** If something isn't standing out, the fix is often to mute what's
  competing with it, not to make the target louder. (E.g., don't give a sidebar a background color
  if it's fighting the main content for attention — let the sidebar sit on the same background and
  let position alone do the separating, as `#sidebar` already does.)

## Layout and spacing (Ch. "Layout and Spacing")

- **Start with too much white space, then remove it — don't start cramped and add space until
  it's "not bad."** The default instinct (add margin until it looks okay) caps out at "barely
  acceptable"; starting generous and trimming back gets you to "actually good."
- **Define a spacing scale where no two values are within ~25% of each other**, so choices are
  obviously right or wrong rather than agonized over pixel-by-pixel. ChatUI has no such scale yet —
  padding/height values in `_demo_ui.py` (1, 2, 3, "0 1", "0 0 1 0"...) were picked ad hoc per widget.
  Worth defining a small fixed scale (e.g. 1/2/3/5 rows, matching Textual's cell-based units) before
  `app.py`'s real layout work, for the same reason as the color scale above.
- **Avoid ambiguous spacing — always leave more space *around* a group than *within* it.** This is
  the exact principle behind the border-junction problem discovered tonight: two adjacent widgets'
  independent borders meeting without a shared joint character read as "disconnected" specifically
  because the spacing didn't clearly signal one group vs. two. The fix already applied (background
  color grouping instead of a border at that seam) is this same principle, just solved a different
  way — see "Use fewer borders" below, they're really the same idea from two angles.
- **Don't feel obligated to fill the available space.** A TUI's whole width doesn't need to be used
  just because it's there — matches the "not every pane needs to be wide" instinct behind keeping
  `#sidebar` and `#chat` fixed/bounded widths rather than proportionally flexing everything.

## Text and readability (Ch. "Designing Text" — most of this chapter is font-choice/type-scale and doesn't apply to a fixed monospace grid; the exceptions below do)

- **Line length: 45–75 characters is the readable range.** This transfers almost literally to a
  terminal, where character count *is* the actual unit of width (no sub-pixel font metrics to
  complicate it). Worth checking the chat/preview pane widths against this range directly, rather
  than picking widths by eye.
- **Right-align numbers in tabular data**, so decimal points/magnitudes line up for easy comparison.
  Relevant to any future tabular output (`files_due_for_review()` listings, `IngestStats` display).
- **Not every interactive element needs the loudest possible treatment.** Ancillary links/actions
  can be de-emphasized (underline-only, or color-on-hover-only) rather than all competing at once —
  same idea as the primary/secondary/tertiary action point above, applied to text-as-link specifically.
- Skipped as not applicable: type scales, font pairing, em-unit sizing, baseline alignment, line-height
  tuning, letter-spacing — all presuppose variable font sizes/faces, which a monospace terminal grid
  doesn't have.

## Color systems (Ch. "Working with Color")

- **Use HSL, not hex, when reasoning about color relationships** — hue/saturation/lightness map to
  how the eye actually perceives color, so "make this a bit darker/warmer/less intense" is a direct
  HSL edit, not a guess-and-check hex change. (Terminals render 24-bit RGB same as browsers, so this
  reasoning transfers directly even though the delivery format ends up as hex in CSS either way.)
- **You need far more colors than five hex codes.** A real palette needs: 8–10 grey shades, 5–10
  shades each of one-or-two primary colors, plus accent colors for semantic states (error/warning/
  success) — each with their own shade range. ChatUI's current palette has exactly one shade each of
  background/surface/border/text/accent/accent-dim/muted/addition-green — a single sample point per
  role, not a range. This is fine for a *first pass* but will start hurting the moment a new need
  shows up that doesn't fit an existing hex value exactly (which is exactly what's been happening —
  a new ad-hoc hex has been added almost every round of feedback tonight).
- **Define shades up front by picking base/darkest/lightest, then filling gaps — never generate
  shades on the fly with "lighten/darken" style tweaks**, or you end up with a dozen near-identical
  colors that all look the same. **Concrete next step for ChatUI:** formalize the amber accent as a
  real shade scale (e.g. 100/300/500/700/900 from `#f0e9d8`-ish lightest down to `#5c3a14`-ish
  darkest) and do the same for the warm-grey neutral, instead of continuing to invent one-off hex
  values per new UI element.
- **Don't let lightness kill saturation** — as a color approaches white or black, the same saturation
  value reads as less colorful; compensate by increasing saturation toward the extremes, or by
  rotating hue toward a brighter/darker hue family (yellow/cyan/magenta are inherently brighter than
  red/green/blue at the same saturation+lightness). Relevant if the amber accent ever needs a very
  light or very dark shade added to its scale.
- **Greys don't have to be neutral grey — a slight hue bias reads as "chosen," not "default."**
  ChatUI's warm brownish-grey (`#8c8272`, `#3a2f20`) already does this correctly (matches the
  artifact-design guidance from earlier in this project too — "a grey with a slight hue bias toward
  the page's accent reads as chosen").
- **Don't rely on color alone to communicate state** — pair it with a second signal (an icon, a
  label, a position) for anything meaningful, since color-blind users can't distinguish hue alone.
  Relevant to any future status indicators (e.g. `model:`/`web:` status bar entries already pair
  color with a text label, which is correct; a future "draft in progress" indicator should do the
  same rather than relying on color alone to mean something).
- **Accessible contrast doesn't require stark black-on-white/white-on-black** — flipping which side
  is dark (dark text on a light-tinted background, rather than light text on a dark-saturated
  background) often meets contrast requirements with less visual loudness. Worth checking WCAG
  contrast ratios (4.5:1 normal text, 3:1 large text) against the actual amber-on-near-black and
  amber-brown-on-amber combinations once the palette is formalized, rather than assuming "looks fine
  to me" is sufficient.

## Finishing touches (Ch. "Finishing Touches")

- **Use fewer borders — two adjacent background colors usually do the same grouping job with less
  visual noise, and without the disconnected-junction problem borders create between independent
  widgets.** This is the exact fix already applied tonight to `#sidebar-head` and `#inputbar` (removed
  `border-bottom`/`border-top`, kept only the surface-color contrast) — arrived at independently
  through debugging a rendering bug, and it turns out to be a named, recommended technique rather
  than a workaround. Worth auditing the rest of the app for other borders that could become a
  background-color distinction instead, especially anywhere two borders might cross at a right angle.
- **Extra spacing alone is a legitimate way to create separation** — doesn't always need a border or
  a color change, just more room between groups.
- **Accent color as a small structural element** (a colored rule/underline/edge) can substitute for
  actual graphic design skill. The amber badge treatment on suggestion counts and the two-tone
  selected-file highlight are both already doing this.
- **Don't overlook empty states.** Relevant once `app.py` is real: what does the preview pane show
  before any file is clicked, what does `/review` show when nothing is due, what does the tree show
  for a genuinely empty vault. Not designed yet — worth a deliberate pass rather than letting these
  default to "just blank."

## Psychology of interaction (Laws of UX, Yablonski) — all 10 laws read in full

Where Refactoring UI covers visual craft, this book covers *why users perceive things the way they
do* — the psychological mechanics underneath. Several of these turned out to be direct, independent
validation for decisions already made tonight, before this book was ever opened; noted explicitly
below rather than just listed as abstract theory.

- **Jakob's Law** — users transfer expectations from every other product they've used; the less a
  design fights those expectations, the less cognitive effort it costs. **Direct validation**: this
  is *why* following existing conventions was the right instinct all evening rather than inventing
  new ones — Input's own readline-style bindings (`ctrl+a`/`ctrl+e`), Textual's default `ctrl+c`
  quit-confirmation, the lazyvim nvim-tree collapsible-sidebar pattern. Novelty has a cost; only pay
  it where it's actually earning something.
- **Fitts's Law** — time to acquire a target is a function of its size and distance; targets need
  to be large enough and well-spaced. Mostly matters for the file tree (a real pointer target) —
  less relevant to the rest of the app now that the toolbar buttons are gone and typing is the
  primary interaction, since typing doesn't have a "target size" in the same sense a click does.
- **Hick's Law** — decision time increases with the number and complexity of available choices.
  **Direct validation** for removing the Tags/Wikilinks/Folder toolbar buttons in favor of typed
  `/commands` — fewer simultaneous visible choices, not just a cosmetic simplification.
- **Miller's Law** — short-term memory holds ~7±2 *chunks*, not items; Miller's own point (routinely
  misquoted) is about chunking content into groups, not a hard numeric limit on navigation items.
  Relevant to how the conversation log interleaves Ask/status/draft content — the color-coded
  separation (muted question / bright answer / accent status) already chunks these into visually
  distinct groups rather than one undifferentiated scroll of text.
- **Postel's Law** ("be conservative in what you send, liberal in what you accept") — **direct
  validation** for `_match_suggestion_kind()`'s natural-language fallback (accepting "search for
  wikilinks" as well as the exact `/wikilinks` command). This is the actual named principle behind
  that design choice, arrived at independently before reading it here.
- **Peak–End Rule** — people judge an experience by its most intense moment and its ending, not the
  average of the whole thing; negative moments are recalled more vividly than positive ones.
  Relevant to two things: (1) tonight's crash was a genuine "peak" moment — worth remembering that a
  single bad crash disproportionately colors the impression of the whole session, which is a real
  argument for the `remain-on-exit`/worker-context fixes being worth the effort they took; (2) forward-
  looking — the *end* of the wikilink walkthrough and the *end* of a `/draft` session are worth
  deliberately designing as good moments, not just letting them trail off.
- **Aesthetic–Usability Effect** — people perceive aesthetically pleasing designs as *more usable*,
  independent of whether they actually are, and tolerate minor usability issues more readily in a
  polished interface. Directly validates that tonight's visual-polish pass (colors, borders, spacing)
  wasn't vanity — it measurably changes how usable the thing will feel, not just how it looks. Also a
  caution: don't let a polished look mask a real usability problem during actual testing later.
- **von Restorff Effect** — an item that visually differs from similar surrounding items is the one
  that gets noticed and remembered (the "isolation effect"). **Direct validation** for the two-tone
  orange selected-file highlight in the tree — it works specifically *because* nothing else in the
  tree looks like it.
- **Tesler's Law** (conservation of complexity) — every process has an irreducible core of complexity
  that has to live *somewhere*, either absorbed by the system or pushed onto the user. Directly
  frames why `classify.py` exists as an LLM-assisted suggestion system rather than pure manual
  tagging: the complexity of picking tags/folder/wikilinks doesn't disappear, it just moves from the
  user typing them by hand to the system suggesting them for review.
- **Doherty Threshold** — system feedback within 400ms keeps productivity and attention; past ~1000ms,
  attention wanders and task performance degrades. A distinct, harder number than CLIG's "100ms
  perceived-instant" guidance — worth keeping both in mind as two points on the same curve, not
  conflating them. Directly the reason `StreamingText`'s token-by-token display exists at all: it
  keeps perceived response time near-zero even when real LLM generation takes several seconds.

**Read but not distilled into rules — low relevance to this project's actual shape:**
- "With Power Comes Responsibility" (persuasive/dark-pattern design ethics, operant conditioning,
  variable-reward mechanics) — meaningful chapter, but ChatUI is a personal single-user tool with no
  engagement-optimization or monetization incentive to guard against; there's no adversarial
  relationship between the tool and the person using it for these principles to caution against.
- "Applying Psychological Principles in Design" (closing chapter — building team awareness of these
  principles, design-review processes at organizational scale) — about *team* design practice, not
  applicable to a solo project with one developer and one user.

## Usability fundamentals (Don't Make Me Think, Revisited — Krug)

Krug's book is web-specific in its examples (Home pages, breadcrumbs, forms) but its actual laws are
about how people think and scan, which is medium-agnostic — most of it transfers to a TUI's chat log
and file tree the same way it transfers to a web page.

**Krug's First Law: "Don't make me think."** Every screen/prompt should be *self-evident* — obvious
at a glance, no thought required — or, failing that, *self-explanatory* — takes only a little thought.
The test: could someone with zero interest in the tool look at it and immediately say what it is. A
concrete, checkable distinction, not just "make it clear."

**Scanning, satisficing, and muddling through — the three facts of how people actually use an
interface, all of which apply just as much to a terminal log as a web page:**
- **We scan, we don't read.** Users skim for the words/phrases that match what they're after; large
  parts of any screen go unlooked-at. This is *why* color-coding the log (muted question / bright
  answer / accent status) matters — it's not decoration, it's what makes scanning possible at all.
  A monotone log would force actual reading to find the boundary between one exchange and the next.
- **We satisfice, we don't optimize.** People take the first reasonable option, not the best one, because
  weighing every option costs more than it's worth and guessing wrong is usually cheap to recover from.
  Directly the reasoning behind `_match_suggestion_kind()`'s loose keyword matching (accepting "tag" as
  well as "/tags") — the goal isn't to force the *exactly correct* phrasing, it's to accept whatever
  reasonable guess the user's first instinct produces.
- **We muddle through, we don't figure out how things work.** Most people use a tool successfully without
  understanding its actual mechanics, and *that's fine* — as long as muddling through actually works.
  Relevant to how much explanation any given feature needs: the goal isn't a user who understands
  Textual's worker-context model, it's a user who never has to think about it because it doesn't break.

**Krug's Second Law: "It doesn't matter how many times I have to click, as long as each click is a
mindless, unambiguous choice."** Click (or keystroke) *count* matters far less than click *difficulty* —
three effortless steps beat one ambiguous one. When a choice can't be made mindless, guidance should be
brief, timely, and unavoidable (placed exactly where the choice is being made, not in a separate help
screen). Directly relevant to the wikilink walkthrough about to be built: each apply/skip decision
should be a mindless yes/no on a single visible candidate, not a batch of ambiguous choices at once.

**Krug's Third Law: "Omit needless words... then omit half of what's left."** Get rid of "happy talk"
(welcoming/self-congratulatory text that conveys no information) and unnecessary instructions (nobody
reads them until muddling-through has already failed, and even then only if they're short). ChatUI's
existing status lines (`Drafting "X"...`, `[preview] X`) already lean terse rather than chatty — worth
holding that line deliberately as more UI text gets written, rather than let explanatory copy creep in.

**Clarity trumps consistency.** Following conventions is the default (see Jakob's Law from the Laws of
UX section above — same idea from a different author), but if breaking one makes something
significantly clearer, break it. Consistency is a tool for reducing thought, not a rule to obey for
its own sake.

**Navigation reveals content, tells you where you are, tells you how to use the site, and builds
confidence in whoever built it** — four jobs, not one. The vault tree is ChatUI's navigation in
exactly this sense: it's not just a way to find a file, it's how the user learns what's *in* the vault
and gets a sense that the tool is organized and trustworthy. Worth keeping in mind if the tree ever
feels like it's "just a file picker" — it's doing more work than that.

**The "Big Bang" idea — a first screen needs to answer, at a glance: what is this, what can I do here,
what do they have here, where do I start.** Krug's Home-page-specific concerns (stakeholder turf wars,
ad placement, registration) don't apply to a single-user personal tool with no stakeholders but the
user themself — but the underlying four questions are exactly what ChatUI's first-run screen needs to
answer wordlessly: the sidebar shows what's here (vault contents), the chat panel shows what you can
do (typed commands), and nothing should require reading a manual to get oriented.

**The myth of the Average User — worth noting as a rare place ChatUI has it easier than the book
assumes.** Krug's chapter 8 is about design teams arguing over what a mythical "average user" would
like, and the antidote being to stop debating and test with real people instead. ChatUI doesn't have
this problem in the first place: there's exactly one real user, and every design decision in this
project has been tested by asking them directly rather than guessing at a persona. The chapter's
actual conclusion — test, don't debate — still applies, though: tonight's whole workflow (build a
demo, get a real reaction, fix what's actually wrong) *is* Krug's "do-it-yourself usability testing"
in miniature, just continuous rather than scheduled.

**Do-it-yourself testing: test early, test small, test often.** Testing one user is 100% better than
testing none; testing one user early beats testing fifty near the end, because early problems are
cheap to fix and late ones aren't. Three participants surface most of the significant problems — you
don't need a large sample to learn something actionable. This directly describes what's already been
happening across this whole session (the demo iterations, the crash discovery, the border-junction
find) — worth continuing deliberately once `app.py` is real, rather than treating "testing" as a
separate phase that happens after the code is done.

**The reservoir of goodwill.** Every interaction either spends or replenishes a user's patience with a
tool; the reservoir is personal and situational (some people start more patient than others, and a bad
day elsewhere lowers everyone's starting level), and a single bad moment can empty it regardless of
how much good came before. This is the same underlying idea as the Peak–End Rule already in the Laws
of UX section, from a different angle — worth reading the two together. Two concrete asks that pair
directly with what's already in `clig_notes.md`'s error-handling guidance: **make it easy to recover
from errors**, and **when in doubt, apologize** — a message that acknowledges the inconvenience reads
very differently than a bare failure notice, even when neither can actually fix the underlying problem.

**Note on chapters 10, 12, 13 (skimmed, not fully distilled):** Ch. 10 (Mobile) is entirely about
touch-target sizing and responsive breakpoints for phone screens — not applicable, ChatUI has no
mobile surface. Ch. 12 (Accessibility) is real and important in principle, but its concrete techniques
(ARIA labels, alt text, HTML focus order, screen-reader markup) are web-specific; TUI accessibility is
a genuinely different, narrower topic (terminal screen-reader support) that would need its own
research rather than a transplant from this chapter — flagged as a real gap, not a dismissal. Ch. 13
(Guide for the Perplexed) is about getting organizational buy-in for usability practices at a company
— not applicable to a solo project, same reasoning as Laws of UX's closing chapter.

## Foundational vocabulary (The Design of Everyday Things — Norman)

This is the book Nielsen's heuristics, Krug's book, and this project's own `clig_further_reading_notes.md`
all cite secondhand — reading it directly turned out to be worth it: it's where the actual
*vocabulary* for talking about any of this comes from, not just more rules layered on top of the
same ideas. Chapters 1–5 (the psychology/design-principles core) read in full; 6–7 (design process
and business strategy) skimmed — see the note at the end of this section for why.

**Affordances vs. signifiers — the single most useful distinction in the book, and one this project
has been conflating.** An *affordance* is what an object actually lets you do (a chair affords
sitting; a screen affords touching anywhere). A *signifier* is the perceivable clue telling you
*where* and *how* to act (a push-plate on a door, an icon showing where to swipe). Affordances exist
whether or not they're visible; signifiers are what make them discoverable. Applied to ChatUI: the
whole tree *affords* selection everywhere, but the two-tone highlight and the muted/bright color split
are signifiers — they don't create new capability, they make an existing one findable at a glance.
Worth being deliberate about this distinction going forward: when something doesn't feel discoverable,
the question is specifically "does it need a new affordance, or just a better signifier for the one
it already has" — usually the latter, and much cheaper to fix.

**Mapping — the relationship between a control and its effect should exploit spatial/logical
correspondence wherever possible**, so the relationship needs no memorizing (rotate a wheel clockwise,
the car goes right). For a text-only TUI, ChatUI's most literal mapping opportunity is the tree's own
structure mirroring the vault's actual folder layout — already true — and worth checking future
controls against: does this control's *position or shape* suggest its effect, or does its meaning have
to be memorized separately? Purely typed commands (`/draft`, `/done`) have zero natural mapping — this
is a real, structural limitation of a command-line interaction style, not a flaw, but a reminder that
CLIG's convention-following recommendation (Jakob's Law, again) is carrying real weight here: since a
typed command can't be *mapped*, it can at best be *conventional*, so verb choice matters more than it
would in a spatial interface.

**Feedback must be immediate, informative, and not excessive — all three, not just one.** Feedback
that's slow, or present but uninterpretable (a bare beep), or so constant it becomes noise, are all
named as failures on equal footing with having none at all. Directly validates `StreamingText`'s
token-by-token display (immediate + informative) and argues against ever adding a generic "processing..."
spinner with no further detail (informative-but-thin) once real content is available to stream instead.

**Conceptual models don't need to be accurate, only useful.** A user's mental model of *how* `/draft`
or `/classify` works internally (LLM calls, retrieval, file writes) doesn't need to be correct — it
needs to be *coherent enough to predict what will happen next*. This reframes how much internal
mechanism ever needs to surface in the UI: not "explain what's really happening," but "give the user
a simplified story that reliably predicts the outcome." The additive-draft-with-a-divider design
already does this — the user doesn't need to know anything about how `revise_draft()` generates a
full rewrite internally; the divider tells a simpler, sufficient story: "here's what's old, here's
what's new."

**The Gulfs of Execution and Evaluation — arguably the most directly applicable framework in the
whole book to `app.py`'s remaining work.** Every interaction has two gaps: the *Gulf of Execution*
(figuring out how to do what you want) and the *Gulf of Evaluation* (figuring out what just happened).
Execution is bridged by signifiers, constraints, mappings, and a conceptual model; evaluation is
bridged by feedback and a conceptual model. Concretely, for the wikilink walkthrough about to be
built: the execution side is "how do I apply or skip this suggestion" (needs an obvious, low-effort
answer — a single keypress, not a typed command); the evaluation side is "did that work, and what's
left" (needs to be visible immediately — how many suggestions remain, which one is now highlighted).
Design both sides deliberately, not just the execution half.

**The Seven Stages of Action** — goal → plan → specify → perform (execution) → perceive → interpret →
compare (evaluation). A useful checklist for any new interaction loop: does the user have a clear goal
at each point, is there always a next action to specify, and — critically — is there always something
to *perceive* afterward that lets them compare the result against what they wanted? A loop that goes
silent after "perform" (no perceivable change, nothing to interpret) breaks at exactly the evaluation
half of the cycle, which is the half ChatUI's own error-handling and status-line work has mostly been
about all evening.

**Knowledge in the head vs. knowledge in the world.** People need less to memorize when the interface
itself carries the information — a labeled key beats a memorized keyboard layout. This directly
frames a real design axis for `app.py`: `/commands` typed from memory are "knowledge in the head";
the footer showing active keybindings, the sidebar showing vault structure, and the statusbar showing
current model/web state are all "knowledge in the world" that reduces what has to be remembered. Worth
auditing any future feature for which side of this line it lands on — a feature that only works if the
user remembers a command with no visible reminder anywhere is asking for more head-knowledge than it
needs to.

**Four kinds of constraints that narrow down what actions make sense: physical, cultural, semantic,
logical.** Physical constraints don't really exist in a TUI (no literal shapes to prevent wrong
actions), but the other three do: *cultural* (readline bindings, `ctrl+c` conventions — same territory
as Jakob's Law), *semantic* (a file can only sensibly be "drafted" or "classified," not both as the
same action — the four verbs are already semantically distinct enough not to be confused), *logical*
(once three of four suggested wikilinks have been resolved, there's only one place the last decision
can apply — relevant to how the walkthrough should present "last one" differently, if at all, from
"more remaining").

**Slips vs. mistakes — a real distinction with different design responses, not just two words for
"error."** A *slip* is the right goal, wrong execution (typing `/daft` instead of `/draft` — a typo).
A *mistake* is the wrong goal or plan entirely (running `/classify` while thinking a different file is
active than the one actually is). Slips are fixed by better constraints/confirmation at the point of
action (e.g., recognizing near-miss command spellings); mistakes are fixed by better feedback about
*system state before the action is taken* (e.g., always showing which file is currently active, so
the plan is formed correctly in the first place). Worth keeping this distinction in mind once `app.py`
handles bad input — a typo and a genuine misunderstanding of what's about to happen call for different
fixes, not the same generic error message.

**Design principles for dealing with error, stated directly:** put knowledge in the world rather than
requiring it all in the head; use constraints (physical/logical/semantic/cultural) to narrow the field
of plausible-but-wrong actions; bridge both gulfs — feedforward (what are my options) on the execution
side, feedback (what just happened) on the evaluation side. Treat "human error" as a signal that the
design left a gap, not a user failing — the same reframe already present in `clig_notes.md`'s "an
error is a documentation opportunity" line, from a different source, converging on the same point.

**"Solve the correct problem" (Ch. 6, briefly).** Norman's rule for himself as a consultant: never
solve the problem you were literally handed, because it's usually a symptom, not the root cause. This
is exactly what happened at the start of this whole rebuild — the old app's problem wasn't "the batch
review UI needs polishing," it was "this doesn't map to any real verb the user actually performs,"
and the four-verb redefinition came from asking that deeper question rather than patching the surface
one.

**Note on chapters 6–7 (skimmed, not fully distilled):** Ch. 6 (Design Thinking) and Ch. 7 (Design in
the World of Business) are about running a design *process* inside an organization — the double-diamond
model, competitive forces, how long it takes to ship a new product at a company. Like the "team
awareness" and "organizational buy-in" chapters skipped at the end of Laws of UX and Don't Make Me
Think, this is about team/company-scale practice, not applicable to a solo project with one developer
and one user. The single idea pulled forward from Ch. 6 ("solve the correct problem," above) is the
one piece that transfers independent of team size.

## Backlog — not yet distilled

**Refactoring UI, skipped chapters (read the TOC/skimmed, not fully distilled — genuinely not
applicable to a monospace terminal grid, not a scoping shortcut):**
- Ch. "Creating Depth" (light source, shadows, layering) — requires shadow/blur rendering a terminal
  character grid can't do. Already established as a hard medium limitation in this project (see the
  "is Textual too limited" discussion in the plan doc).
- Ch. "Working with Images" (photography, image contrast, user-uploaded content) — no images in a
  TUI's character grid.
- Ch. "Leveling Up" (closing chapter — general practice advice: study designs you admire, rebuild
  interfaces from scratch to learn their tricks) — read in full, genuinely just general advice, not
  distilled into a rule since there's no concrete guidance to extract.

No further books queued. This UI research pass (Refactoring UI, Laws of UX, Don't Make Me Think, The
Design of Everyday Things) is now complete; future additions to this doc should come from applying
these principles to real `app.py` work, not from further reading.
