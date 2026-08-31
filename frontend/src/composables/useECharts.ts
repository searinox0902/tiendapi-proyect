import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import type { Ref } from "vue";
import { isDark, theme } from "@/composables/useTheme";
import * as echarts from "echarts/core";
import { BarChart, LineChart } from "echarts/charts";
import {
  DatasetComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  TransformComponent,
} from "echarts/components";
import { LabelLayout } from "echarts/features";
import { CanvasRenderer } from "echarts/renderers";
import type { EChartsOption } from "echarts";

/**
 * Importación selectiva y no `import * as echarts from "echarts"`: el paquete
 * completo trae todos los tipos de gráfico (mapas, gauges, sankey…) y pesa
 * más de 1 MB. Acá solo se usan líneas, así que se registran los módulos
 * necesarios. Importa de verdad porque el empaquetado es un instalable Tauri
 * (D-29/D-31): todo lo que entre al bundle viaja al equipo del cliente.
 */
echarts.use([
  LineChart,
  //  Ventas va en barras (D-69): un período es un conjunto de días cerrados,
  //  y la línea sugería una continuidad entre ellos que no existe.
  BarChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  //  `DatasetComponent` + `TransformComponent` habilitan el patrón
  //  `dataset` + `transform: {type:'filter'}` que usa "Entra vs. sale". Si
  //  faltan, el gráfico monta sin series y ECharts solo deja un warning
  //  discreto en consola — no un error.
  DatasetComponent,
  TransformComponent,
  //  `LabelLayout` es lo que hace funcionar `labelLayout: {moveOverlap}` en el
  //  patrón "Line Race": sin registrarlo la opción se ignora sin decir nada y
  //  las etiquetas del final de cada línea se pisan entre sí.
  LabelLayout,
  CanvasRenderer,
]);

/**
 * Contador que sube en cada cambio de tema de color o de modo claro/oscuro.
 *
 * Existe porque `resolveCssColor` lee `getComputedStyle` **una vez**, en el
 * momento en que se evalúa el `computed` de la opción. Vue no tiene forma de
 * enterarse de que una variable CSS cambió de valor, así que sin esta señal el
 * gráfico se quedaba pintado con el color del tema anterior hasta que algo
 * más —cambiar de período, por ejemplo— invalidara el `computed`. Se nota
 * fuerte al pasar a Obsidiana en oscuro: el primario pasa a blanco en toda la
 * interfaz y las barras seguían negras sobre fondo negro.
 *
 * No hace falta tocarlo desde los gráficos: `resolveCssColor` ya lo lee, así
 * que todo `computed` que resuelva un color queda suscrito solo.
 */
export const themeRevision = ref(0);

/**
 * `flush: "post"` + `nextTick` no son redundantes por gusto: el atributo
 * `data-theme` y la clase `dark` los escriben otros watchers sobre <html>, y
 * si el contador subiera antes que ellos, `getComputedStyle` devolvería
 * justamente el color viejo que se está tratando de reemplazar.
 */
watch(
  [isDark, theme],
  () => {
    void nextTick(() => {
      themeRevision.value += 1;
    });
  },
  { flush: "post" },
);

/**
 * Resuelve una variable CSS del tema a un color concreto.
 *
 * ECharts pinta sobre canvas y **no entiende `var(--primary)`**: recibe el
 * string tal cual y no dibuja nada. Los tokens del proyecto se declaran en
 * OKLCH en `style.css` (D-28), así que hay que leer el valor ya computado.
 */
export function resolveCssColor(variable: string, fallback = "#000"): string {
  //  La lectura de `themeRevision` va acá y no en cada gráfico a propósito:
  //  así cualquier `computed` que llame a esta función queda suscrito al
  //  cambio de tema sin tener que acordarse de declarar la dependencia.
  void themeRevision.value;

  if (typeof window === "undefined") {
    return fallback;
  }
  const value = getComputedStyle(document.documentElement)
    .getPropertyValue(variable)
    .trim();
  return value || fallback;
}

/**
 * Monta un gráfico de ECharts sobre `el` y lo mantiene sincronizado con
 * `option`.
 *
 * Se instancia a mano en vez de usar `vue-echarts` para no meter otra
 * dependencia envolvente — y porque el gráfico anterior de este mismo tablero
 * falló justamente dentro de un wrapper que montaba sin dibujar nada y sin
 * reportar error (ver `SalesChart.vue`). Acá el ciclo de vida está a la vista:
 * se crea, se actualiza, se destruye.
 */
export function useECharts(
  el: Ref<HTMLElement | null>,
  option: Ref<EChartsOption>,
) {
  let chart: echarts.ECharts | null = null;
  let observer: ResizeObserver | null = null;
  //  Ver `settleEndLabels`: se rearma en cada actualización con `notMerge`.
  let hasSettled = false;
  //  Handle del re-apply diferido. Tiene que vivir acá arriba y no dentro de
  //  `settleEndLabels`: se cancela desde el propio rearme y desde el desmontaje,
  //  para no llamar `setOption` sobre un gráfico ya destruido.
  let settleTimer = 0;

  /**
   * Vuelve a aplicar la opción en el frame siguiente al primer render.
   *
   * **Por qué hace falta:** las `endLabel` (las etiquetas pegadas a la punta
   * de cada línea, patrón "Line Race") **no se pintan en el primer
   * `setOption`** de una instancia recién creada. Verificado midiendo píxeles:
   * en montaje limpio el dibujo termina exactamente en el borde del área de
   * trazado y no hay nada en el margen reservado; re-aplicando **la misma
   * opción sin cambiarle nada**, las etiquetas aparecen. No es la
   * configuración — el formatter, el color y `labelLayout` se probaron uno por
   * uno y los tres funcionan.
   *
   * Dos detalles que costaron encontrarse, y por eso quedan escritos:
   *
   * 1. **Hay que esperar a que termine la animación.** La etiqueta se ancla a
   *    la punta de la línea, y mientras la línea se está dibujando esa punta
   *    todavía se mueve: re-aplicar a los pocos milisegundos no la materializa.
   *    Se usa la duración declarada en la propia opción, más un margen. El
   *    evento `finished` de ECharts sería lo natural, pero **no se dispara
   *    nunca** en estos gráficos (comprobado: cero invocaciones).
   * 2. **Hay que re-aplicar `getOption()`, no `option.value`.** Al recibir de
   *    vuelta el mismo objeto que acaba de procesar, ECharts concluye que no
   *    hay cambios y se salta el update — que es justo lo que hay que
   *    provocar. Con `option.value` la etiqueta sigue sin aparecer.
   *
   * Va en modo fusión (sin `notMerge`) para no relanzar la carrera.
   */
  function settleEndLabels() {
    if (hasSettled || chart === null) {
      return;
    }
    hasSettled = true;
    const duration = Number(option.value.animationDuration ?? 0);
    window.clearTimeout(settleTimer);
    settleTimer = window.setTimeout(() => {
      chart?.setOption(chart.getOption());
    }, duration + 120);
  }

  onMounted(() => {
    if (el.value === null) {
      return;
    }

    //  Bug reportado: al hacer scroll de la página, el color de las líneas
    //  desaparece por un instante (parece que el gráfico "se borra"). No es
    //  un bug de la app — no hay nada reactivo a scroll acá ni en los
    //  componentes que llaman a este composable — sino un artefacto conocido
    //  de Chromium: al scrollear, el compositor puede re-teselar/re-rasterizar
    //  las capas que se solapan con el canvas, y si el canvas no tiene su
    //  propia capa GPU, el navegador puede recomponerlo desde una copia
    //  incompleta y dejarlo momentáneamente en blanco (el fenómeno se conoce
    //  como "checkerboarding"; ver el bug de Chromium sobre teselas sin pintar
    //  al scrollear más rápido de lo que el hilo de rasterizado alcanza).
    //  `will-change: transform` promueve el contenedor a su propia capa de
    //  composición: el scroll pasa a mover esa capa ya rasterizada en vez de
    //  re-pintarla, que es justo lo que evita el artefacto. Con dos canvases
    //  pequeños (240px de alto) el costo de memoria GPU es insignificante.
    el.value.style.willChange = "transform";

    chart = echarts.init(el.value);
    chart.setOption(option.value);
    settleEndLabels();

    //  El contenedor cambia de ancho al plegar el sidebar, no solo al
    //  redimensionar la ventana: por eso un `ResizeObserver` sobre el elemento
    //  y no un listener de `window.resize`.
    observer = new ResizeObserver(() => chart?.resize());
    observer.observe(el.value);
  });

  watch(option, (next) => {
    //  `notMerge: true`: al cambiar de período cambia la cantidad de puntos, y
    //  una fusión dejaría colgando los del período anterior. Como esto vuelve
    //  a ser un "primer render" para ECharts, hay que rearmar el arreglo de
    //  las `endLabel`.
    hasSettled = false;
    chart?.setOption(next, true);
    settleEndLabels();
  });

  onBeforeUnmount(() => {
    observer?.disconnect();
    observer = null;
    //  Si se sale del tablero antes de que termine la animación, el re-apply
    //  diferido caería sobre una instancia ya destruida.
    window.clearTimeout(settleTimer);
    //  Sin `dispose` el canvas y sus listeners quedan vivos al salir de la
    //  pantalla — se nota al entrar y salir del tablero varias veces.
    chart?.dispose();
    chart = null;
  });
}
