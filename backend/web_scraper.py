"""Web scraping and search module for CouncilGPT.

Provides URL scraping and DuckDuckGo search capabilities.
Expanded search intent detection so the system automatically triggers
web search for financial queries about current events, prices, etc.
"""

import re
import httpx
from bs4 import BeautifulSoup
from typing import Optional, List, Dict
from duckduckgo_search import DDGS
import traceback


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
        print(f"[WEB_SCRAPER] Error scraping {url}: {e}")
        traceback.print_exc()
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
        print(f"[WEB_SCRAPER] Error searching web: {e}")
        traceback.print_exc()
        return []


def detect_urls(text: str) -> List[str]:
    """Extract URLs from text."""
    url_pattern = re.compile(
        r'https?://[^\s<>"{}|\\^`\[\]]+',
        re.IGNORECASE
    )
    return url_pattern.findall(text)


def detect_search_intent(text: str) -> bool:
    """
    Detect if the user's query would benefit from a live web search.

    This is the KEY function that determines whether the web scraper fires.
    It must be aggressive enough to catch financial queries about current
    events, prices, news, etc. — otherwise the LLM will respond with
    "I don't have access to real-time data."
    """
    text_lower = text.lower()

    # ─── Exact trigger phrases (high confidence) ────────────────────────
    exact_triggers = [
        "search for", "google", "look up", "find out",
        "what's happening", "latest news", "current price",
        "today's", "right now", "live data", "real-time",
        "search the web", "web search", "look online",
        "check online", "find online",
    ]
    if any(trigger in text_lower for trigger in exact_triggers):
        return True

    # ─── Financial current-event signals ────────────────────────────────
    # These indicate the user is asking about something that needs live data
    financial_signals = [
        # Price/market state queries
        "price of", "stock price", "share price", "market cap",
        "trading at", "currently trading", "what is .* trading",
        "how much is", "what's .* worth",
        # News / events
        "recent", "latest", "news about", "headlines",
        "just announced", "breaking", "update on",
        "earnings report", "quarterly results", "annual report",
        "ipo", "merger", "acquisition", "buyout",
        # Temporal markers that imply current data
        "today", "this week", "this month", "this quarter",
        "this year", "yesterday", "last week", "last month",
        "now", "currently", "at the moment", "right now",
        "as of", "2024", "2025", "2026",
        # Analyst / sentiment queries
        "analyst rating", "analyst target", "consensus",
        "sentiment", "what do analysts", "wall street",
        # Specific market data
        "s&p 500", "nasdaq", "dow jones", "nifty", "sensex",
        "bitcoin price", "btc price", "eth price", "crypto",
        "gold price", "oil price", "treasury yield",
        "interest rate", "fed rate", "rbi rate", "ecb rate",
        "inflation rate", "gdp growth", "unemployment",
        "forex", "usd/inr", "eur/usd",
    ]

    for signal in financial_signals:
        if re.search(signal, text_lower):
            return True

    # ─── Ticker symbol detection (e.g., $AAPL, TSLA, NVDA) ─────────────
    ticker_pattern = re.compile(r'\$?[A-Z]{2,5}\b')
    tickers = ticker_pattern.findall(text)
    # Filter common English words that look like tickers
    non_tickers = {
        "I", "A", "THE", "AND", "FOR", "WITH", "THIS", "THAT", "FROM",
        "WHAT", "WHEN", "HOW", "WHY", "WHO", "ARE", "CAN", "WILL",
        "SHOULD", "WOULD", "COULD", "NOT", "BUT", "ALL", "ALSO",
        "BEEN", "HAVE", "HAS", "HAD", "ITS", "MAY", "OUR", "NEW",
        "NOW", "USE", "GET", "LET", "PUT", "SET", "TOP", "TWO",
        "BIG", "BUY", "LOW", "HIGH", "SELL", "ETF", "GDP", "FED",
        "CEO", "CFO", "CIO", "IPO", "ESG", "AI",
    }
    real_tickers = [t.lstrip('$') for t in tickers if t.lstrip('$') not in non_tickers]
    if real_tickers:
        return True

    return False
