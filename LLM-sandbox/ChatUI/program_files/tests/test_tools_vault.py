from datetime import datetime
from pathlib import Path

import pytest

from program_files.utils.models import Chunk, File
from program_files.utils.tools.vault_tools import build_vault_tools
from program_files.utils.vault import Vault


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class _FakeRetriever:
    def __init__(self, chunks: list[Chunk]) -> None:
        self._chunks = chunks
        self.calls: list[tuple[str, int]] = []

    def search(self, query: str, top_k: int) -> list[Chunk]:
        self.calls.append((query, top_k))
        return self._chunks[:top_k]


def _tools(vault: Vault, retriever, touched: list[Path]):
    by_name = {t.name: t for t in build_vault_tools(vault, retriever, touched)}
    return by_name["search_vault"], by_name["read_vault_file"]


@pytest.mark.asyncio
async def test_search_vault_formats_hits_and_records_touched_sources(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    chunks = [Chunk(text="About taxonomy.", source_path=tmp_path / "Taxonomy.md", tags=[], score=0.9)]
    touched: list[Path] = []
    search_vault, _ = _tools(vault, _FakeRetriever(chunks), touched)

    result = await search_vault.handler({"query": "taxonomy"})

    assert "Taxonomy.md" in result
    assert "About taxonomy." in result
    assert touched == [tmp_path / "Taxonomy.md"]


@pytest.mark.asyncio
async def test_search_vault_no_hits_returns_plain_message() -> None:
    vault = Vault(Path("/unused"))
    touched: list[Path] = []
    search_vault, _ = _tools(vault, _FakeRetriever([]), touched)

    result = await search_vault.handler({"query": "nothing"})

    assert result == "No matching notes found."
    assert touched == []


@pytest.mark.asyncio
async def test_search_vault_requires_a_query() -> None:
    vault = Vault(Path("/unused"))
    search_vault, _ = _tools(vault, _FakeRetriever([]), [])

    result = await search_vault.handler({})

    assert "required" in result


@pytest.mark.asyncio
async def test_read_vault_file_returns_body_and_records_source(tmp_path: Path) -> None:
    _write(tmp_path / "Taxonomy.md", '---\ntitle: "Taxonomy"\n---\n\nBody text.\n')
    vault = Vault(tmp_path)
    touched: list[Path] = []
    _, read_vault_file = _tools(vault, _FakeRetriever([]), touched)

    result = await read_vault_file.handler({"path": "Taxonomy.md"})

    assert result == "Body text.\n"
    assert touched == [tmp_path / "Taxonomy.md"]


@pytest.mark.asyncio
async def test_read_vault_file_missing_file_returns_message_not_raise(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    _, read_vault_file = _tools(vault, _FakeRetriever([]), [])

    result = await read_vault_file.handler({"path": "Nope.md"})

    assert "No such file" in result


@pytest.mark.asyncio
async def test_read_vault_file_rejects_path_traversal(tmp_path: Path) -> None:
    vault = Vault(tmp_path / "vault")
    (tmp_path / "vault").mkdir()
    _write(tmp_path / "secret.md", "outside the vault\n")
    _, read_vault_file = _tools(vault, _FakeRetriever([]), [])

    result = await read_vault_file.handler({"path": "../secret.md"})

    assert "must be inside the vault" in result
