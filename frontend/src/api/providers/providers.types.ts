/** Tal cual lo devuelve `GET /providers/` (`ProviderRead`). */
export interface IProvider {
  id: string;
  tenant_id: string;
  provider_code: string | null;
  nit: string | null;
  title: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  version: number;
}

/** Body de `POST /providers/`. */
export interface IProviderCreate {
  provider_code?: string | null;
  nit?: string | null;
  title: string;
  description?: string | null;
}
