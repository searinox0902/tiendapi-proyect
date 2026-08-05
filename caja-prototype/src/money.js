import Decimal from "decimal.js";

// Aritmética monetaria exacta — mismo criterio que frontend/src/lib/money.ts
// (Decimal.js, ROUND_HALF_UP). Nunca punto flotante para dinero.
Decimal.set({ rounding: Decimal.ROUND_HALF_UP });

export function d(value) {
  return new Decimal(value || 0);
}

export function lineSubtotal(unitPrice, qty) {
  return d(unitPrice).times(qty);
}

export function ivaOf(subtotal, ivaPct) {
  return d(subtotal).times(d(ivaPct).div(100));
}

// Formato peso colombiano. COP no usa centavos en la práctica → 0 decimales.
export function formatCOP(value) {
  return new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency: "COP",
    maximumFractionDigits: 0,
  }).format(d(value).toNumber());
}
