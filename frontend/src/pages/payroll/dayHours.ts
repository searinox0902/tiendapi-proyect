import type { ICalendarDay, IMarker, INovelty } from "./payroll.types"

/**
 * Horas trabajadas por persona en un día.
 *
 * **El sistema actúa de buena fe.** Se parte de que todo el mundo cumplió la
 * jornada, y solo las novedades la reducen. Es la misma regla que gobierna la
 * línea de continuidad del calendario (D-99): nunca se registra presencia, se
 * registra la excepción — porque un sistema que hay que alimentar todos los
 * días con "sí vino" es un reloj de marcación, y eso se descartó desde el
 * principio.
 *
 * `hoursPerDay` viene de la configuración y no está fijo en 8: con 48 h
 * semanales sobre seis días daría 8, pero la jornada va a 42 h y el reparto es
 * **A-35**, sin resolver.
 */

export interface IDayHours {
  /** Horas de jornada efectivamente cubiertas. */
  worked: number
  /** Horas que la novedad descontó. */
  deducted: number
  /** Horas extra registradas ese día. */
  overtime: number
}

export function hoursForEmployee(
  day: ICalendarDay,
  employeeId: string,
  novelty: INovelty | undefined,
  hoursPerDay: number,
): IDayHours {
  const overtime = day.markers
    .filter((marker: IMarker) => marker.employeeId === employeeId && marker.kind === "overtime")
    .reduce((total, marker) => total + (marker.quantity ?? 0), 0)

  // El negocio no abrió: nadie cumplió jornada, y las horas extra de un día
  // cerrado no tienen de dónde salir.
  if (!day.isWorkingDay) {
    return { worked: 0, deducted: 0, overtime: 0 }
  }

  if (!novelty) {
    return { worked: hoursPerDay, deducted: 0, overtime }
  }

  if (novelty.span === "half_day") {
    const half = hoursPerDay / 2
    return { worked: half, deducted: half, overtime }
  }

  if (novelty.span === "hours") {
    // Un permiso más largo que la jornada no deja horas negativas.
    const deducted = Math.min(novelty.hours ?? 0, hoursPerDay)
    return { worked: hoursPerDay - deducted, deducted, overtime }
  }

  return { worked: 0, deducted: hoursPerDay, overtime }
}

/** `8` · `7,5` — coma decimal, y sin decimales cuando es entero. */
export function formatHours(value: number): string {
  const rounded = Math.round(value * 100) / 100
  return Number.isInteger(rounded) ? `${rounded} h` : `${rounded.toString().replace(".", ",")} h`
}
