"""Checkbox-style suggestion list — arrow keys or mouse to navigate, space/enter/click to toggle."""

from __future__ import annotations

from rich.table import Table
from rich.text import Text
from textual.binding import Binding
from textual.message import Message
from textual.widgets import OptionList
from textual.widgets.option_list import Option


class SuggestionChecklist(OptionList):
    """A list of suggestion strings with a checkbox prefix; nothing is applied until the caller
    reads checked_items() — this widget only tracks which boxes are ticked."""

    BINDINGS = [Binding("space", "toggle_highlighted", "Toggle", show=False)]

    class Toggled(Message):
        """Posted whenever a checkbox is toggled, so a caller can refresh a live preview."""

    def __init__(
        self,
        items: list[str],
        initial_checked: set[int] | None = None,
        columns: list[tuple[str, Text]] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._items = items
        # A (name, styled-tags) pair per row for callers that need a two-column layout (e.g. the
        # folder-tags batch list) instead of a single line — rendered as a borderless Table.grid
        # so wrapped tag text stays indented under its own column rather than sliding to the left
        # edge, which plain Text concatenation can't do. checked_items()/checked_indices() still
        # resolve against the plain _items, so callers matching on those are unaffected.
        self._columns = columns
        self._column_width = max((len(name) for name, _tags in columns), default=0) if columns else 0
        self._checked: set[int] = set(initial_checked) if initial_checked else set()

    def on_mount(self) -> None:
        self._render_options()

    def _render_options(self) -> None:
        # OptionList starts with nothing highlighted until the user first navigates; defaulting
        # to 0 means arrow keys, space, and click all work immediately without a throwaway
        # first keypress just to establish a highlight.
        highlighted = self.highlighted if self.highlighted is not None else 0
        self.clear_options()
        self.add_options(self._build_options())
        if self._items:
            self.highlighted = highlighted

    def _build_options(self):
        # A divider after every option but the last renders as a blank row (see the
        # option-list--separator CSS, colored to match the background) rather than a visible
        # rule — it's the built-in mechanism for a gap here since it doesn't shift option
        # indices or get swept into the next option's highlight block the way padding baked
        # into each option's own renderable would.
        last = len(self._items) - 1
        for i, item in enumerate(self._items):
            yield Option(self._label(i, item), id=str(i))
            if i != last:
                yield None

    def _label(self, index: int, item: str) -> Text | Table:
        checkbox = "☑" if index in self._checked else "☐"
        if self._columns is None:
            return Text(f"{checkbox} {item}")
        name, tags = self._columns[index]
        table = Table.grid(padding=(0, 1, 0, 0))
        table.add_column(width=2, no_wrap=True)
        table.add_column(width=self._column_width, no_wrap=True)
        table.add_column()
        table.add_row(Text(checkbox), Text(name), tags)
        return table

    def action_toggle_highlighted(self) -> None:
        self._toggle(self.highlighted)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        # Enter and a mouse click both surface as OptionSelected — both should toggle, not dismiss.
        event.stop()
        self._toggle(event.option_index)

    def _toggle(self, index: int | None) -> None:
        if index is None:
            return
        self._checked.symmetric_difference_update({index})
        self._render_options()
        self.post_message(self.Toggled())

    def checked_items(self) -> list[str]:
        return [item for i, item in enumerate(self._items) if i in self._checked]

    def checked_indices(self) -> list[int]:
        """Positions of checked items in the original items list — for callers keying off
        position rather than label text, since labels aren't guaranteed unique (e.g. two files
        named "Overview.md" in different folders)."""
        return sorted(self._checked)
