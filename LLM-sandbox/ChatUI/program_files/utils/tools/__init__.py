"""Tool registry: every capability (vault search, web search, draft/classify/review) is a ToolSpec."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Awaitable, Callable

if TYPE_CHECKING:
    from program_files.utils.config import Settings
    from program_files.utils.llm import ModelClient
    from program_files.utils.retrieval import Retriever
    from program_files.utils.vault import Vault


@dataclass
class ToolSpec:
    """A named capability: description/parameters document it; handler executes it.

    Model-facing tools (search_vault, read_vault_file, web_search) are called by an agent loop
    mid-conversation and their handlers return plain str for the model to read back. Command-facing
    tools (draft_note, classify_note, ...) are called directly by app.py when a slash command fires
    and their handlers return whatever typed object the UI needs (File, ClassificationSuggestion, ...).
    """

    name: str
    description: str
    parameters: dict
    handler: Callable[[dict], Awaitable[Any]]


class ToolRegistry:
    """A name -> ToolSpec catalog, built once at startup and shared by the agent loop and app.py."""

    def __init__(self, tools: list[ToolSpec]) -> None:
        self._by_name = {tool.name: tool for tool in tools}

    def get(self, name: str) -> ToolSpec:
        try:
            return self._by_name[name]
        except KeyError:
            raise KeyError(f"No such tool: {name}") from None

    def subset(self, names: list[str]) -> list[ToolSpec]:
        """Return the named tools, in the given order — for handing a model-facing slice to agent.run()."""
        return [self.get(name) for name in names]

    def all(self) -> list[ToolSpec]:
        return list(self._by_name.values())


def build_registry(vault: Vault, retriever: Retriever, model: ModelClient, settings: Settings) -> ToolRegistry:
    """Build every command tool app.py dispatches to, wired to the app's Vault/Retriever/ModelClient/Settings.

    search_vault/read_vault_file/web_search aren't registered here — they're model-facing tools
    answer_question builds fresh per call (each run needs its own touched_sources list), not
    something app.py ever looks up by name.
    """
    # Imported here, not at module top, so ToolSpec/ToolRegistry exist before these submodules
    # (which import ToolSpec back from this package) get loaded.
    from program_files.utils.tools.ask_tools import build_ask_tools
    from program_files.utils.tools.classify_tools import build_classify_tools
    from program_files.utils.tools.draft_tools import build_draft_tools
    from program_files.utils.tools.review_tools import build_review_tools

    tools = [
        *build_ask_tools(vault, retriever, model, settings.web_search_results),
        *build_draft_tools(vault, model),
        *build_classify_tools(vault, model, retriever),
        *build_review_tools(model),
    ]
    return ToolRegistry(tools)
