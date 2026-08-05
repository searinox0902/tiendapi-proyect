# 09 — Diseño de Interfaz y Sistema de Color

> **Contexto:** Principios visuales y distribución de color de la interfaz. Cárgalo para maquetar pantallas, definir tokens de Tailwind/Shadcn o revisar consistencia visual.
> **Fuente:** [`specs/Addendum_2026-07-01_MVP_Pantallas_UI.md`](../specs/Addendum_2026-07-01_MVP_Pantallas_UI.md).

## 1. Principios de diseño

- **Clara:** predominio de fondos claros, alto contraste, poco ruido visual.
- **Moderna:** consistente con el stack decidido — Tailwind CSS + Shadcn/Vue (ver [02 — Arquitectura](02-arquitectura.md), [STACK_TECH.md](STACK_TECH.md)).
- **Minimalista / pocos clics:** coherente con la propuesta de valor de "menos pantallas, menos clics" (ver [01 — Visión de negocio](01-vision-negocio.md), §5).

## 2. Distribución de color (regla 90 / 7 / 3)

| Rol | Color | Proporción de uso | Dónde aplica |
|-----|-------|--------------------|--------------|
| **Fondos** | Claros — blanco `#FFFFFF` (`--background`) | **~90%** | Fondo de pantalla, tarjetas, paneles, superficies base |
| **Primario** | Púrpura **`#9B44C2`** (`--primary`) | **~7%** | Botones primarios, elementos activos/seleccionados, foco de inputs, iconografía destacada, barra o indicador de navegación activa |
| **Texto / acento** | Negro **`#0A0A0A`** (`--foreground`, texto) y **`#040404`** (`--secondary`) | **~3%** | Tipografía principal, íconos secundarios, bordes/divisores sutiles |

> **Valores exactos (A-08 resuelto).** Los tokens viven en [`frontend/src/style.css`](../frontend/src/style.css) y se declaran en **OKLCH**, no en hex, porque es el formato que emite el CLI de shadcn/vue (D-55) y permite derivar variantes como `bg-primary/90` sin saltos de luminosidad. Equivalencias verificadas: `--primary: oklch(0.556 0.197 313.6)` → `#9B44C2`; `--secondary: oklch(0.107 0 0)` → `#040404`. **Cambiar el token cambia los 34 componentes de `ui/` a la vez** — no se pintan colores a mano en los componentes.

**Lectura de la proporción:** el púrpura es un color de **acento funcional** (llama la atención sobre la acción principal — botón de guardar, ítem seleccionado, campo con foco), **no** un color de relleno masivo. El negro se usa con moderación, solo donde aporta legibilidad (texto, íconos), evitando bloques negros grandes que contradigan la sensación de interfaz "clara".

## 3. Aplicación sugerida por componente

> Los tonos exactos (hex) no fueron especificados en el requisito original; se sugiere partir de la paleta estándar de Tailwind y ajustar con el equipo de diseño. Ver punto abierto A-08 en [07 — Decisiones](07-decisiones-y-puntos-abiertos.md).

| Componente | Color sugerido | Notas |
|------------|-----------------|-------|
| Fondo de app / layout | Blanco o `gray-50` | Base ~90% |
| Tarjetas / paneles | Blanco con borde `gray-100`/`gray-200` | Sutil, sin sombras pesadas |
| Botón primario (ej. "Guardar Referencia", "Registrar Pago") | Púrpura (`purple-600` / `violet-600` como punto de partida) | Único color saturado visible en la pantalla |
| Botón secundario | Fondo claro + borde, texto negro | Evita competir con el primario |
| Texto principal (labels, valores) | Negro / `gray-900` | ~3% de la superficie total |
| Íconos activos, enlaces, estado seleccionado en listas | Púrpura | Refuerza jerarquía visual |
| Inputs — estado normal | Fondo claro, borde `gray-200`, texto negro | — |
| Inputs — estado foco | Borde/anillo púrpura | Señala interactividad, coherente con Shadcn/Vue `focus-visible ring` |
| Autocompletado de Referencia (Pantalla "Registrar Pago") | Resultado sugerido resaltado en púrpura claro (`purple-50`/`purple-100`) al hacer hover/selección | Ver flujo en [05 — Alcance MVP y flujos](05-alcance-mvp-y-flujos.md) |

## 4. Tipografía y forma

- **Tipografía definitiva: Geist Sans** (A-09 resuelto). Se carga **localmente** con `@fontsource/geist-sans` (pesos 400/500/600/700) — nunca desde un CDN, para no depender de internet (D-01, local-first). Declarada en `--font-sans` de [`frontend/src/style.css`](../frontend/src/style.css); `--font-heading` hereda de ella, así que títulos y cuerpo comparten familia. Inter era solo la sugerencia original y **quedó descartada**.
- Radio de borde base: `--radius: 0.625rem`.
- Bordes redondeados suaves y espaciado generoso, coherentes con el lenguaje visual de Shadcn/Vue.

## 5. Accesibilidad

- Mantener contraste AA mínimo entre texto negro y fondos claros.
- El púrpura del botón primario debe tener suficiente contraste con el texto/ícono que contiene (blanco sobre púrpura, típicamente).
- No usar el púrpura como único indicador de estado (acompañarlo de ícono o texto) para usuarios con daltonismo.

## 6. Dónde se usa este sistema de color

Aplica a las tres pantallas de la primera iteración del MVP (ver [05 — Alcance MVP y flujos](05-alcance-mvp-y-flujos.md), §2):

1. Inicio de sesión (mock).
2. Registrar Referencia.
3. Registrar Pago (con autocompletado de Referencia).

Y se extiende como estándar visual para el resto de pantallas futuras del producto.

## 6.1 Componentes UI disponibles (base instalada)

Todos los componentes de `frontend/src/components/ui/` se traen **con el CLI oficial de shadcn/vue** (D-55). Nunca se escriben a mano:

```bash
npx shadcn-vue@latest add <componente> -y
```

**Fuente de verdad = el propio directorio**, no esta lista. Para ver el inventario real: `ls frontend/src/components/ui/`. Para comprobar que ninguno se desvió del registro: `npx shadcn-vue@latest diff`.

Base instalada actualmente (34), agrupada por para qué sirve en el MVP:

| Uso en el MVP | Componentes |
|---|---|
| **Formularios** (Referencia, Productos, Login) | `form`, `input`, `textarea`, `label`, `select`, `checkbox`, `radio-group`, `switch`, `toggle`, `toggle-group` |
| **Búsqueda / autocompletado por SKU** | `command`, `popover` |
| **Listados y tablas** (Productos, histórico de Facturas) | `table`, `pagination`, `scroll-area`, `skeleton` |
| **Modales y confirmaciones** (anular factura, D-35) | `dialog`, `alert-dialog`, `sheet` |
| **Feedback al usuario** | `sonner` (toasts, dep. `vue-sonner`), `alert`, `progress`, `tooltip` |
| **Navegación / layout** | `sidebar`, `breadcrumb`, `tabs`, `separator`, `collapsible`, `dropdown-menu` |
| **Dashboard** | `card`, `chart`, `badge`, `avatar`, `button` |

⚠️ **`number-field` está deliberadamente excluido.** Vincula su valor a un `number` de JavaScript (punto flotante), lo que choca de frente con la regla del proyecto de manejar **dinero con Decimal.js** ([CLAUDE.md](../CLAUDE.md), zonas de alto riesgo). Para importes usar `input` de texto + validación Zod + `Decimal`, nunca un binding numérico nativo. Para cantidades enteras sí sería admisible, pero se dejó fuera para no inducir el mal uso.

**Pendiente de decidir:** `calendar` / date-picker para filtrar el histórico de Facturas por fecha — no instalado porque arrastra `@internationalized/date`; se instalará cuando se especifique ese filtro.

## 7. Pantalla Dashboard (métricas generales) — diseño y definiciones

> **Estado: dentro del alcance del MVP (D-51).** Forma parte de las 5 pantallas del MVP ([05](05-alcance-mvp-y-flujos.md), §2.1) — corrige la nota anterior que la marcaba como "post-MVP" cuando solo existía la primera iteración de 3 pantallas (D-14). Las fórmulas y la ubicación de cada métrica están fijadas en **D-49** ([07](07-decisiones-y-puntos-abiertos.md)). Varias métricas dependen de datos aún no capturados — ver "Dependencias" al final.

### 7.1 Principio de organización: flujo vs. foto vs. ratio

Cada métrica vive donde su **naturaleza contable** corresponde, no todas juntas:

- **Flujo de ventas** (lo que pasó por caja en un período) → pantalla **Facturas**.
- **Foto de inventario** (lo que hay parado *ahora*) → pantalla **Productos**.
- **Ratio transversal de salud** (agrega sobre todo el negocio) → pantalla **Dashboard**.

El Dashboard **no duplica** las cards de las otras pantallas: toma un resumen de cada área y lo corona con el indicador que solo tiene sentido cruzando todo (Margen %).

### 7.2 Métricas y fórmulas (fijadas en D-49)

| Métrica | Fórmula | Naturaleza | Pantalla natural |
|---|---|---|---|
| **Total facturado** | Σ `Bill.total` (con IVA) | Flujo · período | Facturas |
| **IVA recaudado** | Σ `Bill.total_iva` | Flujo · período | Facturas |
| **Utilidad** | Σ (`BillItem.unit_price` − `Item.precio_proveedor`) × qty | Flujo · período | Facturas |
| **Margen %** | Utilidad / facturado **sin** IVA | Ratio transversal | **Dashboard** |
| **Ticket promedio** | Total facturado / N° facturas | Flujo · período | Dashboard / Facturas |
| **N° de facturas** | count(`Bill`) en el período | Flujo · período | Dashboard / Facturas |
| **Valor de bodega** | Σ `Item.precio_proveedor` WHERE `status='disponible'` (**a costo**) | Foto de inventario | Productos |
| **Unidades disponibles** | count(`Item` WHERE `status='disponible'`) | Foto de inventario | Productos |
| **Facturas sin declarar (DIAN)** | count(`Bill` WHERE `fiscal_status` ∈ {contingencia, pendiente}) | **Alerta** (sano = 0) | Banner condicional (D-48) |

> **Margen sin IVA:** el denominador excluye el IVA a propósito — el IVA no es ingreso del negocio, meterlo infla el margen. **Bodega a costo:** valorar a `precio_proveedor` (capital inmovilizado real), no a precio de venta (proyección optimista).

### 7.3 Layout sugerido (coherente con la regla 90/7/3)

- **Selector de período** arriba (Hoy · Semana · Mes) — las métricas de flujo son por período; el inventario es una foto y no cambia con el selector (indicarlo visualmente, ej. un ícono de "snapshot").
- **Fila hero (3–4 KPIs grandes):** Margen % · Total facturado · Utilidad · Valor de bodega. El púrpura primario (7%) resalta **solo un** número clave por fila (sugerido: Margen %), no todos.
- **Fila secundaria (stat tiles pequeños):** Ticket promedio · N° facturas · Unidades en stock · Descuentos otorgados.
- **Banner de alerta fiscal (condicional, D-48):** solo aparece si la integración DIAN está viva **y** hay facturas sin declarar. Tono de advertencia, **fuera** de la grilla de cards (es alarma, no analítica).
- **Codificación por tipo de dato:** dar un tono de acento distinto al ícono/borde según sea **plata** / **porcentaje** / **conteo** / **fiscal**, para escanear la fila sin leer cada label. Nunca usar solo color como indicador (acompañar de ícono, §5).

### 7.4 Íconos sugeridos (`@lucide/vue`, el set de shadcn/vue)

`receipt` (Total facturado) · `landmark` (IVA) · `piggy-bank` (Utilidad) · `chart-pie` (Margen %) · `shopping-bag` (Ticket promedio) · `files` (N° facturas) · `warehouse` (Valor de bodega) · `package` (Unidades) · `file-clock` / `file-warning` (Facturas sin declarar — solo en el banner).

### 7.5 Dependencias (qué falta para que cada card muestre datos reales)

- **Utilidad, Margen %, Valor de bodega** → dependen de `Item.precio_proveedor` (D-47), cuya captura (manual vs. XML de proveedor) es **A-25** sin resolver. Hasta cerrarlo, estas tres se maquetan pero no calculan.
- **Facturas sin declarar** → depende de `Bill.fiscal_status` (D-48, reservado) y de toda la integración DIAN (D-09/D-38, diferida). Es alerta, no card; no va en la grilla del MVP.
- **Total facturado, IVA, Ticket promedio, N° facturas, Unidades disponibles** → calculables **ya** con el modelo actual.

## 8. Animaciones (D-54)

Cuatro necesidades fijadas como parte del MVP — sin librería de animación dedicada, apoyadas en Vue nativo + Tailwind (ya en el stack):

| Necesidad | Herramienta | Nota |
|---|---|---|
| **Transiciones de pantalla** (cambio de ruta) | `<Transition>` nativo de Vue envolviendo `<RouterView>` | `mode="out-in"`, sin dependencias nuevas |
| **Spinners** | Tailwind `animate-spin` + ícono `LoaderCircle` de `@lucide/vue` | ambos ya instalados |
| **Skeletons** | Componente `Skeleton` de shadcn/vue (`@/components/ui/skeleton`, Tailwind `animate-pulse`) | traído con el CLI oficial (D-55); ya está en `frontend/src/components/ui/skeleton/` |
| **Animación de cálculos** (total "corriendo" al cambiar) | `useTransition` de **`@vueuse/core`** (única dependencia nueva) | anima un número entre dos valores en el tiempo; aplica a los totales calculados con Decimal.js |

**Explícitamente no incluido en el MVP:** `@vueuse/motion` (animaciones declarativas más ricas/gestuales) y `@formkit/auto-animate` (animación automática de listas) — quedan como mejora post-MVP si se necesita más pulido.

### 8.1 Duración mínima visible de loaders — con excepción en Facturas

El backend corre **local** (D-01) y responde en pocos ms, lo que hace que spinners/skeletons parpadeen ("flash of loading state") en vez de animar. Solución: **no** se retrasa la petición real, se retrasa solo la **ocultación** del loader — se mantiene visible un mínimo de tiempo (~300ms) aunque la respuesta ya haya llegado antes.

**Excepción explícita: pantalla de Facturas/caja.** Ahí la respuesta debe reflejarse apenas llega, **sin ningún padding cosmético** — es el flujo de mayor sensibilidad a velocidad real (cajero con fila de clientes), coherente con el valor central de D-01. El resto de pantallas (CRUD Referencia, CRUD Productos, Dashboard) sí usan la duración mínima.

Además, solo en **desarrollo** se puede inyectar una latencia artificial configurable (`VITE_FAKE_LATENCY_MS`) para poder ajustar visualmente las animaciones contra un backend que responde casi instantáneo — nunca se activa en producción.
