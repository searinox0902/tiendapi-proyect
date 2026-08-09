import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ReferenceBase(BaseModel):
    provider_id: uuid.UUID
    category_id: Optional[uuid.UUID] = None
    sku: str
    title: str
    brand: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    base_price: Decimal
    iva_percentage: Decimal = Decimal("0")
    # Costo de adquisición (lado compra), independiente de base_price/sale_price
    # (lado venta) — ver D-47. Opcional: el catálogo existente no lo tiene todavía.
    precio_proveedor: Optional[Decimal] = None


class ReferenceCreate(ReferenceBase):
    pass


class ReferenceUpdate(ReferenceBase):
    pass


class ReferenceRead(ReferenceBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    version: int


class ReferenceLatest(BaseModel):
    """Fila mínima de "últimas referencias creadas" — solo lo que pinta la card."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sku: str
    title: str
    base_price: Decimal


class ReferenceSummary(BaseModel):
    """
    Agregados del catálogo para las cards de resumen.

    Se calculan en SQL y no en el cliente: el listado viene paginado y ordenado
    por SKU, así que desde el frontend no hay forma de saber el total de marcas
    ni cuáles son las últimas creadas sin traerse el catálogo entero.
    """

    total_references: int
    total_brands: int
    #  `None` cuando el catálogo está vacío.
    last_updated_at: Optional[datetime] = None
    latest: list[ReferenceLatest]
