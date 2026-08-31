export type TLocationType = "sucursal" | "bodega";

export interface ILocation {
  id: string;
  tenant_id: string;
  name: string;
  address: string | null;
  type: TLocationType;
  created_at: string;
  updated_at: string;
  version: number;
}

/** Body de `POST /locations/`. */
export interface ILocationCreate {
  name: string;
  address?: string | null;
  type: TLocationType;
}
