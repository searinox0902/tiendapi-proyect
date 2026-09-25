<script setup lang="ts">
import { computed } from "vue"
import { IconArrowLeft } from "@tabler/icons-vue"

import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Separator } from "@/components/ui/separator"
import { formatCurrency } from "@/lib/money"
import DayActionsPopover from "./DayActionsPopover.vue"
import { NOVELTY_CHIP, NOVELTY_COLOR } from "./dayActions"
import type { IDayAction } from "./dayActions"
import { formatHours, hoursForEmployee } from "./dayHours"
import { MONTH_NAMES, WEEKDAY_LABELS } from "./usePayrollCalendar"
import type { ICalendarDay, IEmployee, IMarker, INovelty } from "./payroll.types"

/**
 * Una persona en un día concreto.
 *
 * **Todo lo que muestra está acotado a ese día**, y eso no es un recorte: es
 * coherencia. Al modal se llega haciendo clic en alguien *dentro del detalle de
 * un día*, así que hablar del mes rompe el hilo — el usuario venía siguiendo
 * una fecha y de pronto le contestan otra pregunta.
 *
 * Por eso las secciones dicen "Novedades" y no "Novedades del mes": el mes ya
 * está implícito en el calendario que quedó atrás, y repetirlo acá sobra.
 *
 * Lo único que se sale del día a propósito es el **rango** de una novedad: unas
 * vacaciones que cubren el 13 empezaron el 11 y terminan el 15, y mostrar solo
 * "13" escondería que es un evento y no una marca suelta.
 */

const props = defineProps<{
  open: boolean
  employee: IEmployee | null
  day: ICalendarDay | null
  /** Todas las novedades de la persona; acá se filtran al día. */
  novelties: INovelty[]
  markers: IMarker[]
  hoursPerDay: number
}>()

const emit = defineEmits<{
  "update:open": [value: boolean]
  /** Vuelve al detalle del día: sin esto el modal encadenado pierde el camino de regreso. */
  back: []
  /** Una acción del "...", ya sabiendo de quién es: la captura abre con la persona puesta. */
  action: [payload: { employeeId: string; action: IDayAction }]
}>()

const dayLabel = computed(() => {
  if (!props.day) {
    return ""
  }
  const [year, month, dayNumber] = props.day.date.split("-").map(Number)
  const weekday = WEEKDAY_LABELS[(new Date(year, month - 1, dayNumber).getDay() + 6) % 7]
  return `${weekday} ${dayNumber} de ${MONTH_NAMES[month - 1]?.toLowerCase()}`
})

/** Las novedades que cubren este día — normalmente una, a veces ninguna. */
const dayNovelties = computed(() =>
  props.novelties.filter(
    (novelty) => props.day && props.day.date >= novelty.start && props.day.date <= novelty.end,
  ),
)

const dayMarkers = computed(() => props.markers.filter((marker) => marker.date === props.day?.date))

const hours = computed(() => {
  if (!props.day || !props.employee) {
    return null
  }
  return hoursForEmployee(props.day, props.employee.id, dayNovelties.value[0], props.hoursPerDay)
})

const stateChip = computed(() => {
  const novelty = dayNovelties.value[0]
  if (novelty) {
    const partial = novelty.span !== "full_day"
    return {
      label: partial ? `${NOVELTY_CHIP[novelty.kind]} parcial` : NOVELTY_CHIP[novelty.kind],
      color: NOVELTY_COLOR[novelty.kind],
    }
  }
  if (props.day && !props.day.isWorkingDay) {
    return { label: "Día no laborable", color: null }
  }
  return { label: "Laboró", color: null }
})

/**
 * Costo del día para esta persona, proporcional a la jornada cubierta.
 *
 * Misma limitación que el total del detalle del día: una novedad de día
 * completo lo lleva a cero, cuando la ley es más fina —las vacaciones se pagan,
 * la incapacidad al 66,67% desde el tercer día—. El motor legal no existe
 * todavía (D-113, modo simple).
 */
const dayCost = computed(() => {
  if (!props.employee || !hours.value || !props.hoursPerDay) {
    return 0
  }
  return (props.employee.dailyCost * hours.value.worked) / props.hoursPerDay
})

/** "del 11 al 15" — una novedad de varios días no es una marca suelta. */
function rangeLabel(novelty: INovelty): string | null {
  if (novelty.start === novelty.end) {
    return null
  }
  const day = (iso: string) => Number(iso.split("-")[2])
  return `del ${day(novelty.start)} al ${day(novelty.end)}`
}
</script>

<template>
  <Dialog :open="open" @update:open="emit('update:open', $event)">
    <DialogContent v-if="employee" class="max-h-[88vh] sm:max-w-2xl">
      <DialogHeader>
        <!-- El regreso explícito: encadenar modales sin él deja al usuario sin
             forma de volver al día del que venía. -->
        <Button
          variant="ghost"
          size="sm"
          class="-ml-2 h-7 w-fit gap-1 px-2 text-xs text-muted-foreground"
          @click="emit('back')"
        >
          <IconArrowLeft class="size-3.5" />
          Volver al día
        </Button>

        <div class="flex items-center gap-3 pt-1">
          <Avatar class="size-14 shrink-0">
            <AvatarFallback class="bg-muted text-lg font-medium">
              {{ employee.initials }}
            </AvatarFallback>
          </Avatar>
          <div class="min-w-0 flex-1">
            <DialogTitle class="truncate text-lg">{{ employee.name }}</DialogTitle>
            <DialogDescription class="truncate">
              {{ employee.role }}
              <template v-if="employee.workerType === 'contractor'">
                · Prestación de servicios</template>
            </DialogDescription>
          </div>

          <DayActionsPopover
            v-if="day"
            :date="day.date"
            variant="standalone"
            @select="emit('action', { employeeId: employee.id, action: $event })"
          />
        </div>
      </DialogHeader>

      <div class="max-h-[60vh] min-h-[20rem] space-y-4 overflow-y-auto pr-1">
        <!-- El día: estado, jornada y costo. Es el asunto del modal. -->
        <div class="rounded-xl border border-border p-4">
          <div class="flex items-center justify-between gap-3">
            <p class="text-sm font-medium capitalize">{{ dayLabel }}</p>
            <span
              class="rounded-full px-2.5 py-1 text-xs font-medium"
              :style="
                stateChip.color
                  ? {
                      backgroundColor: `color-mix(in oklch, ${stateChip.color} 18%, transparent)`,
                      color: stateChip.color,
                    }
                  : undefined
              "
              :class="stateChip.color ? '' : 'bg-muted text-muted-foreground'"
            >
              {{ stateChip.label }}
            </span>
          </div>

          <div class="mt-4 grid grid-cols-3 gap-3">
            <div>
              <p class="text-xs text-muted-foreground">Jornada</p>
              <p class="text-lg font-semibold tabular-nums">
                {{ hours ? formatHours(hours.worked) : "—" }}
              </p>
            </div>
            <div>
              <p class="text-xs text-muted-foreground">Horas extra</p>
              <p class="text-lg font-semibold tabular-nums">
                {{ hours && hours.overtime ? formatHours(hours.overtime) : "—" }}
              </p>
            </div>
            <div>
              <p class="text-xs text-muted-foreground">Costo del día</p>
              <p class="text-lg font-semibold tabular-nums">{{ formatCurrency(dayCost) }}</p>
            </div>
          </div>

          <p v-if="hours && hours.deducted" class="mt-3 text-xs text-muted-foreground">
            Se descontaron {{ formatHours(hours.deducted) }} de la jornada.
          </p>
        </div>

        <Separator />

        <div class="space-y-1.5">
          <p class="text-xs font-medium text-muted-foreground">Novedades</p>

          <div
            v-for="novelty in dayNovelties"
            :key="novelty.id"
            class="flex items-center justify-between gap-3 rounded-lg bg-muted/40 px-3 py-2"
          >
            <span class="flex min-w-0 items-center gap-2 text-sm">
              <span
                class="size-2 shrink-0 rounded-full"
                :style="{ backgroundColor: NOVELTY_COLOR[novelty.kind] }"
              />
              <span class="truncate">{{ novelty.label }}</span>
            </span>
            <span
              v-if="rangeLabel(novelty)"
              class="shrink-0 text-xs tabular-nums text-muted-foreground"
            >
              {{ rangeLabel(novelty) }}
            </span>
          </div>

          <p v-if="!dayNovelties.length" class="py-3 text-sm text-muted-foreground">
            Sin novedades este día.
          </p>
        </div>

        <div class="space-y-1.5">
          <p class="text-xs font-medium text-muted-foreground">Horas extra</p>

          <p
            v-for="marker in dayMarkers"
            :key="marker.id"
            class="rounded-lg bg-muted/40 px-3 py-2 text-sm"
          >
            {{ marker.label }}
          </p>

          <p v-if="!dayMarkers.length" class="py-3 text-sm text-muted-foreground">
            Sin horas extra.
          </p>
        </div>
      </div>
    </DialogContent>
  </Dialog>
</template>
