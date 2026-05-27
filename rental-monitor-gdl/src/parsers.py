"""
Text parsing and normalization utilities for rental property listings.

Quality score (score_calidad) 0-100:
  +15  precio_mensual presente y > 0
  +10  zona o colonia presente
  +10  tipo presente
  +10  recamaras > 0
  +10  metros_cuadrados > 0
  +15  descripcion_original > 100 chars (8 si > 50)
  +5   mascotas != "No especificado"
  +5   al menos un requisito detectado
  +5   url_canonica válida (starts with https?)
  +5   fuente en lista confiable
  +10  zona de alta prioridad (Centro o equivalente)
  ---
  100 máx

Confidence score (score_confianza_extraccion) 0-100:
  +8   precio extraído explícitamente (no inferido)
  +8   recámaras extraídas explícitamente
  +6   baños extraídos
  +6   metros extraídos
  +8   colonia extraída
  +8   tipo extraído
  +6   mascotas detectadas (señal clara)
  +6   requisitos detectados (al menos uno)
  +10  sin conflictos de parsing
  +8   descripción original disponible
  +8   fecha publicación disponible
  +8   no hubo inferencias débiles
  +10  URL válida y canónica obtenida
  ---
  100 máx
"""

import re
import unicodedata
from typing import Any
from urllib.parse import urlparse, urlunparse, urlencode, parse_qs


# ---------------------------------------------------------------------------
# Text normalization
# ---------------------------------------------------------------------------

def normalize_text(text: str | None) -> str:
    """Lowercase, strip accents, collapse whitespace."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_str).strip().lower()


def strip_html(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"<[^>]+>", " ", text)


# ---------------------------------------------------------------------------
# Price parsing
# ---------------------------------------------------------------------------

_NUM = r"[0-9]{1,3}(?:[,\.][0-9]{3})*|[0-9]{4,7}"
_PRICE_PATTERNS = [
    # $12,500 MXN/mes  |  $12500
    re.compile(r"\$\s*(" + _NUM + r")(?:\.[0-9]{1,2})?", re.IGNORECASE),
    # 12500 pesos / mes  |  12,500 pesos
    re.compile(r"(" + _NUM + r")\s*(?:pesos?|mxn)\b", re.IGNORECASE),
    # renta de 12500
    re.compile(r"renta(?:\s+mensual)?(?:\s+de)?\s*\$?\s*(" + _NUM + r")", re.IGNORECASE),
]


def parse_price(text: str | None) -> int | None:
    """Return monthly rent in MXN as int, or None if not found."""
    if not text:
        return None
    cleaned = strip_html(text)
    for pattern in _PRICE_PATTERNS:
        m = pattern.search(cleaned)
        if m:
            raw = m.group(1).replace(",", "").replace(".", "")
            try:
                value = int(raw)
                if 500 <= value <= 500_000:
                    return value
            except ValueError:
                continue
    return None


# ---------------------------------------------------------------------------
# Bedrooms / bathrooms / parking parsing
# ---------------------------------------------------------------------------

_BEDROOM_PATTERNS = [
    re.compile(r"(\d+)\s*rec[aá]maras?", re.IGNORECASE),
    re.compile(r"(\d+)\s*hab(?:itaciones?)?", re.IGNORECASE),
    re.compile(r"(\d+)\s*cuartos?", re.IGNORECASE),
    re.compile(r"(\d+)\s*dorm(?:itorios?)?", re.IGNORECASE),
    re.compile(r"(\d+)\s*rec\b", re.IGNORECASE),
]

_BATHROOM_PATTERNS = [
    re.compile(r"(\d+(?:\.\d)?)\s*ba[ñn]os?", re.IGNORECASE),
    re.compile(r"(\d+(?:\.\d)?)\s*wc\b", re.IGNORECASE),
    re.compile(r"(\d+(?:\.\d)?)\s*toilets?", re.IGNORECASE),
]

_PARKING_PATTERNS = [
    re.compile(r"(\d+)\s*(?:lugares?|cajones?|espacios?)\s+(?:de\s+)?(?:estacionamiento|cochera)", re.IGNORECASE),
    re.compile(r"(\d+)\s*estacionamientos?", re.IGNORECASE),
    re.compile(r"(\d+)\s*cocheras?", re.IGNORECASE),
]

_SQMT_PATTERNS = [
    re.compile(r"(\d+(?:\.\d+)?)\s*m(?:etros?)?(?:\s*cuadrados?|\s*2|\s*²|\s*\^2)?", re.IGNORECASE),
    re.compile(r"(\d+(?:\.\d+)?)\s*(?:m2|mt2|mts2|m²)", re.IGNORECASE),
]


def _first_int(patterns: list, text: str) -> int | None:
    cleaned = strip_html(text)
    for p in patterns:
        m = p.search(cleaned)
        if m:
            try:
                v = float(m.group(1))
                return int(v)
            except ValueError:
                continue
    return None


def parse_bedrooms(text: str | None) -> int | None:
    return _first_int(_BEDROOM_PATTERNS, text or "")


def parse_bathrooms(text: str | None) -> float | None:
    cleaned = strip_html(text or "")
    for p in _BATHROOM_PATTERNS:
        m = p.search(cleaned)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                continue
    return None


def parse_parking(text: str | None) -> int | None:
    return _first_int(_PARKING_PATTERNS, text or "")


def parse_sqmt(text: str | None) -> float | None:
    cleaned = strip_html(text or "")
    for p in _SQMT_PATTERNS:
        m = p.search(cleaned)
        if m:
            try:
                v = float(m.group(1))
                if 10 <= v <= 5000:
                    return v
            except ValueError:
                continue
    return None


# ---------------------------------------------------------------------------
# Pet policy parsing
# ---------------------------------------------------------------------------

# Signal weights: +1 positive, -1 negative, +0.5 conditional
_NEG_CONTEXT = re.compile(r"\b(?:no|sin|nunca)\b", re.IGNORECASE)


def _pos_matches(patterns: list, text: str) -> list[str]:
    """Return positive-pattern matches that are NOT preceded by a negation within 12 chars."""
    found = []
    for p in patterns:
        for m in p.finditer(text):
            context = text[max(0, m.start() - 12): m.start()]
            if not _NEG_CONTEXT.search(context):
                found.append(m.group())
    return list(dict.fromkeys(found))


_PET_POSITIVE = [
    re.compile(r"(?:se\s+)?acepta[mn]?\s+mascotas?", re.IGNORECASE),
    re.compile(r"pet[\s\-]?friendly", re.IGNORECASE),
    re.compile(r"mascotas?\s+(?:son\s+)?(?:bien)?venidas?", re.IGNORECASE),
    re.compile(r"admite[nm]?\s+mascotas?", re.IGNORECASE),
    re.compile(r"permite[nm]?\s+mascotas?", re.IGNORECASE),
    re.compile(r"mascotas?\s+(?:ok|permitidas?|aceptadas?)", re.IGNORECASE),
    re.compile(r"se\s+aceptan?\s+mascotas?", re.IGNORECASE),
]

_PET_CONDITIONAL = [
    re.compile(r"mascota[s]?\s*peque[ñn]a", re.IGNORECASE),
    re.compile(r"perro[s]?\s*peque[ñn]o", re.IGNORECASE),
    re.compile(r"sujeto\s+a\s+autorizaci[oó]n", re.IGNORECASE),
    re.compile(r"previo\s+acuerdo", re.IGNORECASE),
    re.compile(r"solo\s+gatos?", re.IGNORECASE),
    re.compile(r"(?:con|bajo)\s+restricciones?", re.IGNORECASE),
    re.compile(r"menor[es]?\s+(?:de\s+)?\d+\s*kg", re.IGNORECASE),
    re.compile(r"mascotas?\s+(?:con\s+)?restricci[oó]n", re.IGNORECASE),
    re.compile(r"previa\s+autorizaci[oó]n", re.IGNORECASE),
]

_PET_NEGATIVE = [
    re.compile(r"no\s+(?:se\s+)?acepta[mn]?\s+mascotas?", re.IGNORECASE),
    re.compile(r"no\s+mascotas?", re.IGNORECASE),
    re.compile(r"sin\s+mascotas?", re.IGNORECASE),
    re.compile(r"no\s+(?:se\s+)?acepta[mn]?\s+(?:perros?|gatos?|animales?)", re.IGNORECASE),
    re.compile(r"prohibi(?:do|das?|das?)\s+mascotas?", re.IGNORECASE),
    re.compile(r"mascotas?\s+(?:no\s+)?(?:prohibidas?|no\s+permitidas?)", re.IGNORECASE),
    re.compile(r"no\s+animales?", re.IGNORECASE),
    re.compile(r"no\s+se\s+permiten?\s+mascotas?", re.IGNORECASE),
]


def parse_pets_policy(texts: list[str | None]) -> dict[str, str]:
    """
    Analyze multiple text fields (title, description, requirements) for pet policy.

    Returns dict with keys:
      mascotas, detalle_mascotas, texto_mascotas_original
    """
    combined_texts = [t for t in texts if t]
    full_text = " ".join(combined_texts)
    norm = normalize_text(full_text)

    # Positive matches only when NOT preceded by negation words
    pos_matches = _pos_matches(_PET_POSITIVE, full_text)

    cond_matches: list[str] = []
    for p in _PET_CONDITIONAL:
        for m in p.findall(full_text):
            cond_matches.append(m if isinstance(m, str) else str(m))
    cond_matches = list(dict.fromkeys(cond_matches))

    neg_matches: list[str] = []
    for p in _PET_NEGATIVE:
        for m in p.findall(full_text):
            neg_matches.append(m if isinstance(m, str) else str(m))
    neg_matches = list(dict.fromkeys(neg_matches))

    has_pos = bool(pos_matches)
    has_cond = bool(cond_matches)
    has_neg = bool(neg_matches)

    details: list[str] = []
    if pos_matches:
        details.append("Señales positivas: " + ", ".join(pos_matches[:3]))
    if cond_matches:
        details.append("Restricciones: " + ", ".join(cond_matches[:3]))
    if neg_matches:
        details.append("Señales negativas: " + ", ".join(neg_matches[:3]))

    # Logic
    if has_neg and not has_pos and not has_cond:
        policy = "No acepta mascotas"
    elif has_pos and not has_neg and not has_cond:
        policy = "Sí acepta mascotas"
    elif has_cond and not has_neg and not has_pos:
        policy = "Acepta mascotas con restricciones"
    elif (has_pos and has_neg) or (has_neg and has_cond):
        policy = "Acepta mascotas con restricciones"
        details.append("Señales contradictorias detectadas")
    elif has_pos and has_cond:
        policy = "Acepta mascotas con restricciones"
    else:
        policy = "No especificado"

    return {
        "mascotas": policy,
        "detalle_mascotas": "; ".join(details) if details else "",
        "texto_mascotas_original": full_text[:500] if any([has_pos, has_cond, has_neg]) else "",
    }


# ---------------------------------------------------------------------------
# Rental requirements parsing
# ---------------------------------------------------------------------------

_REQ_PATTERNS: dict[str, list] = {
    "aval_no": [
        re.compile(r"\bsin\s+aval\b", re.IGNORECASE),
        re.compile(r"\bno\s+(?:se\s+)?(?:requiere|pide|solicita)\s+aval\b", re.IGNORECASE),
    ],
    "aval_si": [
        re.compile(r"\baval\b", re.IGNORECASE),
        re.compile(r"\bfiador\b", re.IGNORECASE),
    ],
    "justicia_alternativa_si": [
        re.compile(r"justicia\s+alternativa", re.IGNORECASE),
        re.compile(r"contrato\s+de\s+justicia\s+alternativa", re.IGNORECASE),
        re.compile(r"acepta\s+justicia\s+alternativa", re.IGNORECASE),
    ],
    "obligado_solidario": [
        re.compile(r"obligado\s+solidario", re.IGNORECASE),
        re.compile(r"codeudor\b", re.IGNORECASE),
    ],
    "poliza_juridica": [
        re.compile(r"p[oó]liza\s+jur[ií]dica", re.IGNORECASE),
        re.compile(r"p[oó]liza\s+de\s+garant[ií]a", re.IGNORECASE),
    ],
    "deposito": [
        re.compile(r"dep[oó]sito", re.IGNORECASE),
        re.compile(r"mes(?:es)?\s+(?:de\s+)?dep[oó]sito", re.IGNORECASE),
        re.compile(r"\d+\s+mes(?:es)?\s+(?:de\s+)?dep[oó]sito", re.IGNORECASE),
    ],
    "investigacion": [
        re.compile(r"investigaci[oó]n\s+(?:socio)?(?:econ[oó]mica)?", re.IGNORECASE),
        re.compile(r"estudio\s+socioecon[oó]mico", re.IGNORECASE),
        re.compile(r"investigaci[oó]n\s+de\s+cr[eé]dito", re.IGNORECASE),
    ],
    "comprobantes_ingresos": [
        re.compile(r"comprobante[s]?\s+(?:de\s+)?ingresos?", re.IGNORECASE),
        re.compile(r"estados?\s+de\s+cuenta", re.IGNORECASE),
        re.compile(r"recibos?\s+de\s+(?:sueldo|n[oó]mina)", re.IGNORECASE),
        re.compile(r"comprob(?:aci[oó]n|ante)\s+(?:de\s+)?trabajo", re.IGNORECASE),
    ],
}


def parse_rental_requirements(texts: list[str | None]) -> dict[str, Any]:
    """
    Detect rental requirements from multiple text fields.
    Never invents data: if not found, returns "No especificado".
    """
    combined_texts = [t for t in texts if t]
    full_text = " ".join(combined_texts)

    result: dict[str, Any] = {
        "requiere_aval": "No especificado",
        "justicia_alternativa": "No especificado",
        "requiere_fiador": "No especificado",
        "requiere_obligado_solidario": "No especificado",
        "requiere_poliza_juridica": "No especificado",
        "requiere_deposito": "No especificado",
        "requiere_investigacion": "No especificado",
        "requiere_comprobantes_ingresos": "No especificado",
        "detalle_requisitos": "",
        "texto_requisitos_original": full_text[:800],
    }

    details: list[str] = []

    # Aval / fiador (check negation first)
    aval_no = any(p.search(full_text) for p in _REQ_PATTERNS["aval_no"])
    aval_si_patterns = _REQ_PATTERNS["aval_si"]
    fiador_match = any(p.search(full_text) for p in [aval_si_patterns[1]])
    aval_match = bool(aval_si_patterns[0].search(full_text))

    if aval_no:
        result["requiere_aval"] = "No"
        details.append("Sin aval")
    elif aval_match:
        result["requiere_aval"] = "Sí"
        details.append("Requiere aval")

    if fiador_match and not aval_no:
        result["requiere_fiador"] = "Sí"
        if result["requiere_aval"] == "No especificado":
            result["requiere_aval"] = "Sí"
        details.append("Requiere fiador")

    # Justicia alternativa
    ja_si = any(p.search(full_text) for p in _REQ_PATTERNS["justicia_alternativa_si"])
    # Check if it's listed as option vs requirement
    ja_option = bool(
        re.search(r"(?:aval\s+o\s+justicia\s+alternativa|justicia\s+alternativa\s+o\s+aval)", full_text, re.IGNORECASE)
    )
    if ja_si:
        result["justicia_alternativa"] = "Sí"
        if ja_option:
            details.append("Acepta justicia alternativa (como opción al aval)")
        else:
            details.append("Requiere/acepta justicia alternativa")

    # Obligado solidario
    if any(p.search(full_text) for p in _REQ_PATTERNS["obligado_solidario"]):
        result["requiere_obligado_solidario"] = "Sí"
        details.append("Requiere obligado solidario")

    # Póliza jurídica
    if any(p.search(full_text) for p in _REQ_PATTERNS["poliza_juridica"]):
        result["requiere_poliza_juridica"] = "Sí"
        details.append("Requiere póliza jurídica")

    # Depósito
    if any(p.search(full_text) for p in _REQ_PATTERNS["deposito"]):
        result["requiere_deposito"] = "Sí"
        # Try to extract months
        m = re.search(r"(\d+)\s+mes(?:es)?\s+(?:de\s+)?dep[oó]sito", full_text, re.IGNORECASE)
        if m:
            details.append(f"Depósito: {m.group(1)} mes(es)")
        else:
            details.append("Requiere depósito")

    # Investigación
    if any(p.search(full_text) for p in _REQ_PATTERNS["investigacion"]):
        result["requiere_investigacion"] = "Sí"
        details.append("Requiere investigación socioeconómica")

    # Comprobantes de ingresos
    if any(p.search(full_text) for p in _REQ_PATTERNS["comprobantes_ingresos"]):
        result["requiere_comprobantes_ingresos"] = "Sí"
        details.append("Requiere comprobantes de ingresos")

    result["detalle_requisitos"] = "; ".join(details) if details else "Sin información de requisitos"
    return result


# ---------------------------------------------------------------------------
# URL canonicalization
# ---------------------------------------------------------------------------

_TRACKING_PARAMS = frozenset(
    ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
     "ref", "referrer", "fbclid", "gclid", "mc_cid", "mc_eid"]
)


def canonicalize_url(url: str | None) -> str:
    if not url:
        return ""
    try:
        parsed = urlparse(url.strip())
        scheme = parsed.scheme.lower() or "https"
        netloc = parsed.netloc.lower().lstrip("www.")
        path = re.sub(r"/+", "/", parsed.path.rstrip("/")) or "/"
        # Remove tracking params; flatten multi-value lists to first value
        qs = {k: v[0] for k, v in parse_qs(parsed.query).items() if k not in _TRACKING_PARAMS}
        query = urlencode(sorted(qs.items())) if qs else ""
        return urlunparse((scheme, netloc, path, "", query, ""))
    except Exception:
        return url


def is_valid_url(url: str | None) -> bool:
    if not url:
        return False
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

_TRUSTED_SOURCES = frozenset(["inmuebles24", "vivanuncios", "lamudi", "propiedades.com", "metroscubicos"])

_PRIORITY_ZONES = frozenset([
    "guadalajara centro", "centro historico", "centro", "analco",
    "mexicaltzingo", "santa tere", "santa teresa", "sagrada familia",
    "artesanos", "morelos", "san sebastian",
])


def compute_quality_score(listing: dict[str, Any]) -> int:
    """
    Returns score_calidad 0-100 based on completeness and reliability of listing data.
    See module docstring for scoring breakdown.
    """
    score = 0

    if listing.get("precio_mensual") and listing["precio_mensual"] > 0:
        score += 15

    if listing.get("zona") or listing.get("colonia"):
        score += 10

    if listing.get("tipo"):
        score += 10

    if listing.get("recamaras") and listing["recamaras"] > 0:
        score += 10

    if listing.get("metros_cuadrados") and listing["metros_cuadrados"] > 0:
        score += 10

    desc = listing.get("descripcion_original") or listing.get("descripcion_corta") or ""
    if len(desc) > 100:
        score += 15
    elif len(desc) > 50:
        score += 8

    if listing.get("mascotas") and listing["mascotas"] != "No especificado":
        score += 5

    req_fields = [
        "requiere_aval", "justicia_alternativa", "requiere_deposito",
        "requiere_poliza_juridica", "requiere_investigacion",
    ]
    if any(listing.get(f) and listing[f] != "No especificado" for f in req_fields):
        score += 5

    if is_valid_url(listing.get("url_canonica") or listing.get("url")):
        score += 5

    if normalize_text(listing.get("fuente", "")) in _TRUSTED_SOURCES:
        score += 5

    zona_norm = normalize_text(listing.get("zona", "") + " " + listing.get("colonia", ""))
    if any(pz in zona_norm for pz in _PRIORITY_ZONES):
        score += 10

    return min(score, 100)


def compute_confidence_score(listing: dict[str, Any], extraction_flags: dict[str, bool] | None = None) -> int:
    """
    Returns score_confianza_extraccion 0-100 based on how reliably data was extracted.
    extraction_flags: optional dict with keys 'precio_explicit', 'recamaras_explicit', etc.
    """
    flags = extraction_flags or {}
    score = 0

    if flags.get("precio_explicit", listing.get("precio_mensual") is not None):
        score += 8
    if flags.get("recamaras_explicit", listing.get("recamaras") is not None):
        score += 8
    if flags.get("banos_explicit", listing.get("banos") is not None):
        score += 6
    if flags.get("metros_explicit", listing.get("metros_cuadrados") is not None):
        score += 6
    if flags.get("colonia_explicit", bool(listing.get("colonia"))):
        score += 8
    if flags.get("tipo_explicit", bool(listing.get("tipo"))):
        score += 8
    if listing.get("mascotas") and listing["mascotas"] != "No especificado":
        score += 6
    req_detected = any(
        listing.get(f) and listing[f] not in ("No especificado", "")
        for f in ["requiere_aval", "justicia_alternativa", "requiere_deposito"]
    )
    if req_detected:
        score += 6
    if not flags.get("parsing_conflict", False):
        score += 10
    if listing.get("descripcion_original"):
        score += 8
    if listing.get("fecha_publicacion"):
        score += 8
    if not flags.get("weak_inference", False):
        score += 8
    if is_valid_url(listing.get("url_canonica") or listing.get("url")):
        score += 10

    return min(score, 100)
