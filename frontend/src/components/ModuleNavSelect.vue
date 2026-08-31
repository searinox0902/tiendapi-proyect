<script setup lang="ts">
import { computed } from "vue"
import { IconLayoutGrid } from "@tabler/icons-vue"
import { useRouter } from "vue-router"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { navGroups, navItems } from "@/config/navigation"

/**
 * Reemplaza el `<h1>` de título en el navbar interno de cada módulo por un
 * selector que actúa como segunda navegación del sidebar: mismo listado,
 * mismos íconos, pero a un clic desde cualquier pantalla.
 *
 * `current` es el `to` (nombre de ruta) del módulo dueño de la pantalla —
 * en subpáginas (detalle, alta/edición) es el módulo padre, no la ruta
 * exacta, para que el selector siempre muestre una opción válida del menú.
 *
 * Es **opcional**: hay pantallas que no pertenecen a ningún módulo del menú
 * —el placeholder de módulo en desarrollo, por ejemplo—, y ahí marcar uno como
 * activo sería mentir sobre dónde está el usuario. Sin `current` el selector
 * sigue sirviendo para navegar, solo que se presenta neutro.
 */
const props = defineProps<{ current?: string }>()

const router = useRouter()

const currentItem = computed(() => navItems.find((item) => item.to === props.current))

function onSelect(value: unknown) {
  if (typeof value === "string" && value !== props.current) {
    router.push({ name: value })
  }
}
</script>

<template>
  <Select :model-value="current" @update:model-value="onSelect">
    <SelectTrigger
      class="w-fit gap-2 border-0 bg-transparent px-2 shadow-none hover:bg-accent focus-visible:ring-2 focus-visible:ring-offset-0"
    >
      <SelectValue>
        <span class="flex items-center gap-2">
          <span class="flex size-6 shrink-0 items-center justify-center rounded-md bg-primary/10">
            <component :is="currentItem?.icon ?? IconLayoutGrid" class="size-4 text-brand-icon" />
          </span>
          <!--
            Sin módulo activo el trigger quedaría vacío —solo el chevron— y se
            leería como un control roto. La etiqueta neutra dice qué hace.
          -->
          <span class="text-base font-medium">{{ currentItem?.title ?? "Ir a un módulo" }}</span>
        </span>
      </SelectValue>
    </SelectTrigger>
    <SelectContent align="start">
      <SelectGroup v-for="(group, index) in navGroups" :key="group.label ?? index">
        <SelectLabel v-if="group.label">{{ group.label }}</SelectLabel>
        <SelectItem v-for="item in group.items" :key="item.to" :value="item.to">
          <span class="flex items-center gap-2">
            <span class="flex size-6 shrink-0 items-center justify-center rounded-md bg-primary/10">
              <component :is="item.icon" class="size-4 text-brand-icon" />
            </span>
            {{ item.title }}
          </span>
        </SelectItem>
      </SelectGroup>
    </SelectContent>
  </Select>
</template>
