from datetime import datetime
from pathlib import Path

import pytest

import chatui.classify as classify_module
from chatui.classify import apply_classification, suggest_classification
from chatui.models import ClassificationSuggestion, File
from chatui.vault import Vault


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
    vault = Vault(tmp_path)
    model = _FakeModel({"Suggest 1-4": "ai, machinelearning"})

    suggestion = await suggest_classification(file, vault, model)

    assert suggestion.suggested_tags == ["ai", "machinelearning"]
    assert suggestion.suggested_folder == "600-applied-sciences"
    # folder came from the tag map, not the LLM fallback prompt
    assert not any("classifying a knowledge vault article" in p for p in model.prompts)


@pytest.mark.asyncio
async def test_suggest_classification_falls_back_to_llm_when_tags_unmapped(tmp_path: Path) -> None:
    file = _file(tmp_path, body="A note about something obscure.")
    vault = Vault(tmp_path)
    model = _FakeModel({
        "Suggest 1-4": "general",
        "classifying a knowledge vault article": "500-natural-sciences",
    })

    suggestion = await suggest_classification(file, vault, model)

    assert suggestion.suggested_folder == "500-natural-sciences"


@pytest.mark.asyncio
async def test_suggest_links_only_returns_real_candidate_titles(tmp_path: Path) -> None:
    _write(tmp_path / "Taxonomy.md", '---\ntitle: "Taxonomy"\n---\n\nAbout taxonomy.\n')
    file = _file(tmp_path, body="This references classification systems.")
    vault = Vault(tmp_path)
    model = _FakeModel({
        "Suggest 1-4": "classification",
        "suggesting [[wikilinks]]": "Taxonomy, Made Up Note",
    })

    suggestion = await suggest_classification(file, vault, model)

    assert suggestion.suggested_links == ["Taxonomy"]


@pytest.mark.asyncio
async def test_suggest_links_returns_empty_when_model_says_none(tmp_path: Path) -> None:
    _write(tmp_path / "Taxonomy.md", '---\ntitle: "Taxonomy"\n---\n\nAbout taxonomy.\n')
    file = _file(tmp_path)
    vault = Vault(tmp_path)
    model = _FakeModel({"Suggest 1-4": "ai", "suggesting [[wikilinks]]": "NONE"})

    suggestion = await suggest_classification(file, vault, model)

    assert suggestion.suggested_links == []


def test_apply_classification_moves_file_and_merges_tags(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    file = _file(tmp_path, tags=["existing"])
    vault.save_file(file)

    suggestion = ClassificationSuggestion(
        file_path=file.path, suggested_folder="600-applied-sciences", suggested_tags=["ai"], suggested_links=[]
    )

    updated = apply_classification(file, suggestion, vault)

    assert updated.path == tmp_path / "600-applied-sciences" / "New Paper.md"
    assert not file.path.exists()
    assert updated.path.exists()
    assert updated.tags == ["existing", "ai"]


def test_apply_classification_appends_see_also_section(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    file = _file(tmp_path, body="Some content.\n")
    vault.save_file(file)

    suggestion = ClassificationSuggestion(
        file_path=file.path, suggested_folder=None, suggested_tags=[], suggested_links=["Taxonomy", "Dewey Decimal System"]
    )

    updated = apply_classification(file, suggestion, vault)

    assert "[[Taxonomy]]" in updated.body
    assert "[[Dewey Decimal System]]" in updated.body
    assert sorted(updated.links) == ["Dewey Decimal System", "Taxonomy"]


def test_apply_classification_does_not_duplicate_existing_links(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    file = _file(tmp_path, body="See [[Taxonomy]] for more.\n")
    vault.save_file(file)

    suggestion = ClassificationSuggestion(
        file_path=file.path, suggested_folder=None, suggested_tags=[], suggested_links=["Taxonomy"]
    )

    updated = apply_classification(file, suggestion, vault)

    assert "## See Also" not in updated.body


def test_apply_classification_no_folder_keeps_path(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    file = _file(tmp_path)
    vault.save_file(file)

    suggestion = ClassificationSuggestion(file_path=file.path, suggested_folder=None, suggested_tags=[], suggested_links=[])

    updated = apply_classification(file, suggestion, vault)

    assert updated.path == file.path
