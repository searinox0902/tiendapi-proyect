import { z } from "zod";
import { numericField } from "@/lib/money";

export const referenceFormSchema = z.object({
  sku: z.string().min(1, "El SKU es obligatorio"),
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

export type ReferenceFormValues = z.infer<typeof referenceFormSchema>;
