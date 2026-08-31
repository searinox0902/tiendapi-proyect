<script setup lang="ts">
import { IconPhoto, IconTruck } from "@tabler/icons-vue"
import { useRouter } from "vue-router"

import { Badge } from "@/components/ui/badge"
import { toDecimal } from "@/lib/money"
import type { IRestockRow } from "@/api/dashboard/dashboard.types"

/**
 * "Reponer ya" (D-66) — el cruce demanda × stock, y la razón de ser del
 * Dashboard: es lo único que ninguna otra pantalla puede responder sola.
 *
 * **Muestra el par crudo, no el ratio.** El servidor ordena por días de
 * cobertura (`stock ÷ velocidad diaria`), pero eso nunca se pinta: la fila
 * dice *"quedan 2 · vendiste 14"*, que se entiende sin que nadie explique qué
 * es una cobertura. El ratio solo decide el orden y el tono.
 */
defineProps<{ rows: IRestockRow[] }>()

const router = useRouter()

/** Horizonte con el que un mostrador alcanza a pedirle al proveedor y recibir. */
const CRITICAL_COVER_DAYS = 7

function openProduct(referenceId: string) {
  router.push({ name: "items-detail", params: { referenceId } })
}

function units(value: string) {
  return toDecimal(value).toDecimalPlaces(2).toString()
}

/**
 * Tres niveles y no dos: "agotado" (ya no se puede vender) es un problema
 * distinto de "se está acabando" (todavía hay margen para pedir).
 */
function severity(row: IRestockRow): "out" | "critical" | "ok" {
  if (row.available_units === 0) {
    return "out"
  }
  return row.days_of_cover !== null && row.days_of_cover <= CRITICAL_COVER_DAYS
    ? "critical"
    : "ok"
}
</script>

<template>
  <section class="flex min-w-0 flex-col rounded-xl border border-border">
    <h2 class="flex shrink-0 items-center gap-2 border-b border-border px-4 py-3 text-sm font-semibold">
      <IconTruck class="size-4 text-muted-foreground" />
      Reponer ya
      <span class="ml-auto text-xs font-normal text-muted-foreground">
        lo que se acaba primero
      </span>
    </h2>

    <div class="min-h-0 flex-1 p-3">
      <p v-if="rows.length === 0" class="px-1 py-10 text-center text-sm text-muted-foreground">
        No se vendió nada en este período, así que no hay qué reponer.
      </p>

      <ul v-else class="space-y-1">
        <li v-for="row in rows" :key="row.reference_id">
          <button
            type="button"
            class="flex w-full items-center gap-3 rounded-lg p-2 text-left transition-colors outline-none hover:bg-accent focus-visible:bg-accent"
            @click="openProduct(row.reference_id)"
          >
            <div
              :style="row.image_url ? { backgroundImage: `url('${row.image_url}')` } : {}"
              role="img"
              :aria-label="row.title"
              class="flex size-9 shrink-0 items-center justify-center rounded-md border border-border bg-muted bg-contain bg-center bg-no-repeat text-muted-foreground"
            >
              <IconPhoto v-if="!row.image_url" class="size-4" />
            </div>

            <div class="min-w-0 flex-1">
              <p class="truncate font-mono text-xs text-muted-foreground">
                {{ row.sku }}
              </p>
              <p class="truncate text-sm" :title="row.title">
                {{ row.title }}
              </p>
            </div>

            <!--
              El par crudo. Es la frase entera lo que informa: "quedan 2" solo
              no dice si es poco, y "vendiste 14" solo no dice si alcanza.
            -->
            <div class="shrink-0 text-right">
              <p class="text-sm tabular-nums">
                <span
                  :class="severity(row) === 'ok' ? 'font-semibold' : 'font-bold text-destructive'"
                >
                  {{ row.available_units === 0 ? "agotado" : `quedan ${row.available_units}` }}
                </span>
              </p>
              <p class="truncate text-xs tabular-nums text-muted-foreground">
                vendiste {{ units(row.units_sold) }}
              </p>
            </div>

            <Badge
              v-if="severity(row) !== 'ok'"
              variant="destructive"
              class="w-20 shrink-0 justify-center"
            >
              {{ severity(row) === "out" ? "Sin stock" : "Se acaba" }}
            </Badge>
            <!-- Espaciador: sin él las filas sanas corren de ancho respecto a las marcadas. -->
            <span v-else class="w-20 shrink-0" aria-hidden="true" />
          </button>
        </li>
      </ul>
    </div>
  </section>
</template>
