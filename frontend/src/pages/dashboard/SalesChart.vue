<script setup lang="ts">
import { computed, ref } from "vue"
import type { EChartsOption } from "echarts"

import { resolveCssColor, useECharts } from "@/composables/useECharts"
import { formatCurrency, toDecimal } from "@/lib/money"
import type { ISalesPoint, TBucketGranularity } from "@/api/dashboard/dashboard.types"

/**
 * Ventas del rango elegido, en barras (D-69).
 *
 * **Por qué barras y no la línea que había:** el eje son días cerrados, no una
 * señal continua. Una línea interpola entre el lunes y el martes y dibuja una
 * pendiente donde no hay nada que medir; la barra dice "este día entraron
 * $X" y no sugiere valores intermedios que no existen.
 *
 * **Sin serie comparativa** (D-69, revierte esa parte de D-66): con rango libre
 * el usuario ya elige explícitamente qué ventana mirar, y "el período anterior"
 * de un rango arbitrario es una ventana que nadie pidió. El tooltip sigue
 * dando la cifra exacta de cada barra, que es lo que aporta ECharts sobre un
 * SVG plano.
 */
const props = defineProps<{
  series: ISalesPoint[]
  granularity: TBucketGranularity
  totalBilled: string
}>()

const chartEl = ref<HTMLElement | null>(null)

/**
 * El rótulo del eje depende del ancho del bucket, que decide el servidor: un
 * día se lee por horas, un rango mediano por fecha, y uno largo por la semana
 * en la que cae (la fecha suelta de un lunes no se distingue de un día común).
 */
function formatBucket(bucket: string): string {
  const date = new Date(bucket)
  if (props.granularity === "hour") {
    return date.toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit", hour12: false })
  }
  const day = date.toLocaleDateString("es-CO", { day: "2-digit", month: "short" })
  return props.granularity === "week" ? `sem. ${day}` : day
}

/**
 * Los montos van a ECharts como `number` porque el gráfico calcula
 * coordenadas, no dinero. Toda cifra que el usuario **lee** —el titular y el
 * tooltip— se formatea con `Decimal` vía `formatCurrency`.
 */
const option = computed<EChartsOption>(() => {
  const primary = resolveCssColor("--primary", "#9B44C2")
  const muted = resolveCssColor("--muted-foreground", "#71717a")
  const border = resolveCssColor("--border", "#e4e4e7")

  return {
    grid: { left: 8, right: 16, top: 16, bottom: 8, containLabel: true },
    tooltip: {
      trigger: "axis",
      //  `shadow` y no la línea vertical por defecto: en barras, resaltar la
      //  columna entera dice qué barra se está leyendo; una línea a mitad de
      //  camino entre dos barras deja la duda.
      axisPointer: { type: "shadow" },
      formatter: (params: unknown) => {
        const rows = params as { axisValue: string, value: number }[]
        const row = rows[0]
        if (row === undefined) {
          return ""
        }
        return `<div style="font-size:12px">
                  <div style="margin-bottom:4px;opacity:.7">${row.axisValue}</div>
                  <strong>${formatCurrency(toDecimal(row.value))}</strong>
                </div>`
      },
    },
    xAxis: {
      type: "category",
      data: props.series.map(point => formatBucket(point.bucket)),
      axisLine: { lineStyle: { color: border } },
      axisTick: { show: false },
      //  `hideOverlap` es lo que salva el eje cuando el rango trae 60 barras:
      //  ECharts va salteando rótulos en vez de encimarlos.
      axisLabel: { color: muted, fontSize: 11, hideOverlap: true },
    },
    yAxis: {
      type: "value",
      splitLine: { lineStyle: { color: border, opacity: 0.6 } },
      axisLabel: {
        color: muted,
        fontSize: 11,
        //  Miles en "k" y millones en "M": el eje con la cifra completa
        //  ($ 1.630.950,00) se come el ancho del gráfico.
        formatter: (value: number) => {
          if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
          if (value >= 1_000) return `${Math.round(value / 1_000)}k`
          return String(value)
        },
      },
    },
    series: [
      {
        name: "Ventas",
        type: "bar",
        data: props.series.map(point => Number(point.total)),
        itemStyle: {
          color: primary,
          //  Redondeo solo arriba: la base de la barra tiene que apoyar plana
          //  sobre el eje o parece flotar.
          borderRadius: [3, 3, 0, 0],
        },
        //  Techo al ancho: con un rango de 2 o 3 días, barras al 60% del
        //  gráfico se leen como bloques de color, no como una medida.
        barMaxWidth: 44,
        emphasis: { itemStyle: { color: primary, opacity: 0.85 } },
      },
    ],
  }
})

useECharts(chartEl, option)

/** El titular: la única cifra que el Dashboard comparte con Facturación (D-66). */
const totalDisplay = computed(() => formatCurrency(toDecimal(props.totalBilled)))

/** Sin una sola venta no se dibuja un eje en cero: se dice. */
const hasSales = computed(() => props.series.some(point => Number(point.total) > 0))
</script>

<template>
  <div class="rounded-xl border border-border">
    <div class="flex flex-wrap items-end justify-between gap-3 border-b border-border px-5 py-4">
      <div>
        <p class="text-sm text-muted-foreground">
          Ventas del período
        </p>
        <p class="text-2xl font-bold tabular-nums text-brand-icon">
          {{ totalDisplay }}
        </p>
      </div>
    </div>

    <div class="px-2 py-4">
      <!--
        El canvas se monta SIEMPRE (aunque no haya ventas) y el aviso va encima:
        con un `v-if` el div desaparece del DOM, ECharts pierde su contenedor y
        al volver a haber datos monta sobre un elemento de alto cero.
      -->
      <div class="relative">
        <div ref="chartEl" class="h-[240px] w-full" />
        <p
          v-if="!hasSales"
          class="absolute inset-0 flex items-center justify-center bg-card/80 text-sm text-muted-foreground"
        >
          No hubo ventas en este período.
        </p>
      </div>
    </div>
  </div>
</template>
