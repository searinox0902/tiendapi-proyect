"""
Motor genérico de importación (D-73/D-74, generalizado por D-75).

A diferencia de `app/imports/catalog.py` (Referencia), las cinco entidades de
soporte del Directorio —Proveedor, Ubicación, Categoría, Cliente, Marca— no
tienen ninguna relación que resolver por nombre ni ninguna columna calculada:
cada fila del archivo se traduce directo a los kwargs del modelo. Por eso el
resultado de `parse_payload` acá es un `dict` plano por fila, no un dataclass
tipado como `ParsedRow` — no hay nada más que resolver después del parseo.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from io import BytesIO
from typing import Optional

from openpyxl import load_workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.money import parse_money
from app.core.text import fold
from app.exports.generic import Column, header_candidates, normalize_header

XLSX_CONTENT_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


class ImportFormatError(Exception):
    """El archivo no es un payload reconocible (kind/versión/estructura inválida)."""


@dataclass
class RowError:
    index: int
    key_value: Optional[str]
    reason: str


@dataclass
class ParseResult:
    rows: list[dict] = field(default_factory=list)
    errors: list[RowError] = field(default_factory=list)


def _to_decimal(value, field_label: str) -> Decimal:
    #  `parse_money` y no `Decimal(str(...))` (D-88): el origen puede mandar
    #  `"$ 332.900"`, donde el punto son miles. Parsear crudo daría `332.9` sin
    #  lanzar nada — un error de 1000x que se guarda en silencio.
    try:
        return parse_money(value)
    except ValueError:
        raise ValueError(f"{field_label} no es un número válido: {value!r}")


def parse_payload(
    payload: dict,
    columns: tuple[Column, ...],
    kind: str,
    format_version: int,
    natural_key: str,
) -> ParseResult:
    """
    Valida el sobre (`kind`/`format_version`) y convierte cada `item` en un
    dict `{columna.key: valor_ya_tipado}`, o lo manda a `errors` con el
    motivo. Nunca lanza por una fila mala — solo por un archivo que no es del
    formato esperado, que es un error de raíz distinto.

    Las columnas `derived=True` se ignoran siempre, aunque vengan en el
    archivo: nunca hay ninguna hoy en las entidades de soporte, pero el motor
    se comporta igual que el de Referencia por si alguna la suma después.
    """
    if not isinstance(payload, dict) or payload.get("kind") != kind:
        raise ImportFormatError(
            f"El archivo no es del tipo esperado (kind={payload.get('kind')!r})"
            if isinstance(payload, dict)
            else "El archivo no tiene la estructura esperada"
        )
    if payload.get("format_version") != format_version:
        raise ImportFormatError(
            f"Versión de formato no soportada: {payload.get('format_version')!r} "
            f"(esta versión del sistema espera {format_version})"
        )

    result = ParseResult()
    for index, item in enumerate(payload.get("items") or []):
        if not isinstance(item, dict):
            result.errors.append(RowError(index, None, "fila no es un objeto válido"))
            continue

        row: dict = {}
        error: Optional[str] = None
        for column in columns:
            if column.derived:
                continue
            raw = item.get(column.key)
            is_empty = raw is None or (isinstance(raw, str) and not raw.strip())
            if is_empty:
                if column.required:
                    error = f"falta {column.label}"
                    break
                row[column.key] = None
                continue
            if column.numeric:
                try:
                    row[column.key] = _to_decimal(raw, column.label)
                except ValueError as decimal_error:
                    error = str(decimal_error)
                    break
            else:
                row[column.key] = str(raw).strip()

        key_value = item.get(natural_key)
        key_value_str = str(key_value).strip() if key_value not in (None, "") else None
        if error:
            result.errors.append(RowError(index, key_value_str, error))
            continue
        result.rows.append(row)

    return result


def xlsx_to_payload(
    content: bytes,
    columns: tuple[Column, ...],
    kind: str,
    format_version: int,
    required_any: tuple[tuple[str, ...], ...] = (),
) -> dict:
    """
    Traduce un .xlsx al mismo payload que produce el JSON — de ahí en adelante
    corre `parse_payload()`, sin lógica de negocio duplicada entre las dos
    puertas de entrada.

    Match por **nombre de columna**, no por posición: reordenar columnas en
    Excel no rompe nada. Desde D-87 el nombre se compara **normalizado** (sin
    tildes, sin mayúsculas) y contra la `key` además de la etiqueta, así que
    `Categoría`, `categoria` y `category` son la misma columna — es lo que
    permite subir el archivo de un scraper sin renombrarle los encabezados.

    `required_any` expresa "al menos una de estas": grupos de claves donde el
    archivo debe traer alguna. El `required` de cada `Column` no alcanza para
    eso — pide una columna concreta, y acá cualquiera del grupo sirve.
    """
    try:
        workbook = load_workbook(BytesIO(content), data_only=True, read_only=True)
        sheet = workbook.active
        rows = sheet.iter_rows(values_only=True)
        header_row = next(rows)
    except Exception as error:
        raise ImportFormatError(f"No se pudo leer el archivo Excel: {error}")

    lookup: dict[str, Column] = {}
    for column in columns:
        for candidate in header_candidates(column):
            #  `setdefault`: si dos columnas declararan el mismo alias, gana la
            #  primera en el orden de `COLUMNS` en vez de la última en ganar la
            #  carrera, que sería un empate resuelto al azar.
            lookup.setdefault(candidate, column)

    header_map: dict[int, Column] = {}
    columns_ignored: list[str] = []
    for index, cell in enumerate(header_row):
        raw = str(cell).strip() if cell is not None else ""
        if not raw:
            continue
        column = lookup.get(normalize_header(raw))
        if column is None:
            columns_ignored.append(raw)
            continue
        header_map[index] = column

    found_keys = {column.key for column in header_map.values()}
    missing = {c.key for c in columns if c.required} - found_keys
    if missing:
        missing_labels = [c.label for c in columns if c.key in missing]
        raise ImportFormatError(
            "Faltan columnas obligatorias, o cambiaron de nombre: " + ", ".join(missing_labels)
        )

    for group in required_any:
        if not (set(group) & found_keys):
            options = " o ".join(c.label for c in columns if c.key in group)
            raise ImportFormatError(f"El archivo debe traer al menos una de estas columnas: {options}")

    #  Diagnóstico para el preview (no forma parte del payload canónico que
    #  consume `parse_payload`): qué columnas el archivo SÍ trae, cuáles no y
    #  cuáles no se reconocieron —para que el usuario sepa, antes de confirmar,
    #  qué campos van a quedar con su valor por defecto y qué columnas suyas se
    #  están descartando, sin tener que deducirlo de la lista de filas inválidas.
    #
    #  Las derivadas nunca se esperan de entrada, y las `import_only` ausentes
    #  no son una carencia (son una vía alternativa): ninguna va en `missing`.
    columns_detected = [c.label for c in columns if c.key in found_keys and not c.derived]
    columns_missing = [
        c.label
        for c in columns
        if c.key not in found_keys and not c.derived and not c.import_only
    ]

    items = []
    for row in rows:
        #  Fila totalmente vacía (común al final de una hoja editada a mano).
        if row is None or all(cell is None or str(cell).strip() == "" for cell in row):
            continue
        item: dict = {}
        for index, column in header_map.items():
            value = row[index] if index < len(row) else None
            if value is None or (isinstance(value, str) and not value.strip()):
                item[column.key] = None
            elif column.numeric:
                #  openpyxl entrega `float`/`int` cuando la celda es numérica,
                #  pero un scraper suele dejarla como TEXTO (`"$ 332.900"`).
                #  `parse_money` cubre los dos casos y respeta el punto como
                #  separador de miles (D-88); sin eso el precio entraba
                #  dividido por mil sin que nada fallara.
                try:
                    item[column.key] = str(parse_money(value))
                except ValueError:
                    item[column.key] = str(value)  # se reporta como fila inválida en parse_payload
            else:
                item[column.key] = str(value).strip()
        items.append(item)

    return {
        "format_version": format_version,
        "kind": kind,
        "items": items,
        "columns_detected": columns_detected,
        "columns_missing": columns_missing,
        "columns_ignored": columns_ignored,
    }


def read_upload(
    filename: str,
    content_type: str,
    content: bytes,
    columns: tuple[Column, ...],
    kind: str,
    format_version: int,
    required_any: tuple[tuple[str, ...], ...] = (),
) -> dict:
    """Detecta JSON vs. Excel por nombre/tipo y devuelve siempre el mismo payload canónico."""
    is_xlsx = filename.lower().endswith(".xlsx") or content_type in XLSX_CONTENT_TYPES
    if is_xlsx:
        return xlsx_to_payload(content, columns, kind, format_version, required_any)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        raise ImportFormatError("El archivo no es JSON ni Excel (.xlsx) válido")


def find_existing_keys(
    db: Session, tenant_id: uuid.UUID, model, key_column, values: set[str], normalizer=fold
) -> set[str]:
    """
    Valores de `values` (clave natural, ej. nombre/NIT) que ya existen en
    `model.<key_column>` para este tenant.

    **Comparación normalizada.** Por defecto `app/core/text.py:fold`: sin
    mayúsculas, sin tildes y sin espacios de sobra. Antes era `.lower()` a
    secas, que dejaba entrar `Pírelli` junto a `Pirelli` y `"Marca "` junto a
    `"Marca"` como registros distintos — justo la redundancia que el Directorio
    existe para evitar. Lo que NO hace es adivinar: `Pirelli` y `Pirreli`
    siguen siendo dos.

    `normalizer` se cambia cuando la clave natural no es un nombre: Cliente se
    identifica por NIT y usa `app/core/nit.py`, donde lo que sobra es el
    formato (`900.456.123-4` = `900456123-4`) y no las tildes (D-94).

    Devuelve los valores **plegados**; el llamador cruza con `fold()` sobre sus
    propios valores para recuperar la grafía original del archivo.
    """
    if not values:
        return set()
    folded_values = {normalizer(v) for v in values}
    existing_folded = {
        normalizer(v)
        for v in db.execute(
            select(key_column).where(model.tenant_id == tenant_id)
        ).scalars()
        if v is not None
    }
    #  El vacío no es una clave: un NIT ausente no "coincide" con otro ausente
    #  (D-94, sin documento no se deduplica), y lo mismo vale para un nombre
    #  que quedó en nada al normalizar.
    return (folded_values & existing_folded) - {""}
