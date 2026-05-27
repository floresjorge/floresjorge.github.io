"""Unit tests for src/parsers.py"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.parsers import (
    normalize_text,
    parse_price,
    parse_bedrooms,
    parse_bathrooms,
    parse_sqmt,
    parse_pets_policy,
    parse_rental_requirements,
    canonicalize_url,
    is_valid_url,
    compute_quality_score,
    compute_confidence_score,
)


# ---------------------------------------------------------------------------
# normalize_text
# ---------------------------------------------------------------------------
class TestNormalizeText:
    def test_lowercase(self):
        assert normalize_text("CASA EN RENTA") == "casa en renta"

    def test_accents_stripped(self):
        assert normalize_text("Recámara") == "recamara"
        assert normalize_text("depósito") == "deposito"
        assert normalize_text("póliza") == "poliza"

    def test_whitespace_collapsed(self):
        assert normalize_text("  casa  en   renta  ") == "casa en renta"

    def test_none_input(self):
        assert normalize_text(None) == ""

    def test_empty_string(self):
        assert normalize_text("") == ""


# ---------------------------------------------------------------------------
# parse_price
# ---------------------------------------------------------------------------
class TestParsePrice:
    def test_dollar_sign_comma(self):
        assert parse_price("$12,500") == 12500

    def test_dollar_sign_space(self):
        assert parse_price("$ 9 500") is None  # space-separated thousands not supported

    def test_pesos_keyword(self):
        assert parse_price("10000 pesos mensuales") == 10000

    def test_mxn_keyword(self):
        assert parse_price("Renta: 15,000 MXN/mes") == 15000

    def test_renta_keyword(self):
        assert parse_price("Renta mensual de $8,200") == 8200

    def test_value_too_low(self):
        assert parse_price("$100 al mes") is None

    def test_value_too_high(self):
        assert parse_price("$999,999,999") is None

    def test_none_input(self):
        assert parse_price(None) is None

    def test_no_price(self):
        assert parse_price("Casa en renta en Guadalajara") is None


# ---------------------------------------------------------------------------
# parse_bedrooms
# ---------------------------------------------------------------------------
class TestParseBedrooms:
    def test_recamaras(self):
        assert parse_bedrooms("3 recámaras amplias") == 3

    def test_habitaciones(self):
        assert parse_bedrooms("2 habitaciones") == 2

    def test_cuartos(self):
        assert parse_bedrooms("4 cuartos") == 4

    def test_rec_abbreviation(self):
        assert parse_bedrooms("Casa 2 rec en renta") == 2

    def test_none(self):
        assert parse_bedrooms(None) is None

    def test_no_match(self):
        assert parse_bedrooms("Casa sin datos") is None


# ---------------------------------------------------------------------------
# parse_pets_policy
# ---------------------------------------------------------------------------
class TestParsePetsPolicy:
    def test_no_pets_clear(self):
        result = parse_pets_policy(["No se aceptan mascotas en el edificio"])
        assert result["mascotas"] == "No acepta mascotas"

    def test_pet_friendly_clear(self):
        result = parse_pets_policy(["Departamento pet friendly, mascotas bienvenidas"])
        assert result["mascotas"] == "Sí acepta mascotas"

    def test_acepta_mascotas(self):
        result = parse_pets_policy(["Se aceptan mascotas pequeñas"])
        assert result["mascotas"] in ("Sí acepta mascotas", "Acepta mascotas con restricciones")

    def test_conditional_solo_gatos(self):
        result = parse_pets_policy(["Solo gatos, no perros"])
        assert result["mascotas"] == "Acepta mascotas con restricciones"

    def test_conditional_sujeto_autorizacion(self):
        result = parse_pets_policy(["Mascotas sujeto a autorización del dueño"])
        assert result["mascotas"] == "Acepta mascotas con restricciones"

    def test_contradictory_signals(self):
        result = parse_pets_policy([
            "Se aceptan mascotas",
            "No se aceptan animales en las áreas comunes",
        ])
        assert result["mascotas"] == "Acepta mascotas con restricciones"
        assert "contradictorias" in result["detalle_mascotas"].lower()

    def test_no_mention(self):
        result = parse_pets_policy(["Casa amplia con jardín en el Centro"])
        assert result["mascotas"] == "No especificado"
        assert result["detalle_mascotas"] == ""

    def test_multiple_texts(self):
        result = parse_pets_policy([
            "Casa en renta",
            "Pet friendly",
            "Mascotas bienvenidas con previo acuerdo",
        ])
        assert result["mascotas"] in ("Sí acepta mascotas", "Acepta mascotas con restricciones")

    def test_none_inputs_ignored(self):
        result = parse_pets_policy([None, "Se aceptan mascotas", None])
        assert result["mascotas"] == "Sí acepta mascotas"


# ---------------------------------------------------------------------------
# parse_rental_requirements
# ---------------------------------------------------------------------------
class TestParseRentalRequirements:
    def test_sin_aval(self):
        result = parse_rental_requirements(["Sin aval, acepta justicia alternativa"])
        assert result["requiere_aval"] == "No"

    def test_requiere_aval(self):
        result = parse_rental_requirements(["Se requiere aval propietario en GDL"])
        assert result["requiere_aval"] == "Sí"

    def test_fiador_sets_aval(self):
        result = parse_rental_requirements(["Requiere fiador con propiedad"])
        assert result["requiere_fiador"] == "Sí"
        assert result["requiere_aval"] in ("Sí", "No especificado")

    def test_justicia_alternativa(self):
        result = parse_rental_requirements(["Acepta contrato de justicia alternativa"])
        assert result["justicia_alternativa"] == "Sí"

    def test_poliza_juridica(self):
        result = parse_rental_requirements(["Se requiere póliza jurídica o aval"])
        assert result["requiere_poliza_juridica"] == "Sí"

    def test_deposito(self):
        result = parse_rental_requirements(["2 meses de depósito requeridos"])
        assert result["requiere_deposito"] == "Sí"
        assert "2 mes" in result["detalle_requisitos"].lower()

    def test_investigacion(self):
        result = parse_rental_requirements(["Investigación socioeconómica obligatoria"])
        assert result["requiere_investigacion"] == "Sí"

    def test_comprobantes_ingresos(self):
        result = parse_rental_requirements(["Comprobante de ingresos mínimo 3x la renta"])
        assert result["requiere_comprobantes_ingresos"] == "Sí"

    def test_estados_de_cuenta(self):
        result = parse_rental_requirements(["Estados de cuenta bancarios últimos 3 meses"])
        assert result["requiere_comprobantes_ingresos"] == "Sí"

    def test_no_requirements_mentioned(self):
        result = parse_rental_requirements(["Casa preciosa cerca del parque"])
        assert result["requiere_aval"] == "No especificado"
        assert result["justicia_alternativa"] == "No especificado"
        assert result["requiere_deposito"] == "No especificado"

    def test_none_inputs_ignored(self):
        result = parse_rental_requirements([None, "Requiere aval", None])
        assert result["requiere_aval"] == "Sí"

    def test_aval_o_justicia_alternativa_option(self):
        result = parse_rental_requirements(["Aval o justicia alternativa, a elegir del inquilino"])
        assert result["requiere_aval"] == "Sí"
        assert result["justicia_alternativa"] == "Sí"

    def test_obligado_solidario(self):
        result = parse_rental_requirements(["Requiere obligado solidario con propiedad"])
        assert result["requiere_obligado_solidario"] == "Sí"


# ---------------------------------------------------------------------------
# canonicalize_url
# ---------------------------------------------------------------------------
class TestCanonicalizeUrl:
    def test_removes_utm(self):
        url = "https://example.com/listing/123?utm_source=facebook&utm_medium=cpc"
        assert "utm_source" not in canonicalize_url(url)

    def test_strips_www(self):
        assert "www." not in canonicalize_url("https://www.example.com/listing/1")

    def test_trailing_slash_removed(self):
        result = canonicalize_url("https://example.com/listing/1/")
        assert not result.endswith("/listing/1/")

    def test_none_returns_empty(self):
        assert canonicalize_url(None) == ""

    def test_lowercase_scheme(self):
        result = canonicalize_url("HTTP://Example.com/Listing/1")
        assert result.startswith("http://")

    def test_keeps_path_params(self):
        url = "https://example.com/listing/123?order=price"
        result = canonicalize_url(url)
        assert "order=price" in result


# ---------------------------------------------------------------------------
# compute_quality_score
# ---------------------------------------------------------------------------
class TestComputeQualityScore:
    def _complete_listing(self):
        return {
            "precio_mensual": 12000,
            "zona": "Guadalajara Centro",
            "colonia": "Centro",
            "tipo": "Casa",
            "recamaras": 3,
            "metros_cuadrados": 120,
            "descripcion_original": "Descripción muy detallada con más de 100 caracteres. " * 3,
            "mascotas": "Sí acepta mascotas",
            "requiere_aval": "Sí",
            "url_canonica": "https://example.com/listing/1",
            "fuente": "demo",
        }

    def test_complete_listing_high_score(self):
        listing = self._complete_listing()
        score = compute_quality_score(listing)
        assert score >= 70

    def test_empty_listing_low_score(self):
        score = compute_quality_score({})
        assert score < 20

    def test_price_contributes(self):
        base = compute_quality_score({})
        with_price = compute_quality_score({"precio_mensual": 10000})
        assert with_price > base

    def test_priority_zone_bonus(self):
        listing_centro = self._complete_listing()
        listing_otro = self._complete_listing()
        listing_otro["zona"] = "Tlaquepaque"
        listing_otro["colonia"] = "El Vergel"
        assert compute_quality_score(listing_centro) > compute_quality_score(listing_otro)

    def test_score_max_100(self):
        listing = self._complete_listing()
        listing["descripcion_original"] = "X" * 500
        assert compute_quality_score(listing) <= 100

    def test_score_min_0(self):
        assert compute_quality_score({}) >= 0
