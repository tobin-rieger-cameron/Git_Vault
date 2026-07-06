"""File I/O over the vault: reading/writing vault Files, frontmatter, wikilinks."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import yaml

from chatui.errors import VaultFileNotFoundError, VaultWriteError
from chatui.models import File

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?\n)---\s*\n?", re.DOTALL)
_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
_NORMALIZE_RE = re.compile(r"[-\s_]+")

_EXCLUDED_DIR_NAMES = {"conversations", "config", "local_db"}


class Vault:
    """Reads and writes the Knowledge/ tree; owns which subdirectories aren't vault content."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def list_files(self) -> list[File]:
        """Load every vault file, excluding conversations/config/local_db."""
        return [self.load_file(path) for path in self._discover_files()]

    def load_file(self, path: Path) -> File:
        """Parse a single vault file's frontmatter and body into a File."""
        if not path.is_file():
            raise VaultFileNotFoundError(f"No such vault file: {path}")
        content = path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(content)
        return _file_from_parts(path, meta, body)

    def save_file(self, file: File) -> None:
        """Write title/tags/last_reviewed back into frontmatter and persist the body."""
        meta = {"title": file.title, "tags": file.tags}
        if file.last_reviewed is not None:
            meta["last_reviewed"] = file.last_reviewed
        content = render_frontmatter(meta, file.body)
        try:
            file.path.parent.mkdir(parents=True, exist_ok=True)
            file.path.write_text(content, encoding="utf-8")
        except OSError as exc:
            raise VaultWriteError(f"Failed to write {file.path}: {exc}") from exc

    def find_by_tag(self, tag: str) -> list[File]:
        return [f for f in self.list_files() if tag in f.tags]

    def needs_placement(self, path: Path) -> bool:
        """Return True if path still awaits classification (sits at vault root or in "misc")."""
        parts = path.relative_to(self.root).parts
        return len(parts) == 1 or parts[0] == "misc"

    def _discover_files(self) -> list[Path]:
        return sorted(
            p
            for p in self.root.rglob("*.md")
            if not _EXCLUDED_DIR_NAMES & set(p.relative_to(self.root).parts[:-1])
        )


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Split a file's raw text into its YAML frontmatter dict and Markdown body."""
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return {}, content
    meta = yaml.safe_load(match.group(1)) or {}
    return meta, content[match.end():].lstrip("\n")


def render_frontmatter(meta: dict, body: str) -> str:
    """Serialize meta as YAML frontmatter above body, dropping empty/None fields."""
    clean_meta = {k: v for k, v in meta.items() if v not in (None, [], "")}
    if not clean_meta:
        return body
    frontmatter = yaml.safe_dump(
        clean_meta, sort_keys=False, default_flow_style=False, allow_unicode=True
    )
    return f"---\n{frontmatter}---\n\n{body}"


def extract_wikilinks(body: str) -> list[str]:
    """Return each [[target]] in body, stripping any |alias suffix."""
    links = []
    for match in _WIKILINK_RE.finditer(body):
        target, _, _alias = match.group(1).partition("|")
        links.append(target.strip())
    return links


def normalize_link_target(name: str) -> str:
    """Collapse hyphens/underscores/whitespace to single spaces and lowercase, for title matching."""
    return _NORMALIZE_RE.sub(" ", name).strip().lower()


def _file_from_parts(path: Path, meta: dict, body: str) -> File:
    created = _coerce_datetime(meta.get("created")) or _stat_datetime(path, "st_ctime")
    updated = _coerce_datetime(meta.get("updated")) or _stat_datetime(path, "st_mtime")
    return File(
        path=path,
        title=str(meta.get("title") or path.stem),
        body=body,
        tags=_coerce_str_list(meta.get("tags")),
        links=extract_wikilinks(body),
        created=created,
        updated=updated,
        last_reviewed=_coerce_datetime(meta.get("last_reviewed")),
    )


def _coerce_str_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if v]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _coerce_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if hasattr(value, "year"):  # datetime.date, as parsed by yaml.safe_load
        return datetime(value.year, value.month, value.day)
    return None


def _stat_datetime(path: Path, attr: str) -> datetime:
    return datetime.fromtimestamp(getattr(path.stat(), attr))
