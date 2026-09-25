<script setup lang="ts">
import { IconSearch } from "@tabler/icons-vue"

import { Input } from "@/components/ui/input"

/**
 * Campo de búsqueda de personas, con su encabezado y contador.
 *
 * Existe para que los modales del módulo no diverjan en los detalles chicos —
 * el ícono, el alto, el texto del placeholder, dónde va el contador. Son
 * decisiones que nadie recuerda replicar y que se notan cuando no coinciden.
 */

defineProps<{
  label: string
  /** Cuántos se ven ahora y cuántos hay en total. */
  shown: number
  total: number
  isFiltering: boolean
}>()

const model = defineModel<string>({ required: true })
</script>

<template>
  <div class="space-y-2">
    <p class="text-xs font-medium text-muted-foreground">
      {{ label }}
      <span v-if="isFiltering" class="font-normal">· {{ shown }} de {{ total }}</span>
    </p>

    <div class="relative">
      <IconSearch
        class="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
      />
      <Input v-model="model" placeholder="Buscar persona o cargo" class="h-9 pl-8" />
    </div>
  </div>
</template>
