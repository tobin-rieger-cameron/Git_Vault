import asyncio
from dataclasses import dataclass

import pytest

from program_files.utils.errors import ModelUnavailableError
from program_files.utils.llm import ModelClient


@dataclass
class _FakeChunk:
    content: str


class _FakeStreamingModel:
    """Mimics ChatOllama's .astream() interface: yields chunks with a .content
    attribute, one at a time, so tests can observe intermediate state mid-stream."""

    def __init__(self, full_text: str, chunk_size: int = 3, error: Exception | None = None) -> None:
        self._chunks = [full_text[i : i + chunk_size] for i in range(0, len(full_text), chunk_size)]
        self._error = error

    async def astream(self, _prompt: str):
        for chunk in self._chunks:
            await asyncio.sleep(0)
            yield _FakeChunk(chunk)
        if self._error is not None:
            raise self._error

    async def ainvoke(self, _prompt: str):
        if self._error is not None:
            raise self._error
        return _FakeChunk("".join(self._chunks))


def _client_with_fakes(chat_text: str = "", coding_text: str = "", error: Exception | None = None) -> ModelClient:
    client = ModelClient(chat_model="unused", coding_model="unused")
    client._chat = _FakeStreamingModel(chat_text, error=error)
    client._coding = _FakeStreamingModel(coding_text, error=error)
    return client


@pytest.mark.asyncio
async def test_stream_returns_full_text_and_calls_on_token() -> None:
    client = _client_with_fakes(chat_text="Hello, world!")
    seen: list[str] = []

    result = await client.stream("prompt", on_token=seen.append)

    assert result == "Hello, world!"
    assert "".join(seen) == "Hello, world!"


@pytest.mark.asyncio
async def test_stream_wraps_failures_as_model_unavailable() -> None:
    client = _client_with_fakes(chat_text="partial", error=RuntimeError("connection refused"))

    with pytest.raises(ModelUnavailableError):
        await client.stream("prompt")


@pytest.mark.asyncio
async def test_stream_lines_recognizes_completed_lines_only() -> None:
    full_text = "Taxonomy: taxonomy, classification\nMetadata Standards: metadata\nnot-a-real-note: x\n"
    client = _client_with_fakes(coding_text=full_text)

    notes = {"Taxonomy", "Metadata Standards"}
    tag_map: dict[str, list[str]] = {}

    def on_line(line: str) -> str | None:
        if ":" not in line:
            return None
        stem_part, tags_part = line.split(":", 1)
        key = stem_part.strip()
        tags = [t.strip() for t in tags_part.split(",") if t.strip()]
        if key in notes and tags:
            tag_map[key] = tags
            return f"{key}.md: {', '.join(tags)}"
        return None

    result = await client.stream_lines("prompt", on_line)

    assert result == full_text
    assert tag_map == {"Taxonomy": ["taxonomy", "classification"], "Metadata Standards": ["metadata"]}


@pytest.mark.asyncio
async def test_stream_lines_also_supports_on_token_for_live_display() -> None:
    client = _client_with_fakes(coding_text="a: 1\nb: 2\n")
    tokens: list[str] = []

    await client.stream_lines("prompt", on_line=lambda line: None, on_token=tokens.append)

    assert "".join(tokens) == "a: 1\nb: 2\n"


@pytest.mark.asyncio
async def test_ask_coding_returns_stripped_content() -> None:
    client = _client_with_fakes(coding_text="  the answer  ")

    result = await client.ask_coding("prompt")

    assert result == "the answer"


@pytest.mark.asyncio
async def test_ask_coding_wraps_failures() -> None:
    client = _client_with_fakes(error=RuntimeError("model not pulled"))

    with pytest.raises(ModelUnavailableError):
        await client.ask_coding("prompt")


def test_switch_chat_model_updates_name() -> None:
    client = ModelClient(chat_model="llama3.1:8b", coding_model="qwen2.5-coder:7b")

    client.switch_chat_model("llama3.2:3b")

    assert client.chat_model_name == "llama3.2:3b"
