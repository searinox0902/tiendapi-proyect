# 05 — Alcance del MVP y Flujos

> **Contexto:** Qué entra (y qué no) en el MVP, el flujo operativo principal y la estrategia de facturación electrónica DIAN. Cárgalo para definir scope y roadmap funcional.

## 1. Objetivo del MVP

Un sistema de gestión comercial **de escritorio** que resuelva las fallas del software actual, **sin** la complejidad de un ERP completo. Visión original de **tres funcionalidades core**, de las cuales **dos** entran en el MVP (D-52):

1. ~~**Carga y parseo automático de XML** de proveedores → creación/actualización de referencias.~~ **Diferido post-MVP** (D-52) — en el MVP, las Referencias se crean **únicamente de forma manual** vía CRUD Referencia (D-51).
2. **Búsqueda y autocompletado de referencias** (incluye lectura por **escáner de código de barras**).
3. **Generación rápida de facturas** con cálculos automáticos (totales, impuestos, descuentos).

## 2. Secuencia de pantallas — primera iteración del MVP

> **Fuente:** [`specs/Addendum_2026-07-01_MVP_Pantallas_UI.md`](../specs/Addendum_2026-07-01_MVP_Pantallas_UI.md). Ver decisiones D-14/D-15 y puntos abiertos A-08/A-09 en [07 — Decisiones](07-decisiones-y-puntos-abiertos.md).

Antes de construir el flujo completo (§3 más abajo), la primera iteración prototipable/entregable del MVP se reduce a **tres pantallas concretas**, en este orden:

### Pantalla 1 — Inicio de sesión (sesión simulada / mock)
- El usuario "inicia sesión", pero en esta iteración **no requiere conexión real a un backend de autenticación**.
- Es un **mock local**: el cliente simula un usuario autenticado (estado en memoria/local) para poder navegar el resto de la app.
- **Motivo:** validar el flujo de navegación y la UX sin bloquear el desarrollo por la integración de auth real.
- **A reemplazar más adelante** por el mecanismo real de sesión/licencia descrito en [04 — Seguridad](04-seguridad.md) (token firmado por servidor, validación de licencia, gracia offline). No confundir esta sesión mock con el modelo de seguridad definitivo.

### Pantalla 2 — Registrar Referencia
- Formulario de alta de una **Referencia** (producto/catálogo): nombre, SKU (`reference_id`), descripción, imagen, categoría, precio base y IVA — según el modelo `Reference` en [03 — Modelo de datos](03-modelo-datos.md).
- Es la vía manual de creación de catálogo, complementaria a la carga automática por XML (§1, punto 1).

### Pantalla 3 — Registrar Pago
- Pantalla para registrar un pago/cobro simplificado.
- El usuario **ingresa o busca una Referencia**; si esta **ya existe en el catálogo, sus datos se autocompletan** (nombre, precio base, IVA), evitando reescritura manual.
- Este es el mismo mecanismo de **autocompletado de referencias** que ya forma parte de la propuesta de valor central del producto (ver [01 — Visión de negocio](01-vision-negocio.md), §5) y del flujo de facturación (§3 más abajo).

```
Pantalla 1                Pantalla 2                    Pantalla 3
Inicio de sesión  ──►   Registrar Referencia   ──►   Registrar Pago
 (sesión mock,             (alta manual de              (busca/ingresa Referencia
  sin backend)              producto/catálogo)           → autocompleta si existe)
```

> Esta secuencia es la **primera entrega navegable** del MVP, no reemplaza el flujo funcional completo (carga XML → autocompletado en venta → facturación) descrito en §3, que sigue siendo el objetivo final del MVP.

### 2.1 Alcance final de pantallas del MVP (D-51)

Más allá de la primera iteración navegable (§2, D-14), el **alcance completo de pantallas del MVP** queda fijado en **5 pantallas**:

1. **Inicio de sesión** (mock en esta iteración, D-15; a reemplazar por auth real, D-36/A-10).
2. **CRUD Referencia** — evolución de "Registrar Referencia" (Pantalla 2, §2) a alta/edición/listado completo del catálogo (`Reference`, D-11).
3. **CRUD Productos** — gestión de `Item` (unidad física individual, D-41): alta de N unidades, ajuste de `current_price`/`provider_price` por unidad, cambio de `status`. Pantalla natural de "Unidades en stock"/"Valor de bodega" (D-49).
4. **Facturas** — evolución de "Registrar Pago" (Pantalla 3, §2) a alta de factura + listado/histórico. Pantalla natural de "Total facturado"/"IVA recaudado"/"Utilidad" (D-49).
   > **Exportación empaquetada (D-78):** la pantalla gana un export **reactivo a sus filtros** (rango de fechas, estado fiscal, cliente, código) que entrega un **zip = Excel índice + un PDF por factura**, con nombre y ruta de cada archivo en el Excel. No contradice D-61: lo que D-61 prohíbe es que **el sistema** persista un espejo del documento junto al registro; acá el **usuario** se lleva un corte que él mismo filtró, con fecha de generación y el sello de "no válido ante la DIAN" en cada PDF. Sigue rigiendo la asimetría de D-73: **las facturas salen, nunca entran.**
5. **Dashboard** — métricas generales ([09 — Diseño UI/UX](09-diseno-ui-ux.md), §7; D-49). **Corrige el estado "post-MVP" que tenía asignado antes de esta decisión** — entra en el MVP.

**Explícitamente fuera del MVP:**
- ~~**Configuraciones** — pantalla de ajustes del sistema/negocio.~~
  > ⚠️ **Revertido por D-77.** La pantalla **entra**, pero acotada: hoy no es un panel de ajustes del sistema, es donde viven las operaciones que afectan al **negocio entero** y no a un módulo. Entró porque el respaldo del proyecto completo (nivel 1 de D-73) no tenía dónde ubicarse sin forzarlo dentro de un módulo al que no pertenece. Los "ajustes del sistema/negocio" genéricos siguen fuera del MVP.
- **El constructor de árbol de categorías** (D-41/D-42/D-43: jerarquía por `parent_id`, agregar/renombrar/importar-exportar) sigue fuera — y de hecho nunca se implementó en el modelo (`Category` hoy es plana: `name` + `description`, sin `parent_id`). CRUD Referencia solo **asigna** una categoría ya existente.
  > ⚠️ **Matizado por D-71.** La entrada original de esta fila decía "crear categorías... queda fuera... no crearlas... desde la UI", sin distinguir el árbol (excluido) del alta simple (no lo estaba conceptualmente, solo no existía dónde ponerla). D-71 agrega esa alta plana —nombre + descripción, sin jerarquía— al Directorio, junto a Proveedor/Ubicación/Cliente/Marca. Sigue sin existir el árbol, el drag-and-drop ni el import/export.
- **Reportes DIAN** — coherente con la integración DIAN diferida (§4, D-09/D-38); `Bill.fiscal_status` queda reservado (D-48) pero sin pantalla de reportería en el MVP.

## 3. Flujo funcional completo (objetivo final del producto — pasos 1-2 diferidos post-MVP, D-52)

1. ~~El negocio recibe el **XML del proveedor** y lo carga al sistema.~~ **Diferido post-MVP (D-52)** — en el MVP, este paso no existe; la Referencia ya está creada manualmente (CRUD Referencia, D-51) antes de llegar aquí.
2. ~~El sistema **parsea el XML** y crea/actualiza referencias automáticamente.~~ **Diferido post-MVP (D-52)**.
3. Al facturar, el usuario **busca o escanea** la referencia (autocompletado).
4. El sistema **calcula totales automáticamente** (Decimal.js en cliente).
5. La factura se **prepara para el proveedor tercero** de facturación electrónica (integración futura).
6. La **copia firmada (XML + PDF)** se almacena localmente y entra en la sincronización.

```
XML proveedor ──► Parseo ──► Crea/actualiza Referencias
                                     │
Venta ──► Busca/Escanea ──► Autocompleta ──► Calcula totales
                                     │
                              Prepara factura ──► (3.º DIAN, futuro)
                                     │
                       Copia firmada (XML+PDF) ──► Local + Sync
```

## 4. Facturación electrónica (DIAN) — integración futura

> **Fuera del MVP.** Alcance posterior.

La integración directa con la DIAN (certificado propio, firma, UBL 2.1, ambiente de habilitación) es un **esfuerzo regulatorio ajeno al valor del producto**. Se **delega a un facilitador externo** ya autorizado e integrado con la DIAN vía su API REST:

- El software **genera y calcula** la factura.
- El tercero la **firma y valida**.
- El sistema **almacena la copia firmada**.

**Candidatos a cotizar:** Alegra, Facturación.tech, Facturador.co.

> Decisión de proveedor pendiente y con impacto en pricing → ver [06 — Próximos pasos](06-equipo-riesgos-roadmap.md) y [01 — Modelo de negocio](01-vision-negocio.md).

## 5. Fuera de alcance del MVP (explícito)

- Integración directa con la DIAN (se delega, ver §4).
- Módulos de ERP completo (contabilidad, etc.). **Nómina ya no está en esta lista:** D-97 la reincorpora como **módulo post-MVP acotado** (mini-gestor que calcula, documenta y da visibilidad; **no** dispersa pagos ni transmite el documento soporte a la DIAN). Diseño completo en [13 — Módulo de Nómina](13-modulo-nomina.md); decisiones D-97 a D-102 y puntos abiertos A-34 a A-38 en [07](07-decisiones-y-puntos-abiertos.md). Sigue **fuera del MVP**: entra después de las fases F1–F4.
- Funcionalidades no relacionadas con los tres core (§1).
- Autenticación real / conexión a backend de sesión en la primera iteración de pantallas (§2) — se usa sesión mock; el backend real de auth es posterior.
- **Configuraciones, constructor de árbol de categorías y Reportes DIAN** (D-51, §2.1) — quedan fuera del alcance final de pantallas del MVP.
- **Carga y parseo automático de XML del proveedor** (D-52) — deferido post-MVP completo, no solo el auto-relleno de `provider_price`. En el MVP, Referencias e Ítems se crean **100% manual** (CRUD Referencia/Productos, D-51); `provider_price` (D-47) se captura siempre a mano, sin fuente XML todavía (cierra A-25).
- **Imágenes de producto** (D-40): fuera del MVP, *fast-follow* tras F2. Serán opcionales y con tres modos coexistentes — **local** (archivo en `appDataDir`, gratis, *best-effort*), **URL** (gratis, no offline) y **nube** (add-on de pago, F4+). En la UI del MVP se usa un ícono *placeholder* (`Package` de lucide), no una imagen real.
  - **Recorte 1:1 con `vue-advanced-cropper`** (D-50): el flujo de alta recorta la imagen a **aspect ratio 1:1** antes de guardarla, para que todas las imágenes de Referencias sean homogéneas en listados/tarjetas. El recorte ocurre **antes** de calcular el hash SHA-256 del nombre de archivo (D-40). Implementado como componente reusable `ImageDropCropper.vue` (dropzone → recorte → confirmación); la subida/persistencia real del archivo sigue diferida (D-40 fast-follow).
