<script setup lang="ts">
import { computed, ref } from "vue"
import { IconCheck, IconSelector } from "@tabler/icons-vue"

import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { cn } from "@/lib/utils"
import type { IEmployee } from "./payroll.types"

/**
 * Selector de persona: un combobox, no una lista abierta.
 *
 * Reemplaza al par buscador + lista con scroll. Aquella versión funcionaba pero
 * **se comía el formulario**: ocupaba la mitad del alto del modal para resolver
 * una sola pregunta, y empujaba hacia abajo los campos que venían después.
 * Colapsado, el formulario vuelve a leerse de un vistazo.
 *
 * **Por qué acá sí `Command`, si `ReferenceSearchInput` lo descartó.** Ese
 * componente lo rechazó porque `CommandInput` filtra en el cliente sobre lo ya
 * montado, y las Referencias son miles que llegan paginadas del servidor. Acá
 * pasa lo contrario: el equipo es una **lista cerrada** de 3 a 50 personas que
 * ya está en memoria — exactamente el caso para el que ese comentario dice que
 * `Command` sirve.
 *
 * Y resuelve gratis dos cosas que antes estaban a mano: `useFilter` corre con
 * `sensitivity: "base"`, que **ignora tildes y mayúsculas** (teclear "andres"
 * encuentra a Andrés), y el filtro compara contra el **texto renderizado** del
 * ítem, así que buscar por cargo —"bodega"— funciona sin configurar nada.
 */

const props = defineProps<{
  employees: IEmployee[]
  placeholder?: string
  /**
   * Agrega "Todos" como primera opción, con valor `null`.
   *
   * Filtrando el calendario, "todos" es una respuesta legítima y además la de
   * partida — no es "sin elegir". Por eso va dentro de la lista y no como un
   * botón de limpiar al lado: son opciones del mismo eje.
   */
  allowAll?: boolean
}>()

const model = defineModel<string | null>({ required: true })

const open = ref(false)

const selected = computed(
  () => props.employees.find((employee) => employee.id === model.value) ?? null,
)

function choose(id: string | null) {
  model.value = id
  open.value = false
}
</script>

<template>
  <Popover v-model:open="open">
    <PopoverTrigger as-child>
      <button
        type="button"
        role="combobox"
        :aria-expanded="open"
        class="flex h-12 w-full items-center justify-between gap-2 rounded-md border border-input bg-transparent px-2 text-left transition hover:bg-accent/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <!-- El trigger muestra la misma fila que la lista: avatar, nombre y
             cargo. Así lo elegido se ve igual que como se eligió. -->
        <span v-if="selected" class="flex min-w-0 items-center gap-2.5">
          <Avatar class="size-7 shrink-0">
            <AvatarFallback class="bg-muted text-[10px] font-medium">
              {{ selected.initials }}
            </AvatarFallback>
          </Avatar>
          <span class="min-w-0">
            <span class="block truncate text-sm font-medium">{{ selected.name }}</span>
            <span class="block truncate text-xs text-muted-foreground">{{ selected.role }}</span>
          </span>
        </span>

        <span v-else-if="allowAll" class="pl-1 text-sm font-medium">Todos</span>

        <span v-else class="pl-1 text-sm text-muted-foreground">
          {{ placeholder ?? "Selecciona a la persona" }}
        </span>

        <IconSelector class="size-4 shrink-0 text-muted-foreground" />
      </button>
    </PopoverTrigger>

    <PopoverContent class="w-(--reka-popover-trigger-width) p-0" align="start">
      <Command>
        <CommandInput placeholder="Buscar persona o cargo" />
        <CommandEmpty>Nadie coincide.</CommandEmpty>
        <CommandList>
          <CommandGroup>
            <CommandItem v-if="allowAll" value="Todos" class="gap-2.5 py-2" @select="choose(null)">
              <span class="min-w-0 flex-1 text-sm font-medium">Todos</span>
              <IconCheck :class="cn('size-4 shrink-0', model === null ? 'opacity-100' : 'opacity-0')" />
            </CommandItem>
            <CommandItem
              v-for="employee in employees"
              :key="employee.id"
              :value="employee.id"
              class="gap-2.5 py-2"
              @select="choose(employee.id)"
            >
              <Avatar class="size-7 shrink-0">
                <AvatarFallback class="bg-muted text-[10px] font-medium">
                  {{ employee.initials }}
                </AvatarFallback>
              </Avatar>
              <span class="min-w-0 flex-1">
                <span class="block truncate text-sm font-medium">{{ employee.name }}</span>
                <span class="block truncate text-xs text-muted-foreground">{{ employee.role }}</span>
              </span>
              <IconCheck
                :class="cn('size-4 shrink-0', model === employee.id ? 'opacity-100' : 'opacity-0')"
              />
            </CommandItem>
          </CommandGroup>
        </CommandList>
      </Command>
    </PopoverContent>
  </Popover>
</template>
