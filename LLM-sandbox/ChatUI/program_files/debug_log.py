"""Single-file debug logging: every module's logger.getLogger(__name__) feeds one log file.

Textual owns the terminal while the app runs, so nothing in this package may print() or
write to stderr — that corrupts the TUI's rendering. A file handler on the "chatui" logger
is the only sanctioned way to leave a trace of what happened.
"""

from __future__ import annotations

import logging
from pathlib import Path

_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def configure(log_path: Path, level: int = logging.DEBUG) -> None:
    """Attach a file handler to the "chatui" logger; child loggers propagate into it by default."""
    logger = logging.getLogger("chatui")
    logger.setLevel(level)
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter(_FORMAT))
    logger.addHandler(handler)


def truncate(text: str, limit: int = 400) -> str:
    """Shorten a prompt/response for a log line without losing the shape of what was sent."""
    collapsed = " ".join(text.split())
    return collapsed if len(collapsed) <= limit else collapsed[:limit] + "…"
