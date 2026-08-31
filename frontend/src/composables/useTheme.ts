import { useDark, useStorage, useToggle } from "@vueuse/core"
import { watchEffect } from "vue"

export const isDark = useDark({
  selector: "html",
  attribute: "class",
  valueDark: "dark",
  valueLight: "",
  storageKey: "tiendapi-theme",
})

export const toggleDark = useToggle(isDark)

/**
 * Temas de color (D-80). Son un eje **independiente** del modo claro/oscuro:
 * el tema decide el color primario, `isDark` decide la superficie. Los dos
 * conviven en `<html>` — `class="dark"` y `data-theme="carmesi"` — y cada
 * combinación tiene su bloque de tokens en `style.css`.
 */
export const THEMES = [
  { value: "violeta", label: "Violeta", hint: "Carácter, origen, marca" },
  { value: "carmesi", label: "Carmesí", hint: "Fuerza, pulso, urgencia" },
  { value: "sol", label: "Sol", hint: "Calidez, energía, mediodía" },
  { value: "verde", label: "Verde menta", hint: "Calma, frescura, claridad" },
  { value: "salmon", label: "Salmón", hint: "Cercanía, encuentro, brisa" },
  { value: "grafito", label: "Obsidiana", hint: "Elegancia, sobriedad, absoluto" },
] as const

export type TThemeName = typeof THEMES[number]["value"]

const DEFAULT_THEME: TThemeName = "violeta"

/**
 * Clave distinta de la del modo (`tiendapi-theme`) a propósito: son dos
 * preferencias separadas y guardarlas juntas obligaría a migrar el valor viejo
 * de quien ya tiene un modo elegido.
 *
 * **En Tauri se comporta igual que en el navegador**: WebView2 implementa
 * `localStorage` de forma normal, persistido en la carpeta de datos propia de
 * la instalación — sobrevive cerrar la app y reiniciar el equipo, y no se
 * comparte con el navegador del sistema ni entre equipos.
 */
export const theme = useStorage<TThemeName>("tiendapi-color-theme", DEFAULT_THEME)

//  `watchEffect` y no una llamada suelta: corre al importar el módulo (deja el
//  atributo puesto antes del primer render, incluido el login) y vuelve a
//  correr en cada cambio, sin que cada pantalla tenga que acordarse de aplicarlo.
watchEffect(() => {
  const value = theme.value
  const known = THEMES.some(entry => entry.value === value)
  document.documentElement.dataset.theme = known ? value : DEFAULT_THEME
})

export function setTheme(value: TThemeName) {
  theme.value = value
}
