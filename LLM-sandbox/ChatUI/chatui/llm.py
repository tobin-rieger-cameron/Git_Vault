"""Ollama boundary: chat/coding models and token streaming. No ChatOllama/langchain types escape this module."""

from __future__ import annotations

from typing import Callable


class ModelClient:
    def __init__(self, chat_model: str, coding_model: str) -> None:
        raise NotImplementedError

    def switch_chat_model(self, name: str) -> None:
        raise NotImplementedError

    async def stream(self, prompt: str, on_token: Callable[[str], None] | None = None) -> str:
        """Raises ModelUnavailableError if Ollama is unreachable."""
        raise NotImplementedError

    async def stream_lines(self, prompt: str, on_line: Callable[[str], str | None]) -> str:
        raise NotImplementedError

    async def ask_coding(self, prompt: str) -> str:
        raise NotImplementedError
