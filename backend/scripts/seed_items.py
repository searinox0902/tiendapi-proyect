"""Seed de desarrollo: llena el inventario (Ítems) del negocio demo.

Complementa a `scripts/seed.py` (que solo crea tenant + usuario): acá se crean
proveedores, ubicaciones y las **unidades físicas** de las Referencias que ya
estén en catálogo, para que las pantallas de Productos tengan datos reales.

Uso (con la BBDD levantada y migrada), desde `backend/`:

    python -m scripts.seed_items            # no toca nada si ya hay Ítems
    python -m scripts.seed_items --reset    # borra los Ítems del tenant y re-siembra

Es **determinista** (`random.Random` con semilla fija): dos corridas con
`--reset` producen el mismo inventario —mismas unidades, precios y orden de
ingreso—, así que lo que se ve en pantalla es reproducible al reportar un bug.
Lo único que cambia entre corridas son las fechas absolutas de entrada, que se
anclan al `now()` de cada corrida para que el carrusel de "recién agregados" no
muestre siempre datos viejos; el orden relativo entre productos no cambia.
"""
import argparse
import random
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import delete, func, select

from app.core.database import SessionLocal
from app.core.pricing import sale_price as _sale_price
from app.models.item import Item
from app.models.location import Location
from app.models.provider import Provider
from app.models.reference import Reference
from app.models.user import User

# `sale_price` se importa de `app.core.pricing` en vez de repetir la fórmula:
# es la única implementación del precio de venta (D-45/D-46) y duplicarla sería
# duplicar el bug el día que cambie la regla de redondeo.

DEMO_EMAIL = "demo@tiendapi.co"
SEED = 20260807

PROVIDERS = [
    {"title": "Distribuidora La 80", "nit": "900123456-1", "provider_code": "DL80"},
    {"title": "Lubricantes del Valle", "nit": "901234567-2", "provider_code": "LDV"},
    {"title": "Repuestos La 33", "nit": "902345678-3", "provider_code": "RL33"},
    {"title": "Importadora Motopartes", "nit": "903456789-4", "provider_code": "IMP"},
    {"title": "Frenos y Suspensión SAS", "nit": "904567890-5", "provider_code": "FYS"},
    {"title": "Llantas del Pacífico", "nit": "905678901-6", "provider_code": "LDP"},
    {"title": "Eléctricos Medellín", "nit": "906789012-7", "provider_code": "ELM"},
]

LOCATIONS = [
    {"name": "Vitrina Frontal", "type": "sucursal", "address": "Local principal"},
    {"name": "Isla 1", "type": "sucursal", "address": "Local principal"},
    {"name": "Isla 2", "type": "sucursal", "address": "Local principal"},
    {"name": "Bodega", "type": "bodega", "address": "Trastienda"},
    {"name": "Bodega 2", "type": "bodega", "address": "Local anexo"},
    {"name": "Vitrina Trasera", "type": "sucursal", "address": "Local principal"},
]

# Cuántas unidades recibe cada Referencia, por posición en el catálogo ordenado
# por SKU. Se busca cubrir los casos que las pantallas tienen que saber pintar:
# agotado (0), stock normal, y un caso grande que ejercite la vista de detalle.
UNIT_PLAN = [
    0, 6, 14, 3, 22, 9, 0, 31, 12, 7,
    18, 4, 96, 11, 25, 8, 0, 16, 5, 40,
    13, 2, 27, 10, 19, 6, 33, 1, 15,
]


def _round_50(value: Decimal) -> Decimal:
    """Al múltiplo de $50 más cercano — misma convención que el precio de venta (D-46)."""
    return (value / 50).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * 50


def _ensure(db, model, tenant_id, match_field, rows):
    """Crea las filas que falten, identificándolas por `match_field`. No duplica."""
    existing = {
        getattr(obj, match_field): obj
        for obj in db.execute(select(model).where(model.tenant_id == tenant_id)).scalars()
    }
    created = []
    for row in rows:
        key = row[match_field]
        if key in existing:
            created.append(existing[key])
            continue
        obj = model(tenant_id=tenant_id, **row)
        db.add(obj)
        created.append(obj)
    db.flush()
    return created


def main(reset: bool) -> None:
    rng = random.Random(SEED)
    db = SessionLocal()
    try:
        user = db.execute(select(User).where(User.email == DEMO_EMAIL)).scalar_one_or_none()
        if user is None:
            print(f"No existe {DEMO_EMAIL}. Corre primero: python -m scripts.seed")
            return
        tenant_id = user.tenant_id

        existing_items = db.execute(
            select(func.count()).select_from(Item).where(Item.tenant_id == tenant_id)
        ).scalar_one()
        if existing_items and not reset:
            print(f"Ya hay {existing_items} Ítems. Usa --reset para borrarlos y re-sembrar.")
            return
        if existing_items:
            db.execute(delete(Item).where(Item.tenant_id == tenant_id))
            print(f"Borrados {existing_items} Ítems previos.")

        providers = _ensure(db, Provider, tenant_id, "title", PROVIDERS)
        locations = _ensure(db, Location, tenant_id, "name", LOCATIONS)
        print(f"Proveedores: {len(providers)} | Ubicaciones: {len(locations)}")

        references = list(
            db.execute(
                select(Reference).where(Reference.tenant_id == tenant_id).order_by(Reference.sku)
            ).scalars()
        )
        if not references:
            print("No hay Referencias en catálogo: no hay de qué crear existencias.")
            return

        # `created_at` tiene `server_default=func.now()`, y en Postgres `now()` es
        # el instante de INICIO de la transacción: sin fijarla a mano, las 400+
        # unidades quedarían con el MISMO timestamp y "productos recién
        # agregados" (que ordena por `MAX(Item.created_at)`) no tendría por dónde
        # ordenar. Acá se escalona la entrada de mercancía hacia atrás en el
        # tiempo para que ese carrusel muestre algo con sentido.
        entry_order = list(range(len(references)))
        rng.shuffle(entry_order)
        now = datetime.now(timezone.utc)

        total_created = 0
        for index, reference in enumerate(references):
            # El costo de compra es 100% manual (D-52) y el catálogo existente no
            # lo trae; se rellena acá para que la pantalla de detalle no muestre
            # toda la columna en "—".
            if reference.provider_price is None:
                reference.provider_price = _round_50(
                    reference.base_price * Decimal(rng.randint(68, 82)) / Decimal(100)
                )

            catalog_price = _sale_price(reference.base_price, reference.iva_percentage)
            units = UNIT_PLAN[index % len(UNIT_PLAN)]

            # Cada producto recibió su mercancía en un momento distinto; el
            # `rank` define qué tan atrás quedó ese ingreso.
            rank = entry_order[index]
            entry_at = now - timedelta(hours=rank * 9)

            for unit_number in range(units):
                # Cada unidad tiene su propio precio (D-41): la mayoría va al
                # precio de catálogo y unas pocas quedan con descuento, que es
                # justo el caso de uso que justifica el precio por unidad.
                discount = rng.choice([0, 0, 0, 0, 500, 1000, 2000])
                db.add(
                    Item(
                        tenant_id=tenant_id,
                        reference_id=reference.id,
                        provider_id=rng.choice(providers).id,
                        location_id=rng.choice(locations).id,
                        quantity=Decimal(1),
                        current_price=catalog_price - Decimal(discount),
                        # Las unidades de un mismo ingreso entran con minutos de
                        # diferencia, no todas en el mismo instante.
                        created_at=entry_at + timedelta(minutes=unit_number),
                    )
                )
            total_created += units

        db.commit()
        print(f"Creadas {total_created} unidades sobre {len(references)} Referencias.")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset", action="store_true", help="Borra los Ítems del tenant y re-siembra"
    )
    main(parser.parse_args().reset)
