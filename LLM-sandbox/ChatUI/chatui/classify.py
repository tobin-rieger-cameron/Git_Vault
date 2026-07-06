"""Verb 3 — Classify inline: suggest a file's folder/tags/links right after it's drafted, one at a time."""

from __future__ import annotations

import re
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from chatui.feedback import load_recent_overrides
from chatui.llm import ModelClient
from chatui.models import ClassificationSuggestion, File, Override
from chatui.vault import Vault, extract_wikilinks

_STRUCTURE_PLAN_PATH = Path(__file__).resolve().parent.parent / "config" / "vault-structure-plan.md"

_TABLE_ROW_RE = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$", re.MULTILINE)


async def suggest_classification(file: File, vault: Vault, model: ModelClient) -> ClassificationSuggestion:
    """Suggest tags, then a folder (tag-map first, LLM fallback), then wikilinks — nothing is applied yet."""
    tags = await _suggest_tags(file, model)
    folder = await _suggest_folder(tags or file.tags, file, model)
    links = await _suggest_links(file, vault, model)
    return ClassificationSuggestion(
        file_path=file.path, suggested_folder=folder, suggested_tags=tags, suggested_links=links
    )


def apply_classification(file: File, suggestion: ClassificationSuggestion, vault: Vault) -> File:
    """Move the file if a folder was suggested, merge in new tags, and append a See Also section for new links."""
    new_path = file.path
    if suggestion.suggested_folder:
        new_path = vault.root / suggestion.suggested_folder / file.path.name

    merged_tags = list(dict.fromkeys([*file.tags, *suggestion.suggested_tags]))
    new_body = _apply_see_also(file.body, suggestion.suggested_links)

    updated = replace(
        file,
        path=new_path,
        tags=merged_tags,
        body=new_body,
        links=extract_wikilinks(new_body),
        updated=datetime.now(),
    )

    if new_path != file.path and file.path.exists():
        file.path.unlink()
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


async def _suggest_links(file: File, vault: Vault, model: ModelClient) -> list[str]:
    existing_links = set(file.links)
    candidates = sorted({f.title for f in vault.list_files() if f.path != file.path} - {file.title})
    if not candidates:
        return []

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
        return []
    candidate_set = set(candidates)
    return [t.strip() for t in raw.split(",") if t.strip() in candidate_set and t.strip() not in existing_links]


def _apply_see_also(body: str, links: list[str]) -> str:
    new_links = [link for link in links if link not in extract_wikilinks(body)]
    if not new_links:
        return body
    section = "\n## See Also\n\n" + "\n".join(f"- [[{link}]]" for link in new_links) + "\n"
    return body.rstrip("\n") + "\n" + section


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
