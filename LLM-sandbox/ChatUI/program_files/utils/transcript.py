"""Session transcript writer: appends every visible chat line to a local file as it happens,
so a crash or force-quit loses at most the one line in flight, not the whole session."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


class TranscriptWriter:
    """Appends chat lines to one Markdown file per session, opened fresh at construction."""

    def __init__(self, log_dir: Path, vault_name: str) -> None:
        log_dir.mkdir(parents=True, exist_ok=True)
        started = datetime.now()
        self._path = log_dir / f"{started:%Y-%m-%d_%H%M%S}.md"
        self._path.write_text(f"# Session — {started:%Y-%m-%d %H:%M:%S} — {vault_name}\n\n", encoding="utf-8")

    def write_you(self, text: str) -> None:
        self._append(f"> {text}")

    def write_answer(self, text: str) -> None:
        self._append(text)

    def write_status(self, text: str) -> None:
        self._append(f"· {text}")

    def write_hint(self, text: str) -> None:
        self._append(f"· {text}")

    def _append(self, text: str) -> None:
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(text + "\n\n")
