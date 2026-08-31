"""
Respaldo del proyecto completo (D-77) — nivel 1 de los tres de D-73.

Dos endpoints: uno que **cuenta sin construir nada** (para que el diálogo de
confirmación muestre qué se va a llevar antes de descargar) y otro que arma y
entrega el archivo. Misma forma que el resto de importaciones/exportaciones
del sistema: previsualizar primero, confirmar después.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_tenant_id
from app.core.config import settings
from app.exports import backup as backup_export
from app.models.tenant import Tenant

router = APIRouter(prefix="/backup", tags=["backup"])

#  Etiquetas legibles para el resumen del diálogo — las claves son nombres de
#  tabla, que no se le muestran a un dueño de mostrador.
TABLE_LABELS: dict[str, str] = {
    "tenants": "Negocio",
    "users": "Usuarios",
    "providers": "Proveedores",
    "categories": "Categorías",
    "locations": "Ubicaciones",
    "brands": "Marcas",
    "customers": "Clientes",
    "product_references": "Referencias",
    "items": "Productos (unidades)",
    "bills": "Facturas",
    "bill_items": "Líneas de factura",
}


def _slugify(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower() or "negocio"


@router.get("/summary")
def backup_summary(
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Cuenta qué entraría en el respaldo **sin construir el archivo**: el
    diálogo lo usa para que el usuario vea el alcance real (incluidas las
    facturas) antes de confirmar una descarga que sale sin cifrar.
    """
    counts = []
    for table_name, model in backup_export.TABLES:
        scope = model.id == tenant_id if table_name == "tenants" else model.tenant_id == tenant_id
        total = db.execute(select(func.count()).select_from(model).where(scope)).scalar_one()
        counts.append({"table": table_name, "label": TABLE_LABELS.get(table_name, table_name), "count": total})

    tenant = db.execute(select(Tenant).where(Tenant.id == tenant_id)).scalar_one_or_none()
    return {
        "business_name": tenant.business_name if tenant else "—",
        "platform_version": settings.app_version,
        #  Se declara explícito para que el frontend no tenga que asumirlo:
        #  el día que SQLCipher entre (D-06), esto pasa a `true` y la
        #  advertencia de la UI se apaga sola.
        "encrypted": False,
        "counts": counts,
    }


@router.get("/export")
def export_backup(
    db: Session = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """
    Arma y entrega el respaldo completo del negocio como archivo SQLite.

    Todo sale filtrado por el `tenant_id` del token — nunca por un parámetro
    del cliente: es lo que impide que un negocio se lleve los datos de otro
    en un sistema multi-tenant (D-23).
    """
    content, _counts = backup_export.build_backup(db, tenant_id)

    tenant = db.execute(select(Tenant).where(Tenant.id == tenant_id)).scalar_one_or_none()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    slug = _slugify(tenant.business_name if tenant else "negocio")
    filename = f"tiendapi-respaldo-{slug}-{stamp}.sqlite"

    return Response(
        content=content,
        media_type="application/vnd.sqlite3",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
