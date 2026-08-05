# Addendum — Pantallas del MVP y Sistema de Color

> **Tipo:** Nota fuente (addendum a la especificación original).
> **Fecha:** 2026-07-01
> **Relación con la fuente original:** complementa `Informe_Consolidado.pdf` (PARTE II — Diseño técnico, secciones 7 y 10) sin reemplazarlo. Este documento **es fuente primaria** de los requisitos nuevos descritos abajo; su versión distribuida/organizada vive en `docs/05-alcance-mvp-y-flujos.md` y `docs/09-diseno-ui-ux.md`.

## 1. Requisito recibido (verbatim, resumido)

Para la primera iteración del MVP se definen tres pantallas concretas, en este orden:

1. **Inicio de sesión.** El usuario debe poder "iniciar sesión", aunque sea una **sesión falsa/simulada**: no es necesario que esté conectada a un backend real en esta etapa.
2. **Registrar Referencia.** Pantalla para dar de alta una Referencia (producto) en el catálogo.
3. **Registrar Pago.** Pantalla para registrar un pago/cobro. El usuario ingresa una Referencia; **si esta ya existe, sus datos se autocompletan**.

## 2. Sistema de color solicitado

Interfaz **clara y moderna**, con la siguiente distribución aproximada de color:

| Rol | Color | Proporción de uso |
|-----|-------|--------------------|
| Primario | Púrpura | ~7% |
| Fondos | Claros | ~90% |
| Texto / acento | Negro | ~3% |

## 3. Dónde se distribuyó este contenido

- Secuencia de pantallas del MVP → [`docs/05-alcance-mvp-y-flujos.md`](../docs/05-alcance-mvp-y-flujos.md) (sección "Secuencia de pantallas — primera iteración del MVP").
- Sistema de color y principios de UI → [`docs/09-diseno-ui-ux.md`](../docs/09-diseno-ui-ux.md) (nuevo documento).
- Decisiones registradas → [`docs/07-decisiones-y-puntos-abiertos.md`](../docs/07-decisiones-y-puntos-abiertos.md) (D-14, D-15) y puntos abiertos (A-08, A-09).
- Roadmap de prototipado (Figma) actualizado → [`docs/06-equipo-riesgos-roadmap.md`](../docs/06-equipo-riesgos-roadmap.md).

## 4. Notas del arquitecto (no son parte literal del requisito, sino su interpretación técnica)

- "Sesión falsa" se interpreta como **mock de autenticación en el cliente** (estado local simulando usuario autenticado), sin llamadas reales al backend de auth descrito en [`docs/04-seguridad.md`](../docs/04-seguridad.md). Se documenta como decisión temporal de alcance, a reemplazar por el login real (token firmado, ver `04-seguridad.md`) en una iteración posterior.
- El color púrpura exacto (hex/tono) y la tipografía no fueron especificados; se documentan como puntos abiertos (ver `07-decisiones-y-puntos-abiertos.md`, A-08/A-09), con una sugerencia no vinculante basada en la paleta estándar de Tailwind.
- "Registrar Pago" con autocompletado de Referencia reutiliza el mismo concepto de autocompletado ya descrito como propuesta de valor en `docs/01-vision-negocio.md` y como flujo en `docs/05-alcance-mvp-y-flujos.md`.
