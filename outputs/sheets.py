"""
outputs/sheets.py - Google Sheets integration via gspread.

Appends new listings to the "Listings" tab, overwrites "Summary"
each run, and appends price trend rows to "Price Trends".

The service account JSON is passed as a base64-encoded string
(from the GOOGLE_SHEETS_CREDENTIALS env var).
"""

import base64
import json
import logging
from collections import defaultdict
from datetime import date

import gspread
from google.oauth2.service_account import Credentials

from config import LISTINGS_TAB, SPREADSHEET_NAME, SUMMARY_TAB, TRENDS_TAB

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

LISTINGS_HEADERS = [
    "Date Found",
    "Category",
    "Title",
    "Price (AUD)",
    "Target Price",
    "Discount %",
    "Deal Rating",
    "Platform",
    "URL",
    "Status",
]

SUMMARY_HEADERS = [
    "Category",
    "New Listings",
    "Hot Deals",
    "Best Price Today",
]

TRENDS_HEADERS = [
    "Date",
    "Category",
    "Lowest Price",
    "Avg Price",
    "Num Listings",
]


def _build_client(credentials_b64: str) -> gspread.Client:
    """Build a gspread client from a base64-encoded service account JSON."""
    creds_json = json.loads(base64.b64decode(credentials_b64))
    creds = Credentials.from_service_account_info(creds_json, scopes=SCOPES)
    return gspread.authorize(creds)


def _ensure_tab(spreadsheet, tab_name: str, headers: list[str]):
    """Return the worksheet, creating it with headers if it doesn't exist."""
    try:
        ws = spreadsheet.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(tab_name, rows=1000, cols=len(headers))
        ws.append_row(headers)
        logger.info(f"Created tab '{tab_name}'")
    return ws


def write_listings(credentials_b64: str, scored_listings: list[dict]) -> None:
    """Append new scored listings to the Listings tab."""
    if not scored_listings:
        logger.info("[Sheets] No new listings to write")
        return

    try:
        client = _build_client(credentials_b64)
        spreadsheet = client.open(SPREADSHEET_NAME)
        ws = _ensure_tab(spreadsheet, LISTINGS_TAB, LISTINGS_HEADERS)

        today = date.today().isoformat()
        rows = []
        for listing in scored_listings:
            rows.append([
                today,
                listing.get("category", ""),
                listing.get("title", ""),
                listing.get("price", ""),
                listing.get("target_price", ""),
                listing.get("discount_pct", ""),
                listing.get("deal_rating", "").upper(),
                listing.get("platform", ""),
                listing.get("url", ""),
                "New",
            ])

        ws.append_rows(rows, value_input_option="USER_ENTERED")
        logger.info(f"[Sheets] Appended {len(rows)} rows to '{LISTINGS_TAB}'")

    except Exception as e:
        logger.error(f"[Sheets] Failed to write listings: {e}")
        raise


def write_summary(credentials_b64: str, scored_listings: list[dict]) -> None:
    """Overwrite the Summary tab with a per-category summary for this run."""
    try:
        client = _build_client(credentials_b64)
        spreadsheet = client.open(SPREADSHEET_NAME)
        ws = _ensure_tab(spreadsheet, SUMMARY_TAB, SUMMARY_HEADERS)

        # Aggregate per category
        stats: dict[str, dict] = defaultdict(lambda: {
            "count": 0, "hot": 0, "prices": []
        })
        for listing in scored_listings:
            cat = listing.get("category", "Unknown")
            stats[cat]["count"] += 1
            if listing.get("is_hot_deal"):
                stats[cat]["hot"] += 1
            price = listing.get("price")
            if price is not None:
                stats[cat]["prices"].append(price)

        rows = [SUMMARY_HEADERS]
        for cat, data in sorted(stats.items()):
            best_price = min(data["prices"]) if data["prices"] else "N/A"
            rows.append([cat, data["count"], data["hot"], best_price])

        # Overwrite entire tab
        ws.clear()
        ws.update(range_name="A1", values=rows, value_input_option="USER_ENTERED")
        logger.info(f"[Sheets] Updated '{SUMMARY_TAB}' with {len(rows) - 1} categories")

    except Exception as e:
        logger.error(f"[Sheets] Failed to write summary: {e}")
        raise


def write_price_trends(credentials_b64: str, scored_listings: list[dict]) -> None:
    """Append one row per category to the Price Trends tab."""
    try:
        client = _build_client(credentials_b64)
        spreadsheet = client.open(SPREADSHEET_NAME)
        ws = _ensure_tab(spreadsheet, TRENDS_TAB, TRENDS_HEADERS)

        today = date.today().isoformat()
        stats: dict[str, list[float]] = defaultdict(list)
        for listing in scored_listings:
            price = listing.get("price")
            if price is not None:
                stats[listing.get("category", "Unknown")].append(price)

        rows = []
        for cat, prices in sorted(stats.items()):
            rows.append([
                today,
                cat,
                min(prices),
                round(sum(prices) / len(prices), 2),
                len(prices),
            ])

        if rows:
            ws.append_rows(rows, value_input_option="USER_ENTERED")
            logger.info(f"[Sheets] Appended {len(rows)} trend rows to '{TRENDS_TAB}'")

    except Exception as e:
        logger.error(f"[Sheets] Failed to write price trends: {e}")
        raise


def write_all(credentials_b64: str, scored_listings: list[dict]) -> None:
    """Write listings, summary, and price trends. Falls back to results.json on failure."""
    import json as _json

    try:
        write_listings(credentials_b64, scored_listings)
        write_summary(credentials_b64, scored_listings)
        write_price_trends(credentials_b64, scored_listings)
    except Exception as e:
        logger.error(f"[Sheets] Google Sheets write failed, falling back to results.json: {e}")
        try:
            with open("results.json", "w") as f:
                _json.dump(scored_listings, f, indent=2, default=str)
            logger.info("Fallback: wrote results to results.json")
        except Exception as fe:
            logger.error(f"Fallback results.json write also failed: {fe}")
