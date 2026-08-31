"""Serialización del catálogo de Referencias a los tres formatos de salida (D-73).

Referencia usa su propio módulo —y no directamente `app/exports/generic.py`—
porque resuelve Proveedor/Categoría por **nombre** (no son columnas propias de
`Reference`) y tiene una columna **calculada** (`sale_price`, D-45): ninguna de
las dos cosas la tienen las entidades de soporte del Directorio, que sí usan el
motor genérico sin envoltorio (`app/api/v1/directory_io.py`, D-75).

**El JSON es el formato de intercambio.** No lleva UUIDs —las FKs viajan por
nombre natural (criterio de D-42), que es lo que hace que el archivo signifique
algo en otra instalación— y la plata va como **string**, porque un número JSON
es un float y el dinero se maneja con decimal exacto (D-05, zona de alto riesgo
en CLAUDE.md).

**Excel y Markdown son salida humana** — ahí la plata va como número, o la
hoja no se puede sumar ni filtrar y deja de servirle al contador. La regla
general sigue siendo D-73 (asimetría deliberada: que algo salga en un formato
no implica que pueda volver a entrar por ahí), con **una excepción angosta**:
el propio .xlsx que este módulo produce, con su cabecera intacta, sí puede
reimportarse — no cualquier Excel, solo el nuestro (D-74,
`app/imports/catalog.py:xlsx_to_payload`). Markdown se queda sin vuelta.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from app.core.config import settings
from app.core.pricing import sale_price as _sale_price
from app.exports.generic import Column, build_renderers

#  Se versiona el formato, no el endpoint: un archivo guardado hoy tiene que
#  poder identificarse cuando el importador haya cambiado (D-73).
FORMAT_VERSION = 1
KIND = "catalog.references"

#  Orden deliberado: primero qué identifica al producto, después la cadena de
#  plata en el sentido en que se piensa el negocio — lo que **pago** (costo),
#  la base, el IVA y lo que **cobro**.
#  Solo SKU (identidad/dedup) y precio base se exigen de verdad: todo lo
#  demás tiene un valor por defecto razonable si el archivo no lo trae —
#  Nombre cae al SKU, Proveedor a un placeholder autocreado, IVA % a 0 (el
#  mismo default que ya tiene la columna en el modelo, D-19). Precio base
#  se queda obligatorio a propósito: no hay default seguro para "cuánto vale
#  esto" — un $0 por omisión es un producto vendible gratis, no una
#  aproximación razonable (zona de alto riesgo, CLAUDE.md).
#  Encabezados en **minúscula y sin tildes** (D-87): el archivo lo consume
#  tanto una persona como un scraper, y `categoria` se puede tipear sin
#  depender del teclado. El match además es insensible a mayúsculas y tildes,
#  así que `Categoría` de un archivo viejo sigue entrando igual.
#
#  Cada columna acepta también su `key` como encabezado (ver
#  `exports/generic.py:header_candidates`), así que `title`, `base_price` o
#  `image_url` sirven sin declararse acá — ése es el contrato estable para las
#  integraciones, independiente del idioma de la etiqueta.
COLUMNS: tuple[Column, ...] = (
    Column("sku", "sku", required=True, width=16),
    Column("title", "nombre", aliases=("titulo",), width=42),
    Column("brand", "marca", width=18),
    Column("provider", "proveedor", width=26),
    Column("category", "categoria", width=20),
    #  El sufijo "(sin iva)" no es cosmético: A-26 quedó abierto justamente
    #  porque el label no lo decía, y D-70 lo cerró fijando la convención.
    Column("provider_price", "precio proveedor (sin iva)", numeric=True, width=24),
    Column("base_price", "precio base", numeric=True, width=14),
    Column("iva_percentage", "iva %", numeric=True, width=8),
    Column("sale_price", "precio de venta", numeric=True, derived=True, width=16),
    Column("description", "descripcion", width=48),
    Column("image_url", "imagen", width=32),
    #  Precio final **con IVA** tal como lo publica el sitio de origen (D-87).
    #  No se guarda: se convierte a `base_price` dividiéndolo por (1 + iva/100)
    #  al importar, por eso es `import_only` y no sale en la exportación.
    Column("price_offer", "precio final (con iva)", numeric=True, import_only=True, width=20),
)

#  El archivo tiene que traer **al menos una** de las dos: o el precio base, o
#  el precio final con IVA del que derivarlo. Ninguna es obligatoria por sí
#  sola —de ahí que ambas vayan con `required=False`— pero un catálogo sin
#  ninguna columna de precio no es importable: D-83 dejó dicho por qué el
#  precio no admite un valor por defecto.
PRICE_COLUMN_GROUPS: tuple[tuple[str, ...], ...] = (("base_price", "price_offer"),)


def _decimal_str(value: Decimal | None) -> str | None:
    """
    Decimal → string con **dos decimales siempre**.

    Las columnas que salen de la BBDD ya vienen con escala 2 (`Numeric(12,2)`),
    pero `sale_price` se calcula y `Decimal('4332') * 50` da `216600` pelado.
    Sin normalizar, el mismo archivo mezclaría `"182000.00"` y `"216600"` y
    obligaría a quien lo lea a contemplar las dos formas.
    """
    return None if value is None else str(value.quantize(Decimal("0.01")))


def build_payload(rows) -> dict:
    """`rows` = tuplas `(Reference, provider_title, category_name)`."""
    items = []
    for reference, provider_title, category_name in rows:
        items.append(
            {
                "sku": reference.sku,
                "title": reference.title,
                "brand": reference.brand,
                "provider": provider_title,
                "category": category_name,
                "provider_price": _decimal_str(reference.provider_price),
                "base_price": _decimal_str(reference.base_price),
                "iva_percentage": _decimal_str(reference.iva_percentage),
                #  Se calcula con la función canónica de `core.pricing` (D-45 +
                #  redondeo a $50 de D-46). Nunca replicar la fórmula acá: una
                #  segunda implementación es el bug del día que cambie la regla.
                "sale_price": _decimal_str(
                    _sale_price(reference.base_price, reference.iva_percentage)
                ),
                "description": reference.description,
                #  Crudo a propósito (D-84): va la URL **externa** guardada, no
                #  la resuelta por `resolve_image_url()`. Una ruta local
                #  (`http://192.168.1.5:8000/static/...`) no significa nada en
                #  otra instalación, y D-73 pide justo lo contrario — que el
                #  archivo se entienda al abrirlo en otra parte. La imagen local
                #  viaja por el respaldo (D-33), no por el catálogo exportado.
                "image_url": reference.image_url,
            }
        )

    return {
        "format_version": FORMAT_VERSION,
        #  Distinto de `format_version` (D-76): éste dice qué build del
        #  backend generó el archivo, no qué esquema de columnas tiene.
        "platform_version": settings.app_version,
        "kind": KIND,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        #  Va SIEMPRE, no solo cuando el catálogo está vacío: es lo que convierte
        #  una exportación sin filas en una plantilla utilizable. Un `items: []`
        #  pelado no le enseña a nadie qué columnas hay ni cuáles son obligatorias.
        #  Incluye las `import_only` con su marca (D-87): es el contrato que lee
        #  una integración para saber qué encabezados puede mandar, y omitir
        #  `price_offer` acá lo dejaría indocumentado. `import_only: true` avisa
        #  que se acepta al subir pero nunca sale en los datos.
        "columns": [
            {
                "key": c.key,
                "label": c.label,
                "required": c.required,
                "derived": c.derived,
                "import_only": c.import_only,
            }
            for c in COLUMNS
        ],
        "items": items,
    }


RENDERERS = build_renderers(COLUMNS, sheet_title="Referencias", markdown_title="Catálogo de Referencias")
