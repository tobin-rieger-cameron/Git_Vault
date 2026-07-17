"""Verb 2 — Draft a paper: back-and-forth authoring of a long-form, living document."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from chatui.llm import ModelClient
from chatui.models import File
from chatui.vault import Vault, extract_wikilinks, normalize_link_target


def start_draft(subject: str, vault: Vault) -> File:
    """Resume an existing file whose title matches subject, or start a new unsaved one."""
    title = subject.strip()
    normalized = normalize_link_target(title)
    for file in vault.list_files():
        if normalize_link_target(file.title) == normalized:
            return file

    now = datetime.now()
    path = vault.root / f"{_safe_filename(title)}.md"
    return File(path=path, title=title, body="", tags=[], links=[], created=now, updated=now, last_reviewed=None)


async def revise_draft(file: File, instruction: str, model: ModelClient) -> File:
    """Ask the model to rewrite the full draft per instruction; the caller still needs to save_draft()."""
    prompt = _build_revision_prompt(file, instruction)
    new_body = await model.stream(prompt)
    new_body = new_body.strip() + "\n"
    return replace(file, body=new_body, links=extract_wikilinks(new_body), updated=datetime.now())


def save_draft(file: File, vault: Vault) -> None:
    vault.save_file(file)


def _safe_filename(title: str) -> str:
    return title.replace("/", "-")


def _build_revision_prompt(file: File, instruction: str) -> str:
    if file.body.strip():
        parts = [
            f'You are helping the user write and revise a long-form paper titled "{file.title}".',
            "This is a living document the user returns to expand and restructure over time — "
            "write in the user's own voice, not generic textbook prose.",
            "",
            "--- CURRENT DRAFT ---",
            file.body,
            "--- END DRAFT ---",
            "",
            f"Instruction: {instruction}",
            "",
            "Write the complete updated draft (the full paper, not just the changed part). "
            "No YAML frontmatter — it is added separately.",
        ]
    else:
        parts = [
            f'You are helping the user start a long-form paper titled "{file.title}".',
            "This will be a living document the user returns to expand over time — "
            "write in a clear, conversational voice, not generic textbook prose.",
            "",
            f"Instruction: {instruction}",
            "",
            "Write the opening draft now. No YAML frontmatter — it is added separately.",
        ]
    return "\n".join(parts)
