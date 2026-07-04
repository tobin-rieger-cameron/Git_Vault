"""Web search supplement (ddgs)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WebResult:
    url: str
    title: str
    snippet: str


def search_web(query: str, max_results: int) -> list[WebResult]:
    raise NotImplementedError
