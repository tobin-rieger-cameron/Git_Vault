"""The retrieve/act/observe loop engine: hands a model a toolbox and lets it drive its own research."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from program_files.utils.llm import ModelClient
from program_files.utils.tools import ToolSpec


@dataclass
class AgentResult:
    """One run's outcome: the final answer, every vault file touched along the way, and a
    (tool_name, args) transcript in call order for UI status display."""

    answer: str
    sources: list[Path] = field(default_factory=list)
    transcript: list[tuple[str, dict]] = field(default_factory=list)


async def run(
    model: ModelClient,
    instructions: str,
    tools: list[ToolSpec],
    touched_sources: list[Path],
    on_tool_call: Callable[[str, dict], None] | None = None,
    on_token: Callable[[str], None] | None = None,
) -> AgentResult:
    """Run instructions through model's tool-calling loop, then package the result with what it touched.

    touched_sources is populated by the tool handlers themselves as they run (see vault_tools.py) —
    the caller passes the same list it built the toolbox with, so this just reads it back afterward.
    on_token fires with real predicted tokens as they arrive during the final answer.
    """
    transcript: list[tuple[str, dict]] = []

    def record_call(name: str, args: dict) -> None:
        transcript.append((name, args))
        if on_tool_call is not None:
            on_tool_call(name, args)

    answer = await model.stream_with_tools(instructions, tools, on_token=on_token, on_tool_call=record_call)
    sources = sorted(set(touched_sources), key=str)
    return AgentResult(answer=answer, sources=sources, transcript=transcript)
