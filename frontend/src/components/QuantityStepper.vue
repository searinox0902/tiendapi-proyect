<script setup lang="ts">
import { ref, watch } from "vue"
import { IconMinus, IconPlus } from "@tabler/icons-vue"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

/**
 * Botonera de cantidad: `(-) [número editable] (+)`.
 *
 * Patrón compartido de toda la app — nace en `CreateStockUnitDialog.vue` (alta
 * de existencias por lote) y esta es su versión reusable, mismo
 * comportamiento: los botones dan pasos de a uno, pero el número **siempre se
 * puede teclear directo**, porque para una cantidad grande (30, 50…) escribirla
 * gana por lejos a hacer 30 clics. Cualquier botonera de cantidad nueva debería
 * salir de acá en vez de reinventar el patrón.
 */
const props = withDefaults(defineProps<{
  modelValue: number
  min?: number
  max?: number
  disabled?: boolean
  /** `xs` es la botonera compacta de una fila de lista (ej. carrito); el tamaño por defecto es el de un formulario. */
  size?: "xs" | "default"
}>(), {
  min: 1,
  max: undefined,
  disabled: false,
  size: "default",
})

const emit = defineEmits<{
  "update:modelValue": [value: number]
}>()

/**
 * Texto tal cual lo escribe el usuario, separado del número real: así se
 * puede dejar el input momentáneamente vacío mientras se retipea (borrar "1"
 * para escribir "30") sin que cada tecla dispare un clamp que lo devuelva a
 * "1" a medio camino.
 */
const textInput = ref(String(props.modelValue))

//  Si el número cambia desde afuera (otro botón, otra fila) el texto se
//  resincroniza — pero no si el cambio vino de acá mismo, para no pisarle al
//  usuario lo que está tecleando.
watch(() => props.modelValue, (value) => {
  if (Number(textInput.value) !== value) {
    textInput.value = String(value)
  }
})

function clamp(value: number) {
  const withMax = props.max === undefined ? value : Math.min(value, props.max)
  return Math.max(props.min, withMax)
}

watch(textInput, (raw) => {
  const parsed = Math.trunc(Number(raw))
  const isValid = raw !== "" && Number.isInteger(parsed) && parsed === Number(raw)
  if (isValid && parsed >= props.min && (props.max === undefined || parsed <= props.max)) {
    emit("update:modelValue", parsed)
  }
})

/** Al salir del campo, lo que haya quedado (vacío, 0, fuera de rango) se corrige al último valor válido. */
function normalize() {
  textInput.value = String(props.modelValue)
}

function decrement() {
  emit("update:modelValue", clamp(props.modelValue - 1))
}

function increment() {
  emit("update:modelValue", clamp(props.modelValue + 1))
}
</script>

<template>
  <div class="flex items-center" :class="size === 'xs' ? 'gap-1' : 'gap-2'">
    <Button
      type="button"
      variant="outline"
      :size="size === 'xs' ? 'icon-xs' : 'icon'"
      :disabled="disabled || modelValue <= min"
      :aria-label="'Disminuir cantidad'"
      @click="decrement"
    >
      <IconMinus />
    </Button>
    <Input
      v-model="textInput"
      type="number"
      inputmode="numeric"
      :min="min"
      :max="max"
      :disabled="disabled"
      :class="size === 'xs'
        ? 'h-6 w-12 px-1 text-center text-xs font-medium tabular-nums'
        : 'w-20 text-center text-lg font-semibold tabular-nums'"
      @blur="normalize"
    />
    <Button
      type="button"
      variant="outline"
      :size="size === 'xs' ? 'icon-xs' : 'icon'"
      :disabled="disabled || (max !== undefined && modelValue >= max)"
      :aria-label="'Aumentar cantidad'"
      @click="increment"
    >
      <IconPlus />
    </Button>
  </div>
</template>
