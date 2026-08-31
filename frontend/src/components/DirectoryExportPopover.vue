<script setup lang="ts">
import { ref } from "vue"
import { IconDownload, IconFileSpreadsheet, IconJson, IconMarkdown } from "@tabler/icons-vue"
import { toast } from "vue-sonner"
import { Button } from "@/components/ui/button"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { directoryIOApi } from "@/api/directory/directoryIO.api"
import type { TDirectoryEntity, TDirectoryExportFormat } from "@/api/directory/directoryIO.types"
import { downloadBlob } from "@/lib/download"
const props = defineProps<{ entity: TDirectoryEntity }>()

const FORMATS = [
  { value: "xlsx", label: "Excel", hint: "Hoja de cálculo (.xlsx)", icon: IconFileSpreadsheet },
  { value: "json", label: "JSON", hint: "El que se puede volver a importar", icon: IconJson },
  { value: "markdown", label: "Markdown", hint: "Tabla para leer o pegar (.md)", icon: IconMarkdown },
] as const

const open = ref(false)
const isExporting = ref(false)

async function download(format: TDirectoryExportFormat) {
  if (isExporting.value) {
    return
  }
  isExporting.value = true
  try {
    const { data, headers } = await directoryIOApi.exportEntity(props.entity, format)
    //  El nombre lo decide el backend (lleva la fecha); si `Content-Disposition`
    //  no viaja, el navegador bautiza la descarga con el nombre del endpoint.
    downloadBlob(data, headers, `export.${format === "markdown" ? "md" : format}`)
    open.value = false
  } catch (error) {
    console.error("Directory export failed:", error)
    toast.error("No se pudo exportar", { position: "bottom-center" })
  } finally {
    isExporting.value = false
  }
}
</script>

<template>
  <Popover v-model:open="open">
    <PopoverTrigger as-child>
      <Button size="icon-sm" variant="ghost" title="Exportar">
        <IconDownload class="size-4" />
      </Button>
    </PopoverTrigger>
    <PopoverContent align="end" class="w-72">
      <div class="grid gap-1">
        <Button
          v-for="option in FORMATS"
          :key="option.value"
          variant="ghost"
          class="h-auto w-full justify-start gap-3 whitespace-normal px-2 py-2"
          :disabled="isExporting"
          @click="download(option.value)"
        >
          <component :is="option.icon" class="size-4 shrink-0 text-brand-icon" />
          <span class="grid min-w-0 gap-0.5 text-left">
            <span class="text-sm font-medium">{{ option.label }}</span>
            <span class="text-xs font-normal text-muted-foreground">{{ option.hint }}</span>
          </span>
        </Button>
      </div>
    </PopoverContent>
  </Popover>
</template>
