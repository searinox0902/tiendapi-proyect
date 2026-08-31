import { http } from "@/lib/axios";
import type { ICategory, ICategoryCreate } from "./categories.types";

export const categoriesApi = {
  getCategories(params: { skip?: number; limit?: number } = {}) {
    return http.get<ICategory[]>("/categories/", { params });
  },

  createCategory(payload: ICategoryCreate) {
    return http.post<ICategory>("/categories/", payload);
  },
};
