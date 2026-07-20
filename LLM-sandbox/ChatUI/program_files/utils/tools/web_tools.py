"""Model-facing tool for supplementing vault context with a live web search."""

from __future__ import annotations

from program_files.utils.tools import ToolSpec
from program_files.utils.web import search_web

_MAX_RESULT_CHARS = 4000


def build_web_tools(max_results: int) -> list[ToolSpec]:
    """Build the web_search tool; caller only includes this in a toolbox when /web is on."""

    async def _web_search(args: dict) -> str:
        query = str(args.get("query", "")).strip()
        if not query:
            return "query is required"
        results = search_web(query, max_results)
        if not results:
            return "No web results found."
        blocks = [f"Source: {r.url}\nTitle: {r.title}\n{r.snippet}" for r in results]
        text = "\n\n---\n\n".join(blocks)
        return text if len(text) <= _MAX_RESULT_CHARS else text[:_MAX_RESULT_CHARS] + "…"

    return [
        ToolSpec(
            name="web_search",
            description="Search the web for current information not likely to be in training data or the vault.",
            parameters={
                "type": "object",
                "properties": {"query": {"type": "string", "description": "What to search for"}},
                "required": ["query"],
            },
            handler=_web_search,
        )
    ]
