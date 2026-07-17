from pathlib import Path

import program_files.utils.feedback as feedback_module
from program_files.utils.feedback import load_recent_overrides, log_override


def _use_scratch_log(monkeypatch, tmp_path: Path) -> Path:
    log_path = tmp_path / "feedback.md"
    monkeypatch.setattr(feedback_module, "_FEEDBACK_PATH", log_path)
    return log_path


def test_log_override_creates_file_with_header(monkeypatch, tmp_path: Path) -> None:
    log_path = _use_scratch_log(monkeypatch, tmp_path)

    log_override("placement", Path("Taxonomy.md"), "misc", "000-information", "should be filed by topic")

    content = log_path.read_text(encoding="utf-8")
    assert content.startswith("---\nsummary:")
    assert "Taxonomy.md (placement)" in content
    assert "Proposed: misc" in content
    assert "Chosen: 000-information" in content
    assert "Reason: should be filed by topic" in content


def test_log_override_defaults_reason_when_missing(monkeypatch, tmp_path: Path) -> None:
    _use_scratch_log(monkeypatch, tmp_path)

    log_override("tags", Path("A.md"), "ai", "ai, ml", None)

    overrides = load_recent_overrides("tags")
    assert overrides[0].reason is None


def test_load_recent_overrides_roundtrips(monkeypatch, tmp_path: Path) -> None:
    _use_scratch_log(monkeypatch, tmp_path)

    log_override("wikilink", Path("A.md"), "[[Old Name]]", "[[New Name]]", "renamed last week")

    overrides = load_recent_overrides("wikilink")

    assert len(overrides) == 1
    o = overrides[0]
    assert o.kind == "wikilink"
    assert o.path == Path("A.md")
    assert o.proposed == "[[Old Name]]"
    assert o.chosen == "[[New Name]]"
    assert o.reason == "renamed last week"


def test_load_recent_overrides_filters_by_kind(monkeypatch, tmp_path: Path) -> None:
    _use_scratch_log(monkeypatch, tmp_path)

    log_override("tags", Path("A.md"), "x", "y", None)
    log_override("placement", Path("B.md"), "x", "y", None)

    assert len(load_recent_overrides("tags")) == 1
    assert len(load_recent_overrides("placement")) == 1
    assert len(load_recent_overrides("nonexistent")) == 0


def test_load_recent_overrides_respects_limit(monkeypatch, tmp_path: Path) -> None:
    _use_scratch_log(monkeypatch, tmp_path)

    for i in range(10):
        log_override("tags", Path(f"{i}.md"), "x", "y", None)

    overrides = load_recent_overrides("tags", limit=3)

    assert len(overrides) == 3
    assert [o.path.stem for o in overrides] == ["7", "8", "9"]


def test_load_recent_overrides_missing_file_returns_empty(monkeypatch, tmp_path: Path) -> None:
    _use_scratch_log(monkeypatch, tmp_path)

    assert load_recent_overrides("tags") == []
