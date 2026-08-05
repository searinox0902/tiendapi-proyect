from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class Tenant(Base, UUIDPKMixin, TimestampMixin):
    """
    Negocio (pyme) suscrito a la plataforma — no confundir con `Customer`
    (los clientes finales DEL negocio). Ver docs/01-vision-negocio.md.

    Entidad nueva, no presente en el DDL original de docs/03-modelo-datos.md:
    necesaria para el aislamiento por cliente (D-10) en el backend central
    multi-tenant. Ver docs/07-decisiones-y-puntos-abiertos.md, D-23.
    """

    __tablename__ = "tenants"

    business_name: Mapped[str] = mapped_column(String, nullable=False)
    subscription_status: Mapped[str] = mapped_column(String, nullable=False, default="trial")
    subscribed_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
