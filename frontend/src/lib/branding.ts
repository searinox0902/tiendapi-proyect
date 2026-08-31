/**
 * Imagen del negocio recordada localmente, para pintarla en el login.
 *
 * **El problema que resuelve:** la pantalla de inicio de sesión se dibuja
 * ANTES de autenticarse, así que no hay token del cual sacar el `tenant_id`
 * para preguntarle al backend cuál es la imagen de este negocio. Y el sistema
 * es multi-tenant, así que el servidor tampoco puede adivinarlo desde una
 * petición anónima.
 *
 * La salida se apoya en dos hechos que ya existen: `/static` se sirve sin
 * autenticación, y el producto es **desktop-first, un negocio por instalación**
 * (D-29/D-32). Alcanza con que el cliente recuerde la ruta al entrar (o al
 * subir la imagen) y la use la próxima vez. En una máquina nueva, la primera
 * pantalla de login muestra el fondo por defecto: correcto, todavía no hay
 * negocio asociado a esa instalación.
 *
 * **Se guarda la ruta relativa, nunca la absoluta.** Un host quemado
 * (`http://localhost:8000/...`) resuelve contra sí mismo en cualquier otra
 * máquina de la LAN y deja la imagen rota — es exactamente el bug que D-84
 * eliminó de la base de datos, y no tiene por qué volver por `localStorage`.
 * El host se compone al leer, con el que la app esté usando en ese momento.
 */
const LOGIN_IMAGE_KEY = "tiendapi.branding.loginImage";

/** Guarda la ruta relativa, o la olvida si se quitó la imagen. */
export function rememberLoginImage(path: string | null): void {
  if (path) {
    localStorage.setItem(LOGIN_IMAGE_KEY, path);
  } else {
    localStorage.removeItem(LOGIN_IMAGE_KEY);
  }
}

/**
 * URL absoluta lista para pintar, o `null` si no hay imagen recordada.
 *
 * Se descarta cualquier valor que no sea una ruta relativa nuestra: un
 * `localStorage` es editable a mano, y sin este filtro un valor manipulado
 * terminaría dentro de un `url(...)` de CSS.
 */
export function readLoginImageUrl(): string | null {
  const path = localStorage.getItem(LOGIN_IMAGE_KEY);
  if (!path || !path.startsWith("/static/")) {
    return null;
  }
  return `${import.meta.env.VITE_API_URL}${path}`;
}
