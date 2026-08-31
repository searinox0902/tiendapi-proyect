import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_tenant_id
from app.api.filters import contains as _contains
from app.core.nit import normalize_nit
from app.crud.base import CRUDBase
from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerRead

router = APIRouter(prefix="/customers", tags=["customers"])
crud = CRUDBase(Customer)


@router.get("/", response_model=list[CustomerRead])
def list_customers(
    skip: int = 0,
    limit: int = Query(100, ge=1, le=200),
    search: str | None = Query(None, description="Coincidencia parcial en cédula/NIT **o** nombre"),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Listado de Clientes, con búsqueda para el autocompletado del cobro.

    `search` cruza cédula/NIT y nombre con **OR**, misma razón que en
    Referencias: el cajero teclea lo que el cliente le dicta —a veces el
    documento, a veces el nombre— y no debería tener que decidir en qué campo
    va. Con AND habría que acertar en los dos a la vez.
    """
    if not search:
        return crud.get_multi(db, tenant_id, skip=skip, limit=limit)

    pattern = _contains(search)
    return list(
        db.execute(
            select(Customer)
            .where(
                Customer.tenant_id == tenant_id,
                or_(
                    Customer.nit.ilike(pattern, escape="\\"),
                    Customer.fullname.ilike(pattern, escape="\\"),
                ),
            )
            .order_by(Customer.fullname)
            .offset(skip)
            .limit(limit)
        ).scalars()
    )


@router.get("/lookup", response_model=CustomerRead | None)
def lookup_customer(
    nit: str | None = Query(None, description="Cédula/NIT exacto"),
    fullname: str | None = Query(None, description="Nombre exacto, ignora mayúsculas"),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Coincidencia **exacta** por documento o nombre; `null` si no existe.

    Es lo que decide si el cobro ofrece registrar al cliente: la búsqueda
    parcial de `/` sirve para sugerir mientras se escribe, pero "Andrés" no es
    el mismo cliente que "Andrés Gómez", y ofrecer registrar basándose en una
    coincidencia parcial crearía duplicados del mismo cliente.
    """
    conditions = [Customer.tenant_id == tenant_id]
    if nit:
        conditions.append(Customer.nit == nit)
    elif fullname:
        conditions.append(func.lower(Customer.fullname) == fullname.strip().lower())
    else:
        return None

    return db.execute(select(Customer).where(*conditions).limit(1)).scalar_one_or_none()


@router.post("/", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: CustomerCreate,
    response: Response,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Alta de un Cliente.

    **La identidad es el NIT/cédula, no el nombre** — al revés que en el resto
    del Directorio (D-94). Dos personas distintas se llaman igual con toda
    naturalidad, así que fusionar por nombre borraría un cliente real; en
    cambio el mismo documento cargado dos veces es siempre el mismo cliente.

    Con NIT que ya existe se devuelve ése (`200 OK` en vez de `201`), y la
    comparación descarta el **formato**: `900.456.123-4` encuentra a
    `900456123-4`. **Sin NIT no se deduplica nunca** y se crea siempre: sin
    documento no hay nada que permita afirmar que son la misma persona.
    """
    existente = crud.find_by_name(
        db, tenant_id, Customer.nit, payload.nit, normalizer=normalize_nit
    )
    if existente is not None:
        response.status_code = status.HTTP_200_OK
        return existente
    return crud.create(db, tenant_id, payload.model_dump())


@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer(
    customer_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    obj = crud.get(db, tenant_id, customer_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return obj
