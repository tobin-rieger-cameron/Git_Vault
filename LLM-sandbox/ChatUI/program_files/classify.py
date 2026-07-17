"""Verb 3 — Classify inline: suggest a file's folder/tags/links right after it's drafted, one at a time."""

from __future__ import annotations

import logging
import re
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Callable

from program_files.feedback import load_recent_overrides
from program_files.llm import ModelClient
from program_files.models import ClassificationSuggestion, File, Override
from program_files.vault import Vault, extract_wikilinks

_log = logging.getLogger(__name__)

_STRUCTURE_PLAN_PATH = Path(__file__).resolve().parent.parent / "config" / "vault-structure-plan.md"

_TABLE_ROW_RE = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$", re.MULTILINE)


async def suggest_classification(
    file: File, model: ModelClient, on_status: Callable[[str], None] | None = None
) -> ClassificationSuggestion:
    """Suggest tags, then a folder (tag-map first, LLM fallback) — nothing is applied yet."""
    status = on_status or (lambda _text: None)
    status("suggesting tags…")
    tags = await _suggest_tags(file, model)
    status("choosing a folder…")
    folder = await _suggest_folder(tags or file.tags, file, model)
    return ClassificationSuggestion(file_path=file.path, suggested_folder=folder, suggested_tags=tags)


async def suggest_wikilinks(
    file: File, vault: Vault, model: ModelClient, on_status: Callable[[str], None] | None = None
) -> tuple[list[str], list[str]]:
    """Return (new links to propose, links proposed but already present) — nothing is applied yet."""
    status = on_status or (lambda _text: None)
    status(f"searching for wikilinks in {file.path.name}…")
    return await _suggest_links(file, vault, model)


def apply_classification(file: File, suggestion: ClassificationSuggestion, vault: Vault) -> File:
    """Move the file if a folder was suggested and merge in new tags — links are applied separately, see apply_wikilink."""
    new_path = file.path
    if suggestion.suggested_folder:
        new_path = vault.root / suggestion.suggested_folder / file.path.name

    merged_tags = list(dict.fromkeys([*file.tags, *suggestion.suggested_tags]))

    updated = replace(file, path=new_path, tags=merged_tags, updated=datetime.now())

    if new_path != file.path and file.path.exists():
        file.path.unlink()
    vault.save_file(updated)
    return updated


def apply_wikilink(file: File, link: str, vault: Vault) -> File:
    """Wrap link's first occurrence in the body as [[link]] — caller has already confirmed it's present in the text."""
    new_body = _wrap_occurrence(file.body, link)
    updated = replace(file, body=new_body, links=extract_wikilinks(new_body), updated=datetime.now())
    vault.save_file(updated)
    return updated


async def _suggest_tags(file: File, model: ModelClient) -> list[str]:
    feedback = _format_feedback(load_recent_overrides("tags"))
    prompt = (
        (f"{feedback}\n\n" if feedback else "")
        + "Suggest 1-4 short, lowercase, single-word or hyphenated topic tags for this note.\n"
        "Reply with ONLY a comma-separated list of tags, nothing else.\n\n"
        f"Title: {file.title}\n\n"
        f"Content:\n{file.body[:1000]}\n"
    )
    raw = await model.ask_coding(prompt)
    return [t.strip().lower() for t in raw.split(",") if t.strip()]


async def _suggest_folder(tags: list[str], file: File, model: ModelClient) -> str | None:
    tag_map = _load_tag_folder_map(_read_structure_plan())
    for tag in tags:
        folder = tag_map.get(tag)
        if folder:
            return folder

    folders = sorted(set(tag_map.values()) | {"misc"})
    feedback = _format_feedback(load_recent_overrides("placement"))
    prompt = (
        (f"{feedback}\n\n" if feedback else "")
        + "You are classifying a knowledge vault article into a folder.\n\n"
        f"Available folders:\n{', '.join(folders)}\n\n"
        f"Folder descriptions (from vault-structure-plan.md):\n{_read_structure_plan()[:1200]}\n\n"
        f"Article content (first 400 chars):\n{file.body[:400]}\n\n"
        f"Reply with ONLY one folder name from this list: {', '.join(folders)}\n"
        "If uncategorisable, reply: misc\n\nFolder:"
    )
    raw = (await model.ask_coding(prompt)).strip().lower()
    for folder in folders:
        if folder in raw:
            return folder
    return "misc"


async def _suggest_links(file: File, vault: Vault, model: ModelClient) -> tuple[list[str], list[str]]:
    """Return (new links to propose, links proposed but already present in the note)."""
    existing_links = set(file.links)
    candidates = sorted({f.title for f in vault.list_files() if f.path != file.path} - {file.title})
    if not candidates:
        return [], []

    feedback = _format_feedback(load_recent_overrides("wikilink"))
    prompt = (
        (f"{feedback}\n\n" if feedback else "")
        + "You are suggesting [[wikilinks]] to add to a note, linking to OTHER existing notes "
        "in the vault where a phrase in this note's text refers to that note's topic.\n"
        f"Existing vault notes (ONLY suggest links to these exact titles): {', '.join(candidates)}\n\n"
        f"Note content:\n{file.body[:1500]}\n\n"
        "Reply with ONLY a comma-separated list of note titles from the list above that this "
        "note should link to (titles only, no [[ ]] brackets). Reply NONE if none apply.\n"
    )
    raw = await model.ask_coding(prompt)
    if raw.strip().upper() == "NONE":
        _log.info("wikilinks: model replied NONE for %s", file.path)
        return [], []
    candidate_set = set(candidates)
    proposed = [t.strip() for t in raw.split(",") if t.strip()]
    already_linked = [t for t in proposed if t in existing_links]
    invalid = [t for t in proposed if t not in candidate_set and t not in existing_links]
    if invalid:
        _log.warning("wikilinks: dropped %s for %s (not an exact vault-title match)", invalid, file.path)

    # Linking to a topic the note doesn't literally mention is a separate feature (deferred);
    # for now only offer candidates whose phrase actually occurs in the body, since applying
    # wraps that occurrence in place rather than appending a list of unrelated topics.
    candidates_in_body = [t for t in proposed if t in candidate_set and t not in existing_links]
    kept = [t for t in candidates_in_body if t.lower() in file.body.lower()]
    not_in_body = [t for t in candidates_in_body if t not in kept]
    if not_in_body:
        _log.info("wikilinks: deferred (not found in body text) %s for %s", not_in_body, file.path)
    if already_linked:
        _log.info("wikilinks: %s already linked in %s", already_linked, file.path)
    return kept, already_linked


def _wrap_occurrence(body: str, link: str) -> str:
    """Wrap link's first case-insensitive occurrence in body as [[link]], preserving the canonical title."""
    start = body.lower().find(link.lower())
    if start == -1:
        return body
    end = start + len(link)
    return f"{body[:start]}[[{link}]]{body[end:]}"


def _load_tag_folder_map(plan_text: str) -> dict[str, str]:
    """Parse the Tag|Folder table in vault-structure-plan.md, skipping header/separator/"(skip...)" rows."""
    mapping: dict[str, str] = {}
    for tag, folder in _TABLE_ROW_RE.findall(plan_text):
        if tag in ("Tag", "---") or set(tag) <= {"-"} or folder.lower().startswith("(skip"):
            continue
        mapping[tag] = folder
    return mapping


def _read_structure_plan() -> str:
    try:
        return _STRUCTURE_PLAN_PATH.read_text(encoding="utf-8")
    except OSError:
        return ""


def _format_feedback(overrides: list[Override]) -> str:
    if not overrides:
        return ""
    lines = [
        f'- Proposed "{o.proposed}", chose "{o.chosen}"' + (f" ({o.reason})" if o.reason else "")
        for o in overrides
    ]
    return "Past corrections to consider:\n" + "\n".join(lines)
