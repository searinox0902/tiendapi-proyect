<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue"
import { watchDebounced } from "@vueuse/core"
import { IconPercentage, IconPlus, IconSearch } from "@tabler/icons-vue"
import { toast } from "vue-sonner"

import AppSidebar from "@/components/AppSidebar.vue"
import NumericMaskInput from "@/components/NumericMaskInput.vue"
import { Button } from "@/components/ui/button"
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
import { formatCurrency, formatPercentage, toDecimal } from "@/lib/money"
import { referencesApi } from "@/api/references/references.api"
import { useReferencesStore } from "@/stores/references"
import CardItemPos from "./cardItemPos.vue"
import type { IReference } from "@/api/references/references.types"

/** `SelectItem` de reka-ui no acepta value vacío, así que "todas" necesita un centinela. */
const ALL_CATEGORIES = "__all__"
/** Cuántas Referencias trae la grilla. Sin scroll infinito todavía: la caja se opera buscando, no scrolleando. */
const PAGE_SIZE = 60

/** Las categorías son entidad compartida — se reusa el store de Referencias en vez de duplicar el fetch. */
const referencesStore = useReferencesStore()

/**
 * Un solo campo de búsqueda para SKU y nombre (`search`, OR en el backend): el
 * cajero no sabe si lo que tiene en la mano es un código o un nombre, y con un
 * escáner de barras siempre es un código (docs/05, §1.2).
 */
const filters = reactive({
  search: "",
  category: ALL_CATEGORIES,
})

/**
 * Estado local, no un store: la lista de esta pantalla es su propia consulta y
 * mandarla al store de Referencias pisaría el listado del CRUD. El store propio
 * llega cuando exista el carrito (columna 2), que sí es estado con vida larga.
 */
const references = ref<IReference[]>([])
const total = ref(0)
const isLoading = ref(false)
const hasError = ref(false)

async function load() {
  isLoading.value = true
  hasError.value = false
  try {
    const { data } = await referencesApi.getReferences({
      search: filters.search.trim() || undefined,
      category_id: filters.category === ALL_CATEGORIES ? undefined : filters.category,
      limit: PAGE_SIZE,
    })
    references.value = data.items
    total.value = data.total
  } catch {
    hasError.value = true
    references.value = []
    total.value = 0
    toast.error("No se pudieron cargar los productos", { position: "bottom-center" })
  } finally {
    isLoading.value = false
  }
}

/** Con debounce: tecleando "FRE-0001" se dispararía una consulta por carácter. */
watchDebounced(filters, load, { debounce: 350 })

/** La Referencia sobre la que se está armando la línea de venta. `null` = nada elegido todavía. */
const selected = ref<IReference | null>(null)
const quantity = ref(1)
const discount = ref("")

function selectProduct(reference: IReference) {
  selected.value = reference
  quantity.value = 1
  discount.value = ""
}

const hasFilters = computed(() => filters.search !== "" || filters.category !== ALL_CATEGORIES)

/** La grilla trae hasta `PAGE_SIZE`: si hay más, se dice — una lista recortada en silencio se lee como completa. */
const hiddenCount = computed(() => Math.max(0, total.value - references.value.length))

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
    <!--
      La caja no scrollea como página: se ancla al alto de la ventana y solo la
      grilla de productos se desplaza por dentro. `md:h-[calc(100svh-1rem)]`
      descuenta el `m-2` que `SidebarInset` se pone en `variant=inset`.
    -->
    <SidebarInset class="h-svh min-w-0 overflow-hidden md:h-[calc(100svh-1rem)]">
      <header class="flex h-(--header-height) shrink-0 items-center gap-2 border-b">
        <div class="flex w-full items-center gap-1 px-4 lg:gap-2 lg:px-6">
          <SidebarTrigger class="-ml-1" />
          <Separator orientation="vertical" class="mx-2 data-[orientation=vertical]:h-4" />
          <h1 class="text-base font-medium">
            Caja registradora
          </h1>
        </div>
      </header>

      <div class="flex min-h-0 flex-1 gap-4 p-6">
        <!-- Columna 1: buscar → elegir → armar la línea de venta. -->
        <section class="flex min-w-0 flex-1 flex-col gap-4">
          <!-- Fila 1 — filtros. Alto fijo: la grilla es la que cede espacio. -->
          <div class="flex shrink-0 flex-col gap-4 md:flex-row md:items-end">
            <div class="grid w-full gap-2">
              <div class="relative">
                <Input
                  id="pos-search"
                  v-model="filters.search"
                  placeholder="Código SKU / Nombre producto"
                  class="pr-8"
                  autofocus
                />
                <IconSearch
                  class="pointer-events-none absolute right-2 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
                />
              </div>
            </div>

            <div class="grid w-full gap-2 md:max-w-56">
              <Select v-model="filters.category">
                <SelectTrigger id="pos-category" class="w-full">
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
          </div>

          <!--
            Fila 2 — la grilla se queda con todo el alto sobrante (`flex-1`) y
            scrollea por dentro (`min-h-0` + `overflow-y-auto`); sin `min-h-0` un
            hijo de flex no baja de su alto de contenido y empujaría la fila 3
            fuera de la pantalla.
          -->
          <!--
            `scrollbar-gutter:stable` reserva el canal de la barra siempre: con
            12 skeletons no hay scroll y con 29 cards sí, y sin esto las cards
            se encogían 4px justo al llegar los datos.
          -->
          <div class="min-h-0 flex-1 overflow-y-auto [scrollbar-gutter:stable] rounded-xl border border-border p-4">
            <div v-if="isLoading" class="grid gap-4 grid-cols-2 md:grid-cols-4">
              <CardItemPos v-for="placeholder in 12" :key="placeholder" loading />
            </div>

            <!-- Falló la carga: no es lo mismo que "no hay resultados". -->
            <div
              v-else-if="hasError"
              class="flex flex-col items-center gap-2 py-16"
            >
              <p class="text-destructive">
                No se pudieron cargar los productos.
              </p>
              <Button variant="outline" size="sm" @click="load">
                Reintentar
              </Button>
            </div>

            <div
              v-else-if="references.length === 0"
              class="py-16 text-center text-muted-foreground"
            >
              {{
                hasFilters
                  ? "No hay productos que coincidan con la búsqueda."
                  : "Aún no hay productos registrados."
              }}
            </div>

            <template v-else>
              <div class="grid gap-4 grid-cols-2 md:grid-cols-4">
                <CardItemPos
                  v-for="reference in references"
                  :key="reference.id"
                  :reference="reference"
                  :selected="selected?.id === reference.id"
                  @select="selectProduct"
                />
              </div>

              <p v-if="hiddenCount > 0" class="pt-4 text-center text-xs text-muted-foreground">
                Se muestran {{ references.length }} de {{ total }} — afina la búsqueda para ver el resto.
              </p>
            </template>
          </div>

          <!--
            Fila 3 — la línea de venta que se está armando. SKU, nombre, IVA y
            precio base se PINTAN desde la Referencia elegida (autocompletado,
            docs/05 §2 Pantalla 3): son datos de catálogo, no se teclean acá.
            Cantidad y descuento sí son del cobro, y son los únicos editables.
          -->
          <div class="shrink-0 rounded-xl border border-border p-4">
            <div class="flex flex-col gap-4 lg:flex-row lg:items-end">
              <div class="grid w-full gap-2 lg:max-w-36">
                <Label for="pos-sku">SKU</Label>
                <Input id="pos-sku" :model-value="selected?.sku ?? ''" readonly class="bg-muted/40" />
              </div>

              <div class="grid w-full min-w-0 gap-2">
                <Label for="pos-title">Nombre producto</Label>
                <Input id="pos-title" :model-value="selected?.title ?? ''" readonly class="bg-muted/40" />
              </div>

              <div class="grid w-full gap-2 lg:max-w-24">
                <Label for="pos-iva">IVA</Label>
                <Input
                  id="pos-iva"
                  :model-value="selected ? `${formatPercentage(selected.iva_percentage)} %` : ''"
                  readonly
                  class="bg-muted/40 tabular-nums"
                />
              </div>

              <div class="grid w-full gap-2 lg:max-w-40">
                <Label for="pos-base-price">Precio Base</Label>
                <Input
                  id="pos-base-price"
                  :model-value="selected ? formatCurrency(toDecimal(selected.base_price)) : ''"
                  readonly
                  class="bg-muted/40 tabular-nums"
                />
              </div>

              <div class="grid w-full gap-2 lg:max-w-28">
                <Label for="pos-quantity">Cantidad</Label>
                <Input
                  id="pos-quantity"
                  v-model.number="quantity"
                  type="number"
                  min="1"
                  step="1"
                  :disabled="!selected"
                  class="tabular-nums"
                />
              </div>

              <div class="grid w-full gap-2 lg:max-w-32">
                <Label for="pos-discount">Descuento</Label>
                <div class="relative">
                  <IconPercentage class="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                  <NumericMaskInput
                    id="pos-discount"
                    v-model="discount"
                    :max="100"
                    class="pl-8"
                    placeholder="0"
                  />
                </div>
              </div>

              <!--
                Alimenta el carrito, que vive en la columna 2 — todavía sin
                construir, así que por ahora solo se habilita al elegir un
                producto y no dispara ninguna acción.
              -->
              <Button
                class="shrink-0 gap-2 text-white hover:text-white"
                :disabled="!selected"
              >
                Agregar
                <IconPlus class="size-4" />
              </Button>
            </div>
          </div>
        </section>

        <!-- Columna 2 — carrito/cobro. Ancho fijo de 265px; se construye después. -->
        <aside class="hidden w-[265px] shrink-0 rounded-xl border border-border bg-card lg:block" />
      </div>
    </SidebarInset>
  </SidebarProvider>
</template>
