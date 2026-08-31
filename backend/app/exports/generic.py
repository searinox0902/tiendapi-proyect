"""
Motor genérico de export/import (D-73/D-74, generalizado por D-75).

Extraído de `app/exports/catalog.py`: Referencia sigue con su módulo propio
porque resuelve Proveedor/Categoría por nombre y tiene una columna derivada
(precio de venta) — las entidades de soporte del Directorio (Proveedor,
Ubicación, Categoría, Cliente, Marca) no tienen ni relaciones que resolver ni
columnas calculadas, así que este motor —parametrizado por `Column`, `kind` y
`format_version`— les alcanza sin duplicar la lógica de renderizado tres
veces por entidad.

**El JSON es el formato de intercambio** (FKs por nombre natural cuando las
hay, plata como string — D-05). **Excel es la única excepción a la asimetría
de D-73**: el propio .xlsx que este módulo produce, con su cabecera intacta,
puede reimportarse (D-74). **Markdown se queda sin vuelta**, es solo para leer.
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter


@dataclass(frozen=True)
class Column:
    key: str
    label: str
    required: bool = False
    #  `Numeric` en la BBDD: sale como string en JSON y como número en la hoja.
    numeric: bool = False
    #  Calculada, no almacenada — un importador debe ignorarla siempre.
    derived: bool = False
    #  Se acepta al IMPORTAR pero no se emite al exportar (D-87). Para columnas
    #  que existen en el archivo de origen pero no en el modelo — ej.
    #  `price_offer`, que no se guarda: se convierte a `base_price` al entrar.
    import_only: bool = False
    #  Nombres extra que también se aceptan como encabezado. `key` y `label` ya
    #  se aceptan siempre, así que esto es solo para variantes adicionales.
    aliases: tuple[str, ...] = ()
    width: int = 18


def normalize_header(text: str) -> str:
    """
    Encabezado → forma comparable: sin tildes, sin mayúsculas, sin espacios de más.

    Es lo que permite que `Categoría`, `categoria` y `CATEGORÍA` sean la misma
    columna. Sin esto el match era exacto y sensible a mayúsculas, así que un
    archivo de un scraper —que escribe `sku`, no `SKU`— se rechazaba entero
    aunque trajera todos los datos correctos.
    """
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", without_accents).strip().lower()


def header_candidates(column: Column) -> set[str]:
    """
    Todos los encabezados que identifican a esta columna, ya normalizados.

    Incluye **`key`** además de `label`: es lo que hace que el nombre técnico en
    inglés (`base_price`, `image_url`) sirva como encabezado sin declararlo
    columna por columna — el contrato que consumen las integraciones.
    """
    return {normalize_header(value) for value in (column.label, column.key, *column.aliases)}


def export_columns(columns: tuple[Column, ...]) -> tuple[Column, ...]:
    """Las que SÍ se escriben al exportar — descarta las `import_only`."""
    return tuple(column for column in columns if not column.import_only)


def numeric_column_indexes(columns: tuple[Column, ...]) -> tuple[int, ...]:
    return tuple(index for index, column in enumerate(columns, start=1) if column.numeric)


def build_payload(
    items: list[dict],
    columns: tuple[Column, ...],
    kind: str,
    format_version: int,
    platform_version: str,
) -> dict:
    """
    `items` ya viene armado por el llamador (un dict por fila, mismas claves
    que `columns`) — este módulo no sabe nada de modelos de SQLAlchemy, cada
    entidad arma sus propios dicts (ver `app/api/v1/directory_io.py`).

    `platform_version` (D-76) es **distinto** de `format_version`: éste dice
    qué BUILD del backend generó el archivo (para diagnosticar compatibilidad
    a simple vista), aquél dice qué ESQUEMA de columnas tiene — pueden cambiar
    en momentos totalmente distintos y no hay que confundirlos.
    """
    return {
        "format_version": format_version,
        "platform_version": platform_version,
        "kind": kind,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        #  Va SIEMPRE, no solo cuando está vacío: es lo que convierte una
        #  exportación sin filas en una plantilla utilizable.
        "columns": [
            {
                "key": c.key,
                "label": c.label,
                "required": c.required,
                "derived": c.derived,
                "import_only": c.import_only,
            }
            for c in columns
        ],
        "items": items,
    }


def render_json(payload: dict) -> bytes:
    #  `ensure_ascii=False`: nombres con tildes/ñ no deberían escaparse a
    #  \uXXXX, eso vuelve el archivo ilegible para el humano que lo abra.
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def render_xlsx(
    payload: dict,
    columns: tuple[Column, ...],
    sheet_title: str,
    scope_rows: list[tuple[str, str]] | None = None,
) -> bytes:
    """
    `scope_rows` agrega una **segunda hoja "Alcance"** con pares
    etiqueta/valor — para archivos donde el contenido depende de filtros y el
    archivo suelto no dice cuál se aplicó (paquete de Facturación, D-78).
    Omitirlo deja el libro de una sola hoja, idéntico a antes: los seis
    exportadores que ya existen (Referencias + las 5 del Directorio) no pasan
    nada y no cambian de salida.
    """
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = sheet_title

    sheet.append([column.label for column in columns])
    for cell, column in zip(sheet[1], columns):
        #  La calculada se distingue a simple vista (gris, cursiva): en una
        #  hoja que el usuario va a editar, la que no debe tocar se tiene que
        #  ver distinta sin leer documentación.
        cell.font = (
            Font(bold=True, italic=True, color="808080") if column.derived else Font(bold=True)
        )
    #  Con miles de filas, perder la cabecera al bajar hace la hoja inservible.
    sheet.freeze_panes = "A2"

    for index, column in enumerate(columns, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = column.width

    for item in payload["items"]:
        row = []
        for column in columns:
            value = item.get(column.key)
            if column.numeric and value is not None:
                #  Decimal y no float: openpyxl lo escribe como número de la
                #  hoja sin pasar por binario intermedio.
                row.append(Decimal(value))
            else:
                row.append(value)
        sheet.append(row)

    #  Derivado de `columns` y no un rango fijo: con índices a mano, reordenar
    #  una columna deja el formato de moneda apuntando a la de al lado.
    numeric_indexes = numeric_column_indexes(columns)
    for row in sheet.iter_rows(min_row=2):
        for index in numeric_indexes:
            row[index - 1].number_format = "#,##0.00"

    if scope_rows:
        scope = workbook.create_sheet("Alcance")
        scope.column_dimensions["A"].width = 28
        scope.column_dimensions["B"].width = 52
        for label, value in scope_rows:
            scope.append([label, value])
        for row in scope.iter_rows(min_col=1, max_col=1):
            row[0].font = Font(bold=True)

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def render_markdown(payload: dict, columns: tuple[Column, ...], title: str) -> bytes:
    count = len(payload["items"])
    lines = [
        f"# {title}",
        "",
        f"Exportado: {payload['exported_at']}  ",
        f"Generado por TiendAPI v{payload.get('platform_version', '?')}  ",
        f"Filas: {count}",
        "",
    ]

    if count == 0:
        lines += [
            "> Vacío — la tabla de abajo queda como plantilla de las columnas",
            "> esperadas.",
            "",
        ]

    derived_labels = [c.label for c in columns if c.derived]
    if derived_labels:
        lines.append(
            f"`*` obligatoria · `ƒ` calculada, no se carga a mano: {', '.join(derived_labels)}."
        )
    else:
        lines.append("`*` obligatoria.")
    lines.append("")

    headers = [f"{c.label}{' *' if c.required else ''}{' ƒ' if c.derived else ''}" for c in columns]
    lines.append(f"| {' | '.join(headers)} |")
    lines.append(f"|{'|'.join(['---'] * len(columns))}|")

    for item in payload["items"]:
        cells = []
        for column in columns:
            value = item.get(column.key)
            #  Un `|` sin escapar dentro de un texto libre parte la fila y
            #  descuadra la tabla entera de ahí para abajo.
            cells.append("" if value is None else str(value).replace("|", "\\|"))
        lines.append(f"| {' | '.join(cells)} |")

    return "\n".join(lines).encode("utf-8")


def build_renderers(columns: tuple[Column, ...], sheet_title: str, markdown_title: str) -> dict:
    #  `export_columns` y no `columns`: una columna `import_only` se acepta al
    #  subir pero no tiene nada que emitir — no existe como dato guardado.
    columns = export_columns(columns)
    return {
        "json": (render_json, "application/json; charset=utf-8", "json"),
        "xlsx": (
            lambda payload: render_xlsx(payload, columns, sheet_title),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "xlsx",
        ),
        "markdown": (
            lambda payload: render_markdown(payload, columns, markdown_title),
            "text/markdown; charset=utf-8",
            "md",
        ),
    }
