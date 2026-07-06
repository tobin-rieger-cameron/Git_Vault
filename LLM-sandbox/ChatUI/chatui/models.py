"""Plain data structures — no behavior. See style_guide.md's objects-vs-data-structures section."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path


class RetrievalPath(Enum):
    """Which source ask() drew its answer from — vault chunks, weak/no match, or the model alone."""

    VAULT = "vault"
    WEAK_MATCH = "weak_match"
    MODEL_KNOWLEDGE = "model_knowledge"


@dataclass
class File:
    path: Path
    title: str
    body: str
    tags: list[str]
    links: list[str]
    created: datetime
    updated: datetime
    last_reviewed: datetime | None


@dataclass
class Chunk:
    """A retrieved passage; score is Chroma's similarity score, not a raw distance."""

    text: str
    source_path: Path
    tags: list[str]
    score: float


@dataclass
class AskResult:
    answer: str
    path: RetrievalPath
    sources: list[Path]
    web_supplement: str | None


@dataclass
class ClassificationSuggestion:
    file_path: Path
    suggested_folder: str | None
    suggested_tags: list[str]
    suggested_links: list[str]


@dataclass
class ReviewQuestion:
    file_path: Path
    question: str
    answer_hint: str


@dataclass
class Override:
    """A record of the user rejecting a suggestion; kind is e.g. "tags"/"placement"/"wikilink"."""

    kind: str
    path: Path
    proposed: str
    chosen: str
    reason: str | None
    timestamp: datetime


@dataclass
class IngestStats:
    new: int
    updated: int
    removed: int
    unchanged: int
