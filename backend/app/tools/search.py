import json
import logging
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def _duckduckgo_search(query: str, max_results: int = 5) -> list[dict]:
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", ""),
                "source": "DuckDuckGo",
            }
            for r in results
        ]
    except Exception as e:
        logger.warning(f"DuckDuckGo search failed: {e}")
        return []


@tool
def web_search(query: str, max_results: int = 5) -> str:
    """Search the web for information on a topic.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return (default 5, max 10).

    Returns:
        JSON string with search results containing title, url, snippet, source.
    """
    max_results = min(max_results, 10)
    results = _duckduckgo_search(query, max_results)

    if not results:
        return json.dumps({
            "query": query,
            "results": [],
            "error": "Search returned no results. This may be a connectivity issue or the topic returned no matches.",
        })

    return json.dumps({
        "query": query,
        "results": results,
        "total": len(results),
    })
