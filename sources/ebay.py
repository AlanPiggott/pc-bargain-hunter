"""
sources/ebay.py - eBay Browse API integration.

Uses OAuth2 client credentials flow. Tokens are cached in memory
and refreshed automatically when they expire.
"""

import logging
import time
from typing import Optional

import requests

from config import EBAY_RESULTS_PER_TERM

logger = logging.getLogger(__name__)

EBAY_TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
EBAY_SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"

# In-memory token cache
_token_cache: dict = {"token": None, "expires_at": 0}


def _get_access_token(app_id: str, cert_id: str) -> Optional[str]:
    """Fetch or return cached OAuth2 access token."""
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"] - 60:
        return _token_cache["token"]

    logger.info("Fetching new eBay OAuth token")
    try:
        response = requests.post(
            EBAY_TOKEN_URL,
            auth=(app_id, cert_id),
            data={
                "grant_type": "client_credentials",
                "scope": "https://api.ebay.com/oauth/api_scope",
            },
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        _token_cache["token"] = data["access_token"]
        _token_cache["expires_at"] = now + int(data.get("expires_in", 7200))
        return _token_cache["token"]
    except Exception as e:
        logger.error(f"Failed to get eBay token: {e}")
        return None


def _search_ebay(
    token: str,
    search_term: str,
    max_price: int,
    limit: int = EBAY_RESULTS_PER_TERM,
    retries: int = 3,
) -> list[dict]:
    """Search eBay for a single term. Returns list of raw listing dicts."""
    headers = {
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_AU",
    }
    params = {
        "q": search_term,
        "filter": (
            f"price:[..{max_price}],"
            "priceCurrency:AUD,"
            "itemLocationCountry:AU,"
            "buyingOptions:{FIXED_PRICE|AUCTION|BEST_OFFER},"
            "conditions:{USED|FOR_PARTS_OR_NOT_WORKING}"
        ),
        "sort": "price",
        "limit": limit,
    }

    for attempt in range(retries):
        try:
            response = requests.get(
                EBAY_SEARCH_URL,
                headers=headers,
                params=params,
                timeout=15,
            )
            if response.status_code == 429:
                wait = 2 ** attempt
                logger.warning(f"eBay rate limited, waiting {wait}s (attempt {attempt + 1})")
                time.sleep(wait)
                continue
            response.raise_for_status()
            return response.json().get("itemSummaries", [])
        except requests.exceptions.HTTPError as e:
            if attempt == retries - 1:
                logger.error(f"eBay search failed for '{search_term}': {e}")
            else:
                time.sleep(2 ** attempt)
        except Exception as e:
            logger.error(f"eBay search error for '{search_term}': {e}")
            break

    return []


def _parse_listing(item: dict) -> Optional[dict]:
    """Parse a raw eBay item summary into a normalised listing dict."""
    try:
        price_data = item.get("price", {})
        if price_data.get("currency") != "AUD":
            return None
        price = float(price_data.get("value", 0))
        if price <= 0:
            return None

        return {
            "title": item.get("title", ""),
            "price": price,
            "url": item.get("itemWebUrl", item.get("itemId", "")),
            "condition": item.get("condition", "Unknown"),
            "listed_date": item.get("itemCreationDate", ""),
            "seller": item.get("seller", {}).get("username", ""),
            "platform": "eBay",
        }
    except Exception as e:
        logger.warning(f"Failed to parse eBay listing: {e}")
        return None


def fetch_listings(app_id: str, cert_id: str, parts_wishlist: list[dict]) -> list[dict]:
    """
    Fetch listings from eBay for all parts in the wishlist.
    Returns a flat list of normalised listing dicts.
    """
    token = _get_access_token(app_id, cert_id)
    if not token:
        logger.error("Cannot fetch eBay listings: no valid token")
        return []

    all_listings: list[dict] = []

    for part in parts_wishlist:
        category = part["category"]
        max_price = part["max_price_aud"]

        for term in part["search_terms"]:
            logger.info(f"[eBay] Searching: {term} (max ${max_price})")
            raw_items = _search_ebay(token, term, max_price)

            for item in raw_items:
                listing = _parse_listing(item)
                if listing:
                    listing["category_hint"] = category
                    listing["search_term"] = term
                    all_listings.append(listing)

            # Respect eBay rate limits (free tier: 5000/day, ~5 req/s safe)
            time.sleep(0.2)

    logger.info(f"[eBay] Total listings fetched: {len(all_listings)}")
    return all_listings
