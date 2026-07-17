"""End-to-end Ask against real local Ollama models + a real (scratch) ChromaDB.

Skipped automatically if Ollama isn't reachable.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import httpx
import pytest

from program_files.ask import ask
from program_files.utils.llm import ModelClient
from program_files.utils.models import File, RetrievalPath
from program_files.utils.retrieval import Retriever
from program_files.utils.vault import Vault


def _ollama_available() -> bool:
    try:
        httpx.get("http://localhost:11434/api/tags", timeout=1.0)
        return True
    except httpx.HTTPError:
        return False


pytestmark = [
    pytest.mark.skipif(not _ollama_available(), reason="Ollama not reachable on localhost:11434"),
    pytest.mark.asyncio,
]


def _file(path: Path, body: str, tags: list[str]) -> File:
    now = datetime.now()
    return File(path=path, title=path.stem, body=body, tags=tags, links=[], created=now, updated=now, last_reviewed=None)


async def test_ask_answers_from_vault_when_ingested(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    retriever = Retriever(db_path=tmp_path / "db", embed_model="nomic-embed-text")
    model = ModelClient(chat_model="llama3.2:3b", coding_model="qwen2.5-coder:7b")

    files = [
        _file(
            tmp_path / "Photosynthesis.md",
            "Photosynthesis is the process by which plants convert sunlight, water, and "
            "carbon dioxide into glucose and oxygen using chlorophyll in their leaves.",
            ["biology"],
        )
    ]
    retriever.ingest(files)

    result = await ask(
        "What is photosynthesis?", vault, retriever, model, history=[], web_enabled=False,
        similarity_threshold=0.5,
    )

    assert result.path is RetrievalPath.VAULT
    assert result.answer.strip()
    assert result.sources == [Path("Photosynthesis.md")]


async def test_ask_answers_from_model_knowledge_when_vault_empty(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    retriever = Retriever(db_path=tmp_path / "db", embed_model="nomic-embed-text")
    model = ModelClient(chat_model="llama3.2:3b", coding_model="qwen2.5-coder:7b")

    result = await ask("What is the capital of France?", vault, retriever, model, history=[], web_enabled=False)

    assert result.path is RetrievalPath.MODEL_KNOWLEDGE
    assert result.sources == []
    assert result.answer.strip()
