/**
 * Dispara la descarga de un blob que ya llegó del servidor.
 *
 * Existe porque esta misma secuencia —leer el nombre de `Content-Disposition`,
 * crear un object URL, clickear un `<a>` invisible y revocar el URL— estaba
 * copiada en cinco pantallas, y el paso que más se olvida al copiarla es el
 * `revokeObjectURL`: sin él, cada descarga deja el archivo entero retenido en
 * memoria hasta que se recarga la pestaña.
 *
 * El nombre lo decide **siempre el backend** (lleva negocio y fecha, o el
 * consecutivo de la factura). `fallback` solo entra si la cabecera no viajó,
 * que pasa cuando CORS no la expone — por eso todos los endpoints de descarga
 * mandan `Access-Control-Expose-Headers: Content-Disposition`.
 */
export function downloadBlob(
  data: Blob,
  headers: Record<string, unknown> | undefined,
  fallback: string,
): void {
  const disposition = String(headers?.["content-disposition"] ?? "")
  const match = disposition.match(/filename="?([^";]+)"?/)
  const url = URL.createObjectURL(data)
  const link = document.createElement("a")
  link.href = url
  link.download = match?.[1] ?? fallback
  link.click()
  URL.revokeObjectURL(url)
}
