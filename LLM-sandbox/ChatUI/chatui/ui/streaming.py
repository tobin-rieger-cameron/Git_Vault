"""Live token/line display widget — ported from the old app's _stream_llm/_stream_lines pattern."""

from __future__ import annotations

from typing import Callable

from rich.text import Text
from textual.widgets import Static


class StreamingText(Static):
    """A widget that updates its own display token-by-token as a ModelClient stream call runs."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._text = ""

    def show(self, text: str) -> None:
        """Display text immediately, with no streaming — for previewing an already-written file."""
        self._text = text
        self.update(Text(text))  # Text(), not a raw str, so vault content isn't parsed as Rich markup

    async def stream(self, model_stream_call: Callable, prompt: str) -> str:
        """Stream model_stream_call's output into the widget token by token, returning the full text."""
        self._text = ""
        self.update(Text(""))

        def on_token(token: str) -> None:
            self._text += token
            self.update(Text(self._text))

        return await model_stream_call(prompt, on_token=on_token)
