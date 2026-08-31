<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue"
import { watchDebounced } from "@vueuse/core"
import {
  IconDotsVertical,
  IconDownload,
  IconFileSpreadsheet,
  IconFileUpload,
  IconJson,
  IconMarkdown,
  IconPencil,
  IconPhoto,
  IconPlus,
  IconTrash,
} from "@tabler/icons-vue"
import { Moon, Sun } from "@lucide/vue"
import { toast } from "vue-sonner"
import axios from "axios"

import AppSidebar from "@/components/AppSidebar.vue"
import ModuleNavSelect from "@/components/ModuleNavSelect.vue"
import ImportCatalogDialog from "./ImportCatalogDialog.vue"
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
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
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
import { Spinner } from "@/components/ui/spinner"
import { Switch } from "@/components/ui/switch"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { isDark } from "@/composables/useTheme"
import { useReferencesStore } from "@/stores/references"
import { referencesApi } from "@/api/references/references.api"
import type { IReference, IReferenceFilters, TExportFormat } from "@/api/references/references.types"
import { useRouter } from "vue-router"
import { downloadBlob } from "@/lib/download"

const router = useRouter()


/** `SelectItem` de reka-ui no acepta value vacío, así que la opción "todas" necesita un centinela. */
const ALL_CATEGORIES = "__all__"
const PAGE_SIZE = 8

const store = useReferencesStore()

const filters = reactive({
  sku: "",
  title: "",
  category: ALL_CATEGORIES,
})

const page = ref(1)

/** Los filtros vacíos se omiten: el backend los trata como "sin filtro". */
function currentParams(): IReferenceFilters {
  return {
    sku: filters.sku.trim() || undefined,
    title: filters.title.trim() || undefined,
    category_id: filters.category === ALL_CATEGORIES ? undefined : filters.category,
    skip: (page.value - 1) * PAGE_SIZE,
    limit: PAGE_SIZE,
  }
}

async function load() {
  try {
    await store.fetchReferences(currentParams())
  } catch {
    toast.error("No se pudieron cargar las referencias", { position: "bottom-center" })
  }
}

watchDebounced(filters, () => {
  if (page.value !== 1) {
    page.value = 1
    return
  }
  load()
}, { debounce: 350 })

watch(page, load)

const hasFilters = computed(() =>
  filters.sku !== "" || filters.title !== "" || filters.category !== ALL_CATEGORIES,
)

/* ── Selección de filas, mismo patrón que Facturación ────────────────────── */

/** `Set` reactivo: Vue trackea `.add`/`.delete`/`.has` sin tener que recrearlo. */
const selectedIds = ref(new Set<string>())

function toggleSelected(referenceId: string, value: boolean) {
  if (value) {
    selectedIds.value.add(referenceId)
  } else {
    selectedIds.value.delete(referenceId)
  }
}

/** "Todas" opera sobre la página visible: marcar lo que no se ve confunde más de lo que ayuda. */
const isAllVisibleSelected = computed(() =>
  store.references.length > 0 && store.references.every(r => selectedIds.value.has(r.id)),
)
const selectAllState = computed<boolean | "indeterminate">(() => {
  if (isAllVisibleSelected.value) return true
  return store.references.some(r => selectedIds.value.has(r.id)) ? "indeterminate" : false
})

function toggleSelectAll(value: boolean) {
  for (const reference of store.references) {
    toggleSelected(reference.id, value)
  }
}

//  Una página nueva trae otras referencias: mantener marcadas las de la
//  anterior dejaría una selección invisible actuando por detrás (mismo
//  criterio que Facturación).
watch(page, () => selectedIds.value.clear())

/* ── Exportación del catálogo (D-73) ─────────────────────────────────────── */

/** Los mismos filtros de la tabla, **sin** paginación: el archivo no se pagina. */
function exportFilters(): IReferenceFilters {
  return {
    sku: filters.sku.trim() || undefined,
    title: filters.title.trim() || undefined,
    category_id: filters.category === ALL_CATEGORIES ? undefined : filters.category,
  }
}

const EXPORT_FORMATS = [
  { value: "xlsx", label: "Excel", hint: "Hoja de cálculo (.xlsx)", icon: IconFileSpreadsheet },
  { value: "json", label: "JSON", hint: "El que se puede volver a importar", icon: IconJson },
  { value: "markdown", label: "Markdown", hint: "Tabla para leer o pegar (.md)", icon: IconMarkdown },
] as const

const IMPORT_FORMATS = [
  { value: "json", label: "JSON", hint: "El que exporta el propio sistema", icon: IconJson, accept: "application/json,.json" },
  { value: "xlsx", label: "Excel", hint: "La plantilla .xlsx exportada", icon: IconFileSpreadsheet, accept: ".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" },
] as const

const importOpen = ref(false)
const importMenuOpen = ref(false)
const importDialogRef = ref<InstanceType<typeof ImportCatalogDialog> | null>(null)

function pickImportFile(option: (typeof IMPORT_FORMATS)[number]) {
  importMenuOpen.value = false
  importDialogRef.value?.pickFile(option.accept)
}

/** El catálogo cambió por fuera de la tabla: recarga la página actual y el resumen (D-73). */
function onImported() {
  load()
  store.fetchSummary().catch(() => {
    toast.error("No se pudo actualizar el resumen", { position: "bottom-center" })
  })
}

const exportOpen = ref(false)
const isExporting = ref(false)
/** Arranca en "todo": es lo que la gente espera de un botón que dice Exportar. */
const exportScope = ref<"all" | "filtered">("all")

const totalAll = computed(() => store.summary?.total_references ?? 0)
const exportCount = computed(() =>
  exportScope.value === "filtered" ? store.total : totalAll.value,
)

async function downloadExport(format: TExportFormat) {
  if (isExporting.value) {
    return
  }
  isExporting.value = true
  try {
    const { data, headers } = await referencesApi.exportReferences(
      format,
      exportScope.value === "filtered" ? exportFilters() : {},
    )

    //  El nombre lo decide el backend (lleva la fecha). El respaldo local existe
    //  porque si `Content-Disposition` no viaja, el navegador bautiza la
    //  descarga con el nombre del endpoint y baja un archivo sin extensión.
    downloadBlob(data, headers, `referencias.${format === "markdown" ? "md" : format}`)

    exportOpen.value = false
    toast.success(
      //  Un catálogo vacío no es un error: baja igual y el archivo sirve de
      //  plantilla. Decirlo evita que parezca que la descarga falló.
      exportCount.value === 0
        ? "Catálogo vacío: bajó la plantilla con las columnas"
        : `${exportCount.value} referencias exportadas`,
      { position: "bottom-center" },
    )
  } catch (error) {
    console.error("Export references failed:", error)
    toast.error("No se pudo exportar el catálogo", { position: "bottom-center" })
  } finally {
    isExporting.value = false
  }
}

function clearFilters() {
  filters.sku = ""
  filters.title = ""
  filters.category = ALL_CATEGORIES
}

/**
 * Formatea sin convertir a float — regla del proyecto: nunca punto flotante
 * para dinero. `value` llega como string ("12900.00").
 */
function formatPrice(value: string) {
  const [integer, decimals = "00"] = value.split(".")
  const grouped = integer.replace(/\B(?=(\d{3})+(?!\d))/g, ".")
  return `$ ${grouped},${decimals.padEnd(2, "0").slice(0, 2)}`
}

/** El backend manda ISO 8601 con zona; se muestra en hora local del negocio. */
function formatDateTime(value: string | null) {
  if (!value) {
    return "—"
  }
  return new Date(value).toLocaleString("es-CO", {
    dateStyle: "medium",
    timeStyle: "short",
  })
}

function editReference(reference: IReference) {
  router.push({ name: "references-edit", params: { sku: reference.sku } })
}

/**
 * Referencia objetivo del borrado. Deliberadamente separada de `isDeleteDialogOpen`
 * y NUNCA limpiada desde `@update:open`: `AlertDialogAction`/`AlertDialogCancel`
 * heredan de `DialogClose` (reka-ui), que trae su propio `@click="onOpenChange(false)"`
 * en el template — ese handler SIEMPRE corre antes que cualquier `@click` propio
 * pasado desde afuera (llega por fallthrough, después del handler nativo del
 * componente). Si `@update:open` limpiara `pendingDelete`, `confirmDelete` la
 * leería ya en `null`. Por eso solo se limpia explícitamente al terminar
 * `confirmDelete` — quedar "stale" mientras el diálogo está cerrado no importa,
 * `deleteReference` la sobreescribe en la siguiente apertura.
 */
const pendingDelete = ref<IReference | null>(null)
const isDeleteDialogOpen = ref(false)
const isDeleting = ref(false)
/** `true` = el diálogo confirma el borrado de `selectedIds`; `false` = el de `pendingDelete`. */
const isBulkDelete = ref(false)

function deleteReference(reference: IReference) {
  pendingDelete.value = reference
  isBulkDelete.value = false
  isDeleteDialogOpen.value = true
}

function deleteSelected() {
  if (selectedIds.value.size === 0) {
    return
  }
  pendingDelete.value = null
  isBulkDelete.value = true
  isDeleteDialogOpen.value = true
}

function cancelDelete() {
  isDeleteDialogOpen.value = false
}

async function confirmDelete() {
  const ids = isBulkDelete.value
    ? [...selectedIds.value]
    : pendingDelete.value ? [pendingDelete.value.id] : []
  if (ids.length === 0) {
    return
  }
  isDeleting.value = true

  //  Secuencial y no `Promise.all`: no hay endpoint de borrado en lote, y una
  //  Referencia con Ítems asociados la rechaza el servidor (FK restrictiva).
  //  Hace falta saber CUÁLES fallaron, no solo que "algo" falló, y una ráfaga
  //  de N DELETE en paralelo contra el backend local no compra nada.
  const failed: string[] = []
  let firstDetail: string | undefined
  for (const id of ids) {
    try {
      await referencesApi.deleteReference(id)
    } catch (error) {
      failed.push(id)
      if (firstDetail === undefined) {
        const detail = axios.isAxiosError(error) ? error.response?.data?.detail : undefined
        if (typeof detail === "string") {
          firstDetail = detail
        }
      }
    }
  }

  const removed = ids.length - failed.length
  //  La selección queda SOLO con las que fallaron: el usuario ve exactamente
  //  cuáles quedaron sin borrar en vez de tener que cruzarlas contra un toast.
  selectedIds.value = new Set(failed)

  if (failed.length === 0) {
    toast.success(
      removed === 1 ? "Referencia eliminada correctamente" : `${removed} referencias eliminadas`,
      { position: "bottom-center" },
    )
  } else if (removed === 0) {
    toast.error(firstDetail ?? "No se pudo eliminar la referencia", { position: "bottom-center" })
  } else {
    toast.error(
      `${removed} eliminadas · ${failed.length} no se pudieron eliminar${firstDetail ? `: ${firstDetail}` : ""}`,
      { position: "bottom-center" },
    )
  }

  if (removed > 0) {
    //  Si se vació la página y no es la primera, se retrocede una — `watch(page, load)`
    //  dispara la recarga, por eso no se llama a `load()` en esa rama.
    if (removed === store.references.length && page.value > 1) {
      page.value -= 1
    } else {
      await load()
    }
    store.fetchSummary().catch(() => {
      toast.error("No se pudo actualizar el resumen", { position: "bottom-center" })
    })
  }

  isDeleting.value = false
  isDeleteDialogOpen.value = false
  pendingDelete.value = null
}

function goToCreateReference(): void {
  router.push({ name: "references-new" })
}

onMounted(async () => {
  try {
    await store.fetchCategories()
  } catch {
    toast.error("No se pudieron cargar las categorías", { position: "bottom-center" })
  }
  // El resumen es del catálogo completo, no de la página: no se recarga al
  // filtrar ni al paginar, solo cuando el catálogo cambia.
  store.fetchSummary().catch(() => {
    toast.error("No se pudo cargar el resumen", { position: "bottom-center" })
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
    <SidebarInset>
      <div class="px-6 space-y-6 pb-6">

        <header class="flex h-(--header-height) shrink-0 items-center gap-2 border-b">
          <div class="flex w-full items-center gap-1 px-4 lg:gap-2 lg:px-6">
            <SidebarTrigger class="-ml-1" />
            <Separator orientation="vertical" class="mx-2 data-[orientation=vertical]:h-4" />
            <ModuleNavSelect current="references" />
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
                      Importar catálogo
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
                        Exportar catálogo
                      </p>
                      <p class="text-xs text-muted-foreground">
                        Si el catálogo está vacío igual se descarga, con las
                        columnas listas para usar de plantilla.
                      </p>
                    </div>

                    <!--
                      Alcance visible y no implícito: sin esto es imposible
                      saber si el archivo trae el catálogo entero o solo lo que
                      quedó filtrado en pantalla, y el error se descubre tarde.
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
                        <span class="block text-sm font-medium tabular-nums">{{ totalAll }}</span>
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
                        <span class="block text-sm font-medium tabular-nums">{{ store.total }}</span>
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

              <Sun class="size-4 text-muted-foreground" />
              <Switch v-model="isDark" aria-label="Cambiar a tema oscuro" />
              <Moon class="size-4 text-muted-foreground" />
            </div>
          </div>
        </header>

        <div class="flex flex-1 flex-col gap-4">
          <!-- Filters -->
          <div class="flex items-center gap-4"> 
              <div class="flex flex-col flex-1 gap-4 md:flex-row md:items-end">
                <div class="grid w-full gap-2 md:max-w-56">
                  <Label for="filter-sku">SKU</Label>
                  <Input id="filter-sku" v-model="filters.sku" placeholder="FRE-0001" />
                </div>

                <div class="grid w-full gap-2 md:max-w-72">
                  <Label for="filter-title">Nombre de referencia</Label>
                  <Input id="filter-title" v-model="filters.title" placeholder="Pastillas, bujía…" />
                </div>

                <div class="grid w-full gap-2 md:max-w-56">
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
                        v-for="category in store.categories"
                        :key="category.id"
                        :value="category.id"
                      >
                        {{ category.name }}
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <Button v-if="hasFilters" variant="ghost" class="md:mb-0" @click="clearFilters">
                  Limpiar
                </Button>
              </div>
              
              
                  <Button
                    class=" flex-no-wrap justify-start gap-2 text-white hover:text-white"
                    @click="goToCreateReference()"
                  >
                    <IconPlus class="size-4" />
                    Crear Referencia
                  </Button>
              </div>

            
        </div>

        <!--
          Barra de selección, misma forma que la de Facturación para que las
          dos pantallas se operen igual. Va encima de la tabla y no como
          checkbox en la cabecera para no tener dos "seleccionar todas"
          compitiendo en la misma vista.
        -->
        <div
          v-if="!store.isLoading && store.references.length > 0"
          class="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-muted/30 px-4 py-2"
        >
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
            No hay "Quitar selección": el propio checkbox limpia la selección
            (marcado → clic → se desmarcan todas), así que era un segundo
            control para lo que ya hacía el primero.
          -->
          <Button
            v-if="selectedIds.size > 0"
            variant="destructive"
            size="sm"
            class="gap-1.5"
            @click="deleteSelected()"
          >
            <IconTrash class="size-4" />
            Eliminar {{ selectedIds.size }}
          </Button>
        </div>

        <!-- Tabla -->
        <div class="w-full overflow-x-auto rounded-lg border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead class="w-10" />
                <TableHead class="w-16">
                  Foto
                </TableHead>
                <TableHead>SKU</TableHead>
                <TableHead>Nombre de referencia</TableHead>
                <TableHead>Marca</TableHead>
                <TableHead>Categoría</TableHead>
                <TableHead class="text-right">
                  Precio base
                </TableHead>
                <TableHead class="w-12 text-right">
                  Acciones
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-if="store.isLoading">
                <TableCell colspan="8" class="h-24 text-center">
                  <Spinner class="mx-auto" />
                </TableCell>
              </TableRow>

              <TableRow
                v-for="reference in store.isLoading ? [] : store.references"
                :key="reference.id"
                :data-state="selectedIds.has(reference.id) ? 'selected' : undefined"
              >
                <TableCell>
                  <Checkbox
                    :model-value="selectedIds.has(reference.id)"
                    :aria-label="`Seleccionar ${reference.sku}`"
                    @update:model-value="value => toggleSelected(reference.id, value === true)"
                  />
                </TableCell>
                <TableCell>
                  <img
                    v-if="reference.image_url"
                    :src="reference.image_url"
                    :alt="reference.title"
                    class="size-10 rounded-md border border-border object-cover"
                  >
                  <div
                    v-else
                    class="flex size-10 items-center justify-center rounded-md border border-dashed border-border text-muted-foreground"
                  >
                    <IconPhoto class="size-4" />
                  </div>
                </TableCell>
                <TableCell class="font-medium">
                  {{ reference.sku }}
                </TableCell>
                <TableCell>{{ reference.title }}</TableCell>
                <TableCell :class="reference.brand ? '' : 'text-muted-foreground'">
                  {{ reference.brand ?? "—" }}
                </TableCell>
                <TableCell>{{ store.categoryName(reference.category_id) }}</TableCell>
                <TableCell class="text-right tabular-nums">
                  {{ formatPrice(reference.base_price) }}
                </TableCell>
                <TableCell class="text-right">
                  <Popover>
                    <PopoverTrigger as-child>
                      <Button variant="ghost" size="icon" class="size-8">
                        <IconDotsVertical class="size-4" />
                        <span class="sr-only">Acciones para {{ reference.sku }}</span>
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent align="end" class="w-40 p-1">
                      <Button
                        variant="ghost"
                        class="w-full justify-start gap-2"
                        @click="editReference(reference)"
                      >
                        <IconPencil class="size-4" />
                        Editar
                      </Button>
                      <Button
                        variant="ghost"
                        class="w-full justify-start gap-2 text-destructive hover:text-destructive"
                        @click="deleteReference(reference)"
                      >
                        <IconTrash class="size-4" />
                        Eliminar
                      </Button>
                    </PopoverContent>
                  </Popover>
                </TableCell>
              </TableRow>

              <!-- Falló la carga: no es lo mismo que "no hay resultados". -->
              <TableRow v-if="!store.isLoading && store.hasError">
                <TableCell colspan="8" class="h-24 text-center">
                  <p class="text-destructive">
                    No se pudieron cargar las referencias.
                  </p>
                  <Button variant="outline" size="sm" class="mt-2" @click="load">
                    Reintentar
                  </Button>
                </TableCell>
              </TableRow>

              <TableRow
                v-else-if="!store.isLoading && store.references.length === 0"
              >
                <TableCell colspan="8" class="h-24 text-center text-muted-foreground">
                  {{
                    hasFilters
                      ? "No hay referencias que coincidan con los filtros."
                      : "Aún no hay referencias registradas."
                  }}
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>

        <!-- Paginación -->
        <div class="flex flex-col items-center gap-3 sm:flex-row sm:justify-between">
          <p class="text-sm text-muted-foreground">
            {{ store.total }}
            {{ store.total === 1 ? "referencia" : "referencias" }}
          </p>

          <Pagination
            v-slot="{ page: currentPage }"
            v-model:page="page"
            :total="store.total"
            :items-per-page="PAGE_SIZE"
            :sibling-count="1"
            show-edges
            class="mx-0 w-auto"
          >
            <PaginationContent v-slot="{ items }">
              <PaginationPrevious />
              <template v-for="(item, index) in items">
                <PaginationItem
                  v-if="item.type === 'page'"
                  :key="index"
                  :value="item.value"
                  :is-active="item.value === currentPage"
                >
                  {{ item.value }}
                </PaginationItem>
              </template>
              <PaginationNext />
            </PaginationContent>
          </Pagination>
        </div>

        <!-- Resumen del catálogo completo (no de la página actual) -->
        <div class="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader class="border-b">
              <CardTitle>Últimas referencias creadas</CardTitle>
            </CardHeader>
            <CardContent>
              <ul v-if="store.summary?.latest.length" class="divide-y divide-border">
                <li
                  v-for="reference in store.summary.latest"
                  :key="reference.id"
                  class="flex items-center justify-between gap-4 py-3 first:pt-0 last:pb-0"
                >
                  <div class="min-w-0">
                    <p class="truncate text-sm font-medium">
                      {{ reference.title }}
                    </p>
                    <p class="text-xs text-muted-foreground">
                      {{ reference.sku }}
                    </p>
                  </div>
                  <span class="shrink-0 text-sm tabular-nums">
                    {{ formatPrice(reference.base_price) }}
                  </span>
                </li>
              </ul>
              <p v-else class="py-3 text-sm text-muted-foreground">
                Aún no hay referencias registradas.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader class="border-b">
              <CardTitle>Resumen</CardTitle>
            </CardHeader>
            <CardContent>
              <dl class="divide-y divide-border">
                <div class="flex items-center justify-between gap-2 py-1 first:pt-0">
                  <dt class="text-sm text-muted-foreground">
                    Total referencias
                  </dt>
                  <dd class="text-sm font-medium tabular-nums">
                    {{ store.summary?.total_references ?? "—" }}
                  </dd>
                </div>
                <div class="flex items-center justify-between gap-4 py-3">
                  <dt class="text-sm text-muted-foreground">
                    Total marcas
                  </dt>
                  <dd class="text-sm font-medium tabular-nums">
                    {{ store.summary?.total_brands ?? "—" }}
                  </dd>
                </div>
                <div class="flex items-center justify-between gap-4 py-3 last:pb-0">
                  <dt class="text-sm text-muted-foreground">
                    Última actualización
                  </dt>
                  <dd class="text-sm font-medium">
                    {{ formatDateTime(store.summary?.last_updated_at ?? null) }}
                  </dd>
                </div>
              </dl>
            </CardContent>
          </Card>
        </div>
      </div>
    </SidebarInset>
  </SidebarProvider>

  <AlertDialog :open="isDeleteDialogOpen" @update:open="(open) => { if (!open) cancelDelete() }">
    <AlertDialogContent>
      <AlertDialogHeader>
        <AlertDialogTitle>
          {{ isBulkDelete ? `¿Eliminar ${selectedIds.size} referencias?` : "¿Eliminar esta referencia?" }}
        </AlertDialogTitle>
        <AlertDialogDescription>
          <template v-if="isBulkDelete">
            Se eliminarán permanentemente {{ selectedIds.size }} referencias. Esta acción no se
            puede deshacer. Las que tengan existencias asociadas no se pueden eliminar y quedarán
            seleccionadas.
          </template>
          <template v-else>
            Se eliminará permanentemente "{{ pendingDelete?.title }}" ({{ pendingDelete?.sku }}). Esta acción no se puede deshacer.
          </template>
        </AlertDialogDescription>
      </AlertDialogHeader>
      <AlertDialogFooter>
        <AlertDialogCancel :disabled="isDeleting">
          Cancelar
        </AlertDialogCancel>
        <AlertDialogAction
          :disabled="isDeleting"
          class="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          @click="confirmDelete"
        >
          {{ isDeleting ? "Eliminando..." : (isBulkDelete ? `Eliminar ${selectedIds.size}` : "Eliminar") }}
        </AlertDialogAction>
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>

  <ImportCatalogDialog ref="importDialogRef" v-model:open="importOpen" @imported="onImported" />
</template>
