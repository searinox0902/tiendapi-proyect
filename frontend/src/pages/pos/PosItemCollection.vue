<script setup lang="ts">
import { computed, ref } from "vue"
import { IconPhoto, IconReceipt, IconTrash, IconX } from "@tabler/icons-vue"

import QuantityStepper from "@/components/QuantityStepper.vue"
import { Button } from "@/components/ui/button"
import { useAnimatedCurrency } from "@/composables/useAnimatedCurrency"
import { basePriceFromGross, formatCurrency, toDecimal } from "@/lib/money"
import PosPaymentDialog from "./PosPaymentDialog.vue"
import type { IPosCartLine } from "./pos.types"

/**
 * Columna 2 de la caja: el detalle de la factura que se está armando.
 *
 * Los totales se calculan **acá** y con `Decimal` (docs/05, §3.4 — nunca float):
 * es el único lugar que conoce todas las líneas, así que tenerlos en otro lado
 * obligaría a pasarlos hacia abajo y a mantener dos fuentes de la misma cifra.
 * Sigue siendo una vista previa: la factura real la valida el servidor (docs/04).
 */
const props = defineProps<{
  items: IPosCartLine[]
  /** Línea recién tocada por "Agregar": se resalta un instante. Ver `highlightClass`. */
  highlightedId?: string | null
  /** Cobro en curso — bloquea el botón para no emitir la factura dos veces. */
  isSubmitting?: boolean
}>()

const emit = defineEmits<{
  "update:quantity": [referenceId: string, quantity: number]
  remove: [referenceId: string]
  clear: []
  confirm: [payload: {
    customerId: string | null
    newCustomer: { nit: string | null; fullname: string } | null
    cash: string
  }]
}>()

const isPaymentOpen = ref(false)

/** Cerrar el modal es responsabilidad del padre: solo debe cerrarse si la factura salió bien. */
defineExpose({ closePayment: () => { isPaymentOpen.value = false } })

/** Total cobrado de una línea: es el dato firme, de acá se derivan base e IVA. */
function lineTotal(line: IPosCartLine) {
  return toDecimal(line.unitPrice).times(line.quantity)
}

const total = computed(() =>
  props.items.reduce((sum, line) => sum.plus(lineTotal(line)), toDecimal(0)),
)

/**
 * Base imponible: se descompone desde lo cobrado, línea por línea. Sumar las
 * bases del catálogo daría un total distinto al que paga el cliente, porque el
 * precio de venta pasó por el redondeo a $50 (D-46).
 */
const subtotal = computed(() =>
  props.items.reduce(
    (sum, line) => sum.plus(basePriceFromGross(line.unitPrice, line.ivaPercentage).times(line.quantity)),
    toDecimal(0),
  ),
)

/** Por resta, no por fórmula: así `subtotal + IVA` siempre da exactamente `total`. */
const ivaTotal = computed(() => total.value.minus(subtotal.value))

//  Las tres cifras corren al agregar o quitar líneas, en vez de saltar de un
//  número al otro: es el mismo `useAnimatedCurrency` del alta de Referencias.
const subtotalDisplay = useAnimatedCurrency(subtotal)
const ivaTotalDisplay = useAnimatedCurrency(ivaTotal)
const totalDisplay = useAnimatedCurrency(total)

</script>

<template>
  <aside
    class="posItemCollection hidden w-[265px] shrink-0 flex-col overflow-hidden rounded-xl border border-border bg-card lg:flex"
  >
    <h2 class="shrink-0 border-b border-border px-4 py-3 text-sm font-semibold">
      Detalle factura
    </h2>

    <!-- Lista de items seleccionados. Scrollea sola; el cobro queda fijo abajo. -->
    <div class="min-h-0 flex-1 overflow-y-auto p-3">
      <p v-if="items.length === 0" class="px-1 py-8 text-center text-xs text-muted-foreground">
        Sin productos agregados todavía.
      </p>

      <!--
        La línea entra deslizándose desde la derecha — desde el lado donde está
        la grilla — para que se lea de dónde vino. `move-class` es lo que evita
        que las de abajo den un brinco al abrirse el hueco; la que sale pasa a
        `absolute` (de ahí el `relative` del contenedor) para que no siga
        ocupando alto mientras se desvanece y las demás suban de una.
      -->
      <TransitionGroup
        tag="div"
        class="relative space-y-2"
        enter-active-class="transition-all duration-300 ease-out"
        enter-from-class="opacity-0 translate-x-4"
        leave-active-class="transition-all duration-200 ease-in absolute w-[calc(100%-1.5rem)]"
        leave-to-class="opacity-0 scale-95"
        move-class="transition-transform duration-200"
      >
        <div
          v-for="line in items"
          :key="line.referenceId"
          class="rounded-lg border p-2 transition-colors duration-500"
          :class="highlightedId === line.referenceId
            ? 'border-primary bg-primary/5'
            : 'border-border bg-transparent'"
        >
          <div class="flex items-start gap-2">
            <!-- Mismo patrón de fondo que la card de la grilla (D-50): muestra la imagen completa, sin recortarla. -->
            <div
              :style="line.imageUrl ? { backgroundImage: `url('${line.imageUrl}')` } : {}"
              role="img"
              :aria-label="line.title"
              class="flex size-10 shrink-0 items-center justify-center rounded-md border border-border bg-muted bg-contain bg-center bg-no-repeat text-muted-foreground"
            >
              <IconPhoto v-if="!line.imageUrl" class="size-4" />
            </div>

            <div class="min-w-0 flex-1">
              <p class="text-gray-400 font-mono truncate text-sm font-medium">
                {{ line.sku }}
              </p>
              <p class="text-sm " :title="line.title">
                {{ line.title }}
              </p>
            </div>

            <button
              type="button"
              class="shrink-0 rounded-md p-0.5 text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
              :aria-label="`Quitar ${line.sku}`"
              @click="emit('remove', line.referenceId)"
            >
              <IconX class="size-3.5" />
            </button>
          </div>

          <div class="mt-2 flex items-center justify-between gap-2">
            <!-- `max` = existencias reales: sin esto se puede subir la cantidad por encima de lo que hay y el cobro revienta al final. -->
            <QuantityStepper
              :model-value="line.quantity"
              :max="line.availableUnits"
              size="xs"
              @update:model-value="quantity => emit('update:quantity', line.referenceId, quantity)"
            />

            <div class="min-w-0 text-right">
              <p class="truncate text-[10px] tabular-nums" :class="line.quantity >= line.availableUnits ? 'text-destructive' : 'text-muted-foreground'">
                {{ line.quantity >= line.availableUnits ? `máx. ${line.availableUnits}` : `${formatCurrency(toDecimal(line.unitPrice))} c/u` }}
              </p>
              <p class="truncate text-xs font-semibold tabular-nums">
                {{ formatCurrency(lineTotal(line)) }}
              </p>
            </div>
          </div>
        </div>
      </TransitionGroup>
    </div>

    <!--
      Cobro. Aparece solo con líneas cargadas: con el carrito vacío no hay nada
      que totalizar y unos ceros invitan a cobrar una factura en blanco.

      Queda pegado abajo por el flujo flex (`shrink-0` al final de una columna
      cuya lista es `flex-1`), no por `absolute`. Con `absolute` sale del flujo
      y **tapa** las últimas líneas del detalle: medido, con 6 productos la
      última fila quedaba 284px por debajo del borde del bloque de cobro. La
      salida sería medir su alto en vivo y devolvérselo a la lista como padding
      — más piezas móviles para llegar al mismo píxel que da el flex solo.
    -->
    <div
      v-if="items.length > 0"
      class="shrink-0 space-y-3 border-t border-border bg-card p-3"
    >
      <!--
        Nombre del cliente y efectivo ya no viven acá: se fueron al modal de
        cobro. En 265px competían por el mismo aire que el detalle, que es lo
        que el cajero necesita ver mientras arma la venta.
      -->
      <div class="space-y-1 text-xs">
        <div class="flex items-center justify-between gap-2">
          <span class="text-muted-foreground">Subtotal</span>
          <span class="tabular-nums">{{ subtotalDisplay }}</span>
        </div>
        <div class="flex items-center justify-between gap-2">
          <span class="text-muted-foreground">IVA total</span>
          <span class="tabular-nums">{{ ivaTotalDisplay }}</span>
        </div>
        <div class="flex items-center justify-between gap-2 pt-1">
          <span class="font-medium">Total a pagar</span>
          <span class="text-sm font-bold tabular-nums text-brand-icon">{{ totalDisplay }}</span>
        </div>
      </div>

      <div class="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          class="shrink-0 text-destructive hover:text-destructive"
          aria-label="Vaciar detalle"
          @click="emit('clear')"
        >
          <IconTrash class="size-4" />
        </Button>
        <Button
          size="sm"
          class="flex-1 gap-1.5 text-white hover:text-white"
          @click="isPaymentOpen = true"
        >
          <IconReceipt class="size-4" />
          Facturar
        </Button>
      </div>
    </div>

    <PosPaymentDialog
      v-model:open="isPaymentOpen"
      :subtotal="subtotal"
      :iva-total="ivaTotal"
      :total="total"
      :is-submitting="isSubmitting"
      @confirm="payload => emit('confirm', payload)"
    />
  </aside>
</template>
