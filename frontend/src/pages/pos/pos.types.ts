/**
 * Una línea del detalle de factura que se está armando en la caja.
 *
 * Guarda el precio **ya cobrable** (venta con IVA, D-45/D-46, con el descuento
 * de la línea aplicado) y no el precio de catálogo: una vez agregada, la línea
 * no debe cambiar de valor porque alguien edite la Referencia en otra pantalla.
 * De ahí también que copie `sku`/`title` en vez de referenciar el objeto vivo.
 */
export interface IPosCartLine {
  /** `Reference.id` — identifica la línea y evita duplicarla al agregar dos veces lo mismo. */
  referenceId: string;
  sku: string;
  title: string;
  imageUrl?: string;
  /** Precio unitario efectivamente cobrado, con IVA y descuento. String decimal, nunca float. */
  unitPrice: string;
  /** % de IVA de la Referencia. Hace falta para descomponer base e IVA a partir del total cobrado. */
  ivaPercentage: string;
  quantity: number;
  /**
   * Unidades vendibles al momento de agregar la línea. Es el tope de la
   * botonera: sin esto el cajero puede subir la cantidad por encima de lo que
   * hay, y el cobro revienta con un 409 recién al final, cuando ya cobró.
   *
   * Es una **foto**, no un dato vivo: se refresca cuando la grilla recarga.
   * El servidor sigue siendo la autoridad final sobre existencias (evita la
   * carrera entre dos cajas), esto solo evita el error obvio antes de tiempo.
   */
  availableUnits: number;
}
