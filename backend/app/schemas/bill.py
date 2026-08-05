import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class BillItemCreate(BaseModel):
    item_id: uuid.UUID
    quantity: Decimal
    unit_price: Decimal
    iva_percentage: Decimal
    iva_amount: Decimal
    total: Decimal


class BillItemRead(BillItemCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    bill_id: uuid.UUID
    hmac: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    version: int


class BillCreate(BaseModel):
    customer_id: uuid.UUID
    bill_number: str
    subtotal: Decimal
    total_iva: Decimal
    total: Decimal
    items: list[BillItemCreate]


class BillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    customer_id: uuid.UUID
    bill_number: str
    subtotal: Decimal
    total_iva: Decimal
    total: Decimal
    hmac: Optional[str] = None
    prev_hash: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    version: int
    items: list[BillItemRead] = []
