"""item.iva_percentage / item.provider_price — overrides por unidad

Caso de negocio real: dos unidades de la misma Referencia pueden venir de
lotes de compra distintos, a costos distintos, y a veces con un ajuste de IVA
puntual. Ambas columnas son NULLABLE a propósito — `NULL` significa "sigue el
catálogo" (`COALESCE` en el endpoint), no "cero". Solo se materializa un valor
propio cuando alguien edita esa unidad puntual desde el modal de edición.

`base_price` NO se agrega acá — nadie pidió que el precio base varíe por
unidad, y el desglose de IVA de la venta se sigue derivando hacia atrás desde
`current_price` (D-45), no hace falta que `base_price` viva en el Ítem para eso.

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-08

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("items", sa.Column("iva_percentage", sa.Numeric(5, 2), nullable=True))
    op.add_column("items", sa.Column("provider_price", sa.Numeric(12, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("items", "provider_price")
    op.drop_column("items", "iva_percentage")
