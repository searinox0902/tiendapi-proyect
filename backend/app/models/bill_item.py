from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SyncMixin, TenantScopedMixin, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.models.bill import Bill


class BillItem(Base, UUIDPKMixin, TenantScopedMixin, TimestampMixin, SyncMixin):
    """Línea de factura — docs/03-modelo-datos.md §1.6."""

    __tablename__ = "bill_items"

    bill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bills.id"), nullable=False, index=True
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id"), nullable=False, index=True
    )

    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    # antes `iva` en docs/03 (ambiguo % vs. monto — ver D-19)
    iva_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    iva_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    hmac: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    bill: Mapped["Bill"] = relationship("Bill", back_populates="items")
