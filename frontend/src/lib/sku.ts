/**
 * Normalización del SKU — espejo de `backend/app/core/sku.py` (D-85).
 *
 * Espacios, `_`, `*`, `,` y `.` pasan a `-`; las corridas de guiones se
 * colapsan y los extremos se recortan. Ej.: `"50-29028-16 - 50-29001-46"` →
 * `"50-29028-16-50-29001-46"`.
 *
 * **El servidor es la autoridad** (regla del proyecto): el backend normaliza
 * igual al escribir, así que esto no es la validación real. Existe por dos
 * razones concretas del cliente:
 *
 * 1. **El chequeo de SKU duplicado consultaría el valor equivocado.** El
 *    formulario pregunta `GET /references/lookup?sku=...` mientras se teclea;
 *    sin normalizar, buscaría `AB 1` cuando lo que va a quedar guardado es
 *    `AB-1`, y no encontraría el duplicado que sí existe.
 * 2. **Que el usuario vea lo que va a quedar guardado**, en vez de escribir una
 *    cosa y recibir otra distinta del servidor al guardar.
 */
const SEPARATORS = /[\s_*,.]+/g;
const DASH_RUNS = /-{2,}/g;

export function normalizeSku(sku: string): string {
  return sku
    .trim()
    .replace(SEPARATORS, "-")
    .replace(DASH_RUNS, "-")
    .replace(/^-+|-+$/g, "");
}
