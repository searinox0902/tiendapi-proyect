"""item.provider_id / item.location_id opcionales

El alta manual rápida de una existencia (pantalla de detalle del Producto) no
exige elegir proveedor ni ubicación en el momento de crearla — se puede
completar después. `reference_id` se queda obligatorio: sin Referencia la
unidad no pertenece a ningún producto.

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-08

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("items", "provider_id", nullable=True)
    op.alter_column("items", "location_id", nullable=True)


def downgrade() -> None:
    # Ítems creados sin proveedor/ubicación mientras el downgrade no puede
    # inventar un valor válido: si existen filas NULL, este downgrade fallará
    # por el NOT NULL — es la señal correcta de que hay que resolverlas a mano
    # antes de revertir, no silenciarlas con un valor inventado.
    op.alter_column("items", "provider_id", nullable=False)
    op.alter_column("items", "location_id", nullable=False)
