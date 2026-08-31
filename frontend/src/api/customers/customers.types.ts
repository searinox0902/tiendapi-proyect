/** Tal cual lo devuelve `GET /customers/` (`CustomerRead`). */
export interface ICustomer {
  id: string;
  tenant_id: string;
  /** Cédula o NIT. Opcional: un "consumidor final" puede no darlo. */
  nit: string | null;
  fullname: string;
  mail: string | null;
  created_at: string;
  updated_at: string;
  version: number;
}

/** Body de `POST /customers/`. */
export interface ICustomerCreate {
  nit?: string | null;
  fullname: string;
  mail?: string | null;
}
