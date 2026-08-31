"""brand

Marca como entidad propia (docs/07-decisiones-y-puntos-abiertos.md, D-71),
en paralelo a `Reference.brand` (que sigue siendo texto libre, D-57 — no se
toca, no hay FK). La tabla nueva alimenta el Directorio (card + minitabla +
alta) y, a futuro, las sugerencias del formulario de Referencia.

Se hace *backfill* desde los valores distintos ya cargados en
`product_references.brand` para que el Directorio no arranque vacío el mismo
día que existen marcas reales en el catálogo — es una copia inicial, no un
vínculo: crear/editar una Referencia después de esta migración no toca
`brands`, y viceversa.

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-16

"""
import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "brands",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_brands_tenant_id", "brands", ["tenant_id"])

    connection = op.get_bind()
    distinct_brands = connection.execute(
        sa.text(
            "SELECT DISTINCT tenant_id, brand FROM product_references "
            "WHERE brand IS NOT NULL AND brand <> ''"
        )
    ).fetchall()

    if distinct_brands:
        brands_table = sa.table(
            "brands",
            sa.column("id", postgresql.UUID(as_uuid=True)),
            sa.column("tenant_id", postgresql.UUID(as_uuid=True)),
            sa.column("name", sa.String()),
            sa.column("created_at", sa.DateTime(timezone=True)),
            sa.column("updated_at", sa.DateTime(timezone=True)),
            sa.column("version", sa.Integer()),
        )
        now = datetime.now(timezone.utc)
        op.bulk_insert(
            brands_table,
            [
                {
                    "id": uuid.uuid4(),
                    "tenant_id": row.tenant_id,
                    "name": row.brand,
                    "created_at": now,
                    "updated_at": now,
                    "version": 1,
                }
                for row in distinct_brands
            ],
        )


def downgrade() -> None:
    op.drop_index("ix_brands_tenant_id", table_name="brands")
    op.drop_table("brands")
