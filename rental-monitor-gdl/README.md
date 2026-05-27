# Monitor de Renta – Guadalajara

Dashboard estático para monitorear inmuebles en renta en Guadalajara (con prioridad en Guadalajara Centro), actualizado automáticamente cada 12 horas mediante GitHub Actions.

## Estructura del proyecto

```
rental-monitor-gdl/
├── collector.py              # Punto de entrada principal (CLI)
├── src/
│   ├── parsers.py            # Normalización, parsing de texto, scoring
│   ├── deduplicator.py       # Deduplicación por URL y similitud
│   ├── scorer.py             # Pipeline de scoring
│   ├── exporter.py           # Exportación a JSON/CSV/metadata
│   └── sources/
│       ├── base.py           # Clase abstracta BaseSource
│       ├── demo_source.py    # Fuente demo con datos realistas (funcional)
│       └── inmuebles24_stub.py # Stub para Inmuebles24 (no implementado)
├── data/
│   ├── listings.json         # Anuncios exportados (leído por el dashboard)
│   ├── listings.csv          # CSV exportado
│   └── metadata.json         # Metadatos de la última ejecución
├── tests/
│   ├── test_parsers.py       # Tests de normalización, mascotas, requisitos, scores
│   ├── test_deduplicator.py  # Tests de deduplicación
│   └── test_scorer.py        # Tests de pipeline de scoring
├── dashboard.html            # Dashboard HTML responsive (modo claro/oscuro)
└── requirements.txt

.github/workflows/
└── update-rental-data.yml    # Workflow de actualización automática
```

## Instalación

```bash
git clone https://github.com/floresjorge/floresjorge.github.io
cd floresjorge.github.io/rental-monitor-gdl
pip install -r requirements.txt
```

## Uso local

```bash
# Con parámetros por defecto (Guadalajara Centro, $20,000 MXN máx.)
python collector.py

# Cambiar zona y precio máximo
python collector.py --zona "Zapopan" --precio-max 15000

# Especificar fuentes
python collector.py --sources demo

# Directorio de salida personalizado
python collector.py --output-dir /tmp/rental-data

# Modo verbose
python collector.py -v
```

Después de ejecutar, abre `dashboard.html` en tu navegador (doble clic o con un servidor HTTP local):

```bash
python -m http.server 8000
# Abre: http://localhost:8000/rental-monitor-gdl/dashboard.html
```

## Parámetros CLI

| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| `--zona` | `Guadalajara Centro` | Zona objetivo de búsqueda |
| `--precio-max` | `20000` | Precio máximo mensual en MXN |
| `--limite` | `100` | Máximo de anuncios por fuente |
| `--sources` | todas | Fuentes a usar: `demo`, `inmuebles24`, … |
| `--output-dir` | `data/` | Directorio de salida |
| `-v` / `--verbose` | `False` | Logging detallado |

## Despliegue en GitHub Pages

1. Habilita GitHub Pages en **Settings → Pages → Source: main branch**.
2. El dashboard estará en: `https://tuusuario.github.io/rental-monitor-gdl/dashboard.html`
3. Cada vez que GitHub Actions actualice `data/`, el dashboard mostrará los datos más recientes automáticamente.

## Actualización automática

El workflow `.github/workflows/update-rental-data.yml`:

- Se ejecuta **cada 12 horas** (6:00 AM y 6:00 PM UTC).
- Puede dispararse manualmente desde **Actions → Update Rental Data → Run workflow**.
- Solo hace commit si hubo cambios en `data/`.
- Usa `[skip ci]` en el mensaje de commit para no generar loops.

Para configurar fuentes reales en el futuro, agrega las API keys como **Secrets** en el repositorio:
- `INMUEBLES24_API_KEY` → cuando se implemente el conector de Inmuebles24.

## Scores explicados

### `score_calidad` (0–100)
Mide qué tan completo y confiable es el anuncio:

| Criterio | Puntos |
|----------|--------|
| Precio presente y > 0 | 15 |
| Zona o colonia presente | 10 |
| Tipo de inmueble presente | 10 |
| Recámaras > 0 | 10 |
| Metros cuadrados > 0 | 10 |
| Descripción > 100 chars | 15 (8 si > 50) |
| Política de mascotas detectada | 5 |
| Al menos un requisito detectado | 5 |
| URL válida | 5 |
| Fuente confiable | 5 |
| Zona de alta prioridad (Centro) | 10 |

### `score_confianza_extraccion` (0–100)
Mide qué tan confiablemente se extrajeron los datos:

| Criterio | Puntos |
|----------|--------|
| Precio extraído explícitamente | 8 |
| Recámaras extraídas | 8 |
| Baños extraídos | 6 |
| Metros extraídos | 6 |
| Colonia extraída | 8 |
| Tipo extraído | 8 |
| Mascotas detectadas | 6 |
| Requisitos detectados | 6 |
| Sin conflictos de parsing | 10 |
| Descripción original disponible | 8 |
| Fecha de publicación disponible | 8 |
| Sin inferencias débiles | 8 |
| URL válida y canónica | 10 |

## Cómo agregar nuevas fuentes

1. Crea `src/sources/mi_fuente.py` heredando de `BaseSource`:

```python
from .base import BaseSource

class MiFuente(BaseSource):
    name = "mi_fuente"
    base_url = "https://mi-fuente.com"

    def is_available(self) -> bool:
        return bool(os.getenv("MI_FUENTE_API_KEY"))

    def fetch_listings(self, zona, precio_max, limite=50):
        # Tu lógica de extracción aquí
        # Retorna lista de dicts con campos del esquema BaseSource
        ...
```

2. Regístrala en `src/sources/__init__.py`:

```python
from .mi_fuente import MiFuente
ALL_SOURCES["mi_fuente"] = MiFuente
```

3. Úsala:

```bash
python collector.py --sources mi_fuente demo
```

## Correr tests

```bash
python -m pytest tests/ -v
```

## Limitaciones y consideraciones éticas/legales

- **Scraping directo**: La mayoría de portales inmobiliarios prohíbe el scraping automatizado en sus Términos de Servicio. El proyecto está diseñado con una arquitectura de adaptadores para que puedas integrar fuentes autorizadas (APIs oficiales, feeds de datos con licencia) sin cambiar el pipeline principal.

- **Datos demo**: La fuente `demo` genera datos ficticios pero realistas para probar el pipeline completo sin necesidad de scraping. No inventa datos de anuncios reales.

- **robots.txt**: Cualquier conector que realice peticiones HTTP debe respetar `robots.txt` y límites de velocidad. El módulo `base.py` incluye `tenacity` para retries con backoff exponencial.

- **Datos personales**: No almacenes datos personales de arrendadores o inquilinos. Los anuncios son información pública de arrendamiento.

- **Responsabilidad**: Los datos son referenciales. Verifica siempre directamente con el anunciante antes de tomar decisiones.

## Tecnologías

- **Python 3.11+** – pipeline de datos
- **HTML + CSS + JS vanilla** – dashboard sin frameworks pesados
- **GitHub Actions** – automatización
- **GitHub Pages** – hosting estático gratuito
