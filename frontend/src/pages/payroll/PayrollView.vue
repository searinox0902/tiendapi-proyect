<script setup lang="ts">
import { computed, reactive, ref } from "vue"
import { IconChevronLeft, IconChevronRight, IconSparkles } from "@tabler/icons-vue"
import { Moon, Sun } from "@lucide/vue"
import { toast } from "vue-sonner"

import AppSidebar from "@/components/AppSidebar.vue"
import ModuleNavSelect from "@/components/ModuleNavSelect.vue"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"
import { Switch } from "@/components/ui/switch"
import { isDark } from "@/composables/useTheme"

import CalendarMonthGrid from "./CalendarMonthGrid.vue"
import DayDetailDialog from "./DayDetailDialog.vue"
import EmployeeCombobox from "./EmployeeCombobox.vue"
import EmployeeDayDialog from "./EmployeeDayDialog.vue"
import NoveltyCaptureDialog from "./NoveltyCaptureDialog.vue"
import type { ICapturePayload } from "./NoveltyCaptureDialog.vue"
import type { IDayAction } from "./dayActions"
import type { IMarker, INovelty, NoveltyKind } from "./payroll.types"
import PayPeriodBar from "./PayPeriodBar.vue"
import { usePayrollCalendar } from "./usePayrollCalendar"
import {
  buildMockMarkers,
  buildMockNovelties,
  mockEmployees,
  mockHolidays2026,
} from "./payroll.mock"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { MARKER_LABEL, NOVELTY_LABEL } from "./dayActions"
import { PERIODICITY_LABELS, defaultPayrollConfig } from "./payroll.config"
import type { IPayrollPeriod, Periodicity } from "./payroll.types"

/**
 * Nómina — pantalla de aterrizaje del módulo (maqueta).
 *
 * Es un **calendario**, no una tabla, por una razón concreta: la tabla liquida
 * (dos veces al mes) pero el calendario informa (todos los días). Responde las
 * preguntas de entre-quincenas —cuántas vacaciones le quedan a alguien, quién
 * faltó, cuándo cierra el corte— que la tabla no responde, y es la única
 * pantalla del módulo que mira hacia adelante.
 *
 * Diseño completo y decisiones en `docs/13-modulo-nomina.md`. Las vistas
 * "Semana" y "Hoy" son componentes distintos —no zooms de este— y llegan
 * después; el tabulador aparecerá cuando exista la segunda, porque un
 * tabulador de una sola pestaña es ruido.
 */

/**
 * Config de pago. En el producto sale del wizard de arranque (§7.4); acá es
 * `reactive` y hay un selector en pantalla **solo para la maqueta**, porque
 * cambiar la periodicidad reordena por completo los cortes y hay que poder
 * verlo. Se retira cuando exista el wizard.
 */
const payrollConfig = reactive({ ...defaultPayrollConfig })

const periodicityOptions = Object.keys(PERIODICITY_LABELS) as Periodicity[]

function onPeriodicityChange(value: unknown) {
  if (typeof value !== "string") {
    return
  }
  payrollConfig.periodicity = value as Periodicity
  // Cortes de referencia por periodicidad: quincena en 1 y 16, mes el día 1.
  payrollConfig.cutDays = value === "semimonthly" ? [1, 16] : [1]
}

const {
  monthLabel,
  isCurrentMonth,
  calendarDays,
  teamDays,
  periods,
  daysUntilPeriodCloses,
  visibleNoveltyCount,
  selectedEmployeeId,
  hasSelection,
  goToPreviousMonth,
  goToNextMonth,
  goToToday,
} = usePayrollCalendar({
  employees: mockEmployees,
  holidays: mockHolidays2026,
  config: () => payrollConfig,
  closedDays: () => forcedNonWorking.value,
  // Solo el mes actual trae datos: navegar a otro mes muestra el estado vacío,
  // que es el 90% de los casos reales (D-99) y el más difícil de diseñar.
  noveltiesFor: (year, month) => (year === seedYear && month === seedMonth ? novelties.value : []),
  markersFor: (year, month) => (year === seedYear && month === seedMonth ? markers.value : []),
})

/**
 * ─── Estado local, a propósito ────────────────────────────────────────────
 *
 * No hay store de Pinia ni catálogo en tabla todavía, y es deliberado: primero
 * se quiere **sentir el flujo**. Definir la estructura de datos antes empuja a
 * dibujar la interfaz con la forma de la tabla, en vez de al revés.
 *
 * Esto es lo mínimo para que el calendario responda: se siembra del mock y
 * vive en el componente. Cuando el flujo esté validado se reemplaza por el
 * store (D-112) sin tocar las pantallas — el shape ya es el mismo.
 */
const seedNow = new Date()
const seedYear = seedNow.getFullYear()
const seedMonth = seedNow.getMonth() + 1

const novelties = ref<INovelty[]>(buildMockNovelties(seedYear, seedMonth))
const markers = ref<IMarker[]>(buildMockMarkers(seedYear, seedMonth))
/** Anotaciones libres por fecha ISO. No afectan el cálculo. */
const dayNotes = ref<Record<string, string[]>>({})
/** Días que el negocio cerró — propiedad del día, no de una persona. */
const forcedNonWorking = ref<Set<string>>(new Set())

let nextId = 1000

const employeeCount = computed(
  () => mockEmployees.filter((employee) => employee.workerType === "employee").length,
)
const contractors = computed(() =>
  mockEmployees.filter((employee) => employee.workerType === "contractor"),
)

/**
 * Leyenda. Con solo cuatro colores cabe en una línea; si algún día crecen los
 * tipos, el problema no es la leyenda sino que se rompió la regla de que solo
 * las novedades que **consumen días** van al calendario.
 */
const legend = [
  { label: "Ausencia", color: "var(--novelty-absence)", dashed: false },
  { label: "Incapacidad", color: "var(--novelty-sick-leave)", dashed: true },
  { label: "Vacaciones", color: "var(--novelty-vacation)", dashed: false },
  { label: "Permiso / licencia", color: "var(--novelty-leave)", dashed: false },
]

/** Mismos anillos que en la grilla, para que la leyenda se lea como muestra real. */
function legendStyle(item: (typeof legend)[number]) {
  if (item.dashed) {
    return {
      backgroundImage: `repeating-conic-gradient(${item.color} 0deg 14deg, var(--border) 14deg 24deg)`,
    }
  }
  return { backgroundImage: `conic-gradient(${item.color} 0deg 360deg)` }
}

/* ─── Detalle del día: la celda lee ─── */

/**
 * ─── Un solo diálogo montado a la vez ─────────────────────────────────────
 *
 * Los tres diálogos van en una sola cadena `v-if / v-else-if` sobre un único
 * `activeModal`: el que no está activo **no existe**, no está "cerrado
 * esperando". Abrir uno desde otro es asignar el nombre y ya — Vue desmonta
 * el anterior y monta el nuevo en el mismo parche, en ese orden, y cada uno
 * arranca desde cero con lo que le pasan por props.
 *
 * La cadena importa, no es estilo: tres `v-if` hermanos se parchean por
 * posición, y al pasar del segundo al primero Vue montaría el nuevo antes
 * de desmontar el viejo. Con una sola rama el orden es siempre viejo fuera,
 * nuevo dentro.
 *
 * Lo que esto reemplaza, y por qué. La versión anterior mantenía los tres
 * montados y alternaba su prop `open`, con un temporizador de 180 ms entre
 * cerrar uno y abrir el siguiente para que Reka soltara el `pointer-events:
 * none` del `body`, y una memoria (`captureReturnTo`) para volver al modal
 * de abajo al cerrar la captura. Funcionaba casi siempre, y "casi" es el
 * problema: la animación de salida dura 200 ms, así que había 20 ms con dos
 * diálogos vivos; y el modal que reaparecía solo por cerrar otro se leía
 * como un bug, no como una cortesía. Sin nada montado de más no hay carrera
 * que sincronizar, y sin memoria no hay estado que se desactualice.
 *
 * El costo: al cerrar no hay animación de salida, el diálogo se va de una.
 */
type ModalName = "none" | "day" | "employee" | "capture"

const activeModal = ref<ModalName>("none")

/**
 * Cierre pedido por el propio diálogo (Esc, la X, Cancelar, clic afuera).
 *
 * Se comprueba cuál está activo por si un diálogo avisa `false` mientras se
 * está desmontando porque ya se abrió otro: ese aviso no debe cerrar al nuevo.
 */
function closeModal(from: ModalName) {
  if (activeModal.value === from) {
    activeModal.value = "none"
  }
}

const detailDate = ref<string | null>(null)

function onOpenDay(date: string) {
  detailDate.value = date
  activeModal.value = "day"
}

/** Del equipo completo, no de la grilla filtrada: el detalle lista a todos (D-115). */
const detailDay = computed(
  () => teamDays.value.find((day) => day.date === detailDate.value) ?? null,
)
const detailNotes = computed(() =>
  detailDate.value ? (dayNotes.value[detailDate.value] ?? []) : [],
)

/* ─── Captura: el "..." actúa ─── */

const captureAction = ref<IDayAction | null>(null)
const captureDate = ref("")
const capturePreset = ref<string | null>(null)

function onDayAction(payload: { date: string; action: IDayAction }) {
  captureDate.value = payload.date
  captureAction.value = payload.action
  capturePreset.value = selectedEmployeeId.value
  activeModal.value = "capture"
}

/**
 * Desde el detalle de una persona: la captura **reemplaza** ese modal, no se
 * le pone encima. Al cerrarla se vuelve al calendario; quien quiera el
 * detalle otra vez lo abre otra vez.
 */
function onEmployeeAction(payload: { employeeId: string; action: IDayAction }) {
  captureDate.value = detailDate.value ?? ""
  captureAction.value = payload.action
  capturePreset.value = payload.employeeId
  activeModal.value = "capture"
}

/**
 * Crear, editar y quitar por el mismo camino.
 *
 * Editar es **quitar y volver a poner**: con un modelo de esta forma —alguien,
 * un día, un tipo, una cantidad— no hay nada que preservar del registro viejo,
 * y tratar la edición como un caso aparte solo duplicaría la lógica de armado.
 */
function onCaptureSave(payload: ICapturePayload) {
  const date = captureDate.value

  // Lo que existía se va, haya venido un reemplazo o no.
  if (payload.existingNoveltyId) {
    const id = payload.existingNoveltyId
    novelties.value = novelties.value.filter((novelty) => novelty.id !== id)
  }
  if (payload.existingMarkerId) {
    const id = payload.existingMarkerId
    markers.value = markers.value.filter((marker) => marker.id !== id)
  }

  if (!payload.selection) {
    toast("Novedad quitada", { description: "La persona queda como que laboró normal." })
    return
  }

  const { selection } = payload
  nextId += 1

  if (selection.type === "novelty" && payload.employeeId) {
    novelties.value = [
      ...novelties.value,
      {
        id: `n${nextId}`,
        employeeId: payload.employeeId,
        kind: selection.kind,
        start: date,
        // El rango sale del formulario: el inicio es el día de contexto y el
        // fin es libre hacia adelante.
        end: payload.endDate,
        span: payload.span,
        hours: payload.span === "hours" ? Number(payload.amount) || undefined : undefined,
        attachmentName: payload.attachmentName ?? undefined,
        label: labelFor(selection.kind, payload),
      },
    ]
  } else if (selection.type === "marker" && payload.employeeId) {
    markers.value = [
      ...markers.value,
      {
        id: `m${nextId}`,
        employeeId: payload.employeeId,
        kind: selection.kind,
        date,
        quantity: Number(payload.amount) || undefined,
        label: payload.amount
          ? `${MARKER_LABEL[selection.kind]}: ${payload.amount} h`
          : MARKER_LABEL[selection.kind],
      },
    ]
  } else if (selection.type === "day" && selection.kind === "note") {
    dayNotes.value = {
      ...dayNotes.value,
      [date]: [...(dayNotes.value[date] ?? []), payload.note || "Sin detalle"],
    }
  } else if (selection.type === "day" && selection.kind === "non_working") {
    forcedNonWorking.value = new Set(forcedNonWorking.value).add(date)
    if (payload.note) {
      dayNotes.value = {
        ...dayNotes.value,
        [date]: [...(dayNotes.value[date] ?? []), payload.note],
      }
    }
  }

  toast(payload.existingNoveltyId || payload.existingMarkerId ? "Actualizado" : "Listo", {
    description: "Se registró en el calendario.",
  })
}

/** "Permiso · 2 h" en vez de solo "Permiso": la duración va en el texto. */
function labelFor(kind: NoveltyKind, payload: ICapturePayload): string {
  const base = NOVELTY_LABEL[kind]
  if (payload.span === "half_day") {
    return `${base} · medio día`
  }
  if (payload.span === "hours" && payload.amount) {
    return `${base} · ${payload.amount} h`
  }
  return base
}

/* ─── La persona, entrando desde un día ─── */

const employeeDayId = ref<string | null>(null)
function onOpenEmployee(id: string) {
  employeeDayId.value = id
  activeModal.value = "employee"
}

/** "Volver al día" no restaura nada: abre el detalle del día de nuevo. */
function backToDay() {
  activeModal.value = "day"
}

const captureDayNovelties = computed(() =>
  novelties.value.filter(
    (novelty) => captureDate.value >= novelty.start && captureDate.value <= novelty.end,
  ),
)
const captureDayMarkers = computed(() =>
  markers.value.filter((marker) => marker.date === captureDate.value),
)

const employeeDay = computed(
  () => mockEmployees.find((employee) => employee.id === employeeDayId.value) ?? null,
)
const employeeNovelties = computed(() =>
  novelties.value.filter((novelty) => novelty.employeeId === employeeDayId.value),
)
const employeeMarkers = computed(() =>
  markers.value.filter((marker) => marker.employeeId === employeeDayId.value),
)

/* ─── Edición desde el calendario y el detalle ─── */

/**
 * Clic en un avatar del calendario: abre **esa** novedad para editarla.
 *
 * Antes llevaba al detalle del día, porque no existía un editor. Ahora que el
 * modal de novedad autocompleta con lo registrado, el gesto directo es el
 * correcto: se señaló una novedad concreta, se abre esa novedad.
 */
function onOpenNovelty(id: string) {
  const found = novelties.value.find((novelty) => novelty.id === id)
  if (!found) {
    return
  }
  captureDate.value = found.start
  captureAction.value = null
  capturePreset.value = found.employeeId
  activeModal.value = "capture"
}

function removeNovelty(id: string) {
  novelties.value = novelties.value.filter((novelty) => novelty.id !== id)
}

function removeNote(index: number) {
  const date = detailDate.value
  if (!date) {
    return
  }
  dayNotes.value = {
    ...dayNotes.value,
    [date]: (dayNotes.value[date] ?? []).filter((_, i) => i !== index),
  }
}

function restoreWorking() {
  const date = detailDate.value
  if (!date) {
    return
  }
  const next = new Set(forcedNonWorking.value)
  next.delete(date)
  forcedNonWorking.value = next
}

function onSettle(period: IPayrollPeriod) {
  toast(period.label, { description: "La tabla de liquidación llega después." })
}
</script>

<template>
  <SidebarProvider
    :style="{
      '--sidebar-width': 'calc(var(--spacing) * 72)',
      '--header-height': 'calc(var(--spacing) * 12)',
    }"
  >
    <AppSidebar variant="inset" />
    <SidebarInset class="min-w-0">
      <div class="min-w-0 space-y-5 px-6 pb-8">
        <header class="flex h-(--header-height) shrink-0 items-center gap-2 border-b">
          <div class="flex w-full items-center gap-1 px-4 lg:gap-2 lg:px-6">
            <SidebarTrigger class="-ml-1" />
            <Separator orientation="vertical" class="mx-2 data-[orientation=vertical]:h-4" />
            <ModuleNavSelect current="payroll" />
            <div class="ml-auto flex items-center gap-2">
              <Sun class="size-4 text-muted-foreground" />
              <Switch v-model="isDark" aria-label="Cambiar a tema oscuro" />
              <Moon class="size-4 text-muted-foreground" />
            </div>
          </div>
        </header>

        <!-- Navegación de mes + filtro de equipo -->
        <div class="flex flex-wrap items-center justify-between gap-4">
          <div class="flex items-center gap-1">
            <Button variant="ghost" size="icon" class="size-8" aria-label="Mes anterior" @click="goToPreviousMonth">
              <IconChevronLeft class="size-4" />
            </Button>
            <h2 class="min-w-44 text-center text-lg font-semibold">{{ monthLabel }}</h2>
            <Button variant="ghost" size="icon" class="size-8" aria-label="Mes siguiente" @click="goToNextMonth">
              <IconChevronRight class="size-4" />
            </Button>
            <Button
              v-if="!isCurrentMonth"
              variant="outline"
              size="sm"
              class="ml-2 h-8"
              @click="goToToday"
            >
              Hoy
            </Button>

            <!-- Andamiaje de maqueta: se va cuando exista el wizard (§7.4). -->
            <Select :model-value="payrollConfig.periodicity" @update:model-value="onPeriodicityChange">
              <SelectTrigger class="ml-3 h-8 w-36 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="option in periodicityOptions" :key="option" :value="option">
                  {{ PERIODICITY_LABELS[option] }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <!--
            Filtro del calendario. "Todos" es el valor de partida, y al elegir a
            una persona la línea deja de ser un agregado y pasa a hablar de ella:
            sus días laborados, sus días liquidados.
          -->
          <div class="w-64">
            <EmployeeCombobox v-model="selectedEmployeeId" :employees="mockEmployees" allow-all />
          </div>
        </div>

        <PayPeriodBar
          :periods="periods"
          :days-until-close="daysUntilPeriodCloses"
          :employee-count="employeeCount"
          :contractors="contractors"
          @settle="onSettle"
        />

        <!--
          Fila delgada sobre el calendario: a la izquierda el estado del mes, a
          la derecha la clave de color.

          Se eliminaron las notas instructivas del pie ("el arco es la duración",
          "la línea se corta entre periods"): si la pantalla necesita un manual
          debajo, el problema es la pantalla. Lo único que queda es la clave de
          color, que no es una instrucción sino un diccionario — y va arriba,
          donde se consulta antes de mirar, no después.
        -->
        <div class="flex flex-wrap items-center justify-between gap-x-6 gap-y-2">
          <!--
            Estado vacío **anticipatorio**, no confirmatorio. Un calendario
            limpio puede leerse como "no cargó"; esta línea lo convierte en "el
            mes va normal". No confundir con el estado cero (negocio recién
            instalado, sin empleados), que es otra pantalla: ahí no corresponde
            un calendario sino una invitación a agregar gente.
          -->
          <p
            v-if="visibleNoveltyCount === 0"
            class="flex items-center gap-2 text-sm text-muted-foreground"
          >
            <IconSparkles class="size-4 shrink-0 text-brand-icon" />
            <span v-if="hasSelection">
              Sin novedades de esta persona en {{ monthLabel.toLowerCase() }}.
            </span>
            <span v-else>
              Sin novedades en {{ monthLabel.toLowerCase() }} — el equipo trabajó normal.
            </span>
          </p>
          <span v-else />

          <div class="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted-foreground">
            <span v-for="item in legend" :key="item.label" class="flex items-center gap-1.5">
              <span class="rounded-full p-[2px]" :style="legendStyle(item)">
                <span class="block size-2.5 rounded-full bg-background" />
              </span>
              {{ item.label }}
            </span>
            <span class="flex items-center gap-1.5">
              <span class="size-1.5 rounded-full bg-novelty-marker" />
              Hora extra
            </span>

            <!--
              Los tres estados del corte. No es una instrucción sino un
              diccionario de color, igual que los anillos: dice qué significa
              cada tono, no cómo usar la pantalla.
            -->
            <span class="flex items-center gap-1.5 border-l border-border pl-4">
              <span class="h-1.5 w-6 bg-period-line-settled" />
              Liquidado
            </span>
            <span class="flex items-center gap-1.5">
              <span class="h-1.5 w-6 bg-period-line-worked" />
              Laborado
            </span>
          </div>
        </div>

        <CalendarMonthGrid
          :days="calendarDays"
          @open-day="onOpenDay"
          @day-action="onDayAction"
          @open-novelty="onOpenNovelty"
        />

        <!--
          Una sola cadena v-if/v-else-if y no `:open`: el diálogo inactivo no
          está cerrado, no existe. Ver "un solo diálogo montado a la vez".
        -->
        <DayDetailDialog
          v-if="activeModal === 'day'"
          open
          @update:open="$event || closeModal('day')"
          :day="detailDay"
          :employees="mockEmployees"
          :notes="detailNotes"
          :is-forced-non-working="detailDate ? forcedNonWorking.has(detailDate) : false"
          :hours-per-day="payrollConfig.hoursPerDay"
          @remove-novelty="removeNovelty"
          @remove-note="removeNote"
          @restore-working="restoreWorking"
          @open-employee="onOpenEmployee"
        />

        <EmployeeDayDialog
          v-else-if="activeModal === 'employee'"
          open
          @update:open="$event || closeModal('employee')"
          :employee="employeeDay"
          :day="detailDay"
          :novelties="employeeNovelties"
          :markers="employeeMarkers"
          :hours-per-day="payrollConfig.hoursPerDay"
          @back="backToDay"
          @action="onEmployeeAction"
        />

        <NoveltyCaptureDialog
          v-else-if="activeModal === 'capture'"
          open
          :action="captureAction"
          :date="captureDate"
          :employees="mockEmployees"
          :preset-employee-id="capturePreset"
          :day-novelties="captureDayNovelties"
          :day-markers="captureDayMarkers"
          @update:open="$event || closeModal('capture')"
          @save="onCaptureSave"
        />
      </div>
    </SidebarInset>
  </SidebarProvider>
</template>
