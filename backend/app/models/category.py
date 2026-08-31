import uuid
from typing import Optional

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SyncMixin, TenantScopedMixin, TimestampMixin, UUIDPKMixin


class Category(Base, UUIDPKMixin, TenantScopedMixin, TimestampMixin, SyncMixin):
    """Categoría — nueva entidad, docs/03-modelo-datos.md §1.7."""

    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    #  Nombre de ícono lucide (ej. "wrench"), sin `enum`/`CHECK` a propósito
    #  (D-72): a diferencia de `Location.type`, el set de íconos vive y crece
    #  en el frontend, no es un vocabulario de negocio fijo. Un nombre huérfano
    #  (ícono removido, dato viejo) cae a un ícono por defecto en el resolver
    #  del cliente, nunca rompe la UI.
    icon: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    #  Etiqueta de lote de importación (D-75, mismo criterio que
    #  `Reference.import_batch_id`, D-73) — habilita deshacer un lote entero.
    import_batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
