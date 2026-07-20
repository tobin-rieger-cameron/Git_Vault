"""Tree-based file picker — technique salvaged from the shelved front-end-refactor plan."""

from __future__ import annotations

from pathlib import Path

from rich.style import Style
from rich.text import Text
from textual.fuzzy import Matcher
from textual.widgets import Tree
from textual.widgets.tree import TreeNode

from program_files.utils.models import File
from program_files.ui import theme
from program_files.utils.vault import Vault


class FilePicker(Tree[Path]):
    """A Textual Tree of the vault's folder structure, for picking a file to draft/classify/review."""

    def __init__(self, vault: Vault) -> None:
        super().__init__(label="Vault")
        self.vault = vault
        self.show_root = False
        self._all_files = sorted(vault.list_files(), key=lambda f: f.path.relative_to(vault.root).parts)
        # None until the first /ingest reports what's actually embedded — no coloring or ghost
        # entries render until then, since "new" and "stale" are both relative to that manifest.
        self._ingested_paths: set[Path] | None = None
        self._status_by_path: dict[Path, str] = {}
        self._filter_active = False
        self._populate(self._all_files)

    def render_label(self, node: TreeNode[Path], base_style: Style, style: Style) -> Text:
        """Render a folder node muted, a file node bright (or green/red for ingest status),
        ellipsis-truncated to fit the pane."""
        plain = node.label.plain
        if node.allow_expand:
            icon = "▼ " if node.is_expanded else "▶ "
            color = theme.MUTED
        else:
            icon = "  "
            status = self._status_by_path.get(node.data)
            color = theme.ADDITION if status == "new" else theme.TAG_REMOVE if status == "stale" else theme.BRIGHT

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
        self._status_by_path = {}
        entries: list[tuple[Path, str]] = [
            # The tree shows the file's actual on-disk name, not frontmatter title — those two
            # drift apart the moment someone renames a file without also updating its title:
            # field, and the browser should always match what's really on disk.
            (file.path, file.path.stem + (" [misc]" if self.vault.needs_placement(file.path) else ""))
            for file in files
        ]
        if self._ingested_paths is not None:
            current_paths = {file.path for file in files}
            for file in files:
                if file.path not in self._ingested_paths:
                    self._status_by_path[file.path] = "new"
            for stale_path in sorted(self._ingested_paths - current_paths):
                try:
                    stale_path.relative_to(self.vault.root)
                except ValueError:
                    continue  # outside the vault root entirely — not ours to show
                self._status_by_path[stale_path] = "stale"
                entries.append((stale_path, f"{stale_path.stem} [stale index]"))
        entries.sort(key=lambda entry: entry[0].relative_to(self.vault.root).parts)

        folder_nodes: dict[Path, TreeNode[Path]] = {self.vault.root: self.root}
        for path, label in entries:
            parent_node = self.root
            parent_dir = self.vault.root
            for part in path.relative_to(self.vault.root).parts[:-1]:
                parent_dir = parent_dir / part
                if parent_dir not in folder_nodes:
                    folder_nodes[parent_dir] = parent_node.add(part, data=parent_dir)
                parent_node = folder_nodes[parent_dir]
            # Text(), not the plain str — Tree.process_label runs a bare str through
            # Text.from_markup(), which silently swallows anything inside [...] as an (invalid,
            # unrecognized) style tag instead of literal brackets. Pre-existing: "[misc]" below
            # was never actually visible in the UI before this fix.
            parent_node.add_leaf(Text(label), data=path)
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
        self._filter_active = bool(query)
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

    def reload(self, ingested_paths: set[Path] | None = None) -> None:
        """Re-scan the vault and rebuild the tree unconditionally — call after anything that
        definitely moved, renamed, or added a file (a classify apply, a draft being saved, an
        /ingest run). Passing ingested_paths (Retriever.ingested_paths()) refreshes new/stale
        coloring too; omit it to keep whatever coloring was last set."""
        self._all_files = sorted(self.vault.list_files(), key=lambda f: f.path.relative_to(self.vault.root).parts)
        if ingested_paths is not None:
            self._ingested_paths = ingested_paths
        self._populate(self._all_files)

    def refresh_from_disk(self, ingested_paths: set[Path] | None = None) -> bool:
        """Re-scan the vault and rebuild the tree only if something actually changed — for a
        timer-driven poll, where rebuilding unconditionally would reset the tree's expand/cursor
        state every tick even when nothing on disk moved. Returns whether it rebuilt. No-ops
        while a search filter is active, so a poll can't yank the view back to the full tree out
        from under someone mid-search."""
        if self._filter_active:
            return False
        fresh = sorted(self.vault.list_files(), key=lambda f: f.path.relative_to(self.vault.root).parts)
        changed = [(f.path, f.updated) for f in fresh] != [(f.path, f.updated) for f in self._all_files]
        ingest_changed = ingested_paths is not None and ingested_paths != self._ingested_paths
        if not changed and not ingest_changed:
            return False
        self._all_files = fresh
        if ingested_paths is not None:
            self._ingested_paths = ingested_paths
        self._populate(self._all_files)
        return True
