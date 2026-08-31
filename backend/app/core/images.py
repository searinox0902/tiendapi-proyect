"""Resolución de la imagen de una Referencia: local primero, externa después (D-84).

Una Referencia puede tener imagen **local**, **externa**, **las dos o ninguna**,
y la local siempre gana. La regla vive acá y no en cada endpoint porque hay
siete puntos que emiten `image_url` (Referencias, Productos ×2, Facturas,
Dashboard ×2) y ocho componentes del frontend que la pintan: una segunda
implementación de la precedencia es el bug del día que la regla cambie — mismo
criterio por el que el precio de venta vive en `app/core/pricing.py` y no en
los routers.

**`Reference.image_url` guarda SOLO la URL externa.** Que exista una imagen
local es un hecho **derivado del disco**, no una columna: el archivo se llama
como el SKU (D-58), y con eso alcanza para encontrarlo. Esa asimetría es lo que
hace que el catálogo pueda arrancar con puras URLs externas y, más adelante,
bajarlas a disco **sin tocar la BBDD ni la UI** — aparecen los archivos y la
local empieza a ganar sola.

**La URL local se arma con el host del request entrante, nunca con uno
guardado.** Antes de D-84 el cliente concatenaba `VITE_API_URL` y persistía
`http://localhost:8000/...` en la columna: eso rompía en cualquier máquina de
la LAN que no fuera la que subió el archivo (D-32/D-33), porque `localhost`
resolvía contra sí misma. Derivarla del request la deja correcta por
construcción en cada contexto.
"""
from __future__ import annotations

import os
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Optional

#  Medida temporal de DESARROLLO (D-40/D-58): en producción los archivos viven
#  en `appDataDir` del usuario (Tauri), no servidos por el backend central.
#  Cuando eso llegue se cambia esta constante y `_local_filename()`; los siete
#  puntos que llaman a `resolve_image_url()` no se enteran.
STATIC_IMAGES_DIR = Path(__file__).resolve().parents[2] / "static" / "images"

#  Orden = precedencia: si conviven `ABC.jpg` y `ABC.png`, gana el primero de
#  esta lista. Sin un orden fijo, cuál se muestra dependería de cómo el sistema
#  de archivos devuelva las entradas del directorio, que no es determinista.
ALLOWED_IMAGE_EXTENSIONS: tuple[str, ...] = (".jpg", ".jpeg", ".png", ".webp")
_EXTENSION_RANK = {extension: rank for rank, extension in enumerate(ALLOWED_IMAGE_EXTENSIONS)}

#  Un `scandir` por tenant en vez de un `stat` por fila: una grilla de 200
#  productos haría 200 accesos a disco para responder la misma pregunta. El TTL
#  es corto porque el caso que importa —el usuario arrastra un archivo a la
#  carpeta y refresca— tiene que reflejarse enseguida; la subida por la API
#  además invalida el índice de una (`invalidate_tenant_index`).
_INDEX_TTL_SECONDS = 5.0
_index_cache: dict[str, tuple[float, dict[str, tuple[str, int]]]] = {}
_index_lock = threading.Lock()


def sanitize_sku(sku: str) -> str:
    """
    SKU → nombre de archivo (D-58). Ídem la sanitización que hará el cliente de
    escritorio: fuera cualquier carácter inválido en filesystem.

    ⚠️ Es **lossy y no reversible**: `AB/12`, `AB 12` y `AB.12` colapsan todos a
    `AB_12`. Sumado a que el SKU tiene unicidad **blanda** a propósito (docs/03
    §1.2), dos Referencias distintas pueden terminar apuntando al mismo archivo.
    Con SKUs alfanuméricos (los scrapeados, los generados) no pasa; con SKUs
    tipeados a mano con separadores, puede. Anotado y aceptado — el precio de
    arreglarlo es un mapa explícito archivo↔referencia, que es justo la
    estructura paralela que la convención evita.
    """
    return re.sub(r"[^A-Za-z0-9_-]", "_", sku)


def _build_index(tenant_id: str) -> dict[str, tuple[str, int]]:
    """`{stem: (nombre_archivo, mtime)}` de la carpeta del tenant, o vacío si no existe."""
    best: dict[str, tuple[int, str, int]] = {}
    try:
        entries = os.scandir(STATIC_IMAGES_DIR / tenant_id)
    except (FileNotFoundError, NotADirectoryError):
        return {}
    with entries:
        for entry in entries:
            try:
                if not entry.is_file():
                    continue
                stem, extension = os.path.splitext(entry.name)
                rank = _EXTENSION_RANK.get(extension.lower())
                if rank is None:
                    continue
                current = best.get(stem)
                if current is None or rank < current[0]:
                    best[stem] = (rank, entry.name, int(entry.stat().st_mtime))
            except OSError:
                #  Archivo borrado entre el listado y el stat: no es un error
                #  del que haya que enterarse, simplemente no hay imagen local.
                continue
    return {stem: (name, mtime) for stem, (_, name, mtime) in best.items()}


def _tenant_index(tenant_id: str) -> dict[str, tuple[str, int]]:
    now = time.monotonic()
    with _index_lock:
        cached = _index_cache.get(tenant_id)
        if cached is not None and cached[0] > now:
            return cached[1]
    #  El escaneo va FUERA del lock: es I/O, y bloquear a todos los hilos
    #  mientras uno lee el directorio convierte el caché en un cuello de
    #  botella. Dos hilos pueden escanear a la vez la primera; es idempotente.
    index = _build_index(tenant_id)
    with _index_lock:
        _index_cache[tenant_id] = (now + _INDEX_TTL_SECONDS, index)
    return index


def invalidate_tenant_index(tenant_id: uuid.UUID | str) -> None:
    """Fuerza el relevamiento del disco en la próxima consulta (tras subir/borrar un archivo)."""
    with _index_lock:
        _index_cache.pop(str(tenant_id), None)


def local_image_url(sku: str, tenant_id: uuid.UUID | str, base_url: str) -> Optional[str]:
    """
    URL de la imagen local si el archivo existe, `None` si no.

    Lleva `?v={mtime}` porque el nombre del archivo es fijo (el SKU): sin eso,
    reemplazar la imagen deja al navegador mostrando la vieja desde su caché —
    y "arrastro una nueva encima" es justamente el flujo que esta convención
    habilita.
    """
    entry = _tenant_index(str(tenant_id)).get(sanitize_sku(sku))
    if entry is None:
        return None
    filename, mtime = entry
    return f"{base_url.rstrip('/')}/static/images/{tenant_id}/{filename}?v={mtime}"


def resolve_image_url(
    sku: str,
    stored_url: Optional[str],
    tenant_id: uuid.UUID | str,
    base_url: str,
) -> Optional[str]:
    """
    Local → externa → `None` (la UI ya pinta su propio placeholder con `None`).

    `stored_url` es la columna `Reference.image_url`, que **solo** contiene URLs
    externas (D-84). Un string vacío cuenta como ausencia, no como URL.
    """
    return local_image_url(sku, tenant_id, base_url) or (stored_url or None)
