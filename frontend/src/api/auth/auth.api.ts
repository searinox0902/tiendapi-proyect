import { http } from "@/lib/axios";
import type { ILoginCredentials, ILoginResponse } from "./auth.types";

export const authApi = {
  posLogin(payload: ILoginCredentials) {
    return http.post<ILoginResponse>("/auth/login", payload);
  },
};
