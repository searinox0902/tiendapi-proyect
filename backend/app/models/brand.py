import uuid
from typing import Optional

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SyncMixin, TenantScopedMixin, TimestampMixin, UUIDPKMixin


class Brand(Base, UUIDPKMixin, TenantScopedMixin, TimestampMixin, SyncMixin):
    """Marca del fabricante — catálogo propio, docs/07-decisiones-y-puntos-abiertos.md, D-71.

    Independiente de `Reference.brand` (texto libre, D-57): esta tabla es la
    fuente de sugerencias/gestión del Directorio, no una FK de `Reference` — ver
    D-71 para el porqué de mantenerlas desacopladas.
    """

    __tablename__ = "brands"

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    #  Etiqueta de lote de importación (D-75, mismo criterio que
    #  `Reference.import_batch_id`, D-73) — habilita deshacer un lote entero.
    import_batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
