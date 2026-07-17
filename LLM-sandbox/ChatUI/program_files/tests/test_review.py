from datetime import datetime, timedelta
from pathlib import Path

import pytest

from chatui.models import File
from chatui.review import files_due_for_review, generate_review_questions, mark_reviewed
from chatui.vault import Vault


def _file(tmp_path: Path, name: str, last_reviewed: datetime | None) -> File:
    now = datetime.now()
    return File(
        path=tmp_path / name, title=name[:-3], body="Body.\n", tags=[], links=[],
        created=now, updated=now, last_reviewed=last_reviewed,
    )


class _FakeModel:
    def __init__(self, response: str) -> None:
        self.response = response
        self.prompts: list[str] = []

    async def ask_coding(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.response


@pytest.mark.asyncio
async def test_generate_review_questions_parses_q_and_hint_pairs(tmp_path: Path) -> None:
    file = _file(tmp_path, "Taxonomy.md", None)
    response = (
        "Q: What is taxonomy?\nHint: classification of organisms\n\n"
        "Q: Who introduced binomial nomenclature?\nHint: an 18th century botanist\n"
    )
    model = _FakeModel(response)

    questions = await generate_review_questions(file, model, count=3)

    assert len(questions) == 2
    assert questions[0].question == "What is taxonomy?"
    assert questions[0].answer_hint == "classification of organisms"
    assert all(q.file_path == file.path for q in questions)


@pytest.mark.asyncio
async def test_generate_review_questions_respects_count_limit(tmp_path: Path) -> None:
    file = _file(tmp_path, "A.md", None)
    response = "\n\n".join(f"Q: Question {i}?\nHint: hint {i}" for i in range(5))
    model = _FakeModel(response)

    questions = await generate_review_questions(file, model, count=2)

    assert len(questions) == 2


@pytest.mark.asyncio
async def test_generate_review_questions_empty_on_malformed_response(tmp_path: Path) -> None:
    file = _file(tmp_path, "A.md", None)
    model = _FakeModel("I don't understand the request.")

    questions = await generate_review_questions(file, model)

    assert questions == []


def test_mark_reviewed_sets_timestamp_and_saves(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    file = _file(tmp_path, "A.md", None)
    vault.save_file(file)

    updated = mark_reviewed(file, vault)

    assert updated.last_reviewed is not None
    reloaded = vault.load_file(file.path)
    assert reloaded.last_reviewed is not None


def test_files_due_for_review_includes_never_reviewed(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    never = _file(tmp_path, "Never.md", None)
    recent = _file(tmp_path, "Recent.md", datetime.now())
    vault.save_file(never)
    vault.save_file(recent)

    due = files_due_for_review(vault, staleness=timedelta(days=30))

    assert [f.title for f in due] == ["Never"]


def test_files_due_for_review_includes_stale_files(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    stale = _file(tmp_path, "Stale.md", datetime.now() - timedelta(days=60))
    fresh = _file(tmp_path, "Fresh.md", datetime.now())
    vault.save_file(stale)
    vault.save_file(fresh)

    due = files_due_for_review(vault, staleness=timedelta(days=30))

    assert [f.title for f in due] == ["Stale"]


def test_files_due_for_review_sorts_most_stale_first(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    never = _file(tmp_path, "Never.md", None)
    old = _file(tmp_path, "VeryOld.md", datetime.now() - timedelta(days=90))
    less_old = _file(tmp_path, "SlightlyOld.md", datetime.now() - timedelta(days=40))
    for f in (less_old, never, old):
        vault.save_file(f)

    due = files_due_for_review(vault, staleness=timedelta(days=30))

    assert [f.title for f in due] == ["Never", "VeryOld", "SlightlyOld"]
