import uuid
from typing import Generic, Optional, Sequence, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.text import fold
from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class CRUDBase(Generic[ModelType]):
    """CRUD genérico con aislamiento por tenant (docs/07-decisiones-y-puntos-abiertos.md, D-23)."""

    def __init__(self, model: Type[ModelType]):
        self.model = model

    def get(self, db: Session, tenant_id: uuid.UUID, id: uuid.UUID) -> Optional[ModelType]:
        stmt = select(self.model).where(self.model.id == id, self.model.tenant_id == tenant_id)
        return db.execute(stmt).scalar_one_or_none()

    def get_multi(
        self, db: Session, tenant_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> Sequence[ModelType]:
        #  Sin ORDER BY el orden entre llamadas no está garantizado (mismo
        #  motivo que en `references.py list_references`). Más reciente primero
        #  es el default más útil para un listado simple; se desempata por `id`
        #  porque dos filas creadas en el mismo instante podrían alternar orden.
        stmt = (
            select(self.model)
            .where(self.model.tenant_id == tenant_id)
            .order_by(self.model.created_at.desc(), self.model.id.desc())
            .offset(skip)
            .limit(limit)
        )
        return db.execute(stmt).scalars().all()

    def find_by_name(
        self, db: Session, tenant_id: uuid.UUID, column, value: Optional[str], normalizer=fold
    ) -> Optional[ModelType]:
        """
        Registro cuyo `column` coincide con `value` **normalizado**, o `None`.

        La normalización por defecto es `fold` (D-93): sin mayúsculas, sin
        tildes, sin espacios de sobra, así que `HONDA`, `Hónda` y `"Honda "`
        encuentran al `Honda` que ya existe. `normalizer` se cambia cuando la
        clave no es un nombre — un NIT se compara con `core/nit.py`, donde lo
        que sobra es el formato y no las tildes.

        **Se compara en Python y no en el `WHERE`** por lo mismo que documenta
        `app/imports/names.py`: plegar en SQL exigiría la extensión `unaccent`
        de Postgres, que no está instalada y que no existe en SQLite, la BBDD
        local del producto (D-01/D-02). Las tablas donde esto se usa son las
        del Directorio, de decenas de filas.

        Hermano de `NameIndex` y no un duplicado suyo: aquél es un índice en
        bloque para importar miles de filas, éste es la consulta suelta del
        alta manual. Los dos delegan la regla en la misma función.
        """
        if not value or not value.strip():
            return None
        objetivo = normalizer(value)
        if not objetivo:
            return None
        rows = db.execute(
            select(self.model)
            .where(self.model.tenant_id == tenant_id)
            .order_by(self.model.created_at, self.model.id)
        ).scalars()
        for row in rows:
            #  El más viejo gana: mismo criterio determinista que `NameIndex`
            #  para cuando la base ya arrastra dos grafías de lo mismo.
            if normalizer(getattr(row, column.key)) == objetivo:
                return row
        return None

    def create(self, db: Session, tenant_id: uuid.UUID, obj_in: dict) -> ModelType:
        db_obj = self.model(tenant_id=tenant_id, **obj_in)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self, db: Session, tenant_id: uuid.UUID, id: uuid.UUID, obj_in: dict
    ) -> Optional[ModelType]:
        db_obj = self.get(db, tenant_id, id)
        if db_obj is None:
            return None
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        db_obj.version += 1  # control de versión (D-20) — resolución de conflictos de sync
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, tenant_id: uuid.UUID, id: uuid.UUID) -> bool:
        db_obj = self.get(db, tenant_id, id)
        if db_obj is None:
            return False
        db.delete(db_obj)
        db.commit()
        return True
