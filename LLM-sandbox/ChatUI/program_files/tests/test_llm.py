import asyncio
from dataclasses import dataclass, field

import pytest

from program_files.utils.errors import ModelUnavailableError
from program_files.utils.llm import ModelClient
from program_files.utils.tools import ToolSpec


@dataclass
class _FakeChunk:
    content: str

    def __add__(self, other: "_FakeChunk") -> "_FakeChunk":
        return _FakeChunk(content=self.content + other.content)


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


@dataclass
class _FakeToolResponse:
    """Mimics an AIMessageChunk: .content is the text, .tool_calls is empty once the model is done."""

    content: str
    tool_calls: list[dict] = field(default_factory=list)

    def __add__(self, other: "_FakeToolResponse") -> "_FakeToolResponse":
        return _FakeToolResponse(content=self.content + other.content, tool_calls=other.tool_calls or self.tool_calls)


class _FakeBoundModel:
    """Mimics the object bind_tools() returns: scripted responses, one per .astream() call (single chunk each)."""

    def __init__(self, responses: list[_FakeToolResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[list] = []

    async def astream(self, messages: list):
        self.calls.append(list(messages))
        yield self._responses.pop(0)


class _FakeToolCallingModel(_FakeStreamingModel):
    """Adds bind_tools() on top of _FakeStreamingModel, for stream_with_tools tests."""

    def __init__(self, bound_responses: list[_FakeToolResponse], final_text: str = "forced final answer") -> None:
        super().__init__(final_text)
        self.bound_responses = bound_responses
        self.bind_tools_calls: list[list[dict]] = []

    def bind_tools(self, schemas: list[dict]) -> _FakeBoundModel:
        self.bind_tools_calls.append(schemas)
        return _FakeBoundModel(self.bound_responses)


def _tool(name: str, handler) -> ToolSpec:
    return ToolSpec(name=name, description=f"{name} tool", parameters={"type": "object", "properties": {}}, handler=handler)


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


@pytest.mark.asyncio
async def test_stream_with_tools_empty_toolbox_delegates_to_stream() -> None:
    client = _client_with_fakes(chat_text="plain answer")

    result = await client.stream_with_tools("prompt", tools=[])

    assert result == "plain answer"


@pytest.mark.asyncio
async def test_stream_with_tools_runs_a_tool_then_returns_final_answer() -> None:
    calls: list[dict] = []

    async def handler(args: dict) -> str:
        calls.append(args)
        return "3 matching notes"

    tool = _tool("search_vault", handler)
    fake = _FakeToolCallingModel(
        bound_responses=[
            _FakeToolResponse(content="", tool_calls=[{"name": "search_vault", "args": {"query": "x"}, "id": "1"}]),
            _FakeToolResponse(content="Here's the answer."),
        ]
    )
    client = ModelClient(chat_model="unused", coding_model="unused")
    client._chat = fake

    seen: list[tuple[str, dict]] = []
    result = await client.stream_with_tools("prompt", [tool], on_tool_call=lambda n, a: seen.append((n, a)))

    assert result == "Here's the answer."
    assert calls == [{"query": "x"}]
    assert seen == [("search_vault", {"query": "x"})]


@pytest.mark.asyncio
async def test_stream_with_tools_unknown_tool_name_is_reported_not_raised() -> None:
    fake = _FakeToolCallingModel(
        bound_responses=[
            _FakeToolResponse(content="", tool_calls=[{"name": "no_such_tool", "args": {}, "id": "1"}]),
            _FakeToolResponse(content="done anyway"),
        ]
    )
    client = ModelClient(chat_model="unused", coding_model="unused")
    client._chat = fake

    result = await client.stream_with_tools("prompt", [_tool("search_vault", lambda args: "x")])

    assert result == "done anyway"


@pytest.mark.asyncio
async def test_stream_with_tools_forces_a_final_answer_after_max_iterations() -> None:
    async def handler(_args: dict) -> str:
        return "still searching"

    tool = _tool("search_vault", handler)
    # Every scripted round keeps calling the tool — never a final no-tool-calls response — so the
    # loop should hit its iteration cap and force a plain answer via the unbound model instead.
    fake = _FakeToolCallingModel(
        bound_responses=[
            _FakeToolResponse(content="", tool_calls=[{"name": "search_vault", "args": {}, "id": str(i)}])
            for i in range(4)
        ],
        final_text="forced final answer",
    )
    client = ModelClient(chat_model="unused", coding_model="unused")
    client._chat = fake

    result = await client.stream_with_tools("prompt", [tool])

    assert result == "forced final answer"
