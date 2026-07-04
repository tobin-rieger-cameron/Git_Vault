"""Verb 1 — Ask: vault-first RAG, falling back to grounded/model-knowledge, with optional web supplement."""

from __future__ import annotations

from pathlib import Path

from chatui.llm import ModelClient
from chatui.models import AskResult, Chunk, RetrievalPath
from chatui.retrieval import Retriever
from chatui.vault import Vault


async def ask(
    question: str,
    vault: Vault,
    retriever: Retriever,
    model: ModelClient,
    history: list[tuple[str, str]],
    web_enabled: bool,
) -> AskResult:
    raise NotImplementedError


def choose_retrieval_path(chunks: list[Chunk], threshold: float) -> RetrievalPath:
    raise NotImplementedError


def is_broad_topic_question(question: str) -> bool:
    raise NotImplementedError


def source_covers_topic(sources: list[Path], topic: str) -> bool:
    raise NotImplementedError
