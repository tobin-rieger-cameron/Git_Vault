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
# primary accent rather than a variant of it.
ADDITION = "#7fae6b"     # draft additions only; never reused for anything else

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

PADDING_TIGHT = "0 1"         # horizontal-only breathing room — statusbar
PADDING_COMFORTABLE = "1 2"   # full breathing room — preview body text
