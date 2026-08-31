import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class FiscalStatus(str, Enum):
    """
    Estado fiscal DIAN de la factura (D-48).

    La ausencia de valor (`None` en la columna) **no** es uno de estos:
    significa que la factura todavía no entró a ningún trámite fiscal. Se
    modela como `NULL` y no como un quinto miembro para que no se pueda
    confundir con 'pendiente', que sí afirma que está en cola.
    """

    CONTINGENCIA = "contingencia"
    PENDIENTE = "pendiente"
    AUTORIZADA = "autorizada"
    RECHAZADA = "rechazada"


class BillItemCreate(BaseModel):
    item_id: uuid.UUID
    quantity: Decimal
    unit_price: Decimal
    iva_percentage: Decimal
    iva_amount: Decimal
    total: Decimal


class BillItemRead(BillItemCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    bill_id: uuid.UUID
    hmac: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    version: int


class BillCreate(BaseModel):
    customer_id: uuid.UUID
    bill_number: str
    subtotal: Decimal
    total_iva: Decimal
    total: Decimal
    items: list[BillItemCreate]


class CheckoutLine(BaseModel):
    """
    Una línea del carrito de la caja, tal como la conoce el cliente.

    Habla de **Referencia y cantidad**, no de unidades físicas: el cajero
    vende "3 pastillas de freno", no las unidades `a1b2`, `c3d4` y `e5f6`.
    Resolver cuáles son esas unidades es trabajo del servidor (ver
    `checkout`), que además es el único que puede hacerlo sin condiciones de
    carrera.
    """

    reference_id: uuid.UUID
    quantity: int = Field(gt=0)
    #  Precio efectivamente cobrado por unidad, con IVA y descuento ya
    #  aplicados. Es un dato de negocio real (el cajero puede rebajar), así que
    #  el servidor lo acepta — pero **no** acepta el desglose base/IVA: eso lo
    #  deriva él (D-45), que es lo que garantiza que `subtotal + IVA = total`.
    unit_price: Decimal = Field(gt=0)


class CheckoutNewCustomer(BaseModel):
    """Cliente a registrar en el mismo acto del cobro, si no existía."""

    nit: Optional[str] = None
    fullname: str = Field(min_length=1)


class CheckoutCreate(BaseModel):
    """
    Cobro de la caja registradora.

    O viene `customer_id` (cliente ya existente) o `new_customer` (se registra
    en la misma transacción). Nunca los dos ni ninguno — lo valida el router.
    """

    customer_id: Optional[uuid.UUID] = None
    new_customer: Optional[CheckoutNewCustomer] = None
    lines: list[CheckoutLine] = Field(min_length=1)


class BillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    customer_id: uuid.UUID
    bill_number: str
    subtotal: Decimal
    total_iva: Decimal
    total: Decimal
    fiscal_status: Optional[FiscalStatus] = None
    voided_at: Optional[datetime] = None
    void_reason: Optional[str] = None
    hmac: Optional[str] = None
    prev_hash: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    version: int
    items: list[BillItemRead] = []


class BillVoid(BaseModel):
    """
    Anulación de una factura (D-60).

    El motivo es obligatorio: un mes después, "anulada" a secas no permite
    distinguir un error de digitación de una devolución del cliente, y son
    cosas distintas para el inventario y para la contabilidad.
    """

    reason: str = Field(min_length=3, max_length=500)


class BillDetailLine(BaseModel):
    """
    Una línea del detalle, tal como se lee en pantalla: **por Referencia**, no
    por unidad física.

    El checkout guarda un `BillItem` por cada unidad vendida (`quantity=1`),
    porque cada unidad es una existencia distinta que hay que descontar. Pero
    "3 pastillas de freno" es una sola línea de la factura: mostrarla tres
    veces sería fiel a la base y falso para quien lee el documento. La
    agrupación se hace en el servidor, que es donde está el JOIN a `Reference`.
    """

    reference_id: uuid.UUID
    sku: str
    title: str
    image_url: Optional[str] = None
    quantity: Decimal
    #  Precio cobrado por unidad, con IVA. Es parte de la clave de agrupación:
    #  la misma Referencia vendida con descuento en una línea y sin descuento
    #  en otra son dos renglones distintos, no uno promediado.
    unit_price: Decimal
    iva_percentage: Decimal
    iva_amount: Decimal
    total: Decimal


class BillCustomerRead(BaseModel):
    """Cliente embebido en el detalle: evita una segunda petición para pintar la cabecera."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    fullname: str
    nit: Optional[str] = None


class BillDetailRead(BaseModel):
    """
    Factura completa para la pantalla de detalle.

    No reusa `BillRead` porque esa devuelve `BillItem` crudos: `item_id` sin
    SKU ni nombre, y una fila por unidad física. Acá viaja lo que el documento
    muestra — cliente resuelto y líneas agrupadas por Referencia.
    """

    id: uuid.UUID
    bill_number: str
    customer: BillCustomerRead
    subtotal: Decimal
    total_iva: Decimal
    total: Decimal
    fiscal_status: Optional[FiscalStatus] = None
    voided_at: Optional[datetime] = None
    void_reason: Optional[str] = None
    created_at: datetime
    lines: list[BillDetailLine] = []
    #  Enlace a la **representación gráfica firmada** que emite el proveedor de
    #  facturación electrónica (docs/05, §3.6; docs/02, §9.7 — `FiscalRecord`).
    #  Hoy siempre `None`: la integración DIAN está diferida (D-09/D-38), así
    #  que no existe ningún PDF con validez fiscal que enlazar. La pantalla
    #  reconstruye el documento desde estos datos mientras tanto (D-61) y pasa
    #  a mostrar el archivo el día que este campo traiga una URL.
    pdf_url: Optional[str] = None


class BillListRead(BaseModel):
    """
    Fila de la tabla de Facturación.

    No reusa `BillRead` a propósito: esa arrastra todas las líneas
    (`items`) de cada factura, y una página de 20 facturas se convertiría en
    cientos de objetos que la tabla no pinta. Acá viaja lo que la fila muestra
    — más `customer_name`, que vive en `Customer` y evita que el cliente tenga
    que resolver N nombres con N peticiones.
    """

    id: uuid.UUID
    bill_number: str
    customer_id: uuid.UUID
    customer_name: str
    subtotal: Decimal
    total_iva: Decimal
    total: Decimal
    fiscal_status: Optional[FiscalStatus] = None
    #  Anulada (D-60). Viaja en la fila porque una factura anulada que se ve
    #  igual que una vigente hace creer que ese dinero entró.
    voided_at: Optional[datetime] = None
    #  Cuántas líneas tiene la factura. Es el "tamaño" de la venta de un vistazo.
    items_count: int
    created_at: datetime


class BillSummaryRead(BaseModel):
    """
    Cifras de cabecera de Facturación — fórmulas fijadas por D-49, para que no
    se calculen distinto en cada pantalla.

    **Respetan los filtros activos**: describen lo que se está mirando, no el
    histórico completo. Se calculan en el servidor sobre todas las filas que
    pasan el filtro, no sobre la página cargada.
    """

    #  Las tres cifras de dinero **excluyen las facturas anuladas** (D-60):
    #  una venta que se deshizo y devolvió su mercancía al inventario no es
    #  dinero facturado, ni IVA que se le deba a la DIAN, ni utilidad.
    #  Σ `Bill.total` (con IVA) — D-49.
    total_billed: Decimal
    #  Σ `Bill.total_iva` — D-49.
    total_iva: Decimal
    #  Σ (`BillItem.unit_price` − costo) × qty — D-49. El costo sale de
    #  `COALESCE(Item.provider_price, Reference.provider_price)`.
    total_profit: Decimal
    #  Unidades vendidas sin costo de proveedor cargado: `total_profit` está
    #  incompleta si es > 0, y sin decirlo se leería como completa.
    units_without_cost: int
    #  Cuenta **todas** las facturas que pasan el filtro, incluidas las
    #  anuladas: son documentos que existen y su consecutivo se emitió. El
    #  dinero es lo que se descuenta, no el papel.
    total_bills: int
    #  Cuántas de esas están anuladas (D-60) — sin esto, `total_bills` y las
    #  cifras de dinero parecerían no cuadrar entre sí.
    voided_bills: int
    #
    #  El desglose fiscal (`declared`/`undeclared`/`rejected`/`without_status`)
    #  se retiró en D-81. No es que estorbara: es que con la integración DIAN
    #  diferida (D-09/D-38) `fiscal_status` vale `NULL` en **todas** las
    #  facturas, así que tres de los cuatro contadores eran siempre 0 y el
    #  cuarto era siempre igual a `total_bills`. Cuatro cifras que no varían no
    #  informan, y "sin declarar: 29" se lee como un incumplimiento tributario
    #  cuando lo que pasa es que el subsistema todavía no existe.
    #
    #  `Bill.fiscal_status` sigue en base intacta (D-48/D-59) y los endpoints
    #  siguen aceptando el filtro: esto es un cambio de qué se muestra, no de
    #  qué se guarda, y se revierte sin migración el día que la DIAN entre.
