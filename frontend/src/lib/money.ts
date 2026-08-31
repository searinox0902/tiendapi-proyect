import { z } from "zod";
import Decimal from "decimal.js";

/**
 * Nunca punto flotante para dinero (regla del proyecto, CLAUDE.md): cualquier
 * campo de dinero/porcentaje de la plataforma pasa por acá para llegar a un
 * `Decimal` exacto, sin importar si el input llegó vacío, como string del
 * formulario o como número.
 */
export function toDecimal(raw: unknown): Decimal {
  if (raw === "" || raw === undefined || raw === null) {
    return new Decimal(0);
  }
  return new Decimal(raw as Decimal.Value);
}

/**
 * Agrupa la parte entera con la convención colombiana completa: punto de
 * miles y **apóstrofo en el millón** — `2'500.000`, `1.234'567.890`.
 *
 * El apóstrofo no es decorativo: marca de un golpe la magnitud. En una cifra
 * como `2500000` escrita solo con puntos (`2.500.000`) hay que contar grupos
 * para saber si son dos millones y medio o doscientos cincuenta mil; con el
 * apóstrofo se ve dónde empieza el millón sin contar.
 *
 * Espejo exacto de `_money()` en `backend/app/exports/billing.py`, que imprime
 * los PDF del paquete de facturas (D-78). Si cambias uno, cambia el otro — el
 * papel y la pantalla mostrando la misma plata distinto es justo la divergencia
 * que esa decisión se compromete a evitar.
 */
function groupInteger(digits: string): string {
  const chunks: string[] = [];
  for (let end = digits.length; end > 0; end -= 3) {
    chunks.unshift(digits.slice(Math.max(0, end - 3), end));
  }
  let out = chunks[0];
  for (let index = 1; index < chunks.length; index += 1) {
    //  Posición del grupo contando desde la derecha: 0 = unidades, 1 = miles,
    //  2 = millones. El separador que queda justo antes del grupo de los miles
    //  es el del millón, y ese es el que lleva apóstrofo.
    const fromRight = chunks.length - 1 - index;
    out += (fromRight === 1 ? "'" : ".") + chunks[index];
  }
  return out;
}

/** Formatea en pesos colombianos: `$ 182.000,00`, `$ 2'500.000,00`. */
export function formatCurrency(value: Decimal | number): string {
  const decimal = value instanceof Decimal ? value : new Decimal(value);
  const [integer, decimals] = decimal.toFixed(2).split(".");
  const negative = integer.startsWith("-");
  return `$ ${negative ? "-" : ""}${groupInteger(integer.replace("-", ""))},${decimals}`;
}

/**
 * Cantidad legible: `1`, `2,5` — nunca `1.000` para una unidad.
 *
 * `BillItem.quantity` es `Numeric(12,3)`, así que una unidad llega del servidor
 * como `"1.000"`. Imprimir eso tal cual se lee **mil unidades** en Colombia,
 * donde el punto es el separador de miles. Los decimales van con coma, la misma
 * convención que `formatCurrency`, para no mezclar dos en la misma tabla.
 *
 * Espejo de `_quantity()` en `backend/app/exports/billing.py` (D-78).
 */
export function formatQuantity(value: Decimal | string | number): string {
  const decimal = toDecimal(value).toDecimalPlaces(3);
  return decimal.isInteger() ? decimal.toFixed(0) : decimal.toString().replace(".", ",");
}

/**
 * Formatea un porcentaje con coma decimal ("36,81"), la misma convención que
 * `formatCurrency`. Sin el símbolo `%`, para que quien lo use decida dónde va.
 */
export function formatPercentage(value: Decimal | string | number): string {
  return toDecimal(value).toFixed(2).replace(".", ",");
}

/**
 * Precio de venta con IVA, redondeado al múltiplo de $50 más cercano
 * (D-45/D-46). Espejo en JS de `sale_price` (`backend/app/core/pricing.py`) —
 * misma fórmula, mismo redondeo (`ROUND_HALF_UP`), para que la vista previa en
 * el cliente coincida con lo que el servidor termina guardando de verdad.
 */
export function computeSalePrice(basePrice: Decimal.Value, ivaPercentage: Decimal.Value): Decimal {
  const conIva = toDecimal(basePrice).times(toDecimal(ivaPercentage).dividedBy(100).plus(1));
  return conIva.toNearest(50, Decimal.ROUND_HALF_UP);
}

/**
 * Descompone un precio ya cobrado (con IVA incluido) en su base imponible.
 * Va en esta dirección, y no `base × (1+IVA)`, porque en la caja el dato firme
 * es lo que el cliente paga: derivar la base hacia atrás garantiza que
 * `subtotal + IVA` dé exactamente el total, sin un peso de descuadre por el
 * redondeo a $50.
 */
export function basePriceFromGross(grossPrice: Decimal.Value, ivaPercentage: Decimal.Value): Decimal {
  const divisor = toDecimal(ivaPercentage).dividedBy(100).plus(1);
  return toDecimal(grossPrice).dividedBy(divisor).toDecimalPlaces(2, Decimal.ROUND_HALF_UP);
}

/**
 * Campo numérico de Zod para dinero/porcentaje: convierte "" (input vacío) en
 * `undefined` para que `z.number()` lo marque como obligatorio en vez de
 * tratarlo como 0. Reusar en cualquier schema con un campo de este tipo.
 */
export function numericField(invalidMessage: string) {
  return z.preprocess(
    (value) => (value === "" || value === null ? undefined : value),
    z.coerce.number({ invalid_type_error: invalidMessage }),
  );
}
