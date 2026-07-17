"""Real local-Ollama check that revise_draft actually generates prose. Skipped if unreachable."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import httpx
import pytest

from program_files.draft import revise_draft, save_draft, start_draft
from program_files.utils.llm import ModelClient
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


async def test_draft_full_loop_writes_then_saves(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    model = ModelClient(chat_model="llama3.2:3b", coding_model="qwen2.5-coder:7b")

    file = start_draft("Photosynthesis", vault)
    assert file.body == ""

    revised = await revise_draft(file, "Write one short paragraph explaining what photosynthesis is.", model)
    assert revised.body.strip()
    assert revised.updated > file.created or revised.updated >= datetime.now().replace(microsecond=0)

    save_draft(revised, vault)
    loaded = vault.load_file(file.path)
    assert loaded.body == revised.body
    assert loaded.title == "Photosynthesis"
