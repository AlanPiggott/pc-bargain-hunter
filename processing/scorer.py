"""
processing/scorer.py - Price scoring and deal rating.

Matches each listing to a wishlist category by checking if any of
the category's search terms appear in the listing title. Calculates
discount percentage relative to max_price and assigns deal ratings.
"""

import logging

logger = logging.getLogger(__name__)


def _match_category(title: str, parts_wishlist: list[dict]) -> dict | None:
    """
    Find the first wishlist entry whose search terms appear in the title.
    Returns the matching part dict or None.
    """
    title_lower = title.lower()
    for part in parts_wishlist:
        for term in part["search_terms"]:
            if term.lower() in title_lower:
                return part
    return None


def _deal_rating(price: float, part: dict) -> str:
    """Return 'hot', 'good', 'ok', or None (above max price)."""
    if price <= part["hot_deal_price_aud"]:
        return "hot"
    if price <= part["target_price_aud"]:
        return "good"
    if price <= part["max_price_aud"]:
        return "ok"
    return None


def score_listings(listings: list[dict], parts_wishlist: list[dict]) -> list[dict]:
    """
    Score each listing against the wishlist.

    Adds to each listing dict:
      - category: matched category name
      - target_price: the target_price_aud from the matched part
      - max_price: the max_price_aud from the matched part
      - discount_pct: how far below max_price the listing is (float)
      - deal_rating: "hot" | "good" | "ok"
      - is_hot_deal: bool

    Listings with no price, no category match, or above max price are dropped.
    Results are sorted by discount_pct descending.
    """
    scored = []

    for listing in listings:
        price = listing.get("price")
        title = listing.get("title", "")

        if price is None:
            continue  # no price extracted, skip scoring

        # Try the category_hint first (set by the source fetcher), then
        # fall back to a full text match across all wishlist entries.
        hint = listing.get("category_hint")
        part = None
        if hint:
            part = next((p for p in parts_wishlist if p["category"] == hint), None)
        if part is None:
            part = _match_category(title, parts_wishlist)

        if part is None:
            logger.debug(f"No category match for: {title[:60]}")
            continue

        rating = _deal_rating(price, part)
        if rating is None:
            logger.debug(f"Above max price (${price}): {title[:60]}")
            continue

        discount_pct = (part["max_price_aud"] - price) / part["max_price_aud"] * 100

        scored_listing = {
            **listing,
            "category": part["category"],
            "target_price": part["target_price_aud"],
            "max_price": part["max_price_aud"],
            "discount_pct": round(discount_pct, 1),
            "deal_rating": rating,
            "is_hot_deal": rating == "hot",
        }
        scored.append(scored_listing)

    scored.sort(key=lambda x: x["discount_pct"], reverse=True)
    logger.info(
        f"Scorer: {len(scored)} deals found "
        f"({sum(1 for l in scored if l['is_hot_deal'])} hot, "
        f"{sum(1 for l in scored if l['deal_rating'] == 'good')} good, "
        f"{sum(1 for l in scored if l['deal_rating'] == 'ok')} ok)"
    )
    return scored
