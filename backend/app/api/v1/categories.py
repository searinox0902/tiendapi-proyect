import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_tenant_id
from app.crud.base import CRUDBase
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryRead

router = APIRouter(prefix="/categories", tags=["categories"])
crud = CRUDBase(Category)


@router.get("/", response_model=list[CategoryRead])
def list_categories(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    return crud.get_multi(db, tenant_id, skip=skip, limit=limit)


@router.post("/", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    response: Response,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Alta de una Categoría.

    **Si ya existe uno cuyo nombre coincide plegado —sin mayúsculas, sin tildes,
    sin espacios de sobra (D-93)— se devuelve ése en vez de crear otro**, y la
    respuesta baja de `201 Created` a `200 OK`: no se creó nada, y un cliente
    que mire el código puede notarlo. Decisión del dueño de producto para que
    el alta manual deje de sembrar la redundancia que los importadores ya
    evitan — escribir `HONDA` cuando existe `Honda` no crea una segunda.

    La grafía guardada **no se toca**: manda la que se registró primero.
    """
    existente = crud.find_by_name(db, tenant_id, Category.name, payload.name)
    if existente is not None:
        response.status_code = status.HTTP_200_OK
        return existente
    return crud.create(db, tenant_id, payload.model_dump())


@router.get("/{category_id}", response_model=CategoryRead)
def get_category(
    category_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    obj = crud.get(db, tenant_id, category_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return obj
