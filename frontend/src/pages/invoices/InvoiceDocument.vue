<script setup lang="ts">
import { computed } from "vue"

import { formatCurrency, formatPercentage, formatQuantity, toDecimal } from "@/lib/money"
import type { IBillDetail } from "@/api/bills/bills.types"

/**
 * El documento de la factura, en el panel derecho.
 *
 * **Por qué se reconstruye desde la BBDD en vez de guardar un PDF (D-61):** la
 * integración DIAN está diferida (D-09/D-38), así que hoy no existe ninguna
 * factura con validez fiscal — cualquier PDF que generáramos sería solo una
 * representación gráfica de datos que ya viven en la base. Guardarlo como
 * archivo duplicaría la fuente de verdad (al corregir un dato, el PDF quedaría
 * mintiendo), quedaría **fuera** del cifrado en reposo —SQLCipher protege la
 * base, no archivos sueltos (docs/04)— y no participaría de la cadena HMAC de
 * D-07, que es sobre registros.
 *
 * Cuando llegue la DIAN sí habrá archivo, y **no lo generamos nosotros**: la
 * copia firmada (XML + PDF) la emite el proveedor y se almacena tal cual
 * (docs/05, §3.6; docs/02, §9.7 — `FiscalRecord` con enlace a la
 * representación gráfica). Ese día `pdf_url` deja de ser `null` y este mismo
 * panel muestra el archivo en un `<iframe>` en vez de la hoja reconstruida.
 * Esa es toda la costura: un `v-if`.
 */
const props = defineProps<{ bill: IBillDetail }>()

/**
 * Etiquetas del eje fiscal (D-81). Corrige dos que estaban mal en el listado:
 * `contingencia` se mostraba como **"Bloqueada"**, que no es lo que significa
 * —una factura en contingencia se emitió bien, offline, y se transmite
 * después—, y `pendiente` no se distinguía de ella en la práctica.
 *
 * Hoy ninguna de las cuatro aparece: la integración DIAN está diferida
 * (D-09/D-38) y `fiscal_status` es `NULL` en todas las facturas. Están acá de
 * forma ilustrativa, listas para el día que el trámite exista.
 */
const FISCAL_LABELS: Record<NonNullable<IBillDetail["fiscal_status"]>, string> = {
  autorizada: "Autorizada por la DIAN",
  pendiente: "En proceso ante la DIAN",
  contingencia: "Emitida en contingencia, pendiente de transmitir",
  rechazada: "Rechazada por la DIAN",
}

const issuedAt = computed(() =>
  new Intl.DateTimeFormat("es-CO", {
    day: "2-digit", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit",
  }).format(new Date(props.bill.created_at)),
)

const voidedAt = computed(() =>
  props.bill.voided_at === null
    ? ""
    : new Intl.DateTimeFormat("es-CO", { day: "2-digit", month: "long", year: "numeric" })
      .format(new Date(props.bill.voided_at)),
)

function money(value: string) {
  return formatCurrency(toDecimal(value))
}

/**
 * Vive en `lib/money.ts` y no acá: el PDF del paquete (D-78) tiene que
 * mostrarlas igual, y dos implementaciones fue exactamente lo que produjo el
 * "1.000" para una unidad en la primera corrida del exportador.
 */
const quantity = formatQuantity
</script>

<template>
  <!--
    `bg-muted` alrededor de la hoja: es lo que hace que se lea como una hoja
    apoyada sobre una mesa y no como otro bloque de la pantalla. Scrollea el
    contenedor, no la página.
  -->
  <div class="min-w-0 flex-1 overflow-auto rounded-xl border border-border bg-muted/40 p-4">
    <!--
      Camino futuro: con la copia firmada del proveedor DIAN, el visor real. No
      se renderiza hoy porque `pdf_url` siempre llega `null` (D-09/D-38).
    -->
    <iframe
      v-if="bill.pdf_url"
      :src="bill.pdf_url"
      :title="`Factura ${bill.bill_number}`"
      class="mx-auto block h-[1123px] w-full max-w-[794px] rounded-sm border border-border bg-card"
    />

    <!--
      Hoja reconstruida. Proporción carta/A4 (794×1123 px a 96 dpi) para que lo
      que se ve en pantalla sea lo que sale por la impresora.
      `id` fijo: es el ancla del `@media print` de abajo.
    -->
    <div
      v-else
      id="invoice-print-area"
      class="relative mx-auto w-full max-w-[794px] rounded-sm border border-border bg-card p-10 shadow-sm"
      style="min-height: 1123px"
    >
      <!--
        Sello de anulada. `-rotate-12` y baja opacidad para que se lea encima
        sin tapar las cifras: quien mire la hoja tiene que ver de una que este
        documento no cobra, pero sigue teniendo que poder leerlo.
      -->
      <div
        v-if="bill.voided_at"
        class="pointer-events-none absolute inset-0 flex items-center justify-center"
        aria-hidden="true"
      >
        <span class="-rotate-12 rounded-lg border-4 border-destructive px-8 py-2 text-5xl font-black uppercase tracking-widest text-destructive opacity-20">
          Anulada
        </span>
      </div>

      <header class="flex items-start justify-between gap-6 border-b border-border pb-6">
        <div class="min-w-0">
          <p class="text-xs uppercase tracking-widest text-muted-foreground">
            Factura de venta
          </p>
          <p class="font-mono text-2xl font-bold">
            {{ bill.bill_number }}
          </p>
        </div>
        <div class="shrink-0 text-right text-xs text-muted-foreground">
          <p>Fecha de emisión</p>
          <p class="font-medium text-foreground">
            {{ issuedAt }}
          </p>
        </div>
      </header>

      <section class="grid gap-6 border-b border-border py-6 sm:grid-cols-2">
        <div class="min-w-0">
          <p class="text-[10px] uppercase tracking-widest text-muted-foreground">
            Cliente
          </p>
          <p class="truncate font-medium" :title="bill.customer.fullname">
            {{ bill.customer.fullname }}
          </p>
          <p class="text-xs text-muted-foreground">
            <!-- Sin documento no se inventa uno: se dice que no está cargado. -->
            {{ bill.customer.nit ? `CC/NIT ${bill.customer.nit}` : "Sin documento registrado" }}
          </p>
        </div>
        <div class="min-w-0 sm:text-right">
          <p class="text-[10px] uppercase tracking-widest text-muted-foreground">
            Estado fiscal
          </p>
          <!--
            `null` no es un estado: es que la factura nunca entró al trámite
            (D-48/D-59). Este es el único lugar donde lo fiscal se muestra
            (D-81) — salió del listado, donde repetía la misma etiqueta en 26
            de 29 filas. Y la frase dice quién no ha emitido: **"Sin declarar"
            a secas se lee como un incumplimiento del negocio**, cuando lo que
            falta es la integración, que es nuestra (D-09/D-38).
          -->
          <p class="font-medium">
            {{ bill.fiscal_status ? FISCAL_LABELS[bill.fiscal_status] : "Facturación electrónica no habilitada" }}
          </p>
          <p v-if="bill.voided_at" class="text-xs text-destructive">
            Anulada el {{ voidedAt }}
          </p>
        </div>
      </section>

      <table class="w-full border-collapse py-6 text-sm">
        <thead>
          <tr class="border-b border-border text-left text-[10px] uppercase tracking-widest text-muted-foreground">
            <th class="py-2 font-medium">
              Descripción
            </th>
            <th class="py-2 text-right font-medium">
              Cant.
            </th>
            <th class="py-2 text-right font-medium">
              IVA
            </th>
            <th class="py-2 text-right font-medium">
              V. unitario
            </th>
            <th class="py-2 text-right font-medium">
              Total
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="line in bill.lines" :key="`${line.reference_id}-${line.unit_price}`" class="border-b border-border/60 align-top">
            <td class="py-2 pr-3">
              <p class="font-mono text-xs text-muted-foreground">
                {{ line.sku }}
              </p>
              <p>{{ line.title }}</p>
            </td>
            <td class="py-2 text-right tabular-nums">
              {{ quantity(line.quantity) }}
            </td>
            <td class="py-2 text-right tabular-nums">
              {{ formatPercentage(line.iva_percentage) }} %
            </td>
            <td class="py-2 text-right tabular-nums">
              {{ money(line.unit_price) }}
            </td>
            <td class="py-2 text-right font-medium tabular-nums">
              {{ money(line.total) }}
            </td>
          </tr>
          <tr v-if="bill.lines.length === 0">
            <td colspan="5" class="py-8 text-center text-muted-foreground">
              Esta factura no tiene ítems.
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Totales pegados a la derecha, como en cualquier factura impresa. -->
      <section class="mt-6 flex justify-end">
        <dl class="w-full max-w-64 space-y-1 text-sm">
          <div class="flex items-center justify-between gap-4">
            <dt class="text-muted-foreground">
              Subtotal
            </dt>
            <dd class="tabular-nums">
              {{ money(bill.subtotal) }}
            </dd>
          </div>
          <div class="flex items-center justify-between gap-4">
            <dt class="text-muted-foreground">
              IVA
            </dt>
            <dd class="tabular-nums">
              {{ money(bill.total_iva) }}
            </dd>
          </div>
          <div class="flex items-center justify-between gap-4 border-t border-border pt-2">
            <dt class="font-semibold">
              Total
            </dt>
            <dd class="text-lg font-bold tabular-nums">
              {{ money(bill.total) }}
            </dd>
          </div>
        </dl>
      </section>

      <!--
        El aviso NO es decorativo ni provisional-de-mentira: mientras la
        integración DIAN esté diferida, este papel no es una factura
        electrónica. Un documento que se imprime igual que una factura válida y
        no lo dice induce al error de entregárselo a un cliente como si lo
        fuera. Se va el día que `pdf_url` traiga la copia firmada.
      -->
      <footer class="mt-10 border-t border-border pt-4 text-[10px] leading-relaxed text-muted-foreground">
        Documento generado por el sistema a partir de los datos de la venta.
        <strong class="font-semibold">No constituye factura electrónica válida ante la DIAN</strong>
        mientras no cuente con autorización y representación gráfica firmada del
        proveedor de facturación electrónica.
      </footer>
    </div>
  </div>
</template>

<!--
  Sin `scoped` a propósito: la regla tiene que poder ocultar el resto de la
  página (sidebar, cabecera, botonera), que son nodos de otros componentes.

  `visibility` en vez de `display: none`: con `display` el navegador rearma el
  layout de cero y la hoja pierde su ancho. Con `visibility` todo sigue
  ocupando su lugar, solo que invisible, y la hoja se reposiciona sola arriba a
  la izquierda del papel. El `#invoice-print-area` acota el alcance: nada de
  esto aplica fuera de esta pantalla.
-->
<style>
@media print {
  body * {
    visibility: hidden !important;
  }

  #invoice-print-area,
  #invoice-print-area * {
    visibility: visible !important;
  }

  #invoice-print-area {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    max-width: none;
    min-height: 0 !important;
    border: none;
    box-shadow: none;
    padding: 0;
  }

  @page {
    margin: 14mm;
  }
}
</style>
