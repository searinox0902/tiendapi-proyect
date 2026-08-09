import { z } from "zod";
import { numericField } from "@/lib/money";
import { referencesApi } from "./references.api";

/**
 * Verifica que el SKU no exista ya (`GET /references/lookup`), pero sin pegarle
 * al backend en cada tecla: espera SKU_CHECK_DEBOUNCE_MS y, si para entonces ya
 * hay una tecleada más nueva en curso, se descarta a sí misma (devuelve válido)
 * en vez de contestar — solo la verificación MÁS RECIENTE llega a consultar el
 * backend y a decidir el resultado. Si la consulta falla, no bloquea al usuario.
 */
let skuCheckSeq = 0;
const SKU_CHECK_DEBOUNCE_MS = 400;

/**
 * `excludedSku` es el SKU propio de la Referencia que se está editando: como ya
 * existe en el backend, `lookupReference` la encontraría a sí misma y marcaría
 * el SKU como "ya existe" aunque el usuario no lo haya tocado. En modo crear no
 * se pasa (`undefined`), así que nunca hace match.
 */
function buildIsSkuAvailable(excludedSku?: string) {
  return async function isSkuAvailable(sku: string): Promise<boolean> {
    if (sku === excludedSku) {
      return true;
    }
    const seq = ++skuCheckSeq;
    await new Promise(resolve => setTimeout(resolve, SKU_CHECK_DEBOUNCE_MS));
    if (seq !== skuCheckSeq) {
      return true;
    }
    try {
      const { data } = await referencesApi.lookupReference(sku);
      return data === null;
    } catch {
      return true;
    }
  };
}

export function buildReferenceFormSchema(excludedSku?: string) {
  return z.object({
    sku: z.string().min(1, "El SKU es obligatorio").refine(buildIsSkuAvailable(excludedSku), {
      message: "Ya existe una referencia con este SKU",
    }),
    // El Select empieza en `undefined` (no `""`): sin `required_error`, Zod usaría
    // su mensaje genérico "Required" porque `undefined` falla el tipo antes de
    // llegar a evaluar `.min(1)`.
    provider_id: z.string({ required_error: "El proveedor es obligatorio" }).min(1, "El proveedor es obligatorio"),
    brand: z.string().optional(),
    category_id: z.string().optional(),
    title: z.string().min(1, "El nombre es obligatorio"),
    description: z.string().optional(),
    // Costo de adquisición (lado compra) — independiente de base_price/sale_price (lado venta, D-45/D-47).
    precio_proveedor: numericField("El precio proveedor es obligatorio").pipe(
      z.number().nonnegative("El precio proveedor no puede ser negativo"),
    ),
    base_price: numericField("El precio base es obligatorio").pipe(
      z.number().nonnegative("El precio base no puede ser negativo"),
    ),
    iva_percentage: numericField("El IVA es obligatorio").pipe(
      z.number().min(0, "El IVA no puede ser negativo").max(100, "El IVA no puede superar el 100%"),
    ),
  });
}

export const referenceFormSchema = buildReferenceFormSchema();

export type ReferenceFormValues = z.infer<typeof referenceFormSchema>;
