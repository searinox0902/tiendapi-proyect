import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy import ForeignKey, Index, Numeric, String
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

    #  SKU único **por tenant** (D-90, migración 0018) — revoca la unicidad
    #  blanda de D-73. Compuesto y no sobre `sku` solo porque el catálogo es
    #  multi-tenant: dos negocios pueden usar el mismo código del mismo
    #  proveedor sin que eso sea un conflicto. Reemplaza al índice común que
    #  tenía la columna, y sirve igual para las búsquedas por SKU.
    __table_args__ = (
        Index("ix_product_references_tenant_sku", "tenant_id", "sku", unique=True),
    )

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("providers.id"), nullable=False, index=True
    )
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True, index=True
    )

    # antes `reference_id` en docs/03 (renombrado: aquí "id" ya es la PK propia)
    #  Sin `index=True`: lo cubre el índice único compuesto de `__table_args__`.
    sku: Mapped[str] = mapped_column(String, nullable=False)
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
    # Costo de adquisición (lado COMPRA) — eje independiente de base_price/sale_price
    # (lado VENTA), sin fórmula que lo derive (D-47). Nullable: el catálogo existente
    # no lo tiene todavía; se captura 100% manual desde el CRUD (D-52).
    # Se llamaba `precio_proveedor` hasta la migración 0011 (D-62): mismo nombre
    # que su equivalente por unidad, `Item.provider_price`, que es el que lo
    # sobreescribe cuando esa unidad puntual costó otra cosa.
    provider_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)

    #  Etiqueta de lote de importación (D-73), NO una FK a una tabla de lotes:
    #  no hace falta historial de corridas, solo poder deshacer una en bloque.
    #  Un UUID nuevo por corrida agrupa las filas que creó; `NULL` = alta manual
    #  o de un lote ya deshecho (ver `revert_import_batch`).
    import_batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
