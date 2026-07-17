"""Throwaway layout demo v2 — NOT part of the chatui package, delete before this branch ships.

Real FilePicker/StreamingText widgets, real Vault content on click. /draft and Ask are faked
(canned text, simulated token-by-token reveal) so this runs with no Ollama/ChromaDB needed.

Changes from v1 per user feedback:
- Sidebar (tree) is collapsible, slides fully out of view with f2 (lazyvim nvim-tree style)
- Order is now: sidebar | file preview | chat (was: sidebar+chat | preview)
- Scrollbars hidden everywhere
- /draft is additive: original body stays visible, new content appends below a divider
  instead of replacing the pane (so nothing already written disappears mid-revision)

Changes from v2:
- No buttons — "/tags"/"/wikilinks"/"/folder" or a plain mention of the same word triggers the
  suggestion popup instead (styled like Textual's own built-in ctrl+c quit-confirmation dialog)
- Command palette stays on ctrl+p (Textual's default) — rebinding to ctrl+c was considered and
  rejected: ctrl+c already has a plain (non-priority) binding to the quit-confirmation dialog,
  and Textual always registers COMMAND_PALETTE_BINDING with priority=True, so reusing ctrl+c
  would have made the palette win and silently shadowed the quit-confirmation the user liked.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Iterable

from rich.text import Text
from textual import events, on
from textual.app import App, ComposeResult, SystemCommand
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.suggester import SuggestFromList
from textual.widgets import Header, Input, Label, RichLog, Static, Tree

from chatui.ui import theme
from chatui.ui.picker import FilePicker
from chatui.ui.streaming import StreamingText
from chatui.vault import Vault

# Priority order matters: SuggestFromList returns the first prefix match, so "/draft" (the
# most frequent command) is listed ahead of "/done" for the shared "/d" prefix.
_COMMANDS = ["/draft", "/done", "/tags", "/wikilinks", "/folder", "/explorer", "/palette"]

_CANNED_ADDITION = (
    "Photosynthesis is the process by which green plants, algae, and some bacteria "
    "convert light energy into chemical energy, producing glucose and oxygen from "
    "carbon dioxide and water."
)

_CANNED_SUGGESTIONS = {
    "tags": ["biology", "energy", "cellular-processes"],
    # Phrases chosen to actually appear in the Photosynthesis example text (original body
    # has "glucose"; the streamed addition adds "carbon dioxide" and "Chlorophyll") so the
    # walkthrough's highlight-in-context has something real to find, same as classify.py's
    # real suggestions will always be substrings of the file they were generated from.
    "wikilinks": ["glucose", "carbon dioxide", "Chlorophyll"],
}


def _highlight_candidate(text: str, candidate: str) -> tuple[Text, bool, int]:
    """Return text with candidate's first occurrence highlighted, whether it was found, and
    the character offset it starts at (0 if not found, for scrolling to the top instead)."""
    start = text.lower().find(candidate.lower())
    if start == -1:
        return Text(text), False, 0
    end = start + len(candidate)
    result = Text(text[:start])
    result.append(text[start:end], style=f"bold {theme.ACCENT_DARK} on {theme.ACCENT}")
    result.append(text[end:])
    return result, True, start


def _match_suggestion_kind(text: str) -> str | None:
    """Recognize "/tags"/"/wikilinks"/"/folder" or a plain-language mention of the same, e.g.
    "search for wikilinks" — no buttons; typed commands and natural language are the only UI."""
    lowered = text.lower()
    if lowered in ("/tags", "/wikilinks", "/folder"):
        return lowered[1:]
    if "wikilink" in lowered:
        return "wikilinks"
    if "folder" in lowered:
        return "folder"
    if "tag" in lowered:
        return "tags"
    return None


def _write_hint(log: RichLog, text: str) -> None:
    log.write(Text(text, style=theme.MUTED))


def _write_you(log: RichLog, text: str) -> None:
    log.write(Text.assemble(("› ", f"bold {theme.ACCENT}"), (text, theme.MUTED)))


def _write_answer(log: RichLog, text: str) -> None:
    log.write(Text(text, style=theme.BRIGHT))


def _write_status(log: RichLog, text: str) -> None:
    """Bright accent up to the first ":", faded accent after it — the label is the headline,
    everything past the colon is supporting detail (same idea as MUTED fading TEXT, applied
    within the accent family itself)."""
    label, sep, detail = text.partition(":")
    if not sep:
        log.write(Text(text, style=theme.ACCENT))
        return
    log.write(Text.assemble((label + sep, theme.ACCENT), (detail, theme.ACCENT_MUTED)))


class SuggestionPopup(ModalScreen[bool]):
    """Same visual pattern as Textual's built-in quit-confirmation dialog."""

    DEFAULT_CSS = (
        """
    SuggestionPopup {
        align: center middle;
        background: rgba(20, 17, 13, 0.6);
    }
    #dialog {
        width: 46; height: auto; padding: %(padding)s;
        border: thick %(accent)s; background: %(surface)s; color: %(text)s;
    }
    #dialog Static { margin-bottom: 1; }
    """
        % {"padding": theme.PADDING_COMFORTABLE, "accent": theme.ACCENT, "surface": theme.SURFACE, "text": theme.TEXT}
    )

    def __init__(self, title: str, items: list[str]) -> None:
        super().__init__()
        self.title_text = title
        self.items = items

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static(f"[b]{self.title_text}[/b]")
            for item in self.items:
                yield Static(f"  + {item}")
            yield Static("[dim]enter: accept all    escape: cancel[/dim]")

    def on_key(self, event) -> None:
        if event.key == "enter":
            self.dismiss(True)
        elif event.key == "escape":
            self.dismiss(False)


class DemoApp(App):
    # Amber-phosphor terminal palette, matching the visual-comp artifact — every value below
    # is named once in chatui/ui/theme.py, not hand-picked fresh per rule (see "define systems
    # in advance" in config/ui_style_guide.md).
    CSS = (
        """
    Screen { background: %(bg)s; color: %(text)s; }
    Header { background: %(surface)s; color: %(text)s; }
    HeaderTitle { content-align: left middle; }

    #statusbar { height: %(border_row)s; background: %(surface)s; color: %(muted)s; padding: %(padding_tight)s; }
    #statusbar .value { color: %(accent)s; text-style: bold; }

    #sidebar { width: %(sidebar_width)s; border-right: solid %(border)s; background: %(bg)s; }
    #sidebar.collapsed { width: 0; border-right: none; display: none; }
    /* No border-bottom: it would meet #sidebar's own border-right at a right angle, and
       Textual draws each widget's border independently with no shared corner glyph — you'd
       get a bare │ sitting next to a bare ─ instead of a proper ┬ joint. The surface color
       does the grouping instead, same idea as #inputbar below. */
    #file-search { height: %(sidebar_head_height)s; background: %(surface)s; color: %(text)s; border: none; padding: 0 1; }
    #file-search:focus { background-tint: transparent; }
    FilePicker { height: 1fr; scrollbar-size: 0 0; background: %(bg)s; color: %(text)s; }
    /* Selected file: bright accent background, a darker amber-brown text — two shades of
       orange, not orange-on-black, per the artifact's active-file treatment. */
    FilePicker > .tree--cursor { background: %(accent)s; color: %(accent_dark)s; text-style: bold; }
    FilePicker > .tree--highlight { color: %(accent)s; }

    #middle { width: 1fr; border-right: solid %(border)s; background: %(bg)s; }
    #preview-scroll { scrollbar-size: 0 0; background: %(bg)s; }
    #preview-body { padding: %(padding_comfortable)s; background: %(bg)s; color: %(text)s; }

    #chat { width: %(chat_width)s; background: %(bg)s; }
    #log { height: 1fr; scrollbar-size: 0 0; background: %(bg)s; color: %(text)s; }
    /* height 3, not 2: 1 for the border line, 1 for the "> _" row, 1 spare so the prompt
       isn't crammed right against the border — the earlier 2-row version left no breathing
       room below the text itself. */
    /* Surface color, not a border-top — same reasoning as #sidebar-head above. */
    #inputbar { height: %(input_bar_height)s; padding: 0 0 %(breathing_row)s 0; background: %(surface)s; }
    #caret { width: %(caret_width)s; color: %(accent)s; text-style: bold; }
    #cmd { background: %(surface)s; color: %(text)s; border: none; padding: 0; }
    /* Input applies a background-tint on :focus by default (a built-in "focus glow"), which
       shows as a mismatched patch since this input is focused almost all the time here. */
    #cmd:focus { background-tint: transparent; }
    """
        % {
            "bg": theme.BG,
            "surface": theme.SURFACE,
            "border": theme.BORDER,
            "muted": theme.MUTED,
            "text": theme.TEXT,
            "accent": theme.ACCENT,
            "accent_dark": theme.ACCENT_DARK,
            "sidebar_width": theme.SIDEBAR_WIDTH,
            "chat_width": theme.CHAT_WIDTH,
            "caret_width": theme.CARET_WIDTH,
            "border_row": theme.BORDER_ROW,
            "breathing_row": theme.BREATHING_ROW,
            "sidebar_head_height": theme.SIDEBAR_HEAD_HEIGHT,
            "input_bar_height": theme.INPUT_BAR_HEIGHT,
            "padding_tight": theme.PADDING_TIGHT,
            "padding_comfortable": theme.PADDING_COMFORTABLE,
        }
    )

    # ctrl+e collides with Input's built-in "go to end of line" binding, so it never reaches
    # the App while the input box has focus (which is almost always) — f2 is unclaimed.
    # ctrl+f is the near-universal "find" convention (browsers, editors) per Jakob's Law —
    # nothing else in this app claims it.
    # tab needs priority=True: Screen has its own plain "tab" -> "app.focus_next" binding
    # (textual/screen.py), which is resolved through Textual's binding system independently
    # of message-based on_key handlers — stopping the Key event there does not block it, only
    # a higher-priority binding does (same mechanism as COMMAND_PALETTE_BINDING, confirmed by
    # testing: without priority=True, Tab completed the text but focus still moved away).
    BINDINGS = [
        Binding("f2", "toggle_sidebar", "Toggle explorer"),
        Binding("ctrl+f", "focus_search", "Find file"),
        Binding("tab", "accept_suggestion_or_focus_next", "Accept suggestion", priority=True, show=False),
    ]

    def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
        # Drop "Theme" from the palette: every color here is a hardcoded hex value, not a
        # theme variable, so switching themes visibly does nothing to this app.
        for command in super().get_system_commands(screen):
            if command.title != "Theme":
                yield command

    def __init__(self, vault: Vault) -> None:
        super().__init__()
        self.vault = vault
        self._original_body = ""
        self._preview_text = ""
        self._active_title = ""  # whatever's currently previewed — /draft (bare) targets this
        self._wikilink_queue: list[str] = []
        self._wikilink_index = 0

    def compose(self) -> ComposeResult:
        yield Header(icon="")  # the default "⭘" icon has no function here — just noise
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Input(id="file-search", placeholder="search files…")
                yield FilePicker(self.vault)
            with Vertical(id="middle"):
                with VerticalScroll(id="preview-scroll"):
                    yield StreamingText(id="preview-body")
            with Vertical(id="chat"):
                # min_width defaults to 78 — RichLog would lay text out assuming at least that
                # many columns regardless of the pane's real ~50-wide size, and the overflow
                # would scroll off horizontally (invisibly, since scrollbars are hidden) rather
                # than actually wrapping. min_width=1 makes it wrap to whatever width it's given.
                yield RichLog(id="log", wrap=True, min_width=1, markup=False)
                with Horizontal(id="inputbar"):
                    yield Label("›", id="caret")
                    yield Input(id="cmd", placeholder="_", suggester=SuggestFromList(_COMMANDS, case_sensitive=False))
        yield Static(id="statusbar")

    def on_mount(self) -> None:
        self.title = "chatui — Knowledge/"
        log = self.query_one("#log", RichLog)
        _write_hint(log, "/explorer or f2 toggles the file tree. ctrl+f or click search to find a file.")
        _write_hint(log, "Click a file (or jump to one), then /draft to start revising it — additive,")
        _write_hint(log, "nothing gets overwritten. /tags, /wikilinks, /folder, /palette also work.")
        self.query_one("#cmd", Input).focus()
        self._update_statusbar()

    def _update_statusbar(self) -> None:
        n = len(self.vault.list_files())
        self.query_one("#statusbar", Static).update(
            Text.assemble(
                ("model: ", theme.MUTED), ("llama3.1:8b", f"{theme.ACCENT} bold"), ("   web: off   vault: ", theme.MUTED),
                (f"{n} files", f"{theme.ACCENT} bold"),
            )
        )

    def action_toggle_sidebar(self) -> None:
        self.query_one("#sidebar").toggle_class("collapsed")

    def action_focus_search(self) -> None:
        self.query_one("#file-search", Input).focus()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        picker = self.query_one(FilePicker)
        path = picker.selected_path()
        if path is not None:
            self._preview_file(path)

    def _preview_file(self, path: Path) -> None:
        # No log line here on purpose — the preview pane updating *is* the feedback; a
        # "[preview] X" status line would just be restating what's already visually obvious.
        file = self.vault.load_file(path)
        self._original_body = file.body
        self._preview_text = file.body
        self._active_title = file.title
        self.query_one(StreamingText).show(file.body)
        self.query_one("#cmd", Input).focus()

    @on(Input.Changed, "#file-search")
    def on_search_changed(self, event: Input.Changed) -> None:
        self.query_one(FilePicker).filter_files(event.value)

    @on(Input.Submitted, "#file-search")
    def on_search_submitted(self, event: Input.Submitted) -> None:
        picker = self.query_one(FilePicker)
        best_match = picker.filter_files(event.value)
        event.input.value = ""
        picker.filter_files("")  # back to the full tree once we've jumped
        if best_match is not None:
            self._preview_file(best_match)
        else:
            self.query_one("#cmd", Input).focus()

    def action_accept_suggestion_or_focus_next(self) -> None:
        # Right-arrow's own accept-suggestion behavior is exactly what Tab should also trigger
        # here — completing a command is the more common intent for this input than tabbing
        # away from it. cmd._suggestion is private (Input has no public "is one pending"
        # accessor), acceptable for a throwaway demo file.
        cmd = self.query_one("#cmd", Input)
        if self.focused is cmd and cmd._suggestion:
            cmd.action_cursor_right()
        else:
            self.screen.focus_next()

    async def on_key(self, event: events.Key) -> None:
        cmd = self.query_one("#cmd", Input)
        # Escape while searching clears the query and hands focus back to the main input,
        # rather than leaving a stale filter and an orphaned focus — an escape route should
        # always work (CLIG), and this is the one place in the app a second Input can steal
        # focus from the primary one.
        search = self.query_one("#file-search", Input)
        if event.key == "escape" and self.focused is search:
            search.value = ""
            self.query_one(FilePicker).filter_files("")
            cmd.focus()
            event.stop()

    # push_screen_wait requires a worker context (Textual raises NoActiveWorker otherwise) —
    # this is the exact NoActiveWorker pitfall CLAUDE.md already documents from the old app.
    async def _show_suggestion_popup(self, kind: str) -> None:
        if kind == "folder":
            accepted = await self.push_screen_wait(SuggestionPopup("Suggested folder", ["600-applied-sciences"]))
        else:
            accepted = await self.push_screen_wait(SuggestionPopup(f"Suggested {kind}", _CANNED_SUGGESTIONS[kind]))
        _write_status(self.query_one("#log", RichLog), f"{kind}: {'accepted' if accepted else 'cancelled'} (demo)")

    def _scroll_preview_to(self, offset: int) -> None:
        """Scroll #preview-scroll so the character at offset (wrap-aware) is centered in view."""
        preview = self.query_one(StreamingText)
        scroll = self.query_one("#preview-scroll", VerticalScroll)
        width = max(1, preview.size.width - 4)  # #preview-body's "padding: 1 2" eats 4 cols
        row = len(Text(self._preview_text[:offset]).wrap(self.console, width)) - 1
        scroll.scroll_to(y=max(0, row - scroll.size.height // 2), animate=True)

    def _start_wikilink_walkthrough(self) -> None:
        """One candidate at a time, highlighted in the preview — not a popup listing all of
        them, since each one corresponds to an actual span of text (unlike tags/folder)."""
        self._wikilink_queue = list(_CANNED_SUGGESTIONS["wikilinks"])
        self._wikilink_index = 0
        self._advance_wikilink()

    def _advance_wikilink(self) -> None:
        log = self.query_one("#log", RichLog)
        cmd = self.query_one("#cmd", Input)
        if self._wikilink_index >= len(self._wikilink_queue):
            _write_status(log, "wikilinks: walkthrough done (demo)")
            self._wikilink_queue = []
            cmd.placeholder = "_"
            self.query_one(StreamingText).show(self._preview_text)
            return
        candidate = self._wikilink_queue[self._wikilink_index]
        highlighted, found, offset = _highlight_candidate(self._preview_text, candidate)
        self.query_one(StreamingText).update(highlighted)
        if found:
            self._scroll_preview_to(offset)
        position = f"{self._wikilink_index + 1}/{len(self._wikilink_queue)}"
        if found:
            _write_status(log, f'wikilink {position}: "{candidate}" — enter: apply   n: skip')
        else:
            _write_status(log, f'wikilink {position}: "{candidate}" (not found in text) — enter: apply anyway   n: skip')
        cmd.placeholder = "enter: apply   n: skip"

    def _resolve_wikilink(self, answer: str) -> None:
        # Only a recognized answer advances the queue — an unmatched typo (a slip, not a
        # mistake, per Norman) re-asks instead of silently applying. Applying is the one
        # action here that isn't a no-op, so it shouldn't be the default for "didn't understand."
        candidate = self._wikilink_queue[self._wikilink_index]
        log = self.query_one("#log", RichLog)
        lowered = answer.lower()
        if lowered in ("", "y", "yes", "apply"):
            _write_status(log, f'"{candidate}": applied — [[{candidate}]] added to See Also (demo)')
        elif lowered in ("n", "no", "skip"):
            _write_status(log, f'"{candidate}": skipped (demo)')
        else:
            _write_status(log, f'not understood: "{answer}" — enter: apply   n: skip')
            return
        self._wikilink_index += 1
        self._advance_wikilink()

    @on(Input.Submitted, "#cmd")
    async def on_cmd_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        log = self.query_one("#log", RichLog)
        preview = self.query_one(StreamingText)
        event.input.value = ""

        if self._wikilink_queue:
            if text == "/done":
                # Escape hatch: abandon the whole walkthrough, not just the current candidate.
                _write_you(log, text)
                _write_status(log, "wikilinks: walkthrough cancelled (demo)")
                self._wikilink_queue = []
                self.query_one("#cmd", Input).placeholder = "_"
                self.query_one(StreamingText).show(self._preview_text)
                return
            # Bare Enter = apply (the mindless default per Krug's Second Law — a walkthrough
            # answer should need at most one keystroke, "n", to deviate from that default).
            _write_you(log, text or "(apply)")
            self._resolve_wikilink(text)
            return

        if not text:
            return
        _write_you(log, text)
        if text == "/done":
            _write_status(log, "Draft ended.")
            return
        if text == "/explorer":
            self.action_toggle_sidebar()
            return
        if text == "/palette":
            self.action_command_palette()
            return
        if text == "/draft":
            # Bare /draft targets whatever's currently previewed — no separate lookup step,
            # so there's no way to draft something other than what's actually on screen.
            if not self._active_title:
                _write_status(log, "nothing to draft: click a file, or search for one, first")
                return
            _write_status(log, f'Drafting "{self._active_title}"... (additive — type /done to stop)')
            await self._stream_addition(preview)
            return
        if text.startswith("/draft "):
            # A named subject starts a brand-new, not-yet-existing draft — this still goes
            # through the same preview state everything else reads from, so it's immediately
            # the active target too, same as clicking or jumping to an existing file would be.
            subject = text[len("/draft "):]
            self._original_body = ""
            self._preview_text = ""
            self._active_title = subject
            preview.show("")
            _write_status(log, f'Drafting "{subject}"... (additive — type /done to stop)')
            await self._stream_addition(preview)
            return

        kind = _match_suggestion_kind(text)
        if kind == "wikilinks":
            self._start_wikilink_walkthrough()
            return
        if kind is not None:
            self.run_worker(self._show_suggestion_popup(kind))
            return

        _write_answer(log, "(demo — not a real answer) This is where ask() output would stream in.")

    async def _stream_addition(self, preview: StreamingText) -> None:
        divider_plain = "\n\n── proposed addition ──\n\n"
        divider = Text(divider_plain, style=theme.MUTED)
        original = Text(self._original_body)
        preview.show(self._original_body)
        added = ""
        for word in _CANNED_ADDITION.split(" "):
            added += word + " "
            preview.update(original + divider + Text(added, style=theme.ADDITION))
            await asyncio.sleep(0.04)
        self._preview_text = self._original_body + divider_plain + added


if __name__ == "__main__":
    vault = Vault(root=Path(__file__).parent.parent / "Knowledge")
    DemoApp(vault).run()
