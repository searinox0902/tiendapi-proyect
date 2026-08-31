<script setup lang="ts">
import { ref } from "vue"
import { IconCheck, IconDatabaseExport } from "@tabler/icons-vue"
import { Moon, Sun } from "@lucide/vue"

import AppSidebar from "@/components/AppSidebar.vue"
import ModuleNavSelect from "@/components/ModuleNavSelect.vue"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"
import { Switch } from "@/components/ui/switch"
import { isDark, setTheme, theme, THEMES } from "@/composables/useTheme"
import BusinessImageCard from "./BusinessImageCard.vue"
import ExportProjectDialog from "./ExportProjectDialog.vue"

/**
 * Configuraciones (D-77) — matiza D-51, que dejaba esta pantalla fuera del
 * MVP. Entra por una necesidad concreta: el respaldo del proyecto completo
 * (nivel 1 de D-73) no tenía dónde vivir. No es una pantalla de "ajustes del
 * sistema" genérica todavía; hoy es el lugar de las operaciones que afectan
 * al negocio entero y no a un módulo.
 */
const exportOpen = ref(false)
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
            <ModuleNavSelect current="settings" />
            <div class="ml-auto flex items-center gap-2">
              <Sun class="size-4 text-muted-foreground" />
              <Switch v-model="isDark" aria-label="Cambiar a tema oscuro" />
              <Moon class="size-4 text-muted-foreground" />
            </div>
          </div>
        </header>

        <div class="max-w-3xl space-y-4">
          <div>
            <h2 class="text-sm font-medium">
              Datos del negocio
            </h2>
            <p class="text-sm text-muted-foreground">
              Operaciones que afectan a todo el proyecto, no a un módulo suelto.
            </p>
          </div>

          <div class="flex flex-col gap-4 rounded-xl border border-border p-4 sm:flex-row sm:items-center sm:justify-between">
            <div class="flex items-start gap-3">
              <div class="flex size-10 shrink-0 items-center justify-center rounded-md bg-primary/10">
                <IconDatabaseExport class="size-5 text-brand-icon" />
              </div>
              <div class="grid gap-1">
                <p class="text-sm font-medium">
                  Exportar proyecto completo
                </p>
                <p class="text-sm text-muted-foreground">
                  Descarga toda la base de datos del negocio en un solo archivo:
                  catálogo, inventario, clientes y facturas.
                </p>
              </div>
            </div>
            <Button class="shrink-0 gap-1.5" @click="exportOpen = true">
              <IconDatabaseExport class="size-4" />
              Exportar
            </Button>
          </div>
        </div>

        <div class="max-w-3xl space-y-4">
          <div>
            <h2 class="text-sm font-medium">
              Identidad
            </h2>
            <p class="text-sm text-muted-foreground">
              Cómo se ve el negocio antes de entrar: es lo primero que aparece
              al abrir la aplicación.
            </p>
          </div>

          <BusinessImageCard />
        </div>

        <div class="max-w-3xl space-y-4">
          <div>
            <h2 class="text-sm font-medium">
              Tema
            </h2>
            <p class="text-sm text-muted-foreground">
              El color de la interfaz. Es independiente del modo claro/oscuro
              del switch de arriba — podés combinar cualquiera de los dos.
            </p>
          </div>

          <!--
            Grid de muestras y no una lista de nombres: el usuario elige por el
            color que ve, no por leer "carmesí". Cada tarjeta pinta su propio
            primario con `data-theme` puesto sobre sí misma, así la muestra es
            el color real del tema y no una aproximación escrita a mano que se
            desincronice de los tokens.

            La clase `dark` también va en la tarjeta, y no solo en <html>: los
            tokens del modo oscuro viven en `.dark[data-theme="x"]`, o sea que
            ambos selectores tienen que caer sobre el MISMO elemento. Sin
            esto la muestra resolvía por `[data-theme="x"]` a secas — el
            primario del modo claro — y en oscuro mentía: Obsidiana pintaba su
            cuadrito negro (el claro) sobre una tarjeta ya oscura, cuando en la
            app real ese tema es blanco.
          -->
          <div class="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <button
              v-for="option in THEMES"
              :key="option.value"
              type="button"
              :data-theme="option.value"
              :aria-pressed="theme === option.value"
              class="group flex items-center gap-3 rounded-xl border p-3 text-left transition-colors"
              :class="[
                isDark ? 'dark' : '',
                theme === option.value
                  ? 'border-primary bg-primary/5 ring-2 ring-primary/30'
                  : 'border-border hover:bg-muted/50',
              ]"
              @click="setTheme(option.value)"
            >
              <span
                class="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground"
              >
                <IconCheck v-if="theme === option.value" class="size-5" />
              </span>
              <span class="grid min-w-0 gap-0.5">
                <span class="truncate text-sm font-medium">{{ option.label }}</span>
                <span class="truncate text-xs text-muted-foreground">{{ option.hint }}</span>
              </span>
            </button>
          </div>
        </div>
      </div>
    </SidebarInset>

    <ExportProjectDialog v-model:open="exportOpen" />
  </SidebarProvider>
</template>
