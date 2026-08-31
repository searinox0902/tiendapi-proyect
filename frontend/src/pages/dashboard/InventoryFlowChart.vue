<script setup lang="ts">
import { computed, ref } from "vue"
import type { EChartsOption } from "echarts"

import { resolveCssColor, useECharts } from "@/composables/useECharts"
import { toDecimal } from "@/lib/money"
import type { IFlowPoint, TBucketGranularity } from "@/api/dashboard/dashboard.types"

/**
 * "Entra vs. sale": unidades ingresadas a bodega contra unidades vendidas.
 *
 * Responde una sola pregunta, y es de plata aunque el eje sea de unidades:
 * **¿estoy comprando más de lo que vendo?** Si la línea de ingresos vive por
 * encima de la de ventas, el inventario crece — y el inventario es plata
 * quieta en un estante. Es el complemento de "Reponer ya", que mira el
 * problema contrario (lo que falta).
 *
 * Las dos series comparten eje y grilla de tiempo con el gráfico de ventas, así
 * que un pico acá se puede leer contra el mismo día allá.
 */
const props = defineProps<{
  flow: IFlowPoint[]
  granularity: TBucketGranularity
}>()

const chartEl = ref<HTMLElement | null>(null)

/** Mismo criterio de rótulo que el gráfico de ventas: los dos comparten grilla. */
function formatBucket(bucket: string): string {
  const date = new Date(bucket)
  if (props.granularity === "hour") {
    return date.toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit", hour12: false })
  }
  const day = date.toLocaleDateString("es-CO", { day: "2-digit", month: "short" })
  return props.granularity === "week" ? `sem. ${day}` : day
}

const totalSold = computed(() =>
  props.flow.reduce((sum, point) => sum.plus(toDecimal(point.sold)), toDecimal(0)),
)
const totalAdded = computed(() =>
  props.flow.reduce((sum, point) => sum + point.added, 0),
)

//  Acá vivía `verdict`: un computed que armaba la frase comparativa
//  ("Entraron 437 unidades más de las que salieron") con la idea de que se
//  leyera antes que los números. Nunca llegó a pintarse en la plantilla y el
//  build lo rechazaba como declaración sin uso. Se retira; está en el
//  historial de git si se quiere retomar — la card hoy muestra solo el par
//  crudo Ingresado/Vendido de la leyenda.

/** Etiquetas de la dimensión `tipo`. Son la clave del filtro y el nombre de la serie: una sola fuente para las dos cosas. */
const INFLOW = "Ingresado a bodega"
const OUTFLOW = "Vendido"

/**
 * Nombre corto para la etiqueta que queda pegada al final de cada línea. El
 * nombre completo se usa en el tooltip y en la leyenda, pero acá compite por
 * el ancho del gráfico: "Ingresado a bodega: 456" obliga a reservarle media
 * cancha al margen derecho.
 */
const SHORT_NAME: Record<string, string> = {
  [INFLOW]: "Entró",
  [OUTFLOW]: "Salió",
}

/**
 * Duración de la "carrera" de las líneas. El ejemplo de ECharts usa 10 s
 * porque dibuja 70 años de datos; acá son 30 puntos y el gráfico se
 * **re-anima en cada cambio de período**, así que 10 s serían una espera en
 * cada clic. Dos segundos alcanzan para que se lea el trazo avanzando.
 */
const RACE_DURATION_MS = 2000

/**
 * Dataset en **formato largo**: una fila por (bucket, tipo, unidades), las dos
 * series apiladas en la misma tabla en vez de dos arrays paralelos.
 *
 * Es la forma que pide el patrón `transform: {type:'filter'}` del ejemplo
 * `data-transform-filter` de ECharts: se entrega **una** fuente cruda y el
 * gráfico deriva cada serie filtrando por una dimensión. La ventaja real sobre
 * pre-separar en JS es que la fuente queda con la misma forma que devuelve el
 * backend, y agregar una tercera serie (por ejemplo "dado de baja") sería una
 * fila más y un filtro más, sin tocar el resto.
 */
const source = computed(() =>
  props.flow.flatMap(point => [
    { bucket: formatBucket(point.bucket), tipo: INFLOW, unidades: point.added },
    { bucket: formatBucket(point.bucket), tipo: OUTFLOW, unidades: Number(point.sold) },
  ]),
)

const option = computed<EChartsOption>(() => {
  const primary = resolveCssColor("--primary", "#9B44C2")
  const muted = resolveCssColor("--muted-foreground", "#71717a")
  const border = resolveCssColor("--border", "#e4e4e7")
  //  Toda la paleta de gráficos del proyecto es del mismo hue púrpura (313.6),
  //  así que dos líneas solo separadas por tono se confunden — y acá
  //  distinguirlas ES el gráfico. Se diferencian además por **trazo**
  //  (punteada vs. sólida), que es lo que exige docs/09 §5: nunca el color
  //  como único indicador. El púrpura primario queda para la venta, que es la
  //  protagónica (regla 90/7/3).
  const inflow = resolveCssColor("--chart-3", "#5b3a7a")

  /** Una serie por tipo, cada una leyendo su dataset ya filtrado. */
  const lineSeries = (name: string, datasetId: string, color: string, dashed: boolean) => ({
    name,
    type: "line" as const,
    datasetId,
    showSymbol: false,
    smooth: true,
    //  `encode` en vez de `data`: le dice a ECharts qué columna del dataset es
    //  el eje X y cuál el valor, igual que en el ejemplo de referencia.
    encode: {
      x: "bucket",
      y: "unidades",
      label: ["tipo", "unidades"],
      itemName: "bucket",
      tooltip: ["unidades"],
    },
    //  Etiqueta pegada a la punta de la línea: es lo que convierte dos líneas
    //  sueltas en una carrera con marcador. Se lee el resultado sin ir a la
    //  leyenda ni pasar el mouse.
    endLabel: {
      show: true,
      color,
      fontSize: 11,
      formatter: (params: { seriesName?: string, value?: unknown }) => {
        const row = params.value as { unidades?: number } | undefined
        return `${SHORT_NAME[params.seriesName ?? ""] ?? params.seriesName} ${row?.unidades ?? 0}`
      },
    },
    //  Con las dos líneas terminando en el mismo valor (días sin movimiento)
    //  las etiquetas quedarían una encima de la otra.
    labelLayout: { moveOverlap: "shiftY" as const },
    //  Al pasar el mouse por una línea, la otra se atenúa. Con dos series es
    //  sutil, pero es lo que permite seguir una sola donde se cruzan.
    emphasis: { focus: "series" as const },
    lineStyle: { color, width: dashed ? 2 : 2.5, type: dashed ? ("dashed" as const) : ("solid" as const) },
    itemStyle: { color },
  })

  return {
    //  La "carrera": las dos líneas se dibujan avanzando en el tiempo en vez
    //  de aparecer completas, que es lo que deja ver en qué momento el ingreso
    //  se despegó de la venta.
    animationDuration: RACE_DURATION_MS,
    dataset: [
      { id: "raw", dimensions: ["bucket", "tipo", "unidades"], source: source.value },
      {
        id: "inflow",
        fromDatasetId: "raw",
        transform: { type: "filter", config: { dimension: "tipo", "=": INFLOW } },
      },
      {
        id: "outflow",
        fromDatasetId: "raw",
        transform: { type: "filter", config: { dimension: "tipo", "=": OUTFLOW } },
      },
    ],
    //  Margen derecho generoso: es donde viven las `endLabel`. Sin él la
    //  etiqueta de la línea queda cortada contra el borde del canvas.
    grid: { left: 8, right: 64, top: 16, bottom: 8, containLabel: true },
    tooltip: {
      trigger: "axis",
      //  Mayor primero: en un gráfico de "entra vs. sale" lo que se busca es
      //  cuál de las dos va ganando ese día, y verlo arriba lo responde solo.
      order: "valueDesc",
      valueFormatter: (value: unknown) => `${Number(value)} u`,
    },
    xAxis: {
      type: "category",
      boundaryGap: false,
      axisLine: { lineStyle: { color: border } },
      axisTick: { show: false },
      axisLabel: { color: muted, fontSize: 11, hideOverlap: true },
    },
    yAxis: {
      type: "value",
      name: "Unidades",
      nameTextStyle: { color: muted, fontSize: 11, align: "left" },
      splitLine: { lineStyle: { color: border, opacity: 0.6 } },
      axisLabel: { color: muted, fontSize: 11 },
    },
    //  Sin `areaStyle` en ninguna de las dos, como el ejemplo de referencia:
    //  lo que hay que leer acá es **dónde se cruzan** las líneas, y dos áreas
    //  del mismo hue superpuestas emborronan justo ese cruce.
    series: [
      lineSeries(INFLOW, "inflow", inflow, true),
      lineSeries(OUTFLOW, "outflow", primary, false),
    ],
  }
})

useECharts(chartEl, option)

const hasMovement = computed(() =>
  props.flow.some(point => point.added > 0 || Number(point.sold) > 0),
)
</script>

<template>
  <div class="rounded-xl border border-border">
    <div class="flex flex-wrap items-end justify-between gap-3 border-b border-border px-5 py-4">
      <div class="min-w-0">
        <p class="text-sm text-muted-foreground">
          Productos: Ingreso vs. venta
        </p>
      </div>

      <div class="flex items-center gap-4 text-xs text-muted-foreground">
        <span class="flex items-center gap-1.5">
          <!-- Punteada, igual que en el gráfico: la leyenda tiene que repetir el trazo, no solo el color. -->
          <span class="w-4 border-t-2 border-dashed border-[var(--chart-3)]" />
          Ingresado ({{ totalAdded }})
        </span>
        <span class="flex items-center gap-1.5">
          <span class="h-0.5 w-4 rounded-full bg-primary" />
          Vendido ({{ totalSold.toDecimalPlaces(0) }})
        </span>
      </div>
    </div>

    <div class="px-2 py-4">
      <div class="relative">
        <div ref="chartEl" class="h-[240px] w-full" />
        <p
          v-if="!hasMovement"
          class="absolute inset-0 flex items-center justify-center bg-card/80 text-sm text-muted-foreground"
        >
          No hubo movimiento de inventario en este período.
        </p>
      </div>
    </div>
  </div>
</template>
