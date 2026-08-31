import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import ImageResolver, get_db, get_image_resolver, get_tenant_id
from app.api.filters import contains as _contains
from app.core import sku as sku_utils
from app.core.images import (
    ALLOWED_IMAGE_EXTENSIONS,
    STATIC_IMAGES_DIR,
    invalidate_tenant_index,
    sanitize_sku,
)
from app.crud.base import CRUDBase
from app.exports import catalog as catalog_export
from app.imports import catalog as catalog_import
from app.models.category import Category
from app.models.provider import Provider
from app.models.reference import Reference
from app.schemas.common import Page
from app.schemas.reference import (
    ReferenceCreate,
    ReferenceImportPreview,
    ReferenceImportResult,
    ReferenceImportUndoResult,
    ReferenceRead,
    ReferenceSummary,
    ReferenceUpdate,
    ReferenceVariantInfo,
)

router = APIRouter(prefix="/references", tags=["references"])
crud = CRUDBase(Reference)

def _next_variant_sku(
    db: Session, tenant_id: uuid.UUID, base: str, reserved: set[str] | None = None
) -> str:
    """
    Siguiente código libre del grupo de variantes de `base` (D-90).

    El grupo son la pieza base y todo lo que arranque con `base#`. Se consulta
    el número más alto y se sigue de ahí — **no se cuenta**: si alguien borró
    la variante 2, contar daría 3 y chocaría con la que ya existe.

    `reserved` son los SKU comprometidos en la misma transacción pero todavía
    sin flush, invisibles para esta consulta.
    """
    prefix = base + sku_utils.VARIANT_SEPARATOR
    existing = set(
        db.execute(
            select(Reference.sku).where(
                Reference.tenant_id == tenant_id,
                or_(Reference.sku == base, Reference.sku.startswith(prefix, autoescape=True)),
            )
        ).scalars()
    ) | (reserved or set())

    highest = max(
        (sku_utils.variant_number(s) for s in existing if sku_utils.base_of(s) == base),
        default=1,
    )
    return sku_utils.variant_sku(base, max(highest + 1, sku_utils.FIRST_VARIANT_NUMBER))


def _serialize(reference: Reference, resolve_image: ImageResolver) -> ReferenceRead:
    """
    `Reference` → `ReferenceRead` con la imagen ya resuelta (D-84).

    Construye un modelo nuevo en vez de asignarle `reference.image_url = ...` al
    objeto ORM: mutar la instancia haría que SQLAlchemy persistiera la URL
    resuelta en el próximo flush, que es justo el error que D-84 vino a deshacer
    (la columna guarda solo la URL externa, nunca la local).
    """
    return ReferenceRead.model_validate(reference).model_copy(
        update={"image_url": resolve_image(reference.sku, reference.image_url)}
    )


def _reference_conditions(
    tenant_id: uuid.UUID,
    sku: str | None,
    title: str | None,
    search: str | None,
    category_id: uuid.UUID | None,
) -> list:
    """
    Filtros del catálogo, compartidos por el listado y la exportación.

    Van juntos a propósito: si la exportación armara su propio `WHERE`, el
    archivo podría no coincidir con lo que el usuario tiene en pantalla — y ese
    desajuste es invisible hasta que alguien compara fila por fila.
    """
    conditions = [Reference.tenant_id == tenant_id]
    if sku:
        conditions.append(Reference.sku.ilike(_contains(sku), escape="\\"))
    if title:
        conditions.append(Reference.title.ilike(_contains(title), escape="\\"))
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


@router.get("/", response_model=Page[ReferenceRead])
def list_references(
    skip: int = Query(0, ge=0, description="Registros a saltar"),
    limit: int = Query(50, ge=1, le=200, description="Máximo de registros por página"),
    sku: str | None = Query(None, description="Coincidencia parcial, ignora mayúsculas"),
    title: str | None = Query(None, description="Coincidencia parcial, ignora mayúsculas"),
    search: str | None = Query(None, description="Coincidencia parcial en SKU **o** nombre"),
    category_id: uuid.UUID | None = Query(None, description="Categoría exacta"),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    resolve_image: ImageResolver = Depends(get_image_resolver),
):
    """
    Listado paginado y filtrable de Referencias.

    Soporta la pantalla "CRUD Referencia" del MVP (docs/05-alcance-mvp-y-flujos.md,
    §2.1). Los filtros se combinan con AND y los de texto son parciales; `total`
    cuenta las filas que pasan el filtro, no las de la página devuelta.

    `search` existe aparte de `sku`/`title` porque une los dos con **OR**: en la
    caja registradora hay un solo campo de búsqueda y el cajero no sabe (ni
    debería) si lo que tiene en la mano es un código o un nombre — y con un
    escáner de barras es siempre un código. Combinar `sku` y `title` no sirve
    para eso: se cruzan con AND y exigirían que el término esté en los dos.
    """
    conditions = _reference_conditions(tenant_id, sku, title, search, category_id)

    total = db.execute(
        select(func.count()).select_from(Reference).where(*conditions)
    ).scalar_one()

    # El ORDER BY no es cosmético: sin un orden estable Postgres puede devolver
    # las filas en cualquier orden entre consultas, y una misma fila acabaría
    # repetida en dos páginas (o sin aparecer en ninguna). Se desempata por `id`
    # porque el SKU no es único a nivel de esquema.
    rows = (
        db.execute(
            select(Reference)
            .where(*conditions)
            .order_by(Reference.sku, Reference.id)
            .offset(skip)
            .limit(limit)
        )
        .scalars()
        .all()
    )

    return {
        "items": [_serialize(reference, resolve_image) for reference in rows],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/variants", response_model=ReferenceVariantInfo)
def reference_variants(
    sku: str = Query(..., description="SKU a consultar; puede ser el de la pieza base o el de una variante"),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Estado del grupo de variantes de un SKU (D-90) — lo que el formulario
    necesita para ofrecer "este código ya existe, ¿crear una variante?".

    Va en un endpoint propio y no dentro de `/lookup` a propósito: `lookup`
    devuelve `ReferenceRead` y lo consume media app (caja, edición,
    autocompletado). Colgarle campos de variante obligaría a todos esos
    consumidores a cargar con un dato que no miran.

    Acepta indistintamente el código base o el de una variante: se normaliza a
    la base antes de consultar, así el formulario no tiene que saber cuál le
    pegó el usuario.
    """
    #  `base_of` ANTES de normalizar, no al revés: `normalize_sku` convierte el
    #  `#` en `-` (D-90, para que la marca sea infalsificable desde la entrada),
    #  así que normalizar primero dejaría `VAR-DEMO#5` como base `VAR-DEMO-5` —
    #  un código que no existe— en vez de `VAR-DEMO`.
    base = sku_utils.normalize_sku(sku_utils.base_of(sku))
    if not base:
        return {"base_sku": "", "exists": False, "variant_count": 0, "next_sku": ""}

    prefix = base + sku_utils.VARIANT_SEPARATOR
    existing = [
        value
        for value in db.execute(
            select(Reference.sku).where(
                Reference.tenant_id == tenant_id,
                or_(Reference.sku == base, Reference.sku.startswith(prefix, autoescape=True)),
            )
        ).scalars()
        if sku_utils.base_of(value) == base
    ]

    return {
        "base_sku": base,
        "exists": bool(existing),
        #  Cuenta la pieza base junto con sus variantes: de cara al usuario el
        #  grupo son "3 variantes", no "la pieza y 2 variantes".
        "variant_count": len(existing),
        #  Se calcula igual que en la importación (`_next_variant_sku`): manda
        #  el número más alto, no el conteo — si alguien borró la 2, contar
        #  daría 3 y chocaría contra la que ya existe.
        "next_sku": _next_variant_sku(db, tenant_id, base) if existing else base,
    }


@router.get("/lookup", response_model=Optional[ReferenceRead])
def lookup_reference(
    sku: str = Query(..., description="SKU exacto a buscar"),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    resolve_image: ImageResolver = Depends(get_image_resolver),
):
    """
    Autocompletado de Referencia por SKU.

    Soporta la pantalla "Registrar Pago" del MVP (docs/05-alcance-mvp-y-flujos.md,
    §2): si la Referencia existe, el cliente la usa para autocompletar el
    formulario; si no existe, responde `null` (200) en vez de un 404, ya que
    "no encontrado" es un resultado válido y esperado del autocompletado.
    """
    stmt = select(Reference).where(Reference.tenant_id == tenant_id, Reference.sku == sku)
    reference = db.execute(stmt).scalar_one_or_none()
    return None if reference is None else _serialize(reference, resolve_image)


@router.get("/summary", response_model=ReferenceSummary)
def reference_summary(
    latest: int = Query(5, ge=1, le=20, description="Cuántas referencias recientes devolver"),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Agregados del catálogo para las cards de resumen de la pantalla Referencias.

    Va aparte del listado porque son datos que la paginación no puede dar: el
    listado devuelve una página ordenada por SKU, no el catálogo completo.

    `total_brands` cuenta marcas **distintas y no nulas** (`brand` es opcional,
    D-57). `last_updated_at` es el máximo `updated_at`, así que se mueve tanto al
    crear una referencia como al editarle la marca — no hace falta un timestamp
    aparte porque la marca es una columna de `Reference`, no una tabla propia.
    """
    scoped = Reference.tenant_id == tenant_id

    totals = db.execute(
        select(
            func.count(Reference.id),
            func.count(func.distinct(Reference.brand)),
            func.max(Reference.updated_at),
        ).where(scoped)
    ).one()

    latest_rows = (
        db.execute(
            select(Reference)
            .where(scoped)
            # Desempate por `id`: sin él, dos referencias creadas en el mismo
            # instante podrían alternar de orden entre llamadas.
            .order_by(Reference.created_at.desc(), Reference.id.desc())
            .limit(latest)
        )
        .scalars()
        .all()
    )

    return {
        "total_references": totals[0],
        "total_brands": totals[1],
        "last_updated_at": totals[2],
        "latest": latest_rows,
    }


@router.get("/export")
def export_references(
    export_format: str = Query(
        "json", alias="format", pattern="^(json|xlsx|markdown)$", description="json | xlsx | markdown"
    ),
    sku: str | None = Query(None),
    title: str | None = Query(None),
    search: str | None = Query(None),
    category_id: uuid.UUID | None = Query(None),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Exporta el catálogo como archivo descargable (D-73).

    Acepta los **mismos filtros que el listado**: mandarlos exporta lo que el
    usuario está viendo, omitirlos exporta el catálogo completo. No hay un
    parámetro `scope` aparte porque sería un segundo lugar donde decidir lo
    mismo.

    **Un catálogo vacío no es un error:** se responde igual, con cabeceras y
    descriptores de columna y sin filas, que es exactamente la plantilla que le
    sirve al usuario para saber qué se espera de cada campo.

    Las FKs salen resueltas por **nombre** (proveedor, categoría) y nunca como
    UUID: un identificador local no significa nada en otra instalación (D-42).
    El `JOIN` a `Provider` es interno porque `provider_id` es obligatorio; el de
    `Category` es externo porque es nullable — con un `JOIN` interno las
    Referencias sin categoría desaparecerían del archivo sin avisar.
    """
    conditions = _reference_conditions(tenant_id, sku, title, search, category_id)

    rows = db.execute(
        select(Reference, Provider.title, Category.name)
        .select_from(Reference)
        .join(Provider, Provider.id == Reference.provider_id)
        .outerjoin(Category, Category.id == Reference.category_id)
        .where(*conditions)
        .order_by(Reference.sku, Reference.id)
    ).all()

    payload = catalog_export.build_payload(rows)
    render, media_type, extension = catalog_export.RENDERERS[export_format]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")

    return Response(
        content=render(payload),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="referencias-{stamp}.{extension}"',
            #  Sin esto el navegador no deja leer el nombre del archivo desde JS
            #  (CORS oculta todas las cabeceras que no estén expuestas), y la
            #  descarga terminaría con un nombre inventado por el cliente.
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.post("/import/preview", response_model=ReferenceImportPreview)
async def preview_reference_import(
    file: UploadFile = File(
        ..., description="Catálogo en JSON o Excel (.xlsx) — el mismo que produce GET /references/export"
    ),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Cuenta qué haría la importación **sin escribir nada** (D-73/D-42: previsualización
    obligatoria antes de aplicar). Acepta el JSON canónico o el .xlsx exportado
    por el propio sistema (D-74) — nunca un Excel de otro origen ni markdown,
    esos no tienen round-trip fiel.
    """
    content = await file.read()
    try:
        body = catalog_import.read_upload(file.filename or "", file.content_type or "", content)
        parsed = catalog_import.parse_payload(body)
    except catalog_import.ImportFormatError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))

    row_skus = {row.sku for row in parsed.rows}
    dupes = catalog_import.existing_skus(db, tenant_id, list(row_skus))
    #  Ordenados por aparición en el archivo (no `set`): la primera grafía es la
    #  que `resolve()` va a guardar, así que es la que hay que anunciar.
    provider_names = list(dict.fromkeys(row.provider_name for row in parsed.rows))
    category_names = list(
        dict.fromkeys(row.category_name for row in parsed.rows if row.category_name)
    )
    #  Sin escribir nada: previsualizar solo pregunta.
    indexes = catalog_import.build_indexes(db, tenant_id)

    return {
        "total_rows": len(parsed.rows) + len(parsed.errors),
        "new_count": len(parsed.rows) - len(dupes),
        "existing_skus": sorted(dupes),
        "invalid": [
            {"index": e.index, "sku": e.sku, "reason": e.reason} for e in parsed.errors
        ],
        #  Comparación **plegada**, no `.lower()` (`app/core/text.py:fold`): un
        #  `HONDA` del archivo contra un `Honda` de la base no es un proveedor
        #  nuevo, y `Pírelli`/`Pirelli` tampoco son dos.
        "new_providers": sorted(indexes["provider"].missing(provider_names)),
        "new_categories": sorted(indexes["category"].missing(category_names)),
        #  Solo presentes cuando el archivo es .xlsx (D-74): el JSON no tiene
        #  encabezados que detectar.
        "columns_detected": body.get("columns_detected"),
        "columns_missing": body.get("columns_missing"),
        "columns_ignored": body.get("columns_ignored"),
    }


@router.post("/import", response_model=ReferenceImportResult, status_code=status.HTTP_201_CREATED)
async def commit_reference_import(
    file: UploadFile = File(..., description="Mismo archivo que /import/preview — JSON o .xlsx"),
    skip_existing: bool = Query(
        True, description="SKU ya existente: saltarlo (default, D-73) o traerlo igual como duplicado"
    ),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Aplica la importación. **Suma, no reemplaza** (nivel 3 de D-73): cada fila
    válida crea una Referencia nueva, nunca actualiza una existente. Proveedor y
    Categoría se resuelven por nombre y se autocrean si el negocio no los tenía
    (mismo criterio que D-42 para Categoría).

    Todas las filas creadas quedan marcadas con el mismo `batch_id`, que es lo
    que habilita deshacer el lote entero con `DELETE /import/{batch_id}` — sin
    esa marca, un archivo mal armado queda indistinguible del catálogo real en
    cuanto entra.
    """
    content = await file.read()
    try:
        body = catalog_import.read_upload(file.filename or "", file.content_type or "", content)
        parsed = catalog_import.parse_payload(body)
    except catalog_import.ImportFormatError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))

    if not parsed.rows:
        return {"created": 0, "skipped": 0, "invalid": len(parsed.errors), "batch_id": None}

    dupes = catalog_import.existing_skus(db, tenant_id, [row.sku for row in parsed.rows])
    batch_id = uuid.uuid4()
    #  Índices por nombre plegado (`app/imports/names.py`), armados una vez: dos
    #  consultas en vez de una por nombre distinto, y dos grafías del mismo
    #  proveedor en el mismo archivo caen en un solo registro.
    indexes = catalog_import.build_indexes(db, tenant_id)
    #  Mismo criterio que el importador de Productos: `brand` es texto libre
    #  (D-57), así que la grafía ya conocida gana sobre la del archivo.
    brands = catalog_import.build_brand_canonicalizer(db, tenant_id)
    created = 0
    skipped = 0
    #  SKU ya comprometidos en ESTA corrida. Las filas nuevas todavía no están
    #  en la BBDD (no hay flush hasta el commit), así que sin este registro dos
    #  filas del mismo archivo con el mismo código elegirían el mismo número de
    #  variante y chocarían contra el índice único.
    reserved: set[str] = set()

    for row in parsed.rows:
        sku = row.sku
        if sku in dupes or sku in reserved:
            if skip_existing:
                skipped += 1
                continue
            #  "Traerlo igual" ya no puede significar "crear un duplicado"
            #  (D-90: el índice único lo impide, y era lo que reventaba el
            #  `lookup` de la caja). Significa crear una **variante**: misma
            #  base de código, número propio, Referencia completa y editable.
            sku = _next_variant_sku(db, tenant_id, sku_utils.base_of(sku), reserved)
        reserved.add(sku)
        provider = indexes["provider"].resolve(row.provider_name)
        category = indexes["category"].resolve(row.category_name)
        db.add(
            Reference(
                tenant_id=tenant_id,
                provider_id=provider.id,
                category_id=category.id if category else None,
                sku=sku,
                title=row.title,
                brand=brands.canonical(row.brand),
                description=row.description,
                image_url=row.image_url,
                base_price=row.base_price,
                iva_percentage=row.iva_percentage,
                provider_price=row.provider_price,
                import_batch_id=batch_id,
            )
        )
        created += 1

    db.commit()
    return {
        "created": created,
        "skipped": skipped,
        "invalid": len(parsed.errors),
        "batch_id": batch_id if created > 0 else None,
    }


@router.delete("/import/{batch_id}", response_model=ReferenceImportUndoResult)
def undo_reference_import(
    batch_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Deshace un lote completo: borra todas las Referencias que quedaron marcadas
    con ese `import_batch_id`.

    **Todo o nada.** Si alguna Referencia del lote ya tiene Ítems de inventario
    asociados (D-41), Postgres rechaza su DELETE (`Item.reference_id` es FK
    restrictiva) y se revierte el lote entero — dejar el resto a medio deshacer
    sería más confuso que negarse: el usuario borra a mano desde Referencias lo
    que sí puede, con contexto de qué unidades tiene esa fila.
    """
    refs = db.execute(
        select(Reference).where(
            Reference.tenant_id == tenant_id, Reference.import_batch_id == batch_id
        )
    ).scalars().all()
    if not refs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado")

    try:
        for reference in refs:
            db.delete(reference)
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "No se puede deshacer: alguna referencia del lote ya tiene "
                "ítems de inventario asociados"
            ),
        )
    db.commit()
    return {"deleted": len(refs)}


@router.post("/", response_model=ReferenceRead, status_code=status.HTTP_201_CREATED)
def create_reference(
    payload: ReferenceCreate,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    resolve_image: ImageResolver = Depends(get_image_resolver),
):
    try:
        obj = crud.create(db, tenant_id, payload.model_dump())
    except IntegrityError:
        #  El índice único `(tenant_id, sku)` de D-90. Se traduce a 409 con un
        #  mensaje que nombra el camino correcto —crear una variante— en vez
        #  del 500 crudo que daría la excepción sin atrapar.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una referencia con el SKU '{payload.sku}'. Creála como variante.",
        )
    return _serialize(obj, resolve_image)


@router.post("/images/{sku}")
async def upload_reference_image(
    sku: str,
    file: UploadFile = File(...),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Guarda la imagen de una Referencia nombrada por SKU (D-58) — medida temporal
    de desarrollo mientras no exista el wrapper Tauri (D-40): el archivo se sirve
    desde el propio backend en vez de `appDataDir`, solo para poder probar el
    flujo end-to-end sin empaquetar la app de escritorio. Independiente de si la
    Referencia ya existe como fila en la BBDD — se identifica solo por SKU.

    **No devuelve una URL para guardar en `image_url`** (D-84): dejar el archivo
    en disco con el nombre del SKU **es** el acto de asociarlo, y de ahí en
    adelante `resolve_image_url()` lo encuentra solo. Persistir además la URL
    era lo que metía `http://localhost:8000/...` en la BBDD y rompía las
    imágenes en el resto de las máquinas de la LAN.
    """
    extension = Path(file.filename or "").suffix.lower() or ".jpg"
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato no soportado: {extension}",
        )

    tenant_dir = STATIC_IMAGES_DIR / str(tenant_id)
    tenant_dir.mkdir(parents=True, exist_ok=True)
    destination = tenant_dir / f"{sanitize_sku(sku)}{extension}"
    destination.write_bytes(await file.read())
    #  Sin esto, el índice cacheado seguiría diciendo "no hay imagen local" por
    #  hasta 5 s — justo al volver de subirla, que es cuando se mira.
    invalidate_tenant_index(tenant_id)

    return {"url": f"/static/images/{tenant_id}/{destination.name}"}


@router.get("/{reference_id}", response_model=ReferenceRead)
def get_reference(
    reference_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    resolve_image: ImageResolver = Depends(get_image_resolver),
):
    obj = crud.get(db, tenant_id, reference_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference not found")
    return _serialize(obj, resolve_image)


@router.put("/{reference_id}", response_model=ReferenceRead)
def update_reference(
    reference_id: uuid.UUID,
    payload: ReferenceUpdate,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    resolve_image: ImageResolver = Depends(get_image_resolver),
):
    try:
        obj = crud.update(db, tenant_id, reference_id, payload.model_dump())
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe otra referencia con el SKU '{payload.sku}'.",
        )
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference not found")
    return _serialize(obj, resolve_image)


@router.delete("/{reference_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reference(
    reference_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    try:
        deleted = crud.delete(db, tenant_id, reference_id)
    except IntegrityError:
        # `Item.reference_id` es FK restrictiva (sin cascade): si hay Ítems
        # apuntando a esta Referencia, Postgres rechaza el DELETE.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar: la referencia tiene ítems de inventario asociados",
        )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference not found")
