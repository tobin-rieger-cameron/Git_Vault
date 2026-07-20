from datetime import datetime
from pathlib import Path

import pytest

from program_files.utils.tools.draft_tools import edit_draft, revise_draft, save_draft
from program_files.utils.models import File
from program_files.utils.vault import Vault


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class _FakeModel:
    def __init__(self, response: str) -> None:
        self.response = response
        self.prompts: list[str] = []

    async def stream(self, prompt: str, on_token=None) -> str:
        self.prompts.append(prompt)
        return self.response


def test_edit_draft_loads_existing_file_by_title(tmp_path: Path) -> None:
    _write(tmp_path / "600-applied-sciences" / "Fine Tuning Methods.md", '---\ntitle: "Fine Tuning Methods"\n---\n\nExisting body.\n')
    vault = Vault(tmp_path)

    file = edit_draft("fine-tuning methods", vault)

    assert file.title == "Fine Tuning Methods"
    assert file.body == "Existing body.\n"
    assert file.path == tmp_path / "600-applied-sciences" / "Fine Tuning Methods.md"


def test_edit_draft_creates_new_file_when_no_match(tmp_path: Path) -> None:
    vault = Vault(tmp_path)

    file = edit_draft("Quantum Computing", vault)

    assert file.title == "Quantum Computing"
    assert file.body == ""
    assert file.tags == []
    assert file.path == tmp_path / "Quantum Computing.md"


def test_edit_draft_sanitizes_slash_in_subject(tmp_path: Path) -> None:
    vault = Vault(tmp_path)

    file = edit_draft("Risk/Reward", vault)

    assert file.path == tmp_path / "Risk-Reward.md"


@pytest.mark.asyncio
async def test_revise_draft_updates_body_links_and_timestamp(tmp_path: Path) -> None:
    now = datetime(2026, 1, 1)
    file = File(
        path=tmp_path / "Taxonomy.md", title="Taxonomy", body="Old body.\n", tags=["taxonomy"],
        links=[], created=now, updated=now, last_reviewed=None,
    )
    model = _FakeModel("New body referencing [[Dewey Decimal System]].")

    revised = await revise_draft(file, "expand the intro", model)

    assert revised.body == "New body referencing [[Dewey Decimal System]].\n"
    assert revised.links == ["Dewey Decimal System"]
    assert revised.updated > now
    assert revised.tags == ["taxonomy"]
    assert "Old body." in model.prompts[0]
    assert "expand the intro" in model.prompts[0]


@pytest.mark.asyncio
async def test_revise_draft_first_pass_prompt_has_no_current_draft_section(tmp_path: Path) -> None:
    now = datetime(2026, 1, 1)
    file = File(path=tmp_path / "New.md", title="New Subject", body="", tags=[], links=[], created=now, updated=now, last_reviewed=None)
    model = _FakeModel("An opening draft.")

    await revise_draft(file, "write an intro", model)

    assert "CURRENT DRAFT" not in model.prompts[0]
    assert "New Subject" in model.prompts[0]


def test_save_draft_writes_via_vault(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    now = datetime.now()
    file = File(
        path=tmp_path / "New Paper.md", title="New Paper", body="Body.\n", tags=["ai"],
        links=[], created=now, updated=now, last_reviewed=None,
    )

    save_draft(file, vault)
    loaded = vault.load_file(file.path)

    assert loaded.title == "New Paper"
    assert loaded.body == "Body.\n"
    assert loaded.tags == ["ai"]
