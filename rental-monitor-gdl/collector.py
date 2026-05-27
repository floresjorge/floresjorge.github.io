#!/usr/bin/env python3
"""
Guadalajara Rental Monitor – main collector script.

Usage:
  python collector.py
  python collector.py --zona "Guadalajara Centro" --precio-max 15000
  python collector.py --sources demo --limite 30
  python collector.py --output-dir /path/to/data
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# Allow running from repo root or from rental-monitor-gdl/
_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from src.sources import get_sources
from src.deduplicator import deduplicate
from src.scorer import score_listings
from src.exporter import export_listings
from src.parsers import geocode_listing

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s – %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("collector")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Collect rental listings in Guadalajara and export to JSON/CSV.",
    )
    p.add_argument("--zona", default="Guadalajara Centro", help="Target zone (default: Guadalajara Centro)")
    p.add_argument("--precio-max", type=int, default=20000, help="Max monthly rent MXN (default: 20000)")
    p.add_argument("--limite", type=int, default=100, help="Max listings per source (default: 100)")
    p.add_argument(
        "--sources",
        nargs="+",
        default=None,
        help="Source names to use (default: all available). Example: --sources demo",
    )
    p.add_argument(
        "--output-dir",
        default=None,
        help="Output directory (default: <script_dir>/data)",
    )
    p.add_argument(
        "--skip-unavailable",
        action="store_true",
        default=True,
        help="Skip sources that report is_available() == False (default: True)",
    )
    p.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    output_dir = Path(args.output_dir) if args.output_dir else _HERE / "data"

    start_time = time.time()
    errors: list[str] = []
    warnings: list[str] = []
    sources_used: list[str] = []
    raw_count = 0

    sources = get_sources(args.sources)
    all_listings: list[dict] = []

    for source in sources:
        if args.skip_unavailable and not source.is_available():
            logger.info("Skipping unavailable source: %s", source.name)
            warnings.append(f"Source '{source.name}' skipped (unavailable)")
            continue

        logger.info("Fetching from source: %s", source.name)
        try:
            listings = source.fetch_listings(
                zona=args.zona,
                precio_max=args.precio_max,
                limite=args.limite,
            )
            raw_count += len(listings)
            all_listings.extend(listings)
            sources_used.append(source.name)
            logger.info("Source %s: %d listings fetched", source.name, len(listings))
        except Exception as exc:
            msg = f"Source '{source.name}' error: {exc}"
            logger.error(msg, exc_info=True)
            errors.append(msg)

    if not all_listings:
        logger.warning("No listings collected from any source.")
        warnings.append("No listings collected; check source availability")

    filtered_count = raw_count - len(all_listings)

    # Deduplication
    deduped, removed = deduplicate(all_listings)
    if removed:
        logger.info("Removed %d duplicate(s)", removed)

    # Geocoding (colonia → lat/lng, no API)
    for listing in deduped:
        if listing.get("lat") is None:
            coords = geocode_listing(listing.get("colonia"), listing.get("zona"))
            if coords:
                listing["lat"], listing["lng"] = coords

    # Scoring
    scored = score_listings(deduped)

    # Sort: priority zone desc, then price asc
    scored.sort(key=lambda x: (-x.get("prioridad_zona", 0), x.get("precio_mensual") or 999_999))

    # Export
    export_listings(
        listings=scored,
        output_dir=output_dir,
        zona_objetivo=args.zona,
        precio_max=args.precio_max,
        start_time=start_time,
        filtered_count=filtered_count,
        sources_used=sources_used,
        errors=errors,
        warnings=warnings,
    )

    elapsed = round(time.time() - start_time, 2)
    logger.info(
        "Done. %d listings exported in %.1fs. Errors: %d, Warnings: %d",
        len(scored), elapsed, len(errors), len(warnings),
    )

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
