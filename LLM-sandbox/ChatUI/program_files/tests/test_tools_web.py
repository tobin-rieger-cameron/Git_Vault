import pytest

from program_files.utils.tools.web_tools import build_web_tools
from program_files.utils.web import WebResult


@pytest.mark.asyncio
async def test_web_search_formats_results(monkeypatch) -> None:
    monkeypatch.setattr(
        "program_files.utils.tools.web_tools.search_web",
        lambda query, max_results: [WebResult(url="https://x.test", title="X", snippet="about x")],
    )
    web_search = build_web_tools(max_results=3)[0]

    result = await web_search.handler({"query": "x"})

    assert "https://x.test" in result
    assert "about x" in result


@pytest.mark.asyncio
async def test_web_search_no_results_returns_plain_message(monkeypatch) -> None:
    monkeypatch.setattr("program_files.utils.tools.web_tools.search_web", lambda query, max_results: [])
    web_search = build_web_tools(max_results=3)[0]

    result = await web_search.handler({"query": "nothing"})

    assert result == "No web results found."


@pytest.mark.asyncio
async def test_web_search_requires_a_query() -> None:
    web_search = build_web_tools(max_results=3)[0]

    result = await web_search.handler({})

    assert "required" in result
