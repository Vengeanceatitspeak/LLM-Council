"""Web scraping and search module for MakeMeRichGPT.

Provides URL scraping and DuckDuckGo search capabilities.
"""

import re
import httpx
from bs4 import BeautifulSoup
from typing import Optional, List, Dict
from duckduckgo_search import DDGS


async def scrape_url(url: str, timeout: float = 15.0) -> Optional[Dict[str, str]]:
    """
    Scrape text content from a URL.

    Returns:
        Dict with 'title', 'text', 'url' or None on failure
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove script and style elements
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe"]):
            tag.decompose()

        title = soup.title.string.strip() if soup.title and soup.title.string else url

        # Extract main content
        main = soup.find("main") or soup.find("article") or soup.find("body")
        if main is None:
            return None

        text = main.get_text(separator="\n", strip=True)

        # Clean up excessive whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        text = "\n".join(lines)

        # Truncate to avoid token overflow
        if len(text) > 8000:
            text = text[:8000] + "\n\n[Content truncated — full page was too long]"

        return {
            "title": title,
            "text": text,
            "url": url,
        }

    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None


def search_web(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Search the web using DuckDuckGo.

    Returns:
        List of dicts with 'title', 'href', 'body'
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            return [
                {
                    "title": r.get("title", ""),
                    "href": r.get("href", ""),
                    "body": r.get("body", ""),
                }
                for r in results
            ]
    except Exception as e:
        print(f"Error searching web: {e}")
        return []


def detect_urls(text: str) -> List[str]:
    """Extract URLs from text."""
    url_pattern = re.compile(
        r'https?://[^\s<>"{}|\\^`\[\]]+',
        re.IGNORECASE
    )
    return url_pattern.findall(text)


def detect_search_intent(text: str) -> bool:
    """Detect if the user wants a web search."""
    search_triggers = [
        "search for", "google", "look up", "find out",
        "what's happening", "latest news", "current price",
        "today's", "right now", "live data", "real-time",
        "search the web", "web search",
    ]
    text_lower = text.lower()
    return any(trigger in text_lower for trigger in search_triggers)
