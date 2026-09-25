<script setup lang="ts">
import { ref } from "vue"
import { IconDots } from "@tabler/icons-vue"

import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Separator } from "@/components/ui/separator"
import { DAY_ACTIONS } from "./dayActions"
import type { IDayAction } from "./dayActions"

/**
 * Botón "..." flotante de cada día.
 *
 * Vive en la esquina superior derecha, **reemplazando los chips de Hoy y
 * Festivo en hover**: es el único punto de la celda donde un botón no le quita
 * sitio a algo que se esté leyendo en ese momento — los chips son contexto y
 * el botón es acción, y mientras el cursor está encima manda la acción.
 *
 * Separa dos intenciones que antes estaban confundidas: **el "..." actúa, la
 * celda lee.** Antes cualquier clic abría un formulario, en una pantalla cuyo
 * trabajo principal es mirar.
 */

withDefaults(
  defineProps<{
    /** Fecha ISO del día — solo para la etiqueta accesible. */
    date: string
    /**
     * `cell` aparece en hover, porque en la grilla el botón compite con el
     * contenido que se está leyendo. `standalone` va siempre visible: dentro de
     * un modal no hay nada de qué esconderse y un botón invisible no se
     * encuentra.
     */
    variant?: "cell" | "standalone"
  }>(),
  { variant: "cell" },
)

const emit = defineEmits<{
  select: [action: IDayAction]
}>()

const open = ref(false)

function choose(action: IDayAction) {
  open.value = false
  emit("select", action)
}
</script>

<template>
  <Popover v-model:open="open">
    <PopoverTrigger as-child>
      <button
        type="button"
        :aria-label="`Acciones del ${date}`"
        class="text-muted-foreground transition hover:text-foreground focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        :class="[
          /*
            En la celda es una pista discreta que compite con el contenido; en
            un modal es el control principal de la pantalla y tiene que pesar
            como tal — un botón de 14px dentro de un diálogo se lee a medio
            terminar.
          */
          variant === 'standalone'
            ? 'flex size-10 items-center justify-center rounded-lg border border-border hover:bg-accent'
            : 'rounded-md bg-accent p-0.5 hover:bg-accent-foreground/10',
          variant === 'standalone' || open ? 'opacity-100' : 'opacity-0 group-hover:opacity-100',
        ]"
        @click.stop
      >
        <IconDots :class="variant === 'standalone' ? 'size-5' : 'size-3.5'" />
      </button>
    </PopoverTrigger>

    <PopoverContent align="end" class="w-64 p-1" @click.stop>
      <template v-for="action in DAY_ACTIONS" :key="action.id">
        <!-- Los grupos se separan con una línea, sin títulos: tres bloques de
             dos a cuatro ítems se leen solos y un encabezado por grupo sería
             más texto que contenido. -->
        <Separator v-if="action.startsGroup" class="my-1" />
        <button
          type="button"
          class="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm transition hover:bg-accent focus-visible:bg-accent focus-visible:outline-none"
          @click="choose(action)"
        >
          <component :is="action.icon" class="size-4 shrink-0 text-muted-foreground" />
          {{ action.label }}
        </button>
      </template>
    </PopoverContent>
  </Popover>
</template>
