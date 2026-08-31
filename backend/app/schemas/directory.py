from pydantic import BaseModel

from app.schemas.brand import BrandRead
from app.schemas.category import CategoryRead
from app.schemas.customer import CustomerRead
from app.schemas.location import LocationRead
from app.schemas.provider import ProviderRead


class DirectorySummary(BaseModel):
    total_providers: int
    total_locations: int
    total_categories: int
    total_customers: int
    total_brands: int

    latest_providers: list[ProviderRead]
    latest_locations: list[LocationRead]
    latest_categories: list[CategoryRead]
    latest_customers: list[CustomerRead]
    latest_brands: list[BrandRead]
