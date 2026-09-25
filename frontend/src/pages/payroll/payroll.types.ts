/**
 * Tipos del módulo de Nómina — maqueta del calendario.
 *
 * El diseño funcional completo está en `docs/13-modulo-nomina.md`. Lo que
 * importa acá es la separación de canales visuales que fija §7:
 *
 *   fondo de la celda → qué **tipo de día** es (propiedad del calendario)
 *   franjas dentro    → qué le pasó a **cada persona** (propiedad persona-día)
 *   bordes            → dónde están los **periods** (fronteras del período)
 *
 * Por eso `NoveltyKind` (franja) y `MarkerKind` (punto) son tipos distintos y
 * no un solo enum: los primeros **consumen días** y los segundos solo
 * **anotan** el día sin quitarlo. Mezclarlos haría que "trabajó horas extra"
 * se leyera igual que "faltó".
 */

/** Novedades que consumen días → se dibujan como franja de color. */
export type NoveltyKind = "absence" | "sick_leave" | "vacation" | "leave"

/**
 * Novedades que NO consumen días → se dibujan como marcador discreto.
 *
 * Solo horas extra: bonificación y descuento no son hechos de un día sino
 * ajustes de un pago, y se capturan al liquidar (D-121).
 */
export type MarkerKind = "overtime"

/**
 * Duración de una novedad dentro de un día. Se renderiza como **ancho** de la
 * franja: la cantidad de tinta es la cantidad de tiempo (§7 del diseño).
 */
export type NoveltySpan = "full_day" | "half_day" | "hours"

/** D-98: `Employee` es entidad independiente, fuera del Directorio. */
export type WorkerType = "employee" | "contractor"

export interface IEmployee {
  id: string
  name: string
  /** Iniciales para el `AvatarFallback` — la maqueta no carga fotos. */
  initials: string
  role: string
  workerType: WorkerType
  /**
   * Lo que esa persona le cuesta al negocio por día.
   *
   * **Es propiedad de la persona, no del día.** No es "lo que se le paga ese
   * día" — eso depende de reglas de ley (una ausencia injustificada no se paga,
   * una incapacidad se paga al 66,67% desde el tercer día) y el motor legal no
   * existe todavía (D-113, modo simple). Acá es una cifra de referencia para
   * dimensionar el impacto de una novedad, no una liquidación.
   */
  dailyCost: number
  /**
   * Días de vacaciones acumulados y no tomados.
   *
   * En Colombia se causan 15 **días hábiles** por año trabajado (1,25 por mes).
   * Acá es una cifra sembrada: el acumulado real sale de `EmployeeAccrual`
   * (§5.4) y lo alimenta el cierre de cada período, que aún no existe.
   */
  vacationBalance: number
}

export interface INovelty {
  id: string
  employeeId: string
  kind: NoveltyKind
  /** Fechas ISO `YYYY-MM-DD`, ambas inclusive. */
  start: string
  end: string
  span: NoveltySpan
  /**
   * Horas que consume la novedad. **Solo con `span: "hours"`.**
   *
   * Sin esto, `"hours"` no significa nada: un permiso "por horas" sin número no
   * se puede restar de la jornada. El `label` lo traía como texto suelto
   * ("Permiso 2 horas"), que se lee pero no se calcula.
   */
  hours?: number
  /**
   * Soporte adjunto: la incapacidad trae certificado de la EPS y el permiso
   * suele traer carta. Acá solo se guarda el nombre del archivo — no hay
   * backend que lo reciba todavía.
   */
  attachmentName?: string
  /** Texto que se muestra en el hover. */
  label: string
}

export interface IMarker {
  id: string
  employeeId: string
  kind: MarkerKind
  date: string
  /** Horas extra. Estructurado, no solo en el label. */
  quantity?: number
  label: string
}

export interface IHoliday {
  date: string
  name: string
}

/** D-110: el pago diario queda fuera — ver A-43. */
export type Periodicity = "weekly" | "semimonthly" | "monthly"

/** D-113: el motor legal es autorelleno sobre la captura manual, no otro camino. */
export type CalcMode = "simple" | "legal"

/**
 * Configuración de pago del negocio (D-103: global, sin override por empleado).
 * Se fija en el wizard de arranque (§7.4).
 */
export interface IPayrollConfig {
  periodicity: Periodicity
  /**
   * Días del mes en que corta el período. D-111: los define el negocio — una
   * quincena puede ser `[5, 20]`, no forzosamente `[1, 16]`. En mensual se usa
   * solo el primero; en semanal se ignora.
   */
  cutDays: number[]
  /** Solo para periodicidad semanal. 0 = domingo, 1 = lunes. */
  weekStartsOn: number
  /**
   * Horas de la jornada diaria. Es lo que el sistema asume **de buena fe** que
   * trabajó cada persona cuando no hay novedad que diga lo contrario.
   *
   * Configurable y no fijo en 8 a propósito: con 48 h semanales sobre seis días
   * da 8, pero la jornada va a 42 h (Ley 2101) y el reparto exacto es **A-35**,
   * todavía sin resolver. Escribir 8 en el código sería fijar una postura legal
   * que no nos corresponde tomar.
   */
  hoursPerDay: number
  calcMode: CalcMode
}

/**
 * Un corte es el período de pago. D-100: el mes es la unidad de cálculo y el
 * period la unidad de pago, por eso los cortes se muestran dentro del mes en
 * pantalla en vez de ser vistas separadas.
 *
 * **Ya no se numera 1 | 2.** Con días de corte configurables (D-111) un mes
 * puede mostrar tres tramos y sus extremos caer fuera del mes, así que el
 * identificador es la fecha de inicio y la etiqueta es el rango.
 */
export interface IPayrollPeriod {
  /** Fecha ISO de inicio: identifica el corte de forma estable. */
  id: string
  start: string
  end: string
  /** "5 – 19 ago" o "20 ago – 4 sep" cuando cruza de mes. */
  label: string
  status: "closed" | "open" | "upcoming"
  /**
   * `YYYY-MM` del mes al que pertenece para efectos de cálculo (D-100).
   * D-111 fija la regla: el mes de la **fecha de fin**, que es cuando se paga.
   */
  monthAnchor: string
}

/** Una celda ya resuelta del mes, lista para pintar. */
export interface ICalendarDay {
  /** ISO `YYYY-MM-DD`. */
  date: string
  dayOfMonth: number
  /** `false` en los días de relleno del mes anterior/siguiente. */
  inMonth: boolean
  isToday: boolean
  isSunday: boolean
  holiday: IHoliday | null
  /** Día hábil establecido: ni domingo ni festivo. Pinta el lienzo de fondo. */
  isWorkingDay: boolean
  /** El corte al que pertenece el día — decide el color de la línea. */
  period: IPayrollPeriod | null
  /**
   * El día todavía no ha ocurrido. La línea no puede afirmar "se laboró" sobre
   * algo que no pasó: en futuro se dibuja tenue, como expectativa.
   */
  isFuture: boolean
  /** Primer día de un corte — la línea de continuidad se corta antes. */
  periodStart: IPayrollPeriod | null
  /** Último día de un corte — la línea se corta después. */
  periodEnd: IPayrollPeriod | null
  /**
   * Proporción del equipo visible que laboró ese día (0 a 1).
   *
   * No se registra en ninguna parte: se **deduce** de las novedades de
   * ausencia (D-99). Es el valor que dibuja la línea de continuidad — 1 es
   * línea sólida, 0 es sin línea, y los intermedios la atenúan.
   */
  workedRatio: number
  /**
   * El día está liquidado **para todos los implicados del filtro actual**.
   *
   * Es "todo o nada" a propósito, y solo se agrega en este estado. Si unos
   * cobraron y otros no, el día **no** está liquidado — pintarlo a medias
   * reviviría el relleno parcial que se descartó: una línea a medio color no
   * significa nada que el usuario pueda leer.
   *
   * Los otros dos estados no necesitan agregación: "por venir" depende solo de
   * la fecha, igual para todo el mundo, y "laborado" es el valor por defecto.
   */
  isSettled: boolean
  /**
   * La novedad de la persona **enfocada** ese día — solo cuando el filtro está
   * en una sola persona. En la vista de todos es siempre `null`.
   *
   * Con ella la línea del día toma el **color del tipo de novedad**: mirando a
   * una persona, su fila deja de ser una línea de pago y se vuelve su línea de
   * tiempo — unas vacaciones del 11 al 15 son cinco días seguidos de verde
   * azulado. Es el wallchart que se descartó para el mes entero, apareciendo
   * solo donde sí cabe: una persona a la vez.
   */
  focusNovelty: IDayNovelty | null
  novelties: IDayNovelty[]
  markers: IMarker[]
}

/** Una novedad recortada al día que la contiene. */
export interface IDayNovelty {
  novelty: INovelty
  employee: IEmployee
  /** Redondea solo los extremos, para que un rango se lea continuo. */
  isFirstDay: boolean
  isLastDay: boolean
}
