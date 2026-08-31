"""Seed de desarrollo: llena el histórico de Facturas del negocio demo.

Corre **después** de `scripts/seed_items.py`: cada línea de factura apunta a una
unidad física real (`Item`), porque así lo exige el modelo (D-41) y porque la
utilidad de D-49 se calcula contra el costo de esa unidad.

Uso (con la BBDD levantada y migrada), desde `backend/`:

    python -m scripts.seed_bills            # no toca nada si ya hay Facturas
    python -m scripts.seed_bills --reset    # borra las Facturas del tenant y re-siembra

Determinista (`random.Random` con semilla fija), igual que `seed_items`: dos
corridas con `--reset` producen el mismo histórico. Lo único anclado al `now()`
de la corrida son las fechas, para que el filtro por rango tenga siempre algo
reciente que mostrar.

Las unidades facturadas quedan en `status='sold'`: una unidad vendida no
puede seguir apareciendo como disponible en la pantalla de Productos.
"""
import argparse
import random
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import delete, func, select

from app.core.database import SessionLocal
from app.models.bill import Bill
from app.models.bill_item import BillItem
from app.models.customer import Customer
from app.models.item import Item
from app.models.reference import Reference
from app.models.user import User

DEMO_EMAIL = "demo@tiendapi.co"
SEED = 20260809

CUSTOMERS = [
    {"fullname": "Consumidor final", "nit": "222222222222", "mail": None},
    {"fullname": "Taller El Motorista", "nit": "900456123-4", "mail": "taller@motorista.co"},
    {"fullname": "Mensajería Rápida SAS", "nit": "901567234-5", "mail": "flota@rapida.co"},
    {"fullname": "Carlos Restrepo", "nit": "71234567", "mail": "crestrepo@mail.com"},
    {"fullname": "Moto Servicio La 70", "nit": "902678345-6", "mail": "contacto@la70.co"},
    {"fullname": "Diana Ospina", "nit": "43876123", "mail": "dospina@mail.com"},
]

#  Estados fiscales de la tanda (D-48). La mayoría autorizada, unas pocas sin
#  declarar y una rechazada: es el reparto que hace visible el desglose de la
#  card sin pintar un negocio en infracción. `None` = nunca entró al trámite,
#  que es lo normal hoy porque la integración DIAN está diferida (D-09/D-38).
FISCAL_PLAN = [
    "autorizada", "autorizada", "autorizada", "pendiente", "autorizada",
    "autorizada", "contingencia", "autorizada", "autorizada", None,
    "autorizada", "rechazada", "autorizada", "pendiente", "autorizada",
    "autorizada", "autorizada", None, "contingencia", "autorizada",
    "autorizada", "autorizada", "pendiente", "autorizada", "autorizada",
]

BILL_COUNT = 25


def _round_2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _ensure_customers(db, tenant_id):
    """Crea los clientes que falten, identificados por nombre. No duplica."""
    existing = {
        obj.fullname: obj
        for obj in db.execute(
            select(Customer).where(Customer.tenant_id == tenant_id)
        ).scalars()
    }
    result = []
    for row in CUSTOMERS:
        obj = existing.get(row["fullname"])
        if obj is None:
            obj = Customer(tenant_id=tenant_id, **row)
            db.add(obj)
        result.append(obj)
    db.flush()
    return result


def main(reset: bool) -> None:
    rng = random.Random(SEED)
    db = SessionLocal()
    try:
        user = db.execute(select(User).where(User.email == DEMO_EMAIL)).scalar_one_or_none()
        if user is None:
            print(f"No existe {DEMO_EMAIL}. Corre primero: python -m scripts.seed")
            return
        tenant_id = user.tenant_id

        existing_bills = db.execute(
            select(func.count()).select_from(Bill).where(Bill.tenant_id == tenant_id)
        ).scalar_one()
        if existing_bills and not reset:
            print(f"Ya hay {existing_bills} Facturas. Usa --reset para borrarlas y re-sembrar.")
            return
        if existing_bills:
            #  Las líneas primero: `BillItem` tiene FK a `Bill` y el cascade solo
            #  aplica al borrar por ORM, no con un DELETE masivo.
            db.execute(delete(BillItem).where(BillItem.tenant_id == tenant_id))
            db.execute(delete(Bill).where(Bill.tenant_id == tenant_id))
            #  Las unidades vuelven a estar disponibles: si no, cada --reset
            #  dejaría inventario marcado como vendido sin factura que lo respalde.
            db.execute(
                Item.__table__.update()
                .where(Item.tenant_id == tenant_id, Item.status == "sold")
                .values(status="available")
            )
            print(f"Borradas {existing_bills} Facturas previas.")

        customers = _ensure_customers(db, tenant_id)

        #  Solo unidades disponibles: facturar una unidad ya vendida sería
        #  venderla dos veces.
        available = list(
            db.execute(
                select(Item, Reference)
                .join(Reference, Reference.id == Item.reference_id)
                .where(Item.tenant_id == tenant_id, Item.status == "available")
                .order_by(Item.id)
            ).all()
        )
        if not available:
            print("No hay unidades disponibles. Corre primero: python -m scripts.seed_items")
            return

        rng.shuffle(available)
        now = datetime.now(timezone.utc)
        cursor = 0
        created = 0

        for index in range(BILL_COUNT):
            lines_count = rng.randint(1, 4)
            batch = available[cursor:cursor + lines_count]
            cursor += lines_count
            if not batch:
                break

            #  Escalonadas hacia atrás: ~3 meses de histórico, para que el
            #  filtro por rango de fechas tenga de dónde recortar.
            issued_at = now - timedelta(days=index * 3, hours=rng.randint(0, 20))

            bill = Bill(
                tenant_id=tenant_id,
                customer_id=rng.choice(customers).id,
                bill_number=f"FV-{2600 + index:04d}",
                subtotal=Decimal(0),
                total_iva=Decimal(0),
                total=Decimal(0),
                fiscal_status=FISCAL_PLAN[index % len(FISCAL_PLAN)],
                created_at=issued_at,
                updated_at=issued_at,
            )
            db.add(bill)
            db.flush()

            subtotal = Decimal(0)
            total_iva = Decimal(0)
            total = Decimal(0)

            for item, reference in batch:
                #  El precio cobrado es el de la unidad (D-45), y base/IVA se
                #  descomponen hacia atrás desde él — misma dirección que la
                #  caja registradora, para que subtotal + IVA dé exactamente el
                #  total pese al redondeo a $50 (D-46).
                unit_price = Decimal(item.current_price)
                iva_percentage = (
                    item.iva_percentage
                    if item.iva_percentage is not None
                    else reference.iva_percentage
                )
                base = _round_2(unit_price / (Decimal(1) + iva_percentage / Decimal(100)))
                iva_amount = unit_price - base

                db.add(
                    BillItem(
                        tenant_id=tenant_id,
                        bill_id=bill.id,
                        item_id=item.id,
                        quantity=Decimal(1),
                        unit_price=unit_price,
                        iva_percentage=iva_percentage,
                        iva_amount=iva_amount,
                        total=unit_price,
                        created_at=issued_at,
                        updated_at=issued_at,
                    )
                )
                item.status = "sold"

                subtotal += base
                total_iva += iva_amount
                total += unit_price

            bill.subtotal = subtotal
            bill.total_iva = total_iva
            bill.total = total
            created += 1

        db.commit()
        print(f"Creadas {created} Facturas sobre {cursor} unidades vendidas.")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset", action="store_true", help="Borra las Facturas del tenant y re-siembra"
    )
    main(parser.parse_args().reset)
