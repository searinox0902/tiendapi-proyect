<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue"
import { watchDebounced } from "@vueuse/core"
import { IconDotsVertical, IconPencil, IconTrash } from "@tabler/icons-vue"
import { toast } from "vue-sonner"

import AppSidebar from "@/components/AppSidebar.vue"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useReferencesStore } from "@/stores/references"
import type { IReference, IReferenceFilters } from "@/api/references/references.types"

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
  // TODO: abrir el formulario de edición.
  console.log("editar", reference.sku)
}

function deleteReference(reference: IReference) {
  // TODO: confirmar y eliminar.
  console.log("eliminar", reference.sku)
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
      <header class="flex h-(--header-height) shrink-0 items-center gap-2 border-b">
        <div class="flex w-full items-center gap-1 px-4 lg:gap-2 lg:px-6">
          <SidebarTrigger class="-ml-1" />
          <Separator orientation="vertical" class="mx-2 data-[orientation=vertical]:h-4" />
          <h1 class="text-base font-medium">
            Referencias
          </h1>
        </div>
      </header>

      <div class="flex flex-1 flex-col gap-4 p-4 lg:p-6">
        <!-- Filtros -->
        <div class="flex flex-col gap-4 md:flex-row md:items-end">
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

        <!-- Tabla -->
        <div class="w-full overflow-x-auto rounded-lg border border-border">
          <Table>
            <TableHeader>
              <TableRow>
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
                <TableCell colspan="6" class="h-24 text-center">
                  <Spinner class="mx-auto" />
                </TableCell>
              </TableRow>

              <TableRow
                v-for="reference in store.isLoading ? [] : store.references"
                :key="reference.id"
              >
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
                <TableCell colspan="6" class="h-24 text-center">
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
                <TableCell colspan="6" class="h-24 text-center text-muted-foreground">
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
                <div class="flex items-center justify-between gap-4 py-3 first:pt-0">
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
</template>
