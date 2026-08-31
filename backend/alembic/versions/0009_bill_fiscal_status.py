"""bill.fiscal_status — estado fiscal DIAN

Columna reservada por D-48 (`contingencia | pendiente | autorizada |
rechazada`, nullable) que hasta ahora estaba documentada pero nunca creada.
Nullable a propósito: sin integración DIAN viva (diferida, D-09/D-38) una
factura no tiene estado fiscal real, y `NULL` dice exactamente eso — distinto
de "pendiente", que sí es una afirmación sobre el trámite.

`CHECK` en la base y no solo enum en Pydantic, mismo criterio que
`ck_locations_type` (D-25): protege el valor incluso ante escrituras que no
pasen por la API. Zona de alto riesgo (control fiscal, CLAUDE.md).

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-09

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bills", sa.Column("fiscal_status", sa.String(), nullable=True))
    op.create_check_constraint(
        "ck_bills_fiscal_status",
        "bills",
        "fiscal_status IN ('contingencia', 'pendiente', 'autorizada', 'rechazada')",
    )
    op.create_index("ix_bills_fiscal_status", "bills", ["fiscal_status"])


def downgrade() -> None:
    op.drop_index("ix_bills_fiscal_status", table_name="bills")
    op.drop_constraint("ck_bills_fiscal_status", "bills", type_="check")
    op.drop_column("bills", "fiscal_status")
