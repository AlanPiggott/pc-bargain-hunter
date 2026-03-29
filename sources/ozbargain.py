"""
sources/ozbargain.py - OzBargain RSS feed parser.

Searches OzBargain's public RSS feed for each part's search terms.
Prices are extracted from post titles using regex — OzBargain titles
usually include "$XX" or "$XX.XX".
"""

import logging
import re
import time
from typing import Optional

import feedparser
import requests

logger = logging.getLogger(__name__)

OZBARGAIN_RSS_URL = "https://www.ozbargain.com.au/deals/feed"

# Matches "$150", "$1,499", "$49.99", "AUD 50", etc.
PRICE_REGEX = re.compile(
    r"(?:AUD\s*|\$)\s*(\d{1,5}(?:,\d{3})*(?:\.\d{1,2})?)",
    re.IGNORECASE,
)


def _extract_price(text: str) -> Optional[float]:
    """Try to pull a dollar amount from a string. Returns None if not found."""
    match = PRICE_REGEX.search(text)
    if match:
        return float(match.group(1).replace(",", ""))
    return None


def _fetch_feed(search_term: str) -> list[dict]:
    """Fetch and parse the OzBargain RSS feed for a search term."""
    try:
        url = OZBARGAIN_RSS_URL
        params = {"q": search_term}
        # feedparser can fetch directly but doesn't pass params cleanly,
        # so we build the URL manually.
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        feed = feedparser.parse(response.text)
        return feed.entries
    except Exception as e:
        logger.error(f"[OzBargain] Failed to fetch feed for '{search_term}': {e}")
        return []


def _parse_entry(entry: dict) -> dict:
    """Parse a feedparser entry into a normalised listing dict."""
    title = entry.get("title", "")
    link = entry.get("link", "")
    published = entry.get("published", "")
    price = _extract_price(title)

    return {
        "title": title,
        "price": price,  # may be None
        "url": link,
        "condition": "New",  # OzBargain is typically new deals
        "listed_date": published,
        "seller": "OzBargain",
        "platform": "OzBargain",
    }


def fetch_listings(parts_wishlist: list[dict]) -> list[dict]:
    """
    Fetch listings from OzBargain for all parts in the wishlist.
    Returns a flat list of normalised listing dicts.
    """
    all_listings: list[dict] = []

    for part in parts_wishlist:
        category = part["category"]

        for term in part["search_terms"]:
            logger.info(f"[OzBargain] Searching: {term}")
            entries = _fetch_feed(term)

            for entry in entries:
                listing = _parse_entry(entry)
                listing["category_hint"] = category
                listing["search_term"] = term
                all_listings.append(listing)

            time.sleep(1)  # polite crawl delay

    logger.info(f"[OzBargain] Total listings fetched: {len(all_listings)}")
    return all_listings
