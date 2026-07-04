"""Verb 4 — Review: lightweight recall questions and a due-for-review signal, not a spaced-repetition engine."""

from __future__ import annotations

from datetime import timedelta

from chatui.llm import ModelClient
from chatui.models import Paper, ReviewQuestion
from chatui.vault import Vault


async def generate_review_questions(paper: Paper, model: ModelClient, count: int = 3) -> list[ReviewQuestion]:
    raise NotImplementedError


def mark_reviewed(paper: Paper, vault: Vault) -> Paper:
    raise NotImplementedError


def papers_due_for_review(vault: Vault, staleness: timedelta) -> list[Paper]:
    raise NotImplementedError
