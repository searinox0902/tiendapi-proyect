<script setup lang="ts">
import { computed, ref } from "vue"
import { IconAlertTriangle, IconFile } from "@tabler/icons-vue"
import axios from "axios"
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
import { Label } from "@/components/ui/label"
import { Spinner } from "@/components/ui/spinner"
import { Switch } from "@/components/ui/switch"
import { directoryIOApi } from "@/api/directory/directoryIO.api"
import type { IDirectoryImportPreview, TDirectoryEntity } from "@/api/directory/directoryIO.types"


const props = defineProps<{ entity: TDirectoryEntity, entityLabel: string }>()

const emit = defineEmits<{ imported: [] }>()

const open = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)
const fileName = ref("")
const selectedFile = ref<File | null>(null)
const preview = ref<IDirectoryImportPreview | null>(null)
const isPreviewing = ref(false)
const isImporting = ref(false)
/** Unicidad blanda (D-73): por defecto se saltan los que ya existen. */
const skipExisting = ref(true)
const errorMessage = ref("")

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

const fileTypeLabel = computed(() =>
  fileName.value.toLowerCase().endsWith(".xlsx") ? "Excel" : "JSON",
)

async function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
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
    const { data } = await directoryIOApi.previewImport(props.entity, file)
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
    const { data } = await directoryIOApi.importEntity(props.entity, selectedFile.value, skipExisting.value)
    open.value = false
    emit("imported")

    const summary = [`${data.created} creados`]
    if (data.skipped > 0) {
      summary.push(`${data.skipped} saltados`)
    }
    if (data.invalid > 0) {
      summary.push(`${data.invalid} inválidos`)
    }

    const batchId = data.batch_id
    toast.success(summary.join(" · "), {
      position: "bottom-center",
      action: batchId
        ? { label: "Deshacer", onClick: () => undoImport(batchId) }
        : undefined,
    })
  } catch (error) {
    console.error("Import failed:", error)
    toast.error("No se pudo importar", { position: "bottom-center" })
  } finally {
    isImporting.value = false
  }
}

async function undoImport(batchId: string) {
  try {
    await directoryIOApi.undoImportBatch(props.entity, batchId)
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
        <DialogTitle>Importar {{ entityLabel }}</DialogTitle>
        <DialogDescription>
          Acepta JSON o el Excel exportado por el sistema. Suma nuevos, nunca reemplaza.
        </DialogDescription>
      </DialogHeader>

      <div class="grid gap-4">
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
          <div class="rounded-lg bg-primary/10 px-4 py-3 text-center">
            <p class="text-3xl font-bold tabular-nums text-brand-icon">
              +{{ preview.new_count }}
            </p>
            <p class="text-sm text-muted-foreground">
              {{ preview.new_count === 1 ? "nuevo" : "nuevos" }}
            </p>
          </div>

          <div
            v-if="preview.existing_keys.length > 0 || preview.invalid.length > 0"
            class="grid grid-cols-2 gap-3 text-center"
          >
            <div v-if="preview.existing_keys.length > 0">
              <p class="text-lg font-semibold tabular-nums">
                {{ preview.existing_keys.length }}
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
                Inválidos
              </p>
            </div>
          </div>

          <div v-if="preview.existing_keys.length > 0" class="flex items-center justify-between gap-4 rounded-md bg-muted px-3 py-2">
            <div class="grid gap-0.5">
              <Label for="skip-existing" class="text-sm">Saltar los que ya existen</Label>
              <p class="text-xs text-muted-foreground">
                Si lo apagas, {{ preview.existing_keys.length }} quedan duplicados.
              </p>
            </div>
            <Switch id="skip-existing" v-model="skipExisting" />
          </div>

          <div v-if="preview.invalid.length > 0" class="grid gap-1 text-xs text-muted-foreground">
            <p
              v-for="row in preview.invalid.slice(0, 5)"
              :key="row.index"
            >
              {{ row.key_value ?? `Fila ${row.index + 1}` }}: {{ row.reason }}
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
          {{ isImporting ? "Importando…" : `Importar ${willImportCount}` }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
