<script setup lang="ts">
import { computed, ref, watch } from "vue"
import {
  IconAlertTriangle,
  IconFileSpreadsheet,
  IconFileText,
  IconPackage,
} from "@tabler/icons-vue"
import { toast } from "vue-sonner"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Spinner } from "@/components/ui/spinner"
import { billsApi } from "@/api/bills/bills.api"
import type { IBillFilters, IBillPackageSummary } from "@/api/bills/bills.types"
import { downloadBlob } from "@/lib/download"

/**
 * Confirmación del paquete de Facturación (D-78) — zip con un PDF por factura
 * más el Excel índice.
 *
 * Previsualiza antes de construir por una razón concreta: el zip se arma en
 * memoria y con un filtro amplio es un PDF por cada factura del año. El
 * usuario tiene que poder ver **cuántas** son antes de confirmar. Mismo patrón
 * previsualizar→confirmar del respaldo completo (D-77) y de las importaciones.
 *
 * **No es la factura de la DIAN y el diálogo lo dice arriba, no al pie:** una
 * advertencia al final no la lee quien solo busca el botón. Los documentos son
 * reconstrucciones desde la base; la copia firmada solo existirá cuando entre
 * la integración con el proveedor (D-09/D-38), y ese día `dian_valid` llega en
 * `true` y este aviso se apaga solo.
 */
const props = defineProps<{ filters: IBillFilters }>()

const open = defineModel<boolean>("open", { default: false })

const summary = ref<IBillPackageSummary | null>(null)
const isLoading = ref(false)
const isExporting = ref(false)
const hasError = ref(false)

/**
 * Fase del progreso. Son dos porque **solo una de las dos es medible**: el
 * servidor arma el zip completo antes de mandar el primer byte, así que durante
 * `building` no hay nada real que medir y la barra va indeterminada. Cuando
 * empiezan a llegar bytes se pasa a `downloading`, que sí tiene porcentaje.
 * Inventar un número en la primera fase sería peor que no mostrarlo: una barra
 * que se llena sola y se queda quieta parece un cuelgue.
 */
const phase = ref<"idle" | "building" | "downloading">("idle")
const downloadedBytes = ref(0)
const totalBytes = ref<number | undefined>(undefined)

const percent = computed(() => {
  if (phase.value !== "downloading" || !totalBytes.value) {
    return 0
  }
  return Math.min(100, Math.round((downloadedBytes.value / totalBytes.value) * 100))
})

const isIndeterminate = computed(() => phase.value === "building")

function formatBytes(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`
  }
  if (bytes < 1024 * 1024) {
    return `${Math.round(bytes / 1024)} KB`
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const progressLabel = computed(() => {
  if (phase.value === "building") {
    const count = summary.value?.total_bills ?? 0
    return `Armando ${count} ${count === 1 ? "documento" : "documentos"} en el servidor…`
  }
  if (totalBytes.value) {
    return `Descargando ${formatBytes(downloadedBytes.value)} de ${formatBytes(totalBytes.value)}`
  }
  return `Descargando ${formatBytes(downloadedBytes.value)}…`
})

/** Etiquetas del corte, para que el usuario reconozca qué filtro está exportando. */
const activeFilters = computed(() => {
  const { customer, bill_number, date_from, date_to, fiscal_status, ids } = props.filters
  const rows: { label: string, value: string }[] = []
  //  Primero, porque es el filtro más fuerte: si hay selección, el resto acota
  //  dentro de ella. Sin decirlo, el usuario que marcó 3 facturas y ve
  //  "Fechas: agosto" no sabría cuál de los dos manda.
  if (ids && ids.length > 0) {
    rows.push({
      label: "Selección",
      value: `${ids.length} ${ids.length === 1 ? "factura marcada" : "facturas marcadas"}`,
    })
  }
  if (date_from || date_to) {
    rows.push({
      label: "Fechas",
      value: `${date_from ?? "el inicio"} → ${date_to ?? "hoy"}`,
    })
  }
  if (customer) {
    rows.push({ label: "Cliente", value: customer })
  }
  if (bill_number) {
    rows.push({ label: "Código", value: bill_number })
  }
  if (fiscal_status) {
    rows.push({ label: "Estado DIAN", value: fiscal_status })
  }
  return rows
})

const isEmpty = computed(() => summary.value?.total_bills === 0)

watch(open, async isOpen => {
  if (!isOpen) {
    return
  }
  summary.value = null
  hasError.value = false
  isLoading.value = true
  try {
    summary.value = (await billsApi.getExportSummary(props.filters)).data
  } catch (error) {
    console.error("Bills export summary failed:", error)
    hasError.value = true
  } finally {
    isLoading.value = false
  }
})

async function confirmExport() {
  if (isExporting.value) {
    return
  }
  isExporting.value = true
  phase.value = "building"
  downloadedBytes.value = 0
  totalBytes.value = undefined
  try {
    const { data, headers } = await billsApi.exportPackage(props.filters, (loaded, total) => {
      //  El primer byte recibido es la señal de que el servidor terminó de
      //  armar el zip: de ahí en adelante el progreso sí es medible.
      phase.value = "downloading"
      downloadedBytes.value = loaded
      totalBytes.value = total
    })
    //  El nombre lo decide el backend (lleva negocio y fecha); si
    //  `Content-Disposition` no viaja, el navegador inventaría uno.
    downloadBlob(data, headers, "tiendapi-facturas.zip")
    open.value = false
    toast.success("Paquete descargado", { position: "bottom-center" })
  } catch (error) {
    console.error("Bills export failed:", error)
    toast.error("No se pudo generar el paquete", { position: "bottom-center" })
  } finally {
    isExporting.value = false
    phase.value = "idle"
  }
}
</script>

<template>
  <Dialog v-model:open="open">
    <DialogContent class="max-h-[85vh] overflow-y-auto sm:max-w-lg">
      <DialogHeader>
        <DialogTitle>Exportar paquete de facturas</DialogTitle>
        <DialogDescription>
          Un archivo .zip con un PDF por factura y un Excel que sirve de índice.
        </DialogDescription>
      </DialogHeader>

      <div class="grid gap-4">
        <!--
          Arriba del resumen a propósito (mismo criterio que el respaldo de
          D-77): si va al pie, quien solo busca el botón no la lee nunca.
        -->
        <div
          v-if="summary && !summary.dian_valid"
          class="flex items-start gap-3 rounded-lg border border-destructive/40 bg-destructive/5 p-3"
        >
          <IconAlertTriangle class="mt-0.5 size-5 shrink-0 text-destructive" />
          <div class="grid gap-1 text-sm">
            <p class="font-medium text-destructive">
              Estos PDF no son la factura electrónica de la DIAN
            </p>
            <p class="text-muted-foreground">
              Son documentos reconstruidos desde tus registros, útiles como
              respaldo propio o para tu manejo interno. Cada uno lo dice
              impreso. Tampoco van cifrados: llevan tus ventas y los datos de
              tus clientes en claro.
            </p>
          </div>
        </div>

        <div v-if="isLoading" class="flex flex-col items-center gap-3 py-6">
          <Spinner class="size-6 text-brand-icon" />
          <p class="text-sm text-muted-foreground">
            Contando las facturas del corte…
          </p>
        </div>

        <p v-else-if="hasError" class="text-sm text-destructive">
          No se pudo calcular el contenido del paquete.
        </p>

        <div v-else-if="summary" class="grid gap-3">
          <div class="flex items-center gap-3 rounded-lg border border-border p-3">
            <div class="flex size-10 shrink-0 items-center justify-center rounded-md bg-primary/10">
              <IconPackage class="size-5 text-brand-icon" />
            </div>
            <div class="min-w-0">
              <p class="truncate text-sm font-medium">
                {{ summary.business_name }}
              </p>
              <p class="text-xs text-muted-foreground">
                {{ summary.total_bills }}
                {{ summary.total_bills === 1 ? "factura" : "facturas" }}
                · versión {{ summary.platform_version }}
              </p>
            </div>
          </div>

          <div class="grid gap-2 rounded-lg border border-border p-3 text-sm">
            <div class="flex items-center gap-2">
              <IconFileText class="size-4 shrink-0 text-muted-foreground" />
              <span class="text-muted-foreground">
                {{ summary.total_bills }} PDF en la carpeta
                <code class="text-xs">facturas/</code>
              </span>
            </div>
            <div class="flex items-center gap-2">
              <IconFileSpreadsheet class="size-4 shrink-0 text-muted-foreground" />
              <span class="text-muted-foreground">
                Excel índice con el nombre y la ruta de cada archivo
              </span>
            </div>
            <!--
              Las anuladas se nombran aparte: el contador las necesita
              distinguibles sin abrir los archivos (D-60/D-78).
            -->
            <div v-if="summary.voided_bills > 0" class="flex items-center gap-2">
              <IconAlertTriangle class="size-4 shrink-0 text-destructive" />
              <span class="text-muted-foreground">
                {{ summary.voided_bills }}
                {{ summary.voided_bills === 1 ? "está anulada" : "están anuladas" }}
                — van marcadas en el nombre del archivo
              </span>
            </div>
          </div>

          <div
            v-if="activeFilters.length > 0"
            class="grid gap-1.5 rounded-lg border border-border p-3 text-sm"
          >
            <p class="text-xs font-medium text-muted-foreground uppercase">
              Corte que se exporta
            </p>
            <div
              v-for="row in activeFilters"
              :key="row.label"
              class="flex items-baseline justify-between gap-3"
            >
              <span class="shrink-0 text-muted-foreground">{{ row.label }}</span>
              <span class="truncate text-right font-medium">{{ row.value }}</span>
            </div>
          </div>
          <p v-else class="text-xs text-muted-foreground">
            Sin filtros activos: se exporta el histórico completo.
          </p>
        </div>
      </div>

      <!--
        La barra reemplaza al spinner mientras se exporta: con cientos de
        facturas esto tarda, y un spinner que gira sin decir nada no distingue
        "trabajando" de "colgado". El texto dice en qué fase va y cuánto pesa
        lo que ya bajó.
      -->
      <div v-if="isExporting" class="grid gap-1.5">
        <div class="h-2 w-full overflow-hidden rounded-full bg-primary/20">
          <div
            v-if="isIndeterminate"
            class="tiendapi-progress-sweep h-full w-1/3 rounded-full bg-primary"
          />
          <div
            v-else
            class="h-full rounded-full bg-primary transition-all"
            :style="{ width: `${percent}%` }"
          />
        </div>
        <div class="flex items-baseline justify-between gap-2 text-xs text-muted-foreground">
          <span class="truncate">{{ progressLabel }}</span>
          <span v-if="!isIndeterminate && totalBytes" class="shrink-0 tabular-nums">
            {{ percent }}%
          </span>
        </div>
      </div>

      <DialogFooter>
        <Button
          :disabled="isLoading || hasError || isExporting || isEmpty"
          class="gap-1.5"
          @click="confirmExport"
        >
          <Spinner v-if="isExporting" class="size-4" />
          {{ isExporting ? "Generando…" : isEmpty ? "No hay facturas" : "Descargar .zip" }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<style scoped>
/*
  Barrido de la fase indeterminada. Va como keyframes propio y no como
  utilidad de Tailwind porque necesita recorrer el ancho del riel
  (`translateX` de -100% a 300%), que ninguna de las animaciones de
  `tw-animate-css` hace.

  `prefers-reduced-motion`: quien pidió menos movimiento recibe una barra
  quieta a media caña en vez de nada — sigue comunicando "esto está en
  progreso" sin el barrido.
*/
@keyframes tiendapi-progress-sweep {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(300%);
  }
}

.tiendapi-progress-sweep {
  animation: tiendapi-progress-sweep 1.2s ease-in-out infinite;
}

@media (prefers-reduced-motion: reduce) {
  .tiendapi-progress-sweep {
    animation: none;
    width: 50%;
  }
}
</style>
