"""item.status — valores del enum al inglés

`disponible|vendido|reservado|de_baja` → `available|sold|reserved|written_off`
(D-63). El nombre de la columna ya estaba en inglés; los **valores guardados**
no, que es el mismo spanglish de `precio_proveedor` (D-62) pero un nivel más
abajo: en el dato, no en el identificador.

Los cuatro pasos van en este orden por una razón: el `CHECK` viejo prohíbe los
valores nuevos, así que hay que soltarlo **antes** del `UPDATE`; y el
`server_default` apunta a un valor que dejará de ser válido, así que hay que
cambiarlo antes de volver a poner el `CHECK`.

`Bill.fiscal_status` NO se toca: `contingencia|pendiente|autorizada|rechazada`
es vocabulario de la DIAN, no nuestro (D-48/D-59). Traducirlo desalinearía el
dato del término regulatorio con el que se contrasta.

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-10

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

#  Traducción, en los dos sentidos. `de_baja` → `written_off` y no `inactive`:
#  la baja es un descarte contable de la unidad (dañada, extraviada), no una
#  desactivación temporal, y "written off" es el término que ya significa eso.
STATUS_MAP = {
    "disponible": "available",
    "vendido": "sold",
    "reservado": "reserved",
    "de_baja": "written_off",
}


def _rename(mapping: dict[str, str], check_values: tuple[str, ...], default: str) -> None:
    op.drop_constraint("ck_items_status", "items", type_="check")
    for old, new in mapping.items():
        op.execute(
            sa.text("UPDATE items SET status = :new WHERE status = :old").bindparams(
                new=new, old=old
            )
        )
    op.alter_column("items", "status", server_default=default)
    values = ", ".join(f"'{value}'" for value in check_values)
    op.create_check_constraint("ck_items_status", "items", f"status IN ({values})")


def upgrade() -> None:
    _rename(STATUS_MAP, tuple(STATUS_MAP.values()), "available")


def downgrade() -> None:
    inverse = {new: old for old, new in STATUS_MAP.items()}
    _rename(inverse, tuple(STATUS_MAP.keys()), "disponible")
