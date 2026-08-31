import { http } from "@/lib/axios";
import type { IProvider, IProviderCreate } from "./providers.types";

export const providersApi = {
  getProviders(params: { skip?: number; limit?: number } = {}) {
    return http.get<IProvider[]>("/providers/", { params });
  },

  createProvider(payload: IProviderCreate) {
    return http.post<IProvider>("/providers/", payload);
  },
};
