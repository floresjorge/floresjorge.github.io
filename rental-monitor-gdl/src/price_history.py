"""
Price history tracker.

Maintains data/price_history.json across runs.
Each listing accumulates dated price snapshots so the dashboard can
show trends and sparklines.

Schema:
  {
    "<listing-id>": {
      "titulo": "...",
      "url_canonica": "...",
      "precios": [
        {"fecha": "2025-05-01", "precio": 12000},
        {"fecha": "2025-05-15", "precio": 11500}
      ]
    },
    ...
  }

A new snapshot is added only when the price changed OR the listing is new.
This keeps the file small and avoids duplicate identical entries.
"""

import json
import logging
from datetime import date
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def update_price_history(
    listings: list[dict[str, Any]],
    history_path: Path,
) -> dict[str, Any]:
    """
    Read existing price history, merge today's prices, save, and return the updated dict.
    Listings without a precio_mensual are skipped.
    """
    history: dict[str, Any] = {}

    if history_path.exists():
        try:
            history = json.loads(history_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not read price history (%s); starting fresh", exc)

    today = str(date.today())
    updated = 0

    for listing in listings:
        lid = listing.get("id")
        price = listing.get("precio_mensual")
        if not lid or price is None:
            continue

        entry = history.setdefault(lid, {
            "titulo": listing.get("titulo", ""),
            "url_canonica": listing.get("url_canonica", ""),
            "precios": [],
        })

        snapshots: list[dict] = entry["precios"]
        last_price = snapshots[-1]["precio"] if snapshots else None

        if last_price != price:
            snapshots.append({"fecha": today, "precio": price})
            updated += 1

    if updated:
        history_path.parent.mkdir(parents=True, exist_ok=True)
        history_path.write_text(
            json.dumps(history, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Price history: %d update(s) written to %s", updated, history_path)
    else:
        logger.info("Price history: no price changes detected")

    return history
