import { http } from "@/lib/axios";
import type { IBrand, IBrandCreate } from "./brands.types";

export const brandsApi = {
  getBrands(params: { skip?: number; limit?: number } = {}) {
    return http.get<IBrand[]>("/brands/", { params });
  },

  createBrand(payload: IBrandCreate) {
    return http.post<IBrand>("/brands/", payload);
  },
};
