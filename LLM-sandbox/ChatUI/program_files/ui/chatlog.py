"""Chat history pane: one widget per message, so a streamed answer can be updated in place
instead of living in a scratch widget that gets swapped for a final one once it completes."""

from __future__ import annotations

from rich.text import Text
from textual.containers import VerticalScroll
from textual.widgets import Static

from program_files.ui import theme

_BOTTOM_TOLERANCE = 1  # rows of slack in the "at bottom" check, for scroll-math rounding


class StreamingMessage:
    """A chat message updated in place as tokens arrive.

    Mounting is deferred to the first update rather than done at construction: status lines
    (retrieval phase, tool calls) can still arrive after begin_streaming() is called but before
    any token does, and they need to land above the answer in the log's child order, not below it.
    """

    def __init__(self, log: "ChatLog") -> None:
        self._log = log
        self._widget: Static | None = None

    def update(self, text: str) -> None:
        renderable = Text(text, style=theme.BRIGHT)
        if self._widget is None:
            self._widget = Static(renderable)
            self._log._mount(self._widget)
        else:
            self._log._mutate(self._widget, renderable)

    def remove(self) -> None:
        if self._widget is not None:
            self._widget.remove()


class ChatLog(VerticalScroll):
    """Scrollable chat history; auto-scrolls to new content only when already at the bottom,
    so scrolling up to read history isn't interrupted by an in-progress answer."""

    def write_hint(self, text: str) -> None:
        self._mount_message(Text(text, style=theme.MUTED))

    def write_you(self, text: str) -> None:
        self._mount_message(Text.assemble(("› ", f"bold {theme.ACCENT}"), (text, theme.MUTED)))

    def write_answer(self, text: str) -> None:
        self._mount_message(Text(text, style=theme.BRIGHT))

    def write_status(self, text: str) -> None:
        label, sep, detail = text.partition(":")
        if not sep:
            self._mount_message(Text(text, style=theme.ACCENT))
            return
        self._mount_message(Text.assemble((label + sep, theme.ACCENT), (detail, theme.ACCENT_MUTED)))

    def begin_streaming(self) -> StreamingMessage:
        """Start a message whose first update() mounts it in place; later updates rewrite it in place."""
        return StreamingMessage(self)

    def _mount_message(self, renderable: Text) -> None:
        self._mount(Static(renderable))

    def _mount(self, widget: Static) -> None:
        was_at_bottom = self._is_at_bottom()
        self.mount(widget)
        if was_at_bottom:
            self.call_after_refresh(lambda: self.scroll_end(animate=False))

    def _mutate(self, widget: Static, renderable: Text) -> None:
        was_at_bottom = self._is_at_bottom()
        widget.update(renderable)
        if was_at_bottom:
            self.call_after_refresh(lambda: self.scroll_end(animate=False))

    def _is_at_bottom(self) -> bool:
        return self.scroll_y >= self.max_scroll_y - _BOTTOM_TOLERANCE
