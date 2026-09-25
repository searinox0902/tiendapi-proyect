<script setup lang="ts">
import { computed } from "vue"
import { IconArrowRight, IconCircleCheckFilled, IconClockHour4 } from "@tabler/icons-vue"

import { Button } from "@/components/ui/button"
import type { IPayrollPeriod, IEmployee } from "./payroll.types"

/**
 * Franja de cortes: el único elemento de la pantalla que se comporta como
 * botón. Es la costura entre la pantalla que **informa** (el calendario) y la
 * que **trabaja** (la tabla de liquidación, aún por construir).
 *
 * Responde sin un solo clic la pregunta "¿qué viene?", que es la razón por la
 * que el calendario es la pantalla de aterrizaje: es el único lugar del módulo
 * que mira hacia adelante — todo lo demás es retrospectivo.
 *
 * **Ya no son dos tarjetas fijas.** Con días de corte configurables (D-111) un
 * mes puede tocar uno, dos o tres tramos, y sus extremos caer fuera del mes
 * visible — de ahí que cada tarjeta muestre su rango completo ("20 ago – 4
 * sep") en vez de un número de corte.
 *
 * Los contratistas viven acá y no en la grilla de días: no tienen días
 * laborados ni ausencias, así que una fila en el calendario estaría siempre
 * vacía. Lo que sí tienen es un corte en el que se les paga.
 */

const props = defineProps<{
  periods: IPayrollPeriod[]
  daysUntilClose: number | null
  employeeCount: number
  contractors: IEmployee[]
}>()

const emit = defineEmits<{
  settle: [period: IPayrollPeriod]
}>()

/**
 * Con tres tramos las tarjetas se estrechan; con uno solo ocuparía todo el
 * ancho y se leería como un banner. Se acota a dos columnas mínimo.
 */
const gridClass = computed(() =>
  props.periods.length >= 3 ? "sm:grid-cols-3" : "sm:grid-cols-2",
)

/** "cierra en 4 días" / "cierra hoy" / "cierra mañana" — nunca una fecha cruda. */
const closingLabel = computed(() => {
  if (props.daysUntilClose === null) {
    return null
  }
  if (props.daysUntilClose <= 0) {
    return "cierra hoy"
  }
  if (props.daysUntilClose === 1) {
    return "cierra mañana"
  }
  return `cierra en ${props.daysUntilClose} días`
})
</script>

<template>
  <div class="grid gap-3" :class="gridClass">
    <div
      v-for="period in periods"
      :key="period.id"
      class="flex items-center justify-between gap-3 rounded-xl border px-4 py-3 transition"
      :class="
        period.status === 'open' ? 'border-primary/40 bg-primary/5' : 'border-border bg-card'
      "
    >
      <div class="min-w-0">
        <p class="truncate text-sm font-medium">{{ period.label }}</p>

        <p class="mt-0.5 flex items-center gap-1.5 text-xs text-muted-foreground">
          <template v-if="period.status === 'closed'">
            <IconCircleCheckFilled class="size-3.5 shrink-0 text-emerald-500" />
            Cerrado · {{ employeeCount }} personas
          </template>
          <template v-else-if="period.status === 'open'">
            <IconClockHour4 class="size-3.5 shrink-0 text-brand-icon" />
            Abierto · {{ employeeCount }} personas<template v-if="closingLabel">
              · {{ closingLabel }}</template>
          </template>
          <template v-else> Aún no empieza </template>
        </p>

        <p v-if="contractors.length" class="mt-1 truncate text-xs text-muted-foreground">
          + {{ contractors.length }} por prestación de servicios
        </p>
      </div>

      <Button
        v-if="period.status === 'open'"
        size="sm"
        class="shrink-0"
        @click="emit('settle', period)"
      >
        Liquidar
        <IconArrowRight class="size-4" />
      </Button>
      <Button
        v-else-if="period.status === 'closed'"
        variant="ghost"
        size="sm"
        class="shrink-0"
        @click="emit('settle', period)"
      >
        Ver
      </Button>
    </div>
  </div>
</template>
