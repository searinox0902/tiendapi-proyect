<script setup lang="ts">
import { ref } from "vue"
import { IconFileSpreadsheet, IconFileUpload, IconJson } from "@tabler/icons-vue"
import { Button } from "@/components/ui/button"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"

/**
 * Igual que el popover "Importar" de Referencias: el usuario elige el
 * formato ANTES de que se abra el navegador de archivos del sistema, así el
 * picker queda filtrado a esa extensión en vez de mezclar las dos.
 */
const FORMATS = [
  {
    value: "json",
    label: "JSON",
    hint: "El que exporta el propio sistema",
    icon: IconJson,
    accept: "application/json,.json",
  },
  {
    value: "xlsx",
    label: "Excel",
    hint: "La plantilla .xlsx exportada",
    icon: IconFileSpreadsheet,
    accept: ".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  },
] as const

const emit = defineEmits<{ pick: [accept: string] }>()

const open = ref(false)

function pick(option: (typeof FORMATS)[number]) {
  open.value = false
  emit("pick", option.accept)
}
</script>

<template>
  <Popover v-model:open="open">
    <PopoverTrigger as-child>
      <Button size="icon-sm" variant="ghost" title="Importar">
        <IconFileUpload class="size-4" />
      </Button>
    </PopoverTrigger>
    <PopoverContent align="end" class="w-72">
      <div class="grid gap-1">
        <Button
          v-for="option in FORMATS"
          :key="option.value"
          variant="ghost"
          class="h-auto w-full justify-start gap-3 whitespace-normal px-2 py-2"
          @click="pick(option)"
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
