import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SyncMixin, TenantScopedMixin, TimestampMixin, UUIDPKMixin


class Reference(Base, UUIDPKMixin, TenantScopedMixin, TimestampMixin, SyncMixin):
    """
    Referencia (catálogo de producto) — docs/03-modelo-datos.md §1.2.

    Tabla física `product_references` (no `references`): ese nombre es palabra
    reservada en SQL (usada en la sintaxis de FOREIGN KEY ... REFERENCES) y
    obligaría a citarla entre comillas en cualquier SQL manual futuro.
    """

    __tablename__ = "product_references"

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("providers.id"), nullable=False, index=True
    )
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True, index=True
    )

    # antes `reference_id` en docs/03 (renombrado: aquí "id" ya es la PK propia)
    sku: Mapped[str] = mapped_column(String, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    # Marca del repuesto: quién lo FABRICA (NGK, Brembo, Motul). No confundir
    # con `provider_id`, que es a quién se le compra — la misma bujía NGK puede
    # venir de varios distribuidores. Tampoco es la marca de la moto a la que
    # le sirve: esa compatibilidad va aparte (A-22, pendiente).
    brand: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    base_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    # antes `iva` en docs/03 (ambiguo % vs. monto — ver D-19)
    iva_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
