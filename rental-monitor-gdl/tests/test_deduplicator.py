"""Unit tests for src/deduplicator.py"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.deduplicator import deduplicate, _title_fingerprint


class TestTitleFingerprint:
    def test_same_title_same_price_same_zone(self):
        fp1 = _title_fingerprint("Casa en renta Centro", 12000, "Centro")
        fp2 = _title_fingerprint("Casa en renta Centro", 12000, "Centro")
        assert fp1 == fp2

    def test_different_price_bucket(self):
        fp1 = _title_fingerprint("Casa en renta", 12000, "Centro")
        fp2 = _title_fingerprint("Casa en renta", 13000, "Centro")
        # Same bucket (both floor to 12000 when divided by 500)
        # 12000//500*500 == 12000, 13000//500*500 == 13000 → different
        # actually 12000//500=24, 13000//500=26, so buckets differ
        assert fp1 != fp2

    def test_none_values_safe(self):
        fp = _title_fingerprint(None, None, None)
        assert isinstance(fp, str)


class TestDeduplicate:
    def _make_listing(self, url, title, price, zona):
        return {
            "url": url,
            "url_canonica": url,
            "titulo": title,
            "precio_mensual": price,
            "zona": zona,
        }

    def test_no_duplicates(self):
        listings = [
            self._make_listing("https://a.com/1", "Casa en Centro", 12000, "Centro"),
            self._make_listing("https://a.com/2", "Depto en Analco", 9000, "Analco"),
        ]
        result, removed = deduplicate(listings)
        assert len(result) == 2
        assert removed == 0

    def test_exact_url_duplicate(self):
        listings = [
            self._make_listing("https://a.com/1", "Casa en Centro", 12000, "Centro"),
            self._make_listing("https://a.com/1", "Casa en Centro", 12000, "Centro"),
        ]
        result, removed = deduplicate(listings)
        assert len(result) == 1
        assert removed == 1

    def test_fuzzy_duplicate_same_title_price_zone(self):
        listings = [
            self._make_listing("https://a.com/1", "Casa colonial en renta Centro", 12000, "Centro"),
            self._make_listing("https://b.com/99", "Casa colonial en renta Centro", 12000, "Centro"),
        ]
        result, removed = deduplicate(listings)
        assert len(result) == 1
        assert removed == 1

    def test_different_price_not_duplicate(self):
        listings = [
            self._make_listing("https://a.com/1", "Casa en renta Centro", 12000, "Centro"),
            self._make_listing("https://b.com/2", "Casa en renta Centro", 15000, "Centro"),
        ]
        result, removed = deduplicate(listings)
        assert len(result) == 2
        assert removed == 0

    def test_empty_list(self):
        result, removed = deduplicate([])
        assert result == []
        assert removed == 0

    def test_single_listing(self):
        listings = [self._make_listing("https://a.com/1", "Casa", 10000, "Centro")]
        result, removed = deduplicate(listings)
        assert len(result) == 1
        assert removed == 0

    def test_preserves_order_of_first_seen(self):
        listings = [
            self._make_listing("https://a.com/1", "Casa A", 10000, "Centro"),
            self._make_listing("https://a.com/2", "Casa B", 11000, "Centro"),
            self._make_listing("https://a.com/1", "Casa A", 10000, "Centro"),  # dup
        ]
        result, _ = deduplicate(listings)
        assert result[0]["url"] == "https://a.com/1"
        assert result[1]["url"] == "https://a.com/2"
