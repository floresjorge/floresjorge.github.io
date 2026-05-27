"""
Stub adapter for Inmuebles24 (inmuebles24.com).

STATUS: NOT IMPLEMENTED – stub only.

Why: Inmuebles24 does not provide a public API. Direct scraping
would violate their Terms of Service (robots.txt disallows crawlers).
This stub defines the interface so a proper implementation can be
added once a legitimate data access method is available (e.g. an
official API partnership, a licensed data feed, or manual export).

To implement:
1. Obtain authorized access (API key, data partnership, etc.)
2. Replace `fetch_listings` with the real HTTP client logic.
3. Map Inmuebles24 JSON fields to the BaseSource schema.
4. Set `is_available()` to check the API key env var.

Env vars expected (when implemented):
  INMUEBLES24_API_KEY  – API key for the data feed
"""

import logging
import os
from typing import Any

from .base import BaseSource

logger = logging.getLogger(__name__)


class Inmuebles24Stub(BaseSource):
    name = "inmuebles24"
    base_url = "https://www.inmuebles24.com"

    def is_available(self) -> bool:
        key = os.getenv("INMUEBLES24_API_KEY", "")
        if not key:
            logger.debug("[inmuebles24] No API key set; source unavailable")
        return False  # always False until implemented

    def fetch_listings(
        self,
        zona: str,
        precio_max: int,
        limite: int = 50,
    ) -> list[dict[str, Any]]:
        logger.warning(
            "[inmuebles24] Source not implemented. "
            "See src/sources/inmuebles24_stub.py for details."
        )
        return []
