<script setup lang="ts">
import { computed, ref } from "vue"
import { IconDownload, IconFileInvoice } from "@tabler/icons-vue"
import { useRouter } from "vue-router"
import { toast } from "vue-sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Spinner } from "@/components/ui/spinner"
import { billsApi } from "@/api/bills/bills.api"
import { downloadBlob } from "@/lib/download"
import { formatCurrency, toDecimal } from "@/lib/money"
import type { IBill } from "@/api/bills/bills.types"

/**
 * Card horizontal de una factura — fila de la tabla de Facturación.
 *
 * Sigue el patrón de `itemStockUnitCard.vue` (checkbox a la izquierda, datos
 * en columnas, card en vez de `<tr>`): una tabla real no deja pintar el ícono
 * ni respirar los montos, y el usuario ya conoce esta forma de la pantalla de
 * Producto.
 */
const props = defineProps<{
  bill: IBill
  selected?: boolean
}>()

defineEmits<{
  "update:selected": [value: boolean]
}>()

/**
 * **Solo se marca la excepción** (D-81). La fila no lleva badge "Vigente":
 * el 90% de las facturas lo están, y una etiqueta que aparece en casi todas
 * las filas es tinta que no informa — la ausencia de marca ya significa
 * vigente. Es el mismo criterio de los POS que no tienen obligación fiscal
 * (Loyverse marca la reembolsada y deja la normal sin nada).
 *
 * Antes esta card pintaba además el estado fiscal, y como la integración DIAN
 * está diferida (D-09/D-38) el resultado real era 26 de 29 filas repitiendo
 * "Sin declarar" — que encima se lee como un incumplimiento tributario cuando
 * lo que pasa es que el subsistema no existe. Lo fiscal se movió al detalle,
 * que es donde tiene espacio para explicarse (D-81).
 */
const isVoided = computed(() => props.bill.voided_at !== null)

const isDownloading = ref(false)

/** El PDF de esta factura sola. Mismo documento que el del paquete (D-78). */
async function downloadPdf() {
  if (isDownloading.value) {
    return
  }
  isDownloading.value = true
  try {
    const { data, headers } = await billsApi.downloadPdf(props.bill.id)
    downloadBlob(data, headers, `${props.bill.bill_number}.pdf`)
  } catch (error) {
    console.error("Bill PDF download failed:", error)
    toast.error("No se pudo descargar la factura", { position: "bottom-center" })
  } finally {
    isDownloading.value = false
  }
}

const router = useRouter()

/** La fila entera abre el detalle — menos el checkbox, que selecciona (ver `@click.stop`). */
function openDetail() {
  router.push({ name: "invoice-detail", params: { id: props.bill.id } })
}

/** Fecha corta y legible; la hora no aporta en un listado y ocuparía el ancho de una columna. */
const issuedAt = computed(() =>
  new Intl.DateTimeFormat("es-CO", { day: "2-digit", month: "short", year: "numeric" })
    .format(new Date(props.bill.created_at)),
)

function money(value: string) {
  return formatCurrency(toDecimal(value))
}
</script>

<template>
  <div
    class="flex cursor-pointer items-center gap-4 rounded-lg border p-3 transition-colors outline-none hover:border-primary focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/30"
    :class="[
      selected ? 'border-primary bg-primary/5' : 'border-border',
      /* Anulada: atenuada, pero sigue abriéndose — es la que más se consulta después. */
      isVoided ? 'opacity-70' : '',
    ]"
    role="link"
    tabindex="0"
    @click="openDetail"
    @keydown.enter="openDetail"
  >
    <!-- `@click.stop`: marcar la factura no debe además navegar al detalle. -->
    <Checkbox
      :model-value="selected"
      :aria-label="`Seleccionar ${bill.bill_number}`"
      @click.stop
      @update:model-value="value => $emit('update:selected', value === true)"
    />

    <!-- El ícono es lo que hace que la fila se lea como una factura y no como un renglón más. -->
    <div class="flex size-10 shrink-0 items-center justify-center rounded-md bg-accent text-brand-icon">
      <IconFileInvoice class="size-5" />
    </div>

    <div class="min-w-0 flex-1">
      <p class="truncate font-mono text-sm font-semibold">
        {{ bill.bill_number }}
      </p>
      <p class="truncate text-xs text-muted-foreground" :title="bill.customer_name">
        {{ bill.customer_name }}
      </p>
    </div>

    <div class="hidden min-w-0 shrink-0 md:block md:w-28">
      <p class="text-[10px] uppercase tracking-wide text-muted-foreground">
        Fecha
      </p>
      <p class="truncate text-xs tabular-nums">
        {{ issuedAt }}
      </p>
    </div>

    <div class="hidden min-w-0 shrink-0 lg:block lg:w-24">
      <p class="text-[10px] uppercase tracking-wide text-muted-foreground">
        Ítems
      </p>
      <p class="truncate text-xs tabular-nums">
        {{ bill.items_count }}
      </p>
    </div>

    <div class="hidden min-w-0 shrink-0 lg:block lg:w-32">
      <p class="text-[10px] uppercase tracking-wide text-muted-foreground">
        IVA
      </p>
      <p class="truncate text-xs tabular-nums">
        {{ money(bill.total_iva) }}
      </p>
    </div>

    <div class="min-w-0 shrink-0 text-right md:w-36">
      <p class="text-[10px] uppercase tracking-wide text-muted-foreground">
        Total
      </p>
      <p class="truncate text-sm font-semibold tabular-nums">
        {{ money(bill.total) }}
      </p>
    </div>

    <!--
      Ancho reservado aunque no haya badge: sin el hueco fijo, las columnas de
      una fila vigente y una anulada no alinean y la lista se ve quebrada.
    -->
    <div class="w-24 shrink-0">
      <Badge v-if="isVoided" variant="destructive" class="w-full justify-center">
        Anulada
      </Badge>
    </div>

    <!--
      `@click.stop`: la fila entera navega al detalle, así que sin esto bajar
      el PDF además cambiaría de pantalla.
    -->
    <Button
      variant="ghost"
      size="icon-sm"
      class="shrink-0"
      :disabled="isDownloading"
      :title="`Descargar PDF de ${bill.bill_number}`"
      :aria-label="`Descargar PDF de ${bill.bill_number}`"
      @click.stop="downloadPdf"
    >
      <Spinner v-if="isDownloading" class="size-4" />
      <IconDownload v-else class="size-4" />
    </Button>
  </div>
</template>
