from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, String
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

    #  Estado fiscal DIAN (D-48). `NULL` = sin trámite fiscal todavía, que es
    #  distinto de 'pendiente' (ya en cola). Sin integración DIAN viva
    #  (diferida, D-09/D-38) lo normal es que esté nulo.
    fiscal_status: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)

    #  Anulación (D-60). Es una marca, **no** un borrado: la factura anulada
    #  sigue existiendo, con su consecutivo y sus líneas, porque un documento
    #  numerado que desaparece deja un hueco en la serie que no se puede
    #  explicar. `NULL` = vigente; con fecha = anulada, y desde ese momento no
    #  suma a ninguna cifra de dinero (ver `bills_summary`).
    voided_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    #  Obligatorio al anular (lo exige el endpoint, no la base): sin motivo, un
    #  mes después nadie puede decir si fue un error de digitación o una
    #  devolución — y son cosas distintas para el inventario y para la DIAN.
    void_reason: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Integridad (docs/04-seguridad.md) — la firma/cadena real no se calcula en este esqueleto.
    hmac: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    prev_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    items: Mapped[list["BillItem"]] = relationship(
        "BillItem", back_populates="bill", cascade="all, delete-orphan"
    )
