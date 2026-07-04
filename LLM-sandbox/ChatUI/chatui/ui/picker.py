"""Tree-based paper picker — technique salvaged from the shelved front-end-refactor plan."""

from __future__ import annotations

from pathlib import Path

from textual.widgets import Tree

from chatui.vault import Vault


class PaperPicker(Tree):
    def __init__(self, vault: Vault) -> None:
        super().__init__(label="Vault")
        self.vault = vault

    def render_label(self, node, base_style, style):
        raise NotImplementedError

    def selected_path(self) -> Path | None:
        raise NotImplementedError
