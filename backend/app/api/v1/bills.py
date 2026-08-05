import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_tenant_id
from app.crud.base import CRUDBase
from app.models.bill import Bill
from app.models.bill_item import BillItem
from app.schemas.bill import BillCreate, BillRead

router = APIRouter(prefix="/bills", tags=["bills"])
crud = CRUDBase(Bill)


@router.get("/", response_model=list[BillRead])
def list_bills(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    return crud.get_multi(db, tenant_id, skip=skip, limit=limit)


@router.post("/", response_model=BillRead, status_code=status.HTTP_201_CREATED)
def create_bill(
    payload: BillCreate,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Crea una Factura con sus líneas en una única transacción.

    La firma HMAC y la cadena de hash (`prev_hash`) descritas en
    docs/04-seguridad.md NO se calculan en este esqueleto — quedan como
    responsabilidad de una capa de seguridad a implementar antes de producción.
    """
    bill = Bill(
        tenant_id=tenant_id,
        customer_id=payload.customer_id,
        bill_number=payload.bill_number,
        subtotal=payload.subtotal,
        total_iva=payload.total_iva,
        total=payload.total,
    )
    db.add(bill)
    db.flush()

    for item_payload in payload.items:
        db.add(
            BillItem(
                tenant_id=tenant_id,
                bill_id=bill.id,
                **item_payload.model_dump(),
            )
        )

    db.commit()
    db.refresh(bill)
    return bill


@router.get("/{bill_id}", response_model=BillRead)
def get_bill(
    bill_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    obj = crud.get(db, tenant_id, bill_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    return obj
