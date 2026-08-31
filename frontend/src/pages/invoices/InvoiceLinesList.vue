<script setup lang="ts">
import { IconPhoto } from "@tabler/icons-vue"

import { formatCurrency, formatQuantity, toDecimal } from "@/lib/money"
import type { IBillDetailLine } from "@/api/bills/bills.types"

/**
 * Lista de ítems vendidos de una factura ya emitida.
 *
 * Es una **copia de solo lectura** de `pos/PosItemCollection.vue`, no ese
 * componente reusado con un flag: allá cada renglón trae la botonera de
 * cantidad y la X de quitar, y acá no hay nada que editar — una factura
 * emitida no se modifica, se anula (D-60). Reusarlo con `v-if` en cada control
 * habría dejado un componente que hace dos cosas distintas y en el que un
 * descuido de props vuelve editable un documento cerrado.
 *
 * La otra diferencia de fondo: allá los totales se **calculan** en el cliente
 * porque la venta todavía se está armando; acá llegan del servidor, que es la
 * autoridad final (docs/04). Recalcularlos en pantalla podría mostrar una cifra
 * distinta a la que quedó guardada en la factura.
 */
defineProps<{
  lines: IBillDetailLine[]
  /** Los tres vienen de `Bill`, tal cual se guardaron. No se recalculan acá. */
  subtotal: string
  totalIva: string
  total: string
  /** Anulada: el detalle se atenúa para que no se lea como una venta vigente. */
  voided?: boolean
}>()

function money(value: string) {
  return formatCurrency(toDecimal(value))
}

/** Compartido con el PDF del paquete (D-78) — ver `formatQuantity`. */
const quantity = formatQuantity
</script>

<template>
  <aside
    class="flex w-full shrink-0 flex-col overflow-hidden rounded-xl border border-border bg-card lg:w-[320px]"
    :class="voided ? 'opacity-60' : ''"
  >
    <h2 class="shrink-0 border-b border-border px-4 py-3 text-sm font-semibold">
      Detalle factura
    </h2>

    <!-- Scrollea sola; los totales quedan fijos abajo, igual que en la caja. -->
    <div class="min-h-0 flex-1 overflow-y-auto p-3">
      <p v-if="lines.length === 0" class="px-1 py-8 text-center text-xs text-muted-foreground">
        Esta factura no tiene ítems.
      </p>

      <div class="space-y-2">
        <div
          v-for="line in lines"
          :key="`${line.reference_id}-${line.unit_price}`"
          class="rounded-lg border border-border p-2"
        >
          <div class="flex items-start gap-2">
            <!-- Mismo patrón de fondo que la caja (D-50): muestra la imagen completa, sin recortarla. -->
            <div
              :style="line.image_url ? { backgroundImage: `url('${line.image_url}')` } : {}"
              role="img"
              :aria-label="line.title"
              class="flex size-10 shrink-0 items-center justify-center rounded-md border border-border bg-muted bg-contain bg-center bg-no-repeat text-muted-foreground"
            >
              <IconPhoto v-if="!line.image_url" class="size-4" />
            </div>

            <div class="min-w-0 flex-1">
              <p class="truncate font-mono text-sm font-medium text-gray-400">
                {{ line.sku }}
              </p>
              <p class="text-sm" :title="line.title">
                {{ line.title }}
              </p>
            </div>
          </div>

          <div class="mt-2 flex items-center justify-between gap-2">
            <!--
              Donde en la caja va la botonera, acá va la cantidad como dato:
              el hueco lo ocupa el mismo renglón para que las dos pantallas se
              lean parecido, pero no hay nada que tocar.
            -->
            <span class="rounded-md bg-muted px-2 py-0.5 text-xs font-medium tabular-nums">
              × {{ quantity(line.quantity) }}
            </span>

            <div class="min-w-0 text-right">
              <p class="truncate text-[10px] tabular-nums text-muted-foreground">
                {{ money(line.unit_price) }} c/u
              </p>
              <p class="truncate text-xs font-semibold tabular-nums">
                {{ money(line.total) }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="shrink-0 space-y-1 border-t border-border bg-card p-3 text-xs">
      <div class="flex items-center justify-between gap-2">
        <span class=" text-base">Subtotal</span>
        <span class="tabular-nums text-base">{{ money(subtotal) }}</span>
      </div>
      <div class="flex items-center justify-between gap-2">
        <span class="text-base">IVA total</span>
        <span class="tabular-nums text-base">{{ money(totalIva) }}</span>
      </div>
      <div class="flex items-center justify-between gap-2 pt-1">
        <span class="font-bold text-lg">Total</span>
        <span class="font-bold text-lg px-4 py-1 bg-accent rounded-full" :class="voided ? 'line-through' : 'text-brand-icon'">
          {{ money(total) }}
        </span>
      </div>
    </div>
  </aside>
</template>
