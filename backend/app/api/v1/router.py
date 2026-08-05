from fastapi import APIRouter

from app.api.v1 import auth, bills, categories, customers, items, locations, providers, references

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(providers.router)
api_router.include_router(categories.router)
api_router.include_router(locations.router)
api_router.include_router(references.router)
api_router.include_router(items.router)
api_router.include_router(customers.router)
api_router.include_router(bills.router)
