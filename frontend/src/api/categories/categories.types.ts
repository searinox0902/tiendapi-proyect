/** Tal cual lo devuelve `GET /categories/` (`CategoryRead`). */
export interface ICategory {
  id: string;
  tenant_id: string;
  name: string;
  description: string | null;
  /** Nombre de ícono lucide (ver `@/lib/categoryIcons`), `null` si no se eligió uno. */
  icon: string | null;
  created_at: string;
  updated_at: string;
  version: number;
}

/** Body de `POST /categories/`. */
export interface ICategoryCreate {
  name: string;
  description?: string | null;
  icon?: string | null;
}
