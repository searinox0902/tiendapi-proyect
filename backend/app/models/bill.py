from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SyncMixin, TenantScopedMixin, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.models.bill_item import BillItem


class Bill(Base, UUIDPKMixin, TenantScopedMixin, TimestampMixin, SyncMixin):
    """Factura — docs/03-modelo-datos.md §1.5. Integridad: ver docs/04-seguridad.md."""

    __tablename__ = "bills"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False, index=True
    )
    bill_number: Mapped[str] = mapped_column(String, nullable=False, index=True)

    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_iva: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Integridad (docs/04-seguridad.md) — la firma/cadena real no se calcula en este esqueleto.
    hmac: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    prev_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    items: Mapped[list["BillItem"]] = relationship(
        "BillItem", back_populates="bill", cascade="all, delete-orphan"
    )
