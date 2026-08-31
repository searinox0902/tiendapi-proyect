import { z } from "zod";
import { numericField } from "@/lib/money";

/**
 * El SKU **no valida contra el catálogo** (D-90). Antes había un chequeo con
 * debounce que consultaba `GET /references/lookup` y marcaba "Ya existe una
 * referencia con este SKU" como error del campo; se retiró a propósito.
 *
 * Que el código exista dejó de ser un error: es la puerta de entrada al modo
 * variante. El formulario lo detecta, lo explica en un aviso propio y **bloquea
 * el resto de los campos hasta que el usuario decida** (cambiar el código o
 * crear la variante). Un mensaje rojo ahí sobraba —el aviso ya dice qué pasa— y
 * encima contradecía al botón "Crear variante" que aparece al lado.
 *
 * La autoridad final sigue siendo el servidor: el índice único
 * `(tenant_id, sku)` rechaza cualquier duplicado con un 409, así que el cliente
 * no necesita replicar la regla para que se cumpla.
 */
export function buildReferenceFormSchema() {
  return z.object({
    // Sin `.min(1)`: vacío es válido y el servidor genera un `GEN-XXXXXXXX`
    // desde el nombre (D-86). Es el mismo criterio que la importación en lote,
    // para que el mismo producto no entre con dos convenciones distintas.
    sku: z.string(),
    // El Select empieza en `undefined` (no `""`): sin `required_error`, Zod usaría
    // su mensaje genérico "Required" porque `undefined` falla el tipo antes de
    // llegar a evaluar `.min(1)`.
    provider_id: z.string({ required_error: "El proveedor es obligatorio" }).min(1, "El proveedor es obligatorio"),
    brand: z.string().optional(),
    category_id: z.string().optional(),
    title: z.string().min(1, "El nombre es obligatorio"),
    description: z.string().optional(),
    // URL externa manual (ej. scraping) — alternativa a subir/recortar un archivo.
    // `z.literal("")` porque el campo vacío es el caso normal (nadie la usa), no un error.
    image_url: z.union([z.literal(""), z.string().url("Ingresá una URL válida (con https://)")]).optional(),
    // Costo de adquisición (lado compra) — independiente de base_price/sale_price (lado venta, D-45/D-47).
    provider_price: numericField("El precio proveedor es obligatorio").pipe(
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
