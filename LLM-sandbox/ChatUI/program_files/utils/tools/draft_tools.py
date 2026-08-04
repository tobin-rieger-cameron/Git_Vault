"""
    draft_note — back-and-forth authoring of a formatted article.
    the model works directly from the draft in hand, revising it per instruction.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from program_files.utils.llm import ModelClient
from program_files.utils.models import File
from program_files.utils.tools import ToolSpec
from program_files.utils.vault import Vault, extract_wikilinks, normalize_link_target


def build_draft_tools(vault: Vault, model: ModelClient) -> list[ToolSpec]:
    """Build the draft_note command tool, closing over the app's Vault/ModelClient."""

    async def _draft_note(args: dict) -> File:
        subject = args.get("subject")
        if subject is not None:
            return edit_draft(subject, vault)
        return await revise_draft(args["file"], args["instruction"], model)

    return [
        ToolSpec(
            name="draft_note",
            description="Start or resume drafting a note: pass subject to open/create one, or file+instruction to revise it.",
            parameters={
                "type": "object",
                "properties": {
                    "subject": {"type": "string"},
                    "file": {"type": "object"},
                    "instruction": {"type": "string"},
                },
            },
            handler=_draft_note,
        )
    ]


def edit_draft(subject: str, vault: Vault) -> File:
    """Load the vault file matching subject for editing, or create a new empty one if none exists."""
    title = subject.strip()
    link = normalize_link_target(title)

    for file in vault.list_files():
        if normalize_link_target(file.title) == link:
            return file

    now = datetime.now()
    path = vault.root / f"{_safe_filename(title)}.md"
    return File(path=path, title=title, body="", tags=[], links=[], created=now, updated=now, last_reviewed=None)


async def revise_draft(file: File, instruction: str, model: ModelClient) -> File:
    """Ask the model to rewrite the full draft per instruction; the caller still needs to save_draft()."""

    #TODO: a model should never rewrite a full file, it should only sugest pieces.

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
