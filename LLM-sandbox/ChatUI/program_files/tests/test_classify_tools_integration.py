"""Real local-Ollama check that suggest_classification produces sane output. Skipped if unreachable."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import httpx
import pytest

from program_files.utils.tools.classify_tools import apply_classification, suggest_classification
from program_files.utils.llm import ModelClient
from program_files.utils.models import File
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


async def test_suggest_and_apply_classification_end_to_end(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    model = ModelClient(chat_model="llama3.2:3b", coding_model="qwen2.5-coder:7b")

    now = datetime.now()
    file = File(
        path=tmp_path / "Neural Networks.md",
        title="Neural Networks",
        body=(
            "Neural networks are computing systems inspired by biological brains, made of "
            "layers of interconnected nodes that learn patterns from data through training."
        ),
        tags=[],
        links=[],
        created=now,
        updated=now,
        last_reviewed=None,
    )
    vault.save_file(file)

    suggestion = await suggest_classification(file, vault, model)

    assert suggestion.suggested_tags
    assert suggestion.suggested_folder

    updated = apply_classification(file, suggestion, vault)

    assert updated.path.exists()
    assert updated.tags
