from datetime import datetime
from pathlib import Path

import pytest

from chatui.errors import VaultFileNotFoundError
from chatui.models import File
from chatui.vault import (
    Vault,
    extract_wikilinks,
    find_wikilinks,
    normalize_link_target,
    parse_frontmatter,
    render_frontmatter,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_parse_frontmatter_splits_meta_and_body() -> None:
    content = '---\ntitle: "Taxonomy"\ntags: [taxonomy, ai]\n---\n\nBody text here.\n'

    meta, body = parse_frontmatter(content)

    assert meta == {"title": "Taxonomy", "tags": ["taxonomy", "ai"]}
    assert body == "Body text here.\n"


def test_parse_frontmatter_no_frontmatter_returns_empty_meta() -> None:
    meta, body = parse_frontmatter("Just a plain file.\n")

    assert meta == {}
    assert body == "Just a plain file.\n"


def test_render_frontmatter_roundtrips_through_parse() -> None:
    rendered = render_frontmatter({"title": "Foo", "tags": ["bar"]}, "Body.\n")
    meta, body = parse_frontmatter(rendered)

    assert meta == {"title": "Foo", "tags": ["bar"]}
    assert body == "Body.\n"


def test_render_frontmatter_drops_empty_values() -> None:
    rendered = render_frontmatter({"title": "Foo", "tags": []}, "Body.\n")

    assert "tags" not in rendered


def test_render_frontmatter_no_meta_returns_body_only() -> None:
    assert render_frontmatter({}, "Body.\n") == "Body.\n"


def test_extract_wikilinks_handles_aliases() -> None:
    body = "See [[Dewey Decimal System|Dewey Decimal Classification]] and [[Taxonomy]]."

    assert extract_wikilinks(body) == ["Dewey Decimal System", "Taxonomy"]


def test_normalize_link_target_collapses_separators() -> None:
    assert normalize_link_target("fine-tuning_methods") == "fine tuning methods"
    assert normalize_link_target("Taxonomy") == "taxonomy"


def test_find_wikilinks_returns_spans_covering_the_full_match() -> None:
    body = "See [[Taxonomy]] and [[Dewey Decimal System|DDS]] for more."

    spans = find_wikilinks(body)

    assert [target for _, _, target in spans] == ["Taxonomy", "Dewey Decimal System"]
    for start, end, _target in spans:
        assert body[start:end].startswith("[[")
        assert body[start:end].endswith("]]")


def test_vault_list_files_excludes_conversations(tmp_path: Path) -> None:
    _write(tmp_path / "000-information" / "Taxonomy.md", '---\ntitle: "Taxonomy"\ntags: [taxonomy]\n---\n\nBody.\n')
    _write(tmp_path / "conversations" / "2026-07-04.md", "excluded\n")

    vault = Vault(tmp_path)
    files = vault.list_files()

    assert len(files) == 1
    assert files[0].title == "Taxonomy"
    assert files[0].tags == ["taxonomy"]


def test_vault_load_file_missing_raises(tmp_path: Path) -> None:
    vault = Vault(tmp_path)

    with pytest.raises(VaultFileNotFoundError):
        vault.load_file(tmp_path / "nope.md")


def test_vault_load_file_falls_back_to_stem_title(tmp_path: Path) -> None:
    _write(tmp_path / "Cupcakes.md", "No frontmatter here.\n")

    vault = Vault(tmp_path)
    file = vault.load_file(tmp_path / "Cupcakes.md")

    assert file.title == "Cupcakes"
    assert file.tags == []
    assert file.last_reviewed is None


def test_vault_save_file_then_load_file_roundtrips(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    path = tmp_path / "600-applied-sciences" / "New Paper.md"
    file = File(
        path=path,
        title="New Paper",
        body="Some content.\n",
        tags=["ai"],
        links=[],
        created=datetime.now(),
        updated=datetime.now(),
        last_reviewed=None,
    )

    vault.save_file(file)
    loaded = vault.load_file(path)

    assert loaded.title == "New Paper"
    assert loaded.tags == ["ai"]
    assert loaded.body == "Some content.\n"


def test_vault_find_by_tag(tmp_path: Path) -> None:
    _write(tmp_path / "A.md", "---\ntitle: A\ntags: [ai]\n---\n\nBody.\n")
    _write(tmp_path / "B.md", "---\ntitle: B\ntags: [biology]\n---\n\nBody.\n")

    vault = Vault(tmp_path)

    assert [f.title for f in vault.find_by_tag("ai")] == ["A"]


def test_vault_needs_placement_root_and_misc(tmp_path: Path) -> None:
    vault = Vault(tmp_path)

    assert vault.needs_placement(tmp_path / "Root File.md") is True
    assert vault.needs_placement(tmp_path / "misc" / "Cupcakes.md") is True
    assert vault.needs_placement(tmp_path / "600-applied-sciences" / "AI.md") is False
