import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "@/stores/auth";

declare module "vue-router" {
  interface RouteMeta {
    /** Si es `true`, el guard de abajo exige sesión antes de entrar. */
    requiresAuth?: boolean;
  }
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      redirect: { name: "login" },
    },
    {
      path: "/login",
      name: "login",
      component: () => import("@/pages/LoginView.vue"),
    },
    {
      path: "/dashboard",
      name: "dashboard",
      component: () => import("@/pages/DashboardView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/referencias",
      name: "references",
      component: () => import("@/pages/references/ReferencesView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/referencias/crear",
      name: "references-new",
      component: () => import("@/pages/references/referencesNew.vue"),
      meta: { requiresAuth: true },
    },
     {
      path: "/blank",
      name: "blank",
      component: () => import("@/pages/blankView.vue"),
      meta: { requiresAuth: true },
    },
  ],
});

router.beforeEach((to) => {
  const auth = useAuthStore();
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: "login" };
  }
});

export default router;
