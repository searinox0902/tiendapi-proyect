"""
Importación granular de Referencias desde el payload canónico (D-73/D-74).

Dos puertas de entrada — JSON y **Excel, el mismo .xlsx que produce**
`GET /references/export` (D-74) — que convergen en la **misma** forma
canónica antes de tocar `parse_payload()`. La lectura de ambos formatos vive
en `app/imports/generic.py` (D-75); lo que se queda acá es lo específico de
Referencia: resolver Proveedor/Categoría por nombre y descartar la columna
calculada. La asimetría de D-73 sigue en pie para cualquier OTRO origen: esto
no abre la puerta a un Excel arbitrario de un proveedor, solo a la plantilla
propia, con su cabecera intacta.

**Suma, no reemplaza** (nivel 3 de D-73): cada fila crea una Referencia nueva,
nunca actualiza una existente. El SKU es **único por tenant** desde D-90
(migración `0018`, revoca la unicidad blanda de D-73), y por eso un código
repetido no tumba el lote sino que tiene salida propia: se salta, o entra como
**variante** `#N` con ficha completa. La previsualización lo reporta antes.

Proveedor y Categoría se resuelven con `app/imports/names.py:NameIndex`, o sea
comparando el nombre **plegado** —sin mayúsculas, sin tildes, sin espacios de
sobra (`app/core/text.py:fold`)—: `Pírelli`, `PIRELLI` y `"Pirelli "` son el
mismo proveedor y no tres.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.money import parse_money
from app.core.sku import generate_sku, normalize_sku
from app.exports.catalog import COLUMNS, FORMAT_VERSION, KIND, PRICE_COLUMN_GROUPS
from app.imports import generic as _generic
from app.imports.generic import ImportFormatError
from app.imports.names import NameIndex, build_brand_canonicalizer  # noqa: F401
from app.models.category import Category
from app.models.provider import Provider
from app.models.reference import Reference

#  Vacío: ya no hay ninguna clave que se exija por presencia literal. El precio
#  sigue siendo obligatorio (D-83: es el único sin default seguro), pero puede
#  llegar por `base_price` **o** por `price_offer` (D-87) — un "una u otra" que
#  este chequeo de conjuntos no sabe expresar, así que lo resuelve
#  `_resolve_base_price()`, que además da un mensaje que nombra las dos.
#  Nombre, Proveedor e IVA % faltantes se completan con su default, y el SKU se
#  genera (D-86).
#
#  Distinto del `required` de la COLUMNA en `exports/catalog.py`, que sigue
#  exigiendo que el archivo TRAIGA la columna SKU, y de `PRICE_COLUMN_GROUPS`,
#  que exige alguna de las dos de precio: que a unas pocas filas les falte un
#  dato es normal en un catálogo scrapeado, pero un archivo sin columna de SKU
#  ni de precio no es una plantilla de Referencias — es otro archivo.
REQUIRED_KEYS: set[str] = set()

#  Autocreado igual que cualquier Proveedor por nombre (mismo criterio D-42 que
#  ya usa Categoría) cuando el archivo no trae ninguno — no bloquea la
#  importación por un dato que muchas fuentes scrapeadas simplemente no tienen.
PLACEHOLDER_PROVIDER_NAME = "Proveedor sin especificar"


@dataclass
class RowError:
    index: int
    sku: Optional[str]
    reason: str


@dataclass
class ParsedRow:
    sku: str
    title: str
    brand: Optional[str]
    provider_name: str
    category_name: Optional[str]
    provider_price: Optional[Decimal]
    base_price: Decimal
    iva_percentage: Decimal
    description: Optional[str]
    image_url: Optional[str]


@dataclass
class ParseResult:
    rows: list[ParsedRow] = field(default_factory=list)
    errors: list[RowError] = field(default_factory=list)


def _to_decimal(value, field_name: str) -> Decimal:
    #  Ver `app/core/money.py` (D-88): el punto puede ser separador de miles.
    try:
        return parse_money(value)
    except ValueError:
        raise ValueError(f"{field_name} no es un número válido: {value!r}")


def _resolve_base_price(item: dict, iva_percentage: Decimal) -> Decimal:
    """
    Precio base de la fila: `base_price` si viene, o derivado de `price_offer` (D-87).

    `price_offer` es el precio **final que publica el sitio de origen, con IVA
    incluido** — el supuesto normal del retail colombiano, y el que ya
    documenta `scripts/import_scraped_references.py`. Se convierte con
    `base_price = price_offer / (1 + iva/100)`.

    Con `iva_percentage = 0` —el default cuando el archivo no trae columna de
    IVA (D-83)— la división es por 1 y el precio pasa tal cual: ahí las dos
    columnas significan lo mismo, y la diferencia recién aparece el día que el
    archivo declare un IVA.

    `ROUND_HALF_UP` explícito y `Decimal` de punta a punta: es plata, zona de
    alto riesgo (CLAUDE.md). No se usa el redondeo a $50 de D-46 — ése es para
    el precio de VENTA de cara al mostrador, no para un costo intermedio.
    """
    if item.get("base_price") not in (None, ""):
        return _to_decimal(item["base_price"], "base_price")
    if item.get("price_offer") not in (None, ""):
        offer = _to_decimal(item["price_offer"], "price_offer")
        return (offer / (Decimal(1) + iva_percentage / Decimal(100))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    raise ValueError("falta el precio: se espera base_price o price_offer")


def parse_payload(payload: dict) -> ParseResult:
    """
    Valida el sobre (`kind`/`format_version`) y convierte cada `item` en una
    fila tipada, o la manda a `errors` con el motivo. Nunca lanza por una fila
    mala — solo por un archivo que no es del formato esperado, que es un error
    de raíz distinto (no tiene sentido seguir leyendo item por item).
    """
    if not isinstance(payload, dict) or payload.get("kind") != KIND:
        raise ImportFormatError(
            f"El archivo no es un catálogo de Referencias (kind={payload.get('kind')!r})"
            if isinstance(payload, dict)
            else "El archivo no tiene la estructura esperada"
        )
    if payload.get("format_version") != FORMAT_VERSION:
        raise ImportFormatError(
            f"Versión de formato no soportada: {payload.get('format_version')!r} "
            f"(esta versión del sistema espera {FORMAT_VERSION})"
        )

    result = ParseResult()
    for index, item in enumerate(payload.get("items") or []):
        if not isinstance(item, dict):
            result.errors.append(RowError(index, None, "fila no es un objeto válido"))
            continue

        missing = REQUIRED_KEYS - item.keys()
        if missing:
            result.errors.append(
                RowError(index, item.get("sku"), f"faltan campos: {', '.join(sorted(missing))}")
            )
            continue

        raw_sku = item.get("sku")
        #  El guardia contra `None` no es defensivo de más: `str(None)` da la
        #  cadena `"None"`, y una celda vacía de Excel llega justo así
        #  (openpyxl entrega `None`). Sin esto, esa fila creaba una Referencia
        #  con el SKU literal `"None"` y la previsualización la contaba como
        #  válida — se colaba en silencio.
        sku = normalize_sku(str(raw_sku)) if raw_sku is not None else ""
        brand = str(item["brand"]).strip() if item.get("brand") else None
        title = str(item["title"]).strip() if item.get("title") else None
        #  Misma normalización y misma generación que el alta manual (D-85/D-86):
        #  un lote de mil filas no puede entrar con otra convención de SKU que la
        #  del formulario, o el mismo producto cargado por las dos vías queda
        #  duplicado.
        if not sku:
            sku = generate_sku(title, brand)
        provider_name = str(item.get("provider") or "").strip() or PLACEHOLDER_PROVIDER_NAME

        try:
            #  El IVA se resuelve ANTES que el precio: si la fila trae
            #  `price_offer` en vez de `base_price`, la conversión lo necesita.
            iva_percentage = (
                _to_decimal(item["iva_percentage"], "iva_percentage")
                if item.get("iva_percentage") not in (None, "")
                else Decimal("0")
            )
            base_price = _resolve_base_price(item, iva_percentage)
        except ValueError as error:
            result.errors.append(RowError(index, sku, str(error)))
            continue

        try:
            result.rows.append(
                ParsedRow(
                    sku=sku,
                    #  D-83: el nombre cae al SKU. Cuando el SKU también se
                    #  generó, cae al `GEN-...` — feo pero honesto, y no hay
                    #  circularidad: generar ya usó el título, que era `None`.
                    title=title or sku,
                    brand=brand,
                    provider_name=provider_name,
                    category_name=(str(item["category"]).strip() if item.get("category") else None),
                    provider_price=(
                        _to_decimal(item["provider_price"], "provider_price")
                        if item.get("provider_price") not in (None, "")
                        else None
                    ),
                    base_price=base_price,
                    iva_percentage=iva_percentage,
                    description=(str(item["description"]) if item.get("description") else None),
                    image_url=(str(item["image_url"]) if item.get("image_url") else None),
                    #  `sale_price` se ignora aunque venga en el archivo (D-45):
                    #  es derivada, y confiar en el valor importado es la única
                    #  forma en que catálogo y archivo terminan divergiendo.
                )
            )
        except ValueError as error:
            result.errors.append(RowError(index, sku, str(error)))

    return result


def xlsx_to_payload(content: bytes) -> dict:
    """Delegado a `app/imports/generic.py` (D-75), atado a las columnas de Referencia."""
    return _generic.xlsx_to_payload(content, COLUMNS, KIND, FORMAT_VERSION, PRICE_COLUMN_GROUPS)


def read_upload(filename: str, content_type: str, content: bytes) -> dict:
    """Delegado a `app/imports/generic.py` (D-75): detecta JSON vs. Excel y devuelve el payload canónico."""
    return _generic.read_upload(
        filename, content_type, content, COLUMNS, KIND, FORMAT_VERSION, PRICE_COLUMN_GROUPS
    )


def existing_skus(db: Session, tenant_id: uuid.UUID, skus: list[str]) -> set[str]:
    if not skus:
        return set()
    return set(
        db.execute(
            select(Reference.sku).where(Reference.tenant_id == tenant_id, Reference.sku.in_(skus))
        ).scalars()
    )


def build_indexes(db: Session, tenant_id: uuid.UUID) -> dict[str, NameIndex]:
    """
    Índices de Proveedor y Categoría por nombre, en dos consultas por corrida.

    Reemplaza a los cuatro helpers que resolvían con `.lower()` uno por uno.
    Dos cambios de comportamiento, los dos buscados:

    1. **La comparación es plegada** (`app/core/text.py:fold`): sin mayúsculas,
       **sin tildes** y sin espacios de sobra. Antes `Pírelli` y `Pirelli` eran
       dos proveedores distintos y cada archivo scrapeado sembraba duplicados.
    2. **Dos grafías del mismo nombre en el mismo archivo caen en un registro**,
       porque lo autocreado entra al índice — antes el `cache` se llevaba solo
       las que coincidían carácter por carácter en minúscula.
    """
    return {
        "provider": NameIndex(db, tenant_id, Provider, Provider.title),
        "category": NameIndex(db, tenant_id, Category, Category.name),
    }
