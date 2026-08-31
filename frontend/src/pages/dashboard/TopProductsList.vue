<script setup lang="ts">
import { IconPhoto, IconTrophy } from "@tabler/icons-vue"
import { useRouter } from "vue-router"

import { formatCurrency, toDecimal } from "@/lib/money"
import type { ITopProduct } from "@/api/dashboard/dashboard.types"

/** Top productos vendidos del período, ordenado por unidades (D-66). */
defineProps<{ products: ITopProduct[] }>()

const router = useRouter()

function openProduct(referenceId: string) {
  router.push({ name: "items-detail", params: { referenceId } })
}

/** `3.000` → `3`: las cantidades llegan como decimal del servidor pero se venden por unidad. */
function units(value: string) {
  return toDecimal(value).toDecimalPlaces(2).toString()
}

function money(value: string) {
  return formatCurrency(toDecimal(value))
}
</script>

<template>
  <section class="flex min-w-0 flex-col rounded-xl border border-border">
    <h2 class="flex shrink-0 items-center gap-2 border-b border-border px-4 py-3 text-sm font-semibold">
      <IconTrophy class="size-4 text-muted-foreground" />
      Top productos vendidos
    </h2>

    <div class="min-h-0 flex-1 p-3">
      <p v-if="products.length === 0" class="px-1 py-10 text-center text-sm text-muted-foreground">
        No se vendió nada en este período.
      </p>

      <ul v-else class="space-y-1">
        <li v-for="(product, index) in products" :key="product.reference_id">
          <button
            type="button"
            class="flex w-full items-center gap-3 rounded-lg p-2 text-left transition-colors outline-none hover:bg-accent focus-visible:bg-accent"
            @click="openProduct(product.reference_id)"
          >
            <!-- El puesto en el ranking: sin él la lista se lee como un listado cualquiera. -->
            <span class="w-4 shrink-0 text-center text-xs font-semibold tabular-nums text-muted-foreground">
              {{ index + 1 }}
            </span>

            <!-- Mismo patrón de fondo que la caja (D-50): imagen completa, sin recortar. -->
            <div
              :style="product.image_url ? { backgroundImage: `url('${product.image_url}')` } : {}"
              role="img"
              :aria-label="product.title"
              class="flex size-9 shrink-0 items-center justify-center rounded-md border border-border bg-muted bg-contain bg-center bg-no-repeat text-muted-foreground"
            >
              <IconPhoto v-if="!product.image_url" class="size-4" />
            </div>

            <div class="min-w-0 flex-1">
              <p class="truncate font-mono text-xs text-muted-foreground">
                {{ product.sku }}
              </p>
              <p class="truncate text-sm" :title="product.title">
                {{ product.title }}
              </p>
            </div>

            <div class="shrink-0 text-right">
              <p class="text-sm font-semibold tabular-nums">
                {{ units(product.units) }} u
              </p>
              <p class="truncate text-xs tabular-nums text-muted-foreground">
                {{ money(product.revenue) }}
              </p>
            </div>
          </button>
        </li>
      </ul>
    </div>
  </section>
</template>
