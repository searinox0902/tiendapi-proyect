import { computed, ref, watch } from "vue"
import type { Ref } from "vue"

import type { IEmployee } from "./payroll.types"

/**
 * Búsqueda sobre una lista de personas, compartida por los modales del módulo.
 *
 * Se extrajo al aparecer el segundo uso (detalle del día y captura de novedad),
 * porque lo que se repite no es el renderizado —cada modal pinta su fila
 * distinto: uno muestra estado y costo, el otro selecciona— sino **el criterio
 * de búsqueda**. Duplicar eso es como termina un producto donde un buscador
 * encuentra a "Andrés" y el otro no.
 */

/**
 * Compara sin tildes ni mayúsculas.
 *
 * En un equipo colombiano los nombres llevan tilde —Andrés, Jhon Cardona— y
 * nadie las escribe al buscar. Sin normalizar, teclear "andres" no encontraría
 * a Andrés, que es exactamente el momento en que el buscador tenía que servir.
 */
export function normalizeForSearch(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .trim()
}

export function useRosterSearch(
  roster: Ref<IEmployee[]> | (() => IEmployee[]),
  /** Se limpia la búsqueda cuando esto cambia — típicamente al abrir el modal. */
  resetOn?: () => unknown,
) {
  const query = ref("")

  if (resetOn) {
    // Arrastrar la búsqueda de un día al siguiente confunde: el usuario ve una
    // lista filtrada sin recordar por qué.
    watch(resetOn, () => {
      query.value = ""
    })
  }

  const source = computed(() => (typeof roster === "function" ? roster() : roster.value))

  /** Busca por nombre y por cargo: "bodega" es tan buen atajo como "Jhon". */
  const results = computed(() => {
    const needle = normalizeForSearch(query.value)
    if (!needle) {
      return source.value
    }
    return source.value.filter(
      (employee) =>
        normalizeForSearch(employee.name).includes(needle) ||
        normalizeForSearch(employee.role).includes(needle),
    )
  })

  const isFiltering = computed(() => query.value.trim().length > 0)
  const isEmpty = computed(() => isFiltering.value && results.value.length === 0)

  return { query, results, isFiltering, isEmpty, total: computed(() => source.value.length) }
}
