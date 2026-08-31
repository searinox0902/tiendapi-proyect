<script setup lang="ts">
import { computed, ref } from "vue"
import { IconAlertTriangle, IconFile } from "@tabler/icons-vue"
import axios from "axios"
import { toast } from "vue-sonner"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Spinner } from "@/components/ui/spinner"
import { Switch } from "@/components/ui/switch"
import { referencesApi } from "@/api/references/references.api"
import type { IReferenceImportPreview } from "@/api/references/references.types"

/**
 * Importación granular de Referencias (D-73, nivel 3: suma, no reemplaza).
 * Acepta JSON o el .xlsx que produce "Exportar" —el mismo esquema de
 * columnas, D-74— porque son los dos formatos con round-trip fiel; markdown
 * sigue siendo de solo salida. El cliente no parsea nada: sube el archivo tal
 * cual y el backend detecta el formato, así el bundle del instalador Tauri no
 * carga ninguna librería de xlsx (D-29/D-31).
 *
 * El input de archivo vive fuera del `<Dialog>` a propósito y siempre montado:
 * el modal recién aparece cuando ya hay un archivo que mostrar (ícono +
 * nombre), no una pantalla vacía pidiendo elegir uno. `pickFile()` es lo que
 * el botón "Importar" del navbar dispara.
 */
const open = defineModel<boolean>("open", { default: false })

const emit = defineEmits<{ imported: [] }>()

const fileInputRef = ref<HTMLInputElement | null>(null)
const fileName = ref("")
const selectedFile = ref<File | null>(null)
const preview = ref<IReferenceImportPreview | null>(null)
const isPreviewing = ref(false)
const isImporting = ref(false)
/** D-73: por defecto se saltan los SKU que ya existen — traerlos igual es la excepción, no el default. */
const skipExisting = ref(true)
const errorMessage = ref("")

/**
 * `accept` filtra el navegador de archivos del sistema operativo a la
 * extensión elegida en el popover — sin esto el usuario ve las dos mezcladas
 * y puede terminar subiendo la que no quería.
 */
function pickFile(accept?: string) {
  if (fileInputRef.value && accept) {
    fileInputRef.value.accept = accept
  }
  fileInputRef.value?.click()
}

defineExpose({ pickFile })

const validRowCount = computed(() => {
  if (!preview.value) {
    return 0
  }
  return preview.value.total_rows - preview.value.invalid.length
})

const willImportCount = computed(() => {
  if (!preview.value) {
    return 0
  }
  return skipExisting.value ? preview.value.new_count : validRowCount.value
})

/** Solo para el subtítulo bajo el nombre — la validación real la hace el backend, no la extensión. */
const fileTypeLabel = computed(() =>
  fileName.value.toLowerCase().endsWith(".xlsx") ? "Excel" : "JSON",
)

async function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  //  Se limpia ya mismo, no al cerrar el modal: sin esto, elegir el MISMO
  //  archivo dos veces seguidas no dispara `change` la segunda vez.
  input.value = ""
  if (!file) {
    return
  }

  selectedFile.value = file
  preview.value = null
  errorMessage.value = ""
  skipExisting.value = true
  fileName.value = file.name
  open.value = true

  isPreviewing.value = true
  try {
    const { data } = await referencesApi.previewImport(file)
    preview.value = data
  } catch (error) {
    console.error("Preview import failed:", error)
    const detail = axios.isAxiosError(error) ? error.response?.data?.detail : undefined
    errorMessage.value = typeof detail === "string" ? detail : "No se pudo leer el archivo"
  } finally {
    isPreviewing.value = false
  }
}

async function confirmImport() {
  if (!selectedFile.value || isImporting.value || willImportCount.value === 0) {
    return
  }
  isImporting.value = true
  try {
    const { data } = await referencesApi.importReferences(selectedFile.value, skipExisting.value)
    open.value = false
    emit("imported")

    const summary = [`${data.created} creadas`]
    if (data.skipped > 0) {
      summary.push(`${data.skipped} saltadas`)
    }
    if (data.invalid > 0) {
      summary.push(`${data.invalid} inválidas`)
    }

    const batchId = data.batch_id
    toast.success(summary.join(" · "), {
      position: "bottom-center",
      //  Sin esto, un archivo mal armado que ya escribió en la BBDD solo se
      //  corrige a mano fila por fila desde Referencias — el "deshacer" es lo
      //  que D-73 pide para que el usuario pueda pulir sin miedo.
      action: batchId
        ? {
            label: "Deshacer",
            onClick: () => undoImport(batchId),
          }
        : undefined,
    })
  } catch (error) {
    console.error("Import references failed:", error)
    toast.error("No se pudo importar el catálogo", { position: "bottom-center" })
  } finally {
    isImporting.value = false
  }
}

async function undoImport(batchId: string) {
  try {
    await referencesApi.undoImportBatch(batchId)
    emit("imported")
    toast.success("Importación deshecha", { position: "bottom-center" })
  } catch (error) {
    console.error("Undo import failed:", error)
    const detail = axios.isAxiosError(error) ? error.response?.data?.detail : undefined
    toast.error(
      typeof detail === "string" ? detail : "No se pudo deshacer la importación",
      { position: "bottom-center" },
    )
  }
}
</script>

<template>
  <input
    ref="fileInputRef"
    type="file"
    accept="application/json,.json,.xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    class="hidden"
    @change="onFileChange"
  >

  <Dialog v-model:open="open">
    <DialogContent class="max-h-[85vh] overflow-y-auto sm:max-w-md">
      <DialogHeader>
        <DialogTitle>Importar catálogo</DialogTitle>
        <DialogDescription>
          Acepta JSON o el Excel exportado por el sistema. Suma referencias
          nuevas al catálogo, nunca lo reemplaza.
        </DialogDescription>
      </DialogHeader>

      <div class="grid gap-4">
        <!-- Identidad del archivo: ícono + nombre, siempre visible una vez elegido. -->
        <div class="flex items-center gap-3 rounded-lg border border-border p-3">
          <div class="flex size-10 shrink-0 items-center justify-center rounded-md bg-primary/10">
            <IconFile class="size-5 text-brand-icon" />
          </div>
          <div class="min-w-0 flex-1">
            <p class="truncate text-sm font-medium" :title="fileName">
              {{ fileName }}
            </p>
            <p class="text-xs text-muted-foreground">
              {{ fileTypeLabel }}
            </p>
          </div>
        </div>

        <!-- Analizando: la "función que analiza" es el preview, mostrada como su propio momento. -->
        <div v-if="isPreviewing" class="flex flex-col items-center gap-3 py-6">
          <Spinner class="size-6 text-brand-icon" />
          <p class="text-sm text-muted-foreground">
            Analizando archivo…
          </p>
        </div>

        <p v-else-if="errorMessage" class="flex items-start gap-2 text-sm text-destructive">
          <IconAlertTriangle class="mt-0.5 size-4 shrink-0" />
          {{ errorMessage }}
        </p>

        <div v-else-if="preview" class="grid gap-4">
          <!-- Resultado del análisis, destacado — ej. "+24 referencias nuevas". -->
          <div class="rounded-lg bg-primary/10 px-4 py-3 text-center">
            <p class="text-3xl font-bold tabular-nums text-brand-icon">
              +{{ preview.new_count }}
            </p>
            <p class="text-sm text-muted-foreground">
              {{ preview.new_count === 1 ? "referencia nueva" : "referencias nuevas" }}
            </p>
          </div>

          <div
            v-if="preview.existing_skus.length > 0 || preview.invalid.length > 0"
            class="grid grid-cols-2 gap-3 text-center"
          >
            <div v-if="preview.existing_skus.length > 0">
              <p class="text-lg font-semibold tabular-nums">
                {{ preview.existing_skus.length }}
              </p>
              <p class="text-xs text-muted-foreground">
                Ya existen
              </p>
            </div>
            <div v-if="preview.invalid.length > 0">
              <p class="text-lg font-semibold tabular-nums text-destructive">
                {{ preview.invalid.length }}
              </p>
              <p class="text-xs text-muted-foreground">
                Inválidas
              </p>
            </div>
          </div>

          <!-- Duplicados: la elección es del usuario, no un default silencioso (D-73). -->
          <div v-if="preview.existing_skus.length > 0" class="flex items-center justify-between gap-4 rounded-md bg-muted px-3 py-2">
            <div class="grid gap-0.5">
              <Label for="skip-existing" class="text-sm">Saltar los que ya existen</Label>
              <p class="text-xs text-muted-foreground">
                Si lo apagas, {{ preview.existing_skus.length }} quedan duplicados —
                elegís cuál te sirve después desde Referencias.
              </p>
            </div>
            <Switch id="skip-existing" v-model="skipExisting" />
          </div>

          <!-- Columnas opcionales ausentes en el .xlsx: esas filas quedan con el
               valor por defecto (Nombre→SKU, Proveedor→placeholder, IVA %→0) en
               vez de rechazarse — el usuario tiene que verlo ANTES de confirmar,
               no descubrirlo en el catálogo después. -->
          <p
            v-if="preview.columns_missing && preview.columns_missing.length > 0"
            class="flex items-start gap-2 text-xs text-muted-foreground"
          >
            <IconAlertTriangle class="mt-0.5 size-3.5 shrink-0" />
            No se encontró columna para: {{ preview.columns_missing.join(", ") }} — esas filas
            quedan con el valor por defecto.
          </p>

          <!-- Columnas del archivo que no corresponden a ningún campo: se
               reportan en vez de descartarse callado, porque una columna mal
               escrita se ve idéntica a una ausente hasta que se dice cuál es. -->
          <p
            v-if="preview.columns_ignored && preview.columns_ignored.length > 0"
            class="flex items-start gap-2 text-xs text-muted-foreground"
          >
            <IconAlertTriangle class="mt-0.5 size-3.5 shrink-0" />
            Columnas que no se reconocen y se ignoran:
            {{ preview.columns_ignored.join(", ") }}.
          </p>

          <div v-if="preview.new_providers.length > 0 || preview.new_categories.length > 0" class="grid gap-1.5 text-sm">
            <p v-if="preview.new_providers.length > 0" class="text-muted-foreground">
              Proveedores nuevos:
              <span v-for="name in preview.new_providers" :key="name" class="inline-block">
                <Badge variant="outline" class="ml-1">{{ name }}</Badge>
              </span>
            </p>
            <p v-if="preview.new_categories.length > 0" class="text-muted-foreground">
              Categorías nuevas:
              <span v-for="name in preview.new_categories" :key="name" class="inline-block">
                <Badge variant="outline" class="ml-1">{{ name }}</Badge>
              </span>
            </p>
          </div>

          <div v-if="preview.invalid.length > 0" class="grid gap-1 text-xs text-muted-foreground">
            <p
              v-for="row in preview.invalid.slice(0, 5)"
              :key="row.index"
            >
              Fila {{ row.index + 1 }}{{ row.sku ? ` (${row.sku})` : "" }}: {{ row.reason }}
            </p>
            <p v-if="preview.invalid.length > 5">
              y {{ preview.invalid.length - 5 }} más…
            </p>
          </div>
        </div>
      </div>

      <DialogFooter v-if="preview">
        <Button
          :disabled="willImportCount === 0 || isImporting"
          class="gap-1.5"
          @click="confirmImport"
        >
          <Spinner v-if="isImporting" class="size-4" />
          {{ isImporting ? "Importando…" : `Importar ${willImportCount} referencias` }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
