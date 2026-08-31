/** Tal cual lo devuelve `GET /brands/` (`BrandRead`). Catálogo propio, independiente de `Reference.brand` (texto libre, D-57) — ver D-71. */
export interface IBrand {
  id: string;
  tenant_id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  version: number;
}

/** Body de `POST /brands/`. */
export interface IBrandCreate {
  name: string;
  description?: string | null;
}
