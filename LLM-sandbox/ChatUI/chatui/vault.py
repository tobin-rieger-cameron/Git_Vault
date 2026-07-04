"""File I/O over the vault: reading/writing Papers, frontmatter, wikilinks."""

from __future__ import annotations

from pathlib import Path

from chatui.models import Paper


class Vault:
    def __init__(self, root: Path) -> None:
        raise NotImplementedError

    def list_papers(self) -> list[Paper]:
        raise NotImplementedError

    def load_paper(self, path: Path) -> Paper:
        """Raises PaperNotFoundError if path doesn't resolve to a paper."""
        raise NotImplementedError

    def save_paper(self, paper: Paper) -> None:
        """Raises VaultWriteError on failure."""
        raise NotImplementedError

    def find_by_tag(self, tag: str) -> list[Paper]:
        raise NotImplementedError

    def needs_placement(self, path: Path) -> bool:
        raise NotImplementedError


def parse_frontmatter(content: str) -> tuple[dict, str]:
    raise NotImplementedError


def render_frontmatter(meta: dict, body: str) -> str:
    raise NotImplementedError


def extract_wikilinks(body: str) -> list[str]:
    raise NotImplementedError


def normalize_link_target(name: str) -> str:
    raise NotImplementedError
