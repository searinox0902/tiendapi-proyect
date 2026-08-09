/**
 * Alarga `promise` hasta que pasen al menos `minMs`, sin tocar su resultado ni
 * su rechazo. Un fetch a `localhost` puede resolver en unos pocos ms, tan
 * rápido que un skeleton nunca alcanza a pintarse — esto le da al usuario
 * tiempo de percibir la animación en vez de un parpadeo.
 */
export function ensureMinDuration<T>(promise: Promise<T>, minMs: number): Promise<T> {
  const delay = new Promise<void>((resolve) => setTimeout(resolve, minMs));
  return Promise.all([promise, delay]).then(([result]) => result);
}
