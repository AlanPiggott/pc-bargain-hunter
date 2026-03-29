"""
main.py - Orchestrator for the PC Bargain Hunter.

Run order:
  1. Fetch listings from all sources (eBay, OzBargain, Reddit)
  2. Deduplicate against seen_listings.json
  3. Score and filter by price targets
  4. Write results to Google Sheets
  5. Send WhatsApp alerts for hot deals
  6. Save updated seen_listings.json

Each source failure is caught and logged — the run continues with
the remaining sources regardless.
"""

import logging
import os
import sys

from dotenv import load_dotenv

# Load .env for local development; no-op if the file doesn't exist.
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def main() -> None:
    # ------------------------------------------------------------------ config
    from config import PARTS_WISHLIST

    ebay_app_id = os.environ.get("EBAY_APP_ID", "")
    ebay_cert_id = os.environ.get("EBAY_CERT_ID", "")
    sheets_credentials = os.environ.get("GOOGLE_SHEETS_CREDENTIALS", "")
    whatsapp_phone = os.environ.get("WHATSAPP_PHONE", "")
    callmebot_api_key = os.environ.get("CALLMEBOT_API_KEY", "")

    # ------------------------------------------------------------------ dedup
    from processing.dedup import DedupTracker
    dedup = DedupTracker()

    # ------------------------------------------------------------------ fetch
    all_raw: list[dict] = []

    # eBay
    if ebay_app_id and ebay_cert_id:
        try:
            from sources.ebay import fetch_listings as ebay_fetch
            ebay_listings = ebay_fetch(ebay_app_id, ebay_cert_id, PARTS_WISHLIST)
            all_raw.extend(ebay_listings)
            logger.info(f"eBay: {len(ebay_listings)} listings fetched")
        except Exception as e:
            logger.error(f"eBay source failed: {e}")
    else:
        logger.warning("EBAY_APP_ID / EBAY_CERT_ID not set, skipping eBay")

    # OzBargain
    try:
        from sources.ozbargain import fetch_listings as oz_fetch
        oz_listings = oz_fetch(PARTS_WISHLIST)
        all_raw.extend(oz_listings)
        logger.info(f"OzBargain: {len(oz_listings)} listings fetched")
    except Exception as e:
        logger.error(f"OzBargain source failed: {e}")

    # Reddit
    try:
        from sources.reddit import fetch_listings as reddit_fetch
        reddit_listings = reddit_fetch(PARTS_WISHLIST)
        all_raw.extend(reddit_listings)
        logger.info(f"Reddit: {len(reddit_listings)} listings fetched")
    except Exception as e:
        logger.error(f"Reddit source failed: {e}")

    logger.info(f"Total raw listings: {len(all_raw)}")

    # ------------------------------------------------------------------ dedup
    new_listings = dedup.filter_new(all_raw)
    logger.info(f"New (unseen) listings: {len(new_listings)}")

    # ------------------------------------------------------------------ score
    from processing.scorer import score_listings
    scored = score_listings(new_listings, PARTS_WISHLIST)
    logger.info(f"Scored deals: {len(scored)}")

    # ------------------------------------------------------------------ output
    if sheets_credentials:
        from outputs.sheets import write_all
        write_all(sheets_credentials, scored)
    else:
        logger.warning("GOOGLE_SHEETS_CREDENTIALS not set, skipping Sheets output")
        # Still write to results.json as a local fallback
        import json
        with open("results.json", "w") as f:
            json.dump(scored, f, indent=2, default=str)
        logger.info("Wrote results to results.json (no Sheets credentials)")

    # ----------------------------------------------------------------- alerts
    if whatsapp_phone and callmebot_api_key:
        from outputs.whatsapp import send_alerts
        send_alerts(whatsapp_phone, callmebot_api_key, scored)
    else:
        logger.warning("WhatsApp env vars not set, skipping alerts")

    # ------------------------------------------------------------------- save
    dedup.save()
    logger.info("Run complete.")


if __name__ == "__main__":
    main()
