"""Ollama boundary: chat/coding models and token streaming. No ChatOllama/langchain types escape this module."""

from __future__ import annotations

import logging
from typing import Callable

from langchain_ollama import ChatOllama

from chatui.debug_log import truncate
from chatui.errors import ModelUnavailableError

_log = logging.getLogger(__name__)


class ModelClient:
    """Wraps two ChatOllama instances (chat + coding) behind plain str-in/str-out methods."""

    def __init__(self, chat_model: str, coding_model: str) -> None:
        self.chat_model_name = chat_model
        self.coding_model_name = coding_model
        self._chat = ChatOllama(model=chat_model)
        self._coding = ChatOllama(model=coding_model)

    def switch_chat_model(self, name: str) -> None:
        self._chat = ChatOllama(model=name)
        self.chat_model_name = name

    async def stream(self, prompt: str, on_token: Callable[[str], None] | None = None) -> str:
        """Stream the chat model, calling on_token per chunk if given, and return the full text."""
        _log.debug("chat prompt (%s): %s", self.chat_model_name, truncate(prompt))
        parts: list[str] = []
        try:
            async for chunk in self._chat.astream(prompt):
                parts.append(chunk.content)
                if on_token is not None:
                    on_token(chunk.content)
        except Exception as exc:
            _log.error("chat model call failed: %s", exc)
            raise ModelUnavailableError(f"Chat model unavailable: {exc}") from exc
        response = "".join(parts)
        _log.debug("chat response: %s", truncate(response))
        return response

    async def stream_lines(
        self,
        prompt: str,
        on_line: Callable[[str], str | None],
        on_token: Callable[[str], None] | None = None,
    ) -> str:
        """Stream the coding model, calling on_line once per completed line (last partial line is never passed)."""
        _log.debug("coding prompt (%s): %s", self.coding_model_name, truncate(prompt))
        parts: list[str] = []
        processed = 0
        try:
            async for chunk in self._coding.astream(prompt):
                parts.append(chunk.content)
                if on_token is not None:
                    on_token(chunk.content)
                text = "".join(parts)
                complete_lines = text.split("\n")[:-1]
                while processed < len(complete_lines):
                    on_line(complete_lines[processed])
                    processed += 1
        except Exception as exc:
            _log.error("coding model streaming call failed: %s", exc)
            raise ModelUnavailableError(f"Coding model unavailable: {exc}") from exc
        response = "".join(parts)
        _log.debug("coding response: %s", truncate(response))
        return response

    async def ask_coding(self, prompt: str) -> str:
        """Make a single non-streaming call to the coding model and return the stripped response text."""
        _log.debug("coding prompt (%s): %s", self.coding_model_name, truncate(prompt))
        try:
            response = await self._coding.ainvoke(prompt)
        except Exception as exc:
            _log.error("coding model call failed: %s", exc)
            raise ModelUnavailableError(f"Coding model unavailable: {exc}") from exc
        text = response.content.strip()
        _log.debug("coding response: %s", truncate(text))
        return text
