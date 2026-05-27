"""
Stub adapter for Lamudi México (lamudi.com.mx).

STATUS: NOT IMPLEMENTED – stub only.

Lamudi operates in multiple LATAM markets and prohibits automated scraping.
They offer a Partner/API program for professional integrations.

To implement:
1. Apply for Lamudi Partner API access at lamudi.com.mx/partner.
2. Implement `fetch_listings` with the authorized REST client.
3. Map Lamudi JSON property objects to the BaseSource schema.

Env vars expected (when implemented):
  LAMUDI_API_KEY
  LAMUDI_API_SECRET
"""

import logging
from typing import Any

from .base import BaseSource

logger = logging.getLogger(__name__)


class LamudiStub(BaseSource):
    name = "lamudi"
    base_url = "https://www.lamudi.com.mx"

    def is_available(self) -> bool:
        return False

    def fetch_listings(self, zona: str, precio_max: int, limite: int = 50) -> list[dict[str, Any]]:
        logger.warning("[lamudi] Source not implemented. See stub for details.")
        return []
