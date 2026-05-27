"""
Demo source: realistic simulated listings for Guadalajara.
Used for testing the full pipeline without live HTTP requests.
All data is fictional but geographically and economically plausible.
"""

import hashlib
import logging
from datetime import date, timedelta
from typing import Any

from .base import BaseSource
from ..parsers import (
    canonicalize_url,
    parse_pets_policy,
    parse_rental_requirements,
    normalize_text,
)

logger = logging.getLogger(__name__)

_ZONE_PRIORITY: dict[str, int] = {
    "guadalajara centro": 10,
    "centro": 10,
    "centro historico": 10,
    "analco": 9,
    "mexicaltzingo": 9,
    "santa teresa": 8,
    "santa tere": 8,
    "sagrada familia": 8,
    "artesanos": 7,
    "morelos": 7,
    "san sebastian": 7,
    "americana": 6,
    "chapalita": 5,
    "providencia": 5,
    "zapopan": 4,
    "tlaquepaque": 3,
}

# fmt: off
_RAW_LISTINGS: list[dict[str, Any]] = [
    {
        "titulo": "Casa en renta Centro Histórico, 3 rec, amplio jardín",
        "tipo": "Casa",
        "zona": "Guadalajara Centro",
        "colonia": "Centro",
        "municipio": "Guadalajara",
        "precio_mensual": 13500,
        "moneda": "MXN",
        "recamaras": 3,
        "banos": 2,
        "estacionamientos": 1,
        "metros_cuadrados": 140,
        "descripcion_original": (
            "Hermosa casa colonial en el corazón del Centro Histórico. "
            "3 recámaras amplias, 2 baños completos, sala, comedor, cocina integral equipada, "
            "pequeño jardín interior. Excelente iluminación natural. "
            "Requisitos: 2 meses de depósito, aval propietario, comprobante de ingresos. "
            "No se aceptan mascotas."
        ),
        "url": "https://demo.example.com/listing/gdl-centro-001",
        "fecha_publicacion": str(date.today() - timedelta(days=3)),
    },
    {
        "titulo": "Departamento en renta Colonia Analco, 2 recámaras, pet friendly",
        "tipo": "Departamento",
        "zona": "Guadalajara Centro",
        "colonia": "Analco",
        "municipio": "Guadalajara",
        "precio_mensual": 9800,
        "moneda": "MXN",
        "recamaras": 2,
        "banos": 1,
        "estacionamientos": 1,
        "metros_cuadrados": 75,
        "descripcion_original": (
            "Departamento luminoso en Analco, a pasos del Centro. "
            "2 recámaras, 1 baño, cocina equipada con refrigerador y estufa. "
            "Edificio seguro con vigilancia. "
            "Se aceptan mascotas pequeñas (máximo 10 kg). "
            "Requisitos: aval o póliza jurídica, 1 mes de depósito, "
            "comprobante de ingresos mínimo 3 veces la renta."
        ),
        "url": "https://demo.example.com/listing/gdl-analco-002",
        "fecha_publicacion": str(date.today() - timedelta(days=1)),
    },
    {
        "titulo": "Casa renta Mexicaltzingo 4 recámaras 2 baños jardín cochera",
        "tipo": "Casa",
        "zona": "Guadalajara Centro",
        "colonia": "Mexicaltzingo",
        "municipio": "Guadalajara",
        "precio_mensual": 15000,
        "moneda": "MXN",
        "recamaras": 4,
        "banos": 2,
        "estacionamientos": 2,
        "metros_cuadrados": 180,
        "descripcion_original": (
            "Amplia casa en Mexicaltzingo, zona tranquila y segura. "
            "4 recámaras, 2 baños completos, sala de TV, jardín grande y 2 cocheras. "
            "Ideal para familia. "
            "Requisitos: aval propietario en Guadalajara o Zapopan, 2 meses de depósito, "
            "investigación socioeconómica, comprobante de ingresos. "
            "No mascotas por favor."
        ),
        "url": "https://demo.example.com/listing/gdl-mexicaltzingo-003",
        "fecha_publicacion": str(date.today() - timedelta(days=5)),
    },
    {
        "titulo": "Departamento Santa Teresa 1 rec estudio moderno",
        "tipo": "Departamento",
        "zona": "Guadalajara Centro",
        "colonia": "Santa Tere",
        "municipio": "Guadalajara",
        "precio_mensual": 7500,
        "moneda": "MXN",
        "recamaras": 1,
        "banos": 1,
        "estacionamientos": 0,
        "metros_cuadrados": 48,
        "descripcion_original": (
            "Estudio moderno en Santa Tere, colonia con excelente ambiente. "
            "1 recámara integrada, baño completo, cocina americana, balcón. "
            "A 5 min caminando del Mercado Alcalde. "
            "Pet friendly: se aceptan mascotas con autorización previa. "
            "Sin aval, se acepta justicia alternativa o depósito equivalente a 1 mes."
        ),
        "url": "https://demo.example.com/listing/gdl-santatere-004",
        "fecha_publicacion": str(date.today() - timedelta(days=2)),
    },
    {
        "titulo": "Casa renta Sagrada Familia 3 recámaras con jardín y cochera",
        "tipo": "Casa",
        "zona": "Guadalajara Centro",
        "colonia": "Sagrada Familia",
        "municipio": "Guadalajara",
        "precio_mensual": 11000,
        "moneda": "MXN",
        "recamaras": 3,
        "banos": 2,
        "estacionamientos": 1,
        "metros_cuadrados": 120,
        "descripcion_original": (
            "Casa de dos plantas en Sagrada Familia. "
            "3 recámaras, 2 baños, sala-comedor amplio, jardín y cochera. "
            "Zona residencial tranquila, cerca de escuelas y supermercados. "
            "Requisitos: fiador con propiedad en la ZMG, 2 meses de depósito. "
            "Mascotas: sujeto a autorización del arrendador."
        ),
        "url": "https://demo.example.com/listing/gdl-sagradafamilia-005",
        "fecha_publicacion": str(date.today() - timedelta(days=7)),
    },
    {
        "titulo": "Departamento en renta Col. Artesanos 2 rec amueblado",
        "tipo": "Departamento",
        "zona": "Guadalajara Centro",
        "colonia": "Artesanos",
        "municipio": "Guadalajara",
        "precio_mensual": 8500,
        "moneda": "MXN",
        "recamaras": 2,
        "banos": 1,
        "estacionamientos": 1,
        "metros_cuadrados": 65,
        "descripcion_original": (
            "Departamento semi-amueblado en Artesanos. "
            "2 recámaras, 1 baño con regadera, cocina con estufa y alacena. "
            "Edificio tranquilo, control de acceso. "
            "Requiere: aval o póliza jurídica, 1 mes de depósito, estados de cuenta bancarios. "
            "No se aceptan perros grandes. Gatos permitidos."
        ),
        "url": "https://demo.example.com/listing/gdl-artesanos-006",
        "fecha_publicacion": str(date.today() - timedelta(days=4)),
    },
    {
        "titulo": "Casa histórica en renta Col. Morelos 3 rec amplio patio",
        "tipo": "Casa",
        "zona": "Guadalajara Centro",
        "colonia": "Morelos",
        "municipio": "Guadalajara",
        "precio_mensual": 12000,
        "moneda": "MXN",
        "recamaras": 3,
        "banos": 2,
        "estacionamientos": 1,
        "metros_cuadrados": 155,
        "descripcion_original": (
            "Casa de estilo colonial en Colonia Morelos. "
            "3 recámaras, 2 baños, sala amplia, comedor, cocina grande con estufa. "
            "Patio central y estacionamiento. Techos altos y pisos de mosaico original. "
            "Requisitos: obligado solidario o aval con propiedad, "
            "2 meses de depósito, comprobante de ingresos (3 veces la renta). "
            "Pet friendly: acepta mascotas pequeñas previo acuerdo."
        ),
        "url": "https://demo.example.com/listing/gdl-morelos-007",
        "fecha_publicacion": str(date.today() - timedelta(days=10)),
    },
    {
        "titulo": "Casa en renta Americana 4 rec 3 baños amplio jardín",
        "tipo": "Casa",
        "zona": "Americana",
        "colonia": "Americana",
        "municipio": "Guadalajara",
        "precio_mensual": 19500,
        "moneda": "MXN",
        "recamaras": 4,
        "banos": 3,
        "estacionamientos": 2,
        "metros_cuadrados": 220,
        "descripcion_original": (
            "Elegante casa en La Americana, una de las colonias más cotizadas de GDL. "
            "4 recámaras con closet, 3 baños completos, sala de TV, estudio, jardín trasero. "
            "Cocina integral con isla. Seguridad 24/7. "
            "Requisitos: aval propietario zona metropolitana, 3 meses de depósito, "
            "investigación socioeconómica, comprobantes de ingresos. "
            "No se aceptan mascotas."
        ),
        "url": "https://demo.example.com/listing/gdl-americana-008",
        "fecha_publicacion": str(date.today() - timedelta(days=6)),
    },
    {
        "titulo": "Departamento Providencia 2 rec vista panorámica",
        "tipo": "Departamento",
        "zona": "Providencia",
        "colonia": "Providencia",
        "municipio": "Guadalajara",
        "precio_mensual": 14000,
        "moneda": "MXN",
        "recamaras": 2,
        "banos": 2,
        "estacionamientos": 1,
        "metros_cuadrados": 90,
        "descripcion_original": (
            "Moderno departamento en Providencia, piso 8 con vista a la ciudad. "
            "2 recámaras, 2 baños, sala amplia, cocina abierta, terraza. "
            "Amenidades: gimnasio, área de asados, seguridad. "
            "Pet friendly (mascotas pequeñas hasta 8 kg). "
            "Requisitos: aval o póliza jurídica, 2 meses de depósito, "
            "comprobante de ingresos, referencias personales."
        ),
        "url": "https://demo.example.com/listing/gdl-providencia-009",
        "fecha_publicacion": str(date.today() - timedelta(days=2)),
    },
    {
        "titulo": "Casa en renta Chapalita 3 rec jardin piscina privada",
        "tipo": "Casa",
        "zona": "Chapalita",
        "colonia": "Chapalita",
        "municipio": "Guadalajara",
        "precio_mensual": 22000,
        "moneda": "MXN",
        "recamaras": 3,
        "banos": 3,
        "estacionamientos": 2,
        "metros_cuadrados": 250,
        "descripcion_original": (
            "Residencia en Chapalita con acabados de lujo. "
            "3 recámaras suite, 3 baños, sala-comedor, cocina italiana, jardín y piscina privada. "
            "Cuarto de servicio y lavandería. Seguridad 24 horas. "
            "Requisitos: aval propietario, 3 meses de depósito, "
            "investigación socioeconómica, estados de cuenta últimos 3 meses. "
            "No se admiten mascotas."
        ),
        "url": "https://demo.example.com/listing/gdl-chapalita-010",
        "fecha_publicacion": str(date.today() - timedelta(days=14)),
    },
    {
        "titulo": "Departamento Centro Histórico 1 rec económico cerca de plazas",
        "tipo": "Departamento",
        "zona": "Guadalajara Centro",
        "colonia": "Centro",
        "municipio": "Guadalajara",
        "precio_mensual": 6000,
        "moneda": "MXN",
        "recamaras": 1,
        "banos": 1,
        "estacionamientos": 0,
        "metros_cuadrados": 40,
        "descripcion_original": (
            "Departamento económico a metros del Teatro Degollado. "
            "1 recámara, 1 baño, sala-cocina integrada. Ideal para estudiante o profesionista. "
            "Sin estacionamiento, excelente acceso a transporte público. "
            "Sin aval, se acepta contrato de justicia alternativa. "
            "No mascotas."
        ),
        "url": "https://demo.example.com/listing/gdl-centro-011",
        "fecha_publicacion": str(date.today() - timedelta(days=1)),
    },
    {
        "titulo": "Casa San Sebastián 2 rec 1 baño patio amplio",
        "tipo": "Casa",
        "zona": "Guadalajara Centro",
        "colonia": "San Sebastianito",
        "municipio": "Guadalajara",
        "precio_mensual": 8000,
        "moneda": "MXN",
        "recamaras": 2,
        "banos": 1,
        "estacionamientos": 1,
        "metros_cuadrados": 90,
        "descripcion_original": (
            "Casa sencilla en San Sebastianito, cerca del Centro. "
            "2 recámaras, 1 baño, sala, cocina, patio grande. "
            "Buen acceso vial, zona tranquila. "
            "Requisitos: aval propietario, 1 mes de depósito. "
            "Se aceptan mascotas (perro o gato)."
        ),
        "url": "https://demo.example.com/listing/gdl-sansebastian-012",
        "fecha_publicacion": str(date.today() - timedelta(days=8)),
    },
    {
        "titulo": "Departamento Zapopan 2 rec frente a parque amueblado",
        "tipo": "Departamento",
        "zona": "Zapopan",
        "colonia": "Ciudad Granja",
        "municipio": "Zapopan",
        "precio_mensual": 11500,
        "moneda": "MXN",
        "recamaras": 2,
        "banos": 2,
        "estacionamientos": 1,
        "metros_cuadrados": 80,
        "descripcion_original": (
            "Departamento amueblado en Zapopan frente a parque. "
            "2 recámaras, 2 baños, sala comedor, cocina equipada, balcón. "
            "Incluye: internet, mantenimiento. Edificio con vigilancia. "
            "Pet friendly: mascotas bienvenidas con depósito adicional. "
            "Requisitos: 2 meses de depósito, comprobante de ingresos, referencias."
        ),
        "url": "https://demo.example.com/listing/zap-ciudadgranja-013",
        "fecha_publicacion": str(date.today() - timedelta(days=3)),
    },
    {
        "titulo": "Casa Tlaquepaque 3 rec remodelada jardín grande",
        "tipo": "Casa",
        "zona": "Tlaquepaque",
        "colonia": "El Vergel",
        "municipio": "Tlaquepaque",
        "precio_mensual": 9500,
        "moneda": "MXN",
        "recamaras": 3,
        "banos": 2,
        "estacionamientos": 1,
        "metros_cuadrados": 130,
        "descripcion_original": (
            "Casa completamente remodelada en Tlaquepaque. "
            "3 recámaras, 2 baños, sala, comedor, cocina integral, jardín amplio. "
            "Instalaciones nuevas, pisos y pintura recientes. "
            "Requisitos: fiador o 2 meses de depósito, comprobante de ingresos. "
            "No se aceptan mascotas."
        ),
        "url": "https://demo.example.com/listing/tlaq-vergel-014",
        "fecha_publicacion": str(date.today() - timedelta(days=11)),
    },
    {
        "titulo": "Departamento Col. Americana 3 rec loft amplio terraza",
        "tipo": "Departamento",
        "zona": "Americana",
        "colonia": "Americana",
        "municipio": "Guadalajara",
        "precio_mensual": 17000,
        "moneda": "MXN",
        "recamaras": 3,
        "banos": 2,
        "estacionamientos": 2,
        "metros_cuadrados": 130,
        "descripcion_original": (
            "Loft de lujo en La Americana con terraza privada. "
            "3 recámaras, 2 baños, sala doble altura, cocina gourmet, terraza con jacuzzi. "
            "Edificio boutique, solo 6 unidades. Seguridad biométrica. "
            "Acepta mascotas con restricciones (raza no peligrosa, máximo 2). "
            "Requisitos: aval propietario o póliza jurídica, 3 meses de depósito, "
            "investigación de crédito, estados de cuenta últimos 6 meses."
        ),
        "url": "https://demo.example.com/listing/gdl-americana-015",
        "fecha_publicacion": str(date.today() - timedelta(days=5)),
    },
    {
        "titulo": "Casa Centro Histórico 2 rec remodelada patio central",
        "tipo": "Casa",
        "zona": "Guadalajara Centro",
        "colonia": "Centro",
        "municipio": "Guadalajara",
        "precio_mensual": 10500,
        "moneda": "MXN",
        "recamaras": 2,
        "banos": 1,
        "estacionamientos": 0,
        "metros_cuadrados": 100,
        "descripcion_original": (
            "Hermosa casa de finales del siglo XIX restaurada en el Centro Histórico. "
            "2 recámaras, 1 baño grande, sala, comedor, cocina amplia con tiro libre, patio central. "
            "Vigas de madera originales, pisos de talavera. Sin estacionamiento propio "
            "pero hay estacionamientos públicos a metros. "
            "Se aceptan mascotas: gatos y perros pequeños (menos de 5 kg). "
            "Requisitos: aval con propiedad o justicia alternativa, 1 mes de depósito."
        ),
        "url": "https://demo.example.com/listing/gdl-centro-016",
        "fecha_publicacion": str(date.today() - timedelta(days=4)),
    },
    {
        "titulo": "Departamento Zapopan Norte 2 rec seguro económico",
        "tipo": "Departamento",
        "zona": "Zapopan",
        "colonia": "Zapopan Norte",
        "municipio": "Zapopan",
        "precio_mensual": 7200,
        "moneda": "MXN",
        "recamaras": 2,
        "banos": 1,
        "estacionamientos": 1,
        "metros_cuadrados": 60,
        "descripcion_original": (
            "Departamento seguro en Zapopan Norte. "
            "2 recámaras, 1 baño, sala-comedor, cocina con alacena. "
            "Estacionamiento incluido. Zona tranquila, buenas escuelas cercanas. "
            "Requiere: aval o 2 meses de depósito, recibo de nómina. "
            "Mascotas no permitidas."
        ),
        "url": "https://demo.example.com/listing/zap-norte-017",
        "fecha_publicacion": str(date.today() - timedelta(days=9)),
    },
    {
        "titulo": "Casa renta Col. Morelos GDL 3 rec con estudio y biblioteca",
        "tipo": "Casa",
        "zona": "Guadalajara Centro",
        "colonia": "Morelos",
        "municipio": "Guadalajara",
        "precio_mensual": 14500,
        "moneda": "MXN",
        "recamaras": 3,
        "banos": 3,
        "estacionamientos": 2,
        "metros_cuadrados": 200,
        "descripcion_original": (
            "Casa señorial en Colonia Morelos con estudio y biblioteca. "
            "3 recámaras suite, 3 baños, sala formal, sala de TV, comedor, estudio, biblioteca, "
            "jardín con fuente y 2 cocheras. Casa de dos plantas con techos de 4 metros. "
            "Requisitos: aval propietario, 2 meses de depósito, "
            "investigación socioeconómica, estados de cuenta. "
            "Mascotas: acepta gatos únicamente."
        ),
        "url": "https://demo.example.com/listing/gdl-morelos-018",
        "fecha_publicacion": str(date.today() - timedelta(days=12)),
    },
    {
        "titulo": "Departamento renta Analco 2 rec recién pintado a precio justo",
        "tipo": "Departamento",
        "zona": "Guadalajara Centro",
        "colonia": "Analco",
        "municipio": "Guadalajara",
        "precio_mensual": 8200,
        "moneda": "MXN",
        "recamaras": 2,
        "banos": 1,
        "estacionamientos": 1,
        "metros_cuadrados": 68,
        "descripcion_original": (
            "Departamento recién pintado y con muebles nuevos en Analco. "
            "2 recámaras, 1 baño completo, sala, cocina con refrigerador. "
            "Estacionamiento propio. Edificio con portero. "
            "Sin aval: aceptamos justicia alternativa o 2 meses de depósito. "
            "Pet friendly hasta 2 mascotas (perro pequeño o gato)."
        ),
        "url": "https://demo.example.com/listing/gdl-analco-019",
        "fecha_publicacion": str(date.today() - timedelta(days=2)),
    },
    {
        "titulo": "Casa Providencia 4 rec moderna seguridad privada",
        "tipo": "Casa",
        "zona": "Providencia",
        "colonia": "Providencia",
        "municipio": "Guadalajara",
        "precio_mensual": 25000,
        "moneda": "MXN",
        "recamaras": 4,
        "banos": 4,
        "estacionamientos": 3,
        "metros_cuadrados": 300,
        "descripcion_original": (
            "Residencia contemporánea en fraccionamiento privado en Providencia. "
            "4 recámaras suite, 4 baños, sala de cine, gimnasio, pool, jardín 200 m². "
            "Cocina de diseño, cuarto de servicio con baño. Seguridad privada 24/7, cámaras. "
            "Requisitos estrictos: aval propietario, 3 meses de depósito, "
            "investigación socioeconómica, comprobantes de ingresos mínimo 5 veces la renta, "
            "estados de cuenta últimos 6 meses, referencias bancarias. "
            "No mascotas por política del fraccionamiento."
        ),
        "url": "https://demo.example.com/listing/gdl-providencia-020",
        "fecha_publicacion": str(date.today() - timedelta(days=20)),
    },
    {
        "titulo": "Local / Departamento Centro uso mixto 1 rec",
        "tipo": "Otro",
        "zona": "Guadalajara Centro",
        "colonia": "Centro",
        "municipio": "Guadalajara",
        "precio_mensual": 5500,
        "moneda": "MXN",
        "recamaras": 1,
        "banos": 1,
        "estacionamientos": 0,
        "metros_cuadrados": 35,
        "descripcion_original": (
            "Espacio de uso mixto en planta baja del Centro. "
            "1 recámara al fondo, sala que puede ser estudio/recepción, pequeño baño. "
            "Ideal para profesionista o pequeño negocio. "
            "Sin aval, se acepta justicia alternativa. "
            "Sin información sobre mascotas."
        ),
        "url": "https://demo.example.com/listing/gdl-centro-021",
        "fecha_publicacion": str(date.today() - timedelta(days=15)),
    },
    {
        "titulo": "Departamento Santa Tere 3 rec con roof garden exclusivo",
        "tipo": "Departamento",
        "zona": "Guadalajara Centro",
        "colonia": "Santa Tere",
        "municipio": "Guadalajara",
        "precio_mensual": 16500,
        "moneda": "MXN",
        "recamaras": 3,
        "banos": 2,
        "estacionamientos": 2,
        "metros_cuadrados": 115,
        "descripcion_original": (
            "Penthouse en Santa Tere con roof garden privado y vista 360°. "
            "3 recámaras, 2 baños, sala amplia, comedor, cocina abierta equipada. "
            "Roof garden con asador y área lounge exclusivos para el piso. "
            "Pet friendly: mascotas bienvenidas con depósito reembolsable. "
            "Requisitos: póliza jurídica o aval propietario, 2 meses de depósito, "
            "comprobante de ingresos."
        ),
        "url": "https://demo.example.com/listing/gdl-santatere-022",
        "fecha_publicacion": str(date.today() - timedelta(days=6)),
    },
    {
        "titulo": "Casa en renta Col. Las Conchas GDL 2 rec económica",
        "tipo": "Casa",
        "zona": "Guadalajara Centro",
        "colonia": "Las Conchas",
        "municipio": "Guadalajara",
        "precio_mensual": 7800,
        "moneda": "MXN",
        "recamaras": 2,
        "banos": 1,
        "estacionamientos": 1,
        "metros_cuadrados": 85,
        "descripcion_original": (
            "Casa económica en Las Conchas, buena ubicación. "
            "2 recámaras, 1 baño, sala, comedor, cocina, cochera. "
            "Zona accesible, cerca de Periférico y mercados. "
            "Requisitos: fiador con propiedad o 2 meses de depósito. "
            "Mascotas: solo gatos, no perros."
        ),
        "url": "https://demo.example.com/listing/gdl-lasconchas-023",
        "fecha_publicacion": str(date.today() - timedelta(days=8)),
    },
    {
        "titulo": "Departamento Zapopan cerca Plaza Patria 2 rec nuevo",
        "tipo": "Departamento",
        "zona": "Zapopan",
        "colonia": "Atemajac",
        "municipio": "Zapopan",
        "precio_mensual": 10200,
        "moneda": "MXN",
        "recamaras": 2,
        "banos": 2,
        "estacionamientos": 1,
        "metros_cuadrados": 78,
        "descripcion_original": (
            "Departamento nuevo en edificio a 5 min de Plaza Patria. "
            "2 recámaras, 2 baños, sala comedor, cocina integral, balcón. "
            "Amenidades: gimnasio, área de asados, seguridad 24h. "
            "Acepta mascotas: perros y gatos (cualquier tamaño). "
            "Requisitos: 2 meses de depósito, comprobante de ingresos 3x la renta, "
            "aval o póliza jurídica."
        ),
        "url": "https://demo.example.com/listing/zap-atemajac-024",
        "fecha_publicacion": str(date.today() - timedelta(days=1)),
    },
    {
        "titulo": "Casa antigua Centro GDL sin datos de precio disponibles",
        "tipo": "Casa",
        "zona": "Guadalajara Centro",
        "colonia": "Centro",
        "municipio": "Guadalajara",
        "precio_mensual": None,
        "moneda": "MXN",
        "recamaras": 3,
        "banos": 2,
        "estacionamientos": 1,
        "metros_cuadrados": None,
        "descripcion_original": (
            "Casa antigua en el Centro, llame para más información. "
            "3 recámaras, amplio. Precio a convenir."
        ),
        "url": "https://demo.example.com/listing/gdl-centro-025",
        "fecha_publicacion": str(date.today() - timedelta(days=30)),
    },
]
# fmt: on


class DemoSource(BaseSource):
    name = "demo"
    base_url = "https://demo.example.com"

    def is_available(self) -> bool:
        return True

    def fetch_listings(
        self,
        zona: str,
        precio_max: int,
        limite: int = 50,
    ) -> list[dict[str, Any]]:
        logger.info("[demo] Fetching listings (zona=%s, precio_max=%d)", zona, precio_max)
        results: list[dict[str, Any]] = []
        today = str(date.today())

        for raw in _RAW_LISTINGS:
            listing = self._default_listing()
            listing.update(raw)

            # Filter by price (None price passes through for manual review)
            price = raw.get("precio_mensual")
            if price is not None and price > precio_max:
                continue

            # Set extraction date
            listing["fecha_extraccion"] = today

            # Canonical URL
            listing["url_canonica"] = canonicalize_url(listing["url"])

            # Unique ID based on canonical URL
            url_hash = hashlib.md5(listing["url_canonica"].encode()).hexdigest()[:8]
            listing["id"] = f"demo-{url_hash}"

            # Short description
            desc = listing.get("descripcion_original", "")
            listing["descripcion_corta"] = desc[:120].rstrip() + ("…" if len(desc) > 120 else "")

            # Zone priority
            zona_key = normalize_text(listing.get("colonia", "") + " " + listing.get("zona", ""))
            listing["prioridad_zona"] = max(
                (_ZONE_PRIORITY.get(k, 0) for k in _ZONE_PRIORITY if k in zona_key),
                default=1,
            )

            # Parse pets from description
            pet_data = parse_pets_policy([
                listing.get("titulo"),
                listing.get("descripcion_original"),
            ])
            listing.update(pet_data)

            # Parse rental requirements
            req_data = parse_rental_requirements([listing.get("descripcion_original")])
            listing.update(req_data)

            # Extraction flags (all explicit for demo)
            listing["_extraction_flags"] = {
                "precio_explicit": price is not None,
                "recamaras_explicit": raw.get("recamaras") is not None,
                "banos_explicit": raw.get("banos") is not None,
                "metros_explicit": raw.get("metros_cuadrados") is not None,
                "colonia_explicit": bool(raw.get("colonia")),
                "tipo_explicit": raw.get("tipo") != "No especificado",
                "parsing_conflict": False,
                "weak_inference": False,
            }

            results.append(listing)
            if len(results) >= limite:
                break

        logger.info("[demo] Returning %d listings", len(results))
        return results
