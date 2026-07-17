"""Real local-Ollama check that generate_review_questions produces usable output."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import httpx
import pytest

from program_files.llm import ModelClient
from program_files.models import File
from program_files.review import generate_review_questions


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


async def test_generate_review_questions_real_model(tmp_path: Path) -> None:
    model = ModelClient(chat_model="llama3.2:3b", coding_model="qwen2.5-coder:7b")
    now = datetime.now()
    file = File(
        path=tmp_path / "Photosynthesis.md",
        title="Photosynthesis",
        body=(
            "Photosynthesis is the process by which plants convert sunlight, water, and carbon "
            "dioxide into glucose and oxygen, using chlorophyll in chloroplasts."
        ),
        tags=["biology"], links=[], created=now, updated=now, last_reviewed=None,
    )

    questions = await generate_review_questions(file, model, count=2)

    assert questions
    assert all(q.question.strip() and q.answer_hint.strip() for q in questions)
