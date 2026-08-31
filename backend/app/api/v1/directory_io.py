"""
Export/import genérico para las entidades de soporte del Directorio (D-75):
Proveedor, Ubicación, Categoría, Cliente, Marca. Mismo patrón que Referencia
(D-73/D-74) — tres formatos de salida, JSON/Excel como puertas de entrada,
previsualización obligatoria, unicidad blanda por clave natural, lote
deshacible — pero **sin resolución de FKs**: a diferencia de Referencia
(Proveedor/Categoría por nombre), ninguna de las cinco entidades de soporte
tiene una relación que resolver, así que un solo router parametrizado por
`entity` alcanza para las cinco en vez de cinco copias casi idénticas.
"""
from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_tenant_id
from app.core.config import settings
from app.core.nit import normalize_nit
from app.core.text import fold
from app.exports.generic import Column, build_payload, build_renderers
from app.imports import generic as generic_import
from app.models.brand import Brand
from app.models.category import Category
from app.models.customer import Customer
from app.models.location import Location
from app.models.provider import Provider

FORMAT_VERSION = 1
#  Únicos valores válidos de `Location.type` (CHECK `ck_locations_type`,
#  migración 0001, D-25) — ninguna otra entidad del Directorio tiene un campo
#  restringido, así que esto se queda como caso especial acá y no en el motor
#  genérico.
LOCATION_TYPES = {"sucursal", "bodega"}


@dataclass(frozen=True)
class EntitySpec:
    key: str
    kind: str
    model: type
    columns: tuple[Column, ...]
    #  Columna usada como clave natural para detectar "ya existe" — unicidad
    #  blanda (D-73): nunca bloquea la importación, solo la reporta.
    natural_key: str
    title: str
    filename: str
    #  Cómo se compara esa clave. Por defecto `fold` (D-93): nombres sin
    #  mayúsculas, tildes ni espacios de sobra. Cliente es la excepción y usa
    #  `normalize_nit`, porque su clave no es un nombre sino un documento —
    #  ver `ENTITY_SPECS` y D-94.
    key_normalizer: Callable[[Optional[str]], str] = fold


#  Encabezados en minúscula y sin tildes (D-87), igual que el catálogo de
#  Referencias. Cada columna acepta además su `key` como encabezado, así que
#  las 5 entidades del Directorio quedan importables desde una integración en
#  inglés sin declarar un alias por columna.
PROVIDER_COLUMNS: tuple[Column, ...] = (
    Column("title", "nombre", aliases=("titulo",), required=True, width=30),
    Column("provider_code", "codigo", width=16),
    Column("nit", "nit", width=16),
    Column("description", "descripcion", width=40),
)

LOCATION_COLUMNS: tuple[Column, ...] = (
    Column("name", "nombre", required=True, width=24),
    Column("type", "tipo (sucursal/bodega)", aliases=("tipo",), required=True, width=20),
    Column("address", "direccion", width=36),
)

CATEGORY_COLUMNS: tuple[Column, ...] = (
    Column("name", "nombre", required=True, width=24),
    Column("description", "descripcion", width=40),
    Column("icon", "icono", width=16),
)

CUSTOMER_COLUMNS: tuple[Column, ...] = (
    Column("fullname", "nombre", required=True, width=30),
    Column("nit", "cedula/nit", aliases=("nit", "cedula"), width=18),
    Column("mail", "correo", aliases=("email",), width=28),
)

BRAND_COLUMNS: tuple[Column, ...] = (
    Column("name", "nombre", required=True, width=24),
    Column("description", "descripcion", width=40),
)

ENTITY_SPECS: dict[str, EntitySpec] = {
    "providers": EntitySpec(
        "providers", "directory.providers", Provider, PROVIDER_COLUMNS, "title", "Proveedores", "proveedores"
    ),
    "locations": EntitySpec(
        "locations", "directory.locations", Location, LOCATION_COLUMNS, "name", "Ubicaciones", "ubicaciones"
    ),
    "categories": EntitySpec(
        "categories", "directory.categories", Category, CATEGORY_COLUMNS, "name", "Categorías", "categorias"
    ),
    #  **Cliente se identifica por el NIT, no por el nombre** (D-94), y es la
    #  única de las cinco. Dos personas distintas se llaman igual con toda
    #  naturalidad, así que deduplicar por `fullname` —como se hacía— borraba
    #  clientes reales de un archivo; en cambio el mismo documento repetido es
    #  siempre la misma persona. Sin NIT no se deduplica: la fila entra igual.
    "customers": EntitySpec(
        "customers", "directory.customers", Customer, CUSTOMER_COLUMNS, "nit", "Clientes",
        "clientes", key_normalizer=normalize_nit,
    ),
    "brands": EntitySpec(
        "brands", "directory.brands", Brand, BRAND_COLUMNS, "name", "Marcas", "marcas"
    ),
}


def _spec(entity: str) -> EntitySpec:
    spec = ENTITY_SPECS.get(entity)
    if spec is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Entidad de Directorio desconocida: {entity!r}")
    return spec


def _serialize(value, column: Column):
    if value is None:
        return None
    if column.numeric and isinstance(value, Decimal):
        return str(value.quantize(Decimal("0.01")))
    return value


def _validate_location_rows(entity: str, result: generic_import.ParseResult) -> None:
    """
    Único caso especial del motor genérico: `Location.type` tiene un `CHECK`
    en base (`ck_locations_type`, D-25) que solo acepta `sucursal`/`bodega` en
    minúscula. Sin esto, "Sucursal" tecleado en Excel pasa el parseo genérico
    y recién revienta en el `commit` con un `IntegrityError` que tumba el lote
    entero — mejor detectarlo acá y reportarlo como fila inválida, como
    cualquier otro dato mal tipeado.
    """
    if entity != "locations":
        return
    kept = []
    for row in result.rows:
        raw_type = (row.get("type") or "").strip().lower()
        if raw_type not in LOCATION_TYPES:
            result.errors.append(
                generic_import.RowError(
                    -1, row.get("name"), f"tipo inválido {row.get('type')!r} (solo 'sucursal' o 'bodega')"
                )
            )
            continue
        row["type"] = raw_type
        kept.append(row)
    result.rows = kept


router = APIRouter(prefix="/directory", tags=["directory"])


@router.get("/{entity}/export")
def export_entity(
    entity: str,
    export_format: str = Query("json", alias="format", pattern="^(json|xlsx|markdown)$"),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """Mismo contrato que `GET /references/export` (D-73), aplicado a una entidad de soporte."""
    spec = _spec(entity)
    rows = db.execute(
        select(spec.model)
        .where(spec.model.tenant_id == tenant_id)
        .order_by(spec.model.created_at.desc(), spec.model.id.desc())
    ).scalars().all()

    items = [
        {column.key: _serialize(getattr(row, column.key), column) for column in spec.columns}
        for row in rows
    ]
    payload = build_payload(items, spec.columns, spec.kind, FORMAT_VERSION, settings.app_version)
    renderers = build_renderers(spec.columns, sheet_title=spec.title, markdown_title=spec.title)
    render, media_type, extension = renderers[export_format]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")

    return Response(
        content=render(payload),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{spec.filename}-{stamp}.{extension}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.post("/{entity}/import/preview")
async def preview_entity_import(
    entity: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    spec = _spec(entity)
    content = await file.read()
    try:
        body = generic_import.read_upload(
            file.filename or "", file.content_type or "", content, spec.columns, spec.kind, FORMAT_VERSION
        )
        parsed = generic_import.parse_payload(body, spec.columns, spec.kind, FORMAT_VERSION, spec.natural_key)
    except generic_import.ImportFormatError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(error))
    _validate_location_rows(entity, parsed)

    key_attr = getattr(spec.model, spec.natural_key)
    row_keys = {row[spec.natural_key] for row in parsed.rows if row.get(spec.natural_key)}
    existing_folded = generic_import.find_existing_keys(
        db, tenant_id, spec.model, key_attr, row_keys, spec.key_normalizer
    )
    existing_in_payload = {v for v in row_keys if spec.key_normalizer(v) in existing_folded}

    #  Se cuenta recorriendo las filas igual que el commit, y no restando
    #  conjuntos: con la comparación plegada, un archivo que trae `Honda` y
    #  `HONDA` crea UNA marca, así que restar "claves distintas que ya existen"
    #  prometería dos. El `skipped` del commit sale de la misma cuenta.
    reserved: set[str] = set()
    new_count = 0
    for row in parsed.rows:
        key_value = row.get(spec.natural_key)
        folded = spec.key_normalizer(key_value) if key_value else None
        if folded and (folded in existing_folded or folded in reserved):
            continue
        if folded:
            reserved.add(folded)
        new_count += 1

    return {
        "total_rows": len(parsed.rows) + len(parsed.errors),
        "new_count": new_count,
        "existing_keys": sorted(existing_in_payload),
        "invalid": [
            {"index": e.index, "key_value": e.key_value, "reason": e.reason} for e in parsed.errors
        ],
    }


@router.post("/{entity}/import", status_code=status.HTTP_201_CREATED)
async def commit_entity_import(
    entity: str,
    file: UploadFile = File(...),
    skip_existing: bool = Query(True, description="Clave ya existente: saltarla (default) o traerla igual como duplicado"),
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    spec = _spec(entity)
    content = await file.read()
    try:
        body = generic_import.read_upload(
            file.filename or "", file.content_type or "", content, spec.columns, spec.kind, FORMAT_VERSION
        )
        parsed = generic_import.parse_payload(body, spec.columns, spec.kind, FORMAT_VERSION, spec.natural_key)
    except generic_import.ImportFormatError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(error))
    _validate_location_rows(entity, parsed)

    if not parsed.rows:
        return {"created": 0, "skipped": 0, "invalid": len(parsed.errors), "batch_id": None}

    key_attr = getattr(spec.model, spec.natural_key)
    row_keys = {row[spec.natural_key] for row in parsed.rows if row.get(spec.natural_key)}
    existing_folded = generic_import.find_existing_keys(
        db, tenant_id, spec.model, key_attr, row_keys, spec.key_normalizer
    )

    batch_id = uuid.uuid4()
    created = 0
    skipped = 0
    #  Claves ya comprometidas por ESTA corrida. Sin esto, un archivo con
    #  `Honda` y `HONDA` creaba dos Marcas: el chequeo de arriba mira la BBDD,
    #  donde ninguna de las dos existe todavía. Es el mismo motivo por el que
    #  la comparación es plegada y no `.lower()` — la redundancia que entra por
    #  el propio archivo cuenta igual que la que entra contra lo ya guardado.
    reserved: set[str] = set()
    for row in parsed.rows:
        key_value = row.get(spec.natural_key)
        folded = spec.key_normalizer(key_value) if key_value else None
        if skip_existing and folded and (folded in existing_folded or folded in reserved):
            skipped += 1
            continue
        if folded:
            reserved.add(folded)
        db.add(spec.model(tenant_id=tenant_id, import_batch_id=batch_id, **row))
        created += 1

    try:
        db.commit()
    except IntegrityError:
        #  Red de seguridad genérica (hoy solo `Location.type` tiene un CHECK,
        #  y ya se filtra antes en `_validate_location_rows`; esto cubre
        #  cualquier restricción de base futura sin tener que anticiparla acá).
        db.rollback()
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Alguna fila no cumple una restricción de la base de datos — no se importó nada de este archivo",
        )

    return {
        "created": created,
        "skipped": skipped,
        "invalid": len(parsed.errors),
        "batch_id": batch_id if created > 0 else None,
    }


@router.delete("/{entity}/import/{batch_id}")
def undo_entity_import(
    entity: str,
    batch_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """Mismo criterio que `DELETE /references/import/{batch_id}` (D-73): todo o nada."""
    spec = _spec(entity)
    rows = db.execute(
        select(spec.model).where(spec.model.tenant_id == tenant_id, spec.model.import_batch_id == batch_id)
    ).scalars().all()
    if not rows:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Lote no encontrado")

    try:
        for row in rows:
            db.delete(row)
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="No se puede deshacer: algún registro del lote ya está referenciado por otro dato",
        )
    db.commit()
    return {"deleted": len(rows)}
