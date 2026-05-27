"""
Mercado Libre API source for Guadalajara rental listings.

Uses the public REST API — no API key, no payment required.
API docs: https://developers.mercadolibre.com.mx/es_ar/items-y-busquedas

Endpoints used:
  Search:      GET https://api.mercadolibre.com/sites/MLM/search
  Item detail: GET https://api.mercadolibre.com/items/{id}
  Description: GET https://api.mercadolibre.com/items/{id}/description

Rate limits: ~100 req/min unauthenticated. We sleep 0.35s between item fetches.
Pagination:  ML returns max 50 results per page; we loop until limite is reached.
"""

import logging
import time
from datetime import date
from typing import Any

import requests
from tenacity import (
    retry, stop_after_attempt, wait_exponential, retry_if_exception_type,
)

from .base import BaseSource
from ..parsers import (
    canonicalize_url, parse_pets_policy, parse_rental_requirements,
    normalize_text, geocode_listing,
)

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://api.mercadolibre.com/sites/MLM/search"
_ITEM_URL   = "https://api.mercadolibre.com/items/{}"
_DESC_URL   = "https://api.mercadolibre.com/items/{}/description"

_HEADERS = {"User-Agent": "rental-monitor-gdl/1.0 (personal, non-commercial)"}

# Attribute IDs → our schema field names
_ATTR_MAP: dict[str, str] = {
    "BEDROOMS":       "recamaras",
    "FULL_BATHROOMS": "banos",
    "BATHROOMS":      "banos",
    "PARKING_LOTS":   "estacionamientos",
    "TOTAL_AREA":     "metros_cuadrados",
    "COVERED_AREA":   "metros_cuadrados",  # fallback when TOTAL_AREA absent
}

# ML property type name → our tipo
_TYPE_MAP: dict[str, str] = {
    "casa":            "Casa",
    "departamento":    "Departamento",
    "apartamento":     "Departamento",
    "ph":              "Departamento",
    "penthouse":       "Departamento",
    "local comercial": "Otro",
    "oficina":         "Otro",
    "bodega":          "Otro",
    "terreno":         "Otro",
    "rancho":          "Otro",
}

_ZONE_PRIORITY: dict[str, int] = {
    "centro": 10, "analco": 9, "mexicaltzingo": 9,
    "santa tere": 8, "santa teresa": 8, "sagrada familia": 8,
    "artesanos": 7, "morelos": 7, "americana": 6,
    "chapalita": 5, "providencia": 5,
    "zapopan": 4, "tlaquepaque": 3,
}

# Delay between individual item API calls (be respectful)
_ITEM_DELAY = 0.35
_PAGE_DELAY = 0.6


class MercadoLibreSource(BaseSource):
    name = "mercadolibre"
    base_url = "https://api.mercadolibre.com"

    def is_available(self) -> bool:
        return True  # public API, no key required

    def fetch_listings(
        self,
        zona: str,
        precio_max: int,
        limite: int = 50,
    ) -> list[dict[str, Any]]:
        logger.info("[ml] Searching rentals — zona=%s, max=$%d, limite=%d", zona, precio_max, limite)

        raw = self._search_all(zona, precio_max, limite)
        logger.info("[ml] %d items from search", len(raw))

        results: list[dict[str, Any]] = []
        today = str(date.today())

        for item in raw:
            try:
                listing = self._build_listing(item, today)
                if listing is not None:
                    results.append(listing)
            except Exception as exc:
                logger.warning("[ml] Skipped %s: %s", item.get("id", "?"), exc)
            time.sleep(_ITEM_DELAY)

        logger.info("[ml] Returning %d listings after processing", len(results))
        return results

    # ── Search (with pagination) ───────────────────────────────
    def _search_all(self, zona: str, precio_max: int, limite: int) -> list[dict]:
        zone_norm = normalize_text(zona)
        if "centro" in zone_norm:
            query = "en renta guadalajara centro"
        else:
            query = f"en renta {zona}"

        items: list[dict] = []
        offset = 0

        while len(items) < limite:
            batch_size = min(50, limite - len(items))
            params = {
                "q":         query,
                "category":  "MLM1459",   # Inmuebles
                "state_id":  "MX-JAL",
                "price_max": precio_max,
                "limit":     batch_size,
                "offset":    offset,
                "sort":      "relevance",
            }
            try:
                data = self._get(_SEARCH_URL, params=params)
            except Exception as exc:
                logger.error("[ml] Search page offset=%d failed: %s", offset, exc)
                break

            batch = data.get("results", [])
            if not batch:
                break

            items.extend(batch)
            paging = data.get("paging", {})
            offset += len(batch)

            if offset >= paging.get("total", 0):
                break

            time.sleep(_PAGE_DELAY)

        return items[:limite]

    # ── Build single listing ───────────────────────────────────
    def _build_listing(self, item: dict, today: str) -> dict[str, Any] | None:
        item_id = item.get("id", "")

        # Fetch full detail and description (both optional — graceful fallback)
        detail   = self._fetch_item(item_id)
        desc_raw = self._fetch_description(item_id)

        listing = self._default_listing()
        extracted: set[str] = set()

        # ── IDs & meta ──
        listing["id"]               = f"ml-{item_id}"
        listing["fuente"]           = "mercadolibre"
        listing["fecha_extraccion"] = today

        # ── Title & price ──
        listing["titulo"]         = item.get("title") or (detail or {}).get("title", "")
        listing["precio_mensual"] = item.get("price")  # None = "consultar precio"
        listing["moneda"]         = item.get("currency_id", "MXN")

        # ── URL ──
        listing["url"]          = item.get("permalink") or (detail or {}).get("permalink", "")
        listing["url_canonica"] = canonicalize_url(listing["url"])

        # ── Publication date ──
        date_str = (detail or item).get("date_created", "")
        if date_str:
            listing["fecha_publicacion"] = date_str[:10]

        # ── Attributes ──
        attrs = (detail or item).get("attributes", [])
        for attr in attrs:
            aid = attr.get("id", "")
            # Try value_name (string), then value_struct.number (numeric)
            val = attr.get("value_name") or (attr.get("value_struct") or {}).get("number")
            if val is None:
                continue

            dest = _ATTR_MAP.get(aid)
            if dest and dest not in extracted:
                try:
                    listing[dest] = int(float(str(val))) if dest != "metros_cuadrados" else float(str(val))
                    extracted.add(dest)
                except (ValueError, TypeError):
                    pass

            if aid == "PROPERTY_TYPE":
                key = normalize_text(str(val))
                listing["tipo"] = next((v for k, v in _TYPE_MAP.items() if k in key), "Otro")
                extracted.add("tipo")

            # Skip items that are for sale, not rental
            if aid == "OPERATION_TYPE":
                op = normalize_text(str(val))
                if "venta" in op or "sale" in op:
                    logger.debug("[ml] Skipping sale listing %s", item_id)
                    return None

        # ── Location ──
        location = (detail or {}).get("location") or {}
        addr_obj = item.get("address") or {}

        city = (location.get("city") or {}).get("name") or addr_obj.get("city_name", "")
        nb   = (location.get("neighborhood") or {}).get("name", "")
        addr = location.get("address_line", "")

        listing["municipio"] = city or "Guadalajara"
        listing["zona"]      = city or "Guadalajara"
        listing["colonia"]   = nb or (addr[:50] if addr else "")
        if listing["colonia"]:
            extracted.add("colonia")

        # ML sometimes returns actual coordinates — use them if available
        lat = location.get("latitude")
        lng = location.get("longitude")
        if lat and lng:
            listing["lat"] = float(lat)
            listing["lng"] = float(lng)
        else:
            coords = geocode_listing(listing.get("colonia"), listing.get("zona"))
            if coords:
                listing["lat"], listing["lng"] = coords

        # ── Description ──
        listing["descripcion_original"] = desc_raw
        listing["descripcion_corta"] = desc_raw[:120].rstrip() + ("…" if len(desc_raw) > 120 else "")

        # ── Pets & requirements ──
        texts = [listing["titulo"], desc_raw]
        listing.update(parse_pets_policy(texts))
        listing.update(parse_rental_requirements(texts))

        # ── Zone priority ──
        zone_key = normalize_text((listing.get("colonia") or "") + " " + (listing.get("zona") or ""))
        listing["prioridad_zona"] = max(
            (_ZONE_PRIORITY.get(k, 0) for k in _ZONE_PRIORITY if k in zone_key),
            default=1,
        )

        # ── Extraction flags ──
        listing["_extraction_flags"] = {
            "precio_explicit":    listing.get("precio_mensual") is not None,
            "recamaras_explicit": "recamaras" in extracted,
            "banos_explicit":     "banos" in extracted,
            "metros_explicit":    "metros_cuadrados" in extracted,
            "colonia_explicit":   "colonia" in extracted,
            "tipo_explicit":      "tipo" in extracted,
            "parsing_conflict":   False,
            "weak_inference":     not bool(desc_raw),
        }

        return listing

    # ── HTTP helpers ───────────────────────────────────────────
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.RequestException),
        reraise=True,
    )
    def _get(self, url: str, **kwargs) -> dict:
        resp = requests.get(url, headers=_HEADERS, timeout=15, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def _fetch_item(self, item_id: str) -> dict | None:
        try:
            return self._get(_ITEM_URL.format(item_id))
        except Exception as exc:
            logger.debug("[ml] Item detail failed %s: %s", item_id, exc)
            return None

    def _fetch_description(self, item_id: str) -> str:
        try:
            data = self._get(_DESC_URL.format(item_id))
            return (data.get("plain_text") or data.get("text") or "").strip()
        except Exception:
            return ""
