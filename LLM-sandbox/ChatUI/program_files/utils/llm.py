"""Ollama boundary: chat/coding models and token streaming. No ChatOllama/langchain types escape this module."""

from __future__ import annotations

import logging
from typing import Callable

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_ollama import ChatOllama

from program_files.utils.debug_log import truncate
from program_files.utils.errors import ModelUnavailableError
from program_files.utils.tools import ToolSpec

_log = logging.getLogger(__name__)

_MAX_TOOL_ITERATIONS = 4


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

    async def stream_with_tools(
        self,
        prompt: str,
        tools: list[ToolSpec],
        on_token: Callable[[str], None] | None = None,
        on_tool_call: Callable[[str, dict], None] | None = None,
    ) -> str:
        """Run prompt through a tool-calling loop (model decides when to call a tool) and return the final answer.

        Every round streams (tool-call rounds carry no content in practice, so on_token only ever
        fires real text during the final answer) — the caller sees tokens as they're predicted
        instead of waiting for the whole response.
        """
        if not tools:
            return await self.stream(prompt, on_token)

        tool_by_name = {tool.name: tool for tool in tools}
        bound = self._chat.bind_tools([_to_tool_schema(tool) for tool in tools])
        messages: list = [HumanMessage(content=prompt)]

        for _ in range(_MAX_TOOL_ITERATIONS):
            response = await self._stream_round(bound, messages, on_token)
            if not response.tool_calls:
                return response.content
            messages.append(response)
            for call in response.tool_calls:
                if on_tool_call is not None:
                    on_tool_call(call["name"], call["args"])
                spec = tool_by_name.get(call["name"])
                result = await spec.handler(call["args"]) if spec else f"Unknown tool: {call['name']}"
                messages.append(ToolMessage(content=result, tool_call_id=call["id"]))

        messages.append(HumanMessage(content="Answer now, using what you've found so far."))
        response = await self._stream_round(self._chat, messages, on_token)
        return response.content

    async def _stream_round(self, model, messages: list, on_token: Callable[[str], None] | None) -> AIMessage:
        """Stream one model turn, merging chunks (langchain accumulates tool_call_chunks into .tool_calls)."""
        full: AIMessage | None = None
        try:
            async for chunk in model.astream(messages):
                full = chunk if full is None else full + chunk
                if chunk.content and on_token is not None:
                    on_token(chunk.content)
        except Exception as exc:
            _log.error("tool-calling call failed: %s", exc)
            raise ModelUnavailableError(f"Chat model unavailable: {exc}") from exc
        return full

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


def _to_tool_schema(spec: ToolSpec) -> dict:
    return {"type": "function", "function": {"name": spec.name, "description": spec.description, "parameters": spec.parameters}}
