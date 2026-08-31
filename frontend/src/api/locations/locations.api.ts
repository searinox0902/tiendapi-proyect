import { http } from "@/lib/axios";
import type { ILocation, ILocationCreate } from "./locations.types";

export const locationsApi = {
  getLocations(params: { skip?: number; limit?: number } = {}) {
    return http.get<ILocation[]>("/locations/", { params });
  },

  createLocation(payload: ILocationCreate) {
    return http.post<ILocation>("/locations/", payload);
  },
};
