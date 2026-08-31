<script setup lang="ts">
import { IconInnerShadowTop, IconLogout } from "@tabler/icons-vue"
import { useRoute, useRouter } from "vue-router"

import { navGroups } from "@/config/navigation"
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
              <IconInnerShadowTop class="!size-5 text-brand-icon" />
              <span class="text-base font-semibold">TiendAPI</span>
            </RouterLink>
          </SidebarMenuButton>
        </SidebarMenuItem>
      </SidebarMenu>
    </SidebarHeader>

    <SidebarContent>
      <SidebarGroup v-for="(group, index) in navGroups" :key="group.label ?? index">
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
                  <component :is="item.icon" class="text-brand-icon" />
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
