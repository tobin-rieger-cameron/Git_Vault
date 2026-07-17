"""ChromaDB boundary: chunking, ingest, and similarity search. No chromadb types escape this module."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import chromadb
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from program_files.errors import IngestError, RetrievalError
from program_files.models import Chunk, File, IngestStats

_log = logging.getLogger(__name__)

_COLLECTION_NAME = "vault"
_MD_HEADERS = [("#", "h1"), ("##", "h2"), ("###", "h3")]


class Retriever:
    """Owns the ChromaDB collection: incremental ingest plus similarity search over it."""

    def __init__(
        self,
        db_path: Path,
        embed_model: str,
        chunk_size: int = 800,
        chunk_overlap: int = 100,
    ) -> None:
        self._db_path = db_path
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._embeddings = OllamaEmbeddings(model=embed_model)
        self._client = chromadb.PersistentClient(path=str(db_path))
        self._db = self._open_collection()

    def search(self, query: str, top_k: int) -> list[Chunk]:
        """Run a similarity search over the whole vault collection."""
        try:
            results = self._db.similarity_search_with_relevance_scores(query, k=top_k)
        except Exception as exc:
            _log.error("vault search failed for %r: %s", query, exc)
            raise RetrievalError(f"Vault search failed: {exc}") from exc
        chunks = [_to_chunk(doc, score) for doc, score in results]
        _log.debug("search %r top_k=%s -> %s", query, top_k, [(str(c.source_path), round(c.score, 3)) for c in chunks])
        return chunks

    def search_scoped(self, query: str, tags: list[str], top_k: int) -> list[Chunk]:
        """Run a similarity search restricted to chunks carrying any one of tags (OR, not AND)."""
        try:
            results = self._db.similarity_search_with_relevance_scores(
                query, k=top_k, filter=_tag_filter(tags)
            )
        except Exception as exc:
            _log.error("scoped vault search failed for %r tags=%s: %s", query, tags, exc)
            raise RetrievalError(f"Scoped vault search failed: {exc}") from exc
        chunks = [_to_chunk(doc, score) for doc, score in results]
        _log.debug(
            "scoped search %r tags=%s top_k=%s -> %s",
            query, tags, top_k, [(str(c.source_path), round(c.score, 3)) for c in chunks],
        )
        return chunks

    def ingest(self, files: list[File], force: bool = False) -> IngestStats:
        """Re-embed only new/changed files against a path→mtime manifest; force wipes and rebuilds."""
        if force:
            self._reset_collection()
            manifest: dict[str, float] = {}
        else:
            manifest = _load_manifest(self._db_path)

        current_by_path = {str(f.path): f for f in files}
        current_paths = set(current_by_path)
        manifest_paths = set(manifest)

        new_paths = current_paths - manifest_paths
        changed_paths = {
            p
            for p in current_paths & manifest_paths
            if current_by_path[p].updated.timestamp() > manifest[p]
        }
        removed_paths = manifest_paths - current_paths
        unchanged = len(current_paths) - len(new_paths) - len(changed_paths)

        try:
            for path in changed_paths | removed_paths:
                self._db._collection.delete(where={"source": path})

            to_embed = [current_by_path[p] for p in new_paths | changed_paths]
            chunks = [
                chunk
                for file in to_embed
                for chunk in chunk_file(file, self._chunk_size, self._chunk_overlap)
            ]
            if chunks:
                self._db.add_documents([_to_document(c) for c in chunks])
        except Exception as exc:
            raise IngestError(f"Ingest failed: {exc}") from exc

        _save_manifest(self._db_path, {str(f.path): f.updated.timestamp() for f in files})
        stats = IngestStats(
            new=len(new_paths),
            updated=len(changed_paths),
            removed=len(removed_paths),
            unchanged=unchanged,
        )
        _log.info("ingest force=%s -> %s", force, stats)
        return stats

    def reingest_one(self, file: File) -> None:
        """Re-embed a single file immediately, bypassing the batch ingest() diff."""
        path = str(file.path)
        try:
            self._db._collection.delete(where={"source": path})
            chunks = chunk_file(file, self._chunk_size, self._chunk_overlap)
            if chunks:
                self._db.add_documents([_to_document(c) for c in chunks])
        except Exception as exc:
            raise IngestError(f"Failed to reingest {path}: {exc}") from exc

        manifest = _load_manifest(self._db_path)
        manifest[path] = file.updated.timestamp()
        _save_manifest(self._db_path, manifest)

    def _open_collection(self) -> Chroma:
        return Chroma(
            embedding_function=self._embeddings,
            client=self._client,
            collection_name=_COLLECTION_NAME,
        )

    def _reset_collection(self) -> None:
        try:
            self._client.delete_collection(_COLLECTION_NAME)
        except Exception:
            pass  # first run: collection doesn't exist yet
        self._db = self._open_collection()


def chunk_file(file: File, chunk_size: int, overlap: int) -> list[Chunk]:
    """Split on Markdown headers first, then re-split any oversized section by character count."""
    header_splits = _split_on_headers(file.body)
    char_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=overlap)
    return [
        Chunk(text=doc.page_content, source_path=file.path, tags=list(file.tags), score=0.0)
        for doc in char_splitter.split_documents(header_splits)
    ]


def _split_on_headers(body: str) -> list[Document]:
    splitter = MarkdownHeaderTextSplitter(headers_to_split_on=_MD_HEADERS, strip_headers=False)
    try:
        return splitter.split_text(body)
    except Exception:
        return [Document(page_content=body)]  # malformed headers: fall back to one unsplit document


def _to_document(chunk: Chunk) -> Document:
    # Chroma metadata values must be scalar, so tags are encoded as one bool-valued key per tag.
    metadata = {"source": str(chunk.source_path)}
    metadata.update({f"tag_{tag}": True for tag in chunk.tags})
    return Document(page_content=chunk.text, metadata=metadata)


def _to_chunk(doc: Document, score: float) -> Chunk:
    tags = [key[4:] for key, value in doc.metadata.items() if key.startswith("tag_") and value is True]
    return Chunk(text=doc.page_content, source_path=Path(doc.metadata.get("source", "")), tags=tags, score=score)


def _tag_filter(tags: list[str]) -> dict:
    if len(tags) == 1:
        return {f"tag_{tags[0]}": True}
    return {"$or": [{f"tag_{tag}": True} for tag in tags]}


def _manifest_path(db_path: Path) -> Path:
    return db_path / "manifest.json"


def _load_manifest(db_path: Path) -> dict[str, float]:
    try:
        return json.loads(_manifest_path(db_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_manifest(db_path: Path, manifest: dict[str, float]) -> None:
    db_path.mkdir(parents=True, exist_ok=True)
    _manifest_path(db_path).write_text(json.dumps(manifest), encoding="utf-8")
