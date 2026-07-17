"""Tree-based file picker — technique salvaged from the shelved front-end-refactor plan."""

from __future__ import annotations

from pathlib import Path

from rich.style import Style
from rich.text import Text
from textual.fuzzy import Matcher
from textual.widgets import Tree
from textual.widgets.tree import TreeNode

from chatui.models import File
from chatui.ui import theme
from chatui.vault import Vault


class FilePicker(Tree[Path]):
    """A Textual Tree of the vault's folder structure, for picking a file to draft/classify/review."""

    def __init__(self, vault: Vault) -> None:
        super().__init__(label="Vault")
        self.vault = vault
        self.show_root = False
        self._all_files = sorted(vault.list_files(), key=lambda f: f.path.relative_to(vault.root).parts)
        self._populate(self._all_files)

    def render_label(self, node: TreeNode[Path], base_style: Style, style: Style) -> Text:
        """Render a folder node muted or a file node bright, ellipsis-truncated to fit the pane."""
        plain = node.label.plain
        if node.allow_expand:
            icon = "▼ " if node.is_expanded else "▶ "
            color = theme.MUTED
        else:
            icon = "  "
            color = theme.BRIGHT

        depth = 0
        ancestor = node
        while ancestor.parent is not None:
            depth += 1
            ancestor = ancestor.parent
        # Tree renders exactly one row per node with no wrap support (no text-wrap/text-overflow
        # CSS affects it — a hard limit of its line cache), so truncate to the pane width here.
        available = max(1, self.size.width - depth * self.guide_depth - len(icon))
        if len(plain) > available:
            plain = plain[: max(0, available - 1)] + "…"

        label = Text(plain, style=color)
        label.stylize(style)
        return Text(icon, style=color) + label

    def _populate(self, files: list[File], expand_all: bool = False) -> None:
        self.clear()
        folder_nodes: dict[Path, TreeNode[Path]] = {self.vault.root: self.root}
        for file in files:
            parent_node = self.root
            parent_dir = self.vault.root
            for part in file.path.relative_to(self.vault.root).parts[:-1]:
                parent_dir = parent_dir / part
                if parent_dir not in folder_nodes:
                    folder_nodes[parent_dir] = parent_node.add(part)
                parent_node = folder_nodes[parent_dir]
            label = file.title + (" [misc]" if self.vault.needs_placement(file.path) else "")
            parent_node.add_leaf(label, data=file.path)
        if expand_all:
            self.root.expand_all()
        else:
            self.root.expand()

    def filter_files(self, query: str) -> Path | None:
        """Rebuild the tree to only the files whose vault-relative path fuzzy-matches query,
        ranked best-first (folders auto-expanded so matches are visible without clicking), and
        return the best match's path so Enter can jump straight to it — or None if query is
        empty or nothing matches. Uses the same Matcher Textual's own command palette uses, so
        fuzzy-find behaves consistently everywhere in the app."""
        if not query:
            self._populate(self._all_files)
            return None
        matcher = Matcher(query)
        scored = [(matcher.match(str(f.path.relative_to(self.vault.root))), f) for f in self._all_files]
        ranked = sorted((pair for pair in scored if pair[0] > 0), key=lambda pair: pair[0], reverse=True)
        self._populate([f for _, f in ranked], expand_all=True)
        return ranked[0][1].path if ranked else None

    def selected_path(self) -> Path | None:
        node = self.cursor_node
        return node.data if node is not None else None

    def reload(self) -> None:
        """Re-scan the vault and rebuild the tree — call after anything that may have moved,
        renamed, or added a file (a classify apply, a draft being saved)."""
        self._all_files = sorted(self.vault.list_files(), key=lambda f: f.path.relative_to(self.vault.root).parts)
        self._populate(self._all_files)
