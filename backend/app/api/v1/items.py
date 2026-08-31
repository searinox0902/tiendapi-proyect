import uuid
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import ImageResolver, get_db, get_image_resolver, get_tenant_id
from app.api.filters import contains as _contains
from app.core.pricing import sale_price as _sale_price
from app.crud.base import CRUDBase
from app.models.category import Category
from app.models.item import Item
from app.models.location import Location
from app.models.provider import Provider
from app.models.reference import Reference
from app.schemas.common import Page
from app.schemas.item import (
    ItemCreate,
    ItemDetailRead,
    ItemRead,
    ItemStockRead,
    ItemStockSummaryRead,
    ItemUpdate,
)

router = APIRouter(prefix="/items", tags=["items"])
crud = CRUDBase(Item)


class StockStatus(str, Enum):
    """Estados de existencia por los que filtra la pantalla Productos."""

    ALL = "all"
    OUT_OF_STOCK = "out_of_stock"
    LOW_STOCK = "low_stock"
    IN_STOCK = "in_stock"


class StockSort(str, Enum):
    NEWEST = "newest"
    OLDEST = "oldest"
    #  Con existencias primero, agotados al final. Es el orden de la caja
    #  registradora: lo vendible tiene que estar arriba, pero lo agotado no se
    #  esconde — desde ahí se le agregan existencias en el momento.
    AVAILABLE_FIRST = "available_first"


#  Umbral de "stock bajo": a partir de acá conviene reponer antes de agotarse.
#  Es un valor plano por ahora; el punto de reorden por producto (que depende de
#  rotación y tiempo de entrega del proveedor) todavía no está modelado.
LOW_STOCK_THRESHOLD = 5


def _units_expression():
    """Unidades por Referencia — `COUNT` sobre el LEFT JOIN, así que 0 si no hay Ítems."""
    return func.count(Item.id)


def _available_join(tenant_id: uuid.UUID):
    """
    `ON` del LEFT JOIN a Ítems para todo lo que cuente **existencias**.

    Filtra a `status='available'`: una unidad vendida o dada de baja no es
    inventario. Sin esto la pantalla mostraba 11 unidades de un producto del
    que solo quedaban 7 vendibles, y el cobro fallaba con un 409 después de
    que el cajero ya la había agregado al carrito. Es además lo que fija D-49
    para el valor de bodega (`WHERE status='available'`).

    Va en el `ON` y no en el `WHERE` por la misma razón que `tenant_id`: en el
    `WHERE` convertiría el LEFT JOIN en INNER y desaparecerían justamente las
    Referencias agotadas, que son las que la pantalla tiene que mostrar.

    Compartido por la grilla y el resumen para que no puedan contar distinto.
    """
    return (
        (Item.reference_id == Reference.id)
        & (Item.tenant_id == tenant_id)
        & (Item.status == "available")
    )


def _last_movement_expression():
    """
    Fecha por la que ordena "más reciente / más antiguo": la última entrada de
    mercancía, y si el producto nunca recibió ninguna, su alta en catálogo.

    El `COALESCE` evita NULLs: sin él los productos agotados quedarían fuera de
    orden y el resultado cambiaría según el sentido del ORDER BY.
    """
    return func.coalesce(func.max(Item.created_at), Reference.created_at)


def _stock_having(status: StockStatus):
    """
    Condición `HAVING` del estado de existencia. Va en `HAVING` y no en `WHERE`
    porque filtra sobre el `COUNT` agregado, que en `WHERE` todavía no existe.
    """
    units = _units_expression()
    if status is StockStatus.OUT_OF_STOCK:
        return units == 0
    if status is StockStatus.LOW_STOCK:
        #  Excluye los agotados a propósito: ya tienen su propia card, y
        #  mezclarlos escondería cuáles todavía se pueden vender.
        return (units > 0) & (units <= LOW_STOCK_THRESHOLD)
    if status is StockStatus.IN_STOCK:
        return units > 0
    return None


def _stock_conditions(
    tenant_id: uuid.UUID,
    sku: str | None,
    title: str | None,
    brand: str | None,
    category_id: uuid.UUID | None,
    search: str | None = None,
) -> list:
    """
    Filtros de la pantalla Productos, compartidos por la grilla y su resumen.

    Viven acá porque las dos consultas tienen que filtrar **idéntico**: si el
    resumen y la grilla difirieran en una condición, las cifras de cabecera no
    corresponderían a las cards de abajo y no habría cómo notarlo mirando.

    Son todas columnas de `Reference` — el `Item` no duplica ninguna.

    `search` es aparte de `sku`/`title` porque los une con **OR**: un solo
    campo de búsqueda (la caja registradora) contra dos columnas. Cruzarlos con
    AND exigiría que el término estuviera en las dos a la vez.
    """
    conditions = [Reference.tenant_id == tenant_id]
    if sku:
        conditions.append(Reference.sku.ilike(_contains(sku), escape="\\"))
    if title:
        conditions.append(Reference.title.ilike(_contains(title), escape="\\"))
    if brand:
        conditions.append(Reference.brand.ilike(_contains(brand), escape="\\"))
    if search:
        pattern = _contains(search)
        conditions.append(
            or_(
                Reference.sku.ilike(pattern, escape="\\"),
                Reference.title.ilike(pattern, escape="\\"),
            )
        )
    if category_id is not None:
        conditions.append(Reference.category_id == category_id)
    return conditions


@router.get("/", response_model=list[ItemRead])
def list_items(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    return crud.get_multi(db, tenant_id, skip=skip, limit=limit)


@router.get("/stock", response_model=Page[ItemStockRead])
def list_stock(
    skip: int = Query(0, ge=0, description="Registros a saltar"),
    limit: int = Query(12, ge=1, le=100, description="Máximo de registros por página"),
    sku: str | None = Query(None, description="Coincidencia parcial, ignora mayúsculas"),
    title: str | None = Query(None, description="Coincidencia parcial, ignora mayúsculas"),
    brand: str | None = Query(None, description="Coincidencia parcial, ignora mayúsculas"),
    search: str | None = Query(None, description="Coincidencia parcial en SKU **o** nombre"),
    category_id: uuid.UUID | None = Query(None, description="Categoría exacta"),
    stock_status: StockStatus = Query(StockStatus.ALL, description="Estado de existencia"),
    sort: StockSort = Query(StockSort.NEWEST, description="Orden de la grilla"),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    resolve_image: ImageResolver = Depends(get_image_resolver),
):
    """
    Existencias agregadas por Referencia — alimenta la grilla de Productos
    (CRUD Productos, D-51) y la de la caja registradora.

    Los filtros de texto (SKU, nombre, marca, categoría) son todos columnas de
    `Reference`: el `Item` no duplica ninguno, por eso la consulta parte de la
    Referencia y agrega los Ítems encima, y no al revés.

    `search` cruza SKU y nombre con **OR** (los otros dos se cruzan con AND):
    en la caja hay un solo campo de búsqueda y el cajero no sabe —ni debería—
    si lo que tiene en la mano es un código o un nombre.

    `stock_status` es distinto: filtra sobre el **conteo agregado** de unidades,
    así que va en `HAVING`, no en `WHERE`. Es lo que hace clicables las cards de
    resumen (agotados / stock bajo).

    **`LEFT JOIN` deliberado:** las Referencias sin ningún Ítem también salen,
    con `units = 0`. Una pantalla de inventario que esconde lo agotado es justo
    la que no sirve para reponer — y en la caja, es desde esa card agotada que
    se agregan existencias en el momento.
    """
    conditions = _stock_conditions(tenant_id, sku, title, brand, category_id, search)
    having = _stock_having(stock_status)
    units = _units_expression()
    last_movement = _last_movement_expression()

    join_on = _available_join(tenant_id)

    # `total` cuenta Referencias que pasan el filtro, no Ítems: es el número de
    # cards que hay que paginar. Contar Ítems daría un total inflado y páginas
    # vacías al final. Con `HAVING` de por medio hay que contar las filas ya
    # agrupadas, de ahí la subconsulta.
    grouped_ids = (
        select(Reference.id)
        .outerjoin(Item, join_on)
        .where(*conditions)
        .group_by(Reference.id)
    )
    if having is not None:
        grouped_ids = grouped_ids.having(having)
    total = db.execute(
        select(func.count()).select_from(grouped_ids.subquery())
    ).scalar_one()

    # Desempate por `id` porque el SKU no es único a nivel de esquema y dos
    # productos con la misma fecha alternarían de orden entre peticiones.
    if sort is StockSort.AVAILABLE_FIRST:
        #  `units == 0` da False (0) para lo vendible y True (1) para lo
        #  agotado; ascendente deja lo vendible arriba. Dentro de cada grupo se
        #  mantiene el orden por última entrada, para que lo recién llegado
        #  siga apareciendo primero.
        order_by = [(units == 0).asc(), last_movement.desc(), Reference.id.desc()]
    else:
        order = last_movement.desc() if sort is StockSort.NEWEST else last_movement.asc()
        order_by = [order, Reference.id.desc()]

    stmt = (
        select(Reference, units.label("units"))
        .outerjoin(Item, join_on)
        .where(*conditions)
        .group_by(Reference.id)
        .order_by(*order_by)
        .offset(skip)
        .limit(limit)
    )
    if having is not None:
        stmt = stmt.having(having)
    rows = db.execute(stmt).all()

    return {
        "items": [
            {
                "reference_id": reference.id,
                "sku": reference.sku,
                "title": reference.title,
                "brand": reference.brand,
                "image_url": resolve_image(reference.sku, reference.image_url),
                "category_id": reference.category_id,
                "units": units,
                "sale_price": _sale_price(reference.base_price, reference.iva_percentage),
                "base_price": reference.base_price,
                "iva_percentage": reference.iva_percentage,
            }
            for reference, units in rows
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }



@router.get("/stock/summary", response_model=ItemStockSummaryRead)
def stock_summary(
    sku: str | None = Query(None, description="Coincidencia parcial, ignora mayúsculas"),
    title: str | None = Query(None, description="Coincidencia parcial, ignora mayúsculas"),
    brand: str | None = Query(None, description="Coincidencia parcial, ignora mayúsculas"),
    category_id: uuid.UUID | None = Query(None, description="Categoría exacta"),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Cifras de cabecera de la pantalla Productos, sobre el mismo conjunto que
    filtra la grilla (`/items/stock`).

    Acepta los mismos filtros de texto a propósito: el resumen describe lo que
    el usuario está mirando. Se calcula sobre **todas** las filas que pasan el
    filtro, no sobre la tanda que el scroll infinito alcanzó a cargar.

    **No acepta `stock_status`, y es deliberado.** Las cards son el marco desde
    el que se filtra: si al hacer clic en "Agotados" el resumen se recalculara
    sobre los agotados, las otras cards quedarían en cero y no habría desde
    dónde volver ni con qué comparar. Los conteos describen el conjunto de
    texto/categoría; `stock_status` recorta la grilla de abajo, no la cabecera.

    `sale_price` es derivado (D-45/D-46, redondeo a $50) y no una columna, así
    que el total de venta no puede salir de un `SUM` en SQL: se agrega por
    Referencia en la consulta y se multiplica en Python con `Decimal`, sin pasar
    nunca por `float`. Son decenas o cientos de Referencias, no millones.

    `LEFT JOIN` igual que en la grilla: las Referencias agotadas cuentan como
    producto (y son las que alimentan `out_of_stock_references`), aunque no
    aporten ni costo ni valor de venta.
    """
    conditions = _stock_conditions(tenant_id, sku, title, brand, category_id)

    rows = db.execute(
        select(
            Reference.base_price,
            Reference.iva_percentage,
            Reference.provider_price,
            func.count(Item.id).label("units"),
        )
        .select_from(Reference)
        .outerjoin(Item, _available_join(tenant_id))
        .where(*conditions)
        .group_by(Reference.id)
    ).all()

    total_references = len(rows)
    total_units = 0
    out_of_stock = 0
    low_stock = 0
    total_cost = Decimal(0)
    total_sale_value = Decimal(0)
    units_without_cost = 0

    for base_price, iva_percentage, provider_price, units in rows:
        total_units += units
        if 0 < units <= LOW_STOCK_THRESHOLD:
            low_stock += 1
        if units == 0:
            out_of_stock += 1
            continue
        total_sale_value += _sale_price(base_price, iva_percentage) * units
        if provider_price is None:
            # No se asume un costo: se cuenta aparte para que la UI pueda avisar
            # que `total_cost` está incompleto en vez de mentir por omisión.
            units_without_cost += units
        else:
            total_cost += provider_price * units

    #  `total_sale_value` incluye IVA (`_sale_price`) y `total_cost` no
    #  (`provider_price` se captura sin IVA, A-26) — mezcla deliberada, mismo
    #  criterio que `total_profit` en bills.py: ver D-70/A-26 antes de "arreglar"
    #  este margen para que quede neto de IVA.
    potential_margin = total_sale_value - total_cost
    margin_percentage = (
        (potential_margin / total_sale_value * 100).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if total_sale_value > 0
        else Decimal(0)
    )

    return {
        "total_references": total_references,
        "total_units": total_units,
        "out_of_stock_references": out_of_stock,
        "low_stock_references": low_stock,
        "low_stock_threshold": LOW_STOCK_THRESHOLD,
        "total_cost": total_cost,
        "total_sale_value": total_sale_value,
        "potential_margin": potential_margin,
        "margin_percentage": margin_percentage,
        "units_without_cost": units_without_cost,
    }


@router.get("/by-reference/{reference_id}", response_model=ItemDetailRead)
def get_detail_by_reference(
    reference_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    resolve_image: ImageResolver = Depends(get_image_resolver),
):
    """
    Cabecera + totales + **todas** las existencias de una Referencia — alimenta
    la pantalla de aterrizaje del Producto.

    Devuelve la lista completa a propósito, sin paginar: son las unidades de UN
    producto (un conjunto acotado, del orden de cientos), y el caso de uso real
    es buscar una existencia puntual — cosa que exige tenerlas todas. El
    despliegue es local-first (D-37): el cliente habla con un backend en la
    misma máquina/LAN, así que el costo dominante sería la BBDD, no la red.

    Por eso lo que sí se cuida es el trabajo por fila:

    * **Una sola consulta con JOINs.** Proveedor y ubicación se traen unidos, no
      resueltos por fila: con 1.000 unidades, hacerlo por separado serían 2.001
      consultas en vez de 1.
    * **Solo las columnas que se pintan.** Se seleccionan campos sueltos y no
      entidades ORM completas, para no hidratar 1.000 objetos con su overhead de
      identity map para luego serializarlos y tirarlos.
    * **`LEFT JOIN`**: `provider_id`/`location_id` son opcionales (D-52-bis, el
      alta manual rápida no exige elegirlos al momento) — un `INNER JOIN`
      perdería justo esas unidades sin dueño ni ubicación asignados todavía.
    * Los totales salen de esas mismas filas, sin una consulta agregada extra.

    `items.reference_id` ya está indexado en el modelo, que es el filtro de esta
    consulta.
    """
    reference = db.execute(
        select(Reference).where(Reference.id == reference_id, Reference.tenant_id == tenant_id)
    ).scalar_one_or_none()
    if reference is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference not found")

    category_name = None
    if reference.category_id is not None:
        category_name = db.execute(
            select(Category.name).where(
                Category.id == reference.category_id, Category.tenant_id == tenant_id
            )
        ).scalar_one_or_none()

    # El orden es por ubicación: quien abre esta pantalla suele estar buscando
    # físicamente una unidad. Postgres pone los NULL al final en ASC, así que
    # las unidades sin ubicación asignada quedan agrupadas al fondo — no
    # perdidas entre las demás. Desempate por `id` para que el orden sea estable.
    #
    # `Reference` NO entra a este SELECT (a propósito): ya está cargada en
    # `reference` desde la consulta de arriba, y agregar sus columnas acá sin
    # un JOIN explícito le pediría a SQLAlchemy unirla sola — como no hay
    # condición de igualdad con `Item`, arma un producto cartesiano contra TODA
    # la tabla de Referencias. El `COALESCE` se hace en Python dos líneas más
    # abajo, no en SQL.
    rows = db.execute(
        select(
            Item.id,
            Item.status,
            Item.provider_id,
            Provider.title,
            Item.location_id,
            Location.name,
            Item.current_price,
            Item.iva_percentage,
            Item.provider_price,
            Item.base_price,
        )
        .outerjoin(Provider, Provider.id == Item.provider_id)
        .outerjoin(Location, Location.id == Item.location_id)
        .where(Item.reference_id == reference_id, Item.tenant_id == tenant_id)
        .order_by(Location.name, Provider.title, Item.id)
    ).all()

    # `COALESCE` en Python: una unidad sin editar sigue el precio/IVA/costo
    # VIGENTES de catálogo (no una foto fija del día que se creó); una unidad
    # editada (migraciones 0007/0008) queda fija en lo que se le escribió, sin
    # arrastrar a las demás existencias de la misma Referencia.
    stock_units = [
        {
            "item_id": item_id,
            "status": item_status,
            "provider_id": provider_id,
            "provider_name": provider_title,
            "location_id": location_id,
            "location_name": location_name,
            "iva_percentage": item_iva if item_iva is not None else reference.iva_percentage,
            "provider_price": (
                item_cost if item_cost is not None else reference.provider_price
            ),
            "base_price": item_base if item_base is not None else reference.base_price,
            "sale_price": current_price,
        }
        for (
            item_id, item_status, provider_id, provider_title, location_id, location_name,
            current_price, item_iva, item_cost, item_base,
        ) in rows
    ]

    # Cuenta TODAS las filas sin importar `status`: una unidad "de baja" sigue
    # siendo capital físico en bodega hasta que alguien la elimine de verdad.
    # Si el negocio prefiere que el resumen refleje solo lo vendible, este es
    # el lugar para filtrar por `status != 'written_off'` — decisión de negocio
    # que no se tomó por mi cuenta, queda anotada para revisar.
    #
    # `total_base`/`total_value` son la SUMA de lo que cada unidad tiene de
    # verdad, no `reference.base_price × unidades`: desde que precio base/venta
    # se pueden editar por unidad (D-45, migraciones 0007/0008), la
    # multiplicación uniforme mentiría en cuanto una sola existencia divergiera
    # del catálogo. `total_iva` se deriva hacia atrás de la diferencia, mismo
    # principio que ya usa la factura para desglosar IVA de un total conocido.
    total_units = len(rows)
    total_base = sum((unit["base_price"] for unit in stock_units), Decimal(0))
    total_value = sum((unit["sale_price"] for unit in stock_units), Decimal(0))
    total_iva = total_value - total_base

    return {
        "summary": {
            "reference_id": reference.id,
            "sku": reference.sku,
            "title": reference.title,
            "brand": reference.brand,
            "image_url": resolve_image(reference.sku, reference.image_url),
            "category_id": reference.category_id,
            "category_name": category_name,
            # Se excluye `None`: una unidad sin proveedor asignado todavía no
            # cuenta como "un proveedor más" — contaría un proveedor fantasma.
            "active_providers_count": len(
                {provider_id for _, provider_id, *_ in rows if provider_id is not None}
            ),
            "sale_price": _sale_price(reference.base_price, reference.iva_percentage),
        },
        "totals": {
            "total_units": total_units,
            "total_base": total_base,
            "total_iva": total_iva,
            "total_value": total_base + total_iva,
        },
        "stock_units": stock_units,
    }


@router.post("/", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
def create_item(
    payload: ItemCreate,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    return crud.create(db, tenant_id, payload.model_dump())


@router.get("/{item_id}", response_model=ItemRead)
def get_item(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    obj = crud.get(db, tenant_id, item_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return obj


@router.patch("/{item_id}", response_model=ItemRead)
def update_item(
    item_id: uuid.UUID,
    payload: ItemUpdate,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Actualización parcial — un mismo endpoint para "dar de baja"/"activar"
    (`{"status": "written_off" | "available"}`) y para reasignar proveedor/ubicación
    en lote (`{"provider_id": ...}` y/o `{"location_id": ...}`), sea una
    existencia o muchas: el cliente llama esto una vez por Ítem seleccionado.

    `exclude_unset=True` es la parte que importa: un campo **ausente** del body
    no se toca, uno presente con `null` sí se limpia. Sin esa distinción,
    reasignar solo la ubicación de un lote borraría el proveedor de cada fila
    (porque el modelo por defecto de Pydantic manda `null` para todo lo que no
    se especificó). Para `iva_percentage`/`provider_price`/`base_price`
    (migraciones 0007/0008), `null` significa además "volvé a seguir el
    catálogo" — ver `ItemUpdate`.

    **`current_price` se recalcula solo** cuando el body trae `base_price` y/o
    `iva_percentage` sin mandar `current_price` explícito — misma dinámica que
    crear una Referencia: el precio de venta se deriva, no se captura a mano
    (D-45/D-46). El lado que no vino en este PATCH se resuelve con lo que la
    unidad ya tenía (su propio override) o, si tampoco tenía, con el catálogo
    — así una existencia con costo/IVA propios sigue siendo consistente
    consigo misma después de tocar solo uno de los dos campos.
    """
    changes = payload.model_dump(exclude_unset=True)
    if "current_price" in changes and changes["current_price"] is None:
        # A diferencia de iva/costo/base, acá NO existe un "volvé al
        # catálogo": la columna es NOT NULL (D-45, toda unidad tiene su propio
        # precio de venta). Se rechaza acá, explícito, en vez de dejar que
        # Postgres tire un 500 genérico por violar el constraint.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="current_price no puede ser null",
        )

    touches_formula = "base_price" in changes or "iva_percentage" in changes
    if touches_formula and "current_price" not in changes:
        item = crud.get(db, tenant_id, item_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
        reference = db.execute(
            select(Reference).where(Reference.id == item.reference_id, Reference.tenant_id == tenant_id)
        ).scalar_one()

        def _effective(field: str, item_value, catalog_value):
            # Presente en este PATCH (incluso `null`) gana; si no, lo que la
            # unidad ya tenía; si tampoco, el catálogo.
            if field in changes:
                return changes[field] if changes[field] is not None else catalog_value
            return item_value if item_value is not None else catalog_value

        effective_base = _effective("base_price", item.base_price, reference.base_price)
        effective_iva = _effective("iva_percentage", item.iva_percentage, reference.iva_percentage)
        changes["current_price"] = _sale_price(effective_base, effective_iva)

    obj = crud.update(db, tenant_id, item_id, changes)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return obj


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    try:
        deleted = crud.delete(db, tenant_id, item_id)
    except IntegrityError:
        # `BillItem.item_id` es FK restrictiva (sin cascade): si esta unidad ya
        # se facturó, Postgres rechaza el DELETE. Es la señal correcta — una
        # unidad vendida es un registro histórico, no algo que se borra; el
        # camino para sacarla de circulación es "dar de baja", no eliminar.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar: la existencia ya está asociada a una factura",
        )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
