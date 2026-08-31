<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue"
import {
  IconChevronLeft,
  IconPencil,
  IconPhoto,
  IconPlus,
  IconRotate,
  IconSearch,
  IconTrash,
} from "@tabler/icons-vue"
import { Moon, Sun } from "@lucide/vue"
import { toast } from "vue-sonner"
import { useRouter } from "vue-router"

import AppSidebar from "@/components/AppSidebar.vue"
import ModuleNavSelect from "@/components/ModuleNavSelect.vue"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
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
import { formatCurrency, toDecimal } from "@/lib/money"
import { itemsApi } from "@/api/items/items.api"
import { useItemsStore } from "@/stores/items"
import { useReferencesStore } from "@/stores/references"
import CreateStockUnitDialog from "./CreateStockUnitDialog.vue"
import EditStockUnitsDialog from "./EditStockUnitsDialog.vue"
import ItemStockUnitCard from "./itemStockUnitCard.vue"
import type { IItemStockUnit, TItemStatus } from "@/api/items/items.types"

const props = defineProps<{ referenceId: string }>()

const router = useRouter()
const store = useItemsStore()
/** Proveedores: entidad compartida, se reusa el store de Referencias en vez de duplicar el fetch. */
const referencesStore = useReferencesStore()

const isCreateDialogOpen = ref(false)
const isEditDialogOpen = ref(false)
/** IDs que va a tocar `EditStockUnitsDialog` — una sola desde el popover de una card, o toda `selectedIds` desde la botonera. */
const editIds = ref<string[]>([])

const isDeleteConfirmOpen = ref(false)
const deleteConfirmIds = ref<string[]>([])

/** Existencias marcadas con el checkbox. Un `Set` reactivo: Vue trackea `.add`/`.delete`/`.has` sin recrearlo. */
const selectedIds = ref(new Set<string>())

/** `SelectItem` de reka-ui no acepta value vacío, así que "todos" necesita un centinela. */
const ALL = "__all__"

const filters = reactive({
  itemId: "",
  location: ALL,
  provider: ALL,
})

async function load() {
  try {
    await store.fetchDetail(props.referenceId)
    // Una recarga trae existencias nuevas o reordenadas: mantener marcada una
    // selección contra datos que ya no están ahí genera checkboxes fantasma.
    selectedIds.value.clear()
  } catch {
    toast.error("No se pudo cargar el producto", { position: "bottom-center" })
  }
}

/**
 * `immediate` cubre el montaje; el watch cubre navegar de un producto a otro
 * sin desmontar la vista (misma ruta, distinto parámetro), caso en el que
 * `onMounted` no se volvería a disparar y quedaría el producto anterior.
 */
watch(() => props.referenceId, () => {
  filters.itemId = ""
  filters.location = ALL
  filters.provider = ALL
  selectedIds.value.clear()
  load()
}, { immediate: true })

const summary = computed(() => store.detail?.summary ?? null)
const totals = computed(() => store.detail?.totals ?? null)
const stockUnits = computed<IItemStockUnit[]>(() => store.detail?.stock_units ?? [])

/**
 * Opciones derivadas de las existencias que devolvió el servidor. Se excluye
 * `null`: proveedor/ubicación son opcionales (migración 0005) y `SelectItem`
 * de reka-ui no acepta value vacío — filtrar "sin asignar" desde acá no tiene
 * sentido como opción de un desplegable de valores existentes.
 */
const locationOptions = computed(() =>
  [...new Set(
    stockUnits.value.map(stockUnit => stockUnit.location_name).filter((name): name is string => name !== null),
  )].sort(),
)
const providerOptions = computed(() =>
  [...new Set(
    stockUnits.value.map(stockUnit => stockUnit.provider_name).filter((name): name is string => name !== null),
  )].sort(),
)

/**
 * Filtrado en cliente: el servidor ya mandó todas las existencias de este
 * producto, así que filtrar acá responde sin ida y vuelta. Si algún día una
 * Referencia tuviera decenas de miles de unidades, el reemplazo es
 * `useVirtualList` (vueuse) o mover los filtros al backend.
 */
const visibleStockUnits = computed(() =>
  stockUnits.value.filter((stockUnit) => {
    const matchesId = filters.itemId === ""
      || stockUnit.item_id.toLowerCase().includes(filters.itemId.trim().toLowerCase())
    const matchesLocation = filters.location === ALL || stockUnit.location_name === filters.location
    const matchesProvider = filters.provider === ALL || stockUnit.provider_name === filters.provider
    return matchesId && matchesLocation && matchesProvider
  }),
)

const hasFilters = computed(() =>
  filters.itemId !== "" || filters.location !== ALL || filters.provider !== ALL,
)

function clearFilters() {
  filters.itemId = ""
  filters.location = ALL
  filters.provider = ALL
}

/** Los totales llegan como string para no perder precisión; pasan por `Decimal` sin tocar float. */
function formatTotal(value: string) {
  return formatCurrency(toDecimal(value))
}

function goBack() {
  router.push({ name: "items" })
}

function addStockUnit() {
  isCreateDialogOpen.value = true
}

function editStockUnit(stockUnit: IItemStockUnit) {
  editIds.value = [stockUnit.item_id]
  isEditDialogOpen.value = true
}

function bulkEdit() {
  editIds.value = [...selectedIds.value]
  isEditDialogOpen.value = true
}

/**
 * Un solo endpoint (`PATCH .../status`) cubre las dos direcciones: activar es
 * dar de baja con el estado destino invertido, no una acción aparte.
 */
async function setStatus(ids: string[], targetStatus: TItemStatus) {
  const results = await Promise.allSettled(
    ids.map(id => itemsApi.updateItem(id, { status: targetStatus })),
  )
  const succeeded = results.filter(result => result.status === "fulfilled").length
  const failed = results.length - succeeded
  const verb = targetStatus === "written_off"
    ? (succeeded === 1 ? "dada de baja" : "dadas de baja")
    : (succeeded === 1 ? "activada" : "activadas")

  if (succeeded > 0) {
    toast.success(
      succeeded === 1 ? `Existencia ${verb}` : `${succeeded} existencias ${verb}`,
      { position: "bottom-center" },
    )
    await load()
  }
  if (failed > 0) {
    toast.error(
      succeeded > 0 ? `${failed} de ${results.length} no se pudieron actualizar` : "No se pudo actualizar",
      { position: "bottom-center" },
    )
  }
}

function toggleStockUnitStatus(stockUnit: IItemStockUnit) {
  setStatus([stockUnit.item_id], stockUnit.status === "written_off" ? "available" : "written_off")
}

function bulkSetStatus(targetStatus: TItemStatus) {
  setStatus([...selectedIds.value], targetStatus)
}

/** Eliminar es la única de las cuatro acciones sin vuelta atrás — por eso pasa por confirmación y las otras no. */
function requestDelete(ids: string[]) {
  deleteConfirmIds.value = ids
  isDeleteConfirmOpen.value = true
}

function removeStockUnit(stockUnit: IItemStockUnit) {
  requestDelete([stockUnit.item_id])
}

function bulkDelete() {
  requestDelete([...selectedIds.value])
}

async function confirmDelete() {
  const ids = deleteConfirmIds.value
  isDeleteConfirmOpen.value = false

  const results = await Promise.allSettled(ids.map(id => itemsApi.deleteItem(id)))
  const succeeded = results.filter(result => result.status === "fulfilled").length
  const failed = results.length - succeeded

  if (succeeded > 0) {
    toast.success(
      succeeded === 1 ? "Existencia eliminada" : `${succeeded} existencias eliminadas`,
      { position: "bottom-center" },
    )
    await load()
  }
  if (failed > 0) {
    // 409 del backend: la unidad ya está facturada (BillItem la referencia, D-41/A-22) — no se puede borrar, hay que darla de baja.
    toast.error(
      succeeded > 0
        ? `${failed} de ${results.length} no se pudieron eliminar (¿ya facturadas?)`
        : "No se pudo eliminar: ¿ya está facturada?",
      { position: "bottom-center" },
    )
  }
}

function toggleSelected(itemId: string, value: boolean) {
  if (value) {
    selectedIds.value.add(itemId)
  } else {
    selectedIds.value.delete(itemId)
  }
}

/** "Todas" opera sobre lo que el filtro deja ver, no sobre el total del producto — seleccionar algo que no se ve confundiría más de lo que ayuda. */
const isAllVisibleSelected = computed(() =>
  visibleStockUnits.value.length > 0
  && visibleStockUnits.value.every(stockUnit => selectedIds.value.has(stockUnit.item_id)),
)
const isSomeVisibleSelected = computed(() =>
  visibleStockUnits.value.some(stockUnit => selectedIds.value.has(stockUnit.item_id)),
)
const selectAllState = computed<boolean | "indeterminate">(() => {
  if (isAllVisibleSelected.value) return true
  return isSomeVisibleSelected.value ? "indeterminate" : false
})

function toggleSelectAll(value: boolean) {
  for (const stockUnit of visibleStockUnits.value) {
    toggleSelected(stockUnit.item_id, value)
  }
}

onMounted(() => {
  referencesStore.fetchProviders().catch(() => {
    toast.error("No se pudieron cargar los proveedores", { position: "bottom-center" })
  })
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
              <Sun class="size-4 text-muted-foreground" />
              <Switch v-model="isDark" aria-label="Cambiar a tema oscuro" />
              <Moon class="size-4 text-muted-foreground" />
            </div>
          </div>
        </header>

        <Button variant="ghost" size="sm" class="-ml-2 gap-1 self-start" @click="goBack">
          <IconChevronLeft class="size-4" />
          Volver a Productos
        </Button>

        <!-- Falló la carga: no es lo mismo que "producto sin existencias". -->
        <div
          v-if="store.hasDetailError"
          class="flex flex-col items-center gap-2 rounded-lg border border-border py-16"
        >
          <p class="text-destructive">
            No se pudo cargar el producto.
          </p>
          <Button variant="outline" size="sm" @click="load">
            Reintentar
          </Button>
        </div>

        <template v-else>
          <!-- Cabecera de la Referencia -->
          <div
            v-if="store.isLoadingDetail || !summary"
            class="flex items-center gap-4 rounded-xl bg-accent px-5 py-4"
          >
            <Skeleton class="size-14 shrink-0 rounded-lg" />
            <div class="flex-1 space-y-2">
              <Skeleton class="h-6 w-64" />
              <Skeleton class="h-4 w-48" />
            </div>
            <Skeleton class="h-9 w-44" />
          </div>

          <div v-else class="flex flex-wrap items-center gap-4 rounded-xl bg-accent px-5 py-4">
            <img
              v-if="summary.image_url"
              :src="summary.image_url"
              :alt="summary.title"
              class="size-14 shrink-0 rounded-lg border border-border object-cover"
            >
            <div
              v-else
              class="flex size-14 shrink-0 items-center justify-center rounded-lg border border-dashed border-border text-muted-foreground"
            >
              <IconPhoto class="size-6" />
            </div>

            <div class="min-w-0 flex-1">
              <h2 class="truncate text-xl font-bold">
                {{ summary.title }}
              </h2>
              <div class="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                <span>SKU - {{ summary.sku }}</span>
                <Badge v-if="summary.category_name" variant="secondary">
                  {{ summary.category_name }}
                </Badge>
                <span>
                  {{ summary.active_providers_count }}
                  {{ summary.active_providers_count === 1 ? "Proveedor activo" : "Proveedores activos" }}
                </span>
              </div>
            </div>

            <Button class="shrink-0 gap-2 text-white hover:text-white" @click="addStockUnit">
              Agregar Existencia
              <IconPlus class="size-4" />
            </Button>
          </div>

          <!-- Totales, calculados en el servidor -->
          <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <template v-if="store.isLoadingDetail || !totals">
              <div v-for="placeholder in 4" :key="placeholder" class="space-y-2 rounded-xl border border-border px-4 py-3">
                <Skeleton class="h-4 w-28" />
                <Skeleton class="h-8 w-32" />
              </div>
            </template>

            <template v-else>
              <div class="rounded-xl border border-border px-4 py-3">
                <p class="text-sm text-muted-foreground">
                  Total Existencias
                </p>
                <p class="text-2xl font-bold tabular-nums">
                  {{ totals.total_units }}
                  <span class="text-base font-normal text-muted-foreground">Un.</span>
                </p>
              </div>

              <div class="rounded-xl border border-border px-4 py-3">
                <p class="text-sm text-muted-foreground">
                  Total Valor Base
                </p>
                <p class="text-2xl font-bold tabular-nums">
                  {{ formatTotal(totals.total_base) }}
                </p>
              </div>

              <div class="rounded-xl border border-border px-4 py-3">
                <p class="text-sm text-muted-foreground">
                  IVA total
                </p>
                <p class="text-2xl font-bold tabular-nums">
                  {{ formatTotal(totals.total_iva) }}
                </p>
              </div>

              <!--
                El prototipo repite el rótulo "Total Existencias" acá, pero el
                valor es base + IVA. Se deja igual que el prototipo a propósito;
                si era un desliz, el nombre correcto sería "Valor Total".
              -->
              <div class="rounded-xl border-2 border-primary px-4 py-3">
                <p class="text-sm text-muted-foreground">
                  Total Existencias
                </p>
                <p class="text-2xl font-bold tabular-nums text-brand-icon">
                  {{ formatTotal(totals.total_value) }}
                </p>
              </div>
            </template>
          </div>

          <!-- Filtros -->
          <div class="rounded-xl border border-border p-4">
            <p class="mb-3 text-sm font-medium">
              Filtros
            </p>
            <div class="flex flex-col gap-4 md:flex-row md:items-end">
              <div class="grid w-full gap-2 md:max-w-56">
                <Label for="filter-item-id">ID producto</Label>
                <div class="relative">
                  <Input
                    id="filter-item-id"
                    v-model="filters.itemId"
                    placeholder="Buscar por ID…"
                    class="pr-8"
                  />
                  <IconSearch
                    class="pointer-events-none absolute right-2 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
                  />
                </div>
              </div>

              <div class="grid w-full gap-2 md:max-w-52">
                <Label for="filter-location">Ubicación</Label>
                <Select v-model="filters.location">
                  <SelectTrigger id="filter-location" class="w-full">
                    <SelectValue placeholder="Todas" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem :value="ALL">
                      Todas
                    </SelectItem>
                    <SelectItem v-for="location in locationOptions" :key="location" :value="location">
                      {{ location }}
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div class="grid w-full gap-2 md:max-w-56">
                <Label for="filter-provider">Proveedor</Label>
                <Select v-model="filters.provider">
                  <SelectTrigger id="filter-provider" class="w-full">
                    <SelectValue placeholder="Todos" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem :value="ALL">
                      Todos
                    </SelectItem>
                    <SelectItem v-for="provider in providerOptions" :key="provider" :value="provider">
                      {{ provider }}
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <Button v-if="hasFilters" variant="ghost" @click="clearFilters">
                Limpiar
              </Button>
            </div>
          </div>

          <!-- Existencias individuales -->
          <div v-if="store.isLoadingDetail" class="space-y-3">
            <Skeleton v-for="placeholder in 5" :key="placeholder" class="h-20 w-full rounded-lg" />
          </div>

          <div
            v-else-if="stockUnits.length === 0"
            class="rounded-lg border border-dashed border-border py-16 text-center text-muted-foreground"
          >
            Este producto no tiene existencias registradas.
          </div>

          <div
            v-else-if="visibleStockUnits.length === 0"
            class="rounded-lg border border-dashed border-border py-16 text-center text-muted-foreground"
          >
            No hay existencias que coincidan con los filtros.
          </div>

          <template v-else>
            <!--
              Barra de selección: "todas" opera sobre lo filtrado, no sobre el
              producto entero (ver `isAllVisibleSelected`). Las acciones en lote
              solo aparecen con algo seleccionado, para no ocupar espacio de
              lectura vacío el resto del tiempo.
            -->
            <div class="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-muted/30 px-4 py-2">
              <label class="flex items-center gap-2 text-sm">
                <Checkbox
                  :model-value="selectAllState"
                  @update:model-value="(value) => toggleSelectAll(value === true)"
                />
                <span>
                  {{ selectedIds.size > 0 ? `${selectedIds.size} seleccionadas` : "Seleccionar todas" }}
                </span>
              </label>

              <div v-if="selectedIds.size > 0" class="flex flex-wrap items-center gap-2">
                <Button variant="outline" size="sm" class="gap-1.5" @click="bulkEdit">
                  <IconPencil class="size-4" />
                  Editar
                </Button>
                <Button variant="outline" size="sm" class="gap-1.5" @click="bulkSetStatus('written_off')">
                  <IconRotate class="size-4" />
                  Dar de baja
                </Button>
                <Button variant="outline" size="sm" class="gap-1.5" @click="bulkSetStatus('available')">
                  <IconRotate class="size-4" />
                  Activar
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  class="gap-1.5 text-destructive hover:text-destructive"
                  @click="bulkDelete"
                >
                  <IconTrash class="size-4" />
                  Eliminar
                </Button>
              </div>
            </div>

            <div class="space-y-3">
              <ItemStockUnitCard
                v-for="stockUnit in visibleStockUnits"
                :key="stockUnit.item_id"
                :stock-unit="stockUnit"
                :selected="selectedIds.has(stockUnit.item_id)"
                @update:selected="(value) => toggleSelected(stockUnit.item_id, value)"
                @edit="editStockUnit"
                @remove="removeStockUnit"
                @toggle-status="toggleStockUnitStatus"
              />
            </div>
          </template>

          <p
            v-if="!store.isLoadingDetail && stockUnits.length > 0"
            class="text-center text-sm text-muted-foreground"
          >
            {{ visibleStockUnits.length }} de {{ stockUnits.length }}
            {{ stockUnits.length === 1 ? "existencia" : "existencias" }}
          </p>
        </template>
      </div>
    </SidebarInset>

    <CreateStockUnitDialog
      v-if="summary"
      v-model:open="isCreateDialogOpen"
      :reference-id="summary.reference_id"
      :default-price="summary.sale_price"
      :providers="referencesStore.providers"
      @created="load"
    />

    <EditStockUnitsDialog
      v-model:open="isEditDialogOpen"
      :item-ids="editIds"
      :providers="referencesStore.providers"
      :stock-units="stockUnits"
      @updated="load"
    />

    <AlertDialog v-model:open="isDeleteConfirmOpen">
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>
            {{
              deleteConfirmIds.length === 1
                ? "¿Eliminar esta existencia?"
                : `¿Eliminar ${deleteConfirmIds.length} existencias?`
            }}
          </AlertDialogTitle>
          <AlertDialogDescription>
            No se puede deshacer. Si alguna ya está facturada, esa en particular no se va a poder
            eliminar — el camino para sacarla de circulación es "Dar de baja".
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>
            Cancelar
          </AlertDialogCancel>
          <AlertDialogAction class="bg-destructive text-white hover:bg-destructive/90" @click="confirmDelete">
            Eliminar
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  </SidebarProvider>
</template>
