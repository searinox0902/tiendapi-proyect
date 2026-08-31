<script setup lang="ts">
import { computed, ref, watch } from "vue"
import { DatePicker } from "v-calendar"
import { IconCalendar, IconX } from "@tabler/icons-vue"
import "v-calendar/style.css"

import { Button } from "@/components/ui/button"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"


const props = defineProps<{
  from?: string
  to?: string
  placeholder?: string
}>()

const emit = defineEmits<{
  "update:from": [value: string | undefined]
  "update:to": [value: string | undefined]
}>()

/** El rango tal como lo maneja V-Calendar: dos `Date` en hora local. */
interface IDateRange {
  start: Date | null
  end: Date | null
}

const open = ref(false)

/** `"2026-08-09"` → `Date` local a medianoche. `null` si viene vacío o mal formado. */
function parse(value: string | undefined): Date | null {
  if (!value) {
    return null
  }
  const [year, month, day] = value.split("-").map(Number)
  if (!year || !month || !day) {
    return null
  }
  return new Date(year, month - 1, day)
}

function serialize(value: Date | null): string | undefined {
  if (value === null) {
    return undefined
  }
  const month = String(value.getMonth() + 1).padStart(2, "0")
  const day = String(value.getDate()).padStart(2, "0")
  return `${value.getFullYear()}-${month}-${day}`
}

const range = ref<IDateRange>({ start: parse(props.from), end: parse(props.to) })

const model = computed(() =>
  range.value.start !== null && range.value.end !== null
    ? { start: range.value.start, end: range.value.end }
    : undefined,
)

/** V-Calendar tipa los extremos como "algo parecido a una fecha"; acá se normaliza a `Date`. */
function toDate(value: unknown): Date | null {
  if (value instanceof Date) {
    return value
  }
  if (typeof value === "string" || typeof value === "number") {
    const parsed = new Date(value)
    return Number.isNaN(parsed.getTime()) ? null : parsed
  }
  return null
}

watch(
  () => [props.from, props.to] as const,
  ([from, to]) => {
    if (serialize(range.value.start) === from && serialize(range.value.end) === to) {
      return
    }
    range.value = { start: parse(from), end: parse(to) }
  },
)

function onRangeChange(value: { start?: unknown, end?: unknown } | null) {
  range.value = { start: toDate(value?.start), end: toDate(value?.end) }
  emit("update:from", serialize(range.value.start))
  emit("update:to", serialize(range.value.end))
  if (range.value.start !== null && range.value.end !== null) {
    open.value = false
  }
}

const formatter = new Intl.DateTimeFormat("es-CO", { day: "2-digit", month: "short" })

function label(value: string | undefined) {
  const parsed = parse(value)
  return parsed === null ? "" : formatter.format(parsed)
}

const hasRange = computed(() => props.from !== undefined || props.to !== undefined)

const displayLabel = computed(() => {
  if (props.from && props.to) {
    return `${label(props.from)} — ${label(props.to)}`
  }
  if (props.from) {
    return `Desde ${label(props.from)}`
  }
  if (props.to) {
    return `Hasta ${label(props.to)}`
  }
  return props.placeholder ?? "Rango de fechas"
})

function clear(event: MouseEvent) {
  //  Sin esto el clic en la "x" abre el popover además de limpiar.
  event.stopPropagation()
  emit("update:from", undefined)
  emit("update:to", undefined)
}
</script>

<template>
  <Popover v-model:open="open">
    <PopoverTrigger as-child>
      <Button
        variant="outline"
        class="w-full justify-start gap-2 font-normal"
        :class="hasRange ? '' : 'text-muted-foreground'"
      >
        <IconCalendar class="size-4 shrink-0" />
        <span class="truncate">{{ displayLabel }}</span>
        <!--
          `role="button"` sobre un span y no un <button>: un <button> dentro de
          otro es HTML inválido y el navegador lo reacomoda fuera del trigger.
        -->
        <span
          v-if="hasRange"
          role="button"
          tabindex="0"
          aria-label="Limpiar rango de fechas"
          class="ml-auto shrink-0 rounded-sm p-0.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          @click="clear"
          @keydown.enter.stop.prevent="clear($event as unknown as MouseEvent)"
        >
          <IconX class="size-3.5" />
        </span>
      </Button>
    </PopoverTrigger>

    <PopoverContent class="w-auto border-none p-0 shadow-none" align="start">

      <DatePicker
        :model-value="model"
        is-range
        is-required
        :columns="2"
        :first-day-of-week="2"
        locale="es-CO"
        color="purple"
        class="tiendapi-calendar"
        @update:model-value="onRangeChange"
      />
    </PopoverContent>
  </Popover>
</template>


<style>

.tiendapi-calendar {

  --vc-accent-50: oklch(0.97 calc(var(--brand-chroma) * 0.1) var(--brand-hue));
  --vc-accent-100: oklch(0.94 calc(var(--brand-chroma) * 0.15) var(--brand-hue));
  --vc-accent-200: oklch(0.89 calc(var(--brand-chroma) * 0.3) var(--brand-hue));
  --vc-accent-300: oklch(0.82 calc(var(--brand-chroma) * 0.5) var(--brand-hue));
  --vc-accent-400: oklch(0.69 calc(var(--brand-chroma) * 0.8) var(--brand-hue));
  --vc-accent-500: var(--primary);
  --vc-accent-600: oklch(0.5 calc(var(--brand-chroma) * 0.95) var(--brand-hue));
  --vc-accent-700: oklch(0.44 calc(var(--brand-chroma) * 0.85) var(--brand-hue));
  --vc-accent-800: oklch(0.37 calc(var(--brand-chroma) * 0.7) var(--brand-hue));
  --vc-accent-900: oklch(0.3 calc(var(--brand-chroma) * 0.55) var(--brand-hue));


  --vc-bg: var(--popover);
  --vc-color: var(--popover-foreground);
  --vc-border: var(--border);
  --vc-hover-bg: var(--accent);
  --vc-focus-ring: 0 0 0 2px color-mix(in oklch, var(--ring) 45%, transparent);

  --vc-header-title-color: var(--foreground);
  --vc-header-arrow-color: var(--muted-foreground);
  --vc-header-arrow-hover-bg: var(--accent);
  --vc-weekday-color: var(--muted-foreground);
  --vc-day-content-hover-bg: var(--accent);
  --vc-day-content-disabled-color: var(--muted-foreground);

  --vc-font-family: inherit;

  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--popover);
}


.tiendapi-calendar .vc-highlight-solid {
  --vc-highlight-solid-content-color: var(--primary-foreground);
}
</style>
