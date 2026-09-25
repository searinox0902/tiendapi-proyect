<script setup lang="ts">
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import DayActionsPopover from "./DayActionsPopover.vue"
import { NOVELTY_COLOR } from "./dayActions"
import type { IDayAction } from "./dayActions"
import { MONTH_NAMES, WEEKDAY_LABELS } from "./usePayrollCalendar"
import type { ICalendarDay, IDayNovelty, NoveltySpan } from "./payroll.types"

/**
 * Grilla del mes. Tres canales visuales que nunca se pisan (docs/13, §7):
 *
 *   fondo de la celda → qué tipo de día es (hábil / no laborable / festivo)
 *   avatares          → a quién le pasó algo ese día
 *   línea inferior    → continuidad del corte y del trabajo
 *
 * **La línea es la pieza central.** Corre por debajo de los días y se rompe en
 * dos sitios: donde nadie laboró y en la **frontera entre periods**. Por eso no
 * hace falta ninguna etiqueta "Corte 1 / Corte 2": los dos tramos continuos de
 * línea *son* los dos cortes. Y su intensidad dice cuánta gente trabajó —
 * sólida es el equipo completo, sin línea es nadie.
 *
 * Nada de eso se registra: se **deduce** de las novedades de ausencia (D-99).
 * La línea es literalmente la fórmula `días del período − ausencias` dibujada.
 */

defineProps<{
  days: ICalendarDay[]
}>()

const emit = defineEmits<{
  /** Clic en la celda → abre el detalle del día. La celda **lee**. */
  "open-day": [date: string]
  /** Una acción del "..." → abre la captura. El botón **actúa**. */
  "day-action": [payload: { date: string; action: IDayAction }]
  /** Clic en un avatar → esa novedad concreta, no una nueva. */
  "open-novelty": [id: string]
}>()

/** Se muestran 5 y el resto colapsa en un "+N" que revela los nombres al pasar. */
const MAX_VISIBLE_AVATARS = 5

/** Fracción del día que ocupa la novedad — se dibuja como arco del anillo. */
const SPAN_FRACTION: Record<NoveltySpan, number> = {
  full_day: 1,
  half_day: 0.5,
  hours: 0.25,
}

/**
 * El tipo de novedad viaja en el **anillo** del avatar: una sola marca dice
 * quién y qué. Y el anillo no siempre da la vuelta completa — el arco es la
 * duración, así que un permiso de 2 horas se ve como un cuarto de anillo y un
 * día completo como el círculo entero. La misma idea de "la cantidad de tinta
 * es la cantidad de tiempo", ahora en el borde en vez de en una franja.
 *
 * La incapacidad lleva anillo **punteado** además del color, porque el color
 * nunca puede ser el único canal (docs/09 §5).
 */
function avatarRingStyle(item: IDayNovelty) {
  const color = NOVELTY_COLOR[item.novelty.kind]

  if (item.novelty.kind === "sick_leave") {
    return {
      backgroundImage: `repeating-conic-gradient(${color} 0deg 14deg, var(--border) 14deg 24deg)`,
    }
  }

  const degrees = SPAN_FRACTION[item.novelty.span] * 360
  return {
    backgroundImage: `conic-gradient(${color} 0deg ${degrees}deg, var(--border) ${degrees}deg 360deg)`,
  }
}

/**
 * Rango de una novedad de varios días, para el hover.
 *
 * Es la única información del calendario que **no se puede obtener mirando**:
 * parado sobre el miércoles 13 no hay forma de saber que esas vacaciones van
 * del 11 al 15 sin recorrer las celdas con el ojo. El resto del tooltip
 * confirma lo que ya se ve; esto agrega algo.
 */
function rangeLabel(item: IDayNovelty): string | null {
  const { start, end } = item.novelty
  if (start === end) {
    return null
  }
  const [, startMonth, startDay] = start.split("-").map(Number)
  const [, endMonth, endDay] = end.split("-").map(Number)
  const from = `${startDay} de ${MONTH_NAMES[startMonth - 1].toLowerCase()}`
  const to = `${endDay} de ${MONTH_NAMES[endMonth - 1].toLowerCase()}`
  return `Del ${from} al ${to}`
}

function cellBackground(day: ICalendarDay): string {
  if (!day.inMonth) {
    return "bg-transparent"
  }
  if (day.holiday) {
    return "bg-day-holiday"
  }
  if (day.isSunday || !day.isWorkingDay) {
    // Un día cerrado se lee igual que un domingo: el negocio no abrió, y el
    // motivo lo cuenta el detalle del día, no el color.
    return "bg-day-nonworking"
  }
  return "bg-day-working"
}

/**
 * La línea es **binaria y siempre completa**: el día se laboró o no se laboró.
 *
 * Antes se atenuaba según cuánta gente trabajó, y estaba mal: eso duplicaba en
 * la línea una información que ya cuentan los avatares, y dejaba días a medio
 * pintar que no significan nada — si uno de seis está de vacaciones, el negocio
 * abrió igual. Cada canal dice una cosa sola: la línea dice *si hubo jornada*,
 * los avatares dicen *a quién le pasó algo*.
 *
 * Las diagonales tipo poste de barbería le dan **dirección**: la línea deja de
 * ser un subrayado y se lee como algo que avanza de un día al siguiente — el
 * period corriendo hacia su cierre.
 */
function lineStyle(day: ICalendarDay) {
  return {
    left: day.periodStart ? "5px" : "0",
    right: day.periodEnd ? "5px" : "0",
    backgroundColor: lineColor(day),
    backgroundImage:
      "repeating-linear-gradient(45deg, transparent 0 4px, color-mix(in oklch, var(--background) 48%, transparent) 4px 7px)",
  }
}

/**
 * Tres estados, y ahora la pregunta que responden es **"¿este día ya se
 * liquidó?"** — no "¿en qué corte cae?".
 *
 *   primario    · liquidado
 *   gris medio  · laborable, ya ocurrido
 *   gris claro  · laborable, todavía por venir
 *
 * El orden importa: lo liquidado manda, porque un día pagado es un hecho
 * cerrado. Después el futuro, que no puede afirmar que se laboró. Y el resto
 * es el día normal.
 *
 * La agregación de "liquidado" —todos los implicados o ninguno— vive en el
 * composable, no acá: la pinta es una consecuencia del dato, y reconstruir la
 * regla en el componente sería tenerla escrita en dos sitios.
 */
function lineColor(day: ICalendarDay): string {
  /*
    Mirando a una persona, su novedad manda sobre el estado de pago: la línea
    cuenta qué le pasó ese día, y el color es el mismo del anillo del avatar y
    de la leyenda — vocabulario que el usuario ya tiene. En la vista de todos
    `focusNovelty` es `null` y esta rama no aplica.
  */
  if (day.focusNovelty) {
    return NOVELTY_COLOR[day.focusNovelty.novelty.kind]
  }
  if (day.isSettled) {
    return "var(--period-line-settled)"
  }
  if (day.isFuture) {
    return "var(--period-line-upcoming)"
  }
  return "var(--period-line-worked)"
}
</script>

<template>
  <div class="overflow-hidden rounded-xl border border-border">
    <!-- Encabezado de días: lunes primero, convención colombiana. -->
    <div class="grid grid-cols-7 border-b border-border bg-muted/40">
      <div
        v-for="label in WEEKDAY_LABELS"
        :key="label"
        class="px-2 py-2 text-center text-xs font-medium text-muted-foreground"
      >
        {{ label }}
      </div>
    </div>

    <TooltipProvider :delay-duration="150">
      <div class="grid grid-cols-7">
        <div
          v-for="day in days"
          :key="day.date"
          class="group relative min-h-24 border-b border-r border-border p-1.5"
          :class="[
            day.inMonth ? 'cursor-pointer' : '',
            cellBackground(day),
            day.isToday ? 'ring-1 ring-inset ring-primary/35' : '',
          ]"
          @click="day.inMonth && emit('open-day', day.date)"
        >
          <!-- Cabecera: número del día + chips de hoy / festivo -->
          <div class="flex items-start justify-between gap-1">
            <!--
              El número de hoy va en negrilla, sin el círculo primario que tenía
              antes: con el chip "Hoy" al lado, el círculo era una segunda marca
              diciendo lo mismo — y el primario ya está ocupado por la línea de
              period. Una señal fuerte por día, no dos.
            -->
            <span
              class="inline-flex size-6 items-center justify-center text-xs tabular-nums"
              :class="[
                day.isToday ? 'font-bold text-foreground' : '',
                day.inMonth ? 'text-foreground' : 'text-muted-foreground/40',
              ]"
            >
              {{ day.dayOfMonth }}
            </span>

            <div class="flex shrink-0 items-center gap-1">
              <!--
                El "..." reemplaza a los chips mientras el cursor está encima:
                es el único sitio de la celda donde un botón no le quita espacio
                a algo que se esté leyendo en ese momento.
              -->
              <DayActionsPopover
                v-if="day.inMonth"
                :date="day.date"
                @select="emit('day-action', { date: day.date, action: $event })"
              />

              <span
                v-if="day.isToday"
                class="group-hover:hidden"
                :class="'rounded bg-primary px-1.5 py-0.5 text-[10px] font-semibold text-primary-foreground'"
              >
                Hoy
              </span>

              <!--
                Festivo: por ahora se trata como día no laborable + chip, en vez
                de un color propio. Punto abierto de diseño — ver docs/13.
              -->
              <Tooltip v-if="day.holiday">
                <TooltipTrigger as-child>
                  <span
                    class="rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground group-hover:hidden"
                  >
                    Festivo
                  </span>
                </TooltipTrigger>
                <TooltipContent>
                  <p class="text-xs">{{ day.holiday.name }}</p>
                </TooltipContent>
              </Tooltip>
            </div>
          </div>

          <!-- Avatares: quién tiene novedad ese día, apoyados sobre la línea -->
          <div class="mt-2 flex flex-wrap items-center gap-0.5 pb-2.5">
            <Tooltip
              v-for="item in day.novelties.slice(0, MAX_VISIBLE_AVATARS)"
              :key="item.novelty.id"
            >
              <TooltipTrigger as-child>
                <span
                  class="block cursor-pointer rounded-full p-[2px]"
                  :style="avatarRingStyle(item)"
                  @click.stop="emit('open-novelty', item.novelty.id)"
                >
                  <Avatar class="size-5 bg-background">
                    <AvatarFallback class="bg-muted text-[9px] font-medium">
                      {{ item.employee.initials }}
                    </AvatarFallback>
                  </Avatar>
                </span>
              </TooltipTrigger>
              <TooltipContent>
                <p class="font-medium">{{ item.employee.name }}</p>
                <!--
                  El punto repite el color del anillo que se acaba de señalar:
                  ata el tooltip a lo que el cursor está tocando, que con cinco
                  avatares juntos deja de ser obvio.
                -->
                <p class="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <span
                    class="size-1.5 shrink-0 rounded-full"
                    :style="{ backgroundColor: NOVELTY_COLOR[item.novelty.kind] }"
                  />
                  {{ item.novelty.label }}
                </p>
                <p v-if="rangeLabel(item)" class="text-xs text-muted-foreground/80">
                  {{ rangeLabel(item) }}
                </p>
              </TooltipContent>
            </Tooltip>

            <!-- El "+N" también revela nombres: si no, esconde justo lo que se busca. -->
            <Tooltip v-if="day.novelties.length > MAX_VISIBLE_AVATARS">
              <TooltipTrigger as-child>
                <span
                  class="inline-flex size-5 cursor-default items-center justify-center rounded-full bg-muted text-[10px] font-medium text-muted-foreground"
                >
                  +{{ day.novelties.length - MAX_VISIBLE_AVATARS }}
                </span>
              </TooltipTrigger>
              <TooltipContent>
                <p
                  v-for="item in day.novelties.slice(MAX_VISIBLE_AVATARS)"
                  :key="item.novelty.id"
                  class="text-xs"
                >
                  <span class="font-medium">{{ item.employee.name }}</span>
                  <span class="text-muted-foreground"> · {{ item.novelty.label }}</span>
                </p>
              </TooltipContent>
            </Tooltip>
          </div>

          <!--
            Marcadores (horas extra): no consumen el día, solo lo anotan.
            Punto discreto, nunca compitiendo con los avatares.
          -->
          <div v-if="day.markers.length" class="absolute bottom-2.5 right-1.5 flex gap-1">
            <Tooltip v-for="marker in day.markers" :key="marker.id">
              <TooltipTrigger as-child>
                <span class="block size-1.5 rounded-full bg-novelty-marker" />
              </TooltipTrigger>
              <TooltipContent>
                <p class="text-xs">{{ marker.label }}</p>
              </TooltipContent>
            </Tooltip>
          </div>

          <!--
            Frontera de corte: barra vertical propia (no un `border`), para que
            se lea como una división del mes y no como una línea de la grilla.
          -->
          <span
            v-if="day.periodStart"
            class="pointer-events-none absolute inset-y-0 left-0 w-[3px] bg-primary"
          />

          <!--
            La línea de continuidad. Ocupa el día completo salvo un respiro de
            5px justo en la frontera del corte: no alcanza a leerse como día a
            medio pintar, pero basta para que los dos tramos **no se toquen** y
            la división salte a la vista.
          -->
          <span
            v-if="day.isWorkingDay && (day.workedRatio > 0 || day.focusNovelty)"
            class="pointer-events-none absolute bottom-0 h-1.5"
            :style="lineStyle(day)"
          />

        </div>
      </div>
    </TooltipProvider>
  </div>
</template>
