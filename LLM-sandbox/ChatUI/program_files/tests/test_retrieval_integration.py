"""Integration tests against a real local Ollama embedding model.

These hit an actual chromadb.PersistentClient + a running Ollama server (embed_model
must be pulled — see config/models.md). Skipped automatically if Ollama isn't reachable,
since they are not hermetic unit tests.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

pytest.importorskip("langchain_ollama")

import httpx  # noqa: E402

from program_files.models import File  # noqa: E402
from program_files.retrieval import Retriever  # noqa: E402

_EMBED_MODEL = "nomic-embed-text"


def _ollama_available() -> bool:
    try:
        httpx.get("http://localhost:11434/api/tags", timeout=1.0)
        return True
    except httpx.HTTPError:
        return False


pytestmark = pytest.mark.skipif(not _ollama_available(), reason="Ollama not reachable on localhost:11434")


def _file(path: Path, body: str, tags: list[str] | None = None, when: datetime | None = None) -> File:
    ts = when or datetime.now()
    return File(path=path, title=path.stem, body=body, tags=tags or [], links=[], created=ts, updated=ts, last_reviewed=None)


def test_ingest_then_search_finds_relevant_chunk(tmp_path: Path) -> None:
    retriever = Retriever(db_path=tmp_path / "db", embed_model=_EMBED_MODEL)
    files = [
        _file(tmp_path / "Photosynthesis.md", "Photosynthesis converts sunlight into chemical energy in plants.", ["biology"]),
        _file(tmp_path / "Taxonomy.md", "Taxonomy is the science of classification of organisms.", ["taxonomy"]),
    ]

    stats = retriever.ingest(files)

    assert stats.new == 2
    assert stats.updated == 0

    results = retriever.search("How do plants make energy from the sun?", top_k=2)

    assert results
    assert results[0].source_path == files[0].path


def test_ingest_is_incremental_on_second_call(tmp_path: Path) -> None:
    retriever = Retriever(db_path=tmp_path / "db", embed_model=_EMBED_MODEL)
    files = [_file(tmp_path / "A.md", "Some content about ants.", ["biology"])]

    retriever.ingest(files)
    stats = retriever.ingest(files)

    assert stats.new == 0
    assert stats.updated == 0
    assert stats.unchanged == 1


def test_search_scoped_filters_by_tag(tmp_path: Path) -> None:
    retriever = Retriever(db_path=tmp_path / "db", embed_model=_EMBED_MODEL)
    files = [
        _file(tmp_path / "A.md", "Neural networks are a machine learning technique.", ["ai"]),
        _file(tmp_path / "B.md", "Cells are the basic unit of biology.", ["biology"]),
    ]
    retriever.ingest(files)

    results = retriever.search_scoped("networks and cells", tags=["biology"], top_k=5)

    assert results
    assert all("biology" in r.tags for r in results)


def test_reingest_one_updates_a_single_file(tmp_path: Path) -> None:
    retriever = Retriever(db_path=tmp_path / "db", embed_model=_EMBED_MODEL)
    path = tmp_path / "A.md"
    file = _file(path, "Original content about volcanoes.", ["geology"])
    retriever.ingest([file])

    updated_file = _file(path, "Completely different content about oceans.", ["geology"], when=datetime.now())
    retriever.reingest_one(updated_file)

    results = retriever.search("oceans", top_k=1)
    assert results
    assert "oceans" in results[0].text.lower()
