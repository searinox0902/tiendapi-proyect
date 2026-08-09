<script setup lang="ts">
import { computed } from "vue"
import { useClipboard } from "@vueuse/core"
import {
  IconCheck,
  IconCopy,
  IconDotsVertical,
  IconMapPin,
  IconPencil,
  IconRotate,
  IconTrash,
} from "@tabler/icons-vue"
import { toast } from "vue-sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { formatCurrency, toDecimal } from "@/lib/money"
import type { IItemExistence } from "@/api/items/items.types"

const props = defineProps<{ existence: IItemExistence; selected: boolean }>()

const emit = defineEmits<{
  "update:selected": [value: boolean]
  edit: [existence: IItemExistence]
  remove: [existence: IItemExistence]
  /** Dar de baja / activar es el mismo verbo con dos direcciones — el padre decide cuál según `existence.status`. */
  "toggle-status": [existence: IItemExistence]
}>()

/**
 * El ID de la unidad física es lo que el cajero teclea para vender/descontar
 * una existencia puntual (D-41/A-22), así que copiarlo es la acción más
 * frecuente de esta card — no un adorno.
 */
const { copy, copied, isSupported } = useClipboard({ copiedDuring: 1500 })

function copyId() {
  copy(props.existence.item_id)
  toast.success("ID de producto copiado", { position: "bottom-center" })
}

/** El monto de IVA se deriva del precio base y el porcentaje — nunca se guarda pre-calculado. */
const ivaAmount = computed(() =>
  toDecimal(props.existence.base_price)
    .times(toDecimal(props.existence.iva_percentage))
    .dividedBy(100),
)

/**
 * El backend manda `Numeric(5,2)`, o sea "19.00". En el rótulo se muestra "19%":
 * los ceros de la escala del tipo no son precisión que le sirva a nadie leyendo.
 * `Decimal` de por medio, sin `parseFloat`.
 */
const ivaLabel = computed(() => toDecimal(props.existence.iva_percentage).toString())

function formatPrice(value: string) {
  return formatCurrency(toDecimal(value))
}

const isDeBaja = computed(() => props.existence.status === "de_baja")

/**
 * Solo se pinta badge para estados que no son el default esperado
 * ("disponible"): una tarjeta común no necesita gritar que está disponible,
 * pero "de baja" sí exige saltar a la vista antes de mirar cualquier otro dato.
 */
const statusLabel = computed(() => {
  switch (props.existence.status) {
    case "de_baja": return "De baja"
    case "vendido": return "Vendido"
    case "reservado": return "Reservado"
    default: return null
  }
})
</script>

<template>
  <div
    class="flex flex-wrap items-center gap-x-4 gap-y-3 rounded-lg border bg-card px-4 py-3"
    :class="isDeBaja ? 'border-destructive/40 bg-destructive/5' : 'border-border'"
  >
    <Checkbox
      :model-value="selected"
      class="shrink-0"
      :aria-label="`Seleccionar ${existence.item_id}`"
      @update:model-value="(value) => emit('update:selected', value === true)"
    />

    <!-- Identidad de la unidad -->
    <div class="min-w-44 flex-1">
      <div class="flex items-center gap-2">
        <p class="text-sm font-medium">
          ID Producto
        </p>
        <Badge v-if="statusLabel" variant="destructive" class="px-1.5 py-0 text-[10px]">
          {{ statusLabel }}
        </Badge>
      </div>
      <button
        v-if="isSupported"
        type="button"
        class="flex max-w-full items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"
        @click="copyId"
      >
        <IconCheck v-if="copied" class="size-3.5 shrink-0 text-primary" />
        <IconCopy v-else class="size-3.5 shrink-0" />
        <span class="truncate font-mono">{{ existence.item_id }}</span>
      </button>
      <span v-else class="truncate font-mono text-xs text-muted-foreground">
        {{ existence.item_id }}
      </span>
    </div>

    <!--
      Proveedor y dónde está físicamente. Ambos opcionales (migración 0005):
      el alta manual rápida no exige elegirlos en el momento de crear la
      existencia — "Sin asignar" en gris avisa que falta completarlo, no que
      el dato se perdió.
    -->
    <div class="min-w-48 flex-1 border-l border-border pl-4">
      <p
        class="truncate text-sm font-semibold"
        :class="existence.provider_name === null ? 'text-muted-foreground font-normal' : ''"
      >
        {{ existence.provider_name ?? "Sin proveedor asignado" }}
      </p>
      <p class="flex items-center gap-1 text-xs text-muted-foreground">
        <IconMapPin class="size-3.5 shrink-0" />
        <span class="truncate">{{ existence.location_name ?? "Sin ubicación asignada" }}</span>
      </p>
    </div>

    <!-- Cifras: tabular-nums para que las columnas queden alineadas entre cards -->
    <div class="min-w-24 border-l border-border pl-4">
      <p class="text-xs text-muted-foreground">
        IVA {{ ivaLabel }}%
      </p>
      <p class="text-sm font-semibold tabular-nums">
        {{ formatCurrency(ivaAmount) }}
      </p>
    </div>

    <div class="min-w-28">
      <p class="text-xs text-muted-foreground">
        Precio Proveedor
      </p>
      <p
        class="text-sm font-semibold tabular-nums"
        :class="existence.provider_price === null ? 'text-muted-foreground' : ''"
      >
        {{ existence.provider_price === null ? "—" : formatPrice(existence.provider_price) }}
      </p>
    </div>

    <div class="min-w-28">
      <p class="text-xs text-muted-foreground">
        Precio Base
      </p>
      <p class="text-sm font-semibold tabular-nums">
        {{ formatPrice(existence.base_price) }}
      </p>
    </div>

    <div class="min-w-28">
      <p class="text-xs text-muted-foreground">
        Precio Venta
      </p>
      <p class="text-sm font-semibold tabular-nums">
        {{ formatPrice(existence.sale_price) }}
      </p>
    </div>

    <Popover>
      <PopoverTrigger as-child>
        <Button variant="ghost" size="icon" class="size-8 shrink-0">
          <IconDotsVertical class="size-4" />
          <span class="sr-only">Acciones para {{ existence.item_id }}</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" class="w-44 p-1">
        <Button variant="ghost" class="w-full justify-start gap-2" @click="emit('edit', existence)">
          <IconPencil class="size-4" />
          Editar
        </Button>
        <Button variant="ghost" class="w-full justify-start gap-2" @click="emit('toggle-status', existence)">
          <IconRotate class="size-4" />
          {{ isDeBaja ? "Activar" : "Dar de baja" }}
        </Button>
        <Button
          variant="ghost"
          class="w-full justify-start gap-2 text-destructive hover:text-destructive"
          @click="emit('remove', existence)"
        >
          <IconTrash class="size-4" />
          Eliminar
        </Button>
      </PopoverContent>
    </Popover>
  </div>
</template>
