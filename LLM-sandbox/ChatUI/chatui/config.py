"""Runtime settings, loaded once from config/*.md frontmatter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
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


def load_settings(config_dir: Path) -> Settings:
    raise NotImplementedError
