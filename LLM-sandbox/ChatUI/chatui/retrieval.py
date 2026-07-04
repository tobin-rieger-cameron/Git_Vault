"""ChromaDB boundary: chunking, ingest, and similarity search. No chromadb types escape this module."""

from __future__ import annotations

from pathlib import Path

from chatui.models import Chunk, IngestStats, Paper


class Retriever:
    def __init__(self, db_path: Path, embed_model: str) -> None:
        raise NotImplementedError

    def search(self, query: str, top_k: int) -> list[Chunk]:
        """Raises RetrievalError on a chromadb query failure."""
        raise NotImplementedError

    def search_scoped(self, query: str, tags: list[str], top_k: int) -> list[Chunk]:
        raise NotImplementedError

    def ingest(self, papers: list[Paper], force: bool = False) -> IngestStats:
        """Raises IngestError on a chromadb write failure."""
        raise NotImplementedError

    def reingest_one(self, paper: Paper) -> None:
        raise NotImplementedError


def chunk_paper(paper: Paper, chunk_size: int, overlap: int) -> list[Chunk]:
    raise NotImplementedError
