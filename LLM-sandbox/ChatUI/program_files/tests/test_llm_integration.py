"""Integration smoke tests against real local Ollama chat/coding models.

Skipped automatically if Ollama isn't reachable, since they are not hermetic unit tests.
"""

from __future__ import annotations

import httpx
import pytest

from program_files.llm import ModelClient


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


async def test_stream_returns_nonempty_real_response() -> None:
    client = ModelClient(chat_model="llama3.2:3b", coding_model="qwen2.5-coder:7b")

    result = await client.stream("Reply with exactly the word: pong")

    assert result.strip()


async def test_ask_coding_returns_nonempty_real_response() -> None:
    client = ModelClient(chat_model="llama3.2:3b", coding_model="qwen2.5-coder:7b")

    result = await client.ask_coding("Reply with exactly the word: pong")

    assert result.strip()


async def test_switch_chat_model_then_stream_still_works() -> None:
    client = ModelClient(chat_model="llama3.1:8b", coding_model="qwen2.5-coder:7b")

    client.switch_chat_model("llama3.2:3b")
    result = await client.stream("Reply with exactly the word: pong")

    assert client.chat_model_name == "llama3.2:3b"
    assert result.strip()
