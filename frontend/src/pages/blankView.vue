<script setup lang="ts">
import { computed } from "vue"
import { IconArrowLeft, IconTool } from "@tabler/icons-vue"
import { Moon, Sun } from "@lucide/vue"
import { useRoute, useRouter } from "vue-router"

import AppSidebar from "@/components/AppSidebar.vue"
import ModuleNavSelect from "@/components/ModuleNavSelect.vue"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"
import { Switch } from "@/components/ui/switch"
import { isDark } from "@/composables/useTheme"

/**
 * Placeholder de módulo sin construir.
 *
 * Antes esta vista era literalmente `<div />`: quien entraba —por ejemplo desde
 * "Agregar Productos", que apunta acá porque el alta de Ítems todavía no
 * existe (D-51)— caía en una **pantalla en blanco sin sidebar ni cabecera**, o
 * sea sin ninguna forma de salir que no fuera el botón atrás del navegador.
 * Un callejón sin salida se lee como que la aplicación se rompió.
 *
 * Ahora trae el andamiaje transversal completo (sidebar, selector de módulo,
 * switch de tema) para que sea una parada y no una trampa, y dice en palabras
 * que el módulo está en desarrollo en vez de dejar que el usuario lo deduzca.
 */
const route = useRoute()
const router = useRouter()

/**
 * Nombre del módulo, si la ruta lo declara. Se lee de `meta.moduleName` para
 * que agregar otro placeholder sea una línea en el router y no otro
 * componente: mientras más barato sea, menos tentador es dejar un `<div />`.
 */
const moduleName = computed(() => {
  const declared = route.meta.moduleName
  return typeof declared === "string" && declared.length > 0 ? declared : null
})

/** Módulo del menú bajo el que vive esta pantalla, si la ruta lo declara. */
const parentModule = computed(() => {
  const declared = route.meta.parentModule
  return typeof declared === "string" && declared.length > 0 ? declared : undefined
})

/**
 * Volver: si hay historial se retrocede —lo natural cuando se llegó desde un
 * botón—, y si no (entrada directa por URL, recarga) se cae al Dashboard, que
 * siempre existe. Sin el respaldo, `back()` desde una pestaña nueva no hace
 * nada y el botón parecería roto.
 */
function goBack() {
  if (window.history.length > 1) {
    router.back()
    return
  }
  router.push({ name: "dashboard" })
}
</script>

<template>
  <SidebarProvider
    :style="{
      '--sidebar-width': 'calc(var(--spacing) * 72)',
      '--header-height': 'calc(var(--spacing) * 12)',
    }"
  >
    <AppSidebar variant="inset" />
    <SidebarInset class="min-w-0">
      <div class="min-w-0 space-y-6 px-6 pb-6">
        <header class="flex h-(--header-height) shrink-0 items-center gap-2 border-b">
          <div class="flex w-full items-center gap-1 px-4 lg:gap-2 lg:px-6">
            <SidebarTrigger class="-ml-1" />
            <Separator orientation="vertical" class="mx-2 data-[orientation=vertical]:h-4" />
            <!--
              `parentModule` cuando la ruta lo declara (ej. "Agregar Productos"
              vive bajo Productos): deja el selector marcando el módulo padre,
              que es donde el usuario cree estar. Sin él va neutro — marcar uno
              cualquiera sería mentir sobre dónde está.
            -->
            <ModuleNavSelect :current="parentModule" />
            <div class="ml-auto flex items-center gap-2">
              <Sun class="size-4 text-muted-foreground" />
              <Switch v-model="isDark" aria-label="Cambiar a tema oscuro" />
              <Moon class="size-4 text-muted-foreground" />
            </div>
          </div>
        </header>

        <div class="flex min-h-[60vh] items-center justify-center">
          <div class="flex max-w-md flex-col items-center gap-4 text-center">
            <div class="flex size-16 items-center justify-center rounded-2xl bg-accent">
              <IconTool class="size-8 text-brand-icon" />
            </div>

            <div class="space-y-1.5">
              <h1 class="text-xl font-semibold">
                {{ moduleName ? `${moduleName}: en desarrollo` : "Módulo en desarrollo" }}
              </h1>
              <p class="text-sm text-muted-foreground">
                Esta parte todavía no está construida. No es un error ni se
                perdió nada — simplemente aún no existe.
              </p>
            </div>

            <!--
              Dos salidas y no una: el botón devuelve por donde vino, y el
              selector de módulo de arriba permite saltar a cualquier otra
              pantalla sin pasar por el Dashboard.
            -->
            <Button variant="outline" class="gap-2" @click="goBack">
              <IconArrowLeft class="size-4" />
              Volver
            </Button>
          </div>
        </div>
      </div>
    </SidebarInset>
  </SidebarProvider>
</template>
