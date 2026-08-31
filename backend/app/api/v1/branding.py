"""Imagen del negocio — la que se ve en la pantalla de inicio de sesión.

**Vive en `static/branding/` y no en `static/images/`, y no es un detalle
organizativo.** `app/core/images.py` indexa `static/images/<tenant>/` tratando
**el nombre de cada archivo como un SKU** (D-58): dejar acá un `login.jpg`
haría que una Referencia con SKU `LOGIN` heredara la foto del local, y que el
índice de imágenes de producto cargara un archivo que no le corresponde.
Carpeta aparte, problema que no existe.

**Sin columna en `Tenant`, igual que las imágenes de producto (D-84):** que
exista la imagen es un hecho **derivado del disco**, no un dato que haya que
mantener sincronizado con él. El archivo se llama por el tenant, así que
encontrarlo no necesita una fila; y una columna que dice "sí hay imagen"
cuando alguien borró el archivo a mano es exactamente la clase de mentira que
D-84 vino a sacar del modelo.

**La pantalla de login se pinta ANTES de autenticarse**, así que no hay `tenant_id`
en un token para resolver la imagen. Se apoya en dos hechos: `/static` se sirve
sin autenticación, y el cliente guarda la **ruta relativa** en `localStorage` al
entrar (o al subirla). Se guarda relativa y nunca absoluta por lo mismo que
documenta D-84: un host quemado (`http://localhost:8000/...`) rompe en cualquier
otra máquina de la LAN (D-32). El host lo pone el cliente al pintar, con el que
esté usando en ese momento.
"""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps import get_tenant_id
from app.core.images import ALLOWED_IMAGE_EXTENSIONS, STATIC_IMAGES_DIR

router = APIRouter(prefix="/branding", tags=["branding"])

#  Hermana de `STATIC_IMAGES_DIR`, no dentro de ella (ver docstring del módulo).
BRANDING_DIR = STATIC_IMAGES_DIR.parent / "branding"

#  Nombre fijo: hay una sola imagen de negocio por tenant, así que no hace falta
#  ningún identificador dentro del archivo. La extensión varía y por eso se
#  busca por prefijo al leer y se limpian las otras al escribir.
LOGIN_IMAGE_STEM = "login"

#  Tope explícito, a diferencia del alta de imagen de producto, que hoy no tiene
#  ninguno. Acá importa más: el pedido es justamente que **pueda ser una imagen
#  grande**, y el archivo se lee entero en memoria (`await file.read()`). 8 MB
#  deja pasar cómodamente una foto de celular ya redimensionada por el cliente y
#  corta el caso de arrastrar un RAW de 40 MB sin querer.
MAX_UPLOAD_BYTES = 8 * 1024 * 1024


def _tenant_dir(tenant_id: uuid.UUID) -> Path:
    return BRANDING_DIR / str(tenant_id)


def _find_existing(tenant_id: uuid.UUID) -> Path | None:
    """
    Archivo de imagen del negocio, sea cual sea su extensión.

    Recorre `ALLOWED_IMAGE_EXTENSIONS` en orden y no el directorio: el orden de
    la lista **es** la precedencia (mismo criterio que `core/images.py`), y
    depender de cómo el sistema de archivos devuelva las entradas sería
    quedarse sin un ganador determinista si conviven dos formatos.
    """
    directory = _tenant_dir(tenant_id)
    for extension in ALLOWED_IMAGE_EXTENSIONS:
        candidate = directory / f"{LOGIN_IMAGE_STEM}{extension}"
        if candidate.is_file():
            return candidate
    return None


def _relative_url(tenant_id: uuid.UUID, path: Path) -> str:
    return f"/static/branding/{tenant_id}/{path.name}"


@router.get("")
def get_branding(tenant_id: uuid.UUID = Depends(get_tenant_id)):
    """
    Qué imagen tiene cargada el negocio, o `null`.

    Devuelve la ruta **relativa**: el cliente le antepone el host que esté
    usando. Ver el docstring del módulo para por qué nunca una absoluta.
    """
    existing = _find_existing(tenant_id)
    return {"login_image_url": _relative_url(tenant_id, existing) if existing else None}


@router.post("/login-image", status_code=status.HTTP_201_CREATED)
async def upload_login_image(
    file: UploadFile = File(..., description="Imagen del negocio: .jpg, .png o .webp"),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Sube (o reemplaza) la imagen del negocio.

    El cliente ya la redimensiona antes de mandarla, pero el tope se valida
    igual acá: el navegador es una comodidad, no una garantía — cualquiera
    puede llamar al endpoint directo.

    **Se borran las demás extensiones al escribir.** Sin eso, subir un `.png`
    sobre un `.jpg` existente dejaría los dos archivos y ganaría el `.jpg` por
    el orden de `ALLOWED_IMAGE_EXTENSIONS` — o sea, la imagen vieja: el usuario
    sube una foto nueva y no cambia nada, sin ningún error que lo explique.
    """
    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Formato no soportado: {extension or 'sin extensión'}. "
                f"Se aceptan: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
            ),
        )

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"La imagen pesa {len(content) // (1024 * 1024)} MB y el máximo es "
                f"{MAX_UPLOAD_BYTES // (1024 * 1024)} MB"
            ),
        )
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="El archivo está vacío")

    directory = _tenant_dir(tenant_id)
    directory.mkdir(parents=True, exist_ok=True)
    for otra in ALLOWED_IMAGE_EXTENSIONS:
        if otra != extension:
            (directory / f"{LOGIN_IMAGE_STEM}{otra}").unlink(missing_ok=True)

    destination = directory / f"{LOGIN_IMAGE_STEM}{extension}"
    destination.write_bytes(content)
    return {"login_image_url": _relative_url(tenant_id, destination)}


@router.delete("/login-image", status_code=status.HTTP_204_NO_CONTENT)
def delete_login_image(tenant_id: uuid.UUID = Depends(get_tenant_id)):
    """
    Quita la imagen y el login vuelve a su fondo por defecto.

    Borra **todas** las extensiones y no solo la que gana: si quedara una
    variante vieja detrás, "quitar" dejaría una imagen distinta en pantalla en
    vez de ninguna, que es peor que no haber hecho nada.
    """
    directory = _tenant_dir(tenant_id)
    for extension in ALLOWED_IMAGE_EXTENSIONS:
        (directory / f"{LOGIN_IMAGE_STEM}{extension}").unlink(missing_ok=True)
    return None
