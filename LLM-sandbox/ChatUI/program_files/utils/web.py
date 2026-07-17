"""
chatui/web.py
Web search supplement using duckduckgosearch.
"""

from __future__ import annotations

from dataclasses import dataclass

from ddgs import DDGS


@dataclass
class WebResult:
    url: str
    title: str
    snippet: str


def search_web(query: str, max_results: int) -> list[WebResult]:
    try:
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=max_results))
    except Exception:
        return []
    return [
        WebResult(url=r.get("href", ""), title=r.get("title", ""), snippet=r.get("body", ""))
        for r in raw_results
    ]
