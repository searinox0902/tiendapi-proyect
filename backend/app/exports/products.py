"""Serialización de Productos/existencias — contrato de columnas de A-30.

Hermano de `app/exports/catalog.py` (Referencias), con una diferencia de
fondo: **una fila no es un producto, es un grupo de unidades**. El catálogo
tiene una fila por SKU; acá una fila dice "N existencias de este SKU, de este
proveedor, en esta ubicación" y se traduce a **N filas de `Item`** (D-41: la
unidad física es una entidad real, no un contador).

**Por qué las columnas de Referencia también están acá** (nombre, marca,
categoría, precios, descripción, imagen): un archivo de existencias puede
traer SKUs que el catálogo todavía no tiene, y en ese caso la Referencia se
crea con esos datos en la misma pasada (A-30, decisión del dueño de producto)
— sin eso, cargar el inventario inicial de un negocio nuevo exigiría dos
archivos y dos pasadas. Cuando el SKU **ya existe**, esas columnas no editan
nada: la Referencia manda y las diferencias se reportan en la previsualización.

**Ninguna columna de precio es obligatoria, a diferencia del catálogo (D-83).**
Una unidad sin precio propio no es un dato faltante: es una unidad que sigue
el precio vigente del catálogo (`COALESCE(Item.x, Reference.x)`, migraciones
0007/0008). El precio recién se vuelve imprescindible cuando la fila tiene que
**crear** la Referencia, y eso se valida por fila, no rechazando el archivo.

**El agrupamiento del export es el que hace posible reimportarlo** (D-74): se
agrupa por todo lo que se emite —Referencia, proveedor, ubicación y los
overrides de precio de la unidad— así que volver a subir el archivo reproduce
exactamente las mismas unidades. Solo salen las existencias `available`: una
unidad vendida o dada de baja no es inventario (mismo criterio que
`items.py:_available_join`), y reimportarla resucitaría stock que no existe.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from app.core.config import settings
from app.core.pricing import sale_price as _sale_price
from app.exports.generic import Column, build_renderers

#  Se versiona el formato, no el endpoint (D-73).
FORMAT_VERSION = 1
KIND = "stock.products"

#  Orden deliberado: primero qué unidad es (SKU/nombre), después dónde y de
#  quién vino —lo propio de la existencia, que es lo que este archivo aporta
#  sobre el de Referencias— y al final la cadena de plata heredada del catálogo.
#
#  Encabezados en minúscula y sin tildes (D-87). Cada columna acepta además su
#  `key` como encabezado (`exports/generic.py:header_candidates`), así que
#  `units`, `base_price` o `image_url` sirven sin declararse alias.
#
#  **Solo `sku` es obligatoria en el archivo.** Es lo único sin lo cual una
#  fila no dice de qué producto habla; todo lo demás tiene un default honesto:
#  existencias → 1, proveedor/ubicación → sin asignar (la columna del modelo es
#  nullable desde la migración 0005), precios → los del catálogo.
COLUMNS: tuple[Column, ...] = (
    Column("sku", "sku", required=True, width=16),
    #  Discriminador de variante (A-30 + D-89): con el mismo SKU, un nombre
    #  distinto es la única evidencia medida de que la fila habla de OTRA
    #  pieza — `41080-0578-11H` es a la vez disco delantero y trasero. Ni el
    #  proveedor ni la ubicación distinguen piezas: son ejes de la unidad.
    Column("title", "nombre", aliases=("titulo",), width=42),
    Column("brand", "marca", width=18),
    Column("category", "categoria", width=20),
    #  Del ÍTEM, no de la Referencia: a quién se le compró ESTA unidad (D-47).
    #  Que dos filas del mismo SKU traigan proveedores distintos no es un
    #  conflicto — son unidades del mismo producto compradas a distribuidores
    #  distintos, que es exactamente lo que `Item.provider_id` modela.
    Column("provider", "proveedor", width=26),
    #  Del ÍTEM: dónde está físicamente (D-25). Mismo criterio que proveedor.
    Column("location", "ubicacion", width=22),
    #  El dato que define este archivo (A-30). Ausente o vacía = 1 unidad: el
    #  `_productos.xlsx` que ya produce `consolidate_scraped_catalog.py` (D-89)
    #  no trae la columna y cada una de sus filas es una pieza.
    Column("units", "existencias", aliases=("unidades", "cantidad"), numeric=True, width=14),
    Column("provider_price", "precio proveedor (sin iva)", numeric=True, width=24),
    Column("base_price", "precio base", numeric=True, width=14),
    Column("iva_percentage", "iva %", numeric=True, width=8),
    Column("sale_price", "precio de venta", numeric=True, derived=True, width=16),
    Column("description", "descripcion", width=48),
    Column("image_url", "imagen", width=32),
    #  Precio final **con IVA** publicado por el origen (D-87): no se guarda,
    #  se convierte a `base_price` dividiendo por (1 + iva/100) al importar.
    Column("price_offer", "precio final (con iva)", numeric=True, import_only=True, width=20),
)


def _decimal_str(value: Decimal | None) -> str | None:
    """Decimal → string con dos decimales siempre (mismo criterio que el catálogo)."""
    return None if value is None else str(value.quantize(Decimal("0.01")))


def build_payload(rows) -> dict:
    """
    `rows` = tuplas `(Reference, provider_title, location_name, category_name,
    base_price, iva_percentage, provider_price, units)` — los tres precios ya
    resueltos con `COALESCE(Item.x, Reference.x)` por el llamador, y `units`
    contado sobre el grupo.

    La plata va como **string** por lo mismo que en el catálogo: un número JSON
    es un float y el dinero se maneja con decimal exacto (D-05).
    """
    items = []
    for reference, provider_title, location_name, category_name, base, iva, cost, units in rows:
        items.append(
            {
                "sku": reference.sku,
                "title": reference.title,
                "brand": reference.brand,
                "category": category_name,
                "provider": provider_title,
                "location": location_name,
                #  Entero: son unidades contables, no una magnitud continua.
                #  `Item.quantity` (`Numeric(12,3)`) quedó sin uso justamente
                #  porque el sistema cuenta filas, no cantidades (D-41, A-30).
                "units": str(units),
                "provider_price": _decimal_str(cost),
                "base_price": _decimal_str(base),
                "iva_percentage": _decimal_str(iva),
                #  Calculado con la función canónica (D-45 + redondeo de D-46),
                #  nunca replicando la fórmula acá.
                "sale_price": _decimal_str(_sale_price(base, iva)),
                "description": reference.description,
                #  Crudo, la URL externa guardada (D-84): una ruta local no
                #  significa nada en otra instalación.
                "image_url": reference.image_url,
            }
        )

    return {
        "format_version": FORMAT_VERSION,
        "platform_version": settings.app_version,
        "kind": KIND,
        "exported_at": datetime.now(timezone.utc).isoformat(),
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


RENDERERS = build_renderers(
    COLUMNS, sheet_title="Productos", markdown_title="Existencias por Producto"
)
