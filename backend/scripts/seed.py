"""Seed de desarrollo: crea un negocio demo + usuario propietario.

Uso (con la BBDD levantada y migrada), desde `backend/`:

    python -m scripts.seed
"""
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import User

DEMO_EMAIL = "demo@tiendapi.co"
DEMO_PASSWORD = "demo1234"  # noqa: S105 — credencial de desarrollo, no producción


def main() -> None:
    db = SessionLocal()
    try:
        existing = db.execute(select(User).where(User.email == DEMO_EMAIL)).scalar_one_or_none()
        if existing is not None:
            print(f"Ya existe {DEMO_EMAIL} (tenant {existing.tenant_id})")
            return

        tenant = Tenant(business_name="Negocio Demo")
        db.add(tenant)
        db.flush()

        db.add(
            User(
                tenant_id=tenant.id,
                email=DEMO_EMAIL,
                password_hash=hash_password(DEMO_PASSWORD),
                full_name="Dueño Demo",
                role="owner",
            )
        )
        db.commit()
        print(f"Creado: {DEMO_EMAIL} / {DEMO_PASSWORD}  (tenant {tenant.id})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
