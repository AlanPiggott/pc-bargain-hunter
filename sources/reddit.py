"""
sources/reddit.py - Reddit RSS feed parser (no auth required).

Searches r/hardwareswapaustralia and r/bapcsalesaustralia for each
part's search terms via Reddit's public RSS search endpoint.
A custom User-Agent and 2-second delay between requests are used
to avoid 429 rate limits.
"""

import logging
import re
import time
from typing import Optional

import feedparser
import requests

from config import REDDIT_SUBREDDITS

logger = logging.getLogger(__name__)

REDDIT_RSS_TEMPLATE = (
    "https://www.reddit.com/r/{subreddit}/search.rss"
    "?q={query}&sort=new&restrict_sr=1&t=week"
)

HEADERS = {"User-Agent": "pc-bargain-hunter/1.0 (automated deal tracker)"}

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


def _fetch_feed(subreddit: str, search_term: str) -> list[dict]:
    """Fetch and parse the Reddit RSS feed for a subreddit + search term."""
    url = REDDIT_RSS_TEMPLATE.format(
        subreddit=subreddit,
        query=requests.utils.quote(search_term),
    )
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code == 429:
            logger.warning(f"[Reddit] Rate limited on r/{subreddit}, skipping term '{search_term}'")
            return []
        response.raise_for_status()
        feed = feedparser.parse(response.text)
        return feed.entries
    except Exception as e:
        logger.error(f"[Reddit] Failed to fetch r/{subreddit} for '{search_term}': {e}")
        return []


def _parse_entry(entry: dict, subreddit: str) -> dict:
    """Parse a feedparser entry into a normalised listing dict."""
    title = entry.get("title", "")
    link = entry.get("link", "")
    published = entry.get("published", "")
    price = _extract_price(title)

    return {
        "title": title,
        "price": price,  # may be None
        "url": link,
        "condition": "Used",  # hardware swap subreddits are typically second-hand
        "listed_date": published,
        "seller": f"Reddit/r/{subreddit}",
        "platform": "Reddit",
    }


def fetch_listings(parts_wishlist: list[dict]) -> list[dict]:
    """
    Fetch listings from Reddit for all parts and subreddits.
    Returns a flat list of normalised listing dicts.
    """
    all_listings: list[dict] = []

    for part in parts_wishlist:
        category = part["category"]

        for term in part["search_terms"]:
            for subreddit in REDDIT_SUBREDDITS:
                logger.info(f"[Reddit] Searching r/{subreddit}: {term}")
                entries = _fetch_feed(subreddit, term)

                for entry in entries:
                    listing = _parse_entry(entry, subreddit)
                    listing["category_hint"] = category
                    listing["search_term"] = term
                    all_listings.append(listing)

                time.sleep(2)  # Reddit rate limit: 2s between requests

    logger.info(f"[Reddit] Total listings fetched: {len(all_listings)}")
    return all_listings
