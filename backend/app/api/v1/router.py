from fastapi import APIRouter

from app.api.v1 import (
    auth,
    backup,
    bills,
    branding,
    brands,
    categories,
    customers,
    dashboard,
    directory,
    directory_io,
    items,
    locations,
    products_io,
    providers,
    references,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(providers.router)
api_router.include_router(categories.router)
api_router.include_router(locations.router)
api_router.include_router(brands.router)
api_router.include_router(directory.router)
api_router.include_router(directory_io.router)
api_router.include_router(references.router)
#  ANTES que `items.router` a propósito: ahí vive `GET /items/{item_id}`, que
#  capturaría `/items/export` y `/items/import` y los rechazaría con un 422 por
#  no ser UUIDs. FastAPI resuelve por orden de registro.
api_router.include_router(products_io.router)
api_router.include_router(items.router)
api_router.include_router(customers.router)
api_router.include_router(bills.router)
api_router.include_router(dashboard.router)
api_router.include_router(backup.router)
api_router.include_router(branding.router)
