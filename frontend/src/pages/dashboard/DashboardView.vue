<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue"
import {
  IconAlertTriangle,
  IconClockPause,
  IconLayersIntersect,
  IconPackage,
} from "@tabler/icons-vue"
import { Moon, Sun } from "@lucide/vue"
import { toast } from "vue-sonner"

import AppSidebar from "@/components/AppSidebar.vue"
import DateRangePicker from "@/components/DateRangePicker.vue"
import ModuleNavSelect from "@/components/ModuleNavSelect.vue"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"
import { Skeleton } from "@/components/ui/skeleton"
import { Switch } from "@/components/ui/switch"
import { isDark } from "@/composables/useTheme"
import { toDecimal } from "@/lib/money"
import { dashboardApi } from "@/api/dashboard/dashboard.api"
import InventoryFlowChart from "./InventoryFlowChart.vue"
import RestockList from "./RestockList.vue"
import SalesChart from "./SalesChart.vue"
import TopProductsList from "./TopProductsList.vue"
import type { IDashboardSummary } from "@/api/dashboard/dashboard.types"

/**
 * Dashboard operativo de producto (D-66).
 *
 * **No es un roll-up financiero:** no muestra margen ni utilidad — esas viven
 * en Facturación, que es su pantalla natural. Acá se responde el cruce que
 * ninguna otra pantalla puede hacer sola: qué se vende contra qué queda.
 */

/** `Date` local → `"YYYY-MM-DD"`. Nunca `toISOString()`: eso pasa por UTC y corre el día. */
function toISODate(date: Date): string {
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const day = String(date.getDate()).padStart(2, "0")
  return `${date.getFullYear()}-${month}-${day}`
}

/**
 * Rango libre por datepicker (D-69, reemplaza el selector Hoy/7días/30días).
 *
 * Arranca en los últimos 30 días — el mismo valor por defecto que traía el
 * selector viejo — para que el tablero no amanezca vacío pidiendo que el
 * usuario elija fechas antes de ver nada.
 */
const today = new Date()
const dateFrom = ref(toISODate(new Date(today.getFullYear(), today.getMonth(), today.getDate() - 29)))
const dateTo = ref(toISODate(today))

const summary = ref<IDashboardSummary | null>(null)
const isLoading = ref(false)
/** Distingue "falló la carga" de "no hubo ventas": son estados distintos. */
const hasError = ref(false)

async function load() {
  //  Rango a medio elegir (el usuario limpió un extremo): no hay nada que
  //  pedirle al servidor todavía, así que ni se intenta ni se muestra error.
  if (!dateFrom.value || !dateTo.value) {
    return
  }
  isLoading.value = true
  hasError.value = false
  try {
    const { data } = await dashboardApi.getSummary({ from: dateFrom.value, to: dateTo.value })
    summary.value = data
  } catch {
    hasError.value = true
    summary.value = null
    toast.error("No se pudo cargar el tablero", { position: "bottom-center" })
  } finally {
    isLoading.value = false
  }
}

watch([dateFrom, dateTo], load)
onMounted(load)

/** `19.000` → `19`: el servidor manda decimal, pero se venden unidades enteras. */
const unitsSold = computed(() =>
  summary.value === null ? "—" : toDecimal(summary.value.units_sold).toDecimalPlaces(2).toString(),
)

/**
 * Los cuatro tiles de producto (D-66). `alarm` los pinta en destructivo solo
 * cuando el valor exige acción — un cero en "agotados" es buena noticia y no
 * debe verse como alerta.
 */
const tiles = computed(() => {
  const data = summary.value
  return [
    {
      key: "units",
      label: "Unidades vendidas",
      value: unitsSold.value,
      icon: IconPackage,
      alarm: false,
    },
    {
      key: "references",
      label: "Referencias distintas",
      value: data ? String(data.distinct_references_sold) : "—",
      icon: IconLayersIntersect,
      alarm: false,
    },
    {
      key: "out",
      label: "Agotados con demanda",
      value: data ? String(data.out_of_stock_with_demand) : "—",
      icon: IconAlertTriangle,
      alarm: (data?.out_of_stock_with_demand ?? 0) > 0,
    },
    {
      key: "stale",
      label: "Sin rotación (+90 días)",
      value: data ? String(data.stale_references) : "—",
      icon: IconClockPause,
      alarm: (data?.stale_references ?? 0) > 0,
    },
  ]
})
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
            <ModuleNavSelect current="dashboard" />
            <div class="ml-auto flex items-center gap-2">
              <Sun class="size-4 text-muted-foreground" />
              <Switch v-model="isDark" aria-label="Cambiar a tema oscuro" />
              <Moon class="size-4 text-muted-foreground" />
            </div>
          </div>
        </header>

        <!--
          Selector de rango (D-69). Mueve la demanda (gráfico, tiles, top,
          reponer) pero NO el stock: las existencias son una foto del ahora
          (D-66).
        -->
        <div class="flex flex-wrap items-center gap-2">
          <div class="w-full sm:w-72">
            <DateRangePicker
              v-model:from="dateFrom"
              v-model:to="dateTo"
              placeholder="Rango de fechas"
            />
          </div>
        </div>

        <!-- Falló la carga: no es lo mismo que "no hubo ventas". -->
        <div
          v-if="hasError"
          class="flex flex-col items-center gap-2 rounded-xl border border-border py-16"
        >
          <p class="text-destructive">
            No se pudo cargar el tablero.
          </p>
          <Button variant="outline" size="sm" @click="load">
            Reintentar
          </Button>
        </div>

        <template v-else-if="isLoading || summary === null">
          <div class="grid gap-4 xl:grid-cols-2">
            <Skeleton class="h-[340px] rounded-xl" />
            <Skeleton class="h-[340px] rounded-xl" />
          </div>
          <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Skeleton v-for="placeholder in 4" :key="placeholder" class="h-24 rounded-xl" />
          </div>
          <div class="grid gap-4 lg:grid-cols-2">
            <Skeleton class="h-80 rounded-xl" />
            <Skeleton class="h-80 rounded-xl" />
          </div>
        </template>

        <template v-else>
          <!--
            1. Los dos gráficos, uno al lado del otro y sobre la misma grilla
            de tiempo: a la izquierda cuánta plata entró, a la derecha si el
            inventario está creciendo más rápido de lo que se vende. Un pico en
            uno se puede leer contra el mismo día en el otro.
          -->
          <div class="grid gap-4 xl:grid-cols-2">
            <SalesChart
              :series="summary.sales_series"
              :granularity="summary.granularity"
              :total-billed="summary.total_billed"
            />
            <InventoryFlowChart
              :flow="summary.flow_series"
              :granularity="summary.granularity"
            />
          </div>

          <!-- 2. Cuatro tiles de producto. -->
          <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div
              v-for="tile in tiles"
              :key="tile.key"
              class="rounded-xl border px-4 py-3"
              :class="tile.alarm ? 'border-destructive/40 bg-destructive/5' : 'border-border'"
            >
              <div class="flex items-center gap-2 text-muted-foreground">
                <component :is="tile.icon" class="size-4 shrink-0" />
                <p class="truncate text-xs">
                  {{ tile.label }}
                </p>
              </div>
              <p
                class="mt-1 text-2xl font-bold tabular-nums"
                :class="tile.alarm ? 'text-destructive' : ''"
              >
                {{ tile.value }}
              </p>
            </div>
          </div>

          <!-- 3 y 4. Qué se vende (izquierda) contra qué se acaba (derecha). -->
          <div class="grid gap-4 lg:grid-cols-2">
            <TopProductsList :products="summary.top_products" />
            <RestockList :rows="summary.restock" />
          </div>
        </template>
      </div>
    </SidebarInset>
  </SidebarProvider>
</template>
