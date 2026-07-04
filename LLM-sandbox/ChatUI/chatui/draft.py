"""Verb 2 — Draft a paper: back-and-forth authoring of a long-form, living document."""

from __future__ import annotations

from chatui.llm import ModelClient
from chatui.models import Paper
from chatui.vault import Vault


def start_draft(subject: str, vault: Vault) -> Paper:
    raise NotImplementedError


async def revise_draft(paper: Paper, instruction: str, model: ModelClient) -> Paper:
    raise NotImplementedError


def save_draft(paper: Paper, vault: Vault) -> None:
    raise NotImplementedError
