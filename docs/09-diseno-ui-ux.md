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

> **El primario ahora es elegible por el usuario (D-80).** El púrpura `#9B44C2` sigue siendo **el de por defecto y el de la marca**, y A-08 no se revoca: lo que cambia es que Configuraciones ofrece seis temas (violeta, carmesí, sol, verde menta, salmón, grafito) que reemplazan el primario y todo lo que deriva de él. La regla 90/7/3 **se mantiene igual en todos** — lo que cambia es el tono de ese 7%, no su proporción. Los temas son un eje **independiente** del modo claro/oscuro: se combinan libremente. Ver §4.2.

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

### 4.1 Formato de cifras — convención colombiana (D-79)

- **Dinero: `$ 2'500.000,00`** — punto de miles, coma decimal y **apóstrofo en el millón**. El apóstrofo no es decorativo: marca la magnitud de un golpe. En `2.500.000` escrito solo con puntos hay que contar grupos para distinguir dos millones y medio de doscientos cincuenta mil; con el apóstrofo se ve dónde empieza el millón sin contar.
- **Cantidades: `1`, `2,5`** — nunca `1.000` para una unidad. `BillItem.quantity` es `Numeric(12,3)` y llega del servidor como `"1.000"`; imprimir eso tal cual se lee *mil unidades* justamente por el punto de miles.
- **Una sola implementación por lado, y son espejo:** [`frontend/src/lib/money.ts`](../frontend/src/lib/money.ts) (`formatCurrency`, `formatQuantity`) y [`backend/app/exports/billing.py`](../backend/app/exports/billing.py) (`_money`, `_quantity`, para los PDF del paquete de D-78). Verificadas idénticas sobre 18 casos, incluidos negativos y el salto del millón. **Si cambias una, cambia la otra** — el papel y la pantalla mostrando la misma plata distinto es la divergencia que D-78 se compromete a evitar.
- No usar `locale`/`Intl` para el dinero: en el backend depende de qué idiomas tenga instalado el contenedor (un servidor sin `es_CO` cambia el formato sin avisar), y ninguno de los dos entornos produce el apóstrofo.

### 4.2 Temas de color (D-80)

Seis temas elegibles en **Configuraciones → Tema**. El tema decide el **color**; el switch claro/oscuro decide la **superficie**. Son ejes independientes y se combinan: `<html class="dark" data-theme="carmesi">`.

| Tema | Hue | Claro | Oscuro | Texto sobre el primario |
|------|-----|-------|--------|--------------------------|
| **Violeta** (por defecto) | 313.6 | `#9B44C2` | `#B865DF` | blanco / negro |
| **Carmesí** | 25 | `#C73839` | `#E65A56` | blanco / negro |
| **Sol** | 65 | `#DF870A` | `#FE9E26` | **negro** / negro |
| **Verde menta** | 165 | `#029E72` | `#3FBE90` | **negro** / negro |
| **Salmón** | 35 | `#F87B5C` | `#FF987E` | **negro** / negro |
| **Grafito** | — (neutro) | `#161616` | `#EEEEEE` | blanco / negro |

**Los valores están generados, no elegidos a ojo** — [`frontend/scripts/generate-theme-tokens.py`](../frontend/scripts/generate-theme-tokens.py) los calcula y verifica. Para cambiar un tema, edita la tabla `THEMES` del script y regenera; **no edites `style.css` a mano.** El script se comprobó reproduciendo el CSS actual token por token (12 bloques, 0 diferencias).

Tres cosas que el script resuelve y que a mano se rompen:

1. **Gamut por hue.** El chroma máximo de sRGB depende del tono: a L=0.556 el violeta llega a 0.275, el naranja solo a 0.125 y el verde menta a 0.115. Un "cambio de hue" reusando el chroma del violeta saca del gamut a la mitad de los temas y el navegador recorta a un color sucio. Por eso cada tema trae su propio par L/C — Sol y Salmón ya salieron recortados automáticamente.
2. **`--primary-foreground` medido, no supuesto.** Con texto blanco encima, **salmón da 2.52 y sol 2.66**: ambos reprueban WCAG AA. Esos dos llevan texto oscuro. Los 12 pares tema×modo pasan AA; el más bajo es 4.97 (carmesí claro).
3. **Grafito invierte.** Negro en claro, blanco en oscuro — no es estética: un primario `L=0.20` sobre el fondo oscuro da contraste **1.45**, invisible. Invertido da 17.10. Su rampa completa va en chroma 0; aplicarle la rampa de los demás sobre hue 0 le daría acentos rojizos.

**`--primary` rellena; `--brand-icon` entinta.** Son dos usos distintos y un solo token no cubre los dos: sol, verde y salmón tienen primarios **claros a propósito** (llevan texto oscuro encima), y usados como tinta sobre el sidebar casi blanco dan **2.31, 2.90 y 2.20** — bajo el mínimo de 3.0 para íconos y controles. `--brand-icon` es el mismo tono a `L=0.50` en modo claro (peor caso **4.82**) y el propio primario en oscuro (5.07 a 15.48, todos holgados); grafito conserva su negro (17.34), porque bajarlo a gris medio le quitaría lo que lo define. **Regla práctica:** `bg-primary` + `text-primary-foreground` para superficies rellenas (botones, muestras); `text-brand-icon` para íconos y texto de acento sobre fondo claro. Los 41 usos de `text-primary` que había en la app se migraron a `text-brand-icon` — ninguno estaba sobre relleno sólido, se verificó antes de barrer. En el mismo paso se eliminaron los `bg-purple-100`/`text-purple-700` **quemados** que quedaban en cuatro pantallas: nunca habrían seguido al tema.

**Escalas derivadas:** `--brand-hue` y `--brand-chroma` existen para los componentes con escala propia que no usa tokens del sistema — hoy solo el calendario ([`DateRangePicker.vue`](../frontend/src/components/DateRangePicker.vue)), que sin ellos se quedaría púrpura mientras el resto de la app cambia de color.

**Persistencia:** `localStorage`, clave `tiendapi-color-theme`, separada de la del modo (`tiendapi-theme`). Se aplica desde [`main.ts`](../frontend/src/main.ts) y no desde una vista, para que valga también en el **login** (si cuelga de una pantalla, solo se aplicaría al llegar a ella).

⚠️ **Trampa de cascada, documentada porque ya mordió una vez:** `.dark` y `[data-theme="x"]` tienen la **misma especificidad** (0,1,0), y los bloques de tema claro van después en el archivo. Los tokens de `accent` oscuros **deben** declararse en los bloques oscuros; puestos en el `.dark` general, el accent claro (casi blanco) les gana y los hover quedan encandilando sobre fondo negro.

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
| **Búsqueda / autocompletado por SKU** | `popover` (+ `input`) — ver §6.2; `command` NO se usa acá |
| **Listados y tablas** (Productos, histórico de Facturas) | `table`, `pagination`, `scroll-area`, `skeleton` |
| **Modales y confirmaciones** (anular factura, D-35) | `dialog`, `alert-dialog`, `sheet` |
| **Feedback al usuario** | `sonner` (toasts, dep. `vue-sonner`), `alert`, `progress`, `tooltip` |
| **Navegación / layout** | `sidebar`, `breadcrumb`, `tabs`, `separator`, `collapsible`, `dropdown-menu` |
| **Dashboard** | `card`, `chart`, `badge`, `avatar`, `button` |

⚠️ **`number-field` está deliberadamente excluido.** Vincula su valor a un `number` de JavaScript (punto flotante), lo que choca de frente con la regla del proyecto de manejar **dinero con Decimal.js** ([CLAUDE.md](../CLAUDE.md), zonas de alto riesgo). Para importes usar `input` de texto + validación Zod + `Decimal`, nunca un binding numérico nativo. Para cantidades enteras sí sería admisible, pero se dejó fuera para no inducir el mal uso.

**Pendiente de decidir:** `calendar` / date-picker para filtrar el histórico de Facturas por fecha — no instalado porque arrastra `@internationalized/date`; se instalará cuando se especifique ese filtro.

## 6.2 Patrón: autocompletado contra el servidor (D-91)

Un campo que busca en una tabla grande —Referencias, Clientes— se arma **siempre** así: `Popover` + `PopoverAnchor` + un `Input` normal + una lista propia de `<button>`. La consulta la hace el servidor con debounce, y el resaltado por teclado se lleva a mano.

⚠️ **No se usa `command` para esto.** `CommandInput` filtra **en el cliente** sobre los items ya montados: con miles de filas que viven en el servidor y llegan paginadas, filtrar sobre la página en memoria devuelve "sin resultados" para casi todo. `command` queda reservado para paletas de comandos y listas cerradas y cortas.

Reglas del patrón, las tres por una razón concreta:

1. **Al enfocar se muestran resultados aunque el campo esté vacío.** Es lo que le enseña al usuario que el campo busca, en vez de que lo descubra al tercer carácter. El término vacío se permite **solo desde el foco**, nunca desde el tecleo: cuando un formulario se resetea el valor vuelve a `""` y el watcher abriría el popover encima del formulario recién limpiado.
2. **Sin coincidencias no se abre un popover vacío.** Que no exista es un caso normal al dar de alta; un cartel de "sin resultados" es ruido.
3. **El foco se queda en el input** (`@open-auto-focus.prevent`): hay que poder seguir escribiendo con la lista abierta.

Se emite la **entidad entera**, no solo el texto, para que quien lo use decida — el alta de Referencia la usa para ofrecer crear una variante (D-90) y precargar la ficha.

| Componente | Busca | Reemplaza |
|---|---|---|
| `components/ReferenceSearchInput.vue` | Referencias por SKU **o** nombre | el par de campos "SKU" + "Nombre producto" |
| `pages/pos/CustomerAutocomplete.vue` | Clientes por cédula **o** nombre | — |

## 7. Pantalla Dashboard (métricas generales) — diseño y definiciones

> **Estado: dentro del alcance del MVP (D-51).** Forma parte de las 5 pantallas del MVP ([05](05-alcance-mvp-y-flujos.md), §2.1) — corrige la nota anterior que la marcaba como "post-MVP" cuando solo existía la primera iteración de 3 pantallas (D-14).
>
> ⚠️ **Esta sección fue reescrita por D-66 y D-67, y su selector por D-69.** El Dashboard **ya no es** el roll-up financiero encabezado por Margen % que definía D-49: es un tablero **operativo de producto** (decisión del dueño de producto, D-66). El catálogo de fórmulas de D-49 sigue vigente para las **otras** pantallas, con la corrección de Utilidad de D-67. El selector de período (Hoy · Semana · Mes) que describía la §7.3 original fue reemplazado por un **rango de fechas libre** (D-69) — ver esa sección para el layout vigente.

### 7.1 Principio de organización: flujo vs. foto vs. cruce

Cada métrica vive donde su **naturaleza** corresponde, no todas juntas:

- **Flujo de ventas** (lo que pasó por caja en un período) → pantalla **Facturas**.
- **Foto de inventario** (lo que hay parado *ahora*) → pantalla **Productos**.
- **Cruce demanda × stock** (lo que ninguna pantalla sola puede responder) → pantalla **Dashboard**.

**Regla de no duplicación (D-66):** el Dashboard **no repite** las cards de los otros módulos. Su valor no está en resumir lo que ya se ve en otro lado, sino en el cruce que ningún módulo puede hacer solo: qué se vende contra qué queda en el estante. La **única** cifra compartida es el total facturado del período, y va **integrada como titular del gráfico**, no como card propia.

**El Margen % no vive en el Dashboard** (D-66) — se queda en Facturación. Razón registrada: exige demasiada explicación para el perfil de usuario (dueño de mostrador), que lee "cuánto vendí y qué me falta", no un ratio. Objeción anotada en D-66: el tablero pierde toda lectura de rentabilidad.

### 7.2 Métricas y fórmulas (fijadas en D-49)

| Métrica | Fórmula | Naturaleza | Pantalla natural |
|---|---|---|---|
| **Total facturado** | Σ `Bill.total` (con IVA) | Flujo · período | Facturas |
| **IVA recaudado** | Σ `Bill.total_iva` | Flujo · período | Facturas |
| **Utilidad** ⚠️ | Σ (`BillItem.unit_price` **con IVA** − `Item.provider_price` **sin IVA**) × qty — margen de caja, no utilidad neta contable (**D-70**, revierte el cálculo de D-67; ver A-26) | Flujo · período | Facturas |
| **Margen %** | Utilidad / facturado **sin** IVA — sin implementar todavía (no existe en `bills.py`); si se construye, hereda el criterio de D-70: Utilidad ya trae el IVA adentro | Ratio transversal | **Dashboard** |
| **Ticket promedio** | Total facturado / N° facturas | Flujo · período | Dashboard / Facturas |
| **N° de facturas** | count(`Bill`) en el período | Flujo · período | Dashboard / Facturas |
| **Valor de bodega** | Σ `Item.provider_price` WHERE `status='available'` (**a costo**) | Foto de inventario | Productos |
| **Unidades disponibles** | count(`Item` WHERE `status='available'`) | Foto de inventario | Productos |
| **Facturas sin declarar (DIAN)** | count(`Bill` WHERE `fiscal_status` ∈ {contingencia, pendiente}) | **Alerta** (sano = 0) | Banner condicional (D-48) |

> ⚠️ **Sección histórica — el cálculo que proponía D-67 fue revertido por D-70.** D-67 había auditado que la Utilidad de D-49 mezclaba un ingreso con IVA contra un costo sin IVA (+57% con IVA 19%) y propuso restar el IVA también del lado del ingreso. D-70 revierte esa parte a propósito: la Utilidad se queda como margen de caja (ingreso con IVA − costo sin IVA), decisión de producto confirmada con el usuario base. **Bodega a costo:** valorar a `provider_price` (capital inmovilizado real), no a precio de venta (proyección optimista). A-26 (con/sin IVA en `provider_price`) está **resuelto** — ver esa fila más arriba y D-70.

### 7.3 Layout del Dashboard (D-66, selector reescrito por D-69)

Cuatro bloques, todos centrados en producto. Coherente con la regla 90/7/3 — el púrpura primario resalta **un solo** número por pantalla.

**Selector de rango** arriba: un datepicker de rango libre (D-69), sobre **V-Calendar** en vez del `RangeCalendar` de shadcn/reka-ui — mismo componente que ya usaba Facturas, unificado en uno solo. Reemplaza al selector fijo Hoy/7 días/30 días de D-66: con rango libre el dueño puede comparar, por ejemplo, un fin de semana específico contra otro, no solo ventanas móviles predefinidas. Por defecto trae los últimos 30 días. Afecta al gráfico, a los tiles de venta y al Top; el stock es una foto y no cambia con él (indicarlo visualmente).

**Granularidad derivada, no elegida (D-69).** El ancho de cada barra/bucket lo decide el servidor según el largo del rango — **no** es un control aparte: 1 día → por hora · hasta ~2 meses → por día · más de eso → por semana. Dejarlo a criterio del cliente permitiría pedir un rango de un año con buckets de una hora, que ni se calcula razonable ni se lee.

**Techo de rango (D-69).** El servidor limita la consulta a 366 días y recorta el extremo que se pase; si el rango pedido excede el tope, el que vuelve en la respuesta es el efectivamente medido — la UI lo refleja tal cual, no lo que el usuario haya seleccionado.

**1. Dos gráficos lado a lado**, sobre la misma grilla de tiempo para que un pico en uno se lea contra el mismo día en el otro (D-68). Comparten la granularidad que resuelve el servidor.

- **Ventas del período**, en **barras** (D-69, revierte la línea de D-66). El eje son días cerrados y no una señal continua: una línea interpola entre dos días y sugiere una pendiente que no existe. **Sin serie de "período anterior" superpuesta** — con rango libre el usuario ya eligió explícitamente qué ventana mirar, y la comparación automática contra "el período anterior" de un rango arbitrario no es una pregunta que el selector deje formular con la misma claridad que Hoy/Semana/Mes. El **total facturado va como titular** — la única cifra que el Dashboard comparte con otro módulo (D-66).
- **Entra vs. sale.** Sigue en líneas (no barras): acá lo que importa es **dónde se cruzan** dos series, y una línea lo muestra donde una barra no puede. Unidades **ingresadas a bodega** contra **vendidas**, armado con el patrón `dataset` + `transform: {type:'filter'}` de ECharts (D-68): una fuente en formato largo que se filtra en dos series. Sin relleno de área en ninguna — dos áreas del mismo hue emborronarían justo el cruce. Responde "¿estoy comprando más de lo que vendo?", que es una pregunta de plata aunque el eje sea de unidades: inventario que crece es capital quieto en un estante. Es el reverso de "Reponer ya", que mira lo que falta. Lleva el veredicto **escrito** en la cabecera ("Entraron 437 unidades más de las que salieron") porque dos totales sueltos obligan a compararlos mentalmente. Las dos series se distinguen por **trazo** (punteada vs. sólida) además del color: toda la paleta de gráficos es del mismo hue púrpura y dos tonos no se separan a simple vista (§5 — nunca el color como único indicador).

**2. Cuatro tiles de producto**

| Tile | Qué responde |
|---|---|
| Unidades vendidas | el pulso de volumen del período |
| Referencias distintas vendidas | cuánto del catálogo se movió de verdad |
| Agotados con demanda | número de alarma — engancha con el bloque 4 |
| Sin rotación (+90 días) | catálogo muerto ocupando estante |

**3. Top productos vendidos** — foto, SKU, nombre, unidades y facturado. Ordenado por unidades.

**4. "Reponer ya"** — el bloque que justifica la pantalla: cruza demanda reciente contra stock disponible.
- **Ordena internamente por días de cobertura** (`unidades disponibles ÷ velocidad diaria del período`), ascendente; los agotados con ventas recientes van de primeros.
- **Muestra el par crudo, no el ratio:** *"quedan 2 · vendiste 14 este mes"*. La frase no necesita explicación y el orden inteligente queda debajo sin que el usuario tenga que entenderlo.

**Banner de alerta fiscal (condicional, D-48):** solo si la integración DIAN está viva **y** hay facturas sin declarar. Tono de advertencia, **fuera** de la grilla (es alarma, no analítica).

**Codificación por tipo de dato:** tono de acento distinto según sea **plata** / **conteo** / **alarma**, para escanear sin leer cada label. Nunca usar solo color como indicador (acompañar de ícono, §5).

> **Retirado del layout (D-67):** la card **"Descuentos otorgados"** que proponía la versión anterior de esta sección es **inconstruible** — no existe columna de descuento: la caja lo aplica dentro de `unit_price` antes del checkout y el dato se pierde.

> **Nota de implementación — los gráficos usan Apache ECharts (D-68), no `@unovis/vue`.** unovis sigue en el `package.json` porque lo usa el bloque de ejemplo de shadcn, pero **no dibuja nada** en este montaje: `VisXYContainer` recibe la data y los accessors correctos (verificado en runtime — 30 puntos, `x`/`y` devolviendo valores válidos) y aun así sus escalas se quedan en el `[0, 1]` por defecto, sin líneas, sin ticks y sin un solo error en consola; pasar `x-domain`/`y-domain` explícitos tampoco las mueve. ECharts se monta a mano desde el composable `useECharts` (sin `vue-echarts`) con importación selectiva de módulos, porque todo lo que entre al bundle viaja en el instalador Tauri (D-29/D-31). Ojo con dos cosas al tocar estos gráficos: ECharts pinta sobre canvas y **no entiende `var(--primary)`** —hay que resolver el token con `resolveCssColor`—, y el `<div>` del canvas debe seguir montado aunque no haya datos (el aviso de vacío va **encima**, no en su lugar), o al volver los datos el gráfico monta sobre un contenedor de alto cero.

### 7.4 Íconos sugeridos (`@lucide/vue`, el set de shadcn/vue)

**Dashboard (D-66/D-68):** `trending-up` (gráfico de ventas) · `arrows-up-down` (Entra vs. sale) · `package` (Unidades vendidas) · `layers` (Referencias distintas) · `package-x` (Agotados con demanda) · `clock-alert` (Sin rotación) · `trophy` (Top productos) · `truck` (Reponer ya).

**Otras pantallas:** `receipt` (Total facturado) · `landmark` (IVA) · `piggy-bank` (Utilidad) · `chart-pie` (Margen %) · `shopping-bag` (Ticket promedio) · `files` (N° facturas) · `warehouse` (Valor de bodega) · `file-clock` / `file-warning` (Facturas sin declarar — solo en el banner).

### 7.5 Dependencias (qué falta para que cada card muestre datos reales)

> **Nota saneada por D-67.** La versión anterior afirmaba que Utilidad / Margen / Valor de bodega estaban bloqueados por **A-25** — pero A-25 quedó resuelto por **D-52** (captura 100% manual). Esas tres nunca estuvieron bloqueadas; la nota estaba vencida.

- **Todo el Dashboard de D-66** → **calculable ya**, sin migraciones: demanda vía `BillItem → Item → Reference`, stock vía `count(Item WHERE status='available')`, eje temporal vía `Bill.created_at`. Las facturas anuladas (`voided_at`) se excluyen de toda cifra, igual que en `bills_summary`.
- **Utilidad, Margen %, Valor de bodega** (pantallas Facturas / Productos) → **calculables, A-26 resuelto** (D-70): `provider_price` se captura sin IVA. Además, `units_without_cost` debe mostrarse junto al margen — si es > 0, la cifra está incompleta.
- **Facturas sin declarar** → depende de `Bill.fiscal_status` (D-48) y de la integración DIAN (D-09/D-38, diferida). Es alerta, no card.
- **Descuentos otorgados, ventas por método de pago, ventas por cajero** → **no calculables**: no hay columna de descuento en `BillItem`, el efectivo recibido no se persiste (el checkout lo descarta) y `Bill` no tiene FK al usuario que vendió. Requieren esquema nuevo.

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
