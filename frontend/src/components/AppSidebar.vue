<script setup lang="ts">
import {
  IconCashRegister,
  IconDashboard,
  IconInnerShadowTop,
  IconLogout,
  IconPackage,
  IconReceipt,
  IconReport,
  IconTags,
} from "@tabler/icons-vue"
import { useRoute, useRouter } from "vue-router"

import { useAuthStore } from "@/stores/auth"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar'

/**
 * Botonera del sidebar, agrupada por área. `label` es el mini-título del grupo
 * (omitirlo lo deja sin título); `to` apunta al `name` de una ruta del router.
 * Para agregar una opción basta con una línea más en el grupo que corresponda.
 */
const groups = [
  {
    items: [
      { title: "Dashboard", to: "dashboard", icon: IconDashboard },
    ],
  },
  {
    label: "Gestión logística",
    items: [
      { title: "Referencias", to: "references", icon: IconTags },
      { title: "Productos", to: "blank", icon: IconPackage },
    ],
  },
  {
    label: "Ventas",
    items: [
      { title: "Caja registradora", to: "blank", icon: IconCashRegister },
      { title: "Registro de ventas", to: "blank", icon: IconReceipt },
    ],
  },
  {
    label: "Reportes",
    items: [
      { title: "Reporte DIAN", to: "blank", icon: IconReport },
    ],
  },
]

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

function logout() {
  authStore.logout()
  router.push({ name: "login" })
}
</script>

<template>
  <Sidebar collapsible="offcanvas">
    <SidebarHeader>
      <SidebarMenu>
        <SidebarMenuItem>
          <SidebarMenuButton
            as-child
            class="data-[slot=sidebar-menu-button]:!p-1.5"
          >
            <RouterLink :to="{ name: 'dashboard' }">
              <IconInnerShadowTop class="!size-5" />
              <span class="text-base font-semibold">TiendAPI</span>
            </RouterLink>
          </SidebarMenuButton>
        </SidebarMenuItem>
      </SidebarMenu>
    </SidebarHeader>

    <SidebarContent>
      <SidebarGroup v-for="(group, index) in groups" :key="group.label ?? index">
        <SidebarGroupLabel v-if="group.label">
          {{ group.label }}
        </SidebarGroupLabel>
        <SidebarGroupContent>
          <SidebarMenu>
            <SidebarMenuItem v-for="item in group.items" :key="item.title">
              <SidebarMenuButton
                as-child
                :tooltip="item.title"
                :is-active="route.name === item.to"
              >
                <RouterLink :to="{ name: item.to }">
                  <component :is="item.icon" />
                  <span>{{ item.title }}</span>
                </RouterLink>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>
    </SidebarContent>

    <SidebarFooter>
      <SidebarMenu>
        <SidebarMenuItem>
          <SidebarMenuButton tooltip="Cerrar sesión" @click="logout">
            <IconLogout />
            <span>Cerrar sesión</span>
          </SidebarMenuButton>
        </SidebarMenuItem>
      </SidebarMenu>
    </SidebarFooter>
  </Sidebar>
</template>
