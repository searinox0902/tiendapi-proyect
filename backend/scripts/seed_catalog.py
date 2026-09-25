"""Siembra el catálogo real de repuestos de moto bajo el negocio demo.

Es la semilla de producto del proyecto: **1.015 Referencias reales** de
`motopartes.com.co`, ya pasadas por el consolidador (`consolidate_scraped_catalog.py`,
D-89) — **una Referencia por SKU**, con la compatibilidad de modelos estacionada
en `description` como una línea `Compatible: …` hasta que exista A-22.

Uso, desde `backend/` y con la BBDD levantada y migrada:

    python -m scripts.seed          # crea demo@tiendapi.co / demo1234
    python -m scripts.seed_catalog  # carga las 1.015 Referencias bajo ese negocio

Con Docker, sin Python local:

    docker compose exec api python -m scripts.seed
    docker compose exec api python -m scripts.seed_catalog

**Por qué un script y no un `pg_dump`.** Un volcado de la BBDD de desarrollo
arrastra usuarios con su `password_hash`, 34 tenants de pruebas y facturas de
fixtures — ruido y datos de cuentas que no tienen por qué viajar. Esto es solo
el catálogo, en JSON legible y versionable, insertado por el mismo ORM que usa
la API: si el esquema cambia, este script falla en la migración y no a los tres
meses con una fila corrupta.

**Idempotente.** La unicidad es `(tenant_id, sku)` (índice
`ix_product_references_tenant_sku`, D-90), así que correrlo dos veces no
duplica: lo que ya existe se salta y se reporta al final.

Advertencias heredadas de `import_scraped_references.py`, que siguen vigentes:

  - Los precios son **scrapeados**, no negociados: `base_price` ya viene sin IVA
    (se dividió por 1,19 al importar). Son datos de desarrollo, no una lista de
    precios — zona de alto riesgo de CLAUDE.md.
  - No hay proveedor real. Todo cuelga de un placeholder,
    **"Catálogo Externo (Scraping)"**, para que se note que hay que reasignarlo
    antes de cualquier uso serio.
  - `brand` es quien **fabrica** el repuesto, no la moto a la que le sirve; esa
    compatibilidad es la línea `Compatible:` de la descripción.
"""
import json
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.category import Category
from app.models.provider import Provider
from app.models.reference import Reference
from app.models.user import User

DEMO_EMAIL = "demo@tiendapi.co"
PLACEHOLDER_PROVIDER_TITLE = "Catálogo Externo (Scraping)"
DATA_FILE = Path(__file__).parent / "seed_data" / "catalog_repuestos.json"


def main() -> None:
    if not DATA_FILE.exists():
        raise SystemExit(f"No encuentro el catálogo en {DATA_FILE}")

    rows = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    db = SessionLocal()
    try:
        #  El catálogo cuelga del negocio demo a propósito: es el usuario con el
        #  que se entra a la app, y un catálogo que no se ve al iniciar sesión
        #  no sirve de semilla.
        owner = db.execute(select(User).where(User.email == DEMO_EMAIL)).scalar_one_or_none()
        if owner is None:
            raise SystemExit(f"Falta {DEMO_EMAIL}. Corre primero: python -m scripts.seed")
        tenant_id = owner.tenant_id

        provider = db.execute(
            select(Provider).where(
                Provider.tenant_id == tenant_id,
                Provider.title == PLACEHOLDER_PROVIDER_TITLE,
            )
        ).scalar_one_or_none()
        if provider is None:
            provider = Provider(
                tenant_id=tenant_id,
                title=PLACEHOLDER_PROVIDER_TITLE,
                description="Placeholder del catálogo scrapeado. Reasignar a proveedores reales.",
            )
            db.add(provider)
            db.flush()

        categories: dict[str, Category] = {
            category.name: category
            for category in db.execute(
                select(Category).where(Category.tenant_id == tenant_id)
            ).scalars()
        }
        existing_skus = set(
            db.execute(
                select(Reference.sku).where(Reference.tenant_id == tenant_id)
            ).scalars()
        )

        created = skipped = 0
        new_categories = 0
        for row in rows:
            if row["sku"] in existing_skus:
                skipped += 1
                continue

            category = None
            name = row.get("category")
            if name:
                category = categories.get(name)
                if category is None:
                    category = Category(tenant_id=tenant_id, name=name)
                    db.add(category)
                    db.flush()
                    categories[name] = category
                    new_categories += 1

            db.add(
                Reference(
                    tenant_id=tenant_id,
                    provider_id=provider.id,
                    category_id=category.id if category else None,
                    sku=row["sku"],
                    title=row["title"],
                    description=row.get("description"),
                    brand=row.get("brand"),
                    image_url=row.get("image_url"),
                    base_price=Decimal(row["base_price"]),
                    iva_percentage=Decimal(row["iva_percentage"]),
                )
            )
            existing_skus.add(row["sku"])
            created += 1

        db.commit()
        print(f"Negocio: {tenant_id}  ({DEMO_EMAIL})")
        print(f"Referencias creadas: {created}   ya existían: {skipped}")
        print(f"Categorías nuevas: {new_categories}   proveedor: {PLACEHOLDER_PROVIDER_TITLE}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
