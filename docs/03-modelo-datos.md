# 03 — Modelo de Datos

> **Contexto:** Entidades, relaciones y DDL de referencia. Cárgalo para trabajar en esquema, migraciones, ORM o queries.
> **Fuente:** `specs/Informe_Modelo_Datos.pdf` (definición en dbdiagram.io).

## 1. Entidades

### 1.1 Proveedor (`Provider`)
Empresa o persona que vende productos al negocio. Guarda nombre comercial, NIT, código interno y observaciones. Cada producto que entra al inventario está vinculado a un proveedor → siempre se sabe de dónde vino la mercancía.

### 1.2 Referencia (`Reference`)
El **"molde" o plantilla** de un producto: define *qué es*, no *cuánto hay*. Ej.: "Aceite Yamalube 1LT". Guarda nombre, descripción, imagen, código (SKU), **marca** (`brand`, ver abajo), **categoría** (FK a `Category`, ver 1.7), precio base y **porcentaje de IVA del catálogo** (`iva_percentage`). Tiene un **proveedor principal** asociado.

> **Marca vs. Proveedor (`brand`, D-57) — dos ejes distintos.** `brand` es **quién fabrica** el repuesto (NGK, Brembo, Motul); `provider_id` es **a quién se le compra**. No se derivan uno del otro: la misma bujía NGK puede llegar de tres distribuidores distintos, y un mismo distribuidor vende decenas de marcas. Es `NULL`-able porque hay repuestos genéricos sin marca reconocible. **Tampoco es la marca del vehículo compatible** — esa vive en `SpecProfile` (A-22, diferido), y en el vertical de repuestos ambas coexisten: unas pastillas *Brembo* para una *Honda CB190*.

> **Precio de venta a nivel de catálogo (`sale_price`, D-45):** además del `base_price` (pre-IVA), la Referencia expone `sale_price` = **precio de venta con IVA** = `base_price × (1 + iva_percentage/100)`, **redondeado al múltiplo de $50 más cercano** (D-46). **No es una decisión humana independiente**, es el cálculo hecho valor **derivado y persistido** (columna generada / auto-recalculada al cambiar `base_price` o `iva_percentage`) — nunca se edita a mano. Se persiste para que sea trazable desde el alta de la Referencia (hereda `updated_at`/`version`), no para poder divergir del cálculo. El ajuste humano de precio **no** vive aquí, vive en el Ítem (1.3).
>
> **Costo de adquisición (`precio_proveedor`, D-47) — lado opuesto, no confundir con `base_price`.** `base_price`/`sale_price` son lo que el negocio **cobra** (lado venta); `precio_proveedor` es lo que el negocio **paga** al `provider_id` principal para conseguirlo (lado compra) — dos números independientes que nunca se derivan uno del otro. A diferencia de `sale_price`, **no es una fórmula**: es un valor de entrada editable directamente, que sirve como costo **sugerido/por defecto** al crear nuevos Ítems de esta Referencia. El costo real de cada unidad física vive en `Item.precio_proveedor` (1.3), porque puede variar por distribuidor puntual. Mecanismo de captura (manual vs. XML del proveedor) sin decidir — ver A-25 en [07](07-decisiones-y-puntos-abiertos.md).

> **Idea central:** separar Referencia de Ítem evita crear un producto nuevo cada vez que llega un código de barras distinto para el mismo artículo. La Referencia es el punto fijo; lo que varía (existencias, precio actual, proveedor puntual) vive en el Ítem.

### 1.3 Ítem (`Item`)
**Una unidad física individual** de una Referencia — no un lote ni una cantidad. Cada `Item` es una fila propia, con su propio `id` (identidad única), su propia sucursal/bodega (FK a `Location`, ver 1.8), su propio precio de venta, su propio proveedor de origen y su propio estado (`disponible | vendido | reservado | de_baja`). Una Referencia puede tener **N Ítems** — ej. "Aceite Motul" con 24 unidades en stock son **24 filas `Item`**, cada una identificable y editable por separado (D-41).

> **Precio de venta de la unidad (`current_price`, D-45):** es el **precio de venta con IVA de ESTA unidad**. Se **inicializa** como espejo de `Reference.sale_price` al crear el Ítem, y es el **único lugar donde vive el ajuste humano** (descuento puntual a una unidad, D-41): es **mutable mientras `status = 'disponible'`** y se **congela al pasar a `vendido`**. Si nadie lo toca, al vender coincide con el precio de catálogo; si se editó (ej. "te lo dejo en $38.000"), diverge — y esa divergencia es justo lo que permite reportar descuentos otorgados sin reconstruir nada. El desglose base/IVA de esa venta **no** se guarda aquí, se deriva a la inversa en la línea de factura (1.6).
>
> **Costo real de la unidad (`precio_proveedor`, D-47).** Se **inicializa** como espejo de `Reference.precio_proveedor` (el costo sugerido del proveedor principal), pero es **editable independientemente por unidad** — la razón de fondo: la misma Referencia/SKU puede tener Ítems que llegaron de **distribuidores distintos** a costos distintos (ya soportado por `Item.provider_id`, que puede diferir del proveedor principal de la Referencia). Es lo que habilita el cálculo real de utilidad: `utilidad = (BillItem.unit_price − Item.precio_proveedor) × quantity`. No tiene relación con `current_price`/IVA — es un dato de costo puro, nunca se le aplica IVA.

> **Problema que resuelve:** control individual real — ajustar el precio de 1 sola unidad (descuento puntual), saber exactamente cuál unidad se vendió, o adaptarse a negocios donde cada unidad importa por sí misma (electrónica con serial, vehículos con VIN), sin depender de agrupaciones por lote.
>
> **Ítems no discretos (a peso/volumen, ej. "234gr de azúcar"):** no se catalogan como Referencia/Ítem — no son cantidades contables de forma fiable, y en un negocio pequeño/mediano pre-registrar existencias granulares es una carga operativa que no compensa. Se registran como **venta libre** directo en la factura, sin Ítem asociado (ver 1.6, D-42).
>
> **Criterio para decidir** si un producto va por Referencia+Ítem o por venta libre: ¿es *tangible, contable, medible, preciso y predecible* (ej. "Carenaje XTZ 250")? Si sí → Referencia+Ítem. Si no → venta libre.

**Por qué se llegó a este criterio (y no a serializar todo, ni a modelar un modo "a granel"):**

- **El punto de partida era distinto: se consideró serializar hasta lo más pequeño.** La primera idea fue que *todo* producto, sin excepción, tuviera identidad individual — incluso algo tan granular como un tornillo suelto. Se sostiene mientras la unidad de venta es discreta (un tornillo, una botella), pero se cae en cuanto el producto se vende **fraccionado sin una unidad fija** (gramos al ojo, litros a ojo): ahí no hay "unidad" que serializar, hay una masa continua que se corta en el momento de la venta.
- **Se consideró la alternativa intermedia — un modo "a granel" con cantidad aproximada en la Referencia — y se descartó.** Parecía razonable: una Referencia "Azúcar" con un `Item.quantity` decimal que baja con cada venta. Pero esa cantidad **nunca sería precisa** (nadie pesa perfecto a ojo, y nadie va a recontar el saco para corregir el sistema), así que el número en pantalla daría una **falsa sensación de control** — peor que no tener el dato, porque invita a confiar en algo que no es cierto.
- **La evidencia que lo confirmó fue el propio ejemplo del azúcar dividido en 100 bolsas de 1kg.** Es la prueba de que el criterio no depende del *producto* sino de su **estado físico al momento de vender**: la misma azúcar es "venta libre" cuando está suelta en el saco, y pasa a ser "Referencia+Ítem" en el instante en que alguien la empaca en unidades fijas y medidas. El fabricante (o quien empaca) es quien resuelve el problema de medición **de antemano**; si nadie lo resolvió antes de la venta, el sistema no debe fingir que lo resolvió.
- **La razón de negocio, no solo técnica, para no exigir ese empaquetado previo:** un negocio pequeño/mediano no va a detener el mostrador a pesar y embolsar con antelación solo para que el sistema tenga un número que mostrar. Eso es trabajo real, no gratis, a cambio de una precisión que de todas formas se perdería en la primera venta suelta. El criterio evita pedirle al dueño un esfuerzo que el propio negocio no necesita para operar.
- **Por qué "venta libre" no es una renuncia, sino la respuesta honesta:** para lo no discreto, lo único que **realmente** importa registrar es el hecho económico (se vendió, por tanto, a tanto precio) — no un inventario que nadie va a mantener exacto. Fingir precisión ahí sale más caro (en fricción operativa) que no tenerla.

### 1.4 Cliente (`Customer`)
Persona o empresa a quien se le vende. Guarda nombre completo, NIT (si aplica) y correo. Un Cliente puede tener **muchas Facturas**.

### 1.5 Factura (`Bill`)
Documento de venta. Guarda el número consecutivo visible, el subtotal antes de impuestos, el total de IVA y el total final. Cada Factura pertenece a **un único Cliente**. Incluye además los campos de integridad `hmac` y `prev_hash` (ver 1.9).

> **Estado fiscal (`fiscal_status`, D-48) — reservado, no operativo en el MVP.** Columna nullable (`contingencia | pendiente | autorizada | rechazada`) que anticipa el flujo de facturación electrónica DIAN (D-38): una factura emitida offline entra en `contingencia`/`pendiente` y pasa a `autorizada` al recibir el CUFE del `FiscalRecord` remoto. **Sin integración DIAN (diferida, D-09) el campo queda nulo** — se reserva ahora para no migrar `Bill` después. La métrica "facturas sin declarar" que lo consumiría es una **alerta de cumplimiento (valor sano = 0)**, no una card analítica: se surge como badge/banner condicional cuando la integración esté viva, no en la fila de métricas del MVP.

### 1.6 Línea de factura (`BillItem`)
Cada renglón de una Factura: qué Ítem se vendió, cuántas unidades, precio unitario, **porcentaje de IVA aplicado** (`iva_percentage`) y **monto de IVA resultante** (`iva_amount`, ver 1.9), y total de la línea. Una Factura puede tener **muchas líneas**. Como cada `Item` ahora es una unidad individual (1.3), vender N unidades de la misma Referencia genera **N líneas** (una por unidad), no una línea con `quantity=N`.

**Desglose base/IVA derivado a la inversa desde el total confirmado (D-45).** El precio que se confirma en la venta es el **precio final con IVA** (`Item.current_price`, potencialmente ya con descuento) — ese es *la verdad*, lo que realmente cambió de manos. Base e IVA **no** se guardan aparte y se cuadran después; se **derivan del total ya confirmado**:

```
total            = current_price × quantity        (el número confirmado, la fuente de verdad)
unit_price(pre-IVA por unidad) = round(total / (1 + iva_percentage/100)) / quantity
iva_amount       = total − round(total / (1 + iva_percentage/100))
```

Por construcción **`subtotal + iva_amount = total` siempre** — con o sin descuento, sin ramas condicionales (se aplica el inverso *siempre*, tenga o no descuento; sin descuento da el mismo resultado que el cálculo hacia adelante). Esto evita el bug que motivó la decisión: un `base + IVA` que sumado **no** concuerda con un total con descuento (factura inválida ante la DIAN, reportes internos descuadrados). El **redondeo** solo ocurre en la partición interna base/IVA de la línea, **nunca** en el total confirmado; la *regla* de redondeo exacta sigue en A-06.

**Descuento como dato informativo (D-45).** Cuando `current_price` se editó por debajo del precio de catálogo, la línea guarda `discount_amount` y `discount_percentage` **adicionales y puramente informativos** (reportería de "cuánto se dejó de cobrar", y campo `AllowanceCharge` del formato UBL cuando llegue la integración DIAN, D-09). **Nunca** alimentan el cálculo de `unit_price`/`iva_amount` — ese siempre parte del total confirmado, no del descuento.

**Venta libre (D-42):** `item_id` es **opcional**. Si la línea es de algo no catalogado (ítem a peso/volumen, o cualquier cosa sin Referencia previa), `item_id` queda nulo y se llena `description` (texto libre) en su lugar — siempre uno de los dos, nunca ambos vacíos ni ambos llenos. La factura sigue calculando subtotal/IVA/total igual; esa venta simplemente **no descuenta ningún inventario**.

### 1.7 Categoría (`Category`) — nueva entidad
Agrupa Referencias por tipo de producto (ej. "Lubricantes", "Ferretería"). Antes se referenciaba como `category_id` en `Reference` sin tabla propia; ahora es una entidad formal con `id`, `name` y `desc`.

**Jerarquía ligera y constructor libre (D-41, D-42, D-43):** `Category` incorpora `parent_id` opcional (auto-referencia, profundidad recomendada 2-3 niveles — ej. "Refacciones > Moto > Aceites") e `icon` (nombre de ícono, ej. lucide). El árbol es **construible directamente por el usuario del negocio** (agregar/quitar/renombrar nodos, sin drag-and-drop en esta iteración) — crear un nodo **nunca** asigna Referencias automáticamente; la asignación (`Reference.category_id`) sigue siendo manual. El árbol se puede **exportar/importar como archivo JSON portable** (serializado por nombre/estructura, no por UUID local — los IDs se regeneran al importar; requiere previsualización antes de aplicar), pensado como mecanismo de reuso entre negocios del mismo sector, no como feature de un plan superior (libre en todos los planes, D-44). Ver puntos abiertos A-23 (política de conflicto al importar y de reasignación al borrar una categoría con Referencias).

**Semillas por tipo de negocio (D-43):** en el onboarding, según `Tenant.business_type` (§9.1), se precarga un set inicial de categorías típicas del sector (ej. Frenos/Motor/Lubricantes para repuestos de vehículo; Abarrotes/Bebidas/Aseo para tienda de barrio; Medicamentos/Higiene para farmacia) — contenido semilla distinto, mismo esquema para todos.

### 1.8 Ubicación (`Location`) — nueva entidad
Representa una sucursal o bodega física. Antes se referenciaba como `location_id` en `Item` sin tabla propia; ahora es una entidad formal con `id`, `name`, `address` y `type` (`sucursal` | `bodega`), soportando de forma explícita la operación multi-sucursal.

### 1.9 Columnas transversales de integridad y sincronización
Todas las tablas incorporan `updated_at`, `version` y `synced_at` para soportar la estrategia de sincronización y resolución de conflictos descrita en [02 — Arquitectura](02-arquitectura.md), §7. Adicionalmente, `Bill` y `BillItem` —los "movimientos críticos" según [04 — Seguridad](04-seguridad.md)— incorporan `hmac` (firma del registro); `Bill` además incorpora `prev_hash` (hash de la factura anterior, cadena tipo libro contable).

## 2. Relaciones (lenguaje de negocio)

- Un **Proveedor** → muchas **Referencias** (catálogo) y muchos **Ítems** (lotes entregados).
- Una **Referencia** → muchos **Ítems** (existencias en distintas sucursales o lotes).
- Una **Categoría** → muchas **Referencias** (nuevo, antes implícito).
- Una **Ubicación** (sucursal/bodega) → muchos **Ítems** (nuevo, antes implícito).
- Un **Ítem** → muchas **Líneas de factura** (a medida que se vende).
- Un **Cliente** → muchas **Facturas** (historial de compras).
- Una **Factura** → muchas **Líneas de factura** (el "recibo" completo).

```
Category ──< Reference ──< Item >── Location
Provider ──< Reference        │
   └──────────< Item ─────────┘
                 │
                 └──< BillItem >── Bill >── Customer
```

## 3. Por qué el modelo encaja con el negocio

- **Evita duplicación** de productos ante nuevos códigos de barras (separación Referencia / Ítem).
- **Trazabilidad de proveedor** por existencia, incluso si el mismo producto llega de varias fuentes.
- **Multi-sucursal desde el diseño base**, ahora formalizado con la entidad `Location` referenciada desde `Item.location_id` (ver §6).
- **Historial de ventas por cliente** para análisis y fidelización.
- **Cálculo de IVA en dos niveles:** catálogo (`Reference.iva_percentage`) y línea de venta (`BillItem.iva_percentage` + `BillItem.iva_amount`), dando flexibilidad si el IVA cambia entre catalogar y vender, y trazabilidad exacta del monto cobrado por línea.

## 4. Notas de diseño ya resueltas

- **`Bill` no tiene `provider_id` y es correcto:** la Factura llega al Proveedor de forma indirecta vía `BillItem → Item → Provider`.
- **Relación circular corregida:** una versión anterior tenía `Customer.bill_id` → `Bill` mientras `Bill` ya apuntaba a `Customer` vía `customer_id`. La regla real es "un cliente tiene muchas facturas", por lo que **`Customer.bill_id` fue eliminado**. La versión de este documento es la correcta.

## 5. DDL — versión original (dbdiagram.io, histórica)

> Se conserva como referencia histórica de lo recibido originalmente. **No es el esquema vigente** — ver §6 para el DDL corregido y vigente.

```dbml
Table Provider {
  id UUID [pk]              // ID único del proveedor
  provider_id varchar       // Código interno
  nit varchar               // NIT
  title varchar             // Nombre comercial
  desc varchar              // Observaciones
  created_at timestamp      // Fecha de creación
}

Table Reference {
  id UUID [pk]                              // ID único de la referencia
  provider_id UUID [ref: > Provider.id]     // Proveedor principal
  image_url varchar                         // URL de la imagen
  reference_id varchar                      // SKU o código
  title varchar                             // Nombre del producto
  desc varchar                              // Descripción
  base_price decimal                        // Precio base
  iva decimal                               // IVA (%)
  category_id UUID                          // Categoría (sin tabla propia)
  created_at timestamp                      // Fecha de creación
}

Table Item {
  id UUID [pk]                              // ID único del inventario
  reference_id UUID [ref: > Reference.id]   // Referencia asociada
  provider_id UUID [ref: > Provider.id]     // Proveedor del que llegó ESTE ítem
  location_id UUID                          // Sucursal o bodega (sin tabla propia)
  quantity decimal                          // Existencia disponible
  current_price decimal                     // Precio actual de venta
  created_at timestamp                      // Fecha de creación
}

Table Bill {
  id UUID [pk]              // Factura
  customer_id UUID          // Cliente
  bill_number varchar       // Consecutivo visible
  subtotal decimal          // Antes de impuestos
  total_iva decimal         // Total IVA
  total decimal             // Total final
  created_at timestamp      // Fecha de emisión
}

Table BillItem {
  id UUID [pk]                          // Línea de factura
  bill_id UUID [ref: > Bill.id]         // Factura padre
  item_id UUID [ref: > Item.id]         // Item vendido
  quantity decimal                      // Cantidad vendida
  unit_price decimal                    // Precio unitario
  iva decimal                           // IVA aplicado (ambiguo: ¿% o monto?)
  total decimal                         // Total de la línea
  created_at timestamp
}

Table Customer {
  id UUID [pk]
  nit number                            // Inconsistente con Provider.nit (varchar)
  fullname varchar
  mail varchar
  created_at timestamp
}
```

## 6. DDL — versión corregida y vigente

> **Fuente canónica del esquema.** Corrige las observaciones de la versión original (§5); el detalle de cada corrección está en §7.

```dbml
Table Provider {
  id UUID [pk]                    // ID único del proveedor
  provider_id varchar             // Código interno
  nit varchar(20)                 // NIT — varchar en todo el esquema (soporta dígito de verificación / ceros a la izquierda)
  title varchar                   // Nombre comercial
  desc varchar                    // Observaciones
  created_at timestamp            // Fecha de creación
  updated_at timestamp            // Última modificación local (sync)
  version int                     // Control de versión (resolución de conflictos)
  synced_at timestamp             // Última sincronización exitosa con el servidor
}

Table Category {
  id UUID [pk]                    // ID único de la categoría
  name varchar                    // Nombre (ej. "Lubricantes", "Ferretería")
  desc varchar                    // Descripción
  created_at timestamp
  updated_at timestamp
  version int
  synced_at timestamp
}

Table Location {
  id UUID [pk]                    // ID único de la ubicación
  name varchar                    // Nombre de sucursal/bodega
  address varchar                 // Dirección física
  type varchar                    // 'sucursal' | 'bodega'
  created_at timestamp
  updated_at timestamp
  version int
  synced_at timestamp
}

Table Reference {
  id UUID [pk]                              // ID único de la referencia
  provider_id UUID [ref: > Provider.id]     // Proveedor principal
  category_id UUID [ref: > Category.id]     // Categoría (ahora con tabla propia)
  image_url varchar                         // URL de la imagen
  reference_id varchar                      // SKU o código
  title varchar                             // Nombre del producto
  brand varchar [null]                      // Marca del FABRICANTE del repuesto (NGK, Brembo). Distinta de provider_id (a quién se le compra) y de la marca del vehículo compatible (A-22). Nullable: hay repuestos genéricos (D-57)
  desc varchar                              // Descripción
  base_price decimal(12,2)                  // Precio base, PRE-IVA (escala monetaria explícita)
  iva_percentage decimal(5,2)               // % de IVA de catálogo (ej. 19.00) — antes "iva", ahora sin ambigüedad
  sale_price decimal(12,2)                  // Precio de venta CON IVA = base_price × (1 + iva_percentage/100), redondeado al múltiplo de $50 (D-46). DERIVADO y persistido: columna generada / auto-recalculada, nunca editable a mano (D-45)
  precio_proveedor decimal(12,2)            // Costo sugerido/por defecto (lado COMPRA, no confundir con base_price/sale_price que son lado venta). Entrada editable directa, NO derivada. Default al crear nuevos Ítems (D-47)
  created_at timestamp                      // Fecha de creación
  updated_at timestamp
  version int
  synced_at timestamp
}

Table Item {
  id UUID [pk]                              // Identidad de ESTA unidad física individual (D-41)
  reference_id UUID [ref: > Reference.id]   // Referencia asociada (el "molde")
  provider_id UUID [ref: > Provider.id]     // Proveedor del que llegó ESTA unidad
  location_id UUID [ref: > Location.id]     // Sucursal o bodega (ahora con tabla propia)
  status varchar                            // 'disponible' | 'vendido' | 'reservado' | 'de_baja' (D-41)
  current_price decimal(12,2)               // Precio de venta CON IVA de ESTA unidad. Inicializado = Reference.sale_price; mutable mientras status='disponible', congelado al vender (D-45)
  precio_proveedor decimal(12,2)            // Costo real pagado por ESTA unidad (lado COMPRA). Inicializado = Reference.precio_proveedor, editable independiente por unidad — permite distribuidores distintos al mismo SKU (D-47)
  created_at timestamp                      // Fecha de creación
  updated_at timestamp
  version int
  synced_at timestamp
}

Table Customer {
  id UUID [pk]
  nit varchar(20)                           // Unificado con Provider.nit (antes era `number`)
  fullname varchar
  mail varchar
  created_at timestamp
  updated_at timestamp
  version int
  synced_at timestamp
}

Table Bill {
  id UUID [pk]                              // Factura
  customer_id UUID [ref: > Customer.id]     // Cliente (ref explícita, antes implícita)
  bill_number varchar                       // Consecutivo visible
  subtotal decimal(12,2)                    // Antes de impuestos
  total_iva decimal(12,2)                   // Total IVA
  total decimal(12,2)                       // Total final
  fiscal_status varchar [null]              // RESERVADO (D-48): 'contingencia'|'pendiente'|'autorizada'|'rechazada'. Nulo hasta que exista la integración DIAN (D-09/D-38)
  hmac varchar                              // Firma HMAC del registro (integridad, ver 04-seguridad.md)
  prev_hash varchar                         // Hash de la factura anterior (cadena tipo libro contable)
  created_at timestamp                      // Fecha de emisión
  updated_at timestamp
  version int
  synced_at timestamp
}

Table BillItem {
  id UUID [pk]                              // Línea de factura
  bill_id UUID [ref: > Bill.id]             // Factura padre
  item_id UUID [ref: > Item.id, null]       // Item vendido — NULO si es venta libre, sin Referencia previa (D-42)
  description varchar [null]                // Texto libre — solo si item_id es nulo (venta libre, D-42)
  quantity decimal(12,3)                    // Cantidad vendida (venta libre: puede ser peso/volumen)
  unit_price decimal(12,2)                  // Precio unitario PRE-IVA — DERIVADO a la inversa del total confirmado con IVA (D-45), no capturado aparte
  iva_percentage decimal(5,2)               // % de IVA aplicado en esta línea — antes "iva", ahora sin ambigüedad
  iva_amount decimal(12,2)                  // Monto de IVA de la línea — DERIVADO: total − subtotal. Garantiza subtotal + iva_amount = total (D-45)
  total decimal(12,2)                       // Total de la línea CON IVA = current_price × quantity. LA FUENTE DE VERDAD (D-45)
  discount_amount decimal(12,2)             // Descuento aplicado sobre la línea — informativo (reporte + UBL AllowanceCharge); 0 si no hubo. NO alimenta el cálculo base/IVA (D-45)
  discount_percentage decimal(5,2)          // % de descuento — informativo (D-45)
  hmac varchar                              // Firma HMAC de la línea (movimiento crítico, ver 04-seguridad.md)
  created_at timestamp

  // CHECK: (item_id IS NOT NULL) XOR (description IS NOT NULL) — venta libre D-42
  updated_at timestamp
  version int
  synced_at timestamp
}
```

## 7. Correcciones aplicadas (registro de cambios sobre el DDL original)

> Cada observación detectada en la revisión previa fue resuelta directamente en el esquema (§6). Registradas también como decisiones D-17 a D-22 en [07 — Decisiones y puntos abiertos](07-decisiones-y-puntos-abiertos.md).

| # | Observación original | Corrección aplicada |
|---|----------------------|----------------------|
| 1 | `category_id` y `location_id` referenciaban tablas inexistentes | Se crearon las tablas **`Category`** y **`Location`**, con FK reales (`Reference.category_id → Category.id`, `Item.location_id → Location.id`) |
| 2 | `Provider.nit` era `varchar` y `Customer.nit` era `number` | Se unificó **`nit varchar(20)`** en ambas tablas |
| 3 | `iva` era ambiguo entre porcentaje y monto | En `Reference` y `BillItem` se renombró a **`iva_percentage decimal(5,2)`** (porcentaje, ej. `19.00`). En `BillItem` se agregó **`iva_amount decimal(12,2)`** (monto resultante de aplicar el porcentaje a esa línea), quedando ambos conceptos explícitos y sin ambigüedad |
| 4 | Faltaban columnas de integridad/sync exigidas por [04 — Seguridad](04-seguridad.md) | Se agregó **`updated_at`, `version`, `synced_at`** a **todas** las tablas (soporte de sincronización y resolución de conflictos); y **`hmac`** a `Bill`/`BillItem` (movimientos críticos) más **`prev_hash`** en `Bill` (cadena de hash tipo libro contable) |
| 5 | No había precisión/escala definida en los `decimal` | Se estandarizó: **dinero** `decimal(12,2)`, **cantidades** `decimal(12,3)` (soporta unidades fraccionarias como kg o litros), **porcentajes** `decimal(5,2)` |
| 6 | `Bill.customer_id` no tenía anotación de FK explícita | Se agregó `[ref: > Customer.id]` para que la relación quede formalizada en el diagrama |

## 8. Notas pendientes (no resueltas en esta corrección)

- **Regla de redondeo (D-46, quantum de negocio definido):** todo valor monetario de venta se redondea al **múltiplo de $50 COP más cercano** (todo importe termina en `…000`, `…050` o `…100`; empates de $25 hacia arriba). Es el menor efectivo práctico en Colombia. Aplica a `Reference.sale_price`, `Item.current_price` y los totales de línea/factura. Coherente con D-45: base e IVA se derivan del total **ya redondeado**, así que `subtotal + iva_amount = total` sigue cumpliéndose. La **implementación en el front (dónde/cuándo aplicarlo en la UI) queda diferida** por decisión de negocio — ver A-06 en [07](07-decisiones-y-puntos-abiertos.md). El desglose inverso (D-45, ver 1.6) además acota que el redondeo interno base/IVA ocurre solo en la línea, nunca sobre el total confirmado.
- **Ajuste de redondeo en efectivo a nivel de `Bill` (A-24, no decidido):** cuando el pago en efectivo se redondea a la denominación práctica (ej. a $50/$100), ¿se registra explícitamente `total_cobrado` vs. el total calculado y un `ajuste` (delta), o se cobra el total exacto? Propuesto en diseño, **no** resuelto. Mientras tanto, el prototipo de caja cobra el total exacto (guarda `received`, calcula el cambio, no redondea el total). Ver A-24 en [07](07-decisiones-y-puntos-abiertos.md).
- El **tipo `type` de `Location`** (`'sucursal' | 'bodega'`) quedó resuelto en el backend central (§9, D-25: enum Pydantic + `CHECK` en Postgres). Falta aplicar el mismo criterio en el SQLite local del escritorio cuando se implemente.
- **`Item` como unidad individual serializada, no lote (D-41):** cambio respecto a versiones previas de este documento, que describían `Item` como "existencia con `quantity`". Se elimina `Item.quantity`; se agrega `Item.status`. Ver 1.3 y el DDL en §6.
- **Venta libre sin Referencia previa (D-42):** `BillItem.item_id` es nulo cuando la línea es de algo no catalogado (típicamente algo a peso/volumen); se usa `BillItem.description` en su lugar. No se modela un modo "a granel" a nivel de `Reference`/`Item` (evaluado y descartado por YAGNI — la precisión que daría es ilusoria). Ver 1.6.
- **Imágenes de producto (D-40, esquema reservado, aún no implementado):** cuando se añada (fast-follow tras F2), `Reference` llevará `image_source` (`'local' | 'url' | 'cloud'`) + `image_ref` (hash SHA-256 para `local`/`cloud`, o la URL para `url`). **Nunca** el binario como BLOB en la base cifrada; los bytes viven en `appDataDir` (local), externos (URL) o en nuestros servidores (nube de pago). No se agrega la columna todavía (YAGNI); solo queda reservado el diseño para que la migración futura sea limpia.
- **Estado fiscal DIAN (`Bill.fiscal_status`, D-48, columna reservada):** ya presente en el DDL (§6) como campo nullable, pero **no operativa en el MVP** — sin la integración DIAN (diferida, D-09/D-38) queda nula. Se reserva para anticipar el flujo de autorización fiscal (contingencia offline → autorizada con CUFE) sin migrar `Bill` (tabla con `hmac`/`prev_hash`) más adelante. La métrica derivada "facturas sin declarar" es una **alerta de cumplimiento** (valor sano = 0), no una card analítica; se surge condicionalmente cuando exista la integración. Ver 1.5.
- **Compatibilidad de producto (A-22, esquema reservado, diferido a Módulo 3 post-DIAN — ver [06](06-equipo-riesgos-roadmap.md) §4):** dos entidades nuevas cuando se construya — `SpecProfile` (`id`, `category_id` FK opcional, `label`, y atributos técnicos del vertical — arranca con columnas fijas por vertical validado, no JSON genérico) y `ReferenceCompatibility` (tabla puente `reference_id ↔ spec_profile_id`, muchos-a-muchos, para que una Referencia liste varios perfiles compatibles sin duplicar catálogo — mismo principio que D-11). No se agregan todavía; el diseño queda anotado para no tener que migrar `ReferenceCompatibility` después si la forma relacional cambia.

## 9. Extensión multi-tenant y ajustes de la implementación (backend central)

> Esta sección documenta las diferencias entre el DDL de referencia (§6) y el esquema realmente implementado en `backend/` (FastAPI + SQLAlchemy + Alembic). Aplica **solo al backend central (Postgres)**, no al SQLite local de cada negocio (que es inherentemente de un solo tenant). Decisiones registradas como D-23 a D-25 en [07 — Decisiones y puntos abiertos](07-decisiones-y-puntos-abiertos.md).

> ⚠️ **Reubicación pendiente (D-37/D-39, [02](02-arquitectura.md), §9.6):** bajo el reparto local/remoto decidido después, las **8 entidades de negocio** (`Provider`…`BillItem`) pertenecen al backend **local** — paquete `station` (`tiendapi_station`, SQLite, de un solo tenant → sin `tenant_id`)—, no al remoto. El backend **remoto** — paquete `platform` (`tiendapi_platform`)— solo conserva `Tenant`, `User`, `Subscription`, `Payment`, `Device`, `MasterLease`, `Backup`, `FiscalRecord` y `AppRelease`. El código en `backend/` implementa hoy las 8 entidades sobre Postgres/multi-tenant porque se construyó antes de esa decisión; su migración a `station` es un refactor pendiente. Lo de esta §9 (multi-tenant, `tenant_id`, D-23/D-24/D-25) sigue siendo correcto **para el remoto**; para el local, el esquema es el de §6 sin `tenant_id`.

### 9.1 Nueva entidad `Tenant`
El DDL original (§6) no contempla que el backend central sirve a **múltiples negocios (pymes) suscritos** a la vez. Se agregó la entidad `Tenant` (negocio suscrito) y una columna `tenant_id` en **todas** las tablas de negocio (`Provider`, `Category`, `Location`, `Reference`/`product_references`, `Item`, `Customer`, `Bill`, `BillItem`), para aislar lógicamente los datos de cada cliente en la misma base de datos compartida (D-10, D-23).

**No confundir** `Tenant` (el negocio que paga la suscripción, ver [01 — Visión de negocio](01-vision-negocio.md)) con `Customer` (los clientes finales *de* ese negocio, que ya existía en el DDL original).

```dbml
Table Tenant {
  id UUID [pk]
  business_name varchar        // Nombre del negocio suscrito
  business_type varchar        // 'repuestos_vehiculo' | 'tienda_barrio' | 'farmacia' | ... (D-43, onboarding)
  subscription_status varchar  // 'trial' | 'active' | 'grace' | 'restricted'
  subscribed_until timestamp
  created_at timestamp
  updated_at timestamp
}
```

`business_type` (D-43) solo determina qué semillas de `Category` se precargan al aprovisionar el SQLite local del negocio — no condiciona features ni gating (D-44).

Todas las demás tablas de §6 incorporan `tenant_id UUID [ref: > Tenant.id]` como primera FK.

### 9.2 Renombres de campos (D-24)
| Campo original (§6) | Campo implementado | Motivo |
|---|---|---|
| `Provider.provider_id` (código interno) | `Provider.provider_code` | Colisionaba conceptualmente con las columnas `provider_id` (FK) de `Reference`/`Item`, que sí apuntan a `Provider.id` |
| `Reference.reference_id` (SKU) | `Reference.sku` | Mismo problema: `id` ya es la PK propia de la tabla; llamar `reference_id` al SKU inducía a confusión |
| `Provider.desc`, `Reference.desc` | `description` | `DESC` es palabra reservada en SQL (`ORDER BY ... DESC`) |
| Tabla `Reference` | Tabla `product_references` | `REFERENCES` es palabra reservada en SQL (sintaxis de `FOREIGN KEY ... REFERENCES`); usarla como nombre de tabla obliga a citarla en cualquier SQL manual |

Estos son renombres a nivel de columna/tabla física; los nombres conceptuales de la entidad (`Referencia`, `Reference`) no cambian en el resto de la documentación.

### 9.3 Validación de `Location.type` (D-25)
Se cierra el punto abierto A-11 con **doble validación**: `enum` en el schema Pydantic de la API (`LocationType.SUCURSAL` / `LocationType.BODEGA`) y un `CHECK constraint` (`ck_locations_type`) en la migración de Postgres, para que el valor quede protegido incluso ante escrituras que no pasen por la API.

### 9.4 Dónde vive esto
- Modelos ORM: `backend/app/models/`
- Migración inicial (DDL real, verificado contra Postgres en modo `--sql`): `backend/alembic/versions/0001_initial_schema.py`
- Resolución de tenant (stub temporal, ver A-12): `backend/app/api/deps.py`
