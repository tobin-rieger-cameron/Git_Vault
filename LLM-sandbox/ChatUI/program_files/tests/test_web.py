import program_files.web as web_module
from program_files.web import WebResult, search_web


class _FakeDDGS:
    def __init__(self, results: list[dict] | None = None, error: Exception | None = None) -> None:
        self._results = results or []
        self._error = error

    def __enter__(self) -> "_FakeDDGS":
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    def text(self, _query: str, max_results: int) -> list[dict]:
        if self._error is not None:
            raise self._error
        return self._results[:max_results]


def test_search_web_returns_typed_results(monkeypatch) -> None:
    fake_results = [
        {"href": "https://example.com/a", "title": "A", "body": "About A"},
        {"href": "https://example.com/b", "title": "B", "body": "About B"},
    ]
    monkeypatch.setattr(web_module, "DDGS", lambda: _FakeDDGS(fake_results))

    results = search_web("query", max_results=2)

    assert results == [
        WebResult(url="https://example.com/a", title="A", snippet="About A"),
        WebResult(url="https://example.com/b", title="B", snippet="About B"),
    ]


def test_search_web_no_results_returns_empty_list(monkeypatch) -> None:
    monkeypatch.setattr(web_module, "DDGS", lambda: _FakeDDGS([]))

    assert search_web("query", max_results=3) == []


def test_search_web_failure_returns_empty_list_not_sentinel_string(monkeypatch) -> None:
    monkeypatch.setattr(web_module, "DDGS", lambda: _FakeDDGS(error=RuntimeError("network down")))

    assert search_web("query", max_results=3) == []
