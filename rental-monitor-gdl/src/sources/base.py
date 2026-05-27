"""Abstract base class for property listing sources."""

from abc import ABC, abstractmethod
from typing import Any


class BaseSource(ABC):
    name: str = "base"
    base_url: str = ""

    @abstractmethod
    def fetch_listings(
        self,
        zona: str,
        precio_max: int,
        limite: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Fetch rental listings for the given zone up to precio_max MXN/month.
        Must return a list of raw dicts with at minimum:
          titulo, url, fuente
        All other fields optional (will be filled with defaults downstream).
        """

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the source is functional (e.g. not blocked, API key present)."""

    def _default_listing(self) -> dict[str, Any]:
        """Skeleton listing with all expected fields at safe defaults."""
        return {
            "id": "",
            "titulo": "",
            "tipo": "No especificado",
            "zona": "",
            "colonia": "",
            "municipio": "Guadalajara",
            "precio_mensual": None,
            "moneda": "MXN",
            "recamaras": None,
            "banos": None,
            "estacionamientos": None,
            "metros_cuadrados": None,
            "descripcion_corta": "",
            "descripcion_original": "",
            "url": "",
            "url_canonica": "",
            "fuente": self.name,
            "fecha_publicacion": None,
            "fecha_extraccion": None,
            "prioridad_zona": 0,
            "mascotas": "No especificado",
            "detalle_mascotas": "",
            "texto_mascotas_original": "",
            "requiere_aval": "No especificado",
            "justicia_alternativa": "No especificado",
            "requiere_fiador": "No especificado",
            "requiere_obligado_solidario": "No especificado",
            "requiere_poliza_juridica": "No especificado",
            "requiere_deposito": "No especificado",
            "requiere_investigacion": "No especificado",
            "requiere_comprobantes_ingresos": "No especificado",
            "detalle_requisitos": "",
            "texto_requisitos_original": "",
            "lat": None,
            "lng": None,
            "score_calidad": 0,
            "score_confianza_extraccion": 0,
            "_extraction_flags": {},
        }
