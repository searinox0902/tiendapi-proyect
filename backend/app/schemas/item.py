import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ItemStatus(str, Enum):
    """
    Ciclo de vida de la unidad física — docs/03-modelo-datos.md §1.3 (D-41).

    Valores en inglés desde la migración `0012` (D-63); antes eran
    `disponible|vendido|reservado|de_baja`. `WRITTEN_OFF` es la baja manual
    (dañada, extraviada): un descarte de la unidad, no una desactivación
    temporal — de ahí el término contable y no `inactive`.
    """

    AVAILABLE = "available"
    SOLD = "sold"
    RESERVED = "reserved"
    WRITTEN_OFF = "written_off"


class ItemBase(BaseModel):
    reference_id: uuid.UUID
    #  Opcionales (migración 0005): el alta manual rápida no exige elegir
    #  proveedor ni ubicación en el momento — se completan después.
    provider_id: Optional[uuid.UUID] = None
    location_id: Optional[uuid.UUID] = None
    quantity: Decimal = Decimal("0")
    current_price: Decimal


class ItemCreate(ItemBase):
    #  `status`, `iva_percentage` y `provider_price` NO se exponen acá a
    #  propósito: toda existencia nueva nace 'available' y sin overrides —
    #  hereda el IVA/costo vigentes de catálogo (migración 0007) hasta que
    #  alguien la edite con `PATCH /items/{id}`.
    pass


class ItemUpdate(BaseModel):
    """
    Actualización parcial (`PATCH /items/{id}`). Solo se tocan los campos que
    vienen en el body (`exclude_unset` en el router) — omitir un campo lo deja
    intacto; mandarlo en `null` sí lo borra. Distinción real, no cosmética: es
    lo que permite reasignar ubicación en lote sin arrastrar el proveedor de
    cada fila al mismo valor por accidente.

    `iva_percentage`/`provider_price`/`base_price` en `null` **restablece al
    catálogo**: el endpoint hace `COALESCE(Item.x, Reference.x)` al leer, así
    que borrar el override no dice "cero", dice "volvé a seguir la Referencia".

    `current_price` **no se manda desde el modal de edición** — misma dinámica
    que crear una Referencia: se deriva de `base_price` + `iva_percentage`
    (D-45/D-46), nunca se captura a mano. Si el body cambia `base_price` y/o
    `iva_percentage` sin mandar `current_price` explícito, el router lo
    recalcula solo (ver `update_item`). Sigue existiendo como campo propio acá
    por si algún flujo futuro necesita fijarlo directo; cuando viene explícito,
    gana él y el router no recalcula nada. En `null` no es válido — la columna
    es NOT NULL (D-45: toda unidad tiene un precio de venta propio) — el router
    lo rechaza en vez de dejar que Postgres tire un 500 por el constraint.
    """

    provider_id: Optional[uuid.UUID] = None
    location_id: Optional[uuid.UUID] = None
    status: Optional[ItemStatus] = None
    current_price: Optional[Decimal] = Field(None, gt=0)
    base_price: Optional[Decimal] = Field(None, gt=0)
    iva_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    provider_price: Optional[Decimal] = Field(None, ge=0)


class ItemRead(ItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    status: ItemStatus
    #  Overrides crudos (sin `COALESCE`): `None` = sigue el catálogo.
    base_price: Optional[Decimal] = None
    iva_percentage: Optional[Decimal] = None
    provider_price: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime
    version: int


class ItemStockSummaryRead(BaseModel):
    """
    Cifras de cabecera de la pantalla Productos.

    **Respeta los filtros activos**: son el resumen de lo que el usuario está
    mirando, no del inventario entero. Filtrar por categoría "Frenos" y ver
    cuánto capital hay parado en frenos es justamente la pregunta útil; unas
    cifras que no se mueven al filtrar se leen como rotas.

    Se calculan en el servidor sobre **todas** las filas que pasan el filtro, no
    sobre las que el scroll infinito alcanzó a cargar — si no, el resumen
    cambiaría según cuánto scrolleaste.
    """

    #  Productos (Referencias) que pasan el filtro. Es el número de cards.
    total_references: int
    #  Unidades físicas (`Item`) de esos productos. No es lo mismo: 29 productos
    #  pueden ser 453 unidades (D-41).
    total_units: int
    #  Productos con 0 unidades: venta perdida, es la cifra que exige acción.
    out_of_stock_references: int
    #  Productos con existencias pero por debajo del umbral: la señal de reponer
    #  ANTES de agotarse. Excluye a los agotados, que ya tienen su propio conteo.
    low_stock_references: int
    #  Umbral usado para `low_stock_references`, para que la UI no lo hardcodee.
    low_stock_threshold: int
    #  Capital inmovilizado: Σ(provider_price × unidades). Lo que hay en plata
    #  parada en las estanterías.
    total_cost: Decimal
    #  Σ(sale_price × unidades) — lo que entraría si se vendiera todo.
    total_sale_value: Decimal
    #  `total_sale_value - total_cost`.
    potential_margin: Decimal
    #  Margen bruto sobre la venta, en %. `0` si no hay valor de venta.
    margin_percentage: Decimal
    #  Unidades cuya Referencia no tiene `provider_price` cargado (D-52, captura
    #  manual). Sin esto, `total_cost` se leería como completo cuando no lo es.
    units_without_cost: int


class ItemStockUnitRead(BaseModel):
    """
    Una unidad física concreta en la pantalla de aterrizaje del Producto.

    A diferencia de `ItemStockRead` —que agrega y cuenta— acá cada fila ES un
    `Item` (D-41), con su identidad propia: es el `item_id` que el cajero teclea
    para vender o descontar esta unidad y no otra (A-22).

    Se llamaba `ItemExistenceRead` hasta D-64: "existence" es un calco de
    "existencias" que en inglés significa "el hecho de existir", no stock.
    `stock_unit` y no `unit` a secas para no chocar con `ItemStockRead.units`,
    que es un **conteo**, no una fila.

    `sale_price` sale de `Item.current_price` y no de la fórmula del catálogo:
    justamente el punto de que cada unidad tenga su precio es poder descontar
    una sola sin partir la Referencia (D-41).
    """

    item_id: uuid.UUID
    status: ItemStatus
    #  Nullable (migración 0005): el alta manual rápida no exige elegir
    #  proveedor ni ubicación en el momento.
    provider_id: Optional[uuid.UUID] = None
    provider_name: Optional[str] = None
    location_id: Optional[uuid.UUID] = None
    location_name: Optional[str] = None
    #  Porcentaje, no monto (D-19). El monto se deriva al pintar.
    iva_percentage: Decimal
    #  Costo de adquisición. Hoy vive en la Referencia (D-47), no en el Item:
    #  todas las unidades de una misma Referencia comparten este valor.
    provider_price: Optional[Decimal] = None
    base_price: Decimal
    sale_price: Decimal


class ItemDetailTotals(BaseModel):
    """
    Totales del producto, calculados en el servidor.

    No se dejan al cliente aunque éste reciba todas las filas: el servidor es la
    autoridad final sobre cifras de dinero (docs/04) y así el día que la lista
    se recorte o pagine los totales siguen siendo los del producto completo.
    """

    total_units: int
    total_base: Decimal
    total_iva: Decimal
    #  `total_base + total_iva` — el valor del inventario de este producto.
    total_value: Decimal


class ProductSummaryRead(BaseModel):
    """Cabecera de la pantalla: datos de catálogo de la Referencia que agrupa las existencias."""

    reference_id: uuid.UUID
    sku: str
    title: str
    brand: Optional[str] = None
    image_url: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    category_name: Optional[str] = None
    #  Proveedores distintos entre las existencias vivas — se deriva de los
    #  Ítems, no es un campo del catálogo.
    active_providers_count: int
    #  Precio con IVA del catálogo (D-45/D-46) — para prellenar el precio al
    #  agregar una existencia nueva sin recalcular la fórmula en el cliente.
    sale_price: Decimal


class ItemDetailRead(BaseModel):
    """
    Todo lo que pinta la pantalla de aterrizaje, en una sola respuesta.

    Va junto y no en tres endpoints porque la pantalla carga todo de una vez: un
    solo viaje evita que cabecera, totales y lista se pisen entre sí si el
    inventario cambia entre peticiones.
    """

    summary: ProductSummaryRead
    totals: ItemDetailTotals
    stock_units: list[ItemStockUnitRead]


class ItemStockRead(BaseModel):
    """
    Existencias agregadas **por Referencia** — una card de la pantalla Productos
    (CRUD Productos, D-51).

    No es un `Item`: cada `Item` es UNA unidad física individual
    (docs/03-modelo-datos.md §1.3, D-41), así que una lista cruda de ítems
    mostraría 24 tarjetas idénticas para "Aceite Motul x24". La pantalla necesita
    el eje contrario — qué hay en catálogo y cuántas unidades quedan de cada
    cosa — de ahí que la fila sea la Referencia y `units` el conteo de sus Ítems.

    Los campos de identificación (`sku`, `title`, `brand`, `image_url`,
    `category_id`) vienen de la Referencia porque el `Item` no los duplica.
    """

    reference_id: uuid.UUID
    sku: str
    title: str
    brand: Optional[str] = None
    image_url: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    #  Unidades en existencia = cuántas filas `Item` apuntan a esta Referencia
    #  con `status='available'` (ver `_available_join`).
    units: int
    #  Precio de venta con IVA del catálogo (D-45/D-46). Ver `_sale_price` en el router.
    sale_price: Decimal
    #  Base e IVA del catálogo. Viajan para que la caja registradora arme la
    #  línea de venta (base, IVA y descuento) con una sola consulta: sin esto
    #  tendría que pedir la Referencia aparte para cada producto que el cajero
    #  toca, y es justo el momento en que no puede esperar.
    base_price: Decimal
    iva_percentage: Decimal


class ProductImportInvalidRow(BaseModel):
    """Fila que no se pudo aplicar — no bloquea las demás (D-73)."""

    index: int
    sku: Optional[str] = None
    reason: str


class ProductImportVariant(BaseModel):
    """
    Variante que la importación va a crear (A-30 + D-90).

    Se lista con nombre y código asignado **antes** de confirmar: la creación es
    automática (decisión del dueño de producto), pero no puede ser invisible —
    un archivo que escribe el mismo producto con dos nombres distintos crearía
    dos fichas, y eso tiene que verse en la previsualización, no descubrirse
    después en el catálogo.
    """

    base_sku: str
    sku: str
    title: str
    units: int


class ProductImportDiscrepancy(BaseModel):
    """
    Fila cuyo dato de catálogo no coincide con la Referencia que ya existe.

    **No se aplica nada**: el archivo de existencias nunca edita el catálogo
    (decisión del dueño de producto). Se reporta para que el usuario sepa que
    su archivo dice otra cosa y decida corregir la Referencia por su cuenta.
    """

    sku: str
    #  Etiquetas de los campos que difieren: marca, categoria, precio base…
    fields: list[str]


class ProductImportPreview(BaseModel):
    """
    Respuesta de `POST /items/import/preview` — no escribe nada.

    Las cifras salen del **mismo planificador** que ejecuta el commit
    (`app/imports/products.py:plan`), así que lo que se promete acá es
    literalmente lo que va a pasar, incluso cuando el archivo repite un SKU.
    """

    total_rows: int
    #  Titular de la pantalla: existencias que se van a crear (D-41: una fila
    #  de `Item` por unidad). No es el número de filas del archivo.
    units_total: int
    #  Filas que se enganchan a una Referencia que ya existe.
    matched_count: int
    #  SKUs que no están en el catálogo y se van a crear como Referencia nueva.
    new_references: list[str]
    new_variants: list[ProductImportVariant]
    invalid: list[ProductImportInvalidRow]
    new_providers: list[str]
    new_locations: list[str]
    new_categories: list[str]
    discrepancies: list[ProductImportDiscrepancy]
    #  `None` para un archivo JSON — no tiene encabezados que detectar (D-74).
    columns_detected: Optional[list[str]] = None
    columns_missing: Optional[list[str]] = None
    columns_ignored: Optional[list[str]] = None


class ProductImportResult(BaseModel):
    """Respuesta de `POST /items/import` — ya escribió en la BBDD."""

    units_created: int
    references_created: int
    variants_created: int
    invalid: int
    #  `None` cuando no se creó ninguna unidad: no hay lote que deshacer.
    batch_id: Optional[uuid.UUID] = None


class ProductImportUndoResult(BaseModel):
    """
    Un lote de Productos puede haber creado unidades **y** catálogo, así que el
    undo informa las dos cosas por separado.
    """

    units_deleted: int
    references_deleted: int
    #  Proveedores/Ubicaciones/Categorías que el archivo autocreó y que nadie
    #  más está usando. Los que sí quedaron en uso se dejan y no bloquean.
    directory_deleted: int
