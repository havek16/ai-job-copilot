"""
web_search.py — Company research via Tavily API.

Design principle: this tool NEVER raises. Any failure (timeout, bad key,
rate limit) sets a skip flag on the returned state and logs a warning.
The calling step then continues with whatever it has.

This mirrors production resilience patterns where an optional enrichment
step should degrade gracefully, not take down the whole pipeline.
"""

from __future__ import annotations

from src.config import config
from src.logger import get_logger
from src.schemas import SearchResult

logger = get_logger(__name__)


def search_company(company_name: str) -> list[SearchResult]:
    """
    Search for recent information about a company using Tavily.

    Args:
        company_name: The name of the company to research.

    Returns:
        A list of SearchResult objects (may be empty if search fails).
        Never raises — failures are logged and an empty list is returned.
    """
    if not config.TAVILY_API_KEY:
        logger.warning(
            "TAVILY_API_KEY not set — skipping web search",
            extra={"company": company_name},
        )
        return []

    try:
        # Import here so the app works even without tavily installed
        from tavily import TavilyClient  # type: ignore

        client = TavilyClient(api_key=config.TAVILY_API_KEY)

        query = (
            f"{company_name} company recent news product engineering culture 2024 2025"
        )
        logger.info(
            f"Searching Tavily for company info",
            extra={"company": company_name, "query": query},
        )

        response = client.search(
            query=query,
            search_depth="basic",
            max_results=5,
            include_answer=False,
        )

        results: list[SearchResult] = []
        for item in response.get("results", []):
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    content=item.get("content", "")[:500],  # Truncate to avoid prompt bloat
                )
            )

        logger.info(
            f"Web search completed",
            extra={"company": company_name, "result_count": len(results)},
        )
        return results

    except ImportError:
        logger.warning(
            "tavily-python not installed — skipping web search. "
            "Run: pip install tavily-python"
        )
        return []

    except Exception as err:
        # Catch everything: timeout, HTTP error, auth failure, rate limit
        logger.warning(
            f"Web search failed — continuing without research data",
            extra={"company": company_name, "error": str(err)},
        )
        return []


def format_search_results(results: list[SearchResult]) -> str:
    """
    Format search results into a readable block for the LLM prompt.
    Returns empty string if no results.
    """
    if not results:
        return ""

    lines: list[str] = []
    for i, r in enumerate(results, start=1):
        lines.append(f"[{i}] {r.title}")
        lines.append(f"    URL: {r.url}")
        lines.append(f"    {r.content}")
        lines.append("")

    return "\n".join(lines)
