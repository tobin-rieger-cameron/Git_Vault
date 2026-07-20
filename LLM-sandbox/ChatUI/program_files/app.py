# LLM-sandbox/ChatUI/program_files/app.py
"""Textual shell; dispatches four modules: ask, classify, draft, review"""

from __future__ import annotations

import asyncio
import difflib
import logging
from datetime import timedelta
from pathlib import Path
from typing import Iterable

from rich.text import Text
from textual import events, on
from textual.app import App, ComposeResult, SystemCommand
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.suggester import SuggestFromList
from textual.widgets import Header, Input, Label, RichLog, Static, Tree

from program_files import ask, classify, draft, review
from program_files.utils.config import Settings
from program_files.utils.errors import ChatUIError
from program_files.utils.llm import ModelClient
from program_files.utils.models import ClassificationSuggestion, File, FolderTagChange, ReviewQuestion
from program_files.utils.retrieval import Retriever
from program_files.ui import theme
from program_files.ui.checklist import SuggestionChecklist
from program_files.ui.picker import FilePicker
from program_files.ui.streaming import StreamingText
from program_files.utils.vault import Vault, find_wikilinks, normalize_link_target, render_frontmatter

_log = logging.getLogger(__name__)

_COMMANDS = [
    "/draft", "/done", "/tags", "/wikilinks", "/folder", "/review",
    "/ingest", "/web", "/model", "/explorer", "/palette",
]

_FILE_TREE_POLL_SECONDS = 2.0  # how often the sidebar re-scans disk for files added/removed
                               # outside the app; list_files() re-parses every file, so this
                               # trades a little steady background cost for near-live updates


def _diff_highlight(old: str, new: str) -> Text:
    """Return inserted or changed spans styled in color."""
    matcher = difflib.SequenceMatcher(None, old, new, autojunk=False)
    result = Text()
    for opcode, _i1, _i2, j1, j2 in matcher.get_opcodes():
        segment = new[j1:j2]
        if not segment:
            continue
        result.append(segment, style=theme.ADDITION if opcode in ("insert", "replace") else theme.TEXT)
    return result


def _truncate(text: str, limit: int) -> str:
    """Cut text to limit chars, appending "..." (so the visible result can run 3 chars longer)."""
    return text if len(text) <= limit else f"{text[:limit]}..."


def _match_suggestion_kind(text: str) -> str | None:
    text = text.lower()
    if text in ("/tags", "/wikilinks", "/folder"):
        return text[1:]
    if "wikilink" in text:
        return "wikilinks"
    if "folder" in text:
        return "folder"
    if "tag" in text:
        return "tags"
    return None


def _write_hint(log: RichLog, text: str) -> None:
    log.write(Text(text, style=theme.MUTED))


def _write_you(log: RichLog, text: str) -> None:
    log.write(Text.assemble(("› ", f"bold {theme.ACCENT}"), (text, theme.MUTED)))


def _write_answer(log: RichLog, text: str) -> None:
    log.write(Text(text, style=theme.BRIGHT))


def _write_status(log: RichLog, text: str) -> None:
    """Write stylized text."""
    label, sep, detail = text.partition(":")
    if not sep:
        log.write(Text(text, style=theme.ACCENT))
        return
    log.write(Text.assemble((label + sep, theme.ACCENT), (detail, theme.ACCENT_MUTED)))


class ChatApp(App):
    """Textual application shell."""

    # Every color and size below is a named value from program_files.ui.theme
    CSS = (
        """
    Screen { background: %(bg)s; color: %(text)s; }
    Header { background: %(surface)s; color: %(text)s; }
    HeaderTitle { content-align: left middle; }

    #statusbar { height: %(border_row)s; background: %(surface)s; color: %(muted)s; padding: %(padding_tight)s; }
    #statusbar .value { color: %(accent)s; text-style: bold; }

    #sidebar { width: %(sidebar_width)s; border-right: solid %(border)s; background: %(bg)s; }
    #sidebar.collapsed { width: 0; border-right: none; display: none; }
    /* No border-bottom here: Textual draws each widget's border independently with no shared
       corner glyph, so a border-right meeting a border-bottom renders as a broken │ beside a
       ─ instead of a ┬. The surface color groups these strips instead. */
    #file-search { height: %(sidebar_head_height)s; background: %(surface)s; color: %(text)s; border: none; padding: 0 1; }
    #file-search:focus { background-tint: transparent; }
    FilePicker { height: 1fr; scrollbar-size: 0 0; background: %(bg)s; color: %(text)s; }
    /* Selected file: bright accent background with darker amber-brown text — two shades of
       orange rather than orange-on-black. */
    FilePicker > .tree--cursor { background: %(accent)s; color: %(accent_dark)s; text-style: bold; }
    FilePicker > .tree--highlight { color: %(accent)s; }

    #middle { width: 1fr; border-right: solid %(border)s; background: %(bg)s; }
    #preview-scroll { scrollbar-size: 0 0; background: %(bg)s; }
    #preview-body { padding: %(padding_comfortable)s; background: %(bg)s; color: %(text)s; }

    #chat { width: %(chat_width)s; background: %(bg)s; }
    #log { height: 1fr; scrollbar-size: 0 0; background: %(bg)s; color: %(text)s; }
    /* Suggestion checklist: docked above the input bar, inline in the chat column rather than a
       modal overlay — a suggestion is a list to review, not an interruption to dismiss. Same
       background as #log and no border (OptionList's default draws one on all sides, reappearing
       on :focus even after border-top alone was overridden), so it reads as more chat output
       rather than a boxed dialog. background-tint reset for the same reason as #cmd:focus below:
       OptionList blends in a 5%%-foreground tint by default while focused, which this widget
       almost always is, showing up as a permanent lightened background on every row. */
    SuggestionChecklist, SuggestionChecklist:focus {
        height: auto; max-height: %(checklist_max_height)s; background: %(bg)s; color: %(text)s;
        border: none; padding: 0; scrollbar-size: 0 0; background-tint: transparent;
    }
    SuggestionChecklist > .option-list--option-highlighted { background: %(accent)s; color: %(accent_dark)s; }
    /* Row divider recolored to match the background so it reads as a blank gap between rows
       (see SuggestionChecklist._build_options) rather than the default visible ─── rule. */
    SuggestionChecklist > .option-list--separator { color: %(bg)s; background: %(bg)s; }
    /* Surface color rather than a border-top, for the same reason as #file-search above. */
    #inputbar { height: %(input_bar_height)s; padding: 0 0 %(breathing_row)s 0; background: %(surface)s; }
    #caret { width: %(caret_width)s; color: %(accent)s; text-style: bold; }
    #cmd { background: %(surface)s; color: %(text)s; border: none; padding: 0; }
    /* Input adds a background-tint on :focus by default; since this input is focused almost
       always, that shows as a permanent mismatched patch. */
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
            "checklist_max_height": theme.CHECKLIST_MAX_HEIGHT,
            "border_row": theme.BORDER_ROW,
            "breathing_row": theme.BREATHING_ROW,
            "sidebar_head_height": theme.SIDEBAR_HEAD_HEIGHT,
            "input_bar_height": theme.INPUT_BAR_HEIGHT,
            "padding_tight": theme.PADDING_TIGHT,
            "padding_comfortable": theme.PADDING_COMFORTABLE,
        }
    )

    # ctrl+e is taken by Input's built-in "go to end of line" and never reaches the App while
    # the input has focus (almost always), so f2 (unclaimed) toggles the sidebar and ctrl+f
    # (the usual find key) focuses search. tab needs priority=True: Screen's own plain "tab"
    # -> "app.focus_next" binding otherwise wins, and only a higher-priority binding overrides it.

    #TODO: fix improper commenting ^

    BINDINGS = [
        Binding("f2", "toggle_sidebar", "Toggle explorer"),
        Binding("ctrl+f", "focus_search", "Find file"),
        Binding("tab", "accept_suggestion_or_focus_next", "Accept suggestion", priority=True, show=False),
    ]

    def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
        for command in super().get_system_commands(screen):
            if command.title != "Theme":
                yield command

    #TODO: why is init all the way down here?
    def __init__(self, vault: Vault, retriever: Retriever, model: ModelClient, settings: Settings) -> None:
        super().__init__()
        self.vault = vault
        self.retriever = retriever
        self.model = model
        self.settings = settings
        self._active_file: File | None = None
        self._selected_folder: Path | None = None
        self._folder_tag_plan: list[tuple[Path, FolderTagChange]] = []
        self._drafting = False
        self._history: list[tuple[str, str]] = []
        self._web_enabled = False
        self._classification: ClassificationSuggestion | None = None
        self._checklist: SuggestionChecklist | None = None
        self._checklist_kind: str | None = None  # "tags" | "folder" | "wikilinks"
        self._checklist_wikilink_kind: dict[str, str] = {}  # title -> "inline" | "see_also"
        self._review_queue: list[ReviewQuestion] = []
        self._review_index = 0

    def compose(self) -> ComposeResult:
        yield Header(icon="")  # the default "⭘" icon has no function here — just noise
        #TODO: remove this comment and any that reffer to old stale lines of code. claude added a comment instead of just removing th lin:w
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Input(id="file-search", placeholder="search files…")
                yield FilePicker(self.vault)
            with Vertical(id="middle"):
                with VerticalScroll(id="preview-scroll"):
                    yield StreamingText(id="preview-body")
            with Vertical(id="chat"):
                # min_width defaults to 78, so RichLog lays out assuming ≥78 columns even in
                # this ~70-wide pane; the overflow then scrolls off horizontally (invisibly,
                # scrollbars are hidden) instead of wrapping. min_width=1 wraps to the real width.
                yield RichLog(id="log", wrap=True, min_width=1, markup=False)
                with Horizontal(id="inputbar"):
                    yield Label("›", id="caret")
                    yield Input(id="cmd", placeholder="_", suggester=SuggestFromList(_COMMANDS, case_sensitive=False))
        yield Static(id="statusbar")

    def on_mount(self) -> None:
        self.title = f"chatui — {self.vault.root.name}/"
        log = self.query_one("#log", RichLog)
        _write_hint(log, "/explorer or f2 toggles the file tree. ctrl+f or click search to find a file.")
        _write_hint(log, "Click a file (or jump to one), then /draft to start revising it — write an")
        _write_hint(log, "instruction, /done saves. /tags, /wikilinks, /folder, /review, /ingest,")
        _write_hint(log, "/model, /web, /palette also work.")
        self.query_one("#cmd", Input).focus()
        self.query_one(StreamingText).on_link_click = self._open_wikilink_target
        self._update_statusbar()
        # Retriever.ingest() already diffs against local_db/manifest.json and only re-embeds
        # new/changed files (and prunes removed ones) — running it on every launch keeps the
        # index in sync with on-disk edits automatically, without a full re-embed each time.
        self.run_worker(self._handle_ingest())
        self.set_interval(_FILE_TREE_POLL_SECONDS, self._poll_file_tree)

    def _poll_file_tree(self) -> None:
        # Best-effort: a file dropped on disk by another editor should show up (green, pending
        # ingest) without the user having to run /ingest or restart the app first.
        self.query_one(FilePicker).refresh_from_disk(self.retriever.ingested_paths())

    def _update_statusbar(self) -> None:
        n = len(self.vault.list_files())
        web = "on" if self._web_enabled else "off"
        self.query_one("#statusbar", Static).update(
            Text.assemble(
                ("model: ", theme.MUTED), (self.model.chat_model_name, f"{theme.ACCENT} bold"),
                (f"   web: {web}   vault: ", theme.MUTED), (f"{n} files", f"{theme.ACCENT} bold"),
            )
        )

    def action_toggle_sidebar(self) -> None:
        self.query_one("#sidebar").toggle_class("collapsed")

    def action_focus_search(self) -> None:
        self.query_one("#file-search", Input).focus()

    def action_accept_suggestion_or_focus_next(self) -> None:
        # Does what Right-arrow does here — accept the pending autocomplete suggestion — or
        # else cycles focus. cmd._suggestion is private, but Input exposes no public
        # "is a suggestion pending" accessor.
        cmd = self.query_one("#cmd", Input)
        if self.focused is cmd and cmd._suggestion:
            cmd.action_cursor_right()
        else:
            self.screen.focus_next()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        picker = self.query_one(FilePicker)
        path = picker.selected_path()
        if path is None:
            return
        if path.is_dir():
            self._selected_folder = path
            self._flash_status(f"{path.relative_to(self.vault.root)}: selected — /tags to tag every file inside")
            return
        if not path.is_file():
            self._flash_status(f"{path.stem}: still in the ingest index but no longer in the vault — /ingest to clean up")
            return
        self._selected_folder = None
        self._preview_file(path)

    def _preview_file(self, path: Path) -> None:
        self._set_active_file(self.vault.load_file(path))

    def _open_wikilink_target(self, target: str) -> None:
        """Navigate to the vault file a clicked committed [[wikilink]] points to, if it exists."""
        normalized = normalize_link_target(target)
        for file in self.vault.list_files():
            if normalize_link_target(file.title) == normalized:
                self._preview_file(file.path)
                return

    def _set_active_file(self, file: File) -> None:
        log = self.query_one("#log", RichLog)
        if self._drafting and self._active_file is not None:
            _write_status(log, f'"{self._active_file.title}": left with unsaved changes (switched away)')
        self._active_file = file
        self._selected_folder = None
        self._classification = None
        self._drafting = False
        self._review_queue = []
        if self._checklist is not None:
            self._checklist.remove()  # belonged to the file we're leaving — discard, don't apply
            self._checklist = None
            self._checklist_kind = None
            self._checklist_wikilink_kind = {}
        self.query_one("#cmd", Input).placeholder = "_"
        self._refresh_preview()
        self.query_one("#preview-scroll", VerticalScroll).scroll_to(y=0, animate=False)
        self.query_one("#cmd", Input).focus()
        self._update_statusbar()

    def _refresh_preview(self) -> None:
        if self._active_file is None:
            return
        text, spans = self._preview_content()
        self.query_one(StreamingText).show_links(text, spans, -1 if not spans else 0)

    def _preview_content(self) -> tuple[str, list[tuple[str, int, int]]]:
        """Text + pending-highlight spans for the preview pane, reflecting an open checklist's
        currently-checked items — nothing here is written to disk until /done."""
        file = self._active_file
        if self._checklist is None or self._checklist_kind is None:
            return file.body, []
        checked = self._checklist.checked_items()
        if not checked:
            return file.body, []

        if self._checklist_kind == "wikilinks":
            inline = [t for t in checked if self._checklist_wikilink_kind.get(t) == "inline"]
            see_also = [t for t in checked if self._checklist_wikilink_kind.get(t) == "see_also"]
            preview_body = classify.preview_with_wikilinks(file.body, inline, see_also)
            # Every [[wikilink]] not already saved in the file is part of this pending preview.
            spans = [
                (target, start, end)
                for start, end, target in find_wikilinks(preview_body)
                if target not in file.links
            ]
            return preview_body, spans

        if self._checklist_kind == "tags":
            meta = {"title": file.title, "tags": list(dict.fromkeys([*file.tags, *checked]))}
            if file.last_reviewed is not None:
                meta["last_reviewed"] = file.last_reviewed
            preview_text = render_frontmatter(meta, file.body)
            return preview_text, [("frontmatter", 0, len(preview_text) - len(file.body))]

        return file.body, []  # "folder"/"folder-tags": no body location to preview into

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

    async def on_key(self, event: events.Key) -> None:
        # Escape while searching clears the query and returns focus to the main input, rather
        # than leaving a stale filter and orphaned focus. This is the one place a second Input
        # can steal focus from the primary one.
        search = self.query_one("#file-search", Input)
        if event.key == "escape" and self.focused is search:
            search.value = ""
            self.query_one(FilePicker).filter_files("")
            self.query_one("#cmd", Input).focus()
            event.stop()
            return
        if event.key == "escape" and self._checklist is not None and self.focused is self._checklist:
            event.stop()
            await self._dismiss_checklist("cancelled")

    # --- Ask -----------------------------------------------------------------------------

    async def _ask(self, question: str) -> None:
        log = self.query_one("#log", RichLog)
        _write_status(log, "thinking…")
        try:
            result = await ask.ask(
                question, self.vault, self.retriever, self.model, self._history, self._web_enabled,
                top_k=self.settings.top_k, similarity_threshold=self.settings.similarity_threshold,
                history_window=self.settings.history_window, web_search_results=self.settings.web_search_results,
            )
        except ChatUIError as exc:
            _log.error("ask failed for %r: %s", question, exc)
            _write_status(log, f"couldn't answer: {exc}")
            return
        self._history.append((question, result.answer))
        _write_answer(log, result.answer)
        if result.sources:
            _write_status(log, "source: " + ", ".join(str(p) for p in result.sources))
        if result.web_supplement:
            _write_answer(log, result.web_supplement)

    # --- Draft -----------------------------------------------------------------------------

    async def _start_or_continue_draft(self, subject: str | None) -> None:
        log = self.query_one("#log", RichLog)
        if subject is not None:
            self._set_active_file(draft.edit_draft(subject, self.vault))
        elif self._active_file is None:
            _write_status(log, "nothing to draft: click a file, search for one, or /draft <subject> to start new")
            return
        self._drafting = True
        _write_status(log, f'drafting "{self._active_file.title}"... (write an instruction, /done to save and stop)')

    async def _revise_active_draft(self, instruction: str) -> None:
        log = self.query_one("#log", RichLog)
        old_body = self._active_file.body
        try:
            revised = await draft.revise_draft(self._active_file, instruction, self.model)
        except ChatUIError as exc:
            _log.error("draft revision failed for %r: %s", self._active_file.path, exc)
            _write_status(log, f"revision failed: {exc}")
            return
        self._active_file = revised
        self.query_one(StreamingText).update(_diff_highlight(old_body, revised.body))
        _write_status(log, "revised — another instruction, or /done to save and stop")

    async def _finish_draft(self) -> None:
        log = self.query_one("#log", RichLog)
        if not self._drafting or self._active_file is None:
            _write_status(log, "nothing being drafted")
            return
        draft.save_draft(self._active_file, self.vault)
        self._drafting = False
        try:
            self.retriever.reingest_one(self._active_file)
        except ChatUIError as exc:
            _log.error("reindex failed for %s: %s", self._active_file.path, exc)
            _write_status(log, f"saved, but re-indexing failed: {exc}")
        else:
            _write_status(log, f'"{self._active_file.title}": saved')
        self.query_one(FilePicker).reload(self.retriever.ingested_paths())
        self._refresh_preview()

    # --- Classify: tags / folder / wikilinks (all share one checklist) -----------------------

    async def _ensure_classification(self) -> ClassificationSuggestion | None:
        if self._active_file is None:
            return None
        if self._classification is None or self._classification.file_path != self._active_file.path:
            log = self.query_one("#log", RichLog)
            try:
                self._classification = await classify.suggest_classification(
                    self._active_file, self.vault, self.model,
                    on_status=lambda text: _write_status(log, text),
                )
            except ChatUIError as exc:
                _log.error("classification failed for %s: %s", self._active_file.path, exc)
                _write_status(log, f"couldn't get suggestions: {exc}")
                return None
            _log.info("classification for %s: %s", self._active_file.path, self._classification)
        return self._classification

    async def _show_suggestion_checklist(self, kind: str) -> None:
        log = self.query_one("#log", RichLog)
        if self._active_file is None:
            _write_status(log, f"nothing to suggest {kind} for: click a file or search for one first")
            return
        suggestion = await self._ensure_classification()
        if suggestion is None:
            return
        if kind == "tags":
            items = suggestion.suggested_tags
        else:
            items = [suggestion.suggested_folder] if suggestion.suggested_folder else []
        if not items:
            _write_status(log, f"no {kind} suggested")
            return
        await self._open_checklist(kind, items)

    async def _start_wikilink_walkthrough(self) -> None:
        """Suggest wikilinks: inline (text match) and see-also (vector-similar, no text match)
        candidates share one checklist — checking either kind previews it live (wrapped in place,
        or appended as a "## See also" bullet) until /done writes it for real."""
        if self._active_file is None:
            self._flash_status("nothing to link: click a file or search for one first")
            return
        self._flash_status(f"searching for wikilinks in {self._active_file.path.name}…")
        try:
            suggestion = await classify.suggest_wikilinks(
                self._active_file, self.vault, self.retriever,
                top_k=self.settings.top_k, similarity_threshold=self.settings.similarity_threshold,
            )
        except ChatUIError as exc:
            _log.error("wikilink suggestion failed for %s: %s", self._active_file.path, exc)
            self._flash_status(f"couldn't get suggestions: {exc}")
            return

        if not suggestion.inline_new and not suggestion.see_also_new:
            self._flash_status(
                f"already linked: {', '.join(suggestion.already_linked)}"
                if suggestion.already_linked else "no wikilinks suggested"
            )
            return

        self._checklist_wikilink_kind = {t: "inline" for t in suggestion.inline_new}
        self._checklist_wikilink_kind.update({t: "see_also" for t in suggestion.see_also_new})
        await self._open_checklist("wikilinks", suggestion.inline_new + suggestion.see_also_new)

    async def _show_folder_tag_checklist(self) -> None:
        """Batch counterpart to /tags on a single file: syncs every file under the selected folder
        to the current folder structure — adds missing folder-derived tags (Vault.folder_tags) and
        strips stale ones left over from a folder that was since moved/renamed — all pre-checked
        for review."""
        log = self.query_one("#log", RichLog)
        folder = self._selected_folder
        plan = classify.suggest_folder_tags(folder, self.vault)
        if not plan:
            _write_status(log, f"{folder.relative_to(self.vault.root)}: every file's tags already match the folder structure")
            return
        self._folder_tag_plan = list(plan.items())
        items = [
            f"{path.stem} +{', '.join(change.add)} -{', '.join(change.remove)}"
            for path, change in self._folder_tag_plan
        ]
        columns = [
            (_truncate(path.stem, theme.CHECKLIST_NAME_WIDTH), self._folder_tag_change_text(change))
            for path, change in self._folder_tag_plan
        ]
        await self._open_checklist(
            "folder-tags", items, initial_checked=set(range(len(items))), columns=columns
        )

    @staticmethod
    def _folder_tag_change_text(change: FolderTagChange) -> Text:
        text = Text()
        if change.add:
            text.append("+" + ", +".join(change.add), style=theme.TAG)
        if change.remove:
            if change.add:
                text.append("  ")
            text.append("-" + ", -".join(change.remove), style=theme.TAG_REMOVE)
        return text

    async def _open_checklist(
        self,
        kind: str,
        items: list[str],
        initial_checked: set[int] | None = None,
        columns: list[tuple[str, Text]] | None = None,
    ) -> None:
        if self._checklist is not None:
            await self._checklist.remove()
        self._checklist_kind = kind
        checklist = SuggestionChecklist(items, initial_checked=initial_checked, columns=columns, id="checklist")
        self._checklist = checklist
        await self.query_one("#chat", Vertical).mount(checklist, before="#inputbar")
        checklist.focus()
        self._refresh_preview()
        _write_status(
            self.query_one("#log", RichLog),
            f"{kind}: space/enter/click to toggle, /done to apply, escape to cancel",
        )

    def on_suggestion_checklist_toggled(self, _event: SuggestionChecklist.Toggled) -> None:
        self._refresh_preview()

    async def _close_checklist(self) -> None:
        if self._checklist is not None:
            await self._checklist.remove()
        self._checklist = None
        self._checklist_kind = None
        self._checklist_wikilink_kind = {}
        self._folder_tag_plan = []
        self._refresh_preview()
        self.query_one("#cmd", Input).focus()

    async def _dismiss_checklist(self, reason: str) -> None:
        kind = self._checklist_kind
        await self._close_checklist()
        _write_status(self.query_one("#log", RichLog), f"{kind}: {reason}")

    async def _apply_checklist(self) -> None:
        kind = self._checklist_kind
        checked = self._checklist.checked_items()
        checked_indices = self._checklist.checked_indices()
        # Snapshot lookups keyed by this checklist before closing it — _close_checklist wipes
        # both, and reading them afterward would silently see nothing checked as "applied".
        wikilink_kind = dict(self._checklist_wikilink_kind)
        folder_tag_plan = list(self._folder_tag_plan)
        log = self.query_one("#log", RichLog)
        await self._close_checklist()

        if not checked:
            _write_status(log, f"{kind}: nothing checked, no changes made")
            return

        if kind == "wikilinks":
            inline = [t for t in checked if wikilink_kind.get(t) == "inline"]
            see_also = [t for t in checked if wikilink_kind.get(t) == "see_also"]
            for title in inline:
                self._active_file = classify.apply_wikilink(self._active_file, title, self.vault)
            if see_also:
                self._active_file = classify.apply_see_also(self._active_file, see_also, self.vault)
        elif kind == "folder-tags":
            plan = dict(folder_tag_plan[i] for i in checked_indices)
            updated = classify.apply_folder_tags(plan, self.vault)
            self._selected_folder = None
            for file in updated:
                try:
                    self.retriever.reingest_one(file)
                except ChatUIError as exc:
                    _log.warning("best-effort reindex failed for %s: %s", file.path, exc)
            self.query_one(FilePicker).reload(self.retriever.ingested_paths())
            if self._active_file is not None and self._active_file.path in plan:
                self._active_file = self.vault.load_file(self._active_file.path)
            self._refresh_preview()
            _write_status(log, f"folder-tags: applied to {len(updated)} file(s)")
            return
        else:
            partial = ClassificationSuggestion(
                file_path=self._active_file.path,
                suggested_folder=checked[0] if kind == "folder" else None,
                suggested_tags=checked if kind == "tags" else [],
            )
            self._active_file = classify.apply_classification(self._active_file, partial, self.vault)

        try:
            self.retriever.reingest_one(self._active_file)
        except ChatUIError as exc:
            _log.warning("best-effort reindex failed for %s: %s", self._active_file.path, exc)
        self.query_one(FilePicker).reload(self.retriever.ingested_paths())
        self._refresh_preview()
        _write_status(log, f"{kind}: applied")

    def _flash_status(self, text: str) -> None:
        self.query_one("#statusbar", Static).update(Text(text, style=theme.ACCENT))

    # --- Review ------------------------------------------------------------------------------

    async def _start_review(self) -> None:
        log = self.query_one("#log", RichLog)
        if self._active_file is None:
            due = review.files_due_for_review(
                self.vault, timedelta(days=self.settings.review_staleness_days)
            )
            if not due:
                _write_status(log, "nothing due for review")
                return
            titles = ", ".join(f.title for f in due[:5])
            _write_status(log, f"due for review: {titles} — click one, or search for one, first")
            return
        _write_status(log, "thinking…")
        try:
            questions = await review.generate_review_questions(self._active_file, self.model)
        except ChatUIError as exc:
            _write_status(log, f"couldn't generate questions: {exc}")
            return
        if not questions:
            _write_status(log, "no questions generated")
            return
        self._review_queue = questions
        self._review_index = 0
        self._ask_review_question()

    def _ask_review_question(self) -> None:
        log = self.query_one("#log", RichLog)
        cmd = self.query_one("#cmd", Input)
        position = f"{self._review_index + 1}/{len(self._review_queue)}"
        _write_status(log, f"review {position}: {self._review_queue[self._review_index].question}")
        cmd.placeholder = "your answer, or /hint, or /done"

    def _resolve_review(self, answer: str) -> None:
        log = self.query_one("#log", RichLog)
        cmd = self.query_one("#cmd", Input)
        if answer == "/hint":
            _write_status(log, f"hint: {self._review_queue[self._review_index].answer_hint}")
            return
        if answer == "/done":
            _write_status(log, "review: stopped early")
            self._review_queue = []
            cmd.placeholder = "_"
            return
        self._review_index += 1
        if self._review_index >= len(self._review_queue):
            self._active_file = review.mark_reviewed(self._active_file, self.vault)
            _write_status(log, "review: done — marked reviewed")
            self._review_queue = []
            cmd.placeholder = "_"
            return
        self._ask_review_question()

    # --- Support commands ----------------------------------------------------------------

    async def _handle_ingest(self) -> None:
        log = self.query_one("#log", RichLog)
        _write_status(log, "ingesting…")
        try:
            # Retriever.ingest() is synchronous (chromadb/langchain, no async), so run it in a
            # thread to keep embedding from stalling the UI.
            stats = await asyncio.to_thread(self.retriever.ingest, self.vault.list_files())
        except ChatUIError as exc:
            _log.error("ingest failed: %s", exc)
            _write_status(log, f"ingest failed: {exc}")
            return
        _write_status(log, f"ingest: {stats.new} new, {stats.updated} updated, {stats.removed} removed, {stats.unchanged} unchanged")
        self.query_one(FilePicker).reload(self.retriever.ingested_paths())
        self._update_statusbar()

    def _handle_model_command(self, text: str) -> None:
        log = self.query_one("#log", RichLog)
        name = text[len("/model"):].strip()
        if not name:
            _write_status(log, f"model: {self.model.chat_model_name}")
            return
        self.model.switch_chat_model(name)
        _write_status(log, f"model: switched to {name}")
        self._update_statusbar()

    # --- Dispatch ----------------------------------------------------------------------------

    @on(Input.Submitted, "#cmd")
    async def on_cmd_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        event.input.value = ""
        log = self.query_one("#log", RichLog)

        if self._checklist is not None:
            if text == "/done":
                await self._apply_checklist()
            elif text in ("/cancel", "/dismiss"):
                await self._dismiss_checklist("cancelled")
            elif text:
                _write_you(log, text)
                _write_status(log, f"{self._checklist_kind}: /done to apply, /cancel to discard")
            return

        if self._review_queue:
            _write_you(log, text or "(next)")
            self._resolve_review(text)
            return

        if not text:
            return
        _write_you(log, text)
        _log.debug("dispatch: %r (active_file=%s)", text, self._active_file.path if self._active_file else None)

        if text == "/done":
            await self._finish_draft()
            return
        if text == "/explorer":
            self.action_toggle_sidebar()
            return
        if text == "/palette":
            self.action_command_palette()
            return
        if text == "/web":
            self._web_enabled = not self._web_enabled
            _write_status(log, f"web search: {'on' if self._web_enabled else 'off'}")
            self._update_statusbar()
            return
        if text == "/model" or text.startswith("/model "):
            self._handle_model_command(text)
            return
        if text == "/ingest":
            await self._handle_ingest()
            return
        if text == "/draft":
            await self._start_or_continue_draft(None)
            return
        if text.startswith("/draft "):
            await self._start_or_continue_draft(text[len("/draft "):])
            return
        if text == "/review":
            await self._start_review()
            return

        kind = _match_suggestion_kind(text)
        if kind == "wikilinks":
            self.run_worker(self._start_wikilink_walkthrough())
            return
        if kind == "tags" and self._selected_folder is not None:
            self.run_worker(self._show_folder_tag_checklist())
            return
        if kind in ("tags", "folder"):
            self.run_worker(self._show_suggestion_checklist(kind))
            return

        if self._drafting:
            await self._revise_active_draft(text)
            return

        await self._ask(text)
