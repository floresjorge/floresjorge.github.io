"""
Manual feed source: load listings from a user-maintained CSV or JSON file.

Use this to add listings you find manually (from any site, WhatsApp groups,
classified ads, etc.) without needing to implement a scraper.

Expected file location (configurable via env var MANUAL_FEED_PATH):
  rental-monitor-gdl/data/manual_listings.csv   (default)
  or any .json file with the same schema

CSV format (header row required, extra columns ignored):
  titulo,tipo,zona,colonia,municipio,precio_mensual,recamaras,banos,
  estacionamientos,metros_cuadrados,descripcion_original,url,fecha_publicacion

JSON format:
  List of objects with the same fields (any subset).

Example CSV rows:
  Casa céntrica 3 rec,Casa,Guadalajara Centro,Centro,Guadalajara,12000,
    3,2,1,130,"Patio grande, exige aval",https://wa.me/...,2025-05-20

Env var: MANUAL_FEED_PATH – override the default CSV path.
"""

import csv
import json
import logging
import os
from datetime import date
from pathlib import Path
from typing import Any

from .base import BaseSource
from ..parsers import canonicalize_url, parse_pets_policy, parse_rental_requirements, normalize_text

logger = logging.getLogger(__name__)

_DEFAULT_PATH = Path(__file__).parent.parent.parent / "data" / "manual_listings.csv"

_INT_FIELDS = {"precio_mensual", "recamaras", "banos", "estacionamientos"}
_FLOAT_FIELDS = {"metros_cuadrados"}


def _coerce(key: str, val: str) -> Any:
    val = val.strip()
    if not val:
        return None
    if key in _INT_FIELDS:
        try:
            return int(float(val))
        except ValueError:
            return None
    if key in _FLOAT_FIELDS:
        try:
            return float(val)
        except ValueError:
            return None
    return val


class ManualFeedSource(BaseSource):
    name = "manual"
    base_url = ""

    def __init__(self):
        path_env = os.getenv("MANUAL_FEED_PATH", "")
        self._path = Path(path_env) if path_env else _DEFAULT_PATH

    def is_available(self) -> bool:
        return self._path.exists()

    def fetch_listings(self, zona: str, precio_max: int, limite: int = 50) -> list[dict[str, Any]]:
        if not self._path.exists():
            logger.info("[manual] Feed file not found: %s", self._path)
            return []

        logger.info("[manual] Loading from %s", self._path)
        try:
            raw = self._load_file()
        except Exception as exc:
            logger.error("[manual] Failed to load feed: %s", exc)
            return []

        today = str(date.today())
        results: list[dict[str, Any]] = []

        for i, row in enumerate(raw):
            listing = self._default_listing()
            for k, v in row.items():
                if k in listing or k not in ("id", "score_calidad", "score_confianza_extraccion"):
                    listing[k] = _coerce(k, str(v)) if isinstance(v, str) else v

            listing["fuente"] = "manual"
            listing["fecha_extraccion"] = listing.get("fecha_extraccion") or today
            listing["moneda"] = listing.get("moneda") or "MXN"

            price = listing.get("precio_mensual")
            if price is not None and price > precio_max:
                continue

            url = listing.get("url", "")
            listing["url_canonica"] = canonicalize_url(url) if url else f"manual-{i}"
            listing["id"] = f"manual-{i}"

            desc = listing.get("descripcion_original", "")
            listing["descripcion_corta"] = desc[:120].rstrip() + ("…" if len(desc) > 120 else "")

            listing.update(parse_pets_policy([listing.get("titulo"), desc]))
            listing.update(parse_rental_requirements([desc]))

            listing["_extraction_flags"] = {
                "precio_explicit": listing.get("precio_mensual") is not None,
                "recamaras_explicit": listing.get("recamaras") is not None,
                "banos_explicit": listing.get("banos") is not None,
                "metros_explicit": listing.get("metros_cuadrados") is not None,
                "colonia_explicit": bool(listing.get("colonia")),
                "tipo_explicit": listing.get("tipo") not in (None, "", "No especificado"),
                "parsing_conflict": False,
                "weak_inference": True,  # manual data may be incomplete
            }

            results.append(listing)
            if len(results) >= limite:
                break

        logger.info("[manual] Loaded %d listings from feed", len(results))
        return results

    def _load_file(self) -> list[dict]:
        suffix = self._path.suffix.lower()
        if suffix == ".json":
            with self._path.open(encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        # Default: CSV
        with self._path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            return [dict(row) for row in reader]
