from datetime import datetime
from pathlib import Path

from program_files.utils.models import Chunk, File
from program_files.utils.retrieval import _tag_filter, _to_chunk, _to_document, chunk_file


def _file(body: str, tags: list[str] | None = None) -> File:
    now = datetime.now()
    return File(
        path=Path("/vault/Example.md"),
        title="Example",
        body=body,
        tags=tags or [],
        links=[],
        created=now,
        updated=now,
        last_reviewed=None,
    )


def test_chunk_file_splits_long_body_and_stamps_tags() -> None:
    body = "# Heading\n\n" + ("word " * 400)
    file = _file(body, tags=["ai", "taxonomy"])

    chunks = chunk_file(file, chunk_size=200, overlap=20)

    assert len(chunks) > 1
    assert all(c.source_path == file.path for c in chunks)
    assert all(c.tags == ["ai", "taxonomy"] for c in chunks)


def test_chunk_file_short_body_single_chunk() -> None:
    file = _file("Short body.\n")

    chunks = chunk_file(file, chunk_size=800, overlap=100)

    assert len(chunks) == 1
    assert "Short body." in chunks[0].text


def test_document_chunk_roundtrip() -> None:
    chunk = Chunk(text="hello", source_path=Path("/vault/A.md"), tags=["ai", "biology"], score=0.0)

    doc = _to_document(chunk)
    back = _to_chunk(doc, score=0.82)

    assert doc.metadata["source"] == "/vault/A.md"
    assert doc.metadata["tag_ai"] is True
    assert back.text == "hello"
    assert back.source_path == Path("/vault/A.md")
    assert sorted(back.tags) == ["ai", "biology"]
    assert back.score == 0.82


def test_tag_filter_single_tag() -> None:
    assert _tag_filter(["ai"]) == {"tag_ai": True}


def test_tag_filter_multiple_tags_uses_or() -> None:
    assert _tag_filter(["ai", "biology"]) == {
        "$or": [{"tag_ai": True}, {"tag_biology": True}]
    }
