"""Comparación de NIT/cédula — misma idea que `text.py:fold`, otro tipo de dato.

Un NIT no es un nombre: no tiene mayúsculas ni tildes, tiene **separadores de
formato**. Sobre los clientes reales del sistema conviven las dos escrituras —
`900456123-4` (con guion del dígito de verificación) y `71234567` (pelado)— y
nada impide que alguien escriba `900.456.123-4`, que es como lo imprime una
factura. Comparar literal deja las tres como identidades distintas, que es
justo la duplicidad que el NIT existe para evitar.

**Solo se descarta el formato, no se interpreta el número.** `900.456.123-4` y
`900456123-4` son el mismo documento escrito distinto: certeza. En cambio
`900456123-4` y `900456123` —el mismo NIT con y sin dígito de verificación—
**se dejan distintos**: parece obvio que son el mismo, pero afirmarlo exige
saber que ese `4` es un DV y no el último dígito del número, y eso ya es
deducir. Mismo límite que `fold` con `Pirelli`/`Pirreli` (D-93): se fusiona lo
que se puede demostrar, no lo que se puede suponer.
"""
from __future__ import annotations

import re

#  Todo lo que no sea alfanumérico es formato: puntos de miles, guion del DV,
#  espacios. Se conservan las letras porque algunos documentos las llevan
#  (cédula de extranjería, pasaporte) y ahí sí distinguen.
_FORMATO = re.compile(r"[^0-9A-Za-z]")


def normalize_nit(value: str | None) -> str:
    """
    `"900.456.123-4"` → `"9004561234"`. `None` y vacío dan `""`.

    En minúscula para que una letra de documento no dependa de cómo se tipeó,
    por el mismo motivo que `fold` baja las mayúsculas.
    """
    return _FORMATO.sub("", value or "").lower()
