<script setup lang="ts">
import { computed } from "vue"
import { IconCalendarOff, IconFileText, IconTrash } from "@tabler/icons-vue"

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
import RosterSearchInput from "./RosterSearchInput.vue"
import { useRosterSearch } from "./useRosterSearch"
import { formatHours, hoursForEmployee } from "./dayHours"
import { NOVELTY_CHIP, NOVELTY_COLOR } from "./dayActions"
import { MONTH_NAMES, WEEKDAY_LABELS } from "./usePayrollCalendar"
import type { ICalendarDay, IEmployee, INovelty } from "./payroll.types"

/**
 * Detalle de un día. Es el lugar que faltaba: con cinco avatares y un "+N", un
 * día cargado **no se puede leer desde la celda**, y el tooltip del "+N" era un
 * parche.
 *
 * Acá sí se lista **a todo el equipo**, no solo las excepciones. En la grilla
 * eso se descartó por habituación —treinta celdas iguales apagan el ojo y una
 * novedad deja de saltar—, pero este panel se abre a propósito: es opt-in, no
 * ambiental. La regla queda coherente: **la grilla muestra excepciones, el
 * detalle muestra todo.**
 */

const props = defineProps<{
  open: boolean
  day: ICalendarDay | null
  employees: IEmployee[]
  notes: string[]
  isForcedNonWorking: boolean
  hoursPerDay: number
}>()

const emit = defineEmits<{
  "update:open": [value: boolean]
  "remove-novelty": [id: string]
  "remove-note": [index: number]
  "restore-working": []
  "open-employee": [id: string]
}>()

interface IStateChip {
  label: string
  /** `null` = chip neutro (laboró, día no laborable). */
  color: string | null
}

/**
 * El estado de una persona ese día, como chip.
 *
 * El color es el **mismo de la leyenda del calendario**: el usuario ya aprendió
 * esos cuatro tonos mirando la grilla, así que el chip no le enseña un
 * vocabulario nuevo, le confirma el que ya tiene. Los dos estados que no son
 * novedad —laboró y día no laborable— van neutros, porque no son excepciones.
 *
 * "Parcial" sale del `span`: un permiso de dos horas no es lo mismo que uno de
 * día completo, y en la grilla eso ya se ve como arco incompleto del anillo.
 */
function stateChip(employeeId: string): IStateChip {
  if (nonWorkingReason.value) {
    return { label: "Día no laborable", color: null }
  }
  const novelty = noveltyByEmployee.value.get(employeeId)
  if (!novelty) {
    return { label: "Laboró", color: null }
  }
  const partial = novelty.span !== "full_day"
  return {
    label: partial ? `${NOVELTY_CHIP[novelty.kind]} parcial` : NOVELTY_CHIP[novelty.kind],
    color: NOVELTY_COLOR[novelty.kind],
  }
}

const title = computed(() => {
  if (!props.day) {
    return ""
  }
  const [year, month, dayNumber] = props.day.date.split("-").map(Number)
  const weekday = WEEKDAY_LABELS[(new Date(year, month - 1, dayNumber).getDay() + 6) % 7]
  return `${weekday} ${dayNumber} de ${MONTH_NAMES[month - 1]?.toLowerCase()}`
})

/** Por qué el día no es laborable — el usuario merece el motivo, no solo el hecho. */
const nonWorkingReason = computed(() => {
  if (!props.day) {
    return null
  }
  if (props.isForcedNonWorking) {
    return "Marcado como no laborable"
  }
  if (props.day.holiday) {
    return `Festivo · ${props.day.holiday.name}`
  }
  if (props.day.isSunday) {
    return "Domingo"
  }
  return null
})

const noveltyByEmployee = computed(() => {
  const map = new Map<string, INovelty>()
  props.day?.novelties.forEach((item) => map.set(item.novelty.employeeId, item.novelty))
  return map
})

/**
 * Todo el equipo, con los que tuvieron novedad arriba: lo excepcional primero,
 * que es lo que la persona vino a mirar.
 */
const roster = computed(() => {
  const withNovelty = props.employees.filter((e) => noveltyByEmployee.value.has(e.id))
  const rest = props.employees.filter((e) => !noveltyByEmployee.value.has(e.id))
  return [...withNovelty, ...rest]
})

const {
  query: search,
  results: visibleRoster,
  isFiltering,
  isEmpty,
  total: rosterTotal,
} = useRosterSearch(roster, () => [props.open, props.day?.date])

const workedCount = computed(
  () =>
    props.employees.filter(
      (employee) => employee.workerType === "employee" && !noveltyByEmployee.value.has(employee.id),
    ).length,
)

/**
 * Costo del día: suma de quienes efectivamente trabajaron.
 *
 * **No es una liquidación** y no pretende serlo. Deja fuera a quien tiene
 * cualquier novedad, cuando la realidad legal es más fina — las vacaciones se
 * pagan, la incapacidad se paga al 66,67% desde el tercer día, un permiso
 * remunerado se paga y uno no remunerado no. Todo eso es el motor legal, que
 * por D-113 todavía no existe: el módulo está en modo simple.
 *
 * Se muestra igual porque dimensiona el impacto de una novedad, que es lo que
 * el dueño quiere ver al abrir un día. La etiqueta dice "referencial" para que
 * nadie lo confunda con lo que hay que pagar.
 */
/** Horas de una persona ese día. Buena fe: jornada completa salvo novedad. */
function hoursOf(employeeId: string) {
  if (!props.day) {
    return null
  }
  return hoursForEmployee(
    props.day,
    employeeId,
    noveltyByEmployee.value.get(employeeId),
    props.hoursPerDay,
  )
}

/** Horas de jornada del día, sumando a todo el equipo. Las extra van aparte. */
const dayHours = computed(() => {
  if (!props.day) {
    return { worked: 0, overtime: 0 }
  }
  return props.employees
    .filter((employee) => employee.workerType === "employee")
    .reduce(
      (total, employee) => {
        const hours = hoursOf(employee.id)
        return {
          worked: total.worked + (hours?.worked ?? 0),
          overtime: total.overtime + (hours?.overtime ?? 0),
        }
      },
      { worked: 0, overtime: 0 },
    )
})

const dayCost = computed(() =>
  props.employees
    .filter(
      (employee) => employee.workerType === "employee" && !noveltyByEmployee.value.has(employee.id),
    )
    .reduce((total, employee) => total + employee.dailyCost, 0),
)
</script>

<template>
  <Dialog :open="open" @update:open="emit('update:open', $event)">
    <DialogContent v-if="day" class="max-h-[88vh] sm:max-w-3xl">
      <DialogHeader>
        <DialogTitle class="capitalize">{{ title }}</DialogTitle>
        <DialogDescription>
          <template v-if="nonWorkingReason">{{ nonWorkingReason }}</template>
          <template v-else>{{ workedCount }} personas laboraron</template>
        </DialogDescription>
      </DialogHeader>

      <div class="space-y-4">
        <!-- Día no laborable forzado: se puede revertir desde acá -->
        <div
          v-if="isForcedNonWorking"
          class="flex items-center justify-between gap-2 rounded-lg border border-border px-3 py-2"
        >
          <p class="flex items-center gap-2 text-sm text-muted-foreground">
            <IconCalendarOff class="size-4 shrink-0" />
            El negocio no abrió este día
          </p>
          <Button variant="ghost" size="sm" @click="emit('restore-working')">
            Deshacer
          </Button>
        </div>

        <!-- Anotaciones del día -->
        <div v-if="notes.length" class="space-y-1.5">
          <p class="text-xs font-medium text-muted-foreground">Anotaciones</p>
          <div
            v-for="(note, index) in notes"
            :key="index"
            class="group/note flex items-start justify-between gap-2 rounded-lg bg-muted/50 px-3 py-2"
          >
            <p class="flex items-start gap-2 text-sm">
              <IconFileText class="mt-0.5 size-3.5 shrink-0 text-muted-foreground" />
              {{ note }}
            </p>
            <button
              type="button"
              class="shrink-0 text-muted-foreground opacity-0 transition group-hover/note:opacity-100 hover:text-destructive"
              aria-label="Eliminar anotación"
              @click="emit('remove-note', index)"
            >
              <IconTrash class="size-3.5" />
            </button>
          </div>
        </div>

        <Separator v-if="notes.length || isForcedNonWorking" />

        <!-- El equipo completo -->
        <div class="space-y-2">
          <RosterSearchInput
            v-model="search"
            label="Equipo"
            :shown="visibleRoster.length"
            :total="rosterTotal"
            :is-filtering="isFiltering"
          />

          <!--
            El scroll vive **solo en la lista**, no en todo el contenido: así el
            costo del día y las anotaciones no se van hacia arriba al recorrer un
            equipo de cuarenta personas. Lo que se busca queda quieto.
          -->
          <div class="max-h-[26rem] min-h-[14rem] space-y-1 overflow-y-auto pr-1">
          <div
            v-for="employee in visibleRoster"
            :key="employee.id"
            class="group/row flex items-center justify-between gap-3 rounded-lg px-1 py-1.5"
          >
            <!-- Nombre y avatar abren a la persona: el resto de la fila no,
                 para que borrar una novedad no se confunda con navegar.
                 Sin realce en hover — el cursor basta como señal. -->
            <button
              type="button"
              class="flex min-w-0 cursor-pointer items-center gap-2.5 py-0.5 pr-2 text-left"
              @click="emit('open-employee', employee.id)"
            >
              <Avatar class="size-7 shrink-0">
                <AvatarFallback class="bg-muted text-[10px] font-medium">
                  {{ employee.initials }}
                </AvatarFallback>
              </Avatar>
              <span class="min-w-0">
                <span class="block truncate text-sm font-medium">{{ employee.name }}</span>
                <span class="block truncate text-xs text-muted-foreground">{{ employee.role }}</span>
              </span>
            </button>

            <div class="flex shrink-0 items-center gap-2">
              <!-- Costo diario: la cifra a la izquierda del estado, tabular
                   para que las columnas se alineen al leer la lista. -->
              <span
                v-if="employee.workerType === 'employee' && hoursOf(employee.id)"
                class="text-xs tabular-nums text-muted-foreground"
              >
                {{ formatHours(hoursOf(employee.id)!.worked) }}
                <template v-if="hoursOf(employee.id)!.overtime">
                  + {{ formatHours(hoursOf(employee.id)!.overtime) }}
                </template>
              </span>

              <span class="text-xs tabular-nums text-muted-foreground">
                {{ formatCurrency(employee.dailyCost) }}
              </span>

              <span
                v-if="employee.workerType === 'contractor'"
                class="rounded-full border border-border px-2 py-0.5 text-[11px] text-muted-foreground"
              >
                Prestación de servicios
              </span>

              <template v-else>
                <span
                  class="rounded-full px-2 py-0.5 text-[11px] font-medium"
                  :style="
                    stateChip(employee.id).color
                      ? {
                          backgroundColor: `color-mix(in oklch, ${stateChip(employee.id).color} 18%, transparent)`,
                          color: stateChip(employee.id).color!,
                        }
                      : undefined
                  "
                  :class="stateChip(employee.id).color ? '' : 'bg-muted text-muted-foreground'"
                >
                  {{ stateChip(employee.id).label }}
                </span>

                <button
                  v-if="noveltyByEmployee.get(employee.id)"
                  type="button"
                  class="text-muted-foreground opacity-0 transition group-hover/row:opacity-100 hover:text-destructive"
                  aria-label="Eliminar novedad"
                  @click="emit('remove-novelty', noveltyByEmployee.get(employee.id)!.id)"
                >
                  <IconTrash class="size-3.5" />
                </button>
              </template>
            </div>
          </div>

            <p v-if="isEmpty" class="py-6 text-center text-sm text-muted-foreground">
              Nadie coincide con "{{ search }}"
            </p>
          </div>
        </div>

        <Separator />

        <div class="flex items-baseline justify-between gap-2">
          <div>
            <p class="text-sm font-medium">Costo del día</p>
            <p class="text-[11px] text-muted-foreground">
              Referencial — sin reglas de ley todavía
            </p>
          </div>
          <div class="text-right">
            <p class="text-lg font-semibold tabular-nums">{{ formatCurrency(dayCost) }}</p>
            <p class="text-[11px] tabular-nums text-muted-foreground">
              {{ formatHours(dayHours.worked) }} de jornada<template v-if="dayHours.overtime">
                · {{ formatHours(dayHours.overtime) }} extra</template>
            </p>
          </div>
        </div>

        <!-- Marcadores: solo horas extra (D-121) -->
        <template v-if="day.markers.length">
          <Separator />
          <div class="space-y-1">
            <p class="text-xs font-medium text-muted-foreground">Horas extra</p>
            <p v-for="marker in day.markers" :key="marker.id" class="text-sm">
              {{ marker.label }}
            </p>
          </div>
        </template>
      </div>
    </DialogContent>
  </Dialog>
</template>
