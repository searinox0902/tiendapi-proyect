import { http } from "@/lib/axios";
import type { IDirectorySummary } from "./directory.types";

export const directoryApi = {
  getSummary(latest = 5) {
    return http.get<IDirectorySummary>("/directory/summary", { params: { latest } });
  },
};
