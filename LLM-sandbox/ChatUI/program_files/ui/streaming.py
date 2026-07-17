"""Live token/line display widget — ported from the old app's _stream_llm/_stream_lines pattern."""

from __future__ import annotations

from typing import Callable

from rich.text import Text
from textual import events
from textual.widgets import Static

from program_files.ui import theme
from program_files.vault import find_wikilinks


class StreamingText(Static):
    """Displays streamed or static text; renders [[wikilinks]] as clickable, plus optional pending-candidate spans."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._text = ""
        self._committed_spans: list[tuple[int, int, str]] = []
        self.on_link_click: Callable[[str], None] | None = None

    def show(self, text: str) -> None:
        """Display text immediately, with no streaming — for previewing an already-written file."""
        self.show_links(text)

    def show_links(
        self, text: str, pending: list[tuple[str, int, int]] | None = None, focus_index: int = -1
    ) -> None:
        """Render text with existing [[wikilinks]] styled and clickable, plus pending candidate spans highlighted."""
        self._text = text
        self._committed_spans = find_wikilinks(text)
        result = Text(text)  # Text(), not a raw str, so vault content isn't parsed as Rich markup
        for start, end, _target in self._committed_spans:
            result.stylize(f"underline {theme.ACCENT}", start, end)
        for index, (_title, start, end) in enumerate(pending or []):
            style = (
                f"bold {theme.ACCENT_DARK} on {theme.ACCENT}"
                if index == focus_index
                else f"bold {theme.ACCENT_DARK} on {theme.ACCENT_MUTED}"
            )
            result.stylize(style, start, end)
        self.update(result)

    async def stream(self, model_stream_call: Callable, prompt: str) -> str:
        """Stream model_stream_call's output into the widget token by token, returning the full text."""
        self._text = ""
        self._committed_spans = []
        self.update(Text(""))

        def on_token(token: str) -> None:
            self._text += token
            self.update(Text(self._text))

        return await model_stream_call(prompt, on_token=on_token)

    def on_click(self, event: events.Click) -> None:
        if self.on_link_click is None or not self._committed_spans:
            return
        offset = self._offset_at(event.x, event.y)
        if offset is None:
            return
        for start, end, target in self._committed_spans:
            if start <= offset < end:
                self.on_link_click(target)
                return

    def _offset_at(self, x: int, y: int) -> int | None:
        """Map a click's widget-local (x, y) to a character offset in self._text (wrap-aware, best-effort)."""
        padding = self.styles.padding
        row, col = y - padding.top, x - padding.left
        if row < 0 or col < 0:
            return None
        width = max(1, self.size.width - padding.left - padding.right)
        lines = Text(self._text).wrap(self.app.console, width)
        if row >= len(lines):
            return None
        offset = sum(len(line.plain) for line in lines[:row])
        return offset + min(col, len(lines[row].plain))
