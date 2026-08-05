import uuid
from typing import Generic, Optional, Sequence, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

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
        stmt = (
            select(self.model)
            .where(self.model.tenant_id == tenant_id)
            .offset(skip)
            .limit(limit)
        )
        return db.execute(stmt).scalars().all()

    def create(self, db: Session, tenant_id: uuid.UUID, obj_in: dict) -> ModelType:
        db_obj = self.model(tenant_id=tenant_id, **obj_in)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
