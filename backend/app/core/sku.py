"""Normalización del SKU — separadores unificados a guion (D-85).

Espacios, `_`, `*`, `,` y `.` se convierten en `-` al **escribir** una
Referencia: alta manual por la API y lote importado pasan los dos por acá. Es
una regla de escritura, no de lectura — leer una Referencia nunca altera su
SKU, o el valor que devuelve la API dejaría de servir para volver a buscarla.

Vive en `app/core/` y no dentro de un router por lo mismo que el precio de
venta (`pricing.py`) y la resolución de imagen (`images.py`): hay dos puertas de
escritura y una segunda implementación de la regla es el bug del día que cambie.

**Colapsa corridas y recorta los extremos** (fallo de la junta). Un SKU real del
catálogo del usuario es `50-29028-16 - 50-29001-46`: con sustitución 1:1 el
`" - "` daría `---`, porque el espacio de cada lado se convierte y el guion del
medio ya lo era. Colapsando queda `50-29028-16-50-29001-46`, y la operación es
**idempotente** — condición necesaria, porque el catálogo exportado se puede
reimportar (D-74) y el SKU tiene que sobrevivir la vuelta sin mutar.

⚠️ **Puede fusionar SKUs distintos**: `AB.1`, `AB_1` y `AB 1` terminan los tres
en `AB-1`. No se pierde nada silenciosamente — el SKU tiene unicidad *blanda* a
propósito (docs/03 §1.2), así que los duplicados se crean igual y la
previsualización de importación los reporta antes de confirmar (D-73).

Efecto lateral buscado: como el SKU normalizado ya solo contiene
`[A-Za-z0-9-]`, `images.sanitize_sku()` pasa a ser **lossless** para todo dato
nuevo — se cierra la trampa de colisión de nombres de archivo anotada en D-84.
"""
from __future__ import annotations

import hashlib
import re
import uuid

#  `+` para que " , " (varios separadores seguidos) cuente como uno solo. No
#  incluye `-`: ya es el destino, y meterlo acá no cambiaría el resultado
#  porque el colapso de abajo se encarga de las corridas.
#
#  **`#` está en la lista a propósito** (D-90): es la marca reservada de
#  variante, y convertirla a `-` en la entrada es lo que la vuelve
#  **infalsificable** — solo el sistema puede producir un `#`, vía
#  `variant_sku()`. Sin esto, un proveedor con `#` en su código heredaría
#  variantes fantasma que nadie creó.
_SEPARATORS = re.compile(r"[\s_*,.#]+")
_DASH_RUNS = re.compile(r"-{2,}")
#  La marca de variante bien formada: `#` + dígitos, al final del código. Es la
#  única forma en que un `#` sobrevive a la normalización.
_VARIANT_SUFFIX = re.compile(r"^(.*)#(\d+)$")


def _normalize_core(sku: str) -> str:
    return _DASH_RUNS.sub("-", _SEPARATORS.sub("-", sku.strip())).strip("-")


def normalize_sku(sku: str) -> str:
    """
    `"50-29028-16 - 50-29001-46"` → `"50-29028-16-50-29001-46"`.

    **Preserva la marca de variante bien formada** (`#` seguido de dígitos, al
    final): `"ABC#2"` → `"ABC#2"`, pero `"A#B"` → `"A-B"`. Sin esa excepción el
    sistema destruía su propio código: el validador de escritura normaliza
    todo lo que entra, así que la variante `ABC#2` que el propio backend
    acababa de ofrecer se guardaba como `ABC-2` — un código distinto, fuera del
    grupo, y encima ambiguo con los 75 SKU reales que ya terminan en `-<n>`.

    El `#` suelto se sigue convirtiendo a `-`, así que un código de proveedor
    con `#` no puede fabricar una variante fantasma salvo que traiga
    exactamente la forma `#<número>` al final — que no aparece en ninguno de
    los 1027 SKU del catálogo real.

    Puede devolver string vacío (ej. un SKU que era puro separadores). **No
    lanza**: quién lo llama decide qué hacer con el vacío — el alta por API lo
    rechaza como error de validación, y la importación lo marca como fila
    inválida sin tumbar el resto del lote.
    """
    match = _VARIANT_SUFFIX.match(sku.strip())
    if match:
        base = _normalize_core(match.group(1))
        #  Un sufijo sin base (`"#2"`) no identifica ninguna pieza — no hay de
        #  qué ser variante. Cae al camino común, donde el `#` es separador y
        #  queda `"2"`: un código raro pero válido, no una variante huérfana.
        if base:
            return f"{base}{VARIANT_SEPARATOR}{int(match.group(2))}"
    return _normalize_core(sku)


#  Prefijo visible a propósito: el dueño tiene que poder filtrar por `GEN-` y
#  ver de una cuáles códigos los puso el sistema y cuáles vienen del proveedor.
#  Son placeholders para revisar, no códigos de catálogo definitivos.
GENERATED_SKU_PREFIX = "GEN-"
_GENERATED_LENGTH = 8


def generate_sku(title: str | None, brand: str | None = None) -> str:
    """
    SKU para una fila que no trae ninguno (D-86) — `GEN-` + 8 hex, ej. `GEN-A3F2C1D9`.

    **Determinista sobre título+marca**, no aleatorio: la misma fila del mismo
    archivo produce siempre el mismo código, así que reimportar no duplica —
    la Referencia se detecta como ya existente y la previsualización lo
    reporta (D-73). Con un código nuevo por corrida, cada reimportación
    ensuciaría el catálogo con copias que después hay que borrar a mano.

    **Aleatorio solo cuando no hay de dónde derivar** (fila sin título ni
    marca): ahí un hash constante le daría el mismo código a todas esas filas
    y las colapsaría en un solo producto, que es peor que perder idempotencia
    en el puñado de filas que no traen ni nombre.

    Dos productos distintos con idéntico título+marca reciben el mismo código
    a propósito: es la señal correcta —probablemente son la misma fila
    repetida en el scrapeo—, y la unicidad blanda (docs/03 §1.2) deja que
    convivan igual si el usuario decide traer los duplicados.
    """
    seed = f"{(brand or '').strip().lower()}|{(title or '').strip().lower()}"
    if seed == "|":
        digest = uuid.uuid4().hex
    else:
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return f"{GENERATED_SKU_PREFIX}{digest[:_GENERATED_LENGTH].upper()}"


#  ── Variantes (D-90) ──────────────────────────────────────────────────────
#
#  Una variante es una Referencia **propia y completa**, con SKU único a nivel
#  de datos; lo único compartido es la **base** del código, y de ahí sale la
#  presentación agrupada ("tiene 2 variantes"). No hay relación padre/hijo, ni
#  columna, ni FK: el vínculo es la convención de nombre, así que agrupar es
#  una consulta por prefijo y borrar una no deja huérfana a ninguna otra.
#
#  **Por qué `#` y no un sufijo `-2`:** medido sobre el catálogo real de 1027
#  SKUs, **75 ya terminan en `-<número>`** (`KN-303`, `KN-151`…), así que el
#  guion es ambiguo — `KN-303` se leería como "variante 303 de KN". El `#` no
#  aparece en ninguno de los 1027, y se reconoce a simple vista como una marca
#  puesta por el sistema y no por el proveedor.
VARIANT_SEPARATOR = "#"
#  La pieza base es la variante 1 implícita y conserva su código limpio; las
#  que se agregan después empiezan en 2, que es como se enuncian de cara al
#  usuario ("Variante 2 de 3").
FIRST_VARIANT_NUMBER = 2


def variant_sku(base: str, number: int) -> str:
    """`("41080-0578-11H", 2)` → `"41080-0578-11H#2"`."""
    return f"{base}{VARIANT_SEPARATOR}{number}"


def base_of(sku: str) -> str:
    """
    SKU → código de la pieza, sin la marca de variante.

    `"41080-0578-11H#2"` → `"41080-0578-11H"`; un SKU sin marca se devuelve
    igual, así que sirve para agrupar cualquier fila sin preguntar antes si es
    variante o no.
    """
    return sku.split(VARIANT_SEPARATOR, 1)[0]


def variant_number(sku: str) -> int:
    """
    Número de variante que declara el SKU. La pieza base es la 1.

    Tolera un sufijo no numérico (`"ABC#x"`) devolviendo 1 en vez de lanzar:
    esto se usa para ordenar y presentar, y un dato viejo o raro no debería
    tumbar el listado de Referencias.
    """
    _, _, suffix = sku.partition(VARIANT_SEPARATOR)
    return int(suffix) if suffix.isdigit() else 1


def is_variant(sku: str) -> bool:
    return VARIANT_SEPARATOR in sku
