import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_tenant_id
from app.crud.base import CRUDBase
from app.models.reference import Reference
from app.schemas.common import Page
from app.schemas.reference import ReferenceCreate, ReferenceRead, ReferenceSummary

router = APIRouter(prefix="/references", tags=["references"])
crud = CRUDBase(Reference)


def _contains(value: str) -> str:
    """
    Construye el patrón LIKE de "contiene", escapando los comodines del texto.

    Sin escapar, buscar `50%` o `PZ_1` haría que `%` y `_` actúen como comodines
    de SQL y devolvieran filas que el usuario no pidió.
    """
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


@router.get("/", response_model=Page[ReferenceRead])
def list_references(
    skip: int = Query(0, ge=0, description="Registros a saltar"),
    limit: int = Query(50, ge=1, le=200, description="Máximo de registros por página"),
    sku: str | None = Query(None, description="Coincidencia parcial, ignora mayúsculas"),
    title: str | None = Query(None, description="Coincidencia parcial, ignora mayúsculas"),
    category_id: uuid.UUID | None = Query(None, description="Categoría exacta"),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Listado paginado y filtrable de Referencias.

    Soporta la pantalla "CRUD Referencia" del MVP (docs/05-alcance-mvp-y-flujos.md,
    §2.1). Los filtros se combinan con AND y los de texto son parciales; `total`
    cuenta las filas que pasan el filtro, no las de la página devuelta.
    """
    conditions = [Reference.tenant_id == tenant_id]
    if sku:
        conditions.append(Reference.sku.ilike(_contains(sku), escape="\\"))
    if title:
        conditions.append(Reference.title.ilike(_contains(title), escape="\\"))
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
