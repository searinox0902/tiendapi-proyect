/**
 * Redimensiona una imagen a un canvas, preservando su aspect ratio original,
 * para que su lado más largo no supere `maxDimension`. Pensado para cargar
 * fotos de cámara/celular (fácilmente 3000px+) sin que el navegador tenga que
 * decodificar/mover ese peso completo solo para mostrarlas en un recortador.
 */
export async function resizeToFit(file: File | Blob, maxDimension: number): Promise<Blob> {
  const bitmap = await createImageBitmap(file);
  try {
    const scale = Math.min(1, maxDimension / Math.max(bitmap.width, bitmap.height));
    const width = Math.round(bitmap.width * scale);
    const height = Math.round(bitmap.height * scale);
    return await drawToBlob(bitmap, width, height);
  } finally {
    bitmap.close();
  }
}

/** Redimensiona un canvas/imagen ya recortada (cuadrada) a un tamaño de salida fijo — homologa todas las imágenes de la plataforma al mismo peso/resolución. */
export async function resizeSquareTo(source: CanvasImageSource, outputSize: number): Promise<Blob> {
  return drawToBlob(source, outputSize, outputSize);
}

async function drawToBlob(source: CanvasImageSource, width: number, height: number): Promise<Blob> {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    throw new Error("No se pudo obtener el contexto 2D del canvas");
  }
  ctx.drawImage(source, 0, 0, width, height);
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) {
        resolve(blob);
      } else {
        reject(new Error("No se pudo generar la imagen redimensionada"));
      }
    }, "image/jpeg", 0.9);
  });
}
