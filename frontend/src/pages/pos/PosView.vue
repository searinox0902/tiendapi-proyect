<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from "vue";
import { useInfiniteScroll, watchDebounced } from "@vueuse/core";
import {
  IconCurrencyDollar,
  IconPhoto,
  IconPlus,
  IconSearch,
} from "@tabler/icons-vue";
import { Moon, Sun } from "@lucide/vue";
import { toast } from "vue-sonner";

import AppSidebar from "@/components/AppSidebar.vue";
import ModuleNavSelect from "@/components/ModuleNavSelect.vue";
import NumericMaskInput from "@/components/NumericMaskInput.vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { Switch } from "@/components/ui/switch";
//  `formatCurrency` salió del import: el formateo de plata de esta pantalla
//  pasó a `useAnimatedCurrency`, que lo aplica internamente.
import {
  basePriceFromGross,
  computeSalePrice,
  formatPercentage,
  toDecimal,
} from "@/lib/money";
import { useAnimatedCurrency } from "@/composables/useAnimatedCurrency";
import { isDark } from "@/composables/useTheme";
import { billsApi } from "@/api/bills/bills.api";
import { itemsApi } from "@/api/items/items.api";
import { useReferencesStore } from "@/stores/references";
import CreateStockUnitDialog from "@/pages/Items/CreateStockUnitDialog.vue";
import PosItemCard from "./PosItemCard.vue";
import PosItemCollection from "./PosItemCollection.vue";
import type { IPosCartLine } from "./pos.types";
import type { IItemStock } from "@/api/items/items.types";

/** `SelectItem` de reka-ui no acepta value vacío, así que "todas" necesita un centinela. */
const ALL_CATEGORIES = "__all__";
/** Cuántas Referencias trae la grilla. Sin scroll infinito todavía: la caja se opera buscando, no scrolleando. */
/**
 * Tanda del scroll infinito. 24 = 6 filas de 4 columnas, o sea algo más de lo
 * que entra en pantalla: se ve que hay más abajo sin traer el catálogo entero.
 * Antes eran 60 de una sola vez con un cartel de "afiná la búsqueda", que
 * obligaba al cajero a adivinar un término en vez de simplemente scrollear.
 */
const BATCH_SIZE = 24;

/** Las categorías son entidad compartida — se reusa el store de Referencias en vez de duplicar el fetch. */
const referencesStore = useReferencesStore();

/**
 * Un solo campo de búsqueda para SKU y nombre (`search`, OR en el backend): el
 * cajero no sabe si lo que tiene en la mano es un código o un nombre, y con un
 * escáner de barras siempre es un código (docs/05, §1.2).
 */
const filters = reactive({
  search: "",
  category: ALL_CATEGORIES,
});

/**
 * Estado local, no un store: la lista de esta pantalla es su propia consulta y
 * mandarla al store de Productos pisaría la grilla del CRUD.
 */
const references = ref<IItemStock[]>([]);
const total = ref(0);
const isLoading = ref(false);
const isLoadingMore = ref(false);
const hasError = ref(false);
/** Contenedor con `overflow-y-auto`: el scroll es interno, no el de la ventana. */
const gridRef = ref<HTMLElement | null>(null);
/** Se prende si la última tanda falló, para no reintentar en bucle con el scroll en el fondo. */
const loadMoreFailed = ref(false);

/** Quedan productos por traer más allá de lo ya cargado. */
const hasMore = computed(() => references.value.length < total.value);

/**
 * La grilla sale de `/items/stock`, no de `/references/`: es la única fuente
 * que sabe **cuántas unidades vendibles** hay de cada producto, y toda esta
 * pantalla depende de ese número (el tope de cantidad, la card de agotado, el
 * carrito). Trae además base e IVA de catálogo, así que la fila 3 arma la
 * línea de venta sin una segunda petición por producto tocado.
 *
 * `available_first`: lo vendible arriba y lo agotado al final — pero visible,
 * porque desde la card agotada se le cargan existencias en el momento.
 */
/** `skip` es lo ya cargado, no un número de página. */
function currentParams(skip: number) {
  return {
    search: filters.search.trim() || undefined,
    category_id:
      filters.category === ALL_CATEGORIES ? undefined : filters.category,
    sort: "available_first" as const,
    skip,
    limit: BATCH_SIZE,
  };
}

async function load() {
  isLoading.value = true;
  hasError.value = false;
  loadMoreFailed.value = false;
  try {
    const { data } = await itemsApi.getStock(currentParams(0));
    references.value = data.items;
    total.value = data.total;
    //  Al cambiar el filtro el conjunto es otro: quedarse a mitad del scroll
    //  anterior mostraría la tanda nueva empezada por el medio.
    gridRef.value?.scrollTo({ top: 0 });
    syncCartWithStock();
  } catch {
    hasError.value = true;
    references.value = [];
    total.value = 0;
    toast.error("No se pudieron cargar los productos", {
      position: "bottom-center",
    });
  } finally {
    isLoading.value = false;
  }
}

/** Siguiente tanda al acercarse al final del scroll interno. */
async function loadMore() {
  isLoadingMore.value = true;
  try {
    const { data } = await itemsApi.getStock(currentParams(references.value.length));
    references.value = [...references.value, ...data.items];
    total.value = data.total;
    //  Se re-sincroniza: la tanda nueva puede traer el stock de un producto que
    //  ya está en el carrito y que hasta ahora no se conocía.
    syncCartWithStock();
    loadMoreFailed.value = false;
  } catch {
    loadMoreFailed.value = true;
    toast.error("No se pudieron cargar más productos", {
      position: "bottom-center",
    });
  } finally {
    isLoadingMore.value = false;
  }
}

/**
 * Scroll infinito sobre **el contenedor de la grilla**, no sobre la ventana: en
 * esta pantalla la página no scrollea (la fila 2 tiene su propio
 * `overflow-y-auto` y la línea de venta queda fija abajo), así que observar
 * `window` nunca dispararía.
 *
 * `distance: 300` arranca la tanda antes de tocar fondo. `canLoadMore` corta
 * por `loadMoreFailed` —si no, reintentaría cada ~100ms mientras el scroll siga
 * abajo— y por las dos banderas de carga, que vueuse no conoce.
 */
useInfiniteScroll(gridRef, loadMore, {
  distance: 300,
  canLoadMore: () =>
    hasMore.value && !loadMoreFailed.value && !isLoading.value && !isLoadingMore.value,
});

/**
 * Reconcilia el carrito con las existencias que acaba de traer la grilla.
 *
 * Hace falta porque el carrito guarda una **foto** del stock al agregar, y
 * entre medias pueden haber cambiado las cosas: otra caja vendió, o el propio
 * cajero le cargó existencias a un agotado. Si una línea quedó por encima de
 * lo que hay, se recorta acá y se avisa — mejor enterarse ahora que con un 409
 * cuando ya cobró.
 */
function syncCartWithStock() {
  const stockByReference = new Map(
    references.value.map(item => [item.reference_id, item.units]),
  );
  const trimmed: string[] = [];
  for (const line of cart.value) {
    const units = stockByReference.get(line.referenceId);
    //  Un producto que no vino en esta página no se toca: no saber su stock no
    //  es lo mismo que saber que es cero.
    if (units === undefined) {
      continue;
    }
    line.availableUnits = units;
    if (line.quantity > units) {
      line.quantity = Math.max(1, units);
      trimmed.push(line.sku);
    }
  }
  if (trimmed.length > 0) {
    toast.warning(`Cantidad ajustada por existencias: ${trimmed.join(", ")}`, {
      position: "bottom-center",
    });
  }
}

/** Con debounce: tecleando "FRE-0001" se dispararía una consulta por carácter. */
watchDebounced(filters, load, { debounce: 350 });

/** El producto sobre el que se está armando la línea de venta. `null` = nada elegido todavía. */
const selected = ref<IItemStock | null>(null);
const quantity = ref(1);
const discount = ref("");

function selectProduct(reference: IItemStock) {
  selected.value = reference;
  quantity.value = 1;
  discount.value = "";
}

/**
 * Tope de cantidad: las unidades vendibles del producto, menos lo que ya está
 * en el carrito de ese mismo producto. Sin restar lo del carrito se podría
 * armar 3 + 3 sobre un stock de 4 y el cobro reventaría al final.
 */
const maxQuantity = computed(() => {
  const reference = selected.value;
  if (reference === null) {
    return 1;
  }
  const inCart = cart.value.find(line => line.referenceId === reference.reference_id);
  return Math.max(1, reference.units - (inCart?.quantity ?? 0));
});

/** Vuelve la fila 3 a su estado en blanco — mismo reseteo que abrir una selección nueva, pero sin ninguna. */
function clearSelection() {
  selected.value = null;
  quantity.value = 1;
  discount.value = "";
}

/**
 * Clic fuera de todo lo relevante: deselecciona. "Todo lo relevante" son tres
 * zonas, no una — cada una por una razón distinta:
 *   - una card: elegir OTRO producto ya es la acción, no hay nada que limpiar
 *   - `.posItemCollection` (el carrito): tocar +/-, X o "Facturar" no debería
 *     borrar lo que se está armando en la fila 3
 *   - `.selectedItemInputs` (la fila 3 misma): es la selección — si no se
 *     excluye, un clic para teclear Cantidad o Descuento se autodestruye
 *     apenas se hace, porque el input no es ni una card ni el carrito.
 * Los `[role]` de Reka-UI (diálogo de pago, listbox de Categoría) se excluyen
 * aparte porque se renderizan por `Teleport` fuera del árbol de la página —
 * sin esto, escribir dentro del modal de cobro limpiaría la selección de
 * fondo en cada clic.
 */
function handleOutsideClick(event: MouseEvent) {
  if (selected.value === null) {
    return;
  }
  const target = event.target as HTMLElement;
  if (target.closest('[role="dialog"], [role="listbox"], [role="menu"]')) {
    return;
  }
  if (target.closest('[data-slot="card"]')) {
    return;
  }
  if (target.closest(".posItemCollection") || target.closest(".selectedItemInputs")) {
    return;
  }
  clearSelection();
}

/**
 * Nunca 0 ni fracciones: se venden unidades enteras (D-41) y con 0 las
 * divisiones revientan. Y nunca por encima de lo que hay: `maxQuantity` ya
 * descuenta lo que está en el carrito.
 */
const units = computed(() =>
  Math.min(maxQuantity.value, Math.max(1, Math.trunc(quantity.value || 1))),
);

/**
 * El descuento es un **monto de la línea completa** y se descuenta de la
 * **base**, no del total: en Colombia un descuento comercial otorgado en la
 * factura reduce la base gravable, y el IVA se liquida sobre esa base ya
 * rebajada. Restarlo después del IVA cobraría impuesto sobre plata que el
 * cliente nunca pagó. Por eso el IVA se "autoajusta": es consecuencia de la
 * base nueva, no una segunda decisión.
 */
const unitGrossPrice = computed(() => {
  const reference = selected.value;
  if (reference === null) {
    return toDecimal(0);
  }
  const perUnitDiscount = toDecimal(discount.value).dividedBy(units.value);
  const baseAfterDiscount = toDecimal(reference.base_price).minus(
    perUnitDiscount,
  );
  //  El tope del input evita llegar acá en negativo; el clamp es el cinturón.
  return computeSalePrice(
    baseAfterDiscount.isNegative() ? 0 : baseAfterDiscount,
    reference.iva_percentage,
  );
});

/**
 * Base e IVA de la línea entera (por eso cambian también al mover la cantidad).
 * Se derivan del precio unitario YA redondeado a $50, que es exactamente lo que
 * se guarda en el carrito: así la vista previa y el detalle nunca discrepan.
 */
const lineTotal = computed(() => unitGrossPrice.value.times(units.value));
const lineBase = computed(() =>
  selected.value === null
    ? toDecimal(0)
    : basePriceFromGross(
        unitGrossPrice.value,
        selected.value.iva_percentage,
      ).times(units.value),
);
const lineIva = computed(() => lineTotal.value.minus(lineBase.value));

const basePriceDisplay = useAnimatedCurrency(lineBase);
const ivaAmountDisplay = useAnimatedCurrency(lineIva);
const lineTotalDisplay = useAnimatedCurrency(lineTotal);

/**
 * Tope del descuento: la base de la línea. `NumericMaskInput` bloquea la tecla
 * que se pase, así que no hace falta un mensaje de error que además movería la
 * fila entera al aparecer.
 */
const maxDiscount = computed(() =>
  selected.value === null
    ? undefined
    : toDecimal(selected.value.base_price).times(units.value).toNumber(),
);

/** Detalle de factura en curso. Estado de esta pantalla; se pierde al salir, como una venta abandonada. */
const cart = ref<IPosCartLine[]>([]);

/**
 * Agrega la línea que se armó en la fila 3. Si la Referencia ya está en el
 * detalle **suma cantidad** en vez de abrir una segunda línea: dos filas del
 * mismo SKU se leen como un error de digitación, no como una decisión.
 */
/**
 * Línea recién agregada. Se resalta un instante en el detalle: cuando el
 * producto ya estaba en la lista no entra una fila nueva que se vea llegar, y
 * sin esta señal el clic en "Agregar" no produce ningún cambio perceptible
 * (peor todavía si la fila quedó fuera del scroll).
 */
const highlightedId = ref<string | null>(null);
let highlightTimer: ReturnType<typeof setTimeout> | undefined;

function highlight(referenceId: string) {
  highlightedId.value = referenceId;
  clearTimeout(highlightTimer);
  highlightTimer = setTimeout(() => {
    highlightedId.value = null;
  }, 900);
}

function addToCart() {
  const reference = selected.value;
  if (reference === null) {
    return;
  }
  //  Agotado: no hay nada que agregar. La card ya ofrece cargar existencias,
  //  pero el botón podría alcanzarse por teclado con el stock recién en cero.
  if (reference.units === 0) {
    toast.error(`${reference.sku} está agotado`, { position: "bottom-center" });
    return;
  }
  const existing = cart.value.find(
    (line) => line.referenceId === reference.reference_id,
  );
  if (existing === undefined) {
    cart.value.push({
      referenceId: reference.reference_id,
      sku: reference.sku,
      title: reference.title,
      imageUrl: reference.image_url ?? undefined,
      unitPrice: unitGrossPrice.value.toFixed(2),
      ivaPercentage: reference.iva_percentage,
      quantity: units.value,
      availableUnits: reference.units,
    });
  } else {
    //  El tope vuelve a aplicarse acá y no solo en el input: `units` ya
    //  descuenta lo que hay en el carrito, pero el clamp deja la invariante
    //  escrita donde se muta la línea.
    existing.quantity = Math.min(
      reference.units,
      existing.quantity + units.value,
    );
    existing.availableUnits = reference.units;
  }
  highlight(reference.reference_id);
  //  Se limpia lo del cobro, no el producto: un descuento que sobrevive al
  //  siguiente "Agregar" se cuela sin que nadie lo vuelva a mirar.
  quantity.value = 1;
  discount.value = "";
}

/**
 * Atajo del doble clic / Enter sobre una card: manda el producto al detalle sin
 * pasar por la fila 3. Selecciona primero a propósito — `selectProduct` deja
 * cantidad en 1 y descuento en blanco, así que el agregado rápido siempre es
 * "una unidad, sin descuento", y de paso la fila 3 queda mostrando lo que
 * acabó de entrar.
 */
function quickAddToCart(reference: IItemStock) {
  selectProduct(reference);
  addToCart();
}

/** Producto agotado sobre el que se van a cargar existencias. `null` = diálogo cerrado. */
const stockTarget = ref<IItemStock | null>(null);
const isStockDialogOpen = ref(false);

/**
 * Card agotada: en vez de seleccionar un producto que no se puede vender, se
 * abre el alta de existencias con ese producto ya cargado. Es el atajo que
 * pidió el negocio — el cajero repone sin salir de la caja.
 */
async function openStockDialog(reference: IItemStock) {
  stockTarget.value = reference;
  //  El `nextTick` no es adorno: el diálogo está detrás de un `v-if` sobre
  //  `stockTarget`, así que si se abriera en el mismo tick se montaría con
  //  `open` ya en `true` y su `watch(open)` —el que precarga el precio— nunca
  //  dispararía. Montarlo cerrado y abrirlo después es lo que hace que llegue
  //  con el precio de venta puesto.
  await nextTick();
  isStockDialogOpen.value = true;
}

/** Al crear existencias la grilla se recarga: el producto deja de estar agotado y ya es vendible. */
async function onStockCreated() {
  await load();
  const created = stockTarget.value;
  if (created !== null) {
    //  Se selecciona de una: el cajero abrió esto porque quería vender ese
    //  producto, no para administrar inventario.
    const refreshed = references.value.find(
      (item) => item.reference_id === created.reference_id,
    );
    if (refreshed !== undefined && refreshed.units > 0) {
      selectProduct(refreshed);
    }
  }
}

/** `QuantityStepper` ya valida rango/enteros — acá se aplica el piso de 1 (quitar la línea es la X) y el techo del stock. */
function setLineQuantity(referenceId: string, quantity: number) {
  const line = cart.value.find((item) => item.referenceId === referenceId);
  if (line !== undefined) {
    line.quantity = Math.min(line.availableUnits, Math.max(1, quantity));
  }
}

function removeLine(referenceId: string) {
  cart.value = cart.value.filter((item) => item.referenceId !== referenceId);
}

function clearCart() {
  cart.value = [];
}

const isCheckingOut = ref(false);
const collection = ref<InstanceType<typeof PosItemCollection> | null>(null);

/**
 * Cierra la venta contra el servidor. Manda Referencia + cantidad + precio
 * cobrado; el resto —qué unidades físicas salen, el desglose base/IVA, el
 * consecutivo— lo resuelve el backend en una transacción (ver `checkout`).
 *
 * El carrito solo se vacía si la factura salió: si el cobro falla (sin
 * existencias, red caída), lo peor que se puede hacer es borrar lo que el
 * cajero acaba de armar y dejarlo sin saber si cobró o no.
 */
async function onConfirmPayment(payload: {
  customerId: string | null;
  newCustomer: { nit: string | null; fullname: string } | null;
  cash: string;
}) {
  isCheckingOut.value = true;
  try {
    const { data } = await billsApi.checkout({
      customer_id: payload.customerId,
      new_customer: payload.newCustomer,
      lines: cart.value.map(line => ({
        reference_id: line.referenceId,
        quantity: line.quantity,
        unit_price: line.unitPrice,
      })),
    });
    toast.success(`Factura ${data.bill_number} emitida`, { position: "bottom-center" });
    cart.value = [];
    collection.value?.closePayment();
    //  El inventario cambió: las unidades vendidas ya no son vendibles y la
    //  grilla las seguiría ofreciendo hasta el próximo filtro.
    load();
  } catch (error) {
    //  409 = no alcanzan las existencias. Es el único error que el cajero
    //  puede resolver por su cuenta (quitando unidades), así que se dice tal
    //  cual lo explica el servidor en vez de un "algo salió mal".
    const detail = (error as { response?: { data?: { detail?: string } } }).response?.data?.detail;
    toast.error(detail ?? "No se pudo emitir la factura", { position: "bottom-center" });
  } finally {
    isCheckingOut.value = false;
  }
}

const hasFilters = computed(
  () => filters.search !== "" || filters.category !== ALL_CATEGORIES,
);

onMounted(() => {
  referencesStore.fetchCategories().catch(() => {
    toast.error("No se pudieron cargar las categorías", {
      position: "bottom-center",
    });
  });
  //  Los proveedores son para el alta de existencias desde una card agotada.
  //  Se cargan de una y no al abrir el diálogo: es un atajo pensado para no
  //  frenar al cajero, y esperar una petición ahí lo frenaría.
  referencesStore.fetchProviders().catch(() => {
    toast.error("No se pudieron cargar los proveedores", {
      position: "bottom-center",
    });
  });
  load();
  document.addEventListener("click", handleOutsideClick);
});

onUnmounted(() => {
  document.removeEventListener("click", handleOutsideClick);
});
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
    <SidebarInset
      class="h-svh min-w-0 overflow-hidden md:h-[calc(100svh-1rem)]"
    >
      <header
        class="flex h-(--header-height) shrink-0 items-center gap-2 border-b"
      >
        <div class="flex w-full items-center gap-1 px-4 lg:gap-2 lg:px-6">
          <SidebarTrigger class="-ml-1" />
          <Separator
            orientation="vertical"
            class="mx-2 data-[orientation=vertical]:h-4"
          />
          <ModuleNavSelect current="pos" />
          <div class="ml-auto flex items-center gap-2">
            <Sun class="size-4 text-muted-foreground" />
            <Switch v-model="isDark" aria-label="Cambiar a tema oscuro" />
            <Moon class="size-4 text-muted-foreground" />
          </div>
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
                  <SelectItem :value="ALL_CATEGORIES"> Todas </SelectItem>
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
          <div
            ref="gridRef"
            class="min-h-0 flex-1 overflow-y-auto [scrollbar-gutter:stable] rounded-xl border border-border p-4"
          >
            <div v-if="isLoading" class="grid gap-4 grid-cols-2 md:grid-cols-4">
              <PosItemCard
                v-for="placeholder in 12"
                :key="placeholder"
                loading
              />
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
                <PosItemCard
                  v-for="reference in references"
                  :key="reference.reference_id"
                  :reference="reference"
                  :selected="selected?.reference_id === reference.reference_id"
                  @select="selectProduct"
                  @quick-add="quickAddToCart"
                  @add-stock="openStockDialog"
                />

                <!-- La tanda que viene, dentro de la misma grilla: así el hueco
                     ya tiene la forma de las cards que van a llegar. -->
                <PosItemCard
                  v-for="placeholder in isLoadingMore ? 4 : 0"
                  :key="`more-${placeholder}`"
                  loading
                />
              </div>
            </template>
          </div>

          <!--
            Fila 3 — la línea de venta que se está armando. SKU, nombre, IVA y
            precio base se PINTAN desde la Referencia elegida (autocompletado,
            docs/05 §2 Pantalla 3): son datos de catálogo, no se teclean acá.
            Cantidad y descuento sí son del cobro, y son los únicos editables.
          -->
          <div class="selectedItemInputs shrink-0 rounded-xl border border-border p-4 flex flex-col gap-4">
            
            <div class="flex items-center gap-3 pb-2 border-b border-gray-200 ">
                    <!-- Mismo patrón de fondo que las cards de la grilla (D-50): imagen completa, sin recortar. -->
                    <div
                      :style="selected?.image_url ? { backgroundImage: `url('${selected.image_url}')` } : {}"
                      role="img"
                      :aria-label="selected?.title"
                      class="flex size-10 shrink-0 items-center justify-center rounded-md border border-border bg-muted bg-contain bg-center bg-no-repeat text-muted-foreground"
                    >
                      <IconPhoto v-if="!selected?.image_url" class="size-5" />
                    </div>

                    <p class="text-gray-800 text-base m-0 p-0 flex-1 font-semibold ">
                      {{ selected?.title }} {{ selected?.brand }}  {{selected?.sku}}
                    </p>

                    <!-- Existencias del producto elegido: es el tope de lo que se puede cobrar. -->
                    <Badge v-if="selected" variant="secondary" class="shrink-0">
                      {{ selected.units }} en existencia
                    </Badge>

                    <!--
                      Precio final = total de la línea (precio unitario ya con
                      IVA y descuento × cantidad). Antes era un valor quemado.
                      Animado como el resto de cifras derivadas.
                    -->
                    <p class="auto-cols-max text-gray-800 text-base m-0 p-0">
                      Precio Final :
                      <span
                        class="text-back bg-accent text-brand-icon rounded-full px-2 inline-block text-lg font-bold tabular-nums"
                      >
                        {{ selected ? lineTotalDisplay : "$ 0,00" }}
                      </span>
                    </p>

                     
            </div>
            
            <div
              class="grid grid-cols-5 flex-col gap-4 lg:flex-row lg:items-end"
            >
              <div class="grid w-full gap-2 ">
                <Label for="pos-iva">
                  IVA<span v-if="selected" class="text-muted-foreground">
                    ({{ formatPercentage(selected.iva_percentage) }}%)</span
                  >
                </Label>
                <Input
                  id="pos-iva"
                  :model-value="selected ? ivaAmountDisplay : ''"
                  readonly
                  class="w-full bg-muted/40 tabular-nums"
                />
              </div>

              <div class="grid w-full gap-2">
                <Label for="pos-base-price">Precio Base</Label>
                <Input
                  id="pos-base-price"
                  :model-value="selected ? basePriceDisplay : ''"
                  readonly
                  class="bg-muted/40 tabular-nums"
                />
              </div>

              <!-- `max` = existencias menos lo que ya está en el carrito de este mismo producto. -->
              <div class="grid w-full gap-2">
                <Label for="pos-quantity">
                  Cantidad<span v-if="selected" class="text-muted-foreground">
                    (máx. {{ maxQuantity }})</span
                  >
                </Label>
                <Input
                  id="pos-quantity"
                  v-model.number="quantity"
                  type="number"
                  min="1"
                  :max="maxQuantity"
                  step="1"
                  :disabled="!selected"
                  class="tabular-nums"
                />
              </div>

              <!-- Monto en pesos sobre el total de la línea, no un %. Tope: la base de la línea. -->
              <div class="grid w-full gap-2 ">
                <Label for="pos-discount">Descuento</Label>
                <div class="relative">
                  <IconCurrencyDollar
                    class="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
                  />
                  <NumericMaskInput
                    id="pos-discount"
                    v-model="discount"
                    :max="maxDiscount"
                    :disabled="!selected"
                    class="pl-8"
                    placeholder="0"
                  />
                </div>
              </div>


              <Button
                    class="shrink-0 gap-2 text-white hover:text-white"
                    :disabled="!selected"
                    @click="addToCart"
                  >
                    Agregar
                    <IconPlus class="size-4" />
                  </Button>
            </div>
          
          </div>
        </section>

        <!-- Columna 2 — detalle de la factura y cobro (emite contra `/bills/checkout`). -->
        <PosItemCollection
          ref="collection"
          :items="cart"
          :highlighted-id="highlightedId"
          :is-submitting="isCheckingOut"
          @update:quantity="setLineQuantity"
          @remove="removeLine"
          @clear="clearCart"
          @confirm="onConfirmPayment"
        />
      </div>
    </SidebarInset>

    <!--
      Alta de existencias sin salir de la caja, para el producto agotado que se
      acaba de tocar. Se reusa el mismo diálogo de la pantalla de Producto en vez
      de escribir otro: si cambia la forma de dar de alta una unidad, cambia en
      un solo lugar.
    -->
    <CreateStockUnitDialog
      v-if="stockTarget"
      v-model:open="isStockDialogOpen"
      :reference-id="stockTarget.reference_id"
      :default-price="stockTarget.sale_price"
      :providers="referencesStore.providers"
      @created="onStockCreated"
    />
  </SidebarProvider>
</template>
