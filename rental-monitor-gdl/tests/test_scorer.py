"""Unit tests for scoring pipeline."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scorer import score_listings
from src.parsers import compute_quality_score


class TestScoreListings:
    def _listing(self, **kwargs):
        base = {
            "precio_mensual": 10000,
            "zona": "Guadalajara Centro",
            "colonia": "Centro",
            "tipo": "Casa",
            "recamaras": 3,
            "metros_cuadrados": 120,
            "descripcion_original": "Casa bonita con jardín en el centro histórico de Guadalajara.",
            "mascotas": "No especificado",
            "requiere_aval": "No especificado",
            "justicia_alternativa": "No especificado",
            "requiere_deposito": "No especificado",
            "requiere_poliza_juridica": "No especificado",
            "requiere_investigacion": "No especificado",
            "url_canonica": "https://example.com/1",
            "fuente": "demo",
        }
        base.update(kwargs)
        return base

    def test_scores_injected(self):
        listings = [self._listing()]
        result = score_listings(listings)
        assert "score_calidad" in result[0]
        assert "score_confianza_extraccion" in result[0]

    def test_scores_are_integers(self):
        listings = [self._listing()]
        result = score_listings(listings)
        assert isinstance(result[0]["score_calidad"], int)
        assert isinstance(result[0]["score_confianza_extraccion"], int)

    def test_scores_in_range(self):
        listings = [self._listing()]
        result = score_listings(listings)
        assert 0 <= result[0]["score_calidad"] <= 100
        assert 0 <= result[0]["score_confianza_extraccion"] <= 100

    def test_extraction_flags_consumed(self):
        listing = self._listing()
        listing["_extraction_flags"] = {"precio_explicit": True, "weak_inference": False}
        result = score_listings([listing])
        assert "_extraction_flags" not in result[0]

    def test_full_listing_higher_score_than_empty(self):
        full_score = compute_quality_score(self._listing())
        empty_score = compute_quality_score({})
        assert full_score > empty_score

    def test_batch_processing(self):
        listings = [self._listing(precio_mensual=p) for p in [8000, 9000, 10000]]
        result = score_listings(listings)
        assert len(result) == 3
        for r in result:
            assert "score_calidad" in r
