import { computed, ref } from "vue"

import { periodsTouchingMonth } from "./payroll.config"
import type {
  ICalendarDay,
  IDayNovelty,
  IEmployee,
  IHoliday,
  IMarker,
  INovelty,
  IPayrollConfig,
} from "./payroll.types"

/**
 * Lógica de la grilla del mes.
 *
 * **Por qué no hay librería de calendario acá:** las tres vistas del módulo
 * (mes, semana, hoy) no son calendarios de eventos — son grillas donde nosotros
 * controlamos el 100% del contenido de cada celda (franjas, marcadores, bordes
 * de corte). Una librería completa aporta lo que no necesitamos (rejilla
 * horaria, posicionamiento automático, arrastre) y estorba justo donde
 * necesitamos libertad. Y las dos grandes —FullCalendar y schedule-x v4—
 * dejaron la vista de recursos y el drag-and-drop detrás de licencia paga.
 *
 * La aritmética de fechas se hace con tuplas `{y, m, d}` y strings ISO, nunca
 * con objetos `Date` (salvo para el día de la semana), para no arrastrar zonas
 * horarias en una app local-first. Al conectar backend conviene migrar a
 * `@internationalized/date`, que ya es dependencia del proyecto.
 */

function pad(value: number): string {
  return String(value).padStart(2, "0")
}

export function isoOf(year: number, month: number, day: number): string {
  return `${year}-${pad(month)}-${pad(day)}`
}

function daysInMonth(year: number, month: number): number {
  return new Date(year, month, 0).getDate()
}

/** Día de la semana con **lunes = 0** (convención colombiana, no domingo). */
function weekdayMondayFirst(year: number, month: number, day: number): number {
  return (new Date(year, month - 1, day).getDay() + 6) % 7
}

function isSundayDate(year: number, month: number, day: number): boolean {
  return new Date(year, month - 1, day).getDay() === 0
}

/** Diferencia en días entre dos fechas ISO (b − a). */
export function daysBetween(a: string, b: string): number {
  const [ay, am, ad] = a.split("-").map(Number)
  const [by, bm, bd] = b.split("-").map(Number)
  const msPerDay = 86_400_000
  // Mediodía UTC evita que un cambio de horario mueva el resultado un día.
  const start = Date.UTC(ay, am - 1, ad, 12)
  const end = Date.UTC(by, bm - 1, bd, 12)
  return Math.round((end - start) / msPerDay)
}

export const MONTH_NAMES = [
  "Enero",
  "Febrero",
  "Marzo",
  "Abril",
  "Mayo",
  "Junio",
  "Julio",
  "Agosto",
  "Septiembre",
  "Octubre",
  "Noviembre",
  "Diciembre",
]

export const WEEKDAY_LABELS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

interface IUsePayrollCalendarOptions {
  employees: IEmployee[]
  holidays: IHoliday[]
  /** Reactiva: cambiar la periodicidad recalcula los cortes sin recrear nada. */
  config: () => IPayrollConfig
  /**
   * Días que el negocio cerró — inventario, fiesta del pueblo, se dañó la
   * máquina. Es propiedad **del día** y afecta a todos, así que no puede
   * modelarse como una novedad por persona. Se suma a domingos y festivos para
   * decidir si el día fue laborable.
   */
  closedDays?: () => Set<string>
  /** Novedades y marcadores del mes que se está viendo. */
  noveltiesFor: (year: number, month: number) => INovelty[]
  markersFor: (year: number, month: number) => IMarker[]
}

export function usePayrollCalendar(options: IUsePayrollCalendarOptions) {
  const now = new Date()
  const todayIso = isoOf(now.getFullYear(), now.getMonth() + 1, now.getDate())

  const year = ref(now.getFullYear())
  const month = ref(now.getMonth() + 1)

  /**
   * Filtro del calendario. `null` = todos.
   *
   * Pasó de selección múltiple a única al cambiar la barra de avatares por un
   * selector: con "Todos" como opción de la misma lista, elegir a varios deja
   * de tener una forma clara de expresarse — y en la práctica nadie comparaba
   * a tres personas a la vez, se enfocaba en una.
   */
  const selectedEmployeeId = ref<string | null>(null)

  function selectEmployee(id: string | null) {
    selectedEmployeeId.value = id
  }

  const hasSelection = computed(() => selectedEmployeeId.value !== null)

  function isSelected(id: string): boolean {
    return selectedEmployeeId.value === id
  }

  function goToPreviousMonth() {
    if (month.value === 1) {
      month.value = 12
      year.value -= 1
    } else {
      month.value -= 1
    }
  }

  function goToNextMonth() {
    if (month.value === 12) {
      month.value = 1
      year.value += 1
    } else {
      month.value += 1
    }
  }

  function goToToday() {
    year.value = now.getFullYear()
    month.value = now.getMonth() + 1
  }

  const isCurrentMonth = computed(
    () => year.value === now.getFullYear() && month.value === now.getMonth() + 1,
  )

  const monthLabel = computed(() => `${MONTH_NAMES[month.value - 1]} ${year.value}`)

  const employeeById = computed(() => {
    const map = new Map<string, IEmployee>()
    options.employees.forEach((employee) => map.set(employee.id, employee))
    return map
  })

  const holidayByDate = computed(() => {
    const map = new Map<string, IHoliday>()
    options.holidays.forEach((holiday) => map.set(holiday.date, holiday))
    return map
  })

  const monthNovelties = computed(() => options.noveltiesFor(year.value, month.value))
  const monthMarkers = computed(() => options.markersFor(year.value, month.value))

  /**
   * Los cortes que **tocan** el mes visible — no "los dos cortes del mes".
   *
   * D-111: con días de corte configurables, un mes puede mostrar tres tramos
   * (la cola del anterior, uno completo y el arranque del siguiente) y sus
   * extremos caer fuera del mes. El cálculo vive en `payroll.config.ts`.
   */
  const periods = computed(() =>
    periodsTouchingMonth(year.value, month.value, options.config(), todayIso),
  )

  const openPeriod = computed(() => periods.value.find((period) => period.status === "open") ?? null)

  /** Días que faltan para que cierre el corte abierto — alimenta el estado anticipatorio. */
  const daysUntilPeriodCloses = computed(() => {
    if (!openPeriod.value) {
      return null
    }
    return daysBetween(todayIso, openPeriod.value.end)
  })

  /**
   * La grilla completa: relleno del mes anterior, el mes, y relleno del
   * siguiente hasta completar semanas de 7. Los días de relleno se pintan
   * atenuados pero **se muestran** — un calendario recortado se lee roto.
   */
  /**
   * Construye las celdas del mes para un alcance: una persona o todo el
   * equipo (`null`).
   *
   * Son dos vistas del mismo mes y las dos hacen falta a la vez. La grilla
   * muestra el alcance del filtro —esa es su gracia—, pero el detalle del día
   * lista **a todo el equipo** (D-115), y si recibiera la celda filtrada
   * mostraría "Laboró" a quien sí tuvo novedad, solo porque no era la
   * persona seleccionada. Ese fue un bug real.
   */
  function buildDays(scopeEmployeeId: string | null): ICalendarDay[] {
    const inScope = (employeeId: string) =>
      scopeEmployeeId === null || employeeId === scopeEmployeeId

    const leading = weekdayMondayFirst(year.value, month.value, 1)
    const totalDays = daysInMonth(year.value, month.value)
    const cellCount = Math.ceil((leading + totalDays) / 7) * 7

    const visibleNovelties = monthNovelties.value.filter((novelty) => inScope(novelty.employeeId))
    const visibleMarkers = monthMarkers.value.filter((marker) => inScope(marker.employeeId))

    const cells: ICalendarDay[] = []

    for (let index = 0; index < cellCount; index += 1) {
      const offset = index - leading
      // `new Date(y, m-1, 1 + offset)` normaliza solo el desbordamiento de mes.
      const cursor = new Date(year.value, month.value - 1, 1 + offset)
      const cellYear = cursor.getFullYear()
      const cellMonth = cursor.getMonth() + 1
      const cellDay = cursor.getDate()
      const date = isoOf(cellYear, cellMonth, cellDay)
      const inMonth = cellMonth === month.value && cellYear === year.value

      const novelties: IDayNovelty[] = inMonth
        ? visibleNovelties
            .filter((novelty) => date >= novelty.start && date <= novelty.end)
            .map((novelty) => ({
              novelty,
              employee: employeeById.value.get(novelty.employeeId)!,
              isFirstDay: date === novelty.start,
              isLastDay: date === novelty.end,
            }))
        : []

      const markers = inMonth ? visibleMarkers.filter((marker) => marker.date === date) : []

      /*
        Un corte puede empezar o terminar FUERA del mes visible (D-111), así que
        estas marcas solo aplican cuando la frontera cae en un día del mes: si
        el tramo arrancó el 20 de julio, agosto no dibuja su barra de inicio.
      */
      const periodStart = inMonth ? (periods.value.find((c) => c.start === date) ?? null) : null
      const periodEnd = inMonth ? (periods.value.find((c) => c.end === date) ?? null) : null

      const isSunday = isSundayDate(cellYear, cellMonth, cellDay)
      const holiday = inMonth ? (holidayByDate.value.get(date) ?? null) : null
      const isClosed = options.closedDays?.().has(date) ?? false
      const isWorkingDay = inMonth && !isSunday && !holiday && !isClosed

      /*
        `workedRatio` se **deduce**, no se registra: parte de que todo el mundo
        trabajó y descuenta a quien tenga una novedad que consuma el día
        completo. Un permiso de horas o medio día no saca a nadie de la cuenta
        —sí trabajó— pero su avatar aparece igual sobre la línea.
      */
      const visibleTeam = options.employees.filter(
        (employee) => employee.workerType === "employee" && inScope(employee.id),
      )
      const absentIds = new Set(
        novelties
          .filter((item) => item.novelty.span === "full_day")
          .map((item) => item.novelty.employeeId),
      )
      const workedRatio =
        !isWorkingDay || visibleTeam.length === 0
          ? 0
          : visibleTeam.filter((employee) => !absentIds.has(employee.id)).length /
            visibleTeam.length

      const period = inMonth
        ? (periods.value.find((c) => date >= c.start && date <= c.end) ?? null)
        : null

      /*
        Liquidado = **todos** los implicados cobraron ese día.

        Implicados son quienes están en nómina y a quienes ese día les tocaba
        trabajar; con el filtro puesto, solo esa persona. El `length > 0` no es
        defensivo por gusto: `[].every()` devuelve `true`, y sin esa guarda un
        día sin nadie implicado se pintaría como liquidado.

        `isSettledFor` es la costura del pago: hoy no existe el pago como
        entidad y un día está liquidado si su corte cerró —igual para todos—,
        así que la agregación no cambia nada todavía. Cuando el pago exista
        (D-114), esta función pasa a mirar su cobertura por persona y el
        "todo o nada" empieza a distinguir de verdad.
      */
      const isSettledFor = (_employeeId: string) => period?.status === "closed"
      const isSettled =
        isWorkingDay &&
        visibleTeam.length > 0 &&
        visibleTeam.every((employee) => isSettledFor(employee.id))

      /*
        Con una sola persona seleccionada, `novelties` ya viene filtrado a ella:
        lo que haya es *su* novedad del día. En la vista de todos se deja en
        `null` a propósito — ahí la línea sigue hablando de pagos, no de
        nadie en particular, y colorearla por la novedad de uno de seis sería
        mentir sobre los otros cinco.
      */
      const focusNovelty = scopeEmployeeId !== null && inMonth ? (novelties[0] ?? null) : null

      cells.push({
        date,
        dayOfMonth: cellDay,
        inMonth,
        isToday: date === todayIso,
        isFuture: date > todayIso,
        isSunday,
        holiday,
        isWorkingDay,
        period,
        periodStart,
        periodEnd,
        workedRatio,
        isSettled,
        focusNovelty,
        novelties,
        markers,
      })
    }

    return cells
  }

  /** Lo que pinta la grilla: el alcance del filtro. */
  const calendarDays = computed<ICalendarDay[]>(() => buildDays(selectedEmployeeId.value))

  /** Lo que leen los detalles: todo el equipo, sin importar el filtro. */
  const teamDays = computed<ICalendarDay[]>(() => buildDays(null))

  /** Cuenta de novedades visibles: decide si el mes se lee vacío o cargado. */
  const visibleNoveltyCount = computed(
    () =>
      monthNovelties.value.filter(
        (novelty) => !hasSelection.value || isSelected(novelty.employeeId),
      ).length,
  )

  return {
    year,
    month,
    monthLabel,
    isCurrentMonth,
    todayIso,
    calendarDays,
    teamDays,
    periods,
    openPeriod,
    daysUntilPeriodCloses,
    visibleNoveltyCount,
    selectedEmployeeId,
    hasSelection,
    isSelected,
    selectEmployee,
    goToPreviousMonth,
    goToNextMonth,
    goToToday,
  }
}
