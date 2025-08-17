from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Union
from urllib.parse import quote_plus

import requests
from fastmcp import FastMCP

from utils.const import MCPToolsTags

# JSON-like return type without recursive self-references (pydantic-friendly)
JSONValue = Union[None, bool, int, float, str, List[Any], Dict[str, Any]]
NewsItems = List[Dict[str, str]]


def _text(el: ET.Element | None) -> str:
    return (el.text or "").strip() if el is not None else ""


def _fetch_google_news_rss(query: str, max_items: int = 5) -> NewsItems:
    """Fetch news items from Google News RSS for a given query.

    Returns a list of dicts with keys: title, link, published.
    """
    url = (
        "https://news.google.com/rss/search?q="
        + quote_plus(query)
        + "&hl=en-US&gl=US&ceid=US:en"
    )
    response = requests.get(url, timeout=15)
    response.raise_for_status()

    root = ET.fromstring(response.content)
    channel = root.find("channel")
    if channel is None:
        return []

    items: List[Dict[str, str]] = []
    for item in channel.findall("item")[:max_items]:
        title_el = item.find("title")
        link_el = item.find("link")
        pub_el = item.find("pubDate")
        items.append(
            {
                "title": _text(title_el),
                "link": _text(link_el),
                "published": _text(pub_el),
            }
        )
    return items


def _fetch_yahoo_news_rss(query: str, max_items: int = 5) -> NewsItems:
    """Fetch news items from Yahoo News RSS search for a given query.

    Returns a list of dicts with keys: title, link, published.
    """
    url = "https://news.search.yahoo.com/rss?p=" + quote_plus(query)
    response = requests.get(url, timeout=15)
    response.raise_for_status()

    root = ET.fromstring(response.content)
    channel = root.find("channel")
    if channel is None:
        return []

    items: List[Dict[str, str]] = []
    for item in channel.findall("item")[:max_items]:
        title_el = item.find("title")
        link_el = item.find("link")
        pub_el = item.find("pubDate")
        items.append(
            {
                "title": _text(title_el),
                "link": _text(link_el),
                "published": _text(pub_el),
            }
        )
    return items


def _format_items_as_bullets(items: List[Dict[str, str]]) -> str:
    lines: List[str] = []
    for itm in items:
        title = itm.get("title", "").strip()
        link = itm.get("link", "").strip()
        published = itm.get("published", "").strip()
        if title or link:
            if published:
                lines.append(f"- {title} ({published})\n  {link}")
            else:
                lines.append(f"- {title}\n  {link}")
    return "\n".join(lines)


def register_external_tools(mcp: FastMCP) -> None:
    """Register external tools like news scraping.

    Tools:
      - scrape_stock_news_summaries(keywords: list[str]) -> dict[str, str]
        Returns a mapping of provider name to a single formatted string
        containing bullet-pointed news items (title and link) for each
        provider.
    """

    @mcp.tool(
        name="scrape_stock_news_summaries",
        description=(
            "Aggregate recent stock news snippets from multiple public "
            "providers for the given keywords. Providers include: "
            "google_news, yahoo_news, moneycontrol, "
            "economic_times_markets, business_standard_markets. "
            "Returns a dict mapping provider->content string."
        ),
        tags=[MCPToolsTags.INDIAN_EXCHANGE.value],
    )
    def scrape_stock_news_summaries(keywords: List[str]) -> JSONValue:
        """Fetch news from multiple providers for the given keywords.

        Args:
          keywords: List of search terms, e.g., ["TCS", "results"].

        Returns:
          dict[str, str]: Mapping of provider to text block with
          bullet-pointed headlines and links.
        """

        if not isinstance(keywords, list) or not all(
            isinstance(k, str) and k.strip() for k in keywords
        ):
            raise ValueError(
                "keywords must be a non-empty list of " "non-empty strings"
            )

        query = " ".join(k.strip() for k in keywords)

        providers: Dict[str, str] = {}

        try:
            google_items = _fetch_google_news_rss(query)
            providers["google_news"] = (
                _format_items_as_bullets(google_items) or "No results"
            )
        except Exception as exc:  # noqa: BLE001 - provider-specific failure
            providers["google_news"] = f"Error: {exc}"

        try:
            yahoo_items = _fetch_yahoo_news_rss(query)
            providers["yahoo_news"] = (
                _format_items_as_bullets(yahoo_items) or "No results"
            )
        except Exception as exc:  # noqa: BLE001
            providers["yahoo_news"] = f"Error: {exc}"

        # Site-filtered Google News queries for specific Indian markets sites
        try:
            mc_items = _fetch_google_news_rss(f"{query} site:moneycontrol.com")
            providers["moneycontrol"] = (
                _format_items_as_bullets(mc_items) or "No results"
            )
        except Exception as exc:  # noqa: BLE001
            providers["moneycontrol"] = f"Error: {exc}"

        try:
            et_items = _fetch_google_news_rss(
                f"{query} site:economictimes.indiatimes.com/markets"
            )
            providers["economic_times_markets"] = (
                _format_items_as_bullets(et_items) or "No results"
            )
        except Exception as exc:  # noqa: BLE001
            providers["economic_times_markets"] = f"Error: {exc}"

        try:
            bs_items = _fetch_google_news_rss(
                f"{query} site:business-standard.com/markets"
            )
            providers["business_standard_markets"] = (
                _format_items_as_bullets(bs_items) or "No results"
            )
        except Exception as exc:  # noqa: BLE001
            providers["business_standard_markets"] = f"Error: {exc}"

        return providers
