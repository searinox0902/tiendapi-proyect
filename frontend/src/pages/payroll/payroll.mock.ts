import type { IEmployee, IHoliday, IMarker, INovelty } from "./payroll.types"

/**
 * Datos de maqueta del módulo de Nómina.
 *
 * Autocontenido y sin backend, igual que el resto del frontend en esta etapa
 * (D-27). Cuando se conecte, esto se reemplaza por el store/API; los tipos de
 * `payroll.types.ts` ya son el contrato.
 *
 * Las novedades se generan **relativas al mes actual** en vez de con fechas
 * fijas: así la maqueta siempre abre con contenido, y navegar al mes siguiente
 * muestra el **estado vacío** —que es el 90% de los casos reales (D-99)— sin
 * tener que tocar datos.
 */

/** Un negocio pequeño real: 5 vinculados + 1 contratista. */
export const mockEmployees: IEmployee[] = [
  // Costos diarios de referencia: un salario mínimo 2026 ($1.750.905) sobre 30
  // días son ~$58.400, y de ahí para arriba según el cargo.
  { id: "e1", name: "Fernando Ruiz", initials: "FR", role: "Vendedor", workerType: "employee", dailyCost: 72000, vacationBalance: 12 },
  { id: "e2", name: "Marcela Ortiz", initials: "MO", role: "Cajera", workerType: "employee", dailyCost: 58400, vacationBalance: 6 },
  { id: "e3", name: "Jhon Cardona", initials: "JC", role: "Bodega", workerType: "employee", dailyCost: 58400, vacationBalance: 3 },
  { id: "e4", name: "Luisa Betancur", initials: "LB", role: "Vendedora", workerType: "employee", dailyCost: 65000, vacationBalance: 15 },
  { id: "e5", name: "Andrés Gómez", initials: "AG", role: "Domicilios", workerType: "employee", dailyCost: 54000, vacationBalance: 1 },
  {
    id: "e6",
    name: "Paula Restrepo",
    initials: "PR",
    role: "Contadora",
    workerType: "contractor",
    dailyCost: 120000,
    // Un contratista no causa vacaciones: no hay relación laboral.
    vacationBalance: 0,
  },
]

/** `YYYY-MM-DD` de un día del mes indicado, sin pasar por `Date` ni zonas horarias. */
function iso(year: number, month: number, day: number): string {
  const mm = String(month).padStart(2, "0")
  const dd = String(day).padStart(2, "0")
  return `${year}-${mm}-${dd}`
}

/**
 * Novedades sembradas en el mes que se le pase. Solo el mes actual las recibe
 * (ver `PayrollView.vue`) — los demás quedan vacíos a propósito.
 */
export function buildMockNovelties(year: number, month: number): INovelty[] {
  return [
    {
      id: "n1",
      employeeId: "e1",
      kind: "vacation",
      start: iso(year, month, 11),
      end: iso(year, month, 15),
      span: "full_day",
      label: "Vacaciones",
    },
    {
      id: "n2",
      employeeId: "e3",
      kind: "sick_leave",
      start: iso(year, month, 5),
      end: iso(year, month, 7),
      span: "full_day",
      label: "Incapacidad general (EPS)",
    },
    {
      id: "n3",
      employeeId: "e2",
      kind: "leave",
      start: iso(year, month, 12),
      end: iso(year, month, 12),
      span: "hours",
      label: "Permiso 2 horas (tarde)",
    },
    {
      id: "n4",
      employeeId: "e5",
      kind: "absence",
      start: iso(year, month, 19),
      end: iso(year, month, 19),
      span: "full_day",
      label: "Ausencia injustificada",
    },
    {
      id: "n5",
      employeeId: "e4",
      kind: "leave",
      start: iso(year, month, 24),
      end: iso(year, month, 24),
      span: "half_day",
      label: "Medio día libre (remunerado)",
    },
    {
      id: "n6",
      employeeId: "e2",
      kind: "vacation",
      start: iso(year, month, 24),
      end: iso(year, month, 27),
      span: "full_day",
      label: "Vacaciones",
    },
    {
      id: "n7",
      employeeId: "e3",
      kind: "leave",
      start: iso(year, month, 24),
      end: iso(year, month, 24),
      span: "full_day",
      label: "Día de descanso remunerado",
    },
    {
      id: "n8",
      employeeId: "e1",
      kind: "leave",
      start: iso(year, month, 24),
      end: iso(year, month, 24),
      span: "hours",
      label: "Permiso 3 horas (cita médica)",
    },
  ]
}

/** Marcadores: anotan el día sin consumirlo (horas extra). */
export function buildMockMarkers(year: number, month: number): IMarker[] {
  return [
    {
      id: "m1",
      employeeId: "e5",
      kind: "overtime",
      date: iso(year, month, 8),
      label: "2h extra diurnas",
    },
    {
      id: "m2",
      employeeId: "e4",
      kind: "overtime",
      date: iso(year, month, 22),
      label: "3h extra nocturnas",
    },
  ]
}

/**
 * Festivos colombianos 2026 — **solo para la maqueta**.
 *
 * ⚠️ No calcules esto a mano en producción: la Ley Emiliani (Ley 51 de 1983)
 * traslada 12 festivos religiosos al lunes siguiente y varios dependen de la
 * Pascua. Al conectar el módulo, reemplazar por un paquete de festivos
 * colombianos (`festivos-colombianos` / `colombia-holidays`) — es lógica de
 * dominio aburrida y con reglas raras, no vale la pena mantenerla acá.
 */
export const mockHolidays2026: IHoliday[] = [
  { date: "2026-01-01", name: "Año Nuevo" },
  { date: "2026-01-12", name: "Reyes Magos" },
  { date: "2026-03-23", name: "San José" },
  { date: "2026-04-02", name: "Jueves Santo" },
  { date: "2026-04-03", name: "Viernes Santo" },
  { date: "2026-05-01", name: "Día del Trabajo" },
  { date: "2026-05-18", name: "Ascensión" },
  { date: "2026-06-08", name: "Corpus Christi" },
  { date: "2026-06-15", name: "Sagrado Corazón" },
  { date: "2026-06-29", name: "San Pedro y San Pablo" },
  { date: "2026-07-20", name: "Independencia" },
  { date: "2026-08-07", name: "Batalla de Boyacá" },
  { date: "2026-08-17", name: "Asunción" },
  { date: "2026-10-12", name: "Día de la Raza" },
  { date: "2026-11-02", name: "Todos los Santos" },
  { date: "2026-11-16", name: "Independencia de Cartagena" },
  { date: "2026-12-08", name: "Inmaculada Concepción" },
  { date: "2026-12-25", name: "Navidad" },
]
