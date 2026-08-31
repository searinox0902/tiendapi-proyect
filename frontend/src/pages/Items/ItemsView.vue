<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue"
import { useInfiniteScroll, watchDebounced } from "@vueuse/core"
import {
  IconDownload,
  IconFileSpreadsheet,
  IconFileUpload,
  IconJson,
  IconMarkdown,
  IconPhoto,
  IconPlus,
} from "@tabler/icons-vue"
import { Moon, Sun } from "@lucide/vue"
import { toast } from "vue-sonner"
import { useRouter } from "vue-router"

import AppSidebar from "@/components/AppSidebar.vue"
import ModuleNavSelect from "@/components/ModuleNavSelect.vue"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import ReferenceSearchInput from "@/components/ReferenceSearchInput.vue"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Label } from "@/components/ui/label"
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
import { formatCurrency, formatPercentage, toDecimal } from "@/lib/money"
import { useItemsStore } from "@/stores/items"
import { useReferencesStore } from "@/stores/references"
import { itemsApi } from "@/api/items/items.api"
import { downloadBlob } from "@/lib/download"
import type { IItemStockFilters, TStockSort, TStockStatus } from "@/api/items/items.types"
import type { TExportFormat } from "@/api/references/references.types"
import ImportProductsDialog from "./ImportProductsDialog.vue"

const router = useRouter()

/** `SelectItem` de reka-ui no acepta value vacío, así que la opción "todas" necesita un centinela. */
const ALL_CATEGORIES = "__all__"
/** Múltiplo de 4 para que la última fila de la grilla no quede coja. Tamaño de cada tanda del scroll infinito. */
const BATCH_SIZE = 12

const store = useItemsStore()
/**
 * Las categorías son una entidad compartida, no un dato de la pantalla de
 * Referencias: se reusa ese store en vez de duplicar `fetchCategories` y el
 * mapeo id → nombre.
 */
const referencesStore = useReferencesStore()

const filters = reactive({
  /**
   * Un solo campo para código **y** nombre (D-91). Reemplaza a los filtros
   * `sku` y `title` separados, que el backend cruzaba con **AND**: se podía
   * pedir "sku contiene FRE Y nombre contiene pastilla". Ahora usa `search`,
   * que es **OR** — el mismo parámetro que la caja usa desde antes, porque
   * quien busca un repuesto recuerda el código o el nombre, no los dos.
   */
  search: "",
  brand: "",
  category: ALL_CATEGORIES,
  /** Lo selecciona el clic en las cards de resumen, no un input. */
  stockStatus: "all" as TStockStatus,
  sort: "newest" as TStockSort,
})

/** Los filtros vacíos se omiten: el backend los trata como "sin filtro". */
function currentParams(skip: number): IItemStockFilters {
  return {
    search: filters.search.trim() || undefined,
    brand: filters.brand.trim() || undefined,
    category_id: filters.category === ALL_CATEGORIES ? undefined : filters.category,
    stock_status: filters.stockStatus,
    sort: filters.sort,
    skip,
    limit: BATCH_SIZE,
  }
}

/**
 * El resumen NO lleva `stock_status`: las cards son el marco desde el que se
 * filtra, así que sus conteos describen el conjunto de texto/categoría. Si se
 * recalcularan sobre el estado seleccionado, al entrar a "Agotados" las demás
 * cards quedarían en cero y no habría desde dónde volver.
 */
function summaryParams(): IItemStockFilters {
  const { stock_status: _ignored, sort: _sort, skip: _skip, limit: _limit, ...rest } = currentParams(0)
  return rest
}

/**
 * Clic en una card: alterna ese estado. Volver a hacer clic en la card activa
 * deselecciona (vuelve a "todos"), que es lo que uno espera de un toggle.
 */
function toggleStockStatus(status: TStockStatus) {
  filters.stockStatus = filters.stockStatus === status ? "all" : status
}

/** Aún quedan Referencias por traer más allá de lo ya cargado. */
const hasMore = computed(() => store.stock.length < store.total)
/** Se prende si la última tanda falló, para no reintentar en bucle apenas el scroll siga en el fondo. */
const loadMoreFailed = ref(false)

/**
 * Carga inicial o recarga por cambio de filtros: reemplaza la grilla desde cero
 * y recalcula las cifras de cabecera, que describen el conjunto filtrado.
 * Van en paralelo porque no dependen una de la otra.
 */
async function load() {
  loadMoreFailed.value = false
  const [grid] = await Promise.allSettled([
    store.fetchStock(currentParams(0)),
    // El resumen es accesorio: si falla, la grilla sigue sirviendo y no se
    // apila un segundo toast encima del de abajo.
    store.fetchSummary(summaryParams()),
  ])
  if (grid.status === "rejected") {
    toast.error("No se pudieron cargar los productos", { position: "bottom-center" })
  }
}

/** Siguiente tanda al llegar cerca del final del scroll. `skip` es lo ya cargado, no una página. */
async function loadMore() {
  try {
    await store.fetchStock(currentParams(store.stock.length), { append: true })
    loadMoreFailed.value = false
  } catch {
    loadMoreFailed.value = true
    toast.error("No se pudieron cargar más productos", { position: "bottom-center" })
  }
}

/** Filtros reactivos con debounce: tecleando "FRE-0001" se dispararía una consulta por carácter. */
watchDebounced(filters, load, { debounce: 350 })

/**
 * Scroll infinito nativo de vueuse sobre la ventana (la página entera scrollea,
 * `SidebarInset` no tiene su propio contenedor con overflow). `distance: 300`
 * dispara `loadMore` un poco antes de tocar fondo, para que la tanda nueva ya
 * esté cargando cuando el usuario llega. `canLoadMore` es la única guardia
 * necesaria: vueuse ya evita solapar llamadas mientras la anterior no resuelve,
 * pero no sabe de `store.isLoading` (recarga por cambio de filtro, una petición
 * aparte) ni de `loadMoreFailed` (si no se corta acá, reintentaría cada ~100ms
 * mientras el scroll siga en el fondo).
 */
useInfiniteScroll(window, loadMore, {
  distance: 300,
  canLoadMore: () => hasMore.value && !loadMoreFailed.value && !store.isLoading && !store.isLoadingMore,
})

const hasFilters = computed(() =>
  filters.search !== ""
  || filters.brand !== ""
  || filters.category !== ALL_CATEGORIES
  || filters.stockStatus !== "all",
)

function clearFilters() {
  filters.search = ""
  filters.brand = ""
  filters.category = ALL_CATEGORIES
  filters.stockStatus = "all"
}

/**
 * `sale_price` llega como string ("12900.00") y pasa por `Decimal` sin tocar
 * float en ningún punto — regla del proyecto para dinero.
 */
function formatPrice(value: string) {
  return formatCurrency(toDecimal(value))
}

const IMPORT_FORMATS = [
  { value: "json", label: "JSON", hint: "El que exporta el propio sistema", icon: IconJson, accept: "application/json,.json" },
  { value: "xlsx", label: "Excel", hint: "La plantilla .xlsx exportada", icon: IconFileSpreadsheet, accept: ".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" },
] as const

const EXPORT_FORMATS = [
  //  Excel primero y con la etiqueta que importa: es el **mismo** archivo que
  //  el importador acepta (D-74/D-92), o sea el que sirve para editar en una
  //  hoja y volver a subir. JSON también vuelve a entrar; markdown es solo
  //  para leer.
  { value: "xlsx", label: "Excel", hint: "El que se puede editar y volver a importar", icon: IconFileSpreadsheet },
  { value: "json", label: "JSON", hint: "Mismo contenido, para integraciones", icon: IconJson },
  { value: "markdown", label: "Markdown", hint: "Tabla para leer o pegar (.md)", icon: IconMarkdown },
] as const

const exportOpen = ref(false)
const isExporting = ref(false)
/** Arranca en "todo": es lo que la gente espera de un botón que dice Exportar. */
const exportScope = ref<"all" | "filtered">("all")

/**
 * Filtros que viajan al exportar "lo filtrado".
 *
 * No incluye `sort`: el orden de la grilla es de presentación y el archivo
 * sale siempre por SKU, que es como se busca una fila en una hoja de cálculo.
 */
function exportFilters(): IItemStockFilters {
  return {
    search: filters.search.trim() || undefined,
    brand: filters.brand.trim() || undefined,
    category_id: filters.category === ALL_CATEGORIES ? undefined : filters.category,
    stock_status: filters.stockStatus,
  }
}

async function downloadExport(format: TExportFormat) {
  if (isExporting.value) {
    return
  }
  isExporting.value = true
  try {
    //  Se mandan los mismos filtros que la grilla, y el backend los aplica con
    //  las mismas condiciones (`items.py:_stock_conditions`): el archivo no
    //  puede discrepar de lo que se está viendo en pantalla.
    const { data, headers } = await itemsApi.exportProducts(
      format,
      exportScope.value === "filtered" ? exportFilters() : {},
    )
    //  El nombre lo decide el backend (lleva la fecha). El respaldo local entra
    //  solo si `Content-Disposition` no viajó.
    downloadBlob(data, headers, `productos.${format === "markdown" ? "md" : format}`)
    exportOpen.value = false
    toast.success("Existencias exportadas", { position: "bottom-center" })
  } catch (error) {
    console.error("Export products failed:", error)
    toast.error("No se pudieron exportar las existencias", { position: "bottom-center" })
  } finally {
    isExporting.value = false
  }
}

const importOpen = ref(false)
const importMenuOpen = ref(false)
const importDialogRef = ref<InstanceType<typeof ImportProductsDialog> | null>(null)

function pickImportFile(option: (typeof IMPORT_FORMATS)[number]) {
  importMenuOpen.value = false
  importDialogRef.value?.pickFile(option.accept)
}

/**
 * El inventario cambió por fuera de la grilla. Se recarga desde cero —y no se
 * hace un append— porque una importación puede crear productos nuevos que
 * caen en cualquier página del orden actual, no al final.
 */
function onImported() {
  load()
}

function addItems() {
  router.push({ name: "items-new" })
}

/** El margen llega como "36.81"; se muestra con coma decimal, igual que el dinero. */
const marginLabel = computed(() =>
  store.summary === null ? "" : formatPercentage(store.summary.margin_percentage),
)

/**
 * La card lleva al aterrizaje del producto. Viaja `reference_id` y no el SKU
 * porque el SKU no es único a nivel de esquema (ver el ORDER BY del endpoint
 * `/items/stock`), así que como identificador de ruta sería ambiguo.
 */
function openProduct(referenceId: string) {
  router.push({ name: "items-detail", params: { referenceId } })
}

onMounted(() => {
  referencesStore.fetchCategories().catch(() => {
    toast.error("No se pudieron cargar las categorías", { position: "bottom-center" })
  })
  load()
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
      <div class="min-w-0 px-6 space-y-6 pb-6">
        <header class="flex h-(--header-height) shrink-0 items-center gap-2 border-b">
          <div class="flex w-full items-center gap-1 px-4 lg:gap-2 lg:px-6">
            <SidebarTrigger class="-ml-1" />
            <Separator orientation="vertical" class="mx-2 data-[orientation=vertical]:h-4" />
            <ModuleNavSelect current="items" />
            <div class="ml-auto flex items-center gap-2">
              <Popover v-model:open="importMenuOpen">
                <PopoverTrigger as-child>
                  <Button variant="outline" size="sm" class="gap-1.5">
                    <IconFileUpload class="size-4" />
                    Importar
                  </Button>
                </PopoverTrigger>
                <PopoverContent align="start" class="w-64">
                  <div class="grid gap-1">
                    <p class="px-2 py-1.5 text-sm font-medium">
                      Importar existencias
                    </p>
                    <Button
                      v-for="option in IMPORT_FORMATS"
                      :key="option.value"
                      variant="ghost"
                      class="h-auto w-full justify-start gap-3 whitespace-normal px-2 py-2"
                      @click="pickImportFile(option)"
                    >
                      <component :is="option.icon" class="size-4 shrink-0 text-brand-icon" />
                      <span class="grid min-w-0 gap-0.5 text-left">
                        <span class="text-sm font-medium">{{ option.label }}</span>
                        <span class="text-xs font-normal text-muted-foreground">{{ option.hint }}</span>
                      </span>
                    </Button>
                  </div>
                </PopoverContent>
              </Popover>

              <Popover v-model:open="exportOpen">
                <PopoverTrigger as-child>
                  <Button variant="outline" size="sm" class="gap-1.5">
                    <IconDownload class="size-4" />
                    Exportar
                  </Button>
                </PopoverTrigger>
                <PopoverContent align="end" class="w-80">
                  <div class="grid gap-4">
                    <div class="grid gap-1">
                      <p class="text-sm font-medium">
                        Exportar existencias
                      </p>
                      <p class="text-xs text-muted-foreground">
                        Una fila por grupo de unidades iguales. Sin existencias
                        igual se descarga, con las columnas listas para usar de
                        plantilla.
                      </p>
                    </div>

                    <!--
                      Alcance visible y no implícito, mismo criterio que en
                      Referencias: sin esto es imposible saber si el archivo
                      trae el inventario entero o solo lo filtrado, y el error
                      se descubre tarde.
                    -->
                    <div class="grid grid-cols-2 gap-2">
                      <button
                        type="button"
                        :aria-pressed="exportScope === 'all'"
                        class="rounded-md border px-3 py-2 text-left transition-colors"
                        :class="exportScope === 'all'
                          ? 'border-primary bg-primary/10'
                          : 'border-border hover:border-primary/50'"
                        @click="exportScope = 'all'"
                      >
                        <span class="block text-xs text-muted-foreground">Todo</span>
                        <span class="block text-sm font-medium">Inventario completo</span>
                      </button>
                      <button
                        type="button"
                        :aria-pressed="exportScope === 'filtered'"
                        :disabled="!hasFilters"
                        class="rounded-md border px-3 py-2 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-50"
                        :class="exportScope === 'filtered'
                          ? 'border-primary bg-primary/10'
                          : 'border-border hover:border-primary/50'"
                        @click="exportScope = 'filtered'"
                      >
                        <span class="block text-xs text-muted-foreground">Filtrado</span>
                        <span class="block text-sm font-medium tabular-nums">
                          {{ store.total }} {{ store.total === 1 ? "producto" : "productos" }}
                        </span>
                      </button>
                    </div>

                    <div class="grid gap-1">
                      <Button
                        v-for="option in EXPORT_FORMATS"
                        :key="option.value"
                        variant="ghost"
                        class="h-auto w-full justify-start gap-3 whitespace-normal px-2 py-2"
                        :disabled="isExporting"
                        @click="downloadExport(option.value)"
                      >
                        <component :is="option.icon" class="size-4 shrink-0 text-brand-icon" />
                        <span class="grid min-w-0 gap-0.5 text-left">
                          <span class="text-sm font-medium">{{ option.label }}</span>
                          <span class="text-xs font-normal text-muted-foreground">{{ option.hint }}</span>
                        </span>
                      </Button>
                    </div>
                  </div>
                </PopoverContent>
              </Popover>

              <Separator orientation="vertical" class="data-[orientation=vertical]:h-4" />
              <Sun class="size-4 text-muted-foreground" />
              <Switch v-model="isDark" aria-label="Cambiar a tema oscuro" />
              <Moon class="size-4 text-muted-foreground" />
            </div>
          </div>
        </header>

        <!--
          Resumen del conjunto filtrado. Cuatro cifras que responden, en orden:
          cuánto hay, qué exige acción, cuánta plata está parada y si el precio
          deja margen sano.
        -->
        <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <!--
            `min-h-26` va en el skeleton Y en las cards reales: sin una altura
            común, el skeleton medía 102px y el contenido 96px, y la fila entera
            saltaba 6px cada vez que se cambiaba un filtro.
          -->
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
            <!--
              Las tres primeras cards son estados de una misma dimensión (stock),
              así que se comportan como un grupo de radio: por eso `aria-pressed`
              y no `checkbox`. La cuarta es contexto de plata, no un subconjunto
              filtrable — dejarla clicable prometería un filtro que no existe.
            -->
            <button
              type="button"
              :aria-pressed="filters.stockStatus === 'all'"
              class="min-h-26 rounded-xl border px-4 py-3 text-left transition-all hover:border-primary"
              :class="filters.stockStatus === 'all' ? 'border-primary ring-2 ring-primary/30' : 'border-border'"
              @click="filters.stockStatus = 'all'"
            >
              <p class="text-sm text-muted-foreground">
                Total Productos
              </p>
              <p class="text-2xl font-bold tabular-nums">
                {{ store.summary.total_references }}
              </p>
              <!-- Productos y unidades no son lo mismo (D-41): 29 productos pueden ser 453 unidades. -->
              <p class="truncate text-xs text-muted-foreground" :title="`${store.summary.total_units} unidades en existencia`">
                {{ store.summary.total_units }}
                {{ store.summary.total_units === 1 ? "unidad en existencia" : "unidades en existencia" }}
              </p>
            </button>

            <!-- Agotados: venta que ya se está perdiendo. -->
            <button
              type="button"
              :aria-pressed="filters.stockStatus === 'out_of_stock'"
              class="min-h-26 rounded-xl border px-4 py-3 text-left transition-all hover:border-destructive"
              :class="filters.stockStatus === 'out_of_stock'
                ? 'border-destructive ring-2 ring-destructive/30'
                : 'border-border'"
              @click="toggleStockStatus('out_of_stock')"
            >
              <p class="text-sm text-muted-foreground">
                Agotados
              </p>
              <p
                class="text-2xl font-bold tabular-nums"
                :class="store.summary.out_of_stock_references > 0 ? 'text-destructive' : ''"
              >
                {{ store.summary.out_of_stock_references }}
              </p>
              <p class="truncate text-xs text-muted-foreground">
                {{ store.summary.out_of_stock_references === 0 ? "Nada por reponer" : "Sin unidades para vender" }}
              </p>
            </button>

            <!-- Stock bajo: la venta que TODAVÍA se puede salvar reponiendo. -->
            <button
              type="button"
              :aria-pressed="filters.stockStatus === 'low_stock'"
              class="min-h-26 rounded-xl border px-4 py-3 text-left transition-all hover:border-primary"
              :class="filters.stockStatus === 'low_stock' ? 'border-primary ring-2 ring-primary/30' : 'border-border'"
              @click="toggleStockStatus('low_stock')"
            >
              <p class="text-sm text-muted-foreground">
                Stock Bajo
              </p>
              <p class="text-2xl font-bold tabular-nums">
                {{ store.summary.low_stock_references }}
              </p>
              <p class="truncate text-xs text-muted-foreground">
                {{ store.summary.low_stock_threshold }} unidades o menos
              </p>
            </button>

            <div class="min-h-26 rounded-xl border-2 border-primary px-4 py-3">
              <p class="text-sm text-muted-foreground">
                Capital Invertido
              </p>
              <!--
                `text-xl` y no `text-2xl`: un total de inventario de 8 dígitos
                se partía en dos líneas y, como la fila se estira a la card más
                alta, empujaba a las otras tres. `truncate` es la red de
                seguridad para montos aún mayores, con el valor completo en el
                `title`.
              -->
              <p
                class="truncate text-xl font-bold tabular-nums text-brand-icon"
                :title="formatPrice(store.summary.total_cost)"
              >
                {{ formatPrice(store.summary.total_cost) }}
              </p>
              <!--
                Si faltan costos, se dice: un total incompleto que se ve
                completo engaña. El texto se mantiene corto a propósito — con el
                valor de venta adentro no cabía en una línea y el `truncate`
                terminaba cortando justo el margen, que es el dato que importa.
                El detalle completo queda en el `title`.
              -->
              <p
                class="truncate text-xs"
                :class="store.summary.units_without_cost > 0 ? 'text-destructive' : 'text-muted-foreground'"
                :title="store.summary.units_without_cost > 0
                  ? `${store.summary.units_without_cost} unidades sin precio de proveedor cargado`
                  : `Margen de ${marginLabel}% sobre ${formatPrice(store.summary.total_sale_value)} de venta potencial`"
              >
                {{
                  store.summary.units_without_cost > 0
                    ? `${store.summary.units_without_cost} unidades sin costo`
                    : `Margen ${marginLabel}%`
                }}
              </p>
            </div>
          </template>
        </div>

        <!-- Filtros -->
        <div class="flex items-center gap-4">
          <div class="flex flex-1 flex-col gap-4 md:flex-row md:items-end">
            <div class="grid w-full gap-2 md:max-w-72">
              <Label for="filter-search">Código o nombre</Label>
              <!-- Patrón de autocompletado contra el servidor (D-91): el mismo
                   componente que el alta de Referencia. Elegir una sugerencia
                   deja su SKU en el campo, o sea acota la grilla a esa pieza. -->
              <ReferenceSearchInput
                id="filter-search"
                v-model="filters.search"
                placeholder="FRE-0001, pastillas, bujía…"
                hint="Coincidencias en tu catálogo"
                empty-hint="Tu catálogo — escribí un código o un nombre"
              />
            </div>

            <div class="grid w-full gap-2 md:max-w-44">
              <Label for="filter-brand">Marca</Label>
              <Input id="filter-brand" v-model="filters.brand" placeholder="NGK, Brembo…" />
            </div>

            <div class="grid w-full gap-2 md:max-w-52">
              <Label for="filter-category">Categoría</Label>
              <Select v-model="filters.category">
                <SelectTrigger id="filter-category" class="w-full">
                  <SelectValue placeholder="Todas" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem :value="ALL_CATEGORIES">
                    Todas
                  </SelectItem>
                  <SelectItem
                    v-for="category in referencesStore.categories"
                    :key="category.id"
                    :value="category.id"
                  >
                    {{ category.name }}
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div class="grid w-full gap-2 md:max-w-48">
              <Label for="filter-sort">Ordenar por</Label>
              <Select v-model="filters.sort">
                <SelectTrigger id="filter-sort" class="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="newest">
                    Más reciente
                  </SelectItem>
                  <SelectItem value="oldest">
                    Más antiguo
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <!--
              Siempre montado: con `v-if` el botón entraba y salía del flex y
              corría de lugar a todo lo que tiene al lado. `invisible` le deja
              el espacio reservado; `pointer-events-none` + `tabindex="-1"`
              evitan que se pueda clickear o tabular estando oculto.
            -->
            <Button
              variant="ghost"
              class="md:mb-0 mt-2"
              :class="hasFilters ? '' : 'invisible pointer-events-none'"
              :tabindex="hasFilters ? 0 : -1"
              :aria-hidden="!hasFilters"
              @click="clearFilters"
            >
              Limpiar
            </Button>
          </div>

          <Button class="flex-no-wrap justify-start gap-2 text-white mt-5 hover:text-white" @click="addItems">
            
            Agregar
            <IconPlus class="size-4" />
          </Button>
        </div>

        <!--
          Grilla. Se pintan `BATCH_SIZE` skeletons, no un puñado: la tanda que
          va a llegar tiene ese tamaño, así que con menos la página crecería de
          golpe al resolver la petición. Con 4 el salto era de dos filas.
        -->
        <div v-if="store.isLoading" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card v-for="placeholder in BATCH_SIZE" :key="placeholder" class="gap-0 overflow-hidden p-0">
            <Skeleton class="aspect-square w-full rounded-none" />
            <CardContent class="min-h-33 space-y-2 p-4">
              <Skeleton class="h-4 w-24" />
              <Skeleton class="h-3 w-32" />
              <Skeleton class="h-5 w-20" />
            </CardContent>
          </Card>
        </div>

        <!-- Falló la carga: no es lo mismo que "no hay resultados". -->
        <div
          v-else-if="store.hasError"
          class="flex flex-col items-center gap-2 rounded-lg border border-border py-16"
        >
          <p class="text-destructive">
            No se pudieron cargar los productos.
          </p>
          <Button variant="outline" size="sm" @click="load">
            Reintentar
          </Button>
        </div>

        <div
          v-else-if="store.stock.length === 0"
          class="rounded-lg border border-dashed border-border py-16 text-center text-muted-foreground"
        >
          {{
            hasFilters
              ? "No hay productos que coincidan con los filtros."
              : "Aún no hay productos registrados."
          }}
        </div>

        <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card
            v-for="product in store.stock"
            :key="product.reference_id"
            class="gap-0 overflow-hidden p-0 cursor-pointer pointer hover:border-primary fade-in-55 transition-all"
            @click="openProduct(product.reference_id)"
          >
            <!-- 1:1 fijo: las imágenes ya se recortan cuadradas al capturarlas (D-50). -->
            <img
              v-if="product.image_url"
              :src="product.image_url"
              :alt="product.title"
              class="aspect-square w-full border-b border-border object-cover"
            >
            <div
              v-else
              class="flex aspect-square w-full items-center justify-center border-b border-dashed border-border text-muted-foreground"
            >
              <IconPhoto class="size-8" />
            </div>

            <CardContent class="min-h-33 space-y-3 p-4">
              <div class="flex items-start justify-between gap-2">
                <div class="min-w-0">
                  <p class="truncate font-medium">
                    {{ product.sku }}
                  </p>
                  <p class="truncate text-sm text-muted-foreground">
                    {{ product.title }}
                  </p>
                </div>
                <!-- Agotado se resalta: es la card sobre la que hay que actuar. -->
                <Badge :variant="product.units === 0 ? 'destructive' : 'secondary'" class="shrink-0">
                  {{ product.units }} {{ product.units === 1 ? "unidad" : "unidades" }}
                </Badge>
              </div>

              <div class="flex items-end justify-between gap-2">
                <div class="min-w-0">
                  <p class="text-xs text-muted-foreground">
                    Precio de venta
                  </p>
                  <p class="truncate text-lg font-semibold tabular-nums">
                    {{ formatPrice(product.sale_price) }}
                  </p>
                </div>
                <Badge variant="outline" class="shrink-0 max-w-32 truncate">
                  {{ referencesStore.categoryName(product.category_id) }}
                </Badge>
              </div>
            </CardContent>
          </Card>

          <!-- Placeholders de la siguiente tanda mientras carga, para que la grilla no dé un salto vacío. -->
          <template v-if="store.isLoadingMore">
            <Card v-for="placeholder in 4" :key="`more-${placeholder}`" class="gap-0 overflow-hidden p-0">
              <Skeleton class="aspect-square w-full rounded-none" />
              <CardContent class="min-h-33 space-y-2 p-4">
                <Skeleton class="h-4 w-24" />
                <Skeleton class="h-3 w-32" />
                <Skeleton class="h-5 w-20" />
              </CardContent>
            </Card>
          </template>
        </div>

        <!--
          Siempre ocupa su línea, aunque no haya nada que contar: con `v-if` el
          pie aparecía y desaparecía y movía el final de la página.
        -->
        <p
          class="text-center text-sm text-muted-foreground"
          :class="store.stock.length > 0 ? '' : 'invisible'"
        >
          {{ store.stock.length }} de {{ store.total }}
          {{ store.total === 1 ? "producto" : "productos" }}
        </p>
      </div>
    </SidebarInset>

    <ImportProductsDialog ref="importDialogRef" v-model:open="importOpen" @imported="onImported" />
  </SidebarProvider>
</template>
