"""Learn-from-corrections loop: classify/review suggestions the user overrides feed back into future prompts."""

from __future__ import annotations

from pathlib import Path

from chatui.models import Override


def log_override(kind: str, path: Path, proposed: str, chosen: str, reason: str | None) -> None:
    raise NotImplementedError


def load_recent_overrides(kind: str, limit: int = 8) -> list[Override]:
    raise NotImplementedError
