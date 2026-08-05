import uuid

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class User(Base, UUIDPKMixin, TimestampMixin):
    """
    Usuario (asiento) del backend online. Un `Tenant` (negocio) tiene como
    máximo 3 usuarios — la regla de ≤3 asientos de D-32 (ver docs/07).

    - `email` es único a nivel **global** para que el login por email resuelva
      a un solo usuario; su `tenant_id` viaja luego en el token de sesión.
    - Cierra A-12: el `tenant_id` operativo se deriva del token de este usuario,
      ya no de un header `X-Tenant-ID` enviado por el cliente.
    """

    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False, default="member")  # owner | member
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
