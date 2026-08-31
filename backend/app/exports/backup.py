"""
Respaldo del proyecto completo como archivo SQLite (D-77, nivel 1 de D-73).

A diferencia del export de catálogo/Directorio —que es por entidad y sirve
para mover datos maestros entre instalaciones— esto vuelca **todo el negocio
en un solo archivo**, facturas incluidas. Es el "exportar proyecto completo"
que D-73 describía como nivel 1.

**SQLite y no JSON** porque D-73 ya lo fijó así y porque es el formato al que
apunta la arquitectura objetivo (D-01/D-02: SQLite local como fuente de
verdad). `sqlite3` es stdlib — no suma dependencias al backend.

Tres reglas que no son negociables acá:

1. **Todo va filtrado por `tenant_id`.** La base es multi-tenant (D-23): un
   volcado crudo tipo `pg_dump` exportaría los datos de *todos* los negocios
   dentro del archivo que se descarga un cliente. Cada consulta de este módulo
   lleva su filtro; no hay una sola tabla que se copie entera.
2. **`users.password_hash` NO se exporta.** Es un archivo que el usuario baja a
   su disco: meter ahí los hashes de las credenciales de los asientos regala
   material para un ataque offline sin ganar nada — un respaldo de datos de
   negocio no necesita las contraseñas.
3. **La plata viaja como TEXT.** SQLite no tiene tipo decimal; guardar
   `Numeric` como REAL lo pasaría por punto flotante y rompería la exactitud
   que exige el proyecto (D-05, zona de alto riesgo de CLAUDE.md).

⚠️ **El archivo sale SIN cifrar.** SQLCipher (D-06) es parte del modelo de
seguridad objetivo pero todavía no está implementado, así que este respaldo
contiene toda la información financiera del negocio en claro. La UI lo
advierte explícitamente (D-77) en vez de dejar que el usuario lo asuma.
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import Boolean, Integer, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.bill import Bill
from app.models.bill_item import BillItem
from app.models.brand import Brand
from app.models.category import Category
from app.models.customer import Customer
from app.models.item import Item
from app.models.location import Location
from app.models.provider import Provider
from app.models.reference import Reference
from app.models.tenant import Tenant
from app.models.user import User

#  Versión del formato del respaldo, independiente de `platform_version`
#  (D-76) y del `format_version` de los export por entidad (D-73): éste
#  versiona la estructura de ESTE archivo.
BACKUP_FORMAT_VERSION = 1

#  Columnas que nunca salen del servidor, por tabla.
EXCLUDED_COLUMNS: dict[str, set[str]] = {"users": {"password_hash"}}

#  Orden de volcado = orden de dependencias (padres antes que hijos), para que
#  el archivo se pueda leer/restaurar de arriba a abajo sin violar FKs.
#  `Tenant` filtra por `id` porque es la propia fila del negocio; el resto
#  filtra por `tenant_id`.
TABLES: tuple[tuple[str, type], ...] = (
    ("tenants", Tenant),
    ("users", User),
    ("providers", Provider),
    ("categories", Category),
    ("locations", Location),
    ("brands", Brand),
    ("customers", Customer),
    ("product_references", Reference),
    ("items", Item),
    ("bills", Bill),
    ("bill_items", BillItem),
)


def _sqlite_type(column) -> str:
    """
    Afinidad SQLite de cada columna. Todo lo que no es entero/booleano cae a
    TEXT **a propósito**: `Numeric` como TEXT preserva el decimal exacto, y
    las fechas/UUID como texto ISO son legibles con cualquier visor de SQLite.
    """
    if isinstance(column.type, Boolean):
        return "INTEGER"
    if isinstance(column.type, Integer):
        return "INTEGER"
    return "TEXT"


def _to_sqlite_value(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (uuid.UUID, Decimal)):
        #  Decimal → str y no float: es la línea que mantiene la exactitud
        #  del dinero al cruzar a un motor que no tiene tipo decimal.
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _schema_revision(db: Session) -> str | None:
    """Revisión de Alembic del esquema que produjo este respaldo — sirve para diagnosticar compatibilidad (D-76)."""
    try:
        return db.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
    except Exception:
        return None


def build_backup(db: Session, tenant_id: uuid.UUID) -> tuple[bytes, dict]:
    """
    Devuelve `(bytes del archivo .sqlite, resumen de conteos por tabla)`.

    El resumen se usa para confirmarle al usuario qué se llevó — un archivo
    binario del que solo se sabe el peso no le dice a nadie si el respaldo
    salió completo.
    """
    tenant = db.execute(select(Tenant).where(Tenant.id == tenant_id)).scalar_one_or_none()
    counts: dict[str, int] = {}

    with TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / "backup.sqlite"
        connection = sqlite3.connect(path)
        try:
            for table_name, model in TABLES:
                columns = [
                    column
                    for column in model.__table__.columns
                    if column.name not in EXCLUDED_COLUMNS.get(table_name, set())
                ]
                column_defs = ", ".join(f'"{c.name}" {_sqlite_type(c)}' for c in columns)
                connection.execute(f'CREATE TABLE "{table_name}" ({column_defs})')

                scope = (
                    model.id == tenant_id if table_name == "tenants" else model.tenant_id == tenant_id
                )
                rows = db.execute(select(model).where(scope)).scalars().all()

                placeholders = ", ".join("?" for _ in columns)
                column_names = ", ".join(f'"{c.name}"' for c in columns)
                connection.executemany(
                    f'INSERT INTO "{table_name}" ({column_names}) VALUES ({placeholders})',
                    [
                        tuple(_to_sqlite_value(getattr(row, c.name)) for c in columns)
                        for row in rows
                    ],
                )
                counts[table_name] = len(rows)

            #  Metadata del propio respaldo: sin esto, un archivo suelto no
            #  dice de qué negocio es, cuándo se sacó ni con qué versión —
            #  justo lo que hace falta para diagnosticar (D-76).
            connection.execute(
                'CREATE TABLE "_backup_metadata" ("key" TEXT, "value" TEXT)'
            )
            connection.executemany(
                'INSERT INTO "_backup_metadata" ("key", "value") VALUES (?, ?)',
                [
                    ("backup_format_version", str(BACKUP_FORMAT_VERSION)),
                    ("platform_version", settings.app_version),
                    ("schema_revision", _schema_revision(db) or "unknown"),
                    ("exported_at", datetime.now(timezone.utc).isoformat()),
                    ("tenant_id", str(tenant_id)),
                    ("business_name", tenant.business_name if tenant else "unknown"),
                    ("encrypted", "false"),
                ],
            )
            connection.commit()
        finally:
            connection.close()

        return path.read_bytes(), counts
