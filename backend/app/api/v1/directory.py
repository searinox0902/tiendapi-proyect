import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_tenant_id
from app.models.brand import Brand
from app.models.category import Category
from app.models.customer import Customer
from app.models.location import Location
from app.models.provider import Provider
from app.schemas.directory import DirectorySummary

router = APIRouter(prefix="/directory", tags=["directory"])

#  (modelo, columna de conteo/orden) — mismo modelo para las cinco entidades
#  "de soporte" del Directorio: cada una es chica (decenas/cientos de filas en
#  un negocio real), así que cinco COUNT + cinco SELECT...LIMIT por separado es
#  perfectamente barato y mucho más legible que forzarlas a una sola consulta.
_ENTITIES = (
    ("providers", Provider),
    ("locations", Location),
    ("categories", Category),
    ("customers", Customer),
    ("brands", Brand),
)


@router.get("/summary", response_model=DirectorySummary)
def directory_summary(
    latest: int = Query(5, ge=1, le=20, description="Cuántos registros recientes devolver por entidad"),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Agregados para la pantalla Directorio: conteo + últimos creados de cada
    entidad de soporte (Proveedores, Ubicaciones, Categorías, Clientes,
    Marcas). Un solo viaje al backend en vez de cinco listados + cinco
    conteos por separado desde el cliente.
    """
    result: dict = {}
    for key, model in _ENTITIES:
        scoped = model.tenant_id == tenant_id
        total = db.execute(select(func.count()).select_from(model).where(scoped)).scalar_one()
        rows = (
            db.execute(
                select(model)
                .where(scoped)
                .order_by(model.created_at.desc(), model.id.desc())
                .limit(latest)
            )
            .scalars()
            .all()
        )
        result[f"total_{key}"] = total
        result[f"latest_{key}"] = rows

    return result
