# 11 — Informe: Offline, resiliencia y facturación

> **Contexto:** Informe consolidado de la arquitectura operativa local del producto: cómo trabaja sin red, cómo se recupera ante fallas, cómo se organizan los computadores de un negocio (maestro/esclavo) y cómo se manejan las facturas (agregar/anular). Es el resumen ejecutivo; el detalle vive en [02 — Arquitectura](02-arquitectura.md) §9, [04 — Seguridad](04-seguridad.md) §7 y las decisiones **D-32 a D-35** en [07](07-decisiones-y-puntos-abiertos.md).
>
> **Estado:** resuelto. Fecha: 2026-07-03.

## 1. Resumen en una frase

Un negocio opera con **un computador maestro** (fuente de verdad local en SQLite) y **hasta 2 esclavos** en la misma red; **funciona sin internet**; ante una falla el dueño **se recupera solo** desde el respaldo en la nube; y las facturas **no se editan, se agregan y se anulan** como en un libro contable.

## 2. Operación sin red (offline)

- La operación diaria (referencias, inventario, facturación) ocurre **100% en local**. La nube solo se usa para **credenciales, estado de licencia, respaldo y la integración DIAN**.
- **"Offline" significa "sin internet".** La tienda sigue vendiendo con normalidad mientras la **licencia esté en su ventana de gracia** (valor de partida: **3 días**, A-02).
- Precisión importante: *sin internet* ≠ *sin maestro*. Los esclavos necesitan al **maestro encendido en la red local** para operar (no tienen base propia).

## 3. Sistema maestro / esclavo

| Rol | Qué corre | Función |
|-----|-----------|---------|
| **Maestro** | Frontend + backend local + **única SQLite** | Fuente de verdad operativa; sube el respaldo a la nube |
| **Esclavo** (×1–2) | Frontend (cliente ligero) | Opera contra el maestro por la LAN; sin BBDD propia |

- Un negocio = **1 tenant, máximo 3 asientos**. No hay multi-negocio local.
- El mismo `.exe` sirve para ambos roles: en la primera ejecución se elige **"principal"** o **"conectarse a uno existente"** (descubrimiento en la LAN — mecanismo por definir, A-14).
- Como **solo el maestro escribe**, no hay fusiones ni conflictos: el respaldo a la nube es una **copia**, no un *merge*.

### 3.1 Dos backends: local (operación) y remoto (gestión) — D-37

No son dos copias del mismo backend, son **responsabilidades distintas**:

- **Backend LOCAL** (el maestro, SQLite): las 8 entidades operativas (`Provider`…`BillItem`). El frontend lo consume por **HTTP** (mismo patrón que el remoto; los esclavos le pegan por la LAN). **Es el único que escribe** el dominio operativo.
- **Backend REMOTO** (nube, Postgres): solo *gestión* — `Tenant`/`User`, licencia/cobro, respaldo (blob), actualizaciones, `FiscalRecord`, y —fase posterior— un **modelo de lectura de solo-lectura**. **Nunca escribe** el dominio operativo.
- Es el patrón *desktop-client + thin-cloud* (Terabox/Dropbox), pero con **maestro único** en vez de "copia en conflicto", porque manejamos un libro contable, no archivos sueltos.

## 4. Resiliencia del sistema (recuperación ante fallas)

### 4.1 Falla del maestro — recuperación autogestionada
El dueño, sin soporte técnico y en minutos:
1. Instala el `.exe` en otro equipo → 2. Inicia sesión → 3. Elige **"Este es el principal"** → 4. Descarga el **último respaldo** de la nube y continúa.

- **Pérdida máxima (RPO) = lo ocurrido desde el último respaldo.** Aceptado para el caso de daño físico (no se exige el último segundo).
- **Sin "dos maestros" (anti split-brain):** el rol de maestro **lo certifica la nube**. Al reclamarlo, invalida al anterior; si el viejo reaparece, se **degrada a esclavo** solo.
- **Cambio planeado** de maestro (equipo nuevo) = migración por la LAN con ambos vivos → **cero pérdida**.

### 4.2 Contingencia total — "nunca detener la operación"
Si falla todo a la vez (sin maestro y sin red), el sistema opera con una **base provisional** y, al reconectar, **añade** esos registros sobre el respaldo (append, sin sobrescribir). El dueño puede **registrar la realidad libremente** — es una capacidad normal, no un modo de emergencia.

### 4.3 Cadencia de respaldo
- Respaldo general: borrador cada **~10–15 min** (A-15).
- **Eventos fiscales/DIAN: push inmediato** a la nube al autorizarse (nunca viven solo en un disco que se puede quemar).

### 4.4 Riesgo residual aceptado
Si el maestro **muere físicamente durante** un corte de red, se pierde lo no respaldado hasta que vuelva la conexión. El único dato en riesgo real es el que **no tiene testigo externo** (una referencia, un ajuste de inventario); las facturas DIAN están triplemente respaldadas (§6). Mitigación futura opcional en A-17.

## 5. Facturas: agregar y anular (no editar)

**"Editar" no existe como verbo.** El sistema es un libro: no se borra, se corrige con un asiento nuevo.

| Operación | Qué hace |
|-----------|----------|
| **Agregar** | Registra una venta/factura (incluso tardía, para reflejar lo que pasó) |
| **Anular** | Crea un registro de anulación **vinculado** al original (no lo borra) y **revierte** sus efectos (inventario, caja) |
| **Corregir** | Anula + emite una factura nueva. Si la original ya fue **autorizada por la DIAN**, se dispara una **nota crédito** vía el proveedor (D-09) |

- Para el usuario se siente como "corregir": anula, y el sistema le abre una factura nueva pre-llenada para ajustar lo que estaba mal.
- Beneficio técnico: como nada se sobrescribe, la **cadena de hash/HMAC** (D-07) **nunca se rompe** por una operación legítima → la detección de manipulación (proteger al dueño de alteraciones internas) sigue sirviendo.

## 6. Facturas DIAN: triple redundancia

La factura reportada a la DIAN es el dato **más protegido** del sistema; existe en 3 lugares independientes:

1. **La nube** (push inmediato) — estructurada, re-importable.
2. **El proveedor DIAN** (D-09) — autoritativo legal (CUFE/XML); recuperable por su API (criterio para elegir proveedor, A-03).
3. **La factura física** (papel) — último recurso manual.

### 6.1 Flujo de facturación (D-38)

```
maestro ordena → servidor remoto (intermedia) → proveedor → DIAN (autoriza)
                       └── registra FiscalRecord ──► responde al maestro (CUFE)
```

- Las **credenciales del proveedor viven solo en el servidor**, no en cada `.exe`.
- No rompe el maestro único: el maestro origina la factura; el remoto intermedia y guarda copia.
- **Contingencia offline (A-18):** sin red o con el servidor caído, el maestro emite localmente ya (ventana DIAN ~48 h) y encola la autorización.
- **Idempotencia:** id único de solicitud → un reintento no genera factura duplicada.
- **Costo (A-19):** el uptime del servidor pasa a gatear la facturación en línea (infra F4).

## 7. Criterio rector

> **Proteger con fuerza el dato irreversible y sin testigo externo; mantener simple lo que se puede re-teclear o recuperar de un tercero.**

Ni todo blindado (nunca se entrega), ni todo simple (una factura legal no es una nota adhesiva): la arquitectura sabe **cuál de los dos criterios aplicar a cada dato**.

## 8. Qué queda por definir (puntos abiertos)

| ID | Pendiente |
|----|-----------|
| **A-02** | Duración exacta de la gracia offline (partida: 3 días) |
| **A-03** | Proveedor DIAN — ahora con "recuperabilidad vía API" como criterio |
| **A-14** | Mecanismo de descubrimiento del maestro en la LAN (mDNS vs. IP manual) |
| **A-15** | Cadencia de respaldo a la nube (define el RPO) |
| **A-16** | Riesgo residual de falla doble (aceptado) |
| **A-17** | Hardening futuro: bitácora en esclavos / réplica caliente (diferido) |

## 9. Decisiones registradas en esta ronda

- **D-32** — Topología maestro/esclavo en LAN.
- **D-33** — Recuperación ante falla del maestro; la nube como árbitro del rol.
- **D-34** — "Libro de la realidad": operación en contingencia sin pantalla de conciliación.
- **D-35** — Facturas append-only: agregar / anular / nota crédito.
- **D-36** — Autenticación real (JWT, tenant desde token) en el backend remoto.
- **D-37** — Reparto local/remoto (CQRS): la nube no escribe el dominio operativo; frontend↔datos locales por HTTP.
- **D-38** — Flujo de facturación DIAN vía servidor remoto, con contingencia offline e idempotencia.

Puntos abiertos nuevos: **A-18** (contingencia DIAN), **A-19** (SLA del servicio fiscal). Detalle completo en [07 — Decisiones](07-decisiones-y-puntos-abiertos.md).
