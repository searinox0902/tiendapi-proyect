r"""Comparación de nombres — forma plegada, la regla de "¿son el mismo nombre?".

**Protocolo único del proyecto para comparar nombres de texto libre**: nombre
de pieza, Proveedor, Categoría, Ubicación, Marca y Cliente. Todos pasan por
`fold()` — nunca por `.lower()` suelto, que solo cubre un tercio del problema.

Tres transformaciones, cada una por un caso real:

1. **Mayúsculas** — `Honda` / `HONDA`. Un scraper grita, una persona no.
2. **Tildes** — `Pírelli` / `Pirelli`, `Ára` / `ara`. Un teclado sin tildes, un
   origen que las perdió en la codificación, o simplemente quien las omite al
   tipear: ninguno de los tres está creando un proveedor nuevo.
3. **Espacios** — `"Pirelli "` / `"Pirelli"`, y espacios internos repetidos.
   Incluye el **espacio duro** (U+00A0), que es lo que emite un scraper y que
   `\s` de Python sí matchea (mismo bicho que documenta `money.py`, D-88).

**Lo que `fold()` NO hace, a propósito: no adivina.** `Pirelli` y `Pirreli` —
una letra distinta, una letra de más— se quedan como nombres **distintos**. No
hay distancia de edición ni comparación difusa: con una letra cambiada es
imposible saber si es un error de tipeo o dos cosas realmente distintas, y
fusionar de más borra un dato sin que nadie se entere, que es el sesgo que D-89
ya había fijado para el catálogo. El límite está donde termina la certeza.

⚠️ **La `ñ` se pliega a `n`** (`Señal` → `senal`), efecto de descomponer en NFKD
y descartar los diacríticos. En castellano son letras distintas —`año` no es
`ano`— así que la regla puede fusionar dos nombres que no lo son. Se acepta a
sabiendas: en el dominio real (marcas y proveedores de repuestos) el caso que
aparece es alguien escribiendo `Penalosa` por `Peñalosa`, y ahí fusionar es lo
correcto; el caso contrario es teórico. Si algún día muerde, la salida es
preservar `ñ` antes de descomponer, no abandonar el plegado.

Vive en `app/core/` y no dentro del importador por lo mismo que `pricing.py`,
`money.py` y `sku.py`: es una regla del negocio y necesita un solo lugar donde
mirarla. `exports/generic.py:normalize_header` aplica la misma transformación a
los **encabezados de columna** (D-87), y se deja aparte a propósito: son dos
contratos independientes que pueden evolucionar distinto — un encabezado nunca
lleva puntuación y un nombre de pieza sí.
"""
from __future__ import annotations

import re
import unicodedata

_SPACES = re.compile(r"\s+")


def fold(text: str | None) -> str:
    """
    `"  Válvulas   ADMISIÓN "` → `"valvulas admision"`.

    Sin tildes, sin mayúsculas, espacios colapsados. `None` y vacío dan `""`,
    que el llamador trata como "la fila no dice nombre" — distinto de "dice un
    nombre que no coincide".
    """
    decomposed = unicodedata.normalize("NFKD", text or "")
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return _SPACES.sub(" ", without_accents).strip().lower()
