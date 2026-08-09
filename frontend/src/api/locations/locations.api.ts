import { http } from "@/lib/axios";
import type { ILocation } from "./locations.types";

export const locationsApi = {
  getLocations() {
    return http.get<ILocation[]>("/locations/");
  },
};
