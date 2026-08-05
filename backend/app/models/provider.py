from typing import Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SyncMixin, TenantScopedMixin, TimestampMixin, UUIDPKMixin


class Provider(Base, UUIDPKMixin, TenantScopedMixin, TimestampMixin, SyncMixin):
    """Proveedor — docs/03-modelo-datos.md §1.1."""

    __tablename__ = "providers"

    # antes `provider_id` en docs/03 (renombrado para no chocar con las FKs
    # `provider_id` de otras tablas que apuntan a `Provider.id`)
    provider_code: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    nit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    # antes `desc` en docs/03 (palabra reservada en SQL)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
