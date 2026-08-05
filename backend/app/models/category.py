from typing import Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SyncMixin, TenantScopedMixin, TimestampMixin, UUIDPKMixin


class Category(Base, UUIDPKMixin, TenantScopedMixin, TimestampMixin, SyncMixin):
    """Categoría — nueva entidad, docs/03-modelo-datos.md §1.7."""

    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
