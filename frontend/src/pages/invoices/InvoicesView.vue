<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue"
import { watchDebounced } from "@vueuse/core"
import { IconDownload, IconPackage, IconTable } from "@tabler/icons-vue"
import { Moon, Sun } from "@lucide/vue"
import { toast } from "vue-sonner"

import AppSidebar from "@/components/AppSidebar.vue"
import DateRangePicker from "@/components/DateRangePicker.vue"
import ModuleNavSelect from "@/components/ModuleNavSelect.vue"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"
import { Skeleton } from "@/components/ui/skeleton"
import { Switch } from "@/components/ui/switch"
import { isDark } from "@/composables/useTheme"
import { formatCurrency, toDecimal } from "@/lib/money"
import { useBillsStore } from "@/stores/bills"
import ExportBillsDialog from "./ExportBillsDialog.vue"
import InvoiceCard from "./InvoiceCard.vue"
import type { IBillFilters } from "@/api/bills/bills.types"

/** `SelectItem` de reka-ui no acepta value vacío, así que "todos" necesita un centinela. */
const ALL_STATUSES = "__all__"
const PAGE_SIZE = 10

const store = useBillsStore()

const filters = reactive({
  customer: "",
  billNumber: "",
  dateFrom: undefined as string | undefined,
  dateTo: undefined as string | undefined,
  status: ALL_STATUSES,
})

const page = ref(1)
/** Facturas marcadas. Un `Set` reactivo: Vue trackea `.add`/`.delete`/`.has` sin recrearlo. */
const selectedIds = ref(new Set<string>())

/** Los filtros vacíos se omiten: el backend los trata como "sin filtro". */
function currentParams(): IBillFilters {
  return {
    customer: filters.customer.trim() || undefined,
    bill_number: filters.billNumber.trim() || undefined,
    date_from: filters.dateFrom,
    date_to: filters.dateTo,
    //  `undefined` = todas. El backend distingue los tres casos: omitido,
    //  `false` (vigentes) y `true` (anuladas) — ver `_bill_conditions`.
    voided: filters.status === ALL_STATUSES ? undefined : filters.status === "anuladas",
    skip: (page.value - 1) * PAGE_SIZE,
    limit: PAGE_SIZE,
  }
}

/**
 * El resumen ignora la paginación (no `skip`/`limit`) a propósito: describe
 * **todo** lo que pasa el filtro, no la página que se alcanzó a cargar. Si
 * cambiara al pasar de página, las cifras de cabecera dejarían de tener
 * sentido.
 */
function summaryParams(): IBillFilters {
  const { skip: _skip, limit: _limit, ...rest } = currentParams()
  return rest
}

async function load() {
  const [list] = await Promise.allSettled([
    store.fetchBills(currentParams()),
    //  El resumen es accesorio: si falla, la tabla sigue sirviendo y no se
    //  apilan dos toasts.
    store.fetchSummary(summaryParams()),
  ])
  if (list.status === "rejected") {
    toast.error("No se pudieron cargar las facturas", { position: "bottom-center" })
  }
  //  Una página nueva trae otras facturas: mantener marcadas las de la
  //  anterior dejaría una selección invisible actuando por detrás.
  selectedIds.value.clear()
}

/** Con debounce: tecleando un nombre se dispararía una consulta por carácter. */
watchDebounced(filters, () => {
  //  Cualquier cambio de filtro vuelve a la página 1: quedarse en la 4 de un
  //  resultado que ahora tiene 2 páginas muestra una tabla vacía sin explicar
  //  por qué.
  page.value = 1
  load()
}, { debounce: 350 })

watch(page, load)

const totalPages = computed(() => Math.max(1, Math.ceil(store.total / PAGE_SIZE)))

const hasFilters = computed(() =>
  filters.customer !== ""
  || filters.billNumber !== ""
  || filters.dateFrom !== undefined
  || filters.dateTo !== undefined
  || filters.status !== ALL_STATUSES,
)

function clearFilters() {
  filters.customer = ""
  filters.billNumber = ""
  filters.dateFrom = undefined
  filters.dateTo = undefined
  filters.status = ALL_STATUSES
}

function money(value: string) {
  return formatCurrency(toDecimal(value))
}

function toggleSelected(billId: string, value: boolean) {
  if (value) {
    selectedIds.value.add(billId)
  } else {
    selectedIds.value.delete(billId)
  }
}

/** "Todas" opera sobre la página visible, no sobre el total filtrado — marcar lo que no se ve confunde más de lo que ayuda. */
const isAllVisibleSelected = computed(() =>
  store.bills.length > 0 && store.bills.every(bill => selectedIds.value.has(bill.id)),
)
const isSomeVisibleSelected = computed(() =>
  store.bills.some(bill => selectedIds.value.has(bill.id)),
)
const selectAllState = computed<boolean | "indeterminate">(() => {
  if (isAllVisibleSelected.value) return true
  return isSomeVisibleSelected.value ? "indeterminate" : false
})

function toggleSelectAll(value: boolean) {
  for (const bill of store.bills) {
    toggleSelected(bill.id, value)
  }
}

const isExportMenuOpen = ref(false)
const isPackageDialogOpen = ref(false)
/**
 * De dónde salió el diálogo: del botón "Exportar" (todo el corte filtrado) o
 * de la barra de selección (solo lo marcado). Es un modo y no dos diálogos
 * porque el contenido es idéntico — cambia el conjunto, no la pregunta.
 */
const exportsSelectionOnly = ref(false)

const exportFilters = computed<IBillFilters>(() => {
  const base = summaryParams()
  //  Los ids **se suman** a los filtros, no los reemplazan: el servidor los
  //  combina (ver `_bill_conditions`), así que exportar una selección sigue
  //  respetando el rango de fechas y el resto del corte. Y el `tenant_id` del
  //  token aplica igual, así que una lista de ids no es una puerta lateral.
  return exportsSelectionOnly.value
    ? { ...base, ids: [...selectedIds.value] }
    : base
})

function openPackageDialog(selectionOnly = false) {
  isExportMenuOpen.value = false
  exportsSelectionOnly.value = selectionOnly
  isPackageDialogOpen.value = true
}

/**
 * Exporta a CSV **en el cliente y solo lo que está en pantalla** (o lo
 * seleccionado).
 *
 * No es el export contable: ese es el **paquete** de D-78 (`openPackageDialog`),
 * que sale del servidor sobre todo el conjunto filtrado y trae los PDF. Este se
 * conserva porque cubre un caso que el otro no: marcar tres facturas puntuales
 * con los checkboxes y llevarse solo esas — el paquete filtra por los mismos
 * criterios de la pantalla, no por selección manual.
 */
function exportCsv() {
  isExportMenuOpen.value = false
  const rows = selectedIds.value.size > 0
    ? store.bills.filter(bill => selectedIds.value.has(bill.id))
    : store.bills
  if (rows.length === 0) {
    toast.error("No hay facturas para exportar", { position: "bottom-center" })
    return
  }

  const header = ["Factura", "Cliente", "Fecha", "Items", "Subtotal", "IVA", "Total", "Estado"]
  //  Comillas dobles escapadas: un nombre de cliente con coma partiría la fila.
  const escape = (value: string | number) => `"${String(value).replace(/"/g, '""')}"`
  const body = rows.map(bill => [
    bill.bill_number,
    bill.customer_name,
    bill.created_at.slice(0, 10),
    bill.items_count,
    bill.subtotal,
    bill.total_iva,
    bill.total,
    //  Anulada primero: exportar una factura anulada con su estado fiscal
    //  la haría contar como venta en la hoja de cálculo.
    bill.voided_at !== null ? "anulada" : bill.fiscal_status ?? "sin declarar",
  ].map(escape).join(","))

  //  BOM al inicio: sin él Excel en Windows abre el CSV en ANSI y parte las tildes.
  const csv = `﻿${[header.map(escape).join(","), ...body].join("\r\n")}`
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8;" }))
  const link = document.createElement("a")
  link.href = url
  link.download = `facturas-pagina-${page.value}.csv`
  link.click()
  URL.revokeObjectURL(url)

  toast.success(`${rows.length} facturas exportadas`, { position: "bottom-center" })
}

onMounted(load)
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
      <div class="min-w-0 px-6 space-y-6 pb-6">
        <header class="flex h-(--header-height) shrink-0 items-center gap-2 border-b">
          <div class="flex w-full items-center gap-1 px-4 lg:gap-2 lg:px-6">
            <SidebarTrigger class="-ml-1" />
            <Separator orientation="vertical" class="mx-2 data-[orientation=vertical]:h-4" />
            <ModuleNavSelect current="invoices" />
            <div class="ml-auto flex items-center gap-2">
              <Sun class="size-4 text-muted-foreground" />
              <Switch v-model="isDark" aria-label="Cambiar a tema oscuro" />
              <Moon class="size-4 text-muted-foreground" />
            </div>
          </div>
        </header>

        <!-- Fila 1 — filtros -->
        <div class="flex flex-col gap-4 md:flex-row md:items-end">
          <div class="grid w-full gap-2 md:max-w-56">
            <Label for="filter-customer">Nombre Cliente</Label>
            <Input id="filter-customer" v-model="filters.customer" placeholder="Buscar cliente…" />
          </div>

          <div class="grid w-full gap-2 md:max-w-44">
            <Label for="filter-bill-number">Código Factura</Label>
            <Input id="filter-bill-number" v-model="filters.billNumber" placeholder="FV-2600" />
          </div>

          <div class="grid w-full gap-2 md:max-w-64">
            <Label>Rango de Fechas</Label>
            <DateRangePicker
              v-model:from="filters.dateFrom"
              v-model:to="filters.dateTo"
            />
          </div>

          <div class="grid w-full gap-2 md:max-w-48">
            <Label for="filter-status">Estado</Label>
            <Select v-model="filters.status">
              <SelectTrigger id="filter-status" class="w-full">
                <SelectValue placeholder="Todos" />
              </SelectTrigger>
              <SelectContent>
                <!--
                  Eje documento (D-81). Antes acá vivían los 4 estados fiscales
                  DIAN, que con la integración diferida (D-09/D-38) filtraban
                  siempre a cero: `fiscal_status` es `NULL` en todas. Y el
                  filtro tampoco ofrecía "anulada", que es el único estado que
                  hoy varía de verdad — se filtraba por lo que no cambia y no
                  por lo que sí.
                -->
                <SelectItem :value="ALL_STATUSES">
                  Todas
                </SelectItem>
                <SelectItem value="vigentes">
                  Vigentes
                </SelectItem>
                <SelectItem value="anuladas">
                  Anuladas
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <!--
            Siempre montado: con `v-if` el botón entra y sale del flex y corre
            de lugar a todo lo que tiene al lado (mismo criterio que Productos).
          -->
          <Button
            variant="ghost"
            :class="hasFilters ? '' : 'invisible pointer-events-none'"
            :tabindex="hasFilters ? 0 : -1"
            :aria-hidden="!hasFilters"
            @click="clearFilters"
          >
            Limpiar
          </Button>

          <!--
            Un solo botón con las dos salidas, y no dos botones "Exportar"
            compitiendo: son cosas distintas (el paquete sale del servidor
            sobre todo el corte filtrado; el CSV es lo que hay en pantalla) y
            ponerlas lado a lado obligaría a adivinar cuál es cuál.
          -->
          <Popover v-model:open="isExportMenuOpen">
            <PopoverTrigger as-child>
              <Button variant="outline" class="shrink-0 gap-2">
                <IconDownload class="size-4" />
                Exportar
              </Button>
            </PopoverTrigger>
            <PopoverContent align="end" class="w-80">
              <div class="grid gap-1">
                <Button
                  variant="ghost"
                  class="h-auto w-full justify-start gap-3 whitespace-normal px-2 py-2"
                  @click="openPackageDialog"
                >
                  <IconPackage class="size-4 shrink-0 text-brand-icon" />
                  <span class="grid min-w-0 gap-0.5 text-left">
                    <span class="text-sm font-medium">Paquete de facturas</span>
                    <span class="text-xs font-normal text-muted-foreground">
                      .zip con un PDF por factura y un Excel índice. Todo el
                      corte filtrado, no solo esta página.
                    </span>
                  </span>
                </Button>
                <Button
                  variant="ghost"
                  class="h-auto w-full justify-start gap-3 whitespace-normal px-2 py-2"
                  @click="exportCsv"
                >
                  <IconTable class="size-4 shrink-0 text-brand-icon" />
                  <span class="grid min-w-0 gap-0.5 text-left">
                    <span class="text-sm font-medium">Solo la tabla (CSV)</span>
                    <span class="text-xs font-normal text-muted-foreground">
                      Las filas de esta página, o las que tengas marcadas. Sin
                      documentos.
                    </span>
                  </span>
                </Button>
              </div>
            </PopoverContent>
          </Popover>
        </div>

        <!--
          Fila 2 — métricas. Fórmulas fijadas por D-49 para que no se calculen
          distinto en cada pantalla. Respetan los filtros activos.
        -->
        <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <template v-if="store.isLoadingSummary || !store.summary">
            <div
              v-for="placeholder in 4"
              :key="placeholder"
              class="min-h-26 space-y-2 rounded-xl border border-border px-4 py-3"
            >
              <Skeleton class="h-4 w-32" />
              <Skeleton class="h-8 w-28" />
              <Skeleton class="h-3 w-24" />
            </div>
          </template>

          <template v-else>
            <div class="min-h-26 rounded-xl border-2 border-primary px-4 py-3">
              <p class="text-sm text-muted-foreground">
                Total facturado
              </p>
              <p
                class="truncate text-xl font-bold tabular-nums text-brand-icon"
                :title="money(store.summary.total_billed)"
              >
                {{ money(store.summary.total_billed) }}
              </p>
              <p class="truncate text-xs text-muted-foreground">
                Con IVA incluido
              </p>
            </div>

            <div class="min-h-26 rounded-xl border border-border px-4 py-3">
              <p class="text-sm text-muted-foreground">
                IVA recaudado
              </p>
              <p
                class="truncate text-xl font-bold tabular-nums"
                :title="money(store.summary.total_iva)"
              >
                {{ money(store.summary.total_iva) }}
              </p>
              <p class="truncate text-xs text-muted-foreground">
                Lo que se le debe a la DIAN
              </p>
            </div>

            <div class="min-h-26 rounded-xl border border-border px-4 py-3">
              <p class="text-sm text-muted-foreground">
                Total Utilidades
              </p>
              <p
                class="truncate text-xl font-bold tabular-nums"
                :title="money(store.summary.total_profit)"
              >
                {{ money(store.summary.total_profit) }}
              </p>
              <!--
                Si faltan costos se dice: una utilidad incompleta que se ve
                completa engaña sobre cuánto se ganó de verdad.
              -->
              <p
                class="truncate text-xs"
                :class="store.summary.units_without_cost > 0 ? 'text-destructive' : 'text-muted-foreground'"
              >
                {{
                  store.summary.units_without_cost > 0
                    ? `${store.summary.units_without_cost} unidades sin costo`
                    : "Venta menos costo de proveedor"
                }}
              </p>
            </div>

            <div class="min-h-26 rounded-xl border border-border px-4 py-3">
              <p class="text-sm text-muted-foreground">
                N.º de facturas
              </p>
              <p class="text-xl font-bold tabular-nums">
                {{ store.summary.total_bills }}
              </p>
              <!--
                Solo las anuladas (D-81). El desglose fiscal que había acá
                —declaradas / sin declarar— se retiró: con la DIAN diferida
                (D-09/D-38) el primero era siempre 0 y el segundo siempre igual
                al total, y "29 sin declarar" se lee como una deuda con la DIAN
                cuando en realidad el trámite no existe todavía.

                Las anuladas sí se dicen: el conteo de facturas las incluye
                mientras que las cifras de dinero no (D-60), así que sin este
                renglón las cuatro cards parecerían no cuadrar entre sí.
              -->
              <p
                class="truncate text-xs text-muted-foreground"
                :class="store.summary.voided_bills > 0 ? '' : 'invisible'"
              >
                {{ store.summary.voided_bills }}
                {{ store.summary.voided_bills === 1 ? "anulada" : "anuladas" }}
                · no suman al dinero
              </p>
            </div>
          </template>
        </div>

        <!-- Fila 3 — tabla de facturas -->
        <div v-if="store.isLoading" class="space-y-3">
          <Skeleton v-for="placeholder in PAGE_SIZE" :key="placeholder" class="h-16 w-full rounded-lg" />
        </div>

        <!-- Falló la carga: no es lo mismo que "no hay resultados". -->
        <div
          v-else-if="store.hasError"
          class="flex flex-col items-center gap-2 rounded-lg border border-border py-16"
        >
          <p class="text-destructive">
            No se pudieron cargar las facturas.
          </p>
          <Button variant="outline" size="sm" @click="load">
            Reintentar
          </Button>
        </div>

        <div
          v-else-if="store.bills.length === 0"
          class="rounded-lg border border-dashed border-border py-16 text-center text-muted-foreground"
        >
          {{
            hasFilters
              ? "No hay facturas que coincidan con los filtros."
              : "Aún no hay facturas registradas."
          }}
        </div>

        <template v-else>
          <div class="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-muted/30 px-4 py-2">
            <label class="flex items-center gap-2 text-sm">
              <Checkbox
                :model-value="selectAllState"
                @update:model-value="value => toggleSelectAll(value === true)"
              />
              <span>
                {{ selectedIds.size > 0 ? `${selectedIds.size} seleccionadas` : "Seleccionar todas" }}
              </span>
            </label>

            <!--
              Solo con algo marcado: un botón que dice "exportar selección"
              cuando no hay selección no tiene qué hacer, y deshabilitado
              ocuparía el lugar sin explicar por qué.
            -->
            <div v-if="selectedIds.size > 0" class="flex items-center gap-2">
              <Button variant="outline" size="sm" class="gap-2" @click="openPackageDialog(true)">
                <IconPackage class="size-4" />
                Exportar {{ selectedIds.size }}
              </Button>
              <Button variant="ghost" size="sm" @click="selectedIds.clear()">
                Quitar selección
              </Button>
            </div>
          </div>

          <div class="space-y-3">
            <InvoiceCard
              v-for="bill in store.bills"
              :key="bill.id"
              :bill="bill"
              :selected="selectedIds.has(bill.id)"
              @update:selected="value => toggleSelected(bill.id, value)"
            />
          </div>

          <Pagination
            v-slot="{ page: current }"
            :items-per-page="PAGE_SIZE"
            :total="store.total"
            :page="page"
            @update:page="value => page = value"
          >
            <PaginationContent class="flex items-center gap-2">
              <PaginationPrevious />
              <PaginationItem :value="current" is-active>
                {{ current }}
              </PaginationItem>
              <span class="text-sm text-muted-foreground">de {{ totalPages }}</span>
              <PaginationNext />
            </PaginationContent>
          </Pagination>
        </template>

        <p
          class="text-center text-sm text-muted-foreground"
          :class="store.bills.length > 0 ? '' : 'invisible'"
        >
          {{ store.bills.length }} de {{ store.total }}
          {{ store.total === 1 ? "factura" : "facturas" }}
        </p>
      </div>
    </SidebarInset>

    <ExportBillsDialog
      v-model:open="isPackageDialogOpen"
      :filters="exportFilters"
    />
  </SidebarProvider>
</template>
