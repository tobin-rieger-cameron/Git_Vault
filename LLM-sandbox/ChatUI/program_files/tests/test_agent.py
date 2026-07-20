from pathlib import Path

import pytest

from program_files.utils import agent
from program_files.utils.tools import ToolSpec


class _FakeModel:
    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.calls: list[tuple[str, list[ToolSpec]]] = []

    async def stream_with_tools(self, prompt: str, tools: list[ToolSpec], on_token=None, on_tool_call=None) -> str:
        self.calls.append((prompt, tools))
        if on_tool_call is not None:
            on_tool_call("search_vault", {"query": "x"})
        return self.answer


@pytest.mark.asyncio
async def test_run_returns_answer_deduped_sources_and_transcript() -> None:
    model = _FakeModel("the answer")
    touched = [Path("A.md"), Path("A.md"), Path("B.md")]

    result = await agent.run(model, "instructions", tools=[], touched_sources=touched)

    assert result.answer == "the answer"
    assert result.sources == [Path("A.md"), Path("B.md")]
    assert result.transcript == [("search_vault", {"query": "x"})]


@pytest.mark.asyncio
async def test_run_forwards_on_tool_call_to_caller() -> None:
    model = _FakeModel("answer")
    seen: list[tuple[str, dict]] = []

    await agent.run(model, "instructions", tools=[], touched_sources=[], on_tool_call=lambda n, a: seen.append((n, a)))

    assert seen == [("search_vault", {"query": "x"})]
