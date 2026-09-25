import type { IPayrollPeriod, IPayrollConfig, Periodicity } from "./payroll.types"

/**
 * Configuración de pago del negocio y cálculo de los cortes.
 *
 * Antes esto vivía incrustado en el composable con dos cortes fijos, 1–15 y
 * 16–fin. **D-111 lo derriba:** los días de period los define el negocio (una
 * quincena puede ser 5 y 20), y D-110 agrega la periodicidad semanal.
 *
 * La consecuencia que obliga a reescribir esto no es la configurabilidad en sí,
 * sino lo que arrastra: **con periods en 5 y 20, el tramo del 20 al 4 cruza el
 * fin de mes**. Cruzar meses deja de ser un caso raro de la semanal y pasa a
 * ser la norma. Por eso ya no se calculan "los dos cortes del mes" sino **los
 * tramos que tocan el mes**, que pueden ser uno, dos o tres — y cuyos extremos
 * caen fuera del mes que se está viendo.
 */

/** Config de la maqueta. Al construir el wizard de arranque (§7.4) sale de ahí. */
export const defaultPayrollConfig: IPayrollConfig = {
  periodicity: "semimonthly",
  // Días de period del negocio. El taller del primer cliente usa 5 y 20.
  cutDays: [1, 16],
  // Lunes. Solo aplica a periodicidad semanal.
  weekStartsOn: 1,
  hoursPerDay: 8,
  calcMode: "simple",
}

function pad(value: number): string {
  return String(value).padStart(2, "0")
}

function iso(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

function addDays(date: Date, days: number): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate() + days)
}

function daysInMonth(year: number, month: number): number {
  return new Date(year, month, 0).getDate()
}

/**
 * Fechas de inicio de period en un rango, según la periodicidad.
 *
 * Se genera con holgura de un mes a cada lado del mes visible: hace falta para
 * encontrar el corte que **empezó el mes anterior** y todavía cubre los
 * primeros días del actual.
 */
function periodStartsAround(year: number, month: number, config: IPayrollConfig): Date[] {
  const starts: Date[] = []

  if (config.periodicity === "weekly") {
    // Retrocede hasta el primer día de la semana anterior al mes.
    const cursor = new Date(year, month - 2, 1)
    while (cursor.getDay() !== config.weekStartsOn) {
      cursor.setDate(cursor.getDate() - 1)
    }
    const limit = new Date(year, month + 1, 1)
    while (cursor < limit) {
      starts.push(new Date(cursor))
      cursor.setDate(cursor.getDate() + 7)
    }
    return starts
  }

  // Mensual y quincenal comparten forma: uno o varios días de period por mes.
  const cutDays = config.periodicity === "monthly" ? [config.cutDays[0] ?? 1] : config.cutDays
  for (let offset = -1; offset <= 1; offset += 1) {
    const cursor = new Date(year, month - 1 + offset, 1)
    const cursorYear = cursor.getFullYear()
    const cursorMonth = cursor.getMonth() + 1
    const lastDay = daysInMonth(cursorYear, cursorMonth)
    for (const day of [...cutDays].sort((a, b) => a - b)) {
      // Un corte configurado el 31 debe caer el 28 en febrero, no desbordar.
      starts.push(new Date(cursorYear, cursorMonth - 1, Math.min(day, lastDay)))
    }
  }
  return starts.sort((a, b) => a.getTime() - b.getTime())
}

function statusOf(start: string, end: string, todayIso: string): IPayrollPeriod["status"] {
  if (end < todayIso) {
    return "closed"
  }
  if (start > todayIso) {
    return "upcoming"
  }
  return "open"
}

const MONTH_SHORT = [
  "ene",
  "feb",
  "mar",
  "abr",
  "may",
  "jun",
  "jul",
  "ago",
  "sep",
  "oct",
  "nov",
  "dic",
]

/** "5 – 19 ago" o "20 ago – 4 sep" cuando el corte cruza de mes. */
function labelFor(start: Date, end: Date): string {
  const from = `${start.getDate()} ${MONTH_SHORT[start.getMonth()]}`
  const to = `${end.getDate()} ${MONTH_SHORT[end.getMonth()]}`
  return start.getMonth() === end.getMonth()
    ? `${start.getDate()} – ${to}`
    : `${from} – ${to}`
}

/**
 * Los cortes que **tocan** el mes indicado — no "los cortes del mes".
 *
 * Con periods en 5 y 20, agosto devuelve tres: la cola del que arrancó el 20 de
 * julio, el completo del 5 al 19, y el que arranca el 20 y termina en
 * septiembre. Con periodicidad mensual y period el día 1, devuelve uno solo.
 */
export function periodsTouchingMonth(
  year: number,
  month: number,
  config: IPayrollConfig,
  todayIso: string,
): IPayrollPeriod[] {
  const starts = periodStartsAround(year, month, config)
  const monthStart = `${year}-${pad(month)}-01`
  const monthEnd = `${year}-${pad(month)}-${pad(daysInMonth(year, month))}`

  const periods: IPayrollPeriod[] = []

  for (let index = 0; index < starts.length - 1; index += 1) {
    const start = starts[index]
    const end = addDays(starts[index + 1], -1)
    const startIso = iso(start)
    const endIso = iso(end)

    // Solapa con el mes visible: empieza antes de que acabe y termina después
    // de que empiece.
    if (startIso > monthEnd || endIso < monthStart) {
      continue
    }

    periods.push({
      id: startIso,
      start: startIso,
      end: endIso,
      label: labelFor(start, end),
      status: statusOf(startIso, endIso, todayIso),
      /*
        D-111: un corte que cruza pertenece al mes de su **fecha de fin**, que
        es cuando se liquida y se paga. Es la regla más simple que no obliga a
        partir el corte. Cuando llegue el motor legal habrá que revisarla contra
        el IBC, que es estrictamente mensual.
      */
      monthAnchor: `${end.getFullYear()}-${pad(end.getMonth() + 1)}`,
    })
  }

  return periods
}

export const PERIODICITY_LABELS: Record<Periodicity, string> = {
  weekly: "Semanal",
  semimonthly: "Quincenal",
  monthly: "Mensual",
}
