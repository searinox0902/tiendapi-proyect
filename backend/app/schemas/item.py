import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ItemBase(BaseModel):
    reference_id: uuid.UUID
    provider_id: uuid.UUID
    location_id: uuid.UUID
    quantity: Decimal = Decimal("0")
    current_price: Decimal


class ItemCreate(ItemBase):
    pass


class ItemRead(ItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    version: int
