"""Checkbox-style suggestion list — arrow keys or mouse to navigate, space/enter/click to toggle."""

from __future__ import annotations

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

    def __init__(self, items: list[str], **kwargs) -> None:
        super().__init__(**kwargs)
        self._items = items
        self._checked: set[int] = set()

    def on_mount(self) -> None:
        self._render_options()

    def _render_options(self) -> None:
        # OptionList starts with nothing highlighted until the user first navigates; defaulting
        # to 0 means arrow keys, space, and click all work immediately without a throwaway
        # first keypress just to establish a highlight.
        highlighted = self.highlighted if self.highlighted is not None else 0
        self.clear_options()
        self.add_options(
            Option(f"{'☑' if i in self._checked else '☐'} {item}", id=str(i))
            for i, item in enumerate(self._items)
        )
        if self._items:
            self.highlighted = highlighted

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
