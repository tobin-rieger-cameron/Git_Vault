"""Verb 3 — Classify inline: suggest a file's folder/tags/links right after it's drafted, one at a time."""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Callable

from program_files.utils.feedback import load_recent_overrides
from program_files.utils.llm import ModelClient
from program_files.utils.models import ClassificationSuggestion, File, Override, WikilinkSuggestion
from program_files.utils.retrieval import Retriever
from program_files.utils.vault import Vault, extract_wikilinks

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
    file: File,
    vault: Vault,
    retriever: Retriever,
    top_k: int,
    similarity_threshold: float,
    on_status: Callable[[str], None] | None = None,
) -> WikilinkSuggestion:
    """Return inline vs. see-also candidates — nothing is applied yet. No model call: substring match
    for inline (mirrors the vault's own "link at the first textual instance" rule), vector search
    over the same embeddings /ask uses for see-also (mirrors "See also only when no inline text fits")."""
    status = on_status or (lambda _text: None)
    status(f"searching for wikilinks in {file.path.name}…")
    return await _suggest_wikilinks(file, vault, retriever, top_k, similarity_threshold)


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


def apply_see_also(file: File, titles: list[str], vault: Vault) -> File:
    """Add titles as `* [[Title]]` bullets under a "## See also" section, creating it if absent."""
    new_titles = [t for t in titles if f"[[{t}]]" not in file.body]
    if not new_titles:
        return file
    new_body = _insert_see_also(file.body, new_titles)
    updated = replace(file, body=new_body, links=extract_wikilinks(new_body), updated=datetime.now())
    vault.save_file(updated)
    return updated


def preview_with_wikilinks(body: str, inline_titles: list[str], see_also_titles: list[str]) -> str:
    """Body as it would read with inline_titles wrapped and see_also_titles appended — pure, no
    save; shares the exact wrap/insert logic apply_wikilink/apply_see_also use, so a preview built
    from this always matches what /done would actually write."""
    for title in inline_titles:
        body = _wrap_occurrence(body, title)
    if see_also_titles:
        body = _insert_see_also(body, see_also_titles)
    return body


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


async def _suggest_wikilinks(
    file: File, vault: Vault, retriever: Retriever, top_k: int, similarity_threshold: float
) -> WikilinkSuggestion:
    """Inline tier: word-boundary text match against every other vault title (deterministic, no model
    call — this is the same check apply_wikilink relies on to find what it's wrapping). See-also tier:
    a vector-similarity search against the vault's existing embeddings (the same ones /ask retrieves
    against), for notes that are topically related without ever mentioning each other's exact title."""
    existing_links = set(file.links)
    other_files = [f for f in vault.list_files() if f.path != file.path]
    candidates = sorted({f.title for f in other_files} - {file.title})
    if not candidates:
        return WikilinkSuggestion([], [], [])

    text_matches = [t for t in candidates if _mentions(file.body, t)]
    already_linked = [t for t in text_matches if t in existing_links]
    inline_new = [t for t in text_matches if t not in existing_links]

    excluded = existing_links | set(text_matches)
    see_also_new = await _suggest_see_also(file, other_files, excluded, retriever, top_k, similarity_threshold)

    return WikilinkSuggestion(inline_new=inline_new, already_linked=already_linked, see_also_new=see_also_new)


def _mentions(body: str, title: str) -> bool:
    """Word-boundary, case-insensitive match — a plain substring check would match "ai" inside "again"."""
    return re.search(rf"\b{re.escape(title)}\b", body, re.IGNORECASE) is not None


async def _suggest_see_also(
    file: File,
    other_files: list[File],
    excluded: set[str],
    retriever: Retriever,
    top_k: int,
    similarity_threshold: float,
) -> list[str]:
    """Titles of other vault files whose embeddings are similar to this one's body, ranked by score."""
    title_by_path = {f.path: f.title for f in other_files}
    try:
        # Retriever/chromadb is sync, so run it off the event loop like Retriever.ingest() already does.
        # exclude_source=file.path: without it, the query text (this file's own body) matches this
        # file's own chunks best of all, filling the whole top_k window and leaving no room for others.
        hits = await asyncio.to_thread(retriever.search, file.body[:2000], top_k, file.path)
    except Exception as exc:
        _log.warning("see-also search failed for %s: %s", file.path, exc)
        return []
    best_score: dict[str, float] = {}
    for chunk in hits:
        title = title_by_path.get(chunk.source_path)
        if title is None or title in excluded or chunk.score < similarity_threshold:
            continue
        best_score[title] = max(best_score.get(title, chunk.score), chunk.score)
    return sorted(best_score, key=lambda t: -best_score[t])


def _wrap_occurrence(body: str, link: str) -> str:
    """Wrap link's first case-insensitive occurrence in body as [[link]], preserving the canonical title."""
    start = body.lower().find(link.lower())
    if start == -1:
        return body
    end = start + len(link)
    return f"{body[:start]}[[{link}]]{body[end:]}"


_SEE_ALSO_HEADING_RE = re.compile(r"^## See also[ \t]*\n", re.MULTILINE)
_NEXT_HEADING_RE = re.compile(r"^##[ \t]+\S", re.MULTILINE)


def _insert_see_also(body: str, titles: list[str]) -> str:
    """Append `* [[Title]]` bullets under an existing "## See also" section, or create one at the end."""
    bullets = "\n".join(f"* [[{t}]]" for t in titles)
    heading = _SEE_ALSO_HEADING_RE.search(body)
    if heading is None:
        return f"{body.rstrip(chr(10))}\n\n## See also\n{bullets}\n"

    next_heading = _NEXT_HEADING_RE.search(body, heading.end())
    section_end = next_heading.start() if next_heading else len(body)
    existing_section = body[heading.end():section_end].rstrip(chr(10))
    joiner = "\n" if existing_section else ""
    return f"{body[:heading.end()]}{existing_section}{joiner}{bullets}\n\n{body[section_end:]}"


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
