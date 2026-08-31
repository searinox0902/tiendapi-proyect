<script setup lang="ts">
import { computed } from "vue"
import { IconPhoto } from "@tabler/icons-vue"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { computeSalePrice, formatCurrency } from "@/lib/money"
import type { IItemStock } from "@/api/items/items.types"

/**
 * Card horizontal de producto en la caja registradora: imagen a la izquierda,
 * SKU / nombre / precio a la derecha.
 *
 * El esqueleto de carga vive **acá adentro** (`loading`) y no como componente
 * aparte a propósito: es el mismo árbol de nodos con las mismas clases, así que
 * la card real y su placeholder no pueden quedar con geometrías distintas
 * cuando alguna de las dos se retoque. Un skeleton en otro archivo se
 * desincroniza en cuanto la maquetación cambia — que es justo lo que le pasó al
 * que estaba escrito a mano dentro de `PosView`.
 */
const props = defineProps<{
  /** Ausente cuando `loading` está activo: ahí no hay producto todavía. */
  reference?: IItemStock
  selected?: boolean
  loading?: boolean
}>()

const emit = defineEmits<{
  select: [reference: IItemStock]
  quickAdd: [reference: IItemStock]
  /** Agotado: en vez de seleccionar, se ofrece cargarle existencias en el momento. */
  addStock: [reference: IItemStock]
}>()

/** Sin unidades vendibles no hay nada que cobrar: la card cambia de acción, no se deshabilita. */
const isOutOfStock = computed(() => props.reference !== undefined && props.reference.units === 0)

/**
 * Ventana del doble clic, en ms. Deliberadamente **más corta** que el ~500ms
 * del `dblclick` nativo: con la ventana larga, volver a hacer clic en la card
 * que ya estaba seleccionada —para revisarla— agregaba un producto sin querer.
 * Acá el segundo clic tiene que ser claramente intencional.
 *
 * El costo de no usar `dblclick` nativo es que se ignora el intervalo que el
 * usuario tenga configurado en su sistema operativo; si a alguien le queda
 * incómodo, este número es la perilla.
 */
const DOUBLE_CLICK_MS = 300
let lastClickAt = 0

function onClick(event: MouseEvent) {
  if (props.loading || props.reference === undefined) {
    return
  }
  //  El foco no se deja al navegador: es lo que habilita el "clic y Enter", y
  //  hacerlo explícito evita depender de cómo cada navegador trate el clic
  //  sobre un elemento con `tabindex`.
  ;(event.currentTarget as HTMLElement).focus()
  //  Agotado: un solo clic abre "agregar existencias". No hay doble clic que
  //  valga — no se puede vender lo que no hay, y hacer esperar un segundo clic
  //  solo retrasaría la única acción posible.
  if (isOutOfStock.value) {
    emit("addStock", props.reference)
    return
  }
  const now = Date.now()
  const isFastDoubleClick = now - lastClickAt <= DOUBLE_CLICK_MS
  //  Se reinicia el reloj tras un doble clic para que un tercer clic no
  //  encadene otro agregado sin querer.
  lastClickAt = isFastDoubleClick ? 0 : now
  //  `if` y no `emit(cond ? "quickAdd" : "select", …)`: con `defineEmits`
  //  tipado, el ternario produce el tipo `"quickAdd" | "select"` y TypeScript
  //  lo compara contra cada sobrecarga por separado, así que ninguna calza y
  //  falla el build. Separarlos deja cada llamada con su nombre literal.
  if (isFastDoubleClick) {
    emit("quickAdd", props.reference)
  } else {
    emit("select", props.reference)
  }
}

/** Con la card enfocada (el clic la enfoca), Enter agrega directo. */
function onEnter() {
  if (props.loading || props.reference === undefined) {
    return
  }
  //  Mismo motivo que en `onClick`: nombre literal por rama.
  if (isOutOfStock.value) {
    emit("addStock", props.reference)
  } else {
    emit("quickAdd", props.reference)
  }
}

/**
 * Precio de venta con IVA, redondeado al múltiplo de $50 (D-45/D-46) — el mismo
 * cálculo que el servidor, para que lo que ve el cajero sea lo que se cobra.
 */
const salePrice = computed(() =>
  props.reference === undefined
    ? ""
    : formatCurrency(computeSalePrice(props.reference.base_price, props.reference.iva_percentage)),
)

const stockLabel = computed(() => {
  if (props.reference === undefined) return ""
  return props.reference.units === 1 ? "1 unidad" : `${props.reference.units} unidades`
})
</script>

<template>
  <!--
    `select-none`: sin esto el doble clic selecciona el texto del SKU y la card
    queda con media línea resaltada en azul cada vez que se agrega rápido.
    `tabindex` la hace enfocable — el clic la enfoca, y de ahí que Enter pueda
    agregar sin tener que volver al mouse.
  -->
  <Card
    class="flex gap-4 select-none overflow-hidden p-2 rounded-lg transition-all outline-none focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/30"
    :class="[
      loading ? '' : 'cursor-pointer hover:border-primary',
      selected ? 'border-primary ring-2 ring-primary/30' : '',
      /* Agotado: atenuado para que se lea distinto de un vendible, pero sin
         `disabled` — sigue siendo clicable, es por donde se le carga stock. */
      isOutOfStock ? 'border-dashed opacity-70 hover:opacity-100' : '',
    ]"
    :tabindex="loading ? -1 : 0"
    @click="onClick"
    @keydown.enter.prevent="onEnter"
  >
    <div class="flex w-full h-full">
      <!--
        `size-20 shrink-0` es lo único que se le agregó a la maquetación: en una
        fila flex, `aspect-square` sin ancho propio crece hasta ocupar la card
        entera y empuja el texto fuera del `overflow-hidden` (medido: 247px de
        contenido dentro de 134px de card — SKU, nombre y precio quedaban
        invisibles). Con un lado fijo, la imagen manda su tamaño y el texto se
        queda con el resto.
      -->
      <Skeleton v-if="loading" class="size-20 shrink-0 rounded-none" />

      <!--
        `background` en vez de `<img>`: a diferencia de `object-cover`, que
        recorta lo que no entra, `bg-contain` siempre muestra la imagen
        completa (aunque no sea 1:1 — la máscara de un dato viejo o subido por
        fuera del flujo de recorte D-50) y `bg-center` la deja centrada dentro
        del cuadro sin deformarla.
      -->
      <div
        v-else-if="reference?.image_url"
        :style="{ backgroundImage: `url('${reference.image_url}')` }"
        :aria-label="reference.title"
        role="img"
        class="h-full w-1/3 rounded-lg shrink-0 bg-contain bg-center bg-no-repeat "
      > &nbsp; </div>
      <div
        v-else
        class="h-full w-1/3 rounded-lg flex shrink-0 bg-gray-100  aspect-square items-center justify-center  text-muted-foreground"
      >
        <IconPhoto class="size-7" />
      </div>

      <!--
        `min-w-0`: sin esto un hijo de flex no baja de su ancho de contenido y
        los `truncate` de abajo no recortan nada — el texto largo volvería a
        estirar la card.
      -->
      <CardContent class="min-w-0 flex-1 items-center  my-auto min-h-16 space-y-1 p-3">
        <!--
          Las alturas NO son estéticas: `h-5 / h-4 / h-5` son exactamente el
          `line-height` de `text-sm / text-xs / text-sm` de los tres párrafos de
          abajo. Con las barras más delgadas la card de carga medía 82px y la
          real 90px, así que la grilla entera daba un salto de 8px por fila al
          llegar los datos. Solo el ancho varía, para que se lea como texto.
        -->
        <template v-if="loading">
          <Skeleton class="h-5 w-20" />
          <Skeleton class="h-4 w-28" />
          <Skeleton class="h-5 w-16" />
        </template>

        <template v-else-if="reference">
          <p class="truncate text-sm font-mono font-medium text-gray-400">
            {{ reference.sku }}
          </p>
          <p class="text-sm line-clamp-2 " :title="reference.title">
            {{ reference.title }}
          </p>
          <div class="flex flex-wrap items-center gap-1.5">
            <p class="truncate py-1 px-3 rounded-full bg-accent inline-block text-sm font-semibold tabular-nums">
              {{ salePrice }}
            </p>
            <!--
              Agotado se resalta en vez de esconderse: es la card sobre la que
              hay que actuar, y el texto dice qué pasa al tocarla.
            -->
            <Badge :variant="isOutOfStock ? 'destructive' : 'secondary'" class="shrink-0">
              {{ isOutOfStock ? "Agotado" : stockLabel }}
            </Badge>
          </div>
          
        </template>
      </CardContent>
    </div>
  </Card>
</template>
