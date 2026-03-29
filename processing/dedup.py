"""
processing/dedup.py - URL-based deduplication using a JSON file.

Seen listings are stored as SHA256(url) -> date_first_seen in
seen_listings.json. The file is read once at startup and written
once at the end of each run. Entries older than 30 days are pruned.
"""

import hashlib
import json
import logging
from datetime import date, timedelta
from pathlib import Path

from config import SEEN_LISTINGS_FILE, SEEN_LISTINGS_MAX_AGE_DAYS

logger = logging.getLogger(__name__)


class DedupTracker:
    def __init__(self, filepath: str = SEEN_LISTINGS_FILE):
        self.filepath = Path(filepath)
        self._seen: dict[str, str] = {}  # hash -> date string "YYYY-MM-DD"
        self._load()

    def _load(self) -> None:
        """Load the seen listings file from disk."""
        if self.filepath.exists():
            try:
                self._seen = json.loads(self.filepath.read_text())
                logger.info(f"Loaded {len(self._seen)} seen listing hashes from {self.filepath}")
            except Exception as e:
                logger.warning(f"Could not read {self.filepath}, starting fresh: {e}")
                self._seen = {}
        else:
            logger.info(f"{self.filepath} not found, starting with empty dedup store")
            self._seen = {}

    def _hash(self, url: str) -> str:
        return hashlib.sha256(url.encode()).hexdigest()

    def is_seen(self, url: str) -> bool:
        """Return True if this URL has been seen before."""
        return self._hash(url) in self._seen

    def mark_seen(self, url: str) -> None:
        """Record a URL as seen today."""
        self._seen[self._hash(url)] = date.today().isoformat()

    def filter_new(self, listings: list[dict]) -> list[dict]:
        """
        Return only listings whose URLs haven't been seen before,
        and mark them as seen.
        """
        new_listings = []
        for listing in listings:
            url = listing.get("url", "")
            if not url:
                continue
            if not self.is_seen(url):
                self.mark_seen(url)
                new_listings.append(listing)
        logger.info(
            f"Dedup: {len(listings)} total, {len(new_listings)} new, "
            f"{len(listings) - len(new_listings)} duplicates skipped"
        )
        return new_listings

    def _prune_old_entries(self) -> None:
        """Remove entries older than SEEN_LISTINGS_MAX_AGE_DAYS."""
        cutoff = (date.today() - timedelta(days=SEEN_LISTINGS_MAX_AGE_DAYS)).isoformat()
        before = len(self._seen)
        self._seen = {k: v for k, v in self._seen.items() if v >= cutoff}
        pruned = before - len(self._seen)
        if pruned:
            logger.info(f"Pruned {pruned} old entries from dedup store")

    def save(self) -> None:
        """Prune old entries and write the dedup store back to disk."""
        self._prune_old_entries()
        try:
            self.filepath.write_text(json.dumps(self._seen, indent=2))
            logger.info(f"Saved {len(self._seen)} hashes to {self.filepath}")
        except Exception as e:
            logger.error(f"Failed to save dedup store: {e}")
