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
      path: "/referencias/editar/:sku",
      name: "references-edit",
      component: () => import("@/pages/references/referencesNew.vue"),
      props: true,
      meta: { requiresAuth: true },
    },
    {
      path: "/productos",
      name: "items",
      component: () => import("@/pages/Items/ItemsView.vue"),
      meta: { requiresAuth: true },
    },
    {
      // El alta de Ítems (D-51) todavía no está construida: la ruta existe y
      // apunta al placeholder para que el botón "Agregar Productos" navegue a
      // algo real en vez de romper. Reemplazar el componente al construirla.
      path: "/productos/crear",
      name: "items-new",
      component: () => import("@/pages/blankView.vue"),
      meta: { requiresAuth: true },
    },
    {
      // Aterrizaje de un Producto: la Referencia y todas sus existencias.
      // Va después de `/productos/crear` para que ese path estático no quede
      // capturado por el parámetro.
      path: "/productos/:referenceId",
      name: "items-detail",
      component: () => import("@/pages/Items/ItemDetailView.vue"),
      props: true,
      meta: { requiresAuth: true },
    },
    {
      path: "/caja",
      name: "pos",
      component: () => import("@/pages/pos/posView.vue"),
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
