import { http } from "@/lib/axios";
import type { ICustomer, ICustomerCreate } from "./customers.types";

export const customersApi = {
  /**
   * `search` cruza cédula/NIT y nombre con **OR**: el cajero teclea lo que el
   * cliente le dicta y no debería tener que decidir en qué campo va.
   */
  getCustomers(params: { search?: string; limit?: number } = {}) {
    return http.get<ICustomer[]>("/customers/", { params });
  },

  /**
   * Coincidencia **exacta** por documento o nombre; `null` si no existe. Es lo
   * que decide si el cobro ofrece registrar al cliente — con coincidencia
   * parcial se crearían duplicados del mismo cliente.
   */
  lookupCustomer(params: { nit?: string; fullname?: string }) {
    return http.get<ICustomer | null>("/customers/lookup", { params });
  },

  createCustomer(payload: ICustomerCreate) {
    return http.post<ICustomer>("/customers/", payload);
  },
};
