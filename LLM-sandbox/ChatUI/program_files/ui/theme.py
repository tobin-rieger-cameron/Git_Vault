"""The amber-phosphor terminal palette and spacing scale, named once so widgets share them."""

from __future__ import annotations

# Neutral scale: warm brown-grey, darkest to lightest.
BG = "#14110d"           # darkest — screen/pane background
SURFACE = "#1c1812"      # one step lighter — header, footer, statusbar, dialogs, grouped strips
BORDER = "#3a2f20"       # dividers between panes
MUTED = "#8c8272"        # secondary text: folder names, hints, dividers, status captions
TEXT = "#e8dcc8"         # default body text
BRIGHT = "#f0e9d8"       # primary text: file names, assistant answers — the "this matters" tier

# Accent scale: amber, three shades.
ACCENT = "#d98f3b"       # badges, caret, cursor background, highlights, borders that must pop
ACCENT_DARK = "#5c3a14"  # text sitting on an ACCENT background — two-tone orange, not orange-on-black
ACCENT_MUTED = "#a8825a" # faded amber for de-emphasized detail within a status line — the accent
                         # family's equivalent of MUTED, same "fade the secondary part" idea

# Semantic — deliberately its own hue, not a shade of ACCENT, so it reads as distinct from the
# primary accent rather than a variant of it. Green always means "added, not yet settled"; red
# always means "stale, needs cleanup" — shared across draft diffs, tag sync, and the file tree.
ADDITION = "#7fae6b"     # draft additions; a vault file that exists on disk but isn't in the
                         # ingest manifest yet (FilePicker)
TAG = "#6d93c8"          # tag text in suggestion checklists — a cool blue against the otherwise
                         # all-warm palette so tags read as their own category, not more prose
TAG_REMOVE = "#c2685f"   # stale-tag-being-removed text; a manifest path with no file on disk
                         # anymore (FilePicker) — a muted red, its own hue from TAG's blue and
                         # ACCENT's orange so an addition and a removal never read the same

# Spacing scale (character cells — the terminal's own native unit).
BORDER_ROW = 1                # a single ─ or │ divider row/column
BREATHING_ROW = 1             # one spare blank row so content doesn't crowd the strip's edge
SIDEBAR_HEAD_HEIGHT = 2       # 1 content row ("vault ... f2") + 1 BREATHING_ROW (no border row;
                              # grouped by SURFACE color instead)
INPUT_BAR_HEIGHT = 3          # 1 BORDER_ROW + 1 content row ("> _") + 1 BREATHING_ROW
SIDEBAR_WIDTH = 34
CHAT_WIDTH = 70  # near the top of the ~45-75 char readable line-length range; wrapped status
                 # lines felt cramped lower down
CARET_WIDTH = 2
CHECKLIST_MAX_HEIGHT = 20  # a batch folder-tags list can run to dozens of files; capped only so
                           # it can't crowd out #inputbar entirely, not to keep it document-small
CHECKLIST_NAME_RATIO = 0.4  # folder-tags checklist's left (filename) column, as a share of
                             # CHAT_WIDTH — the remaining ~60% goes to the tags column; longer
                             # names truncate with an ellipsis (3 more chars) past that width
CHECKLIST_NAME_WIDTH = round(CHAT_WIDTH * CHECKLIST_NAME_RATIO)

PADDING_TIGHT = "0 1"         # horizontal-only breathing room — statusbar
PADDING_COMFORTABLE = "1 2"   # full breathing room — preview body text
