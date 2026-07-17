from datetime import datetime
from pathlib import Path

import pytest

import program_files.classify as classify_module
from program_files.classify import apply_classification, apply_wikilink, suggest_classification, suggest_wikilinks
from program_files.models import ClassificationSuggestion, File
from program_files.vault import Vault


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _file(tmp_path: Path, name: str = "New Paper.md", body: str = "Body about AI.\n", tags: list[str] | None = None) -> File:
    now = datetime.now()
    return File(path=tmp_path / name, title=name[:-3], body=body, tags=tags or [], links=[], created=now, updated=now, last_reviewed=None)


class _FakeModel:
    def __init__(self, responses: dict[str, str]) -> None:
        self._responses = responses
        self.prompts: list[str] = []

    async def ask_coding(self, prompt: str) -> str:
        self.prompts.append(prompt)
        for key, response in self._responses.items():
            if key in prompt:
                return response
        return "misc"


def test_load_tag_folder_map_parses_real_structure_plan() -> None:
    mapping = classify_module._load_tag_folder_map(classify_module._read_structure_plan())

    assert mapping["ai"] == "600-applied-sciences"
    assert mapping["taxonomy"] == "000-information"
    assert "general" not in mapping
    assert "meta" not in mapping


@pytest.mark.asyncio
async def test_suggest_classification_uses_tag_map_before_llm_fallback(tmp_path: Path) -> None:
    file = _file(tmp_path, body="A note about machine learning models.")
    model = _FakeModel({"Suggest 1-4": "ai, machinelearning"})

    suggestion = await suggest_classification(file, model)

    assert suggestion.suggested_tags == ["ai", "machinelearning"]
    assert suggestion.suggested_folder == "600-applied-sciences"
    # folder came from the tag map, not the LLM fallback prompt
    assert not any("classifying a knowledge vault article" in p for p in model.prompts)


@pytest.mark.asyncio
async def test_suggest_classification_falls_back_to_llm_when_tags_unmapped(tmp_path: Path) -> None:
    file = _file(tmp_path, body="A note about something obscure.")
    model = _FakeModel({
        "Suggest 1-4": "general",
        "classifying a knowledge vault article": "500-natural-sciences",
    })

    suggestion = await suggest_classification(file, model)

    assert suggestion.suggested_folder == "500-natural-sciences"


@pytest.mark.asyncio
async def test_suggest_classification_reports_status_for_each_phase(tmp_path: Path) -> None:
    file = _file(tmp_path, body="A note about machine learning models.")
    model = _FakeModel({"Suggest 1-4": "ai, machinelearning"})
    statuses: list[str] = []

    await suggest_classification(file, model, on_status=statuses.append)

    assert statuses == ["suggesting tags…", "choosing a folder…"]


@pytest.mark.asyncio
async def test_suggest_wikilinks_only_returns_candidates_found_in_body(tmp_path: Path) -> None:
    _write(tmp_path / "Taxonomy.md", '---\ntitle: "Taxonomy"\n---\n\nAbout taxonomy.\n')
    file = _file(tmp_path, body="This references taxonomy systems.")
    vault = Vault(tmp_path)
    model = _FakeModel({"suggesting [[wikilinks]]": "Taxonomy, Made Up Note"})

    links, already_linked = await suggest_wikilinks(file, vault, model)

    # "Made Up Note" is dropped (not a real vault title); "Taxonomy" is a real title but the
    # body says "taxonomy" not "Taxonomy systems" — still matches case-insensitively.
    assert links == ["Taxonomy"]
    assert already_linked == []


@pytest.mark.asyncio
async def test_suggest_wikilinks_defers_candidates_not_found_in_body(tmp_path: Path) -> None:
    _write(tmp_path / "Taxonomy.md", '---\ntitle: "Taxonomy"\n---\n\nAbout taxonomy.\n')
    file = _file(tmp_path, body="This note never mentions that topic.")
    vault = Vault(tmp_path)
    model = _FakeModel({"suggesting [[wikilinks]]": "Taxonomy"})

    links, already_linked = await suggest_wikilinks(file, vault, model)

    assert links == []
    assert already_linked == []


@pytest.mark.asyncio
async def test_suggest_wikilinks_reports_status(tmp_path: Path) -> None:
    _write(tmp_path / "Taxonomy.md", '---\ntitle: "Taxonomy"\n---\n\nAbout taxonomy.\n')
    file = _file(tmp_path, body="This references taxonomy.")
    vault = Vault(tmp_path)
    model = _FakeModel({"suggesting [[wikilinks]]": "NONE"})
    statuses: list[str] = []

    await suggest_wikilinks(file, vault, model, on_status=statuses.append)

    assert statuses == [f"searching for wikilinks in {file.path.name}…"]


@pytest.mark.asyncio
async def test_suggest_wikilinks_returns_empty_when_model_says_none(tmp_path: Path) -> None:
    _write(tmp_path / "Taxonomy.md", '---\ntitle: "Taxonomy"\n---\n\nAbout taxonomy.\n')
    file = _file(tmp_path, body="This references taxonomy.")
    vault = Vault(tmp_path)
    model = _FakeModel({"suggesting [[wikilinks]]": "NONE"})

    links, already_linked = await suggest_wikilinks(file, vault, model)

    assert links == []
    assert already_linked == []


@pytest.mark.asyncio
async def test_suggest_wikilinks_reports_already_linked_separately(tmp_path: Path) -> None:
    _write(tmp_path / "Taxonomy.md", '---\ntitle: "Taxonomy"\n---\n\nAbout taxonomy.\n')
    vault = Vault(tmp_path)
    vault.save_file(_file(tmp_path, body="See [[Taxonomy]] for more.\n"))
    file = vault.load_file(tmp_path / "New Paper.md")  # round-trip: populates links from body
    model = _FakeModel({"suggesting [[wikilinks]]": "Taxonomy"})

    links, already_linked = await suggest_wikilinks(file, vault, model)

    assert links == []
    assert already_linked == ["Taxonomy"]


def test_apply_classification_moves_file_and_merges_tags(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    file = _file(tmp_path, tags=["existing"])
    vault.save_file(file)

    suggestion = ClassificationSuggestion(file_path=file.path, suggested_folder="600-applied-sciences", suggested_tags=["ai"])

    updated = apply_classification(file, suggestion, vault)

    assert updated.path == tmp_path / "600-applied-sciences" / "New Paper.md"
    assert not file.path.exists()
    assert updated.path.exists()
    assert updated.tags == ["existing", "ai"]


def test_apply_classification_no_folder_keeps_path(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    file = _file(tmp_path)
    vault.save_file(file)

    suggestion = ClassificationSuggestion(file_path=file.path, suggested_folder=None, suggested_tags=[])

    updated = apply_classification(file, suggestion, vault)

    assert updated.path == file.path


def test_apply_wikilink_wraps_occurrence_inline(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    file = _file(tmp_path, body="This note discusses economics at length.\n")
    vault.save_file(file)

    updated = apply_wikilink(file, "economics", vault)

    assert "[[economics]]" in updated.body
    assert "## See Also" not in updated.body
    assert updated.links == ["economics"]


def test_apply_wikilink_preserves_canonical_title_casing(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    file = _file(tmp_path, body="This note discusses economics at length.\n")
    vault.save_file(file)

    updated = apply_wikilink(file, "Economics", vault)

    assert "[[Economics]]" in updated.body
    assert "economics at length" not in updated.body


def test_apply_wikilink_no_occurrence_leaves_body_unchanged(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    file = _file(tmp_path, body="Nothing relevant here.\n")
    vault.save_file(file)

    updated = apply_wikilink(file, "Taxonomy", vault)

    assert updated.body == file.body
