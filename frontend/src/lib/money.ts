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

/** Formatea en pesos colombianos: punto de miles, coma decimal (ej. "$ 182.000,00"). */
export function formatCurrency(value: Decimal | number): string {
  const decimal = value instanceof Decimal ? value : new Decimal(value);
  const [integer, decimals] = decimal.toFixed(2).split(".");
  const grouped = integer.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return `$ ${grouped},${decimals}`;
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
