<script setup lang="ts">
import { ref, watch } from "vue"
import { IconAlertTriangle, IconDatabase } from "@tabler/icons-vue"
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
import { backupApi } from "@/api/backup/backup.api"
import type { IBackupSummary } from "@/api/backup/backup.types"
import { downloadBlob } from "@/lib/download"

/**
 * Confirmación del respaldo completo (D-77). Dos cosas tiene que dejar claras
 * antes de que el usuario descargue, y ninguna es obvia mirando un botón:
 *
 * 1. **Qué se lleva** — el respaldo incluye las facturas y los datos de los
 *    clientes, no solo el catálogo. Se listan los conteos reales.
 * 2. **Que sale sin cifrar** — SQLCipher (D-06) no está implementado todavía,
 *    así que el archivo tiene toda la información financiera en claro. Que el
 *    usuario lo sepa *antes* es la diferencia entre un respaldo y una fuga.
 */
const open = defineModel<boolean>("open", { default: false })

const summary = ref<IBackupSummary | null>(null)
const isLoading = ref(false)
const isExporting = ref(false)
const hasError = ref(false)

watch(open, async isOpen => {
  if (!isOpen) {
    return
  }
  summary.value = null
  hasError.value = false
  isLoading.value = true
  try {
    summary.value = (await backupApi.getSummary()).data
  } catch (error) {
    console.error("Backup summary failed:", error)
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
  try {
    const { data, headers } = await backupApi.exportProject()
    downloadBlob(data, headers, "tiendapi-respaldo.sqlite")
    open.value = false
    toast.success("Respaldo descargado", { position: "bottom-center" })
  } catch (error) {
    console.error("Backup export failed:", error)
    toast.error("No se pudo generar el respaldo", { position: "bottom-center" })
  } finally {
    isExporting.value = false
  }
}
</script>

<template>
  <Dialog v-model:open="open">
    <DialogContent class="max-h-[85vh] overflow-y-auto sm:max-w-lg">
      <DialogHeader>
        <DialogTitle>Exportar proyecto completo</DialogTitle>
        <DialogDescription>
          Un solo archivo con todo el negocio — catálogo, inventario, clientes
          y facturas.
        </DialogDescription>
      </DialogHeader>

      <div class="grid gap-4">
        <!--
          La advertencia va ARRIBA del resumen y no al pie: si va abajo, el
          usuario que solo busca el botón no la lee nunca.
        -->
        <div class="flex items-start gap-3 rounded-lg border border-destructive/40 bg-destructive/5 p-3">
          <IconAlertTriangle class="mt-0.5 size-5 shrink-0 text-destructive" />
          <div class="grid gap-1 text-sm">
            <p class="font-medium text-destructive">
              El archivo no está cifrado
            </p>
            <p class="text-muted-foreground">
              Cualquiera que lo abra puede ver tus ventas, tus precios de compra
              y los datos de tus clientes. Guardalo en un lugar seguro y no lo
              mandes por correo ni por chat.
            </p>
          </div>
        </div>

        <div v-if="isLoading" class="flex flex-col items-center gap-3 py-6">
          <Spinner class="size-6 text-brand-icon" />
          <p class="text-sm text-muted-foreground">
            Calculando el contenido…
          </p>
        </div>

        <p v-else-if="hasError" class="text-sm text-destructive">
          No se pudo calcular el contenido del respaldo.
        </p>

        <div v-else-if="summary" class="grid gap-3">
          <div class="flex items-center gap-3 rounded-lg border border-border p-3">
            <div class="flex size-10 shrink-0 items-center justify-center rounded-md bg-primary/10">
              <IconDatabase class="size-5 text-brand-icon" />
            </div>
            <div class="min-w-0">
              <p class="truncate text-sm font-medium">
                {{ summary.business_name }}
              </p>
              <p class="text-xs text-muted-foreground">
                Base de datos · versión {{ summary.platform_version }}
              </p>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-x-4 gap-y-1.5 rounded-lg border border-border p-3 text-sm">
            <div
              v-for="row in summary.counts"
              :key="row.table"
              class="flex items-baseline justify-between gap-2"
            >
              <span class="truncate text-muted-foreground">{{ row.label }}</span>
              <span class="shrink-0 font-medium tabular-nums">{{ row.count }}</span>
            </div>
          </div>
        </div>
      </div>

      <DialogFooter>
        <Button
          :disabled="isLoading || hasError || isExporting"
          class="gap-1.5"
          @click="confirmExport"
        >
          <Spinner v-if="isExporting" class="size-4" />
          {{ isExporting ? "Generando…" : "Descargar respaldo" }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
