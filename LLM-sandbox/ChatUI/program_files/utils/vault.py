"""File I/O over the vault: reading/writing vault Files, frontmatter, wikilinks."""

from __future__ import annotations

import fnmatch
import logging
import re
from datetime import datetime
from pathlib import Path

import yaml

from program_files.utils.errors import VaultFileNotFoundError, VaultWriteError
from program_files.utils.models import File

_log = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?\n)---\s*\n?", re.DOTALL)
_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
_NORMALIZE_RE = re.compile(r"[-\s_]+")

_IGNORE_FILE_NAME = ".vaultignore"


class _FlowListDumper(yaml.SafeDumper):
    """Emits lists inline (tags: [a, b]) — Obsidian's own frontmatter convention, and what every
    hand-written vault file already uses; plain safe_dump would emit an unindented "- a" block."""


_FlowListDumper.add_representer(
    list, lambda dumper, data: dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=True)
)


def _is_hidden_or_cache(name: str) -> bool:
    """True for dot-directories (.venv, .git, .pytest_cache, …) and __-wrapped ones (__pycache__)."""
    return name.startswith(".") or name.startswith("__")


def _load_ignore_patterns(root: Path) -> list[str]:
    """Read gitignore-lite patterns from <root>/.vaultignore; missing file means no extra patterns."""
    ignore_file = root / _IGNORE_FILE_NAME
    if not ignore_file.is_file():
        return []
    patterns = []
    for line in ignore_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(line.rstrip("/"))
    return patterns


def _matches_ignore(rel_parts: tuple[str, ...], patterns: list[str]) -> bool:
    """True if any path component (bare pattern) or the full relative path (pattern with "/") matches."""
    rel_path = "/".join(rel_parts)
    for pattern in patterns:
        if "/" in pattern:
            if fnmatch.fnmatch(rel_path, pattern):
                return True
        elif any(fnmatch.fnmatch(part, pattern) for part in rel_parts):
            return True
    return False


class Vault:
    """Reads and writes the vault tree; excludes hidden/cache dirs plus anything in .vaultignore."""

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
            _log.error("failed to write %s: %s", file.path, exc)
            raise VaultWriteError(f"Failed to write {file.path}: {exc}") from exc
        _log.info("saved %s (tags=%s)", file.path, file.tags)

    def find_by_tag(self, tag: str) -> list[File]:
        return [f for f in self.list_files() if tag in f.tags]

    def needs_placement(self, path: Path) -> bool:
        """Return True if path still awaits classification (sits at vault root or in "misc")."""
        parts = path.relative_to(self.root).parts
        return len(parts) == 1 or parts[0] == "misc"

    def _discover_files(self) -> list[Path]:
        patterns = _load_ignore_patterns(self.root)
        files = []
        for p in self.root.rglob("*.md"):
            rel_parts = p.relative_to(self.root).parts
            if any(_is_hidden_or_cache(part) for part in rel_parts[:-1]):
                continue
            if _matches_ignore(rel_parts, patterns):
                continue
            files.append(p)
        return sorted(files)


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
    frontmatter = yaml.dump(
        clean_meta, Dumper=_FlowListDumper, sort_keys=False, default_flow_style=False, allow_unicode=True
    )
    return f"---\n{frontmatter}---\n\n{body}"


def extract_wikilinks(body: str) -> list[str]:
    """Return each [[target]] in body, stripping any |alias suffix."""
    links = []
    for match in _WIKILINK_RE.finditer(body):
        target, _, _alias = match.group(1).partition("|")
        links.append(target.strip())
    return links


def find_wikilinks(body: str) -> list[tuple[int, int, str]]:
    """Return (start, end, target) for each [[target]] match's full span, for highlighting/click mapping."""
    spans = []
    for match in _WIKILINK_RE.finditer(body):
        target, _, _alias = match.group(1).partition("|")
        spans.append((match.start(), match.end(), target.strip()))
    return spans


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
