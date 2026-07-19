"""Runtime settings, loaded once from config/*.md frontmatter."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?\n)---", re.DOTALL)

_DEFAULTS = {
    "chat_model": "llama3.1:8b",
    "coding_model": "qwen2.5-coder:7b",
    "embed_model": "nomic-embed-text",
    "top_k": 5,
    "chunk_size": 800,
    "chunk_overlap": 100,
    "similarity_threshold": 0.65,
    "history_window": 2,
    "web_search_results": 3,
    "review_staleness_days": 30,
}


@dataclass
class Settings:
    """Resolved runtime configuration for one ChatApp session."""

    vault_path: Path
    chat_model: str
    coding_model: str
    embed_model: str
    top_k: int
    chunk_size: int
    chunk_overlap: int
    similarity_threshold: float
    history_window: int
    web_search_results: int
    review_staleness_days: int


def _read_frontmatter(path: Path) -> dict:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return {}
    return yaml.safe_load(match.group(1)) or {}


def load_settings(config_dir: Path) -> Settings:
    """Merge settings.md and models.md frontmatter over _DEFAULTS, resolving vault_path."""
    merged = dict(_DEFAULTS)
    for name in ("settings", "models"):
        merged.update(_read_frontmatter(config_dir / f"{name}.md"))

    vault_path = merged.get("vault_path")
    resolved_vault_path = Path(vault_path) if vault_path else config_dir.parent.parent

    return Settings(
        vault_path=resolved_vault_path,
        chat_model=merged["chat_model"],
        coding_model=merged["coding_model"],
        embed_model=merged["embed_model"],
        top_k=merged["top_k"],
        chunk_size=merged["chunk_size"],
        chunk_overlap=merged["chunk_overlap"],
        similarity_threshold=merged["similarity_threshold"],
        history_window=merged["history_window"],
        web_search_results=merged["web_search_results"],
        review_staleness_days=merged["review_staleness_days"],
    )
