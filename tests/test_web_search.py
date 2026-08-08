from src.schemas import SearchResult
from src.tools.web_search import format_search_results, search_company


def test_search_company_returns_empty_without_api_key(monkeypatch):
    monkeypatch.setattr("src.tools.web_search.config.TAVILY_API_KEY", "")

    results = search_company("Acme Inc")

    assert results == []


def test_search_company_never_raises_on_api_failure(mocker, monkeypatch):
    import sys

    monkeypatch.setattr("src.tools.web_search.config.TAVILY_API_KEY", "test-key")

    mock_tavily = mocker.MagicMock()
    mock_tavily.TavilyClient.return_value.search.side_effect = RuntimeError("rate limited")
    monkeypatch.setitem(sys.modules, "tavily", mock_tavily)

    results = search_company("Acme Inc")

    assert results == []


def test_format_search_results_empty():
    assert format_search_results([]) == ""


def test_format_search_results_formats_entries():
    results = [
        SearchResult(title="News", url="https://example.com", content="Hello"),
    ]
    formatted = format_search_results(results)
    assert "[1] News" in formatted
    assert "https://example.com" in formatted
    assert "Hello" in formatted
