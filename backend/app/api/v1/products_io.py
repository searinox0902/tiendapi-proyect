"""Export/import de Productos y existencias — endpoints de A-30.

Va en un módulo aparte de `items.py` (que ya pasa las 600 líneas) pero bajo el
**mismo prefijo `/items`**, porque son operaciones sobre la misma entidad. Se
registra en `router.py` **antes** que `items.router` a propósito: ahí vive
`GET /items/{item_id}`, que capturaría `/items/export` y lo rechazaría con un
422 por no ser un UUID.

Mismo contrato que los otros dos importadores (D-73/D-74/D-75): dos puertas de
entrada (JSON y el .xlsx propio), previsualización obligatoria antes de
escribir, y lote deshacible. Lo propio de acá está en `app/imports/products.py`
—la frontera unidad/variante— y en que una fila del archivo puede crear **N
filas** de `Item` (D-41), no una.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_tenant_id
from app.api.v1.items import StockStatus, _available_join, _stock_conditions, _stock_having
from app.core.pricing import sale_price as _sale_price
from app.exports import products as products_export
from app.imports import products as products_import
from app.models.category import Category
from app.models.item import Item
from app.models.location import Location
from app.models.provider import Provider
from app.models.reference import Reference
from app.schemas.item import (
    ProductImportPreview,
    ProductImportResult,
    ProductImportUndoResult,
)

router = APIRouter(prefix="/items", tags=["items"])

#  Estado de las unidades que se exportan. Una vendida o dada de baja no es
#  inventario (mismo criterio que `items.py:_available_join`), y reimportar el
#  archivo resucitaría stock que no existe.
EXPORTABLE_STATUS = "available"


#  Los filtros NO se reimplementan acá: se importan de `items.py`, que es donde
#  la grilla y su resumen ya los comparten. Si la exportación armara su propio
#  `WHERE`, el archivo podría no coincidir con lo que el usuario tiene en
#  pantalla — y ese desajuste es invisible hasta que alguien compara fila por
#  fila (mismo criterio que documenta `references.py:_reference_conditions`).


def _qualifying_reference_ids(tenant_id: uuid.UUID, conditions: list, stock_status: StockStatus):
    """
    Referencias que pasan el filtro de **existencias agregadas**, o `None`.

    `stock_status` no es un filtro de fila sino del conteo por Referencia, así
    que en la grilla va en un `HAVING` sobre el grupo. Acá el agrupamiento es
    otro —por Referencia + proveedor + ubicación + precios, para poder
    reimportar— así que se resuelve con la misma consulta agrupada de
    `list_stock` usada como subconsulta, en vez de traducir la regla a mano.
    """
    having = _stock_having(stock_status)
    if having is None:
        return None
    return (
        select(Reference.id)
        .outerjoin(Item, _available_join(tenant_id))
        .where(*conditions)
        .group_by(Reference.id)
        .having(having)
    )


@router.get("/export")
def export_products(
    export_format: str = Query(
        "json",
        alias="format",
        pattern="^(json|xlsx|markdown)$",
        description="json | xlsx | markdown",
    ),
    #  Mismos nombres y semántica que `GET /items/stock`: mandarlos exporta lo
    #  que el usuario está viendo, omitirlos exporta el inventario completo.
    sku: str | None = Query(None, description="Coincidencia parcial, ignora mayúsculas"),
    title: str | None = Query(None, description="Coincidencia parcial, ignora mayúsculas"),
    brand: str | None = Query(None, description="Coincidencia parcial, ignora mayúsculas"),
    search: str | None = Query(None, description="Coincidencia parcial en SKU **o** nombre"),
    category_id: uuid.UUID | None = Query(None, description="Categoría exacta"),
    stock_status: StockStatus = Query(StockStatus.ALL, description="Estado de existencia"),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Exporta las existencias como archivo descargable, y de paso es **la
    plantilla** del importador: un inventario vacío responde igual, con
    cabeceras y descriptores de columna y sin filas (D-73).

    **Una fila por grupo de unidades idénticas**, no por unidad: agrupa por
    Referencia, proveedor, ubicación y los overrides de precio —o sea, por todo
    lo que el archivo emite— y cuenta cuántas hay. Exportar 453 unidades como
    453 filas sería fiel pero inútil, y agrupar por menos campos haría que
    reimportar el archivo no reprodujera las mismas unidades.

    Las FKs salen por **nombre** (proveedor, ubicación, categoría), nunca como
    UUID: un identificador local no significa nada en otra instalación (D-42).
    """
    #  `COALESCE(Item.x, Reference.x)`: `NULL` en la unidad significa "sigue el
    #  catálogo" (migraciones 0007/0008), así que el archivo tiene que llevar el
    #  precio vigente, no un nulo que el importador leería como "sin dato".
    base = func.coalesce(Item.base_price, Reference.base_price)
    iva = func.coalesce(Item.iva_percentage, Reference.iva_percentage)
    cost = func.coalesce(Item.provider_price, Reference.provider_price)

    conditions = _stock_conditions(tenant_id, sku, title, brand, category_id, search)
    stmt = (
        select(
            Reference,
            Provider.title,
            Location.name,
            Category.name,
            base,
            iva,
            cost,
            func.count(Item.id),
        )
        .select_from(Item)
        .join(Reference, Reference.id == Item.reference_id)
        .outerjoin(Provider, Provider.id == Item.provider_id)
        .outerjoin(Location, Location.id == Item.location_id)
        .outerjoin(Category, Category.id == Reference.category_id)
        .where(Item.tenant_id == tenant_id, Item.status == EXPORTABLE_STATUS, *conditions)
        .group_by(Reference.id, Provider.title, Location.name, Category.name, base, iva, cost)
        .order_by(Reference.sku)
    )
    califican = _qualifying_reference_ids(tenant_id, conditions, stock_status)
    if califican is not None:
        stmt = stmt.where(Reference.id.in_(califican))

    rows = db.execute(stmt).all()

    payload = products_export.build_payload(rows)
    render, media_type, extension = products_export.RENDERERS[export_format]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")

    return Response(
        content=render(payload),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="productos-{stamp}.{extension}"',
            #  Sin esto el navegador no deja leer el nombre del archivo desde JS.
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


async def _read_and_plan(
    file: UploadFile, db: Session, tenant_id: uuid.UUID, create_missing: bool
):
    """Lectura + planificación, idénticas para previsualizar y para aplicar."""
    content = await file.read()
    try:
        body = products_import.read_upload(file.filename or "", file.content_type or "", content)
        parsed = products_import.parse_payload(body)
    except products_import.ImportFormatError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(error))

    plan = products_import.plan(db, tenant_id, parsed.rows, create_missing=create_missing)
    if plan.total_units > products_import.MAX_UNITS_PER_IMPORT:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=(
                f"El archivo pide crear {plan.total_units} existencias y el máximo por "
                f"importación es {products_import.MAX_UNITS_PER_IMPORT}. "
                "Partilo en varios archivos."
            ),
        )
    return body, parsed, plan


@router.post("/import/preview", response_model=ProductImportPreview)
async def preview_product_import(
    file: UploadFile = File(
        ...,
        description="Existencias en JSON o Excel (.xlsx) — el mismo que produce GET /items/export",
    ),
    create_missing: bool = Query(
        True,
        description=(
            "SKU que no está en el catálogo: crear la Referencia (default) "
            "o marcar la fila inválida"
        ),
    ),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Cuenta qué haría la importación **sin escribir nada** (D-73: previsualización
    obligatoria antes de aplicar).

    Todas las cifras salen del planificador que después ejecuta el commit, así
    que no pueden divergir — incluidos los casos que un conteo ingenuo erra: un
    SKU repetido en el archivo suma unidades en vez de contarse dos veces como
    producto nuevo.
    """
    body, parsed, plan = await _read_and_plan(file, db, tenant_id, create_missing)

    invalid = [
        {"index": error.index, "sku": error.sku, "reason": error.reason} for error in parsed.errors
    ]
    invalid += [
        {"index": item.row.index, "sku": item.row.sku, "reason": item.reason}
        for item in plan.rows
        if item.action == products_import.ACTION_INVALID
    ]

    variants = [
        {
            "base_sku": products_import.base_of(item.target_sku),
            "sku": item.target_sku,
            "title": item.row.title or item.target_sku,
            "units": item.row.units,
        }
        for item in plan.rows
        if item.action == products_import.ACTION_NEW_VARIANT
    ]
    discrepancies = [
        {"sku": item.target_sku, "fields": item.discrepancies}
        for item in plan.rows
        if item.discrepancies
    ]

    valid = plan.valid
    creating = [
        item
        for item in valid
        if item.action
        in (products_import.ACTION_NEW_REFERENCE, products_import.ACTION_NEW_VARIANT)
    ]
    #  Proveedor y ubicación se resuelven para **cada unidad**, así que
    #  cualquier fila válida que los nombre los crea. La categoría no: solo se
    #  aplica al crear una Referencia — anunciarla desde una fila que solo suma
    #  existencias sería prometer algo que el commit no hace (el archivo nunca
    #  edita el catálogo).
    #  `dict.fromkeys` y no un `set`: deduplica conservando el orden del
    #  archivo, que es el que decide qué grafía se anuncia y se guarda.
    provider_names = list(dict.fromkeys(r.row.provider_name for r in valid if r.row.provider_name))
    location_names = list(dict.fromkeys(r.row.location_name for r in valid if r.row.location_name))
    category_names = list(
        dict.fromkeys(r.row.category_name for r in creating if r.row.category_name)
    )
    #  La Referencia nueva sin proveedor en el archivo cae al placeholder, que
    #  también se autocrea: omitirlo dejaría un Proveedor apareciendo en el
    #  Directorio sin haberse anunciado.
    if any(row.row.provider_name is None for row in creating):
        provider_names.append(products_import.PLACEHOLDER_PROVIDER_NAME)

    #  Sin `batch_id`: previsualizar no crea nada, y el índice acá se usa solo
    #  para preguntar. La comparación es plegada (`app/core/text.py:fold`), así
    #  que un `HONDA` del archivo contra un `Honda` de la base no se anuncia
    #  como proveedor nuevo — no lo es.
    indexes = products_import.build_indexes(db, tenant_id)

    return {
        "total_rows": len(parsed.rows) + len(parsed.errors),
        "units_total": plan.total_units,
        "matched_count": sum(1 for item in valid if item.action == products_import.ACTION_UNITS),
        "new_references": sorted(
            {
                item.target_sku
                for item in plan.rows
                if item.action == products_import.ACTION_NEW_REFERENCE
            }
        ),
        "new_variants": variants,
        "invalid": sorted(invalid, key=lambda row: row["index"]),
        "new_providers": sorted(indexes["provider"].missing(provider_names)),
        "new_locations": sorted(indexes["location"].missing(location_names)),
        "new_categories": sorted(indexes["category"].missing(category_names)),
        "discrepancies": discrepancies,
        #  Solo presentes cuando el archivo es .xlsx (D-74).
        "columns_detected": body.get("columns_detected"),
        "columns_missing": body.get("columns_missing"),
        "columns_ignored": body.get("columns_ignored"),
    }


@router.post("/import", response_model=ProductImportResult, status_code=status.HTTP_201_CREATED)
async def commit_product_import(
    file: UploadFile = File(..., description="Mismo archivo que /import/preview — JSON o .xlsx"),
    create_missing: bool = Query(
        True, description="SKU que no está en el catálogo: crear la Referencia (default)"
    ),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Aplica la importación ejecutando el plan, sin volver a decidir nada.

    **Suma unidades, nunca reconcilia un total** (A-30): si el archivo dice 10 y
    ya había 5, quedan 15. Esa es justamente la diferencia con las existencias
    del nivel de reemplazo de D-73, donde la cantidad no tenía semántica de
    fusión — acá cada fila del archivo son unidades que llegaron, no un
    inventario que se declara.

    **El catálogo nunca se edita.** Marca, categoría y precios de una fila cuyo
    SKU ya existe se ignoran (se reportan en la previsualización); las unidades
    nacen sin overrides, siguiendo el precio vigente de la Referencia.
    """
    _, parsed, plan = await _read_and_plan(file, db, tenant_id, create_missing)

    if not plan.valid:
        return {
            "units_created": 0,
            "references_created": 0,
            "variants_created": 0,
            "invalid": len(parsed.errors) + len(plan.rows) - len(plan.valid),
            "batch_id": None,
        }

    batch_id = uuid.uuid4()
    #  Un índice por entidad, con el `batch_id` de la corrida: lo que se
    #  autocree queda etiquetado y el undo se lo lleva. Comparación plegada, así
    #  que `Honda`/`HONDA`/`Hónda` en el mismo archivo caen en UN proveedor.
    indexes = products_import.build_indexes(db, tenant_id, batch_id)
    #  `Reference.brand` es texto libre (D-57), no una FK: sin esto un archivo
    #  con `Honda`, `HONDA` y `hónda` dejaba tres marcas en el catálogo.
    brands = products_import.build_brand_canonicalizer(db, tenant_id)
    #  Referencias creadas en ESTA corrida, para que la segunda fila del mismo
    #  producto nuevo cuelgue sus unidades de la primera en vez de crear otra.
    created_references: dict[str, Reference] = {}
    units_created = 0
    references_created = 0
    variants_created = 0

    try:
        for item in plan.valid:
            row = item.row
            reference = item.reference or created_references.get(item.target_sku)

            if reference is None:
                #  `provider_id` de la Referencia es NOT NULL: acá sí aplica el
                #  placeholder, y solo acá (ver `ParsedRow.provider_name`).
                provider = indexes["provider"].resolve(
                    row.provider_name or products_import.PLACEHOLDER_PROVIDER_NAME
                )
                category = indexes["category"].resolve(row.category_name)
                reference = Reference(
                    tenant_id=tenant_id,
                    provider_id=provider.id,
                    category_id=category.id if category else None,
                    sku=item.target_sku,
                    #  El nombre cae al SKU cuando la fila no trae ninguno
                    #  (D-83). En una variante siempre hay título: es lo que la
                    #  hizo variante.
                    title=row.title or item.target_sku,
                    brand=brands.canonical(row.brand),
                    description=row.description,
                    image_url=row.image_url,
                    base_price=row.base_price,
                    iva_percentage=row.iva_percentage or Decimal(0),
                    provider_price=row.provider_price,
                    import_batch_id=batch_id,
                )
                db.add(reference)
                db.flush()
                created_references[item.target_sku] = reference
                if item.action == products_import.ACTION_NEW_VARIANT:
                    variants_created += 1
                else:
                    references_created += 1

            #  `resolve` devuelve `None` con nombre vacío: en el Ítem las dos
            #  columnas son nullable (migración 0005) y no llevan placeholder.
            item_provider = indexes["provider"].resolve(row.provider_name)
            item_location = indexes["location"].resolve(row.location_name)
            #  Precio de venta de la unidad con la fórmula canónica (D-45/D-46),
            #  nunca copiado del archivo: `current_price` es NOT NULL y una
            #  unidad recién creada vale lo que dice el catálogo.
            current_price = _sale_price(reference.base_price, reference.iva_percentage)

            for _ in range(row.units):
                db.add(
                    Item(
                        tenant_id=tenant_id,
                        reference_id=reference.id,
                        provider_id=item_provider.id if item_provider else None,
                        location_id=item_location.id if item_location else None,
                        #  Una fila de `Item` por unidad física (D-41), igual
                        #  que el alta manual desde la pantalla de Productos.
                        #  `quantity` queda en 1 porque el sistema **cuenta
                        #  filas** (`func.count(Item.id)`), nunca suma esta
                        #  columna.
                        quantity=Decimal(1),
                        current_price=current_price,
                        #  Sin overrides: la unidad sigue el precio VIGENTE del
                        #  catálogo vía COALESCE, no una foto del día de carga.
                        import_batch_id=batch_id,
                    )
                )
                units_created += 1

        db.commit()
    except IntegrityError:
        #  Red de seguridad, igual que en `directory_io.py`: una restricción de
        #  base no debería salir como 500 con el lote a medio aplicar.
        db.rollback()
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=(
                "Alguna fila no cumple una restricción de la base de datos — "
                "no se importó nada de este archivo"
            ),
        )
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="No se pudo aplicar la importación — no se importó nada de este archivo",
        )

    return {
        "units_created": units_created,
        "references_created": references_created,
        "variants_created": variants_created,
        "invalid": len(parsed.errors) + len(plan.rows) - len(plan.valid),
        "batch_id": batch_id if units_created > 0 else None,
    }


@router.delete("/import/{batch_id}", response_model=ProductImportUndoResult)
def undo_product_import(
    batch_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Deshace un lote completo: las unidades **y** el catálogo que ese archivo
    creó al pasar (Referencias nuevas, variantes, y el Directorio autocreado).

    **Las unidades vendidas bloquean el undo, a propósito.** Un `Item` citado
    por una línea de factura no se puede borrar (`BillItem.item_id` es FK
    restrictiva, D-35/D-60) y tampoco debería: la factura es un documento
    inmutable y la unidad que vendió tiene que seguir existiendo. Se responde
    409 sin borrar nada, mismo criterio "todo o nada" que el undo de
    Referencias.

    El Directorio autocreado se borra **al final y solo si nadie más lo usa**:
    que el usuario le haya asignado ese proveedor a otra cosa después no es
    razón para negarle el undo entero.
    """
    items = db.execute(
        select(Item).where(Item.tenant_id == tenant_id, Item.import_batch_id == batch_id)
    ).scalars().all()
    references = db.execute(
        select(Reference).where(
            Reference.tenant_id == tenant_id, Reference.import_batch_id == batch_id
        )
    ).scalars().all()
    if not items and not references:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Lote no encontrado")

    #  Dos bloques con mensajes distintos y no un `try` que los cubra a los dos:
    #  fallan por razones opuestas y el usuario necesita saber cuál fue. Una
    #  unidad no se deja borrar porque una factura la cita; una Referencia no se
    #  deja borrar porque le quedan existencias de otro origen.
    try:
        for item in items:
            db.delete(item)
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=(
                "No se puede deshacer: alguna unidad del lote ya está vendida o "
                "referenciada por una factura"
            ),
        )

    try:
        for reference in references:
            db.delete(reference)
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=(
                "No se puede deshacer: alguna Referencia que creó este archivo ya "
                "tiene existencias de otra importación o de un alta manual"
            ),
        )

    directory_deleted = 0
    for model in (Provider, Location, Category):
        rows = db.execute(
            select(model).where(model.tenant_id == tenant_id, model.import_batch_id == batch_id)
        ).scalars().all()
        for row in rows:
            #  Savepoint por fila: si esta entidad ya la usa otro dato, se
            #  saltea y el undo sigue, en vez de tumbar todo por un proveedor
            #  que el usuario reutilizó después.
            try:
                with db.begin_nested():
                    db.delete(row)
                directory_deleted += 1
            except IntegrityError:
                continue

    db.commit()
    return {
        "units_deleted": len(items),
        "references_deleted": len(references),
        "directory_deleted": directory_deleted,
    }
