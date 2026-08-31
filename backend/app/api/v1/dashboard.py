import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import ImageResolver, get_db, get_image_resolver, get_tenant_id
from app.models.bill import Bill
from app.models.bill_item import BillItem
from app.models.item import Item
from app.models.reference import Reference
from app.schemas.dashboard import (
    BucketGranularity,
    DashboardSummaryRead,
    FlowPoint,
    RestockRead,
    SalesPoint,
    TopProductRead,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

#  Hora local del negocio. Colombia es UTC-5 fijo (sin horario de verano), así
#  que un offset constante es exacto y no depende de que el contenedor traiga
#  la base de datos de zonas horarias. El nombre IANA se usa solo del lado SQL,
#  donde sí está garantizado (Postgres trae su propia tz database).
BUSINESS_TZ = timezone(timedelta(hours=-5))
BUSINESS_TZ_NAME = "America/Bogota"

#  Una Referencia entra a "sin rotación" si su existencia más vieja lleva más
#  de esto en bodega y en ese mismo lapso no vendió una sola unidad. Los dos
#  lados hacen falta: sin el de antigüedad, un producto que entró ayer contaría
#  como estancado solo por no haberse vendido todavía.
STALE_DAYS = 90

TOP_PRODUCTS_LIMIT = 8
RESTOCK_LIMIT = 8

#  Rango por defecto cuando el cliente no manda fechas: los últimos 30 días.
#  Es el que traía el selector viejo, y sigue siendo el que responde "cómo
#  vengo" sin que el usuario tenga que elegir nada al entrar.
DEFAULT_RANGE_DAYS = 30

#  Techo del rango consultable (D-69). El datepicker deja elegir cualquier par
#  de fechas, incluidos rangos de años; sin tope, una consulta de 2020 a hoy
#  barre toda la tabla de facturas para dibujar cientos de barras que nadie
#  lee. Al pasarse, el servidor **recorta el extremo viejo** y devuelve el
#  rango efectivo en `period_from`, para que la UI muestre lo que se midió.
MAX_RANGE_DAYS = 366

#  Umbral de días a partir del cual se agrupa por semana en vez de por día.
#  ~2 meses de barras diarias es lo último que entra legible en media pantalla;
#  más allá, las barras quedan más finas que su propia separación.
DAILY_MAX_DAYS = 62


def _resolve_range(date_from: date | None, date_to: date | None) -> tuple[date, date]:
    """
    Normaliza el par de fechas que llegó por query a un rango cerrado y sano.

    Rellena los extremos que falten, rechaza el rango invertido y aplica el
    tope de `MAX_RANGE_DAYS`. Trabaja en `date` puro —sin hora ni zona— porque
    eso es lo que el usuario eligió en el calendario; la conversión a instantes
    con zona es cosa de `_range_bounds`.
    """
    today = datetime.now(BUSINESS_TZ).date()
    end = date_to or today
    start = date_from or end - timedelta(days=DEFAULT_RANGE_DAYS - 1)

    if start > end:
        #  422 y no un swap silencioso: si las fechas llegan invertidas es un
        #  bug del cliente, y corregirlo por dentro lo esconde.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="La fecha inicial no puede ser posterior a la final.",
        )

    if (end - start).days + 1 > MAX_RANGE_DAYS:
        start = end - timedelta(days=MAX_RANGE_DAYS - 1)
    return start, end


def _range_bounds(start: date, end: date) -> tuple[datetime, datetime]:
    """
    Convierte el rango de fechas a instantes con zona, anclados a los límites
    del **día local**.

    El extremo derecho se recorta a "ahora" cuando el rango llega a hoy o más
    allá: sin eso, elegir un rango que termina la semana entrante dibujaría
    barras vacías de días que todavía no ocurrieron, que se leen como una caída
    de ventas.
    """
    now = datetime.now(BUSINESS_TZ)
    first = datetime.combine(start, time.min, tzinfo=BUSINESS_TZ)
    last = min(datetime.combine(end, time.max, tzinfo=BUSINESS_TZ), now)
    #  Rango enteramente en el futuro: no hay nada que medir, pero tampoco es
    #  un error. Se colapsa a un solo bucket que vendrá en cero.
    return first, max(last, first)


def _granularity(start: datetime, end: datetime) -> BucketGranularity:
    """Un día se lee por horas; hasta ~2 meses, por día; de ahí en adelante, por semana."""
    span_days = (end.date() - start.date()).days + 1
    if span_days <= 1:
        return BucketGranularity.HOUR
    if span_days <= DAILY_MAX_DAYS:
        return BucketGranularity.DAY
    return BucketGranularity.WEEK


def _bucket_step(granularity: BucketGranularity) -> timedelta:
    return {
        BucketGranularity.HOUR: timedelta(hours=1),
        BucketGranularity.DAY: timedelta(days=1),
        BucketGranularity.WEEK: timedelta(weeks=1),
    }[granularity]


def _truncated(moment: datetime, granularity: BucketGranularity) -> datetime:
    """
    Baja un instante al inicio de su bucket, para que case con lo que devuelve
    `date_trunc` del lado SQL.

    La semana **tiene que empezar en lunes**: es donde la pone `date_trunc
    ('week', …)` de Postgres. Si la grilla de Python arrancara en otro día, las
    claves no cruzarían con las de SQL y toda la serie volvería en cero — un
    fallo silencioso, porque el relleno de huecos taparía cada bucket faltante.
    """
    if granularity is BucketGranularity.HOUR:
        return moment.replace(minute=0, second=0, microsecond=0)
    midnight = moment.replace(hour=0, minute=0, second=0, microsecond=0)
    if granularity is BucketGranularity.WEEK:
        return midnight - timedelta(days=midnight.weekday())
    return midnight


def _sales_series(
    db: Session,
    tenant_id: uuid.UUID,
    first_bucket: datetime,
    buckets: int,
    granularity: BucketGranularity,
) -> list[SalesPoint]:
    """
    Serie de ventas de `buckets` intervalos a partir de `first_bucket`, **con
    los huecos rellenos en cero**.

    Recibe un conteo de buckets y no un rango de fechas porque el extremo
    derecho del rango se recorta a "ahora" (ver `_range_bounds`): derivar la
    cantidad de puntos de un instante a media hora del día metía un bucket de
    más o de menos según el momento en que se abriera el tablero.

    Sin el relleno, una hora sin ventas simplemente no vuelve de SQL y el eje
    saltaría de las 10am a la 1pm como si fueran contiguas — dibujando una
    mañana ocupada donde hubo tres horas muertas.

    El bucket se calcula sobre la hora **local** (`timezone(...)` convierte el
    `timestamptz` a naive local antes de truncar): con UTC, todo lo vendido
    después de las 7pm caería en el día siguiente.
    """
    step = _bucket_step(granularity)
    last_bucket = first_bucket + step * (buckets - 1)
    local_created = func.timezone(BUSINESS_TZ_NAME, Bill.created_at)
    bucket = func.date_trunc(granularity.value, local_created).label("bucket")

    rows = db.execute(
        select(bucket, func.coalesce(func.sum(Bill.total), 0))
        .where(
            Bill.tenant_id == tenant_id,
            #  Una factura anulada no es una venta (D-60): misma exclusión que
            #  usa `bills_summary` para las cifras de dinero.
            Bill.voided_at.is_(None),
            Bill.created_at >= first_bucket,
            #  El bucket final va completo: `last_bucket` es su inicio.
            Bill.created_at < last_bucket + step,
        )
        .group_by(bucket)
    ).all()

    #  Las claves que devuelve `date_trunc` son naive (ya convertidas a local),
    #  así que la grilla se recorre en naive para que casen.
    totals = {row[0]: row[1] for row in rows}
    cursor = first_bucket.replace(tzinfo=None)
    series: list[SalesPoint] = []
    for _ in range(buckets):
        series.append(SalesPoint(bucket=cursor, total=Decimal(totals.get(cursor, 0))))
        cursor += step
    return series


def _flow_series(
    db: Session,
    tenant_id: uuid.UUID,
    first_bucket: datetime,
    buckets: int,
    granularity: BucketGranularity,
) -> list[FlowPoint]:
    """
    "Entra vs. sale" por bucket: unidades ingresadas a bodega contra vendidas.

    Son dos consultas y no un JOIN porque cuelgan de tablas distintas y de
    **fechas distintas** — la venta se fecha por `Bill.created_at` y el ingreso
    por `Item.created_at`. Cruzarlas en SQL multiplicaría filas (el mismo
    producto cartesiano que ya apareció en el resumen de Facturación).

    El ingreso cuenta **todas** las unidades creadas en el bucket, sin mirar su
    estado actual: una unidad que entró y ya se vendió igual entró ese día, y
    excluirla haría que el histórico cambiara con el paso del tiempo.
    """
    step = _bucket_step(granularity)
    last_bucket = first_bucket + step * (buckets - 1)
    window_end = last_bucket + step

    sold_bucket = func.date_trunc(
        granularity.value, func.timezone(BUSINESS_TZ_NAME, Bill.created_at)
    ).label("bucket")
    sold_rows = db.execute(
        select(sold_bucket, func.coalesce(func.sum(BillItem.quantity), 0))
        .select_from(BillItem)
        .join(Bill, Bill.id == BillItem.bill_id)
        .where(
            Bill.tenant_id == tenant_id,
            Bill.voided_at.is_(None),
            Bill.created_at >= first_bucket,
            Bill.created_at < window_end,
        )
        .group_by(sold_bucket)
    ).all()

    added_bucket = func.date_trunc(
        granularity.value, func.timezone(BUSINESS_TZ_NAME, Item.created_at)
    ).label("bucket")
    added_rows = db.execute(
        select(added_bucket, func.count(Item.id))
        .where(
            Item.tenant_id == tenant_id,
            Item.created_at >= first_bucket,
            Item.created_at < window_end,
        )
        .group_by(added_bucket)
    ).all()

    sold_by_bucket = {row[0]: row[1] for row in sold_rows}
    added_by_bucket = {row[0]: row[1] for row in added_rows}

    cursor = first_bucket.replace(tzinfo=None)
    series: list[FlowPoint] = []
    for _ in range(buckets):
        series.append(
            FlowPoint(
                bucket=cursor,
                sold=Decimal(sold_by_bucket.get(cursor, 0)),
                added=int(added_by_bucket.get(cursor, 0)),
            )
        )
        cursor += step
    return series


@router.get("/summary", response_model=DashboardSummaryRead)
def dashboard_summary(
    date_from: date | None = Query(
        None,
        alias="from",
        description="Primer día del rango (YYYY-MM-DD). Por defecto, 29 días antes de `to`.",
    ),
    date_to: date | None = Query(
        None,
        alias="to",
        description="Último día del rango (YYYY-MM-DD), inclusive. Por defecto, hoy.",
    ),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    resolve_image: ImageResolver = Depends(get_image_resolver),
):
    """
    Tablero operativo de producto (D-66), sobre un **rango de fechas libre**
    (D-69).

    **No es un roll-up financiero:** no devuelve margen ni utilidad — esas viven
    en Facturación. Lo que responde es el cruce que ninguna otra pantalla puede
    hacer sola: qué se está vendiendo contra qué queda en el estante.

    Los dos extremos son opcionales e **inclusivos**: `to` cuenta el día
    completo. La granularidad del eje no se pide, se deriva del largo del rango
    y vuelve en `granularity`.

    Todo sale del esquema actual, sin migraciones: la demanda por
    `BillItem → Item → Reference`, el stock por `count(Item WHERE
    status='available')` y el eje temporal por `Bill.created_at`.
    """
    range_start, range_end = _resolve_range(date_from, date_to)
    start, end = _range_bounds(range_start, range_end)
    granularity = _granularity(start, end)
    step = _bucket_step(granularity)

    #  Días efectivamente medidos. Es el divisor de la velocidad de venta en
    #  "Reponer ya": con rango libre ya no puede salir de una tabla de
    #  constantes como antes.
    period_days = (end.date() - start.date()).days + 1

    first_bucket = _truncated(start, granularity)
    buckets = int((_truncated(end, granularity) - first_bucket) / step) + 1

    sales_series = _sales_series(db, tenant_id, first_bucket, buckets, granularity)
    flow_series = _flow_series(db, tenant_id, first_bucket, buckets, granularity)

    total_billed = sum((point.total for point in sales_series), Decimal(0))

    #  Demanda del período, agregada por Referencia. `BillItem` guarda una fila
    #  por unidad física vendida; acá interesa el producto, no la unidad.
    sold = (
        select(
            Item.reference_id.label("reference_id"),
            func.sum(BillItem.quantity).label("units_sold"),
            func.sum(BillItem.total).label("revenue"),
        )
        .select_from(BillItem)
        .join(Bill, Bill.id == BillItem.bill_id)
        .join(Item, Item.id == BillItem.item_id)
        .where(
            Bill.tenant_id == tenant_id,
            Bill.voided_at.is_(None),
            Bill.created_at >= start,
            Bill.created_at <= end,
        )
        .group_by(Item.reference_id)
        .subquery()
    )

    #  Stock vendible AHORA. Es una foto y no depende del período (D-66): el
    #  selector mueve la demanda, no las existencias.
    available = (
        select(
            Item.reference_id.label("reference_id"),
            func.count(Item.id).label("available_units"),
        )
        .where(Item.tenant_id == tenant_id, Item.status == "available")
        .group_by(Item.reference_id)
        .subquery()
    )

    units_sold, distinct_sold = db.execute(
        select(
            func.coalesce(func.sum(sold.c.units_sold), 0),
            func.count(sold.c.reference_id),
        )
    ).one()

    #  Cruce demanda × stock: todo lo que se vendió en el período, con lo que
    #  queda al lado. Un LEFT JOIN y no INNER — una Referencia agotada no tiene
    #  fila en `available`, y es precisamente la que hay que mostrar.
    demand_rows = db.execute(
        select(
            Reference.id,
            Reference.sku,
            Reference.title,
            Reference.image_url,
            sold.c.units_sold,
            sold.c.revenue,
            func.coalesce(available.c.available_units, 0),
        )
        .select_from(sold)
        .join(Reference, Reference.id == sold.c.reference_id)
        .outerjoin(available, available.c.reference_id == sold.c.reference_id)
    ).all()

    top_products = [
        TopProductRead(
            reference_id=row[0],
            sku=row[1],
            title=row[2],
            image_url=resolve_image(row[1], row[3]),
            units=row[4],
            revenue=row[5],
        )
        for row in sorted(demand_rows, key=lambda row: row[4], reverse=True)[:TOP_PRODUCTS_LIMIT]
    ]

    #  "Reponer ya". La cobertura se calcula en Python y no en SQL para no
    #  tener que blindar la división por cero; el conjunto son las Referencias
    #  vendidas en el período, no el catálogo.
    #
    #  **Sin filtro por umbral, a propósito.** Filtrar a "menos de N días de
    #  cobertura" deja la lista vacía cada vez que el inventario está sano, y
    #  una card que casi siempre aparece vacía enseña al usuario a no mirarla —
    #  justo la que más queremos que mire. En vez de eso se muestran siempre
    #  las que se acaban primero y el **tono** dice si hay que actuar:
    #  `days_of_cover` viaja para que la UI pinte agotado / crítico / sano.
    restock: list[RestockRead] = []
    for reference_id, sku, title, image_url, sold_units, _revenue, stock in demand_rows:
        velocity = Decimal(sold_units) / Decimal(period_days)
        #  Agotado: no hay cobertura que calcular, y va de primero. Es distinto
        #  de "cobertura 0.0 días", que sería alcanzar justo para hoy.
        cover = None if stock == 0 else float(Decimal(stock) / velocity)
        restock.append(
            RestockRead(
                reference_id=reference_id,
                sku=sku,
                title=title,
                image_url=resolve_image(sku, image_url),
                available_units=stock,
                units_sold=sold_units,
                days_of_cover=cover,
            )
        )
    #  Agotados primero (cobertura `None`), después por cobertura ascendente:
    #  lo que se acaba antes, arriba.
    restock.sort(key=lambda row: (row.days_of_cover is not None, row.days_of_cover or 0))
    #  Se cuenta sobre TODA la demanda, no sobre la lista ya recortada: el tile
    #  dice cuántos agotados hay, no cuántos alcanzaron a caber en la card.
    out_of_stock_with_demand = sum(1 for row in restock if row.available_units == 0)
    restock = restock[:RESTOCK_LIMIT]

    #  Sin rotación: existencias viejas que además no vendieron nada en el
    #  mismo lapso. Ventana propia (STALE_DAYS), independiente del selector —
    #  "lleva 3 meses quieto" no cambia porque el usuario mire el tablero en
    #  modo "hoy".
    stale_cutoff = datetime.now(timezone.utc) - timedelta(days=STALE_DAYS)
    aged = (
        select(Item.reference_id)
        .where(Item.tenant_id == tenant_id, Item.status == "available")
        .group_by(Item.reference_id)
        .having(func.min(Item.created_at) < stale_cutoff)
        .subquery()
    )
    recently_sold = (
        select(Item.reference_id)
        .select_from(BillItem)
        .join(Bill, Bill.id == BillItem.bill_id)
        .join(Item, Item.id == BillItem.item_id)
        .where(
            Bill.tenant_id == tenant_id,
            Bill.voided_at.is_(None),
            Bill.created_at >= stale_cutoff,
        )
        .subquery()
    )
    stale_references = db.execute(
        select(func.count())
        .select_from(aged)
        .where(aged.c.reference_id.not_in(select(recently_sold.c.reference_id)))
    ).scalar_one()

    return DashboardSummaryRead(
        period_from=start,
        period_to=end,
        granularity=granularity,
        total_billed=total_billed,
        sales_series=sales_series,
        flow_series=flow_series,
        units_sold=units_sold,
        distinct_references_sold=distinct_sold,
        out_of_stock_with_demand=out_of_stock_with_demand,
        stale_references=stale_references,
        top_products=top_products,
        restock=restock,
    )
