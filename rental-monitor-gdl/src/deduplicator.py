"""Deduplication logic: by canonical URL and by fuzzy title+price+zone similarity."""

import re
import logging
from typing import Any

from .parsers import normalize_text, canonicalize_url

logger = logging.getLogger(__name__)


def _title_fingerprint(title: str | None, price: int | None, zona: str | None) -> str:
    """Create a rough fingerprint for fuzzy deduplication."""
    norm_title = normalize_text(title or "")
    # Keep only alphanumeric tokens
    tokens = re.findall(r"[a-z0-9]{3,}", norm_title)
    # Use first 6 meaningful tokens + price bucket + zone
    price_bucket = str((price or 0) // 500 * 500)
    zone_key = normalize_text(zona or "")[:20]
    return "_".join(tokens[:6]) + "__" + price_bucket + "__" + zone_key


def deduplicate(listings: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """
    Remove duplicate listings.
    Deduplication pass 1: by url_canonica.
    Deduplication pass 2: by title fingerprint (title tokens + price bucket + zone).

    Returns (deduplicated_list, count_removed).
    """
    seen_urls: set[str] = set()
    seen_fingerprints: set[str] = set()
    result: list[dict[str, Any]] = []
    removed = 0

    for listing in listings:
        url = listing.get("url_canonica") or canonicalize_url(listing.get("url"))
        if url and url in seen_urls:
            logger.debug("Duplicate URL removed: %s", url)
            removed += 1
            continue
        if url:
            seen_urls.add(url)

        fp = _title_fingerprint(
            listing.get("titulo"),
            listing.get("precio_mensual"),
            listing.get("zona"),
        )
        if fp in seen_fingerprints:
            logger.debug("Fuzzy duplicate removed (fingerprint=%s)", fp)
            removed += 1
            continue
        seen_fingerprints.add(fp)

        result.append(listing)

    if removed:
        logger.info("Deduplication: removed %d duplicate(s), kept %d", removed, len(result))
    return result, removed
