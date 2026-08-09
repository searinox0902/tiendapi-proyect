<script setup lang="ts">
import { computed } from "vue"
import { IconPhoto } from "@tabler/icons-vue"

import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { computeSalePrice, formatCurrency } from "@/lib/money"
import type { IReference } from "@/api/references/references.types"

/**
 * Card horizontal de producto en la caja registradora: imagen a la izquierda,
 * SKU / nombre / precio a la derecha.
 *
 * El esqueleto de carga vive **acá adentro** (`loading`) y no como componente
 * aparte a propósito: es el mismo árbol de nodos con las mismas clases, así que
 * la card real y su placeholder no pueden quedar con geometrías distintas
 * cuando alguna de las dos se retoque. Un skeleton en otro archivo se
 * desincroniza en cuanto la maquetación cambia — que es justo lo que le pasó al
 * que estaba escrito a mano dentro de `posView`.
 */
const props = defineProps<{
  /** Ausente cuando `loading` está activo: ahí no hay Referencia todavía. */
  reference?: IReference
  selected?: boolean
  loading?: boolean
}>()

defineEmits<{
  select: [reference: IReference]
}>()

/**
 * Precio de venta con IVA, redondeado al múltiplo de $50 (D-45/D-46) — el mismo
 * cálculo que el servidor, para que lo que ve el cajero sea lo que se cobra.
 */
const salePrice = computed(() =>
  props.reference === undefined
    ? ""
    : formatCurrency(computeSalePrice(props.reference.base_price, props.reference.iva_percentage)),
)
</script>

<template>
  <Card
    class="flex gap-4 overflow-hidden p-2 rounded-lg transition-all"
    :class="[
      loading ? '' : 'cursor-pointer hover:border-primary',
      selected ? 'border-primary ring-2 ring-primary/30' : '',
    ]"
    @click="!loading && reference && $emit('select', reference)"
  >
    <div class="flex">
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
        class="h-full w-1/3 rounded-lg shrink-0 bg-muted bg-contain bg-center bg-no-repeat border-b border-border"
      > &nbsp; </div>
      <div
        v-else
        class="h-full w-1/3 rounded-lg flex shrink-0 bg-muted aspect-square items-center justify-center border-b border-dashed border-border text-muted-foreground"
      >
        <IconPhoto class="size-7" />
      </div>

      <!--
        `min-w-0`: sin esto un hijo de flex no baja de su ancho de contenido y
        los `truncate` de abajo no recortan nada — el texto largo volvería a
        estirar la card.
      -->
      <CardContent class="min-w-0 flex-1 min-h-16 space-y-1 p-3">
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
          <p class="truncate text-sm font-medium">
            {{ reference.sku }}
          </p>
          <p class="truncate text-xs text-muted-foreground" :title="reference.title">
            {{ reference.title }}
          </p>
          <p class="truncate text-sm font-semibold tabular-nums">
            {{ salePrice }}
          </p>
        </template>
      </CardContent>
    </div>
  </Card>
</template>
