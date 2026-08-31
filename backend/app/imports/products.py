"""Importación de Productos/existencias — resuelve A-30.

Contracara del importador de Referencias (`app/imports/catalog.py`): allá el
SKU es identidad y **debe ser único** (D-90); acá el mismo SKU puede aparecer
en muchas filas y cada aparición es legítima — son más unidades del mismo
producto (D-41: la existencia física es una entidad real, no un contador).

**La frontera unidad / variante, que es la decisión central de A-30:**

| Con el mismo SKU, la fila difiere en… | Vive en    | Resultado                    |
|---------------------------------------|------------|------------------------------|
| existencias                           | N `Item`   | se suman                     |
| proveedor                             | `Item`     | unidades de otro distribuidor|
| ubicación                             | `Item`     | unidades en otro lugar       |
| **nombre**                            | `Reference`| **variante `#N`** (D-90)     |
| marca / categoría / precio            | `Reference`| se ignora y se reporta       |

Proveedor y ubicación **no distinguen piezas**: son ejes de la unidad y el
modelo ya los tiene (`Item.provider_id`/`location_id`, nullable desde la
migración 0005; D-47 dice explícitamente que la misma Referencia puede tener
Ítems llegados de distribuidores distintos). El único discriminador es el
**nombre**, que es lo que D-89 midió sobre datos reales.

**El archivo nunca edita el catálogo** (decisión del dueño de producto). Cuando
el SKU ya existe, la Referencia manda: marca, categoría y precios del archivo
se ignoran y se reportan como discrepancias en la previsualización. Las
unidades nacen sin overrides, o sea siguiendo el precio **vigente** del
catálogo vía `COALESCE(Item.x, Reference.x)` (migraciones 0007/0008).

**Un solo planificador para previsualizar y para aplicar.** `plan()` no
escribe: decide qué haría cada fila y devuelve el plan; el endpoint de preview
lo cuenta y el de commit lo ejecuta. No es prolijidad — es la única forma de
que el número que se le promete al usuario sea el que realmente ocurre. En el
importador de Referencias esas dos cuentas se calculan por separado y ya
divergen cuando el archivo repite un SKU.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.money import parse_money
from app.core.sku import (
    FIRST_VARIANT_NUMBER,
    VARIANT_SEPARATOR,
    base_of,
    generate_sku,
    normalize_sku,
    variant_number,
    variant_sku,
)
from app.core.text import fold
from app.exports.products import COLUMNS, FORMAT_VERSION, KIND
from app.imports import generic as _generic
from app.imports.generic import ImportFormatError
from app.imports.names import NameIndex, build_brand_canonicalizer  # noqa: F401
from app.models.category import Category
from app.models.location import Location
from app.models.provider import Provider
from app.models.reference import Reference

#  Autocreado igual que Proveedor/Categoría cuando el archivo no trae ninguno
#  (mismo criterio D-42), y con el mismo nombre que ya usa el importador de
#  Referencias: los dos archivos tienen que caer en el mismo placeholder o el
#  Directorio termina con dos proveedores fantasma que significan lo mismo.
PLACEHOLDER_PROVIDER_NAME = "Proveedor sin especificar"

#  `Location.type` es NOT NULL con un CHECK de dos valores (D-25), así que
#  autocrear una ubicación exige elegir uno. `bodega` es el default honesto
#  para existencias: una sucursal es una decisión comercial que el dueño toma
#  explícitamente, un depósito es donde la mercadería simplemente está.
PLACEHOLDER_LOCATION_TYPE = "bodega"

#  Topes explícitos, no silenciosos. Una fila con `unidades = 5000` es casi
#  siempre un error de tipeo o una celda mal leída, y como cada unidad es una
#  fila de `Item` (D-41) el costo de creerle es real: 5000 INSERT. El tope del
#  archivo entero protege el tiempo de respuesta del endpoint.
MAX_UNITS_PER_ROW = 1000
MAX_UNITS_PER_IMPORT = 20_000


class ImportTooLargeError(Exception):
    """El archivo pide crear más unidades de las que una corrida acepta."""


@dataclass
class RowError:
    index: int
    sku: Optional[str]
    reason: str


@dataclass
class ParsedRow:
    index: int
    sku: str
    title: Optional[str]
    brand: Optional[str]
    category_name: Optional[str]
    #  Opcional a propósito: el placeholder se aplica recién si hay que CREAR
    #  una Referencia (su `provider_id` es NOT NULL). Ponerlo acá colgaría cada
    #  unidad de un proveedor fantasma cuando el archivo no trae la columna,
    #  y en `Item` el campo es nullable justamente para eso (migración 0005).
    provider_name: Optional[str]
    location_name: Optional[str]
    units: int
    base_price: Optional[Decimal]
    iva_percentage: Optional[Decimal]
    provider_price: Optional[Decimal]
    description: Optional[str]
    image_url: Optional[str]


@dataclass
class ParseResult:
    rows: list[ParsedRow] = field(default_factory=list)
    errors: list[RowError] = field(default_factory=list)


#  ── Lectura del archivo ───────────────────────────────────────────────────


def _to_decimal(value, field_name: str) -> Decimal:
    #  `parse_money` y no `Decimal(str(...))` (D-88): el origen puede mandar
    #  `"$ 332.900"`, donde el punto son miles.
    try:
        return parse_money(value)
    except ValueError:
        raise ValueError(f"{field_name} no es un número válido: {value!r}")


def _optional_price(item: dict, key: str, label: str) -> Optional[Decimal]:
    """Precio opcional y **estrictamente positivo** si viene."""
    if item.get(key) in (None, ""):
        return None
    value = _to_decimal(item[key], label)
    if value <= 0:
        raise ValueError(f"{label} tiene que ser mayor que cero: {value}")
    return value


def _resolve_iva(item: dict) -> Optional[Decimal]:
    if item.get("iva_percentage") in (None, ""):
        return None
    value = _to_decimal(item["iva_percentage"], "iva %")
    #  Rango cerrado, mismo que ya valida `ItemUpdate` para la edición manual
    #  (`Field(ge=0, le=100)`): un IVA fuera de ahí no es un porcentaje, y con
    #  `-100` la conversión de `price_offer` sería una división por cero.
    if not (Decimal(0) <= value <= Decimal(100)):
        raise ValueError(f"iva % tiene que estar entre 0 y 100: {value}")
    return value


def _resolve_base_price(item: dict, iva_percentage: Optional[Decimal]) -> Optional[Decimal]:
    """
    `base_price` si viene; si no, derivado de `price_offer` (D-87); si no hay
    ninguno, `None` — que acá **no es un error**: significa "esta unidad sigue
    el precio del catálogo". Recién es un problema si la fila tiene que crear
    la Referencia, y eso lo decide `plan()`, que sabe si el SKU existe.
    """
    explicit = _optional_price(item, "base_price", "precio base")
    if explicit is not None:
        return explicit
    offer = _optional_price(item, "price_offer", "precio final (con iva)")
    if offer is None:
        return None
    #  `price_offer` es el precio final CON IVA del sitio de origen (D-87).
    #  Con IVA ausente o 0 la división es por 1 y pasa tal cual.
    rate = Decimal(1) + (iva_percentage or Decimal(0)) / Decimal(100)
    return (offer / rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _resolve_units(item: dict) -> int:
    """
    Existencias de la fila. Ausente o vacía = **1**: el `_productos.xlsx` de
    `consolidate_scraped_catalog.py` (D-89) no trae la columna y cada una de
    sus filas es una pieza.

    Entero y positivo, sin fracciones: la unidad física es indivisible (D-41).
    """
    raw = item.get("units")
    if raw in (None, ""):
        return 1
    value = _to_decimal(raw, "existencias")
    if value != value.to_integral_value():
        raise ValueError(f"existencias tiene que ser un número entero: {value}")
    units = int(value)
    if units < 1:
        raise ValueError(f"existencias tiene que ser 1 o más: {units}")
    if units > MAX_UNITS_PER_ROW:
        raise ValueError(f"existencias supera el máximo por fila ({MAX_UNITS_PER_ROW}): {units}")
    return units


def parse_payload(payload: dict) -> ParseResult:
    """
    Valida el sobre (`kind`/`format_version`) y tipa cada fila, o la manda a
    `errors` con el motivo. Nunca lanza por una fila mala — solo por un archivo
    que no es del formato esperado (D-73).

    Captura `ArithmeticError` además de `ValueError`: las excepciones de
    `decimal` (`DivisionByZero`, `InvalidOperation`) **no** heredan de
    `ValueError`, así que atajar solo ése deja que una fila con un número
    absurdo tumbe el request entero en vez de reportarse como fila inválida.
    """
    if not isinstance(payload, dict) or payload.get("kind") != KIND:
        raise ImportFormatError(
            f"El archivo no es un archivo de Productos (kind={payload.get('kind')!r})"
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

        raw_sku = item.get("sku")
        #  `str(None)` da la cadena `"None"` y una celda vacía de Excel llega
        #  justo así (openpyxl entrega `None`) — el agujero que D-86 encontró
        #  en el importador de Referencias, cerrado acá desde el principio.
        sku = normalize_sku(str(raw_sku)) if raw_sku is not None else ""
        title = str(item["title"]).strip() if item.get("title") else None
        brand = str(item["brand"]).strip() if item.get("brand") else None
        #  Misma generación que el catálogo (D-86), determinista sobre
        #  título+marca: una fila sin código reimportada dos veces cae en el
        #  mismo `GEN-...` y suma unidades ahí en vez de inventar un producto
        #  nuevo por corrida.
        if not sku:
            sku = generate_sku(title, brand)

        try:
            iva_percentage = _resolve_iva(item)
            base_price = _resolve_base_price(item, iva_percentage)
            provider_price = _optional_price(item, "provider_price", "precio proveedor")
            units = _resolve_units(item)
        except (ValueError, ArithmeticError) as error:
            result.errors.append(RowError(index, sku, str(error)))
            continue

        result.rows.append(
            ParsedRow(
                index=index,
                sku=sku,
                title=title,
                brand=brand,
                category_name=(str(item["category"]).strip() if item.get("category") else None),
                provider_name=(str(item["provider"]).strip() if item.get("provider") else None),
                location_name=(str(item["location"]).strip() if item.get("location") else None),
                units=units,
                base_price=base_price,
                iva_percentage=iva_percentage,
                provider_price=provider_price,
                description=(str(item["description"]) if item.get("description") else None),
                image_url=(str(item["image_url"]) if item.get("image_url") else None),
                #  `sale_price` se ignora aunque venga (D-45): es derivada, y
                #  confiar en el valor del archivo es la única forma en que
                #  catálogo y existencias terminan divergiendo.
            )
        )

    return result


def xlsx_to_payload(content: bytes) -> dict:
    """Delegado al motor genérico (D-75), atado a las columnas de Productos."""
    return _generic.xlsx_to_payload(content, COLUMNS, KIND, FORMAT_VERSION)


def read_upload(filename: str, content_type: str, content: bytes) -> dict:
    """Detecta JSON vs. Excel y devuelve el payload canónico (D-74/D-75)."""
    return _generic.read_upload(filename, content_type, content, COLUMNS, KIND, FORMAT_VERSION)


#  ── Planificación ─────────────────────────────────────────────────────────

ACTION_UNITS = "units"
ACTION_NEW_REFERENCE = "new_reference"
ACTION_NEW_VARIANT = "new_variant"
ACTION_INVALID = "invalid"


@dataclass
class RowPlan:
    """Qué haría exactamente una fila. Lo mismo que cuenta el preview y ejecuta el commit."""

    row: ParsedRow
    action: str
    #  SKU final al que van las unidades — el de la fila, el de la variante
    #  nueva, o el de una variante que ya existía con ese nombre.
    target_sku: str
    #  Referencia ya existente a la que se enganchan las unidades. `None`
    #  cuando la Referencia todavía hay que crearla (`new_*`).
    reference: Optional[Reference] = None
    reason: Optional[str] = None
    #  Campos del archivo que difieren del catálogo y se ignoran a propósito.
    discrepancies: list[str] = field(default_factory=list)


@dataclass
class Plan:
    rows: list[RowPlan] = field(default_factory=list)

    @property
    def valid(self) -> list[RowPlan]:
        return [plan for plan in self.rows if plan.action != ACTION_INVALID]

    @property
    def total_units(self) -> int:
        return sum(plan.row.units for plan in self.valid)


def _load_groups(db: Session, tenant_id: uuid.UUID, skus: set[str]) -> dict[str, list[Reference]]:
    """
    Grupos de variantes de cada SKU base del archivo, en una sola consulta.

    Trae la pieza base y todo lo que arranque con `base#` (D-90). Es lo que
    permite decidir en memoria —sin una consulta por fila— si un nombre ya
    tiene variante y cuál es el próximo número libre.
    """
    bases = {base_of(sku) for sku in skus}
    if not bases:
        return {}

    conditions = [Reference.sku == base for base in bases]
    conditions += [
        Reference.sku.startswith(base + VARIANT_SEPARATOR, autoescape=True) for base in bases
    ]
    references = db.execute(
        select(Reference).where(Reference.tenant_id == tenant_id, or_(*conditions))
    ).scalars().all()

    groups: dict[str, list[Reference]] = {base: [] for base in bases}
    for reference in references:
        base = base_of(reference.sku)
        #  El `startswith` puede traer parientes de otro grupo si un SKU base
        #  es prefijo de otro; se filtra por base exacta.
        if base in groups:
            groups[base].append(reference)
    return groups


def _price_differs(row_value: Optional[Decimal], catalog_value: Optional[Decimal]) -> bool:
    if row_value is None or catalog_value is None:
        return False
    return row_value.compare(catalog_value) != 0


def _discrepancies(row: ParsedRow, reference: Reference, category_name: Optional[str]) -> list[str]:
    """
    Qué trae la fila que **no coincide** con el catálogo y se va a ignorar.

    No es una advertencia decorativa: es la contrapartida de "el archivo nunca
    edita el catálogo". El usuario tiene que poder ver que su archivo dice otra
    cosa, y decidir por su cuenta si corrige la Referencia desde su pantalla.
    """
    found = []
    if row.brand and fold(row.brand) != fold(reference.brand):
        found.append("marca")
    if row.category_name and fold(row.category_name) != fold(category_name):
        found.append("categoria")
    if _price_differs(row.base_price, reference.base_price):
        found.append("precio base")
    if _price_differs(row.iva_percentage, reference.iva_percentage):
        found.append("iva %")
    if _price_differs(row.provider_price, reference.provider_price):
        found.append("precio proveedor")
    return found


def plan(
    db: Session,
    tenant_id: uuid.UUID,
    rows: list[ParsedRow],
    create_missing: bool = True,
) -> Plan:
    """
    Decide qué hace cada fila **sin escribir nada**.

    Reglas, en orden:

    1. **SKU que no existe** → se crea la Referencia con los datos de la fila y
       se le cuelgan las unidades (A-30, decisión del dueño de producto: cargar
       el inventario inicial en una sola pasada). Con `create_missing=False` la
       fila queda inválida en vez de crear catálogo.
    2. **SKU que existe y el nombre coincide** (o la fila no trae nombre) →
       unidades de esa Referencia. Proveedor y ubicación van en cada `Item`.
    3. **SKU que existe con otro nombre** → variante. Si el grupo ya tiene una
       variante con ese mismo nombre se usa **esa** (reimportar el archivo no
       inventa `#3`, `#4`, `#5` de la misma pieza); si no, se reserva el
       próximo número libre.

    **Crear Referencia —sea nueva o variante— exige precio.** No hay default
    seguro para "cuánto vale esto" (D-83): $0 deja un producto vendible gratis,
    y heredar el precio de la pieza hermana es justo lo que D-89 midió que está
    mal (el mismo código cubría un disco de $93.900 y otro de $154.900). Sin
    precio la fila se reporta inválida, sin tumbar el resto del archivo.
    """
    if not rows:
        return Plan()

    skus = {row.sku for row in rows}
    groups = _load_groups(db, tenant_id, skus)
    by_sku = {
        reference.sku: reference for group in groups.values() for reference in group
    }
    category_names = _category_names(db, tenant_id, by_sku.values())

    #  Estado de la corrida: lo que ya se decidió crear, para que dos filas del
    #  mismo producto no produzcan dos Referencias ni dos variantes distintas.
    planned_references: set[str] = set()
    planned_variants: dict[tuple[str, str], str] = {}
    next_number: dict[str, int] = {}

    result = Plan()
    for row in rows:
        reference = by_sku.get(row.sku)

        if reference is None:
            if row.sku in planned_references:
                #  Segunda fila del mismo SKU nuevo: no crea otra Referencia,
                #  suma unidades a la que ya se planificó.
                result.rows.append(RowPlan(row, ACTION_UNITS, row.sku))
                continue
            if not create_missing:
                result.rows.append(
                    RowPlan(row, ACTION_INVALID, row.sku, reason="el SKU no existe en el catálogo")
                )
                continue
            if row.base_price is None:
                result.rows.append(
                    RowPlan(
                        row,
                        ACTION_INVALID,
                        row.sku,
                        reason="falta el precio: el SKU es nuevo y hay que crear la Referencia",
                    )
                )
                continue
            planned_references.add(row.sku)
            result.rows.append(RowPlan(row, ACTION_NEW_REFERENCE, row.sku))
            continue

        folded_row = fold(row.title)
        if not folded_row or folded_row == fold(reference.title):
            result.rows.append(
                RowPlan(
                    row,
                    ACTION_UNITS,
                    reference.sku,
                    reference=reference,
                    discrepancies=_discrepancies(row, reference, category_names.get(reference.id)),
                )
            )
            continue

        base = base_of(row.sku)
        sibling = next(
            (ref for ref in groups.get(base, []) if fold(ref.title) == folded_row), None
        )
        if sibling is not None:
            result.rows.append(
                RowPlan(
                    row,
                    ACTION_UNITS,
                    sibling.sku,
                    reference=sibling,
                    discrepancies=_discrepancies(row, sibling, category_names.get(sibling.id)),
                )
            )
            continue

        already = planned_variants.get((base, folded_row))
        if already is not None:
            result.rows.append(RowPlan(row, ACTION_UNITS, already))
            continue

        if row.base_price is None:
            result.rows.append(
                RowPlan(
                    row,
                    ACTION_INVALID,
                    row.sku,
                    reason=(
                        "falta el precio: el nombre no coincide con el del catálogo "
                        "y hay que crear una variante"
                    ),
                )
            )
            continue

        if base not in next_number:
            #  El número más alto manda, no el conteo (D-90): si alguien borró
            #  la variante 2, contar daría 3 y chocaría con la que ya existe.
            highest = max((variant_number(ref.sku) for ref in groups.get(base, [])), default=1)
            next_number[base] = max(highest + 1, FIRST_VARIANT_NUMBER)
        new_sku = variant_sku(base, next_number[base])
        next_number[base] += 1
        planned_variants[(base, folded_row)] = new_sku
        result.rows.append(RowPlan(row, ACTION_NEW_VARIANT, new_sku))

    return result


def _category_names(db: Session, tenant_id: uuid.UUID, references) -> dict[uuid.UUID, str]:
    """`Reference.id` → nombre de su categoría, para comparar contra el archivo."""
    ids = {ref.category_id for ref in references if ref.category_id is not None}
    if not ids:
        return {}
    rows = db.execute(
        select(Category.id, Category.name).where(
            Category.tenant_id == tenant_id, Category.id.in_(ids)
        )
    ).all()
    names = {category_id: name for category_id, name in rows}
    return {
        ref.id: names.get(ref.category_id)
        for ref in references
        if ref.category_id is not None and ref.category_id in names
    }


#  ── Resolución de FKs por nombre ──────────────────────────────────────────
#
#  Delegada a `app/imports/names.py`: la comparación es **plegada** (sin
#  mayúsculas, sin tildes, sin espacios de sobra — `app/core/text.py:fold`), no
#  un `.lower()`. Con el criterio viejo, `Pírelli` y `Pirelli` eran dos
#  proveedores distintos y cada archivo scrapeado sembraba duplicados que
#  después hay que unificar a mano.


def build_indexes(
    db: Session, tenant_id: uuid.UUID, batch_id: Optional[uuid.UUID] = None
) -> dict[str, NameIndex]:
    """
    Los tres índices que este importador necesita, en tres consultas.

    Se arma una vez por corrida —no por fila— y se comparte entre la
    previsualización y el commit, así lo que se anuncia como "proveedor nuevo"
    es exactamente lo que se va a crear.
    """
    return {
        "provider": NameIndex(db, tenant_id, Provider, Provider.title, batch_id),
        #  `Location.type` es NOT NULL con un CHECK de dos valores (D-25), así
        #  que autocrear obliga a elegir uno: `bodega` (ver constante arriba).
        "location": NameIndex(
            db, tenant_id, Location, Location.name, batch_id,
            defaults={"type": PLACEHOLDER_LOCATION_TYPE},
        ),
        "category": NameIndex(db, tenant_id, Category, Category.name, batch_id),
    }

