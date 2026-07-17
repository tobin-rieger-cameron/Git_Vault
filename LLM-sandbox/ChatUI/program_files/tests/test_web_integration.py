"""Real network call against ddgs. Skipped if it fails (e.g. offline, rate-limited)."""

from __future__ import annotations

import pytest

from program_files.utils.web import search_web


def test_search_web_returns_real_results_or_skips() -> None:
    results = search_web("Python programming language", max_results=3)
    if not results:
        pytest.skip("no results from a live ddgs call — likely offline or rate-limited")
    assert all(r.url for r in results)
    assert len(results) <= 3
