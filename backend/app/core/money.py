"""Lectura de importes escritos como texto (D-88).

Un scraper no entrega números: entrega `"$\xa0332.900"` — con símbolo de
moneda, con **espacio duro** (U+00A0, no un espacio normal) y con el punto
como **separador de miles** a la colombiana.

**El riesgo acá no es que falle, es que funcione mal.** `Decimal("332.900")`
no lanza ningún error: devuelve `332.9`, un precio **mil veces menor** que se
guarda tan campante y solo se nota cuando los márgenes salen absurdos. Quitar
el `$` y parsear —la solución obvia— es exactamente cómo se produce ese bug.
De ahí que esto viva en `app/core/` con las demás reglas de dinero
(`pricing.py`) y no como un `.replace()` suelto en el importador: es zona de
alto riesgo (CLAUDE.md) y necesita un solo lugar donde mirarla.

Convención es-CO: **punto = miles, coma = decimales** (`1.234.567,89`).
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

#  Se conserva solo lo que puede formar parte de un número. Barre `$`, `COP`,
#  espacios normales y duros, y cualquier adorno que traiga el origen.
_NON_NUMERIC = re.compile(r"[^\d,.\-]")


def _looks_like_thousands(groups: list[str]) -> bool:
    """
    `["332", "900"]` → sí (miles). `["332", "9"]` → no (decimal).

    El criterio es que **todos** los grupos después del primero midan exacto 3
    dígitos: así se escriben los miles y así vienen las 1497 filas del catálogo
    real. Un grupo final de 1 o 2 dígitos (`12.50`) no puede ser un millar, así
    que ahí el separador es decimal.
    """
    return len(groups) > 1 and all(len(group) == 3 for group in groups[1:])


def parse_money(value) -> Decimal:
    """
    Texto o número → `Decimal` exacto. Lanza `ValueError` si no hay número que leer.

    - `"$\xa0332.900"` → `Decimal("332900")`
    - `"$ 1.234.567,89"` → `Decimal("1234567.89")`
    - `"19,5"` → `Decimal("19.5")`   (sirve igual para el % de IVA)
    - `"Consultar"` → `ValueError`   (la fila se reporta inválida, no se inventa un precio)

    Nunca pasa por `float`: la regla del proyecto es aritmética decimal exacta
    de punta a punta (D-05).
    """
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        #  Antes que `int`: en Python `True` es 1, y un booleano como precio es
        #  un dato corrupto, no el número uno.
        raise ValueError(f"no es un importe válido: {value!r}")
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        #  Vía `str()`: `Decimal(0.1)` arrastra la basura binaria del float.
        return Decimal(str(value))

    cleaned = _NON_NUMERIC.sub("", str(value))
    if not cleaned or cleaned in {"-", ".", ","}:
        raise ValueError(f"no es un importe válido: {value!r}")

    has_dot, has_comma = "." in cleaned, "," in cleaned
    if has_dot and has_comma:
        #  Con los dos presentes, el que aparece **último** es el decimal. Así
        #  entra tanto `1.234,56` (es-CO) como `1,234.56` (en-US) sin tener que
        #  saber de antemano quién generó el archivo.
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif has_comma:
        #  Un solo tipo de separador y es coma: decimal, por convención local.
        #  `"19,5"` es 19.5 — el caso que importa es el % de IVA tecleado a mano.
        cleaned = cleaned.replace(",", ".")
    elif has_dot and _looks_like_thousands(cleaned.split(".")):
        cleaned = cleaned.replace(".", "")

    try:
        return Decimal(cleaned)
    except InvalidOperation:
        raise ValueError(f"no es un importe válido: {value!r}")
