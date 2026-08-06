<script setup lang="ts">
import type { HTMLAttributes } from "vue"
import { onBeforeUnmount, onMounted, ref, watch } from "vue"
import { MaskInput } from "maska"
import type { MaskaDetail } from "maska"
import { cn } from "@/lib/utils"

/**
 * Input de dinero/porcentaje con mask en vivo (maska.js): los dígitos se agrupan
 * de a miles a medida que se escriben (1 → 10 → 100 → 1.000 → 1'000.000,00).
 * Solo el separador entre el grupo de millones y el de miles usa apóstrofe; el
 * resto sigue con punto, igual que el resto de la app. El valor emitido siempre
 * es un string decimal canónico ("1000000.00"), nunca un float, para que
 * Zod/Decimal.js lo consuman sin perder precisión.
 *
 * Si se pasa `max`, cualquier dígito que haga superar ese tope se ignora por
 * completo (el campo se queda en el último valor válido) en vez de recortarlo.
 *
 * Usa un <input> nativo en vez del componente `Input` de shadcn: ese componente
 * trae su propio `v-model` sobre el mismo elemento, y compite con Maska por el
 * control del valor (Maska reprocesa el value y vuelve a disparar "input", lo
 * que hacía que el v-model de `Input` reemitiera el texto YA formateado en vez
 * del valor canónico).
 *
 * `componentField` de VeeValidate trae, además de `modelValue`/`onUpdate:modelValue`,
 * un `onInput`, `onChange` y `onBlur` pensados para inputs nativos sin v-model.
 * Si no se declaran como emits propios, caen por fallthrough directo sobre el
 * `<input>` nativo y leen `event.target.value` — que para cuando el evento llega
 * ya es el texto CON máscara ("200.000"), pisando el valor canónico que emitimos
 * nosotros. Por eso los tres se declaran acá (sin reenviar el evento nativo) para
 * que VeeValidate nunca pueda releer el value directamente del DOM.
 */
const props = defineProps<{
  modelValue?: string | number
  /** Tope opcional (ej. 100 para un porcentaje de IVA). */
  max?: number
  class?: HTMLAttributes["class"]
}>()

const emit = defineEmits<{
  (e: "update:modelValue", value: string): void
  (e: "blur", ...args: any[]): void
  (e: "input", ...args: any[]): void
  (e: "change", ...args: any[]): void
}>()

const inputRef = ref<HTMLInputElement>()
let mask: MaskInput | undefined
let lastEmitted: string | undefined
/** Último texto (formateado) que sí pasó el tope de `max`, para poder revertir a él cuando un dígito nuevo se pasa. */
let lastValidMasked = ""

function applyMillionsSeparator(masked: string): string {
  const [integerPart, decimalPart] = masked.split(",")
  const groups = integerPart.split(".")
  if (groups.length < 3) {
    return masked
  }
  const withApostrophe = `${groups[0]}'${groups.slice(1).join(".")}`
  return decimalPart !== undefined ? `${withApostrophe},${decimalPart}` : withApostrophe
}

function handleMaska(detail: MaskaDetail, el: HTMLInputElement) {
  if (props.max !== undefined && detail.unmasked !== "" && Number(detail.unmasked) > props.max) {
    // El dígito hace superar el tope: se ignora el ingreso, el campo vuelve al último valor válido.
    el.value = lastValidMasked
    return
  }
  lastValidMasked = detail.masked
  lastEmitted = detail.unmasked
  emit("update:modelValue", detail.unmasked)
}

function handleBlur() {
  // Reafirma el valor canónico antes de avisar el blur, para que nadie río abajo
  // termine leyendo el texto con máscara del input como si fuera el valor real.
  if (lastEmitted !== undefined) {
    emit("update:modelValue", lastEmitted)
  }
  emit("blur")
}

onMounted(() => {
  const el = inputRef.value
  if (!el) {
    return
  }
  if (props.modelValue !== undefined && props.modelValue !== "") {
    el.value = String(props.modelValue)
  }
  mask = new MaskInput(el, {
    number: { locale: "es-CO", fraction: 2, unsigned: true },
    postProcess: applyMillionsSeparator,
    onMaska: (detail: MaskaDetail) => handleMaska(detail, el),
  })
})

onBeforeUnmount(() => {
  mask?.destroy()
})

watch(() => props.modelValue, (value) => {
  const el = inputRef.value
  if (!el || !mask) {
    return
  }
  const normalized = value === undefined || value === null || value === "" ? "" : String(value)
  if (normalized === lastEmitted) {
    return
  }
  el.value = normalized
  mask.updateValue(el)
})
</script>

<template>
  <input
    ref="inputRef"
    data-slot="input"
    inputmode="decimal"
    @blur="handleBlur"
    :class="cn(
      'file:text-foreground placeholder:text-muted-foreground selection:bg-primary selection:text-primary-foreground dark:bg-input/30 border-input h-9 w-full min-w-0 rounded-md border bg-transparent px-3 py-1 text-base shadow-xs transition-[color,box-shadow] outline-none disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 md:text-sm',
      'focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-3',
      'aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive',
      props.class,
    )"
  >
</template>
