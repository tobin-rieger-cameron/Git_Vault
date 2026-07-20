# LLM-sandbox/ChatUI/program_files/classify.py
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
from program_files.utils.models import (
    ClassificationSuggestion,
    File,
    FolderTagChange,
    Override,
    WikilinkSuggestion,
)
from program_files.utils.retrieval import Retriever
from program_files.utils.vault import Vault, extract_wikilinks

_log = logging.getLogger(__name__)

_STRUCTURE_PLAN_PATH = Path(__file__).resolve().parent.parent / "config" / "vault-structure-plan.md"

_TABLE_ROW_RE = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$", re.MULTILINE)


async def suggest_classification(
    file: File, vault: Vault, model: ModelClient, on_status: Callable[[str], None] | None = None
) -> ClassificationSuggestion:
    """Suggest tags and a folder for review."""
    status = on_status or (lambda _text: None)
    status("suggesting tags…")
    tags = await _suggest_tags(file, vault, model) #TODO: print tags individually as they are "found"
    status("choosing a folder…")
    folder = await _suggest_folder(tags or file.tags, file, model)
    return ClassificationSuggestion(file_path=file.path, suggested_folder=folder, suggested_tags=tags)


def suggest_folder_tags(directory: Path, vault: Vault) -> dict[Path, FolderTagChange]:
    """Map every file under directory to the folder-tag changes (see Vault.folder_tags) that keep
    it in sync with the current folder structure: add whatever's missing, and remove any tag that
    used to name a real vault folder but isn't one of this file's current ancestors anymore (e.g.
    the folder itself got moved). Deterministic, no model call — the batch counterpart to /tags's
    per-file LLM pass, which only ever adds."""
    vocabulary = vault.folder_tag_vocabulary()
    plan: dict[Path, FolderTagChange] = {}
    for file in vault.list_files():
        if directory not in file.path.parents:
            continue
        current = set(vault.folder_tags(file.path.parent))
        existing_lower = {t.lower(): t for t in file.tags}
        to_add = [tag for tag in vault.folder_tags(file.path.parent) if tag not in existing_lower]
        to_remove = [
            original
            for lower, original in existing_lower.items()
            if lower in vocabulary and lower not in current
        ]
        if to_add or to_remove:
            plan[file.path] = FolderTagChange(add=to_add, remove=to_remove)
    return plan


def apply_folder_tags(plan: dict[Path, FolderTagChange], vault: Vault) -> list[File]:
    """Apply each path's planned tag add/remove and persist; returns the updated files."""
    updated_files = []
    for path, change in plan.items():
        file = vault.load_file(path)
        remove_lower = {t.lower() for t in change.remove}
        kept = [t for t in file.tags if t.lower() not in remove_lower]
        updated = replace(file, tags=list(dict.fromkeys([*kept, *change.add])), updated=datetime.now())
        vault.save_file(updated)
        updated_files.append(updated)
    return updated_files


async def suggest_wikilinks(
    file: File,
    vault: Vault,
    retriever: Retriever,
    top_k: int,
    similarity_threshold: float,
    on_status: Callable[[str], None] | None = None,
) -> WikilinkSuggestion:
    """ scan through vault for possible files to link; presents inline and appended link suggestions """
    status = on_status or (lambda _text: None)
    status(f"searching for wikilinks in {file.path.name}…")
    return await _suggest_wikilinks(file, vault, retriever, top_k, similarity_threshold) #TODO: print wikilinks as they are found

#TODO: consider squishing apply_wikilink and apply_see_also into this one function
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
    from this always matches what /done would actually write.""" # this is an example of a verbose docstring, does not follow my intended format, check the dockstrings above, also check their history in the git repo to see how I changed them myself to get a better sense of my tone
    # docstring should be a litteral description of what the function takes as input and returns as output
    for title in inline_titles:
        body = _wrap_occurrence(body, title)
    if see_also_titles:
        body = _insert_see_also(body, see_also_titles)
    return body


async def _suggest_tags(file: File, vault: Vault, model: ModelClient) -> list[str]:
    existing = {t.lower() for t in file.tags}
    folder_tags = [tag for tag in vault.folder_tags(file.path.parent) if tag not in existing]
    feedback = _format_feedback(load_recent_overrides("tags"))
    prompt = (
        (f"{feedback}\n\n" if feedback else "")
        + "Suggest 1-4 short, lowercase, single-word or hyphenated topic tags for this note.\n"
        "Reply with ONLY a comma-separated list of tags, nothing else.\n\n"
        f"Title: {file.title}\n\n"
        f"Content:\n{file.body[:1000]}\n"
    )
    raw = await model.ask_coding(prompt)
    llm_tags = [t.strip().lower() for t in raw.split(",") if t.strip()]
    return list(dict.fromkeys([*folder_tags, *llm_tags]))


async def _suggest_folder(tags: list[str], file: File, model: ModelClient) -> str | None:
    tag_map = _load_tag_folder_map(_read_structure_plan())
    for tag in tags:
        folder = tag_map.get(tag)
        if folder:
            return folder

    folders = sorted(set(tag_map.values()) | {"misc"})
    feedback = _format_feedback(load_recent_overrides("placement"))
    #TODO: use current tags to help with folder consideration
    prompt = (
        (f"{feedback}\n\n" if feedback else "")
        + "You are classifying an article into a folder.\n\n"
        "The folder should fit the subject class of the article"
        f"Available folders:\n{', '.join(folders)}\n\n"
        f"Folder descriptions (from vault-structure-plan.md):\n{_read_structure_plan()[:1200]}\n\n"
        f"Article summary (all text before the first # heading):\n{file.body[:800]}\n\n"
        f"Reply with ONLY one folder name from this list: {', '.join(folders)}\n"
        "If the article does not fit cleanly in one place, provide a list of possible folders"
    )
    raw = (await model.ask_coding(prompt)).strip().lower()
    for folder in folders:
        if folder in raw:
            return folder
    return "misc"


async def _suggest_wikilinks(
    file: File, vault: Vault, retriever: Retriever, top_k: int, similarity_threshold: float
) -> WikilinkSuggestion:
    """ 
    provides a list of wikilinks to files that are mentioned in the file body
    also recommends a list of "See-also" for files that relate to the subject but aren't directly mentioned
    """ # < this is the intended usecase for this function
    """Inline tier: word-boundary text match against every other vault title (deterministic, no model
    call — this is the same check apply_wikilink relies on to find what it's wrapping). See-also tier:
    a vector-similarity search against the vault's existing embeddings (the same ones /ask retrieves
    against), for notes that are topically related without ever mentioning each other's exact title."""
    #TODO: clean up this docstring and consider how to define a "good" docstring

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
