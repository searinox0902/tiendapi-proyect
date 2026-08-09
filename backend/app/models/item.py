import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SyncMixin, TenantScopedMixin, TimestampMixin, UUIDPKMixin


class Item(Base, UUIDPKMixin, TenantScopedMixin, TimestampMixin, SyncMixin):
    """Ítem (existencia física) — docs/03-modelo-datos.md §1.3."""

    __tablename__ = "items"

    reference_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_references.id"), nullable=False, index=True
    )
    # Nullable (migración 0005): el alta manual rápida no exige elegir proveedor
    # ni ubicación en el momento — se puede completar después. La Referencia sí
    # sigue siendo obligatoria: sin ella la unidad no pertenece a ningún
    # producto y no hay nada que mostrar en la pantalla de detalle.
    provider_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("providers.id"), nullable=True, index=True
    )
    location_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id"), nullable=True, index=True
    )

    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False, default=0)
    # Precio de venta CON IVA de ESTA unidad (D-45) — el ajuste humano vive acá,
    # nunca en la Referencia. Obligatorio: se inicializa como espejo del precio
    # de catálogo al crear el Ítem (igual que ya hacía antes de esta columna).
    current_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Overrides opcionales por unidad (migraciones 0007/0008). `NULL` = "sigue
    # el catálogo": el endpoint hace `COALESCE(Item.x, Reference.x)` al leer,
    # así que una unidad sin tocar refleja el precio/IVA VIGENTE de catálogo,
    # no una foto fija del día que se creó — y el día que alguien la edita
    # acá, esa unidad puntual queda fija en lo que se escribió, sin afectar a
    # las demás existencias de la misma Referencia.
    iva_percentage: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    provider_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    # Precio base (sin IVA) propio de esta unidad — misma dinámica que crear
    # una Referencia: base + IVA determinan `current_price`, nunca se captura
    # a mano (migración 0008). Al cambiar éste o `iva_percentage`, el router
    # recalcula `current_price` con la misma fórmula del catálogo (D-45/D-46).
    base_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)

    # Ciclo de vida de la unidad (D-41): 'disponible' | 'vendido' | 'reservado' |
    # 'de_baja'. Se valida en Pydantic (ItemStatus) y con un CHECK acá —mismo
    # patrón que `Location.type`— porque el ORM no impone el enum por sí solo.
    status: Mapped[str] = mapped_column(String, nullable=False, default="disponible")
