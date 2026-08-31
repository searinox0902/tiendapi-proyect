import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class BucketGranularity(str, Enum):
    """
    Ancho de cada bucket del eje de tiempo.

    **No lo elige el usuario: lo deriva el servidor** del largo del rango
    (D-69). Con rango libre, dejarlo a criterio del cliente permitiría pedir
    365 buckets de una hora — 8.760 barras que ni se dibujan ni se leen. El
    valor viaja en la respuesta porque el frontend necesita saber si rotula
    horas, días o semanas.
    """

    HOUR = "hour"
    DAY = "day"
    WEEK = "week"


class SalesPoint(BaseModel):
    """
    Un punto del gráfico de ventas.

    `bucket` viene en hora local del negocio (no UTC): es el eje que el usuario
    lee, y una venta de las 7pm no puede aparecer al día siguiente.
    """

    bucket: datetime
    total: Decimal


class FlowPoint(BaseModel):
    """
    Un punto de "entra vs. sale": unidades que ingresaron a bodega contra
    unidades que se vendieron, en el mismo bucket.

    Las dos caras van en el mismo punto a propósito — la pregunta que responde
    el gráfico es si se está **comprando más de lo que se vende**, y eso solo
    se ve comparándolas sobre el mismo eje de tiempo.
    """

    bucket: datetime
    #  Decimal: `BillItem.quantity` es Numeric(12,3), no un entero.
    sold: Decimal
    #  Conteo de filas de `Item`: cada una es una unidad física (D-41), igual
    #  que cuenta el resto de la app.
    added: int


class TopProductRead(BaseModel):
    """Fila de "Top productos vendidos" — agregada por Referencia, no por unidad física."""

    reference_id: uuid.UUID
    sku: str
    title: str
    image_url: Optional[str] = None
    units: Decimal
    revenue: Decimal


class RestockRead(BaseModel):
    """
    Fila de "Reponer ya" (D-66): el cruce demanda × stock.

    La UI muestra el **par crudo** (`available_units` / `units_sold`), no
    `days_of_cover` — el ratio solo existe para ordenar. Ver D-66: un par de
    números concretos no necesita explicación, un índice de cobertura sí.
    """

    reference_id: uuid.UUID
    sku: str
    title: str
    image_url: Optional[str] = None
    available_units: int
    units_sold: Decimal
    #  `None` cuando no hay nada que cubrir (agotado): distinto de 0.0, que
    #  sería "se acaba hoy". Se manda para que la UI decida el tono de alarma.
    days_of_cover: Optional[float] = None


class DashboardSummaryRead(BaseModel):
    """
    Todo el Dashboard en una sola respuesta (D-66).

    Un endpoint y no cinco: las cuatro secciones comparten el mismo período y
    las mismas exclusiones (facturas anuladas), así que separarlas invitaría a
    que una quedara filtrando distinto que las otras — el mismo criterio por el
    que `bills_summary` comparte `_bill_conditions` con el listado.
    """

    #  Rango efectivamente consultado, ya normalizado a los límites del día
    #  local. Vuelve al cliente porque el servidor puede recortarlo (ver
    #  MAX_RANGE_DAYS) y la UI tiene que reflejar lo que realmente se midió,
    #  no lo que se pidió.
    period_from: datetime
    period_to: datetime
    granularity: BucketGranularity

    #  Única cifra que el Dashboard comparte con otro módulo (D-66), y va como
    #  titular del gráfico, no como card propia.
    total_billed: Decimal
    sales_series: list[SalesPoint]

    #  "Entra vs. sale": misma grilla de buckets que `sales_series`.
    flow_series: list[FlowPoint]

    units_sold: Decimal
    distinct_references_sold: int
    out_of_stock_with_demand: int
    stale_references: int

    top_products: list[TopProductRead]
    restock: list[RestockRead]
