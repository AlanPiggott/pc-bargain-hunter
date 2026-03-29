"""
outputs/whatsapp.py - WhatsApp alerts via CallMeBot (free tier).

Sends hot deal alerts and a daily summary via CallMeBot's GET API.
Rate limited to one message every 3 seconds. Non-200 responses are
logged and silently dropped — WhatsApp is nice-to-have, not critical.
"""

import logging
import time
import requests

from config import CALLMEBOT_DELAY_SECONDS, MAX_HOT_DEAL_ALERTS

logger = logging.getLogger(__name__)

CALLMEBOT_URL = "https://api.callmebot.com/whatsapp.php"


def _send_message(phone: str, api_key: str, text: str) -> bool:
    """Send a single WhatsApp message via CallMeBot. Returns True on success."""
    try:
        params = {
            "phone": phone,
            "text": text,
            "apikey": api_key,
        }
        response = requests.get(CALLMEBOT_URL, params=params, timeout=15)
        if response.status_code != 200:
            logger.error(
                f"[WhatsApp] CallMeBot returned {response.status_code}: {response.text[:200]}"
            )
            return False
        return True
    except Exception as e:
        logger.error(f"[WhatsApp] Failed to send message: {e}")
        return False


def send_hot_deal_alerts(phone: str, api_key: str, hot_deals: list[dict]) -> None:
    """
    Send an alert for each hot deal, up to MAX_HOT_DEAL_ALERTS.
    Deals are assumed to be pre-sorted by discount_pct descending.
    """
    if not hot_deals:
        return

    to_alert = hot_deals[:MAX_HOT_DEAL_ALERTS]
    skipped = len(hot_deals) - len(to_alert)

    for deal in to_alert:
        message = (
            f"🔥 HOT DEAL: {deal.get('category', 'Unknown')}\n"
            f"{deal.get('title', '')}\n"
            f"💰 ${deal.get('price')} "
            f"(target was ${deal.get('target_price')} — "
            f"{deal.get('discount_pct')}% below max)\n"
            f"🔗 {deal.get('url', '')}"
        )
        success = _send_message(phone, api_key, message)
        if success:
            logger.info(f"[WhatsApp] Sent hot deal alert: {deal.get('title', '')[:50]}")
        time.sleep(CALLMEBOT_DELAY_SECONDS)

    if skipped > 0:
        logger.info(f"[WhatsApp] {skipped} additional hot deals not alerted (cap reached)")


def send_daily_summary(
    phone: str,
    api_key: str,
    all_listings: list[dict],
    hot_deals: list[dict],
    extra_hot_count: int = 0,
) -> None:
    """Send a summary message at the end of each run."""
    good_deals = [l for l in all_listings if l.get("deal_rating") == "good"]
    best = all_listings[0] if all_listings else None

    best_line = ""
    if best:
        best_line = f"\nBest find: {best.get('title', '')[:50]} at ${best.get('price')}"

    extra_line = ""
    if extra_hot_count > 0:
        extra_line = f"\n(+{extra_hot_count} more hot deals not individually alerted)"

    message = (
        f"📊 Bargain Hunter Summary\n"
        f"Found {len(all_listings)} new listings today\n"
        f"{len(hot_deals)} hot deals, {len(good_deals)} good deals"
        f"{best_line}"
        f"{extra_line}"
    )

    success = _send_message(phone, api_key, message)
    if success:
        logger.info("[WhatsApp] Sent daily summary")
    time.sleep(CALLMEBOT_DELAY_SECONDS)


def send_alerts(phone: str, api_key: str, scored_listings: list[dict]) -> None:
    """Send all hot deal alerts and the daily summary."""
    if not phone or not api_key:
        logger.warning("[WhatsApp] WHATSAPP_PHONE or CALLMEBOT_API_KEY not set, skipping alerts")
        return

    hot_deals = [l for l in scored_listings if l.get("is_hot_deal")]
    extra_hot_count = max(0, len(hot_deals) - MAX_HOT_DEAL_ALERTS)

    send_hot_deal_alerts(phone, api_key, hot_deals)
    send_daily_summary(phone, api_key, scored_listings, hot_deals, extra_hot_count)
