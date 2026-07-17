"""ChatApp — thin Textual shell; dispatches to the four verb modules, owns no business logic."""

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
from textual.screen import ModalScreen, Screen
from textual.suggester import SuggestFromList
from textual.widgets import Header, Input, Label, RichLog, Static, Tree

from chatui import ask, classify, draft, review
from chatui.config import Settings
from chatui.errors import ChatUIError
from chatui.llm import ModelClient
from chatui.models import ClassificationSuggestion, File, ReviewQuestion
from chatui.retrieval import Retriever
from chatui.ui import theme
from chatui.ui.picker import FilePicker
from chatui.ui.streaming import StreamingText
from chatui.vault import Vault, normalize_link_target

_log = logging.getLogger(__name__)

_COMMANDS = [
    "/draft", "/done", "/tags", "/wikilinks", "/folder", "/review",
    "/ingest", "/web", "/model", "/explorer", "/palette",
]


def _diff_highlight(old: str, new: str) -> Text:
    """Return new with inserted or changed spans styled in the addition color."""
    # revise_draft returns a full rewrite each call, so a real difflib diff is what tells
    # changed text from unchanged — there is no delta-only API to lean on.
    matcher = difflib.SequenceMatcher(None, old, new, autojunk=False)
    result = Text()
    for opcode, _i1, _i2, j1, j2 in matcher.get_opcodes():
        segment = new[j1:j2]
        if not segment:
            continue
        result.append(segment, style=theme.ADDITION if opcode in ("insert", "replace") else theme.TEXT)
    return result


def _match_suggestion_kind(text: str) -> str | None:
    """Return the classify kind named by a "/tags"/"/wikilinks"/"/folder" command or a plain-language mention, else None."""
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
    """Write text with the label (up to the first ":") in bright accent and the rest faded."""
    label, sep, detail = text.partition(":")
    if not sep:
        log.write(Text(text, style=theme.ACCENT))
        return
    log.write(Text.assemble((label + sep, theme.ACCENT), (detail, theme.ACCENT_MUTED)))


class SuggestionPopup(ModalScreen[bool]):
    """Modal dialog listing suggested tags or a folder, for accept-all or cancel."""

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

    def on_key(self, event: events.Key) -> None:
        if event.key == "enter":
            self.dismiss(True)
        elif event.key == "escape":
            self.dismiss(False)


class ChatApp(App):
    """Textual application shell; owns the Vault/Retriever/ModelClient/Settings and delegates to the verb modules."""

    # Every color and size below is a named value from chatui.ui.theme, never a fresh literal,
    # so the palette stays consistent across widgets.
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
    BINDINGS = [
        Binding("f2", "toggle_sidebar", "Toggle explorer"),
        Binding("ctrl+f", "focus_search", "Find file"),
        Binding("tab", "accept_suggestion_or_focus_next", "Accept suggestion", priority=True, show=False),
        Binding("ctrl+x", "dismiss_focused_wikilink", "Dismiss wikilink", show=False),
    ]

    def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
        # Drop "Theme": every color here is a hardcoded hex value, not a theme variable, so
        # switching themes does nothing visible.
        for command in super().get_system_commands(screen):
            if command.title != "Theme":
                yield command

    def __init__(self, vault: Vault, retriever: Retriever, model: ModelClient, settings: Settings) -> None:
        super().__init__()
        self.vault = vault
        self.retriever = retriever
        self.model = model
        self.settings = settings
        self._active_file: File | None = None
        self._drafting = False
        self._history: list[tuple[str, str]] = []
        self._web_enabled = False
        self._classification: ClassificationSuggestion | None = None
        self._pending_titles: list[str] = []  # wikilink candidates not yet applied or dismissed
        self._pending_focus = -1
        self._review_queue: list[ReviewQuestion] = []
        self._review_index = 0

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
        # Tab cycles pending wikilink candidates first, since that's the more common intent
        # while a /wikilinks pass is live; otherwise it does what Right-arrow does here — accept
        # the pending suggestion. cmd._suggestion is private, but Input exposes no public
        # "is a suggestion pending" accessor.
        if self._pending_titles:
            self._cycle_pending_wikilink()
            return
        cmd = self.query_one("#cmd", Input)
        if self.focused is cmd and cmd._suggestion:
            cmd.action_cursor_right()
        else:
            self.screen.focus_next()

    def action_dismiss_focused_wikilink(self) -> None:
        self._dismiss_focused_wikilink()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        picker = self.query_one(FilePicker)
        path = picker.selected_path()
        if path is not None:
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
        self._classification = None
        self._drafting = False
        self._pending_titles = []
        self._pending_focus = -1
        self._review_queue = []
        self.query_one("#cmd", Input).placeholder = "_"
        self._refresh_preview()
        self.query_one("#preview-scroll", VerticalScroll).scroll_to(y=0, animate=False)
        self.query_one("#cmd", Input).focus()
        self._update_statusbar()

    def _refresh_preview(self) -> None:
        if self._active_file is None:
            return
        body = self._active_file.body
        spans = []
        for title in self._pending_titles:
            start = body.lower().find(title.lower())
            if start != -1:
                spans.append((title, start, start + len(title)))
        self.query_one(StreamingText).show_links(body, spans, self._pending_focus)

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

    def _scroll_preview_to(self, text: str, offset: int) -> None:
        """Scroll #preview-scroll so the character at offset (wrap-aware) is centered in view."""
        preview = self.query_one(StreamingText)
        scroll = self.query_one("#preview-scroll", VerticalScroll)
        width = max(1, preview.size.width - 4)  # #preview-body's padding eats 4 cols
        row = len(Text(text[:offset]).wrap(self.console, width)) - 1
        scroll.scroll_to(y=max(0, row - scroll.size.height // 2), animate=True)

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
            self._set_active_file(draft.start_draft(subject, self.vault))
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
        self.query_one(FilePicker).reload()
        try:
            self.retriever.reingest_one(self._active_file)
        except ChatUIError as exc:
            _log.error("reindex failed for %s: %s", self._active_file.path, exc)
            _write_status(log, f"saved, but re-indexing failed: {exc}")
        else:
            _write_status(log, f'"{self._active_file.title}": saved')
        self._refresh_preview()

    # --- Classify: tags / folder (popup) ----------------------------------------------------

    async def _ensure_classification(self) -> ClassificationSuggestion | None:
        if self._active_file is None:
            return None
        if self._classification is None or self._classification.file_path != self._active_file.path:
            log = self.query_one("#log", RichLog)
            try:
                self._classification = await classify.suggest_classification(
                    self._active_file, self.model,
                    on_status=lambda text: _write_status(log, text),
                )
            except ChatUIError as exc:
                _log.error("classification failed for %s: %s", self._active_file.path, exc)
                _write_status(log, f"couldn't get suggestions: {exc}")
                return None
            _log.info("classification for %s: %s", self._active_file.path, self._classification)
        return self._classification

    # push_screen_wait raises NoActiveWorker unless it runs inside a worker, so this method
    # must always be reached via self.run_worker(...), never awaited directly.
    async def _show_suggestion_popup(self, kind: str) -> None:
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
        accepted = await self.push_screen_wait(SuggestionPopup(f"Suggested {kind}", items))
        if not accepted:
            _write_status(log, f"{kind}: cancelled")
            return
        partial = ClassificationSuggestion(
            file_path=self._active_file.path,
            suggested_folder=suggestion.suggested_folder if kind == "folder" else None,
            suggested_tags=suggestion.suggested_tags if kind == "tags" else [],
        )
        updated = classify.apply_classification(self._active_file, partial, self.vault)
        self._active_file = updated
        self.query_one(FilePicker).reload()
        try:
            self.retriever.reingest_one(updated)
        except ChatUIError as exc:
            _log.warning("best-effort reindex failed for %s: %s", updated.path, exc)
        self._refresh_preview()
        _write_status(log, f"{kind}: applied")

    # --- Classify: wikilinks (highlighted in the preview, not the chat log) ------------------

    async def _start_wikilink_walkthrough(self) -> None:
        """Suggest new wikilinks and highlight them (plus any existing ones) directly in the preview."""
        # No chat-log messages and no popup: candidates are highlighted in place in the preview,
        # cycled with tab, applied with enter, dismissed with ctrl+x — status lives in the
        # statusbar only. A dedicated suggest call, not _ensure_classification: wikilinks don't
        # need tags/folder computed alongside them.
        if self._active_file is None:
            self._flash_status("nothing to link: click a file or search for one first")
            return
        self._flash_status(f"searching for wikilinks in {self._active_file.path.name}…")
        try:
            links, already_linked = await classify.suggest_wikilinks(self._active_file, self.vault, self.model)
        except ChatUIError as exc:
            _log.error("wikilink suggestion failed for %s: %s", self._active_file.path, exc)
            self._flash_status(f"couldn't get suggestions: {exc}")
            return
        # Already-linked candidates need no action: they're real [[wikilinks]] already, so the
        # preview's normal committed-link styling covers them — only new ones go into the queue.
        self._pending_titles = links
        self._pending_focus = 0 if links else -1
        self._refresh_preview()
        if not links and not already_linked:
            self._flash_status("no wikilinks suggested")
        else:
            self._update_wikilink_status()

    def _cycle_pending_wikilink(self) -> None:
        if not self._pending_titles:
            return
        self._pending_focus = (self._pending_focus + 1) % len(self._pending_titles)
        self._refresh_preview()
        body = self._active_file.body
        start = body.lower().find(self._pending_titles[self._pending_focus].lower())
        if start != -1:
            self._scroll_preview_to(body, start)
        self._update_wikilink_status()

    def _apply_focused_wikilink(self) -> None:
        if not self._pending_titles or self._pending_focus < 0:
            return
        title = self._pending_titles[self._pending_focus]
        updated = classify.apply_wikilink(self._active_file, title, self.vault)
        self._active_file = updated
        try:
            self.retriever.reingest_one(updated)
        except ChatUIError:
            pass
        del self._pending_titles[self._pending_focus]
        self._pending_focus = self._pending_focus % len(self._pending_titles) if self._pending_titles else -1
        self._refresh_preview()
        self._update_wikilink_status()

    def _dismiss_focused_wikilink(self) -> None:
        if not self._pending_titles or self._pending_focus < 0:
            return
        del self._pending_titles[self._pending_focus]
        self._pending_focus = self._pending_focus % len(self._pending_titles) if self._pending_titles else -1
        self._refresh_preview()
        self._update_wikilink_status()

    def _flash_status(self, text: str) -> None:
        self.query_one("#statusbar", Static).update(Text(text, style=theme.ACCENT))

    def _update_wikilink_status(self) -> None:
        if not self._pending_titles:
            self._update_statusbar()
            return
        focused = self._pending_titles[self._pending_focus]
        bar = self.query_one("#statusbar", Static)
        bar.update(
            Text.assemble(
                (f"{len(self._pending_titles)} pending wikilink(s)", theme.ACCENT),
                (f' — "{focused}" focused — tab: next  enter: apply  ctrl+x: dismiss', theme.ACCENT_MUTED),
            )
        )

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

        if self._pending_titles and not text:
            self._apply_focused_wikilink()
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
            await self._start_wikilink_walkthrough()
            return
        if kind in ("tags", "folder"):
            self.run_worker(self._show_suggestion_popup(kind))
            return

        if self._drafting:
            await self._revise_active_draft(text)
            return

        await self._ask(text)
