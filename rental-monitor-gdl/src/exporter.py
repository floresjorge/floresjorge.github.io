"""Export listings to JSON, CSV, and metadata files."""

import csv
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_CSV_FIELDS = [
    "id", "titulo", "tipo", "zona", "colonia", "municipio",
    "precio_mensual", "moneda", "recamaras", "banos", "estacionamientos",
    "metros_cuadrados", "mascotas", "requiere_aval", "justicia_alternativa",
    "requiere_deposito", "requiere_poliza_juridica", "requiere_investigacion",
    "requiere_comprobantes_ingresos", "score_calidad", "score_confianza_extraccion",
    "prioridad_zona", "fuente", "fecha_publicacion", "fecha_extraccion",
    "url",
]


def export_listings(
    listings: list[dict[str, Any]],
    output_dir: Path,
    zona_objetivo: str,
    precio_max: int,
    start_time: float,
    filtered_count: int,
    sources_used: list[str],
    errors: list[str],
    warnings: list[str],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- listings.json ---
    listings_path = output_dir / "listings.json"
    with listings_path.open("w", encoding="utf-8") as f:
        json.dump(listings, f, ensure_ascii=False, indent=2, default=str)
    logger.info("Exported %d listings to %s", len(listings), listings_path)

    # --- listings.csv ---
    csv_path = output_dir / "listings.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(listings)
    logger.info("Exported CSV to %s", csv_path)

    # --- metadata.json ---
    elapsed = round(time.time() - start_time, 2)
    metadata = {
        "fecha_actualizacion": datetime.now(timezone.utc).isoformat(),
        "total_anuncios": len(listings),
        "anuncios_filtrados": filtered_count,
        "fuentes_utilizadas": sources_used,
        "zona_objetivo": zona_objetivo,
        "precio_maximo": precio_max,
        "tiempo_ejecucion_segundos": elapsed,
        "errores": errors,
        "advertencias": warnings,
    }
    meta_path = output_dir / "metadata.json"
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    logger.info("Metadata written to %s", meta_path)
