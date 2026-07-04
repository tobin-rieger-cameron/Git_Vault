"""Plain data structures — no behavior. See style_guide.md's objects-vs-data-structures section."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path


class RetrievalPath(Enum):
    VAULT = "vault"
    GROUNDED = "grounded"
    MODEL_KNOWLEDGE = "model_knowledge"


@dataclass
class Paper:
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
    paper_path: Path
    suggested_folder: str | None
    suggested_tags: list[str]
    suggested_links: list[str]


@dataclass
class ReviewQuestion:
    paper_path: Path
    question: str
    answer_hint: str


@dataclass
class Override:
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
