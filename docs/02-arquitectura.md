# 02 — Arquitectura General (desktop-first / local-first)

> **Contexto:** Modelo arquitectónico, stack tecnológico, empaquetado, servicios en la nube y estrategia de sincronización. Cárgalo para decisiones de infraestructura, stack y offline.

## 1. Principio rector: desktop-first / local-first

- La **base de datos local es la fuente primaria de verdad**. Toda la operación diaria funciona con conexión local, **sin depender de internet**.
- La nube es una **capa delgada de servicios de apoyo**.
- Objetivo principal desde el inicio: **empaquetado de escritorio (Tauri) + BBDD local (SQLite)**.

## 2. Frontend — Vue 3 + Shadcn/Vue + Tailwind + Pinia

✅ **Decidido** (ver D-13 en [07 — Decisiones](07-decisiones-y-puntos-abiertos.md)).

- **Framework:** Vue 3 (Composition API) + TypeScript.
- **Estado:** Pinia.
- **Estilos/UI:** Tailwind CSS + Shadcn/Vue (tablas, formularios, modales).
- **Validación:** VeeValidate + Zod.
- **Cliente HTTP:** Axios.
- **Persistencia local/offline (capa web):** IndexedDB (Dexie) + Service Worker.
- **Cálculos financieros en cliente:** Decimal.js (evita errores de punto flotante). **Criticidad:** todo redondeo debe validarse manualmente (ver [04 — Seguridad](04-seguridad.md) y [06 — Riesgos](06-equipo-riesgos-roadmap.md)).

## 3. Empaquetado de escritorio (Tauri)

Se elige **Tauri (Rust + WebView del sistema)** sobre Electron:

- Ejecutable liviano: **15–25 MB** vs. 150–200 MB de Electron.
- Menor consumo de RAM.
- Acceso más estable a **dispositivos HID (escáneres)** vía Rust.
- El **95% de los escáneres** funcionan como teclado virtual → la integración básica **no requiere código nativo**.
- Se reutiliza **~90% del código web**.

## 4. Backend — Python

✅ **Decidido: Python** (ver D-12 en [07 — Decisiones](07-decisiones-y-puntos-abiertos.md)).

**Stack recomendado:** FastAPI (async, ligero, OpenAPI nativo) o Django REST (más ecosystem). A confirmar según preferencias del equipo y requerimientos específicos de parseo XML.

**Justificación:**

- Respaldo de un socio con conocimiento técnico en Python.
- Facilidad de integración con **lectoras de barras / dispositivos de lectura física** (HID).
- Alta recomendación para **cálculos, formatos y ciencia de datos**.

## 5. Bases de datos y modelo local-first

| Capa | Tecnología | Rol |
|------|------------|-----|
| **BBDD local** | SQLite (cifrada con SQLCipher) | **Fuente primaria de verdad.** Toda lectura/escritura operativa ocurre aquí, con o sin internet. |
| **BBDD central** | PostgreSQL (servidor) | Destino de **sincronización, respaldo y continuidad** entre equipos y sucursales. **No** es la fuente de verdad operativa. |
| **Servicios cloud** | — | Cargas ligeras: autenticación/sesiones, cobro de suscripción, distribución de actualizaciones. |

Detalles de cifrado de la BBDD local en [04 — Seguridad](04-seguridad.md).

## 6. Servicios que requieren conexión a internet

Solo **cuatro** servicios usan conexión; **todo lo demás es 100% local**:

| Servicio | Función | Frecuencia | Sin conexión |
|----------|---------|------------|--------------|
| **Sesiones / autenticación** | Validar identidad y licencia activa | Al iniciar y periódica | Token en caché con periodo de gracia; la operación continúa |
| **Pago de la suscripción** | Verificar suscripción vigente y cobrar | Mensual / verificación periódica | Periodo de gracia antes de restringir |
| **Actualizaciones** | Descargar e instalar nuevas versiones | Al publicarse una versión | Se pospone; no bloquea el uso |
| **Sincronización de la BBDD** | Respaldar y replicar datos al servidor | En segundo plano con internet | Encola cambios y sincroniza al reconectar |

## 7. Estrategia de sincronización

- **Escritura local inmediata**; la sincronización ocurre en segundo plano sin frenar al usuario.
- **Cola de cambios pendientes** cuando no hay internet; se envían al reconectar.
- **La "sincronización" a la nube es un respaldo, no una fusión.** Como en la LAN escribe **un solo maestro** (§9, D-32), no hay dos versiones que reconciliar: el maestro sube su estado como respaldo. La política de resolución de conflictos (A-01) queda **acotada** por ese modelo de escritor único.
- **Casos borde** (corte a mitad de una factura) → se tratan como **transacción atómica local**.
- **Aislamiento por cliente:** cada negocio es **un solo tenant**; sincroniza (respalda) contra su **propio espacio independiente** en la nube.

> El detalle de la topología local (maestro/esclavo), la recuperación ante falla y el modelo de facturas está en **§9**.

## 8. Diagrama lógico (resumen)

```
┌─────────────────────────────────────────────┐
│  APP DESKTOP (Tauri: Rust + WebView)         │
│  ┌───────────────────────────────────────┐  │
│  │ Frontend: Vue 3 + TS + Pinia + Tailwind│  │
│  │ Decimal.js (cálculos)                  │  │
│  └───────────────────────────────────────┘  │
│  ┌───────────────────────────────────────┐  │
│  │ BBDD LOCAL: SQLite + SQLCipher         │  │ ◄── Fuente de verdad operativa
│  │ (HID / escáner vía Rust)               │  │
│  └───────────────────────────────────────┘  │
└───────────────┬─────────────────────────────┘
                │  sync en 2.º plano (cola offline)
                ▼
┌─────────────────────────────────────────────┐
│  CLOUD (capa delgada)                         │
│  • Auth / sesiones / licencia firmada         │
│  • Cobro de suscripción                        │
│  • Distribución de actualizaciones (firmadas)  │
│  • PostgreSQL: respaldo + continuidad multi-eq.│ ◄── Autoridad final de integridad
└─────────────────────────────────────────────┘
```

## 9. Topología operativa local (maestro/esclavo) y resiliencia

> Modelo de operación real dentro de un negocio con varios computadores, y qué pasa cuando algo falla. Decisiones asociadas: **D-32 a D-35** en [07](07-decisiones-y-puntos-abiertos.md).

### 9.1 Un negocio, un maestro, hasta 3 asientos

Un negocio es **un solo tenant** con **máximo 3 asientos** (usuarios/computadores). No hay multi-negocio en el lado local. En la red local (LAN) los equipos se organizan como **maestro / esclavo** (D-32):

```
        ┌───────────────────────────────┐
        │  MAESTRO (PC principal)        │
        │  Frontend + Backend local      │
        │  SQLite (única fuente de verdad)│
        └──────┬───────────────┬─────────┘
               │ LAN (WiFi)    │ LAN
        ┌──────┴──────┐ ┌──────┴──────┐
        │ ESCLAVO 1   │ │ ESCLAVO 2   │
        │ Frontend    │ │ Frontend    │   ◄── clientes ligeros: operan
        │ (sin BBDD)  │ │ (sin BBDD)  │       contra el maestro por la red
        └─────────────┘ └─────────────┘
               │
               ▼ respaldo (no fusión)
        ┌───────────────────────────────┐
        │ NUBE: licencia + respaldo +    │
        │ árbitro del rol maestro + DIAN │
        └───────────────────────────────┘
```

- El **maestro** hospeda la única SQLite y el backend local; es la fuente de verdad operativa.
- Los **esclavos** son clientes ligeros: todos pueden crear referencias, facturar, etc., pero **escriben contra el maestro** por la LAN.
- **"Offline" tiene dos sentidos** que no hay que confundir:
  - *Sin internet* → toda la tienda opera normal (local-first).
  - *Sin el maestro* (apagado o fuera de la LAN) → los esclavos **no** pueden operar, porque no tienen BBDD propia. **El maestro es el punto único local** y debe estar encendido en horario de operación.

### 9.2 Recuperación ante falla del maestro (D-33)

Ante un daño físico del maestro (se quema, se roba, muere el disco), el dueño se **autogestiona** sin soporte técnico:

1. Instala el `.exe` en cualquier equipo.
2. Inicia sesión (valida credencial + licencia contra la nube).
3. Elige **"Este equipo es el principal"** → descarga el **último respaldo** de la nube y reconstruye la SQLite.
4. Sigue operando. Los otros equipos eligen "conectarse a uno existente" y lo redetectan en la LAN.

- **RPO (pérdida máxima) = lo ocurrido desde el último respaldo.** Aceptado como decisión de negocio: en una catástrofe física no se exige el último segundo.
- **Anti *split-brain*:** el rol de maestro **lo certifica la nube**, no la máquina. Al reclamar "soy el principal", la nube invalida al maestro anterior; si el viejo reaparece, ve que perdió el rol y **se degrada a esclavo**. Nunca hay dos maestros escribiendo en paralelo.
- **Cambio planeado** (comprar un PC nuevo): migración por la LAN con ambos equipos vivos → **cero pérdida**.

### 9.3 Operación en contingencia y "libro de la realidad" (D-34)

Principio: **nunca detener la operación.** La realidad manda y el sistema la refleja — **no hay pantalla de conciliación** tipo *merge* de Git.

- Si al iniciar no hay ni BBDD local ni nube (falla total), el maestro opera con una **base provisional** y sigue vendiendo.
- Al reconectar, descarga el último respaldo y **añade** (append) los registros de la contingencia. No sobrescribe historia.
- La **identidad fiscal** (número/CUFE) la asigna la **DIAN al autorizar**, no un contador local → dos facturas de contingencia **no pueden colisionar** con la numeración legal.
- El dueño puede registrar la realidad libremente (incluso ventas con fecha pasada) como capacidad **normal** del sistema, no como un modo especial.

### 9.4 Facturas: agregar y anular (D-35)

En este sistema **"editar" no existe como verbo**. Las operaciones son:

| Operación | Qué hace | Efecto |
|-----------|----------|--------|
| **Agregar** | Registrar una venta/factura (incluso tardía) | Nuevo registro |
| **Anular** | Dejar sin efecto una factura | Crea un registro de anulación **vinculado** al original (no lo borra) y **revierte** sus efectos (inventario, caja) |
| **Corregir** | Rehacer una factura equivocada | Se **anula** y se emite una **nueva**; si la original ya fue autorizada por la DIAN, se dispara una **nota crédito** (vía proveedor, D-09) |

- Es el principio de un libro contable: **no se borra, se hace un asiento que corrige.** El historial completo ("se vendió, se anuló, se corrigió") queda visible.
- Esto preserva la **cadena de hash / HMAC** ([04](04-seguridad.md), §7, y D-07): como nada se sobrescribe, la cadena nunca se rompe y la detección de manipulación sigue siendo útil.

### 9.5 Facturas DIAN: triple redundancia

Una factura reportada a la DIAN es, paradójicamente, **el dato más protegido** del sistema — vive en tres lugares independientes:

1. **La nube** (push inmediato al autorizar) — la mejor fuente, estructurada y re-importable.
2. **El proveedor de facturación** (D-09) — autoritativo legalmente (CUFE, XML firmado); recuperable por su API/portal (criterio de selección en A-03).
3. **La factura física** (papel) — último recurso, legible pero no re-importable.

> **Criterio rector de resiliencia:** proteger con fuerza el dato **irreversible y sin testigo externo** (una venta que solo existió en el maestro); mantener simple lo que se puede **re-teclear o recuperar de un tercero** (una referencia, una factura DIAN). Ver el riesgo residual aceptado en A-16 y el hardening diferido en A-17.

### 9.6 Reparto local vs. remoto (CQRS) y mecanismo frontend↔datos (D-37)

Hay **dos backends con responsabilidades distintas** (no dos copias del mismo):

| | **Backend LOCAL** (el maestro) | **Backend REMOTO** (la nube) |
|--|--------------------------------|------------------------------|
| BBDD | SQLite (cifrada) | PostgreSQL |
| Entidades | Las 8 de negocio: `Provider`, `Category`, `Location`, `Reference`, `Item`, `Customer`, `Bill`, `BillItem` | `Tenant`, `User`, licencia, punteros de respaldo, `FiscalRecord` |
| Rol | **Operación** (crear/facturar/inventario) | **Gestión**: acceso, licencia/cobro, respaldo, updates, evidencia fiscal, lectura remota |
| Escritura | **Único escritor** del dominio operativo | **Nunca escribe** el dominio operativo |

- **Separación lectura/escritura (CQRS):** *toda escritura* va al maestro local; el remoto solo guarda **modelos de lectura** (blob de respaldo, `FiscalRecord`, y —fase posterior— una réplica de solo-lectura). "Operar remoto" = **solo consultar**; nunca escritura remota. Una acción desde afuera, si se implementa, sería una **intención encolada** al maestro, no una escritura directa.
- **Mecanismo frontend↔datos locales = HTTP** contra el backend del maestro (mismo patrón `axios`/`services` que el remoto, con SQLite en vez de Postgres). **No** se usa IPC de Tauri para esto, porque los esclavos consumen al maestro **por la LAN** y eso exige red. El frontend no sabe si habla con el proceso de su propia máquina o con el del maestro por WiFi: es la misma llamada HTTP con distinto `baseURL`.
- **Espejo real:** es el patrón *desktop-client + thin-cloud* de apps como Terabox/Dropbox (working set local + daemon de sync + blob por bloques + cuenta/metadata en la nube + UI web de lectura). La diferencia deliberada: ellos resuelven conflictos con "copia en conflicto" porque manejan **archivos independientes**; nosotros usamos **maestro único** porque manejamos un **libro contable transaccional** que no admite copias en conflicto.
- **Modelo de lectura remota, por rebanadas:** la **rebanada fiscal** (facturas DIAN) llega **pronto** (el dato ya sube al servidor, §9.7); la **rebanada operativa** (inventario, ventas no fiscales) queda **diferida**.

**Estructura objetivo del código (D-39):** monorepo Python con tres paquetes —
`shared/` (`tiendapi_shared`: config, security/JWT, money/Decimal, mixins base,
schemas comunes), `platform/` (`tiendapi_platform`: el **remoto**, Postgres) y
`station/` (`tiendapi_station`: el **local**, SQLite, corre en el maestro). Se
nombra por función, no por tecnología; el local es `station` y **no** `master`,
porque maestro/esclavo es un rol de *runtime* (§9.1).

- **Remoto (`platform`)** — entidades: `Tenant`, `User` (ya existen) + `Subscription`, `Payment`, `Device`, `MasterLease` (árbitro anti split-brain), `Backup` (punteros a los blobs), `FiscalRecord` (§9.7), `AppRelease` (updater).
- **Local (`station`)** — las 8 de negocio: `Provider`, `Category`, `Location`, `Reference`, `Item`, `Customer`, `Bill`, `BillItem` (SQLite, de un solo tenant, sin `tenant_id`).

> **Estado del código:** el `backend/` actual (con las 8 entidades operativas sobre Postgres/multi-tenant) es, bajo D-37/D-39, el **borrador a repartir** entre `station` (las 8 entidades) y `platform` (`Tenant`/`User`). Es un refactor pendiente, recomendado **antes de F2** (ver [03 — Modelo de datos](03-modelo-datos.md), §9). Punto abierto asociado: autenticación offline en `station` (A-20).

### 9.7 Flujo de facturación DIAN (D-38)

La facturación electrónica se delega a un proveedor tercero (D-09), pero **pasa por el servidor remoto**, no directo desde el `.exe`:

```
maestro ordena factura
      │
      ▼
servidor remoto  ──►  proveedor DIAN  ──►  DIAN (autoriza, CUFE)
   (intermedia)          (gestiona)
      │  ◄──────────────────┘
      ▼
remoto registra FiscalRecord  ──►  responde al maestro (CUFE)
```

- **Por qué pasa por el remoto:** las **credenciales del proveedor viven solo en el servidor**, no embebidas en cada `.exe` (una llave extraída de un instalador comprometería la cuenta). Centraliza también el poder cambiar de proveedor (A-03) y sirve de **palanca de cobro** (sin licencia vigente, no se intermedia).
- **No rompe el maestro único:** el maestro sigue siendo el escritor del libro local; el remoto **intermedia y guarda copia**, no origina la factura.
- **`FiscalRecord` "para ver", no solo auditar:** número, fecha, cliente, total, resumen de líneas, estado, CUFE y **enlace a la representación gráfica (PDF)** del proveedor. Es la pieza fiscal del modelo de lectura remota. *Las facturas DIAN son el dato menos privado del sistema (ya están ante el Estado) → son lo más seguro de guardar estructurado en el servidor.*
- **Condiciones no negociables:**
  1. **Contingencia offline (A-18):** sin red —o con el servidor caído— el maestro **emite localmente ya** (contingencia DIAN, ventana ~48 h) y **encola** la autorización para cuando vuelva la conexión. El paso síncrono "maestro recibe respuesta" es el camino feliz online; el offline es diferido.
  2. **Idempotencia:** el maestro manda un **id único de solicitud**; si reintenta tras una respuesta perdida, el remoto devuelve el **mismo CUFE** en vez de autorizar de nuevo → evita **facturas duplicadas** (zona de alto riesgo, CLAUDE.md).
- **Costo asumido (A-19):** al estar en el camino de la facturación, el uptime del servidor remoto es responsabilidad del negocio (infra F4): su caída impide facturar **en línea** (aunque la contingencia permite seguir vendiendo).
