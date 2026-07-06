"""Live token/line display widget — ported from the old app's _stream_llm/_stream_lines pattern."""

from __future__ import annotations

from typing import Callable

from textual.widgets import Static


class StreamingText(Static):
    """A widget that updates its own display token-by-token as a ModelClient stream call runs."""

    async def stream(self, model_stream_call: Callable, prompt: str) -> str:
        raise NotImplementedError
