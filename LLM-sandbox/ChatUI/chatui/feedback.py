"""Learn-from-corrections loop: classify/review suggestions the user overrides feed back into future prompts."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from chatui.models import Override

_FEEDBACK_PATH = Path(__file__).resolve().parent.parent / "config" / "feedback.md"

_ENTRY_RE = re.compile(
    r"^## (?P<date>\S+) — (?P<name>.+?) \((?P<kind>[^)]+)\)\n"
    r"Proposed: (?P<proposed>.*)\n"
    r"Chosen: (?P<chosen>.*)\n"
    r"Reason: (?P<reason>.*)\n",
    re.MULTILINE,
)


def log_override(kind: str, path: Path, proposed: str, chosen: str, reason: str | None) -> None:
    """Append a structured entry to config/feedback.md recording what the user chose over the suggestion."""
    reason_text = reason.strip() if reason and reason.strip() else "(none given)"
    entry = (
        f"## {datetime.now():%Y-%m-%d} — {path.name} ({kind})\n"
        f"Proposed: {proposed.strip()[:300]}\n"
        f"Chosen: {chosen.strip()[:300]}\n"
        f"Reason: {reason_text}\n"
    )

    if not _FEEDBACK_PATH.exists():
        _FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
        _FEEDBACK_PATH.write_text(
            "---\nsummary: Log of manual overrides during /classify and /review — "
            "fed back into future suggestion prompts.\n---\n\n# Feedback\n\n",
            encoding="utf-8",
        )

    with _FEEDBACK_PATH.open("a", encoding="utf-8") as f:
        f.write(entry + "\n")


def load_recent_overrides(kind: str, limit: int = 8) -> list[Override]:
    """Return the most recent overrides of the given kind, oldest of the limit first."""
    if not _FEEDBACK_PATH.exists():
        return []
    content = _FEEDBACK_PATH.read_text(encoding="utf-8")
    matches = [m for m in _ENTRY_RE.finditer(content) if m.group("kind") == kind]
    return [_to_override(m) for m in matches[-limit:]]


def _to_override(match: re.Match) -> Override:
    reason = match.group("reason")
    return Override(
        kind=match.group("kind"),
        path=Path(match.group("name")),
        proposed=match.group("proposed"),
        chosen=match.group("chosen"),
        reason=None if reason == "(none given)" else reason,
        timestamp=datetime.strptime(match.group("date"), "%Y-%m-%d"),
    )
