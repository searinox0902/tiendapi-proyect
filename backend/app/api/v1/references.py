import re
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_tenant_id
from app.api.filters import contains as _contains
from app.crud.base import CRUDBase
from app.models.reference import Reference
from app.schemas.common import Page
from app.schemas.reference import ReferenceCreate, ReferenceRead, ReferenceSummary, ReferenceUpdate

router = APIRouter(prefix="/references", tags=["references"])
crud = CRUDBase(Reference)

# Medida temporal de DESARROLLO (D-40/D-58): en producción el archivo vive en
# `appDataDir` del usuario (Tauri), nunca en el backend central. Esto solo
# existe para poder probar el flujo "nombre de archivo = SKU" sin el wrapper
# de escritorio, que todavía no está levantado en este repo.
STATIC_IMAGES_DIR = Path(__file__).resolve().parents[3] / "static" / "images"
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def _sanitize_sku(sku: str) -> str:
    """Ídem la sanitización que hará el cliente de escritorio (D-58): fuera cualquier carácter inválido en filesystem."""
    return re.sub(r"[^A-Za-z0-9_-]", "_", sku)


@router.get("/", response_model=Page[ReferenceRead])
def list_references(
    skip: int = Query(0, ge=0, description="Registros a saltar"),
    limit: int = Query(50, ge=1, le=200, description="Máximo de registros por página"),
    sku: str | None = Query(None, description="Coincidencia parcial, ignora mayúsculas"),
    title: str | None = Query(None, description="Coincidencia parcial, ignora mayúsculas"),
    search: str | None = Query(None, description="Coincidencia parcial en SKU **o** nombre"),
    category_id: uuid.UUID | None = Query(None, description="Categoría exacta"),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Listado paginado y filtrable de Referencias.

    Soporta la pantalla "CRUD Referencia" del MVP (docs/05-alcance-mvp-y-flujos.md,
    §2.1). Los filtros se combinan con AND y los de texto son parciales; `total`
    cuenta las filas que pasan el filtro, no las de la página devuelta.

    `search` existe aparte de `sku`/`title` porque une los dos con **OR**: en la
    caja registradora hay un solo campo de búsqueda y el cajero no sabe (ni
    debería) si lo que tiene en la mano es un código o un nombre — y con un
    escáner de barras es siempre un código. Combinar `sku` y `title` no sirve
    para eso: se cruzan con AND y exigirían que el término esté en los dos.
    """
    conditions = [Reference.tenant_id == tenant_id]
    if sku:
        conditions.append(Reference.sku.ilike(_contains(sku), escape="\\"))
    if title:
        conditions.append(Reference.title.ilike(_contains(title), escape="\\"))
    if search:
        pattern = _contains(search)
        conditions.append(
            or_(
                Reference.sku.ilike(pattern, escape="\\"),
                Reference.title.ilike(pattern, escape="\\"),
            )
        )
    if category_id is not None:
        conditions.append(Reference.category_id == category_id)

    total = db.execute(
        select(func.count()).select_from(Reference).where(*conditions)
    ).scalar_one()

    # El ORDER BY no es cosmético: sin un orden estable Postgres puede devolver
    # las filas en cualquier orden entre consultas, y una misma fila acabaría
    # repetida en dos páginas (o sin aparecer en ninguna). Se desempata por `id`
    # porque el SKU no es único a nivel de esquema.
    rows = (
        db.execute(
            select(Reference)
            .where(*conditions)
            .order_by(Reference.sku, Reference.id)
            .offset(skip)
            .limit(limit)
        )
        .scalars()
        .all()
    )

    return {"items": rows, "total": total, "skip": skip, "limit": limit}


@router.get("/lookup", response_model=Optional[ReferenceRead])
def lookup_reference(
    sku: str = Query(..., description="SKU exacto a buscar"),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Autocompletado de Referencia por SKU.

    Soporta la pantalla "Registrar Pago" del MVP (docs/05-alcance-mvp-y-flujos.md,
    §2): si la Referencia existe, el cliente la usa para autocompletar el
    formulario; si no existe, responde `null` (200) en vez de un 404, ya que
    "no encontrado" es un resultado válido y esperado del autocompletado.
    """
    stmt = select(Reference).where(Reference.tenant_id == tenant_id, Reference.sku == sku)
    return db.execute(stmt).scalar_one_or_none()


@router.get("/summary", response_model=ReferenceSummary)
def reference_summary(
    latest: int = Query(5, ge=1, le=20, description="Cuántas referencias recientes devolver"),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Agregados del catálogo para las cards de resumen de la pantalla Referencias.

    Va aparte del listado porque son datos que la paginación no puede dar: el
    listado devuelve una página ordenada por SKU, no el catálogo completo.

    `total_brands` cuenta marcas **distintas y no nulas** (`brand` es opcional,
    D-57). `last_updated_at` es el máximo `updated_at`, así que se mueve tanto al
    crear una referencia como al editarle la marca — no hace falta un timestamp
    aparte porque la marca es una columna de `Reference`, no una tabla propia.
    """
    scoped = Reference.tenant_id == tenant_id

    totals = db.execute(
        select(
            func.count(Reference.id),
            func.count(func.distinct(Reference.brand)),
            func.max(Reference.updated_at),
        ).where(scoped)
    ).one()

    recientes = (
        db.execute(
            select(Reference)
            .where(scoped)
            # Desempate por `id`: sin él, dos referencias creadas en el mismo
            # instante podrían alternar de orden entre llamadas.
            .order_by(Reference.created_at.desc(), Reference.id.desc())
            .limit(latest)
        )
        .scalars()
        .all()
    )

    return {
        "total_references": totals[0],
        "total_brands": totals[1],
        "last_updated_at": totals[2],
        "latest": recientes,
    }


@router.post("/", response_model=ReferenceRead, status_code=status.HTTP_201_CREATED)
def create_reference(
    payload: ReferenceCreate,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    return crud.create(db, tenant_id, payload.model_dump())


@router.post("/images/{sku}")
async def upload_reference_image(
    sku: str,
    file: UploadFile = File(...),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Guarda la imagen de una Referencia nombrada por SKU (D-58) — medida temporal
    de desarrollo mientras no exista el wrapper Tauri (D-40): el archivo se sirve
    desde el propio backend en vez de `appDataDir`, solo para poder probar el
    flujo end-to-end sin empaquetar la app de escritorio. Independiente de si la
    Referencia ya existe como fila en la BBDD — se identifica solo por SKU.
    """
    extension = Path(file.filename or "").suffix.lower() or ".jpg"
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato no soportado: {extension}",
        )

    tenant_dir = STATIC_IMAGES_DIR / str(tenant_id)
    tenant_dir.mkdir(parents=True, exist_ok=True)
    destination = tenant_dir / f"{_sanitize_sku(sku)}{extension}"
    destination.write_bytes(await file.read())

    return {"url": f"/static/images/{tenant_id}/{destination.name}"}


@router.get("/{reference_id}", response_model=ReferenceRead)
def get_reference(
    reference_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    obj = crud.get(db, tenant_id, reference_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference not found")
    return obj


@router.put("/{reference_id}", response_model=ReferenceRead)
def update_reference(
    reference_id: uuid.UUID,
    payload: ReferenceUpdate,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    obj = crud.update(db, tenant_id, reference_id, payload.model_dump())
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference not found")
    return obj


@router.delete("/{reference_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reference(
    reference_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    try:
        deleted = crud.delete(db, tenant_id, reference_id)
    except IntegrityError:
        # `Item.reference_id` es FK restrictiva (sin cascade): si hay Ítems
        # apuntando a esta Referencia, Postgres rechaza el DELETE.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar: la referencia tiene ítems de inventario asociados",
        )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference not found")
