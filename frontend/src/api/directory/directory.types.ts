import type { IBrand } from "@/api/brands/brands.types";
import type { ICategory } from "@/api/categories/categories.types";
import type { ICustomer } from "@/api/customers/customers.types";
import type { ILocation } from "@/api/locations/locations.types";
import type { IProvider } from "@/api/providers/providers.types";

/**
 * Tal cual lo devuelve `GET /directory/summary` (`DirectorySummary`): conteo +
 * últimos creados de cada entidad de soporte, en un solo viaje al backend.
 */
export interface IDirectorySummary {
  total_providers: number;
  total_locations: number;
  total_categories: number;
  total_customers: number;
  total_brands: number;

  latest_providers: IProvider[];
  latest_locations: ILocation[];
  latest_categories: ICategory[];
  latest_customers: ICustomer[];
  latest_brands: IBrand[];
}
