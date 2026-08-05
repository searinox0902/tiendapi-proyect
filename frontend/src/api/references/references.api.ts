import { http } from "@/lib/axios";
import type {
  ICategory,
  IPage,
  IReference,
  IReferenceFilters,
  IReferenceSummary,
} from "./references.types";

export const referencesApi = {
  getReferences(params: IReferenceFilters) {
    return http.get<IPage<IReference>>("/references/", { params });
  },

  getSummary(latest = 5) {
    return http.get<IReferenceSummary>("/references/summary", { params: { latest } });
  },

  getCategories() {
    return http.get<ICategory[]>("/categories/");
  },
};
