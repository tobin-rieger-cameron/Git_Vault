from datetime import datetime
from pathlib import Path

import pytest

from program_files.utils.tools import classify_tools
from program_files.utils.tools.classify_tools import (
    apply_classification,
    apply_folder_tags,
    apply_see_also,
    apply_wikilink,
    suggest_classification,
    suggest_folder_tags,
    suggest_wikilinks,
)
from program_files.utils.models import ClassificationSuggestion, Chunk, File, FolderTagChange
from program_files.utils.vault import Vault


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


class _FakeRetriever:
    """Stands in for Retriever.search — synchronous, like the real thing (classify_tools backgrounds it)."""

    def __init__(self, hits: list[Chunk]) -> None:
        self._hits = hits
        self.queries: list[tuple[str, int, Path | None]] = []

    def search(self, query: str, top_k: int, exclude_source: Path | None = None) -> list[Chunk]:
        self.queries.append((query, top_k, exclude_source))
        return [c for c in self._hits if c.source_path != exclude_source][:top_k]


def test_load_tag_folder_map_parses_real_structure_plan() -> None:
    mapping = classify_tools._load_tag_folder_map(classify_tools._read_structure_plan())

    assert mapping["ai"] == "300-formal-applied-sciences"
    assert mapping["taxonomy"] == "000-information-theory"
    assert "general" not in mapping
    assert "meta" not in mapping


@pytest.mark.asyncio
async def test_suggest_classification_uses_tag_map_before_llm_fallback(tmp_path: Path) -> None:
    file = _file(tmp_path, body="A note about machine learning models.")
    model = _FakeModel({"Suggest 1-4": "ai, machinelearning"})
    vault = Vault(tmp_path)

    suggestion = await suggest_classification(file, vault, model)

    assert suggestion.suggested_tags == ["ai", "machinelearning"]
    assert suggestion.suggested_folder == "300-formal-applied-sciences"
    # folder came from the tag map, not the LLM fallback prompt
    assert not any("classifying an article into a folder" in p for p in model.prompts)


@pytest.mark.asyncio
async def test_suggest_classification_falls_back_to_llm_when_tags_unmapped(tmp_path: Path) -> None:
    file = _file(tmp_path, body="A note about something obscure.")
    model = _FakeModel({
        "Suggest 1-4": "general",
        "classifying an article into a folder": "400-social-natural-sciences",
    })
    vault = Vault(tmp_path)

    suggestion = await suggest_classification(file, vault, model)

    assert suggestion.suggested_folder == "400-social-natural-sciences"


@pytest.mark.asyncio
async def test_suggest_classification_reports_status_for_each_phase(tmp_path: Path) -> None:
    file = _file(tmp_path, body="A note about machine learning models.")
    model = _FakeModel({"Suggest 1-4": "ai, machinelearning"})
    vault = Vault(tmp_path)
    statuses: list[str] = []

    await suggest_classification(file, vault, model, on_status=statuses.append)

    assert statuses == ["suggesting tags…", "choosing a folder…"]


@pytest.mark.asyncio
async def test_suggest_classification_merges_folder_derived_tags_with_llm_tags(tmp_path: Path) -> None:
    file = _file(tmp_path / "000 - Information Science", body="A note about ontologies.")
    model = _FakeModel({"Suggest 1-4": "ontology"})
    vault = Vault(tmp_path)

    suggestion = await suggest_classification(file, vault, model)

    # folder tag comes first, deterministically, alongside whatever the LLM proposed for content.
    assert suggestion.suggested_tags == ["information-science", "ontology"]


@pytest.mark.asyncio
async def test_suggest_classification_skips_folder_tag_already_on_file(tmp_path: Path) -> None:
    file = _file(tmp_path / "000 - Information Science", body="More.", tags=["Information-Science"])
    model = _FakeModel({"Suggest 1-4": "ontology"})
    vault = Vault(tmp_path)

    suggestion = await suggest_classification(file, vault, model)

    assert suggestion.suggested_tags == ["ontology"]


@pytest.mark.asyncio
async def test_suggest_wikilinks_inline_tier_needs_no_model_call(tmp_path: Path) -> None:
    _write(tmp_path / "Taxonomy.md", '---\ntitle: "Taxonomy"\n---\n\nAbout taxonomy.\n')
    file = _file(tmp_path, body="This references taxonomy systems.")
    vault = Vault(tmp_path)
    retriever = _FakeRetriever([])

    suggestion = await suggest_wikilinks(file, vault, retriever, top_k=5, similarity_threshold=0.65)

    # body says "taxonomy" not "Taxonomy" — word-boundary match is still case-insensitive.
    assert suggestion.inline_new == ["Taxonomy"]
    assert suggestion.already_linked == []


@pytest.mark.asyncio
async def test_suggest_wikilinks_inline_tier_is_word_boundary_not_substring(tmp_path: Path) -> None:
    _write(tmp_path / "AI.md", '---\ntitle: "AI"\n---\n\nAbout AI.\n')
    file = _file(tmp_path, body="We met again yesterday and said it again.")
    vault = Vault(tmp_path)
    retriever = _FakeRetriever([])

    suggestion = await suggest_wikilinks(file, vault, retriever, top_k=5, similarity_threshold=0.65)

    # "AI" must not match inside "again" — a plain substring check would wrongly propose it.
    assert suggestion.inline_new == []


@pytest.mark.asyncio
async def test_suggest_wikilinks_reports_already_linked_separately(tmp_path: Path) -> None:
    _write(tmp_path / "Taxonomy.md", '---\ntitle: "Taxonomy"\n---\n\nAbout taxonomy.\n')
    vault = Vault(tmp_path)
    vault.save_file(_file(tmp_path, body="See [[Taxonomy]] for more.\n"))
    file = vault.load_file(tmp_path / "New Paper.md")  # round-trip: populates links from body
    retriever = _FakeRetriever([])

    suggestion = await suggest_wikilinks(file, vault, retriever, top_k=5, similarity_threshold=0.65)

    assert suggestion.inline_new == []
    assert suggestion.already_linked == ["Taxonomy"]


@pytest.mark.asyncio
async def test_suggest_wikilinks_see_also_tier_uses_vector_search_not_text_match(tmp_path: Path) -> None:
    _write(tmp_path / "Ontology.md", '---\ntitle: "Ontology"\n---\n\nAbout ontologies.\n')
    file = _file(tmp_path, body="This note never spells out that other topic's name.")
    vault = Vault(tmp_path)
    retriever = _FakeRetriever(
        [Chunk(text="...", source_path=tmp_path / "Ontology.md", tags=[], score=0.8)]
    )

    suggestion = await suggest_wikilinks(file, vault, retriever, top_k=5, similarity_threshold=0.65)

    assert suggestion.inline_new == []
    assert suggestion.see_also_new == ["Ontology"]
    assert retriever.queries == [(file.body[:2000], 5, file.path)]


@pytest.mark.asyncio
async def test_suggest_wikilinks_see_also_excludes_the_file_own_chunks(tmp_path: Path) -> None:
    # Regression: a query built from a file's own body matches that file's own chunks best of
    # all, so without excluding them at the query level they fill the whole top_k window and
    # leave no room for any other file to ever be suggested.
    _write(tmp_path / "Ontology.md", '---\ntitle: "Ontology"\n---\n\nAbout ontologies.\n')
    file = _file(tmp_path, body="Unrelated content.")
    vault = Vault(tmp_path)
    retriever = _FakeRetriever(
        [
            Chunk(text="...", source_path=file.path, tags=[], score=0.99),
            Chunk(text="...", source_path=file.path, tags=[], score=0.95),
            Chunk(text="...", source_path=tmp_path / "Ontology.md", tags=[], score=0.8),
        ]
    )

    suggestion = await suggest_wikilinks(file, vault, retriever, top_k=2, similarity_threshold=0.65)

    assert suggestion.see_also_new == ["Ontology"]


@pytest.mark.asyncio
async def test_suggest_wikilinks_see_also_tier_drops_hits_below_threshold(tmp_path: Path) -> None:
    _write(tmp_path / "Ontology.md", '---\ntitle: "Ontology"\n---\n\nAbout ontologies.\n')
    file = _file(tmp_path, body="Unrelated content.")
    vault = Vault(tmp_path)
    retriever = _FakeRetriever(
        [Chunk(text="...", source_path=tmp_path / "Ontology.md", tags=[], score=0.4)]
    )

    suggestion = await suggest_wikilinks(file, vault, retriever, top_k=5, similarity_threshold=0.65)

    assert suggestion.see_also_new == []


@pytest.mark.asyncio
async def test_suggest_wikilinks_see_also_tier_excludes_inline_and_already_linked(tmp_path: Path) -> None:
    _write(tmp_path / "Taxonomy.md", '---\ntitle: "Taxonomy"\n---\n\nAbout taxonomy.\n')
    _write(tmp_path / "Ontology.md", '---\ntitle: "Ontology"\n---\n\nAbout ontologies.\n')
    vault = Vault(tmp_path)
    vault.save_file(_file(tmp_path, body="See [[Ontology]]. Also mentions taxonomy directly.\n"))
    file = vault.load_file(tmp_path / "New Paper.md")
    retriever = _FakeRetriever(
        [
            Chunk(text="...", source_path=tmp_path / "Taxonomy.md", tags=[], score=0.9),
            Chunk(text="...", source_path=tmp_path / "Ontology.md", tags=[], score=0.9),
        ]
    )

    suggestion = await suggest_wikilinks(file, vault, retriever, top_k=5, similarity_threshold=0.65)

    # Taxonomy is text-matched -> inline tier, not see-also; Ontology is already a real wikilink.
    assert suggestion.inline_new == ["Taxonomy"]
    assert suggestion.already_linked == ["Ontology"]
    assert suggestion.see_also_new == []


@pytest.mark.asyncio
async def test_suggest_wikilinks_no_candidates_skips_retriever_entirely(tmp_path: Path) -> None:
    file = _file(tmp_path, body="Nothing else in this vault.")
    vault = Vault(tmp_path)
    retriever = _FakeRetriever([])

    suggestion = await suggest_wikilinks(file, vault, retriever, top_k=5, similarity_threshold=0.65)

    assert suggestion.inline_new == []
    assert suggestion.see_also_new == []
    assert retriever.queries == []


@pytest.mark.asyncio
async def test_suggest_wikilinks_reports_status(tmp_path: Path) -> None:
    file = _file(tmp_path, body="This references taxonomy.")
    vault = Vault(tmp_path)
    retriever = _FakeRetriever([])
    statuses: list[str] = []

    await suggest_wikilinks(file, vault, retriever, top_k=5, similarity_threshold=0.65, on_status=statuses.append)

    assert statuses == [f"searching for wikilinks in {file.path.name}…"]


def test_apply_see_also_creates_section_when_absent(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    file = _file(tmp_path, body="Some content.\n")
    vault.save_file(file)

    updated = apply_see_also(file, ["Ontology", "Taxonomy"], vault)

    assert "## See also" in updated.body
    assert "* [[Ontology]]" in updated.body
    assert "* [[Taxonomy]]" in updated.body
    assert updated.links == ["Ontology", "Taxonomy"]


def test_apply_see_also_appends_to_existing_section(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    file = _file(tmp_path, body="Some content.\n\n## See also\n* [[Ontology]]\n\n## References\nFoo.\n")
    vault.save_file(file)

    updated = apply_see_also(file, ["Taxonomy"], vault)

    assert "* [[Ontology]]" in updated.body
    assert "* [[Taxonomy]]" in updated.body
    # the new bullet lands in the See also section, before References, not appended at the end
    assert updated.body.index("[[Taxonomy]]") < updated.body.index("## References")


def test_apply_see_also_skips_titles_already_linked(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    file = _file(tmp_path, body="See [[Ontology]] already.\n")
    vault.save_file(file)

    updated = apply_see_also(file, ["Ontology"], vault)

    assert updated.body.count("[[Ontology]]") == 1


def test_apply_see_also_no_new_titles_leaves_file_unchanged(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    file = _file(tmp_path, body="See [[Ontology]] already.\n")
    vault.save_file(file)

    updated = apply_see_also(file, ["Ontology"], vault)

    assert updated is file


def test_suggest_folder_tags_walks_nested_ancestors(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    vault.save_file(_file(tmp_path / "000 - Information Science" / "Ontology", name="Ontology.md"))
    vault.save_file(_file(tmp_path / "000 - Information Science", name="Taxonomy.md", tags=["information-science"]))

    plan = suggest_folder_tags(tmp_path / "000 - Information Science", vault)

    nested = tmp_path / "000 - Information Science" / "Ontology" / "Ontology.md"
    direct = tmp_path / "000 - Information Science" / "Taxonomy.md"
    assert plan[nested].add == ["ontology", "information-science"]
    assert plan[nested].remove == []
    assert direct not in plan  # already carries the only tag it's missing, nothing to remove either


def test_suggest_folder_tags_matches_existing_tag_case_insensitively(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    vault.save_file(_file(tmp_path / "000 - Information Science", name="Taxonomy.md", tags=["Information-Science"]))

    plan = suggest_folder_tags(tmp_path / "000 - Information Science", vault)

    assert tmp_path / "000 - Information Science" / "Taxonomy.md" not in plan


def test_suggest_folder_tags_ignores_files_outside_the_folder(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    vault.save_file(_file(tmp_path / "600-fine-arts", name="Music.md"))

    plan = suggest_folder_tags(tmp_path / "000 - Information Science", vault)

    assert plan == {}


def test_suggest_folder_tags_removes_stale_tag_from_a_moved_folder(tmp_path: Path) -> None:
    # A file that used to sit under a "Study Notes" folder (so it picked up a "study-notes" tag)
    # has since been moved to a differently-named folder elsewhere in the vault; "study-notes" is
    # still a real folder name somewhere in the vault, so it must be swept up as stale rather than
    # kept as if it were a genuine cross-referencing topic tag.
    vault = Vault(tmp_path)
    vault.save_file(_file(tmp_path / "Study Notes" / "Other", name="Keep.md"))
    vault.save_file(
        _file(tmp_path / "OLD_STRUCTURE", name="Moved.md", tags=["study-notes", "own-thoughts"])
    )

    plan = suggest_folder_tags(tmp_path / "OLD_STRUCTURE", vault)

    moved = tmp_path / "OLD_STRUCTURE" / "Moved.md"
    assert plan[moved].add == ["old-structure"]
    assert plan[moved].remove == ["study-notes"]  # "own-thoughts" isn't a real folder name anywhere, kept


def test_suggest_folder_tags_keeps_topic_tag_that_never_matched_a_folder(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    vault.save_file(_file(tmp_path / "000 - Information Science", name="Note.md", tags=["philosophy"]))

    plan = suggest_folder_tags(tmp_path / "000 - Information Science", vault)

    note = tmp_path / "000 - Information Science" / "Note.md"
    assert plan[note].add == ["information-science"]
    assert plan[note].remove == []  # "philosophy" never named a folder anywhere in this vault


def test_apply_folder_tags_adds_and_removes_then_persists(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    file = _file(tmp_path / "000 - Information Science", name="Ontology.md", tags=["existing", "stale"])
    vault.save_file(file)

    updated = apply_folder_tags(
        {file.path: FolderTagChange(add=["information-science"], remove=["stale"])}, vault
    )

    assert updated[0].tags == ["existing", "information-science"]
    assert vault.load_file(file.path).tags == ["existing", "information-science"]


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
