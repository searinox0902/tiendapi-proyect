import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class BrandBase(BaseModel):
    name: str
    description: Optional[str] = None


class BrandCreate(BrandBase):
    pass


class BrandRead(BrandBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    version: int
