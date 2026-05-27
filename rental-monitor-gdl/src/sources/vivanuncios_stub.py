"""
Stub adapter for Vivanuncios (vivanuncios.com.mx).

STATUS: NOT IMPLEMENTED – stub only.

Vivanuncios is one of the largest real estate portals in Mexico.
Direct scraping is prohibited by their ToS and robots.txt.
This stub defines the interface pending an authorized data access method.

To implement:
1. Obtain a data partnership or API license from Vivanuncios / REA Group.
2. Implement `fetch_listings` using the authorized endpoint.
3. Map response fields to the BaseSource schema.

Env vars expected (when implemented):
  VIVANUNCIOS_API_KEY
"""

import logging
import os
from typing import Any

from .base import BaseSource

logger = logging.getLogger(__name__)


class VivanunciosStub(BaseSource):
    name = "vivanuncios"
    base_url = "https://www.vivanuncios.com.mx"

    def is_available(self) -> bool:
        return False  # always False until implemented

    def fetch_listings(self, zona: str, precio_max: int, limite: int = 50) -> list[dict[str, Any]]:
        logger.warning("[vivanuncios] Source not implemented. See stub for details.")
        return []
