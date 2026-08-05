import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict


class LocationType(str, Enum):
    SUCURSAL = "sucursal"
    BODEGA = "bodega"


class LocationBase(BaseModel):
    name: str
    address: Optional[str] = None
    type: LocationType


class LocationCreate(LocationBase):
    pass


class LocationRead(LocationBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    version: int
