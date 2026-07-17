"""Verb 4 — Review: lightweight recall questions and a due-for-review signal, not a spaced-repetition engine."""

from __future__ import annotations

import re
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path

from chatui.llm import ModelClient
from chatui.models import File, ReviewQuestion
from chatui.vault import Vault

_QUESTION_RE = re.compile(r"Q:\s*(.+?)\s*\n\s*Hint:\s*(.+?)\s*(?:\n|$)", re.MULTILINE)


async def generate_review_questions(file: File, model: ModelClient, count: int = 3) -> list[ReviewQuestion]:
    """Ask the model for count Q/hint pairs; malformed or unparseable lines are silently dropped."""
    prompt = (
        f"Generate exactly {count} short recall questions testing understanding of this note, "
        "each with a brief answer hint (not the full answer — just enough to jog memory).\n"
        "Reply in exactly this format, one Q/Hint pair per two lines, nothing else:\n"
        "Q: <question>\nHint: <hint>\n\n"
        f"Title: {file.title}\n\nContent:\n{file.body[:2000]}\n"
    )
    raw = await model.ask_coding(prompt)
    return _parse_review_questions(raw, file.path, count)


def mark_reviewed(file: File, vault: Vault) -> File:
    updated = replace(file, last_reviewed=datetime.now())
    vault.save_file(updated)
    return updated


def files_due_for_review(vault: Vault, staleness: timedelta) -> list[File]:
    """Return files never reviewed or last reviewed before the staleness cutoff, most overdue first."""
    cutoff = datetime.now() - staleness
    due = [f for f in vault.list_files() if f.last_reviewed is None or f.last_reviewed < cutoff]
    return sorted(due, key=lambda f: f.last_reviewed or datetime.min)


def _parse_review_questions(raw: str, path: Path, count: int) -> list[ReviewQuestion]:
    matches = _QUESTION_RE.findall(raw)
    return [
        ReviewQuestion(file_path=path, question=question.strip(), answer_hint=hint.strip())
        for question, hint in matches[:count]
    ]
