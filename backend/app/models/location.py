from typing import Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SyncMixin, TenantScopedMixin, TimestampMixin, UUIDPKMixin


class Location(Base, UUIDPKMixin, TenantScopedMixin, TimestampMixin, SyncMixin):
    """
    Ubicación (sucursal/bodega) — nueva entidad, docs/03-modelo-datos.md §1.8.

    `type` se valida como enum en la capa de Pydantic (app/schemas/location.py)
    y además con un CHECK constraint en la migración inicial (resuelve A-11).
    """

    __tablename__ = "locations"

    name: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    type: Mapped[str] = mapped_column(String, nullable=False)
