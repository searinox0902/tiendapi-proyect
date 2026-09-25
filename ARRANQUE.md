# Arranque — para quien recibe este repo

> Para un desarrollador que abre el proyecto por primera vez, y para el asistente de IA
> que lo acompañe. Si eres una IA: lee también [`CLAUDE.md`](CLAUDE.md) y
> [`docs/00-indice-maestro.md`](docs/00-indice-maestro.md) antes de tocar código; este
> archivo solo te pone la app a correr y te dice qué es real y qué todavía no.

**Qué es:** software de gestión comercial (catálogo, inventario, facturación) para pymes
de Medellín. **Local-first**: la operación funciona sin internet, la nube es apoyo.
Hoy el negocio piloto es un almacén de **repuestos de moto**.

---

## Los 4 comandos

Necesitas **Docker Desktop** y **Node ≥ 20**.

```bash
cd backend && docker compose up -d
```

Levanta Postgres + API y aplica las migraciones solo. Espera ~10 s y comprueba
http://localhost:8000/health → debe decir `"database":"connected"`.

```bash
docker compose exec api python -m scripts.seed
```

Crea el negocio demo y su usuario propietario. **Estas son las credenciales para entrar:**

| | |
|---|---|
| **Usuario** | `demo@tiendapi.co` |
| **Clave** | `demo1234` |

```bash
docker compose exec api python -m scripts.seed_catalog
```

**La semilla de producto.** Carga **1.015 Referencias reales de repuestos de moto**
(scrapeadas de `motopartes.com.co` y consolidadas) bajo ese mismo negocio demo — así que
al entrar con el usuario de arriba las ves de una. Debe imprimir
`Referencias creadas: 1015`. Es idempotente: correrlo dos veces no duplica nada.

```bash
cd ../frontend && npm install && npm run dev
```

Abre la URL que imprime Vite (por defecto http://localhost:5173) y entra con el usuario
demo.

---

## Sobre la semilla de producto

El archivo es [`backend/scripts/seed_data/catalog_repuestos.json`](backend/scripts/seed_data/catalog_repuestos.json)
(~420 KB, legible y versionado) y lo carga
[`backend/scripts/seed_catalog.py`](backend/scripts/seed_catalog.py).

**Es un JSON y no un `pg_dump` a propósito:** un volcado de la BBDD de desarrollo
arrastraría 34 tenants de pruebas, facturas de fixtures y usuarios con su
`password_hash`. Esto es solo el catálogo, insertado por el mismo ORM que usa la API —
si el esquema cambia, el script falla en la migración y no a los tres meses con una fila
corrupta.

De dónde salió, si necesitas repetir el proceso con otro proveedor:

```
firecrawl map/crawl  →  scripts/import_scraped_references.py  →  scripts/consolidate_scraped_catalog.py
```

El consolidador resuelve un problema concreto (**D-89**): el sitio publica **un anuncio
por cada moto compatible**, así que la misma culata `VA10300` aparece 7 veces —CBF125,
CBF150, RTX150…—. Importar eso tal cual parte el inventario en 7 productos con stock
repartido. El consolidador deja **una Referencia por SKU** y estaciona los modelos
compatibles en `description`, como una línea `Compatible: …`, hasta que exista el módulo
de compatibilidad (**A-22**).

⚠️ **Tres cosas que no debes tomar por buenas:**

- **Los precios son scrapeados, no negociados.** `base_price` viene sin IVA (se dividió
  por 1,19 al importar, asumiendo que el precio publicado lo incluía). Son datos de
  desarrollo. Los cálculos de dinero son **zona de alto riesgo** en este proyecto
  (ver `CLAUDE.md`): aritmética decimal exacta, nunca punto flotante.
- **No hay proveedor real.** Todo cuelga de un placeholder, *"Catálogo Externo
  (Scraping)"*, para que se note.
- **`brand` es quien fabrica el repuesto** (NGK, Brembo, Motul), no la moto a la que le
  sirve. Eso último es la línea `Compatible:`.

---

## Qué está construido de verdad

| | Estado |
|---|---|
| **Backend** (FastAPI + SQLAlchemy + Alembic + Postgres) | Corre. Multi-tenant, migraciones, CI en GitHub Actions |
| **Autenticación real** (JWT, registro/login/me, subusuarios ≤3) | ✅ Cerrada — el `tenant_id` sale del token (A-12) |
| **Frontend** (Vue 3 + TS + Tailwind + shadcn/vue + Pinia) | Catálogo, inventario, facturación, POS |
| **Módulo de Nómina** — `frontend/src/pages/payroll/` | **Maqueta navegable, sin backend.** Ver abajo |
| **Integridad financiera** (F2: totales en servidor, HMAC + cadena de hash de facturas) | ❌ Pendiente |
| **Motor de sync** / licencia / infra cloud productiva (F3–F4) | ❌ Pendiente |
| **Instalador de escritorio (`.exe`)** | ❌ **No existe todavía** — ver abajo |

### El instalador de Tauri no está

`docs/10`, el `README` y `CLAUDE.md` describen un empaquetado con **Tauri**
(`npm run tauri:build`, instalador NSIS). **Ese código no está en el repo**: no hay
`frontend/src-tauri/`, no hay dependencia `@tauri-apps/*`, no hay script `tauri:build`, y
no aparece en ningún commit de la historia. La decisión (**D-29 a D-31**) sigue en pie y
el andamiaje es rutinario de crear; simplemente todavía no se creó. Mientras tanto la app
corre en el navegador con `npm run dev`.

Cuando exista, empaquetará **solo el frontend**: el backend corre aparte, **no** embebido
en el `.exe`. Eso es explícito y no es un descuido (`docs/10`, §regla).

### El módulo de Nómina es una maqueta

`frontend/src/pages/payroll/` (ruta `/nomina`) es un prototipo de interfaz **con estado
local y datos falsos**: no hay store, no hay API, no hay tabla `Employee`. Se construyó
para sentir el flujo antes de fijar el modelo de datos.

Lo que sí está decidido y escrito, si te toca conectarlo:
[`docs/13-modulo-nomina.md`](docs/13-modulo-nomina.md) **§12 — Contrato con el backend**,
que separa lo que se almacena de lo que se deriva, lista los campos que el frontend ya
espera y marca las tres costuras donde entra el servidor.

---

## Antes de cambiar nada

Este proyecto lleva un **registro de decisiones** en
[`docs/07-decisiones-y-puntos-abiertos.md`](docs/07-decisiones-y-puntos-abiertos.md):
`D-XX` son decisiones tomadas (con su porqué) y `A-XX` puntos abiertos. El código las cita
por número. **Consúltalo antes de cambiar algo estructural** — buena parte de lo que
parece raro está ahí explicado, y varias cosas que parecen faltar están deliberadamente
fuera de alcance.

Mapa de la documentación: [`docs/00-indice-maestro.md`](docs/00-indice-maestro.md).

## Apagar

```bash
cd backend && docker compose down
```

Los datos persisten en el volumen. Añade `-v` **solo** si quieres borrarlos — y entonces
toca repetir `seed` y `seed_catalog`.
