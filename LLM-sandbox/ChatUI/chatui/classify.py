"""Verb 3 — Classify inline: suggest a paper's folder/tags/links right after it's drafted, one at a time."""

from __future__ import annotations

from chatui.llm import ModelClient
from chatui.models import ClassificationSuggestion, Paper
from chatui.vault import Vault


async def suggest_classification(paper: Paper, vault: Vault, model: ModelClient) -> ClassificationSuggestion:
    raise NotImplementedError


def apply_classification(paper: Paper, suggestion: ClassificationSuggestion, vault: Vault) -> Paper:
    raise NotImplementedError
