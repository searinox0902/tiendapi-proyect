"""providers/locations/categories/customers/brands.import_batch_id — deshacer
importaciones del Directorio (D-75)

Extiende a las 5 entidades de soporte el mismo mecanismo que ya tiene
`Reference` (D-73, migración `0015`): un UUID nuevo por corrida de
importación agrupa las filas que creó, para poder deshacer el lote entero
si el archivo vino mal armado. `NULL` = alta manual o lote ya revertido.

Revision ID: 0016
Revises: 0015
Create Date: 2026-08-17

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None

TABLES = ("providers", "locations", "categories", "customers", "brands")


def upgrade() -> None:
    for table in TABLES:
        op.add_column(
            table, sa.Column("import_batch_id", postgresql.UUID(as_uuid=True), nullable=True)
        )
        op.create_index(f"ix_{table}_import_batch_id", table, ["import_batch_id"])


def downgrade() -> None:
    for table in TABLES:
        op.drop_index(f"ix_{table}_import_batch_id", table_name=table)
        op.drop_column(table, "import_batch_id")
