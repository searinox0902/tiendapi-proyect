export type TLocationType = "sucursal" | "bodega";

export interface ILocation {
  id: string;
  tenant_id: string;
  name: string;
  address: string | null;
  type: TLocationType;
}
