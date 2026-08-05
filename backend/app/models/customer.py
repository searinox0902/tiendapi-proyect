from typing import Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SyncMixin, TenantScopedMixin, TimestampMixin, UUIDPKMixin


class Customer(Base, UUIDPKMixin, TenantScopedMixin, TimestampMixin, SyncMixin):
    """Cliente — docs/03-modelo-datos.md §1.4."""

    __tablename__ = "customers"

    nit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    fullname: Mapped[str] = mapped_column(String, nullable=False)
    mail: Mapped[Optional[str]] = mapped_column(String, nullable=True)
