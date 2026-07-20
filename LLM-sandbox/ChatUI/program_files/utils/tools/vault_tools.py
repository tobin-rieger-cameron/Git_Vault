"""Model-facing tools over the vault: search chunks, read a file's full text."""

from __future__ import annotations

from pathlib import Path

from program_files.utils.errors import VaultFileNotFoundError
from program_files.utils.retrieval import Retriever
from program_files.utils.tools import ToolSpec
from program_files.utils.vault import Vault

_MAX_RESULT_CHARS = 4000


def build_vault_tools(vault: Vault, retriever: Retriever, touched_sources: list[Path]) -> list[ToolSpec]:
    """Build search_vault/read_vault_file, recording every file they touch into touched_sources."""

    async def _search_vault(args: dict) -> str:
        query = str(args.get("query", "")).strip()
        if not query:
            return "query is required"
        top_k = _clamp(int(args.get("top_k") or 5), 1, 10)
        chunks = retriever.search(query, top_k)
        if not chunks:
            return "No matching notes found."
        touched_sources.extend(chunk.source_path for chunk in chunks)
        blocks = [f"[{chunk.source_path.name}] (score {chunk.score:.2f})\n{chunk.text}" for chunk in chunks]
        return _truncate("\n\n---\n\n".join(blocks))

    async def _read_vault_file(args: dict) -> str:
        rel = str(args.get("path", "")).strip()
        if not rel:
            return "path is required"
        candidate = (vault.root / rel).resolve()
        if not candidate.is_relative_to(vault.root.resolve()):
            return "path must be inside the vault"
        try:
            file = vault.load_file(candidate)
        except VaultFileNotFoundError:
            return f"No such file: {rel}"
        touched_sources.append(file.path)
        return _truncate(file.body)

    return [
        ToolSpec(
            name="search_vault",
            description="Search the user's notes by similarity to a query; returns the best-matching passages.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to search for"},
                    "top_k": {"type": "integer", "description": "How many passages to return (default 5)"},
                },
                "required": ["query"],
            },
            handler=_search_vault,
        ),
        ToolSpec(
            name="read_vault_file",
            description="Read one note's full text by its vault-relative path, for more detail than a search snippet gives.",
            parameters={
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Vault-relative path, e.g. 'Formal Notes/Taxonomy.md'"}},
                "required": ["path"],
            },
            handler=_read_vault_file,
        ),
    ]


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def _truncate(text: str, limit: int = _MAX_RESULT_CHARS) -> str:
    return text if len(text) <= limit else text[:limit] + "…"
