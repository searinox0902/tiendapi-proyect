import { computed, ref } from "vue";
import { defineStore } from "pinia";
import type { IAuthUser, ILoginCredentials } from "@/api/auth/auth.types";
import { authApi } from "@/api/auth/auth.api";

const TOKEN_STORAGE_KEY = "tiendapi.token";

export const useAuthStore = defineStore("auth", () => {
  
  const token = ref<string | null>(localStorage.getItem(TOKEN_STORAGE_KEY));
  const user = ref<Partial<IAuthUser> | null>(null);
  const isLoading = ref(false);

  const isAuthenticated = computed(() => token.value !== null);

  function setToken(newToken: string | null) {
    token.value = newToken;
    if (newToken) {
      localStorage.setItem(TOKEN_STORAGE_KEY, newToken);
    } else {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
    }
  }

  function setUserData(userData: IAuthUser | undefined) {
    if (userData) {
      user.value = userData;
    } else {
      user.value = null;
    }
  }

  async function login(credentials: ILoginCredentials): Promise<void> {
    isLoading.value = true;
    try {
      const { data } = await authApi.posLogin(credentials);
      setToken(data.access_token);

      if(data.user){
        setUserData(data.user)
      }
    } catch (error) {
      console.error("Login failed:", error);
      console.log(error);
      logout()
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  function logout() {
    setToken(null);
    user.value = null;
  }

  return { token, user, isLoading, isAuthenticated, login, logout };
});
