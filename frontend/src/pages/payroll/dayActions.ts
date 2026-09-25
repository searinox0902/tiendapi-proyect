import {
  IconBeach,
  IconCalendarOff,
  IconClockPlus,
  IconFileText,
  IconStethoscope,
  IconUserMinus,
  IconUserQuestion,
} from "@tabler/icons-vue"
import type { Component } from "vue"

import type { MarkerKind, NoveltyKind } from "./payroll.types"

/**
 * Acciones del botón "..." de cada día.
 *
 * **Deliberadamente NO es el catálogo de tipos de novedad (D-112).** Ese
 * catálogo es una tabla con banderas (`unit`, `effect`, `consumes_day`,
 * `dian_code`) y llega cuando se construya el modelo de datos. Esto es una
 * lista plana de acciones, escrita para que el flujo se pueda *sentir* antes de
 * que exista la estructura — si el modelo se define primero, la interfaz sale
 * cuadriculada a su forma.
 *
 * Las cuatro primeras son **las cuatro de la leyenda del calendario**: el
 * usuario ya aprendió esos colores mirando la pantalla, así que la primera
 * pregunta del popover usa un vocabulario que ya domina. Van arriba porque son
 * las frecuentes.
 */

export type DayActionKind =
  /** Consume el día → avatar con anillo de color en la celda. */
  | { type: "novelty"; kind: NoveltyKind }
  /** Solo anota el día → punto discreto. */
  | { type: "marker"; kind: MarkerKind }
  /** Propiedad del día, no de una persona. */
  | { type: "day"; kind: "non_working" | "note" }

export interface IDayAction {
  id: string
  label: string
  icon: Component
  action: DayActionKind
  /** Separador visual antes de esta acción: agrupa sin escribir títulos. */
  startsGroup?: boolean
}

export const DAY_ACTIONS: IDayAction[] = [
  // --- Consumen el día: las cuatro de la leyenda ---
  {
    id: "absence",
    label: "Agregar ausencia",
    icon: IconUserMinus,
    action: { type: "novelty", kind: "absence" },
  },
  {
    id: "sick_leave",
    label: "Agregar incapacidad",
    icon: IconStethoscope,
    action: { type: "novelty", kind: "sick_leave" },
  },
  {
    id: "vacation",
    label: "Agregar vacaciones",
    icon: IconBeach,
    action: { type: "novelty", kind: "vacation" },
  },
  {
    id: "leave",
    label: "Agregar permiso o licencia",
    icon: IconUserQuestion,
    action: { type: "novelty", kind: "leave" },
  },

  /*
    --- Anotan el día sin consumirlo ---

    Solo horas extra. Bonificación y descuento estuvieron aquí y salieron
    (D-121): no son hechos de un día sino ajustes de un pago, y se capturan
    al liquidar.
  */
  {
    id: "overtime",
    label: "Registrar horas extra",
    icon: IconClockPlus,
    action: { type: "marker", kind: "overtime" },
    startsGroup: true,
  },

  /*
    --- Del día, no de una persona ---

    `non_working` cubre un hueco real del modelo: hoy un día es laborable si no
    es domingo ni festivo, y no hay forma de decir "ese jueves cerramos" —
    inventario, fiesta del pueblo, se dañó la máquina. Es propiedad del día y
    afecta a todos, así que no puede ser una novedad por persona.
  */
  {
    id: "non_working",
    label: "Marcar el día como no laborable",
    icon: IconCalendarOff,
    action: { type: "day", kind: "non_working" },
    startsGroup: true,
  },
  {
    id: "note",
    label: "Agregar anotación",
    icon: IconFileText,
    action: { type: "day", kind: "note" },
  },
]

/** Etiquetas legibles por tipo, para el formulario y el detalle del día. */
export const NOVELTY_LABEL: Record<NoveltyKind, string> = {
  absence: "Ausencia",
  sick_leave: "Incapacidad",
  vacation: "Vacaciones",
  leave: "Permiso o licencia",
}

/**
 * Etiqueta corta para los chips de estado del detalle del día.
 *
 * Distinta de `NOVELTY_LABEL`, que es la del menú de acciones ("Agregar permiso
 * o licencia"): en un chip esa frase no cabe ni hace falta, porque el color ya
 * dice de qué familia es.
 */
export const NOVELTY_CHIP: Record<NoveltyKind, string> = {
  absence: "Ausencia",
  sick_leave: "Incapacidad",
  vacation: "Vacaciones",
  leave: "Permiso",
}

export const MARKER_LABEL: Record<MarkerKind, string> = {
  overtime: "Horas extra",
}

/**
 * Color de cada tipo, apuntando a los tokens de `style.css`.
 *
 * Lo leen la grilla, los chips de los detalles y el selector del formulario:
 * un solo mapa para que ningún componente invente un tono y el usuario vea
 * el mismo color donde quiera que aparezca la novedad.
 */
export const NOVELTY_COLOR: Record<NoveltyKind, string> = {
  absence: "var(--novelty-absence)",
  sick_leave: "var(--novelty-sick-leave)",
  vacation: "var(--novelty-vacation)",
  leave: "var(--novelty-leave)",
}

/** Los marcadores son neutros: anotan, no consumen (D-99). */
export const MARKER_COLOR = "var(--novelty-marker)"
