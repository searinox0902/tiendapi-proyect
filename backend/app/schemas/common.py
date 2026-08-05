from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """
    Envoltura para listados paginados.

    Una `list[...]` pelada no puede cargar el total de registros, y sin ese
    total el cliente no sabe cuántas páginas dibujar: solo vería la porción que
    le llegó. `total` es el conteo de filas que pasan los filtros, **ignorando**
    `skip`/`limit`.
    """

    items: list[T]
    total: int
    skip: int
    limit: int
