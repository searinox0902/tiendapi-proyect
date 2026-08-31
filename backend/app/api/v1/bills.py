import uuid
from datetime import date, datetime, time, timezone
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.api.deps import ImageResolver, get_db, get_image_resolver, get_tenant_id
from app.api.filters import contains as _contains
from app.core.config import settings
from app.crud.base import CRUDBase
from app.exports import billing as billing_export
from app.models.bill import Bill
from app.models.bill_item import BillItem
from app.models.customer import Customer
from app.models.item import Item
from app.models.reference import Reference
from app.models.tenant import Tenant
from app.schemas.bill import (
    BillCreate,
    BillDetailRead,
    BillListRead,
    BillRead,
    BillSummaryRead,
    BillVoid,
    CheckoutCreate,
    FiscalStatus,
)
from app.schemas.common import Page

router = APIRouter(prefix="/bills", tags=["bills"])
crud = CRUDBase(Bill)


def _day_bounds(value: date, *, end_of_day: bool) -> datetime:
    """
    Convierte un día suelto del filtro en un instante UTC.

    El rango que manda la UI son fechas sin hora, pero `created_at` es un
    timestamp: comparar contra la fecha pelada dejaría fuera todas las facturas
    del último día (las de las 00:01 en adelante). Por eso el extremo derecho
    se estira hasta el final del día.
    """
    moment = time.max if end_of_day else time.min
    return datetime.combine(value, moment, tzinfo=timezone.utc)


def _bill_conditions(
    tenant_id: uuid.UUID,
    customer: str | None,
    bill_number: str | None,
    date_from: date | None,
    date_to: date | None,
    fiscal_status: FiscalStatus | None,
    voided: bool | None = None,
    ids: list[uuid.UUID] | None = None,
) -> list:
    """
    Filtros de la pantalla Facturación, compartidos por la tabla, su resumen y
    los dos endpoints de exportación (D-78).

    Van juntos por la misma razón que en Productos: si el resumen y la tabla
    filtraran distinto, las cifras de cabecera no corresponderían a las filas
    de abajo y no habría forma de notarlo mirando la pantalla. Y desde D-78 hay
    una razón más fuerte: es lo que hace **demostrable** que el paquete
    exportado es exactamente el conjunto que se ve en pantalla — un filtro que
    exista en la tabla y no acá rompería esa garantía en silencio.

    `voided` es el eje **documento** (D-81): `None` = todas, `False` = solo
    vigentes, `True` = solo anuladas. Es el único estado que el usuario filtra
    hoy; el fiscal sigue aceptándose por API para cuando la integración DIAN
    exista (D-09/D-38), pero ya no se ofrece en la pantalla porque hoy vale
    `NULL` en todas las facturas.
    """
    conditions = [Bill.tenant_id == tenant_id]
    #  Selección explícita del usuario (los checkboxes de la tabla). Se combina
    #  con el resto de filtros en vez de reemplazarlos: `tenant_id` tiene que
    #  seguir aplicando siempre — sin eso, mandar los ids de otro negocio
    #  bastaría para llevarse sus facturas.
    if ids is not None:
        conditions.append(Bill.id.in_(ids))
    if voided is not None:
        conditions.append(
            Bill.voided_at.is_not(None) if voided else Bill.voided_at.is_(None)
        )
    if customer:
        conditions.append(Customer.fullname.ilike(_contains(customer), escape="\\"))
    if bill_number:
        conditions.append(Bill.bill_number.ilike(_contains(bill_number), escape="\\"))
    if date_from is not None:
        conditions.append(Bill.created_at >= _day_bounds(date_from, end_of_day=False))
    if date_to is not None:
        conditions.append(Bill.created_at <= _day_bounds(date_to, end_of_day=True))
    if fiscal_status is not None:
        conditions.append(Bill.fiscal_status == fiscal_status.value)
    return conditions


def _next_bill_number(db: Session, tenant_id: uuid.UUID) -> str:
    """
    Siguiente consecutivo visible (`FV-XXXX`).

    Se calcula del máximo existente y **no** con un contador en memoria: el
    número de factura es un dato fiscal, tiene que sobrevivir a reinicios y no
    puede depender de qué proceso lo emitió. Sigue siendo provisional — la
    numeración autorizada por la DIAN (rangos, prefijo, vigencia) llega con la
    integración (D-09/D-38), y esto es lo que la reemplazará entonces.
    """
    last = db.execute(
        select(func.max(Bill.bill_number)).where(Bill.tenant_id == tenant_id)
    ).scalar_one_or_none()
    if not last:
        return "FV-0001"
    try:
        return f"FV-{int(last.rsplit('-', 1)[1]) + 1:04d}"
    except (IndexError, ValueError):
        #  Numeración con otro formato (importada, migrada): se arranca una
        #  serie propia en vez de fallar el cobro por no poder parsear.
        count = db.execute(
            select(func.count()).select_from(Bill).where(Bill.tenant_id == tenant_id)
        ).scalar_one()
        return f"FV-{count + 1:04d}"


@router.get("/", response_model=Page[BillListRead])
def list_bills(
    skip: int = Query(0, ge=0, description="Registros a saltar"),
    limit: int = Query(20, ge=1, le=100, description="Máximo de registros por página"),
    customer: str | None = Query(None, description="Nombre del cliente, coincidencia parcial"),
    bill_number: str | None = Query(None, description="Código de factura, coincidencia parcial"),
    date_from: date | None = Query(None, description="Desde (inclusive)"),
    date_to: date | None = Query(None, description="Hasta (inclusive, día completo)"),
    fiscal_status: FiscalStatus | None = Query(None, description="Estado fiscal DIAN (D-48)"),
    voided: bool | None = Query(
        None,
        description="Eje documento (D-81): omitir = todas, false = vigentes, true = anuladas",
    ),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Listado paginado y filtrable de Facturas — pantalla Facturación (D-51).

    El `JOIN` con `Customer` no es decorativo: el filtro por nombre de cliente
    se resuelve en la base, y el nombre viaja en la fila para que la tabla no
    tenga que pedir N clientes por página.
    """
    conditions = _bill_conditions(
        tenant_id, customer, bill_number, date_from, date_to, fiscal_status, voided
    )

    total = db.execute(
        select(func.count())
        .select_from(Bill)
        .join(Customer, Customer.id == Bill.customer_id)
        .where(*conditions)
    ).scalar_one()

    #  Subconsulta para el conteo de líneas: hacerlo con un JOIN a `bill_items`
    #  multiplicaría las filas de la factura y rompería el resto de las
    #  columnas (una factura de 3 líneas aparecería 3 veces).
    items_count = (
        select(func.count(BillItem.id))
        .where(BillItem.bill_id == Bill.id)
        .correlate(Bill)
        .scalar_subquery()
    )

    #  Más reciente primero: en una caja lo que se busca es casi siempre la
    #  venta de hoy. Desempate por `id` para que dos facturas del mismo
    #  instante no alternen de orden entre páginas.
    rows = db.execute(
        select(Bill, Customer.fullname, items_count.label("items_count"))
        .join(Customer, Customer.id == Bill.customer_id)
        .where(*conditions)
        .order_by(Bill.created_at.desc(), Bill.id.desc())
        .offset(skip)
        .limit(limit)
    ).all()

    return {
        "items": [
            {
                "id": bill.id,
                "bill_number": bill.bill_number,
                "customer_id": bill.customer_id,
                "customer_name": customer_name,
                "subtotal": bill.subtotal,
                "total_iva": bill.total_iva,
                "total": bill.total,
                "fiscal_status": bill.fiscal_status,
                "voided_at": bill.voided_at,
                "items_count": line_count,
                "created_at": bill.created_at,
            }
            for bill, customer_name, line_count in rows
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/summary", response_model=BillSummaryRead)
def bills_summary(
    customer: str | None = Query(None, description="Nombre del cliente, coincidencia parcial"),
    bill_number: str | None = Query(None, description="Código de factura, coincidencia parcial"),
    date_from: date | None = Query(None, description="Desde (inclusive)"),
    date_to: date | None = Query(None, description="Hasta (inclusive, día completo)"),
    fiscal_status: FiscalStatus | None = Query(None, description="Estado fiscal DIAN (D-48)"),
    voided: bool | None = Query(
        None,
        description="Eje documento (D-81): omitir = todas, false = vigentes, true = anuladas",
    ),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Cifras de cabecera de Facturación — fórmulas de D-49.

    La utilidad va en una consulta aparte, y no como otra columna de la
    primera: se calcula sobre `BillItem` (una fila por línea) mientras que
    facturado/IVA se calculan sobre `Bill` (una fila por factura). Sumar las
    dos cosas en la misma consulta multiplicaría `Bill.total` por el número de
    líneas de cada factura e inflaría el facturado — el mismo error de producto
    cartesiano que ya apareció en el detalle de Producto.
    """
    conditions = _bill_conditions(
        tenant_id, customer, bill_number, date_from, date_to, fiscal_status, voided
    )

    def _count_when(condition) -> int:
        return func.count(case((condition, 1)))

    #  Una factura anulada (D-60) no aporta dinero: su mercancía volvió al
    #  inventario. Se **suma cero** en vez de excluir la fila de la consulta
    #  porque la misma pasada tiene que seguir contándola como documento
    #  emitido (`total_bills`) y clasificándola por estado fiscal.
    def _money_when_valid(column):
        return func.coalesce(func.sum(case((Bill.voided_at.is_(None), column), else_=0)), 0)

    totals = db.execute(
        select(
            _money_when_valid(Bill.total),
            _money_when_valid(Bill.total_iva),
            func.count(Bill.id),
            _count_when(Bill.voided_at.is_not(None)),
        )
        .select_from(Bill)
        .join(Customer, Customer.id == Bill.customer_id)
        .where(*conditions)
    ).one()

    #  Utilidad = Σ (precio final con IVA − costo sin IVA) × cantidad. D-67
    #  había señalado esta resta como "inflada por el IVA" y propuso netear el
    #  IVA del lado del ingreso antes de restar — decisión revertida
    #  deliberadamente (ver D-70/A-26): el usuario base (vendedor) piensa en
    #  caja, no en utilidad neta contable, y el IVA recaudado ya se muestra
    #  aparte en su propia card, así que no se pierde el dato. No "corregir"
    #  esto sin releer D-70. El costo sale del `COALESCE` de siempre: el
    #  override por unidad si lo tiene, si no el del catálogo. `provider_price`
    #  es nullable (captura manual, D-52), y para las unidades sin costo se
    #  cuenta aparte en vez de asumir cero — asumir cero inflaría la utilidad y
    #  haría creer que se ganó más.
    unit_cost = func.coalesce(Item.provider_price, Reference.provider_price)
    profit = db.execute(
        select(
            func.coalesce(
                func.sum((BillItem.unit_price - unit_cost) * BillItem.quantity), 0
            ),
            func.coalesce(
                func.sum(case((unit_cost.is_(None), BillItem.quantity), else_=0)), 0
            ),
        )
        .select_from(BillItem)
        .join(Bill, Bill.id == BillItem.bill_id)
        .join(Customer, Customer.id == Bill.customer_id)
        .join(Item, Item.id == BillItem.item_id)
        .join(Reference, Reference.id == Item.reference_id)
        #  Misma exclusión que arriba: la utilidad de una venta anulada no se
        #  ganó. Acá sí se filtra la fila entera porque esta consulta solo
        #  produce cifras de dinero.
        .where(*conditions, Bill.voided_at.is_(None))
    ).one()

    total_billed, total_iva, total_bills, voided = totals
    total_profit, units_without_cost = profit

    return {
        "total_billed": total_billed,
        "total_iva": total_iva,
        "total_profit": total_profit,
        "units_without_cost": int(units_without_cost or 0),
        "total_bills": total_bills,
        "voided_bills": voided,
    }


#  ⚠️ Los dos endpoints de `/export` van declarados **antes** de cualquier
#  `/{bill_id}`: FastAPI resuelve por orden, y si `/{bill_id}` se registrara
#  primero, `GET /bills/export` entraría por ahí e intentaría parsear "export"
#  como UUID — un 422 confuso en la ruta equivocada. Mismo cuidado que ya se
#  tiene con `/summary`.
@router.get("/export/summary")
def export_summary(
    customer: str | None = Query(None, description="Nombre del cliente, coincidencia parcial"),
    bill_number: str | None = Query(None, description="Código de factura, coincidencia parcial"),
    date_from: date | None = Query(None, description="Desde (inclusive)"),
    date_to: date | None = Query(None, description="Hasta (inclusive, día completo)"),
    fiscal_status: FiscalStatus | None = Query(None, description="Estado fiscal DIAN (D-48)"),
    voided: bool | None = Query(
        None,
        description="Eje documento (D-81): omitir = todas, false = vigentes, true = anuladas",
    ),
    ids: list[uuid.UUID] | None = Query(
        None,
        description="Exportar solo estas facturas (selección de la tabla). Se combina con los demás filtros",
    ),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Cuenta qué entraría en el paquete **sin construir el archivo** (D-78).

    Existe porque el zip se arma en memoria y con un filtro amplio puede ser un
    PDF por cada factura del año: el diálogo necesita poder decir cuántas son
    —y cuántas están anuladas— **antes** de que el usuario confirme. Mismo
    patrón previsualizar→confirmar de `/backup/summary` (D-77).

    No hay tope duro a propósito (D-78): negarle al usuario un paquete que
    quizá necesita es peor que armarlo grande con el dato a la vista.
    """
    conditions = _bill_conditions(
        tenant_id, customer, bill_number, date_from, date_to, fiscal_status, voided, ids
    )

    totals = db.execute(
        select(
            func.count(Bill.id),
            func.count(case((Bill.voided_at.is_not(None), 1))),
        )
        .select_from(Bill)
        .join(Customer, Customer.id == Bill.customer_id)
        .where(*conditions)
    ).one()

    total_bills, voided_bills = totals
    tenant = db.execute(select(Tenant).where(Tenant.id == tenant_id)).scalar_one_or_none()

    return {
        "business_name": tenant.business_name if tenant else "—",
        "platform_version": settings.app_version,
        "total_bills": total_bills,
        "voided_bills": voided_bills,
        #  Se declaran explícitos para que el frontend no los asuma: el día que
        #  SQLCipher entre (D-06) o exista la copia firmada del proveedor DIAN
        #  (D-09/D-38), estos pasan a `true` y las advertencias de la UI se
        #  apagan solas sin tocar el componente. Mismo criterio que D-77.
        "encrypted": False,
        "dian_valid": False,
    }


@router.get("/export")
def export_bills_package(
    customer: str | None = Query(None, description="Nombre del cliente, coincidencia parcial"),
    bill_number: str | None = Query(None, description="Código de factura, coincidencia parcial"),
    date_from: date | None = Query(None, description="Desde (inclusive)"),
    date_to: date | None = Query(None, description="Hasta (inclusive, día completo)"),
    fiscal_status: FiscalStatus | None = Query(None, description="Estado fiscal DIAN (D-48)"),
    voided: bool | None = Query(
        None,
        description="Eje documento (D-81): omitir = todas, false = vigentes, true = anuladas",
    ),
    ids: list[uuid.UUID] | None = Query(
        None,
        description="Exportar solo estas facturas (selección de la tabla). Se combina con los demás filtros",
    ),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Paquete de Facturación: zip con un PDF por factura + Excel índice (D-78).

    Acepta **los mismos filtros que el listado** y los resuelve con el mismo
    `_bill_conditions`: es lo que hace demostrable que el paquete es exactamente
    el conjunto que el usuario está viendo en pantalla, y no un query paralelo
    que podría filtrar distinto sin que nadie lo note.

    **No contradice D-61** (ver el encabezado de `app/exports/billing.py`): el
    sistema no persiste nada, el usuario se lleva un corte que él mismo filtró.
    Y no tiene contraparte de importación — las facturas salen, jamás entran
    (asimetría de D-73, integridad de D-07).
    """
    conditions = _bill_conditions(
        tenant_id, customer, bill_number, date_from, date_to, fiscal_status, voided, ids
    )

    content, filename, _count = billing_export.build_package(
        db,
        tenant_id,
        conditions,
        #  Los filtros viajan al paquete para quedar impresos en la hoja
        #  "Alcance" del Excel: una carpeta suelta no dice qué corte contiene.
        filters={
            "customer": customer,
            "bill_number": bill_number,
            "date_from": date_from,
            "date_to": date_to,
            "fiscal_status": fiscal_status,
        },
    )

    return Response(
        content=content,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            #  Sin esto el navegador no deja leer el nombre del archivo desde JS
            #  (CORS oculta las cabeceras no expuestas) y la descarga
            #  terminaría con un nombre inventado por el cliente.
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.post("/checkout", response_model=BillRead, status_code=status.HTTP_201_CREATED)
def checkout(
    payload: CheckoutCreate,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Cierra una venta de la caja registradora: resuelve unidades, descuenta
    inventario y emite la Factura, todo en una transacción.

    Existe aparte de `POST /` porque el cliente **no sabe** —ni debe saber—
    qué unidades físicas está vendiendo: el carrito habla de Referencia y
    cantidad (D-41). Elegir las unidades acá y no en el navegador es lo único
    que evita que dos cajas vendan la misma unidad: la selección, la marca de
    `sold` y la Factura ocurren dentro de la misma transacción.

    El desglose base/IVA se deriva **hacia atrás** desde el precio cobrado
    (D-45), nunca se acepta del cliente: es lo que garantiza que
    `subtotal + IVA = total` exactamente, incluso con descuento y con el
    redondeo a $50 (D-46) de por medio.
    """
    if (payload.customer_id is None) == (payload.new_customer is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Manda customer_id (cliente existente) o new_customer, no ambos ni ninguno",
        )

    if payload.customer_id is not None:
        customer = db.execute(
            select(Customer).where(
                Customer.id == payload.customer_id, Customer.tenant_id == tenant_id
            )
        ).scalar_one_or_none()
        if customer is None:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
    else:
        customer = Customer(
            tenant_id=tenant_id,
            nit=payload.new_customer.nit,
            fullname=payload.new_customer.fullname.strip(),
        )
        db.add(customer)
        db.flush()

    bill = Bill(
        tenant_id=tenant_id,
        customer_id=customer.id,
        bill_number=_next_bill_number(db, tenant_id),
        subtotal=Decimal(0),
        total_iva=Decimal(0),
        total=Decimal(0),
        #  Sin integración DIAN viva (D-09/D-38) la factura no entra a ningún
        #  trámite fiscal: queda en NULL, que dice exactamente eso (D-48/D-59).
        fiscal_status=None,
    )
    db.add(bill)
    db.flush()

    subtotal = Decimal(0)
    total_iva = Decimal(0)
    total = Decimal(0)

    for line in payload.lines:
        reference = db.execute(
            select(Reference).where(
                Reference.id == line.reference_id, Reference.tenant_id == tenant_id
            )
        ).scalar_one_or_none()
        if reference is None:
            raise HTTPException(status_code=404, detail=f"Referencia {line.reference_id} no existe")

        #  `with_for_update`: bloquea las unidades elegidas hasta el commit, así
        #  una segunda caja que cobre lo mismo al mismo tiempo espera y ve el
        #  inventario ya descontado en vez de vender la misma unidad dos veces.
        units = list(
            db.execute(
                select(Item)
                .where(
                    Item.tenant_id == tenant_id,
                    Item.reference_id == line.reference_id,
                    Item.status == "available",
                )
                .order_by(Item.created_at)
                .limit(line.quantity)
                .with_for_update(skip_locked=True)
            ).scalars()
        )
        if len(units) < line.quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Sin existencias suficientes de {reference.sku}: "
                    f"pediste {line.quantity} y quedan {len(units)}"
                ),
            )

        iva_percentage = (
            units[0].iva_percentage
            if units[0].iva_percentage is not None
            else reference.iva_percentage
        )
        #  Desglose inverso (D-45): del total cobrado se saca la base, y el IVA
        #  es la resta — nunca al revés.
        unit_base = (line.unit_price / (Decimal(1) + iva_percentage / Decimal(100))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        unit_iva = line.unit_price - unit_base

        for unit in units:
            db.add(
                BillItem(
                    tenant_id=tenant_id,
                    bill_id=bill.id,
                    item_id=unit.id,
                    quantity=Decimal(1),
                    unit_price=line.unit_price,
                    iva_percentage=iva_percentage,
                    iva_amount=unit_iva,
                    total=line.unit_price,
                )
            )
            #  Una unidad vendida sale del inventario disponible; si no, seguiría
            #  apareciendo como vendible en Productos y en la propia caja.
            unit.status = "sold"
            unit.current_price = line.unit_price

            subtotal += unit_base
            total_iva += unit_iva
            total += line.unit_price

    bill.subtotal = subtotal
    bill.total_iva = total_iva
    bill.total = total

    db.commit()
    db.refresh(bill)
    return bill


@router.post("/", response_model=BillRead, status_code=status.HTTP_201_CREATED)
def create_bill(
    payload: BillCreate,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Crea una Factura con sus líneas en una única transacción.

    La firma HMAC y la cadena de hash (`prev_hash`) descritas en
    docs/04-seguridad.md NO se calculan en este esqueleto — quedan como
    responsabilidad de una capa de seguridad a implementar antes de producción.
    """
    bill = Bill(
        tenant_id=tenant_id,
        customer_id=payload.customer_id,
        bill_number=payload.bill_number,
        subtotal=payload.subtotal,
        total_iva=payload.total_iva,
        total=payload.total,
    )
    db.add(bill)
    db.flush()

    for item_payload in payload.items:
        db.add(
            BillItem(
                tenant_id=tenant_id,
                bill_id=bill.id,
                **item_payload.model_dump(),
            )
        )

    db.commit()
    db.refresh(bill)
    return bill


@router.get("/{bill_id}", response_model=BillRead)
def get_bill(
    bill_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    obj = crud.get(db, tenant_id, bill_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    return obj


@router.get("/{bill_id}/detail", response_model=BillDetailRead)
def get_bill_detail(
    bill_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    resolve_image: ImageResolver = Depends(get_image_resolver),
):
    """
    Factura completa para la pantalla de detalle (D-61).

    Existe aparte de `GET /{bill_id}` porque esa devuelve `BillItem` crudos:
    `item_id` sin SKU ni nombre, y **una fila por unidad física** — vender 3
    pastillas del mismo tipo produce 3 filas. El documento que lee un humano
    dice "3 pastillas" en un renglón, así que las líneas se agrupan por
    Referencia y precio acá, del lado que tiene el JOIN.
    """
    bill = crud.get(db, tenant_id, bill_id)
    if bill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")

    customer = db.execute(
        select(Customer).where(
            Customer.id == bill.customer_id, Customer.tenant_id == tenant_id
        )
    ).scalar_one_or_none()
    if customer is None:
        #  Datos inconsistentes: la FK existe pero el cliente no. Es un 500
        #  honesto, no un 404 — la factura sí está, lo que falta es el maestro.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"La factura {bill.bill_number} apunta a un cliente inexistente",
        )

    #  `unit_price` e `iva_percentage` entran en la clave de agrupación: la
    #  misma Referencia cobrada con descuento en una línea y sin descuento en
    #  otra son dos renglones distintos. Agruparlas daría un precio unitario
    #  promedio que no fue el que se cobró en ninguna de las dos.
    rows = db.execute(
        select(
            Reference.id,
            Reference.sku,
            Reference.title,
            Reference.image_url,
            BillItem.unit_price,
            BillItem.iva_percentage,
            func.sum(BillItem.quantity),
            func.sum(BillItem.iva_amount),
            func.sum(BillItem.total),
        )
        .select_from(BillItem)
        .join(Item, Item.id == BillItem.item_id)
        .join(Reference, Reference.id == Item.reference_id)
        .where(BillItem.tenant_id == tenant_id, BillItem.bill_id == bill.id)
        .group_by(
            Reference.id,
            Reference.sku,
            Reference.title,
            Reference.image_url,
            BillItem.unit_price,
            BillItem.iva_percentage,
        )
        #  Orden estable por SKU: sin `ORDER BY`, el mismo documento puede
        #  salir con los renglones en otro orden en cada carga.
        .order_by(Reference.sku, BillItem.unit_price)
    ).all()

    return {
        "id": bill.id,
        "bill_number": bill.bill_number,
        "customer": customer,
        "subtotal": bill.subtotal,
        "total_iva": bill.total_iva,
        "total": bill.total,
        "fiscal_status": bill.fiscal_status,
        "voided_at": bill.voided_at,
        "void_reason": bill.void_reason,
        "created_at": bill.created_at,
        "lines": [
            {
                "reference_id": reference_id,
                "sku": sku,
                "title": title,
                "image_url": resolve_image(sku, image_url),
                "quantity": quantity,
                "unit_price": unit_price,
                "iva_percentage": iva_percentage,
                "iva_amount": iva_amount,
                "total": line_total,
            }
            for (
                reference_id,
                sku,
                title,
                image_url,
                unit_price,
                iva_percentage,
                quantity,
                iva_amount,
                line_total,
            ) in rows
        ],
        #  Sin integración DIAN (D-09/D-38) no existe representación gráfica
        #  firmada que enlazar. Ver `BillDetailRead.pdf_url`.
        "pdf_url": None,
    }


@router.get("/{bill_id}/pdf")
def download_bill_pdf(
    bill_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    El PDF de **una** factura, suelto y sin zip.

    Reusa el mismo `render_invoice_pdf` del paquete (D-78), no una segunda
    implementación: el documento que se baja de una fila y el que viene dentro
    del .zip tienen que ser el mismo papel, o el día que uno cambie el otro
    quedaría contando otra cosa.

    Vale lo mismo que ahí: **no es la factura electrónica de la DIAN**, es la
    reconstrucción desde los registros, y lo lleva impreso (D-61/D-78). El
    nombre del archivo marca las anuladas igual que en el paquete (D-60).
    """
    conditions = [Bill.tenant_id == tenant_id, Bill.id == bill_id]
    facturas = billing_export.fetch_bills(db, tenant_id, conditions)
    if not facturas:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")

    factura = facturas[0]
    tenant = db.execute(select(Tenant).where(Tenant.id == tenant_id)).scalar_one_or_none()
    content = billing_export.render_invoice_pdf(
        factura, tenant.business_name if tenant else "Negocio"
    )
    filename = billing_export.invoice_filename(
        factura["bill_number"], voided=factura["voided_at"] is not None
    )

    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.post("/{bill_id}/void", response_model=BillDetailRead)
def void_bill(
    bill_id: uuid.UUID,
    payload: BillVoid,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Anula una factura y **devuelve su mercancía al inventario** (D-60).

    Anular es marcar, no borrar: el consecutivo y las líneas quedan. Un
    documento numerado que desaparece deja un hueco en la serie que después no
    se puede explicar — y `_next_bill_number` se calcula del máximo existente,
    así que borrarlo tampoco liberaría el número.

    Las dos mitades —marca y reversa de inventario— van en la misma
    transacción: una factura anulada cuya mercancía siguió figurando como
    vendida deja stock invisible, y unidades devueltas sobre una factura que
    quedó vigente cobran dos veces lo mismo.

    La reversa alcanza a **todas** las unidades de la factura, sin mirar en qué
    estado están hoy: anular es dejarlas como si la venta no hubiera ocurrido, y
    qué hacer con ellas después es decisión del usuario (ver el bucle).

    Zona de alto riesgo (CLAUDE.md): toca dinero e inventario a la vez.
    """
    bill = crud.get(db, tenant_id, bill_id)
    if bill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")

    if bill.voided_at is not None:
        #  Reintento o doble clic. Sin este corte, la segunda anulación
        #  devolvería las unidades **otra vez** al inventario y crearía stock
        #  de la nada.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"La factura {bill.bill_number} ya estaba anulada",
        )

    if bill.fiscal_status == FiscalStatus.AUTORIZADA.value:
        #  Una factura ya autorizada por la DIAN no se anula por dentro: se
        #  corrige con una **nota crédito** ante la DIAN. Permitirlo acá
        #  dejaría el libro local diciendo una cosa y la DIAN otra, que es
        #  exactamente el descuadre que nadie puede arreglar después.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"La factura {bill.bill_number} está autorizada por la DIAN: "
                "no se anula, se corrige con una nota crédito"
            ),
        )

    #  `with_for_update`: entre leer las unidades y devolverlas, otra caja
    #  podría estar cobrándolas. El bloqueo las congela hasta el commit.
    units = list(
        db.execute(
            select(Item)
            .join(BillItem, BillItem.item_id == Item.id)
            .where(
                BillItem.bill_id == bill.id,
                BillItem.tenant_id == tenant_id,
                Item.tenant_id == tenant_id,
            )
            .with_for_update(of=Item)
        ).scalars()
    )

    for unit in units:
        #  Vuelven **todas** las unidades de la factura, sea cual sea su estado
        #  actual — no solo las que siguen en `sold`.
        #
        #  El criterio es cuál de los dos errores posibles se puede corregir.
        #  Devolver de más deja una unidad disponible que quizá ya no existe:
        #  se ve en pantalla y se da de baja en un clic. **No** devolverla es
        #  silencioso — la anulación no dice que dejó una unidad afuera, y el
        #  inventario queda corto sin que nadie pueda notarlo. Entre un error
        #  visible y reversible y uno invisible, se elige el primero.
        #
        #  Además, una unidad marcada de baja **después** de venderse ya está
        #  en un estado incoherente (si se vendió, dejó de ser del negocio),
        #  así que no es un dato en el que valga la pena basar la decisión.
        #  Anular es deshacer la venta: la unidad queda como si nunca hubiera
        #  salido, y qué hacer con ella después lo decide el usuario.
        unit.status = "available"

    bill.voided_at = datetime.now(timezone.utc)
    bill.void_reason = payload.reason.strip()

    db.commit()

    return get_bill_detail(bill_id=bill.id, db=db, tenant_id=tenant_id)
