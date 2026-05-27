"""Apply quality and confidence scores to a list of listings."""

from typing import Any
from .parsers import compute_quality_score, compute_confidence_score


def score_listings(listings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compute and inject score_calidad and score_confianza_extraccion into each listing."""
    for listing in listings:
        extraction_flags = listing.pop("_extraction_flags", None)
        listing["score_calidad"] = compute_quality_score(listing)
        listing["score_confianza_extraccion"] = compute_confidence_score(listing, extraction_flags)
    return listings
