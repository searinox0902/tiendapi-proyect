# CLAUDE.md

Guía para agentes de IA que trabajan en este repositorio.

## Qué es este proyecto

Software de gestión comercial (referencias, inventario y facturación) para pymes locales de Medellín. Arquitectura **desktop-first / local-first**: la BBDD local (SQLite) es la fuente de verdad y la operación funciona sin internet; la nube es una capa delgada de apoyo (auth, cobro, actualizaciones, sync).

**Estado:** pre-MVP. Ya hay código: backend central (FastAPI/SQLAlchemy/Alembic) y frontend del MVP (Vue 3), más cimientos de infra (Docker, CI). Falta la integración real (wiring, integridad financiera, sync) y el empaquetado Tauri — ver fases F1–F4 en [docs/10](docs/10-infraestructura-dev-y-empaquetado.md).

**Para poner el proyecto a correr** (y para saber qué está construido de verdad y qué solo está documentado): [ARRANQUE.md](ARRANQUE.md).

## Antes de trabajar: carga el contexto que necesites

La documentación está organizada por tema en [`docs/`](docs/). **Empieza siempre por el índice**, que indica qué documento cargar según la tarea:

➡️ **[docs/00-indice-maestro.md](docs/00-indice-maestro.md)**

Mapa rápido:

- Negocio, pricing, posicionamiento → [docs/01-vision-negocio.md](docs/01-vision-negocio.md)
- Infra, stack, empaquetado, sync → [docs/02-arquitectura.md](docs/02-arquitectura.md)
- Esquema, migraciones, ORM, queries → [docs/03-modelo-datos.md](docs/03-modelo-datos.md)
- Cifrado, integridad, licencia, hardening → [docs/04-seguridad.md](docs/04-seguridad.md)
- Scope MVP, flujos, DIAN → [docs/05-alcance-mvp-y-flujos.md](docs/05-alcance-mvp-y-flujos.md)
- Equipo, riesgos, roadmap → [docs/06-equipo-riesgos-roadmap.md](docs/06-equipo-riesgos-roadmap.md)
- Decisiones y puntos abiertos → [docs/07-decisiones-y-puntos-abiertos.md](docs/07-decisiones-y-puntos-abiertos.md)
- Glosario → [docs/08-glosario.md](docs/08-glosario.md)
- Diseño de interfaz / color → [docs/09-diseno-ui-ux.md](docs/09-diseno-ui-ux.md)
- Infra de desarrollo, Docker, CI, empaquetado Tauri → [docs/10-infraestructura-dev-y-empaquetado.md](docs/10-infraestructura-dev-y-empaquetado.md)

Los PDFs y notas fuente originales están en `specs/` (incluye `specs/Addendum_2026-07-01_MVP_Pantallas_UI.md`) y son la fuente primaria; `docs/` es su reorganización temática.

## Código existente

- **[`backend/`](backend/)** — andamiaje del backend central (FastAPI + SQLAlchemy + Alembic + PostgreSQL). Modelos, migración inicial y CRUD skeleton para las 8 entidades de negocio, con extensión multi-tenant (`Tenant` + `tenant_id`, ver [docs/03-modelo-datos.md](docs/03-modelo-datos.md), §9, y decisiones D-23 a D-25 en [docs/07](docs/07-decisiones-y-puntos-abiertos.md)). La resolución de `tenant_id` en `backend/app/api/deps.py` es un **stub temporal** (header `X-Tenant-ID`) — no hay autenticación real todavía (punto abierto A-12).
- **[`frontend/`](frontend/)** — app del MVP (Vue 3 + TS + Tailwind + Pinia sobre Vite). Pantallas construidas: login, dashboard, catálogo de Referencias, Productos (unidades físicas), Caja (POS), Facturación, Directorio, Configuraciones y la maqueta de **Nómina** (`/nomina`, todavía sin backend). Cálculos de dinero con Decimal.js. UI con variables CSS estilo shadcn/vue (D-28). El empaquetado como instalable con **Tauri** está decidido (D-29 revierte D-26) pero **no construido**: no existe `frontend/src-tauri/`; cuando se haga, el código Vue no se toca.
- **Infra de desarrollo y empaquetado** — el backend se levanta como servicio con Docker Compose (Postgres + API) y hay CI en GitHub Actions (lint + migraciones + tests). El instalador Tauri **está pendiente**; cuando exista empaquetará **solo el frontend autocontenido**, con el backend corriendo por separado y **no** embebido en el `.exe` (D-29 a D-31). Guía completa: [docs/10-infraestructura-dev-y-empaquetado.md](docs/10-infraestructura-dev-y-empaquetado.md).
- **Cómo correr todo:** ver [README.md](README.md).
- Aún **falta** (fases F1–F4): autenticación real (A-12), wiring frontend↔backend, validación financiera en servidor, firma HMAC/cadena de hash de facturas ([docs/04-seguridad.md](docs/04-seguridad.md)), motor de sync, licencia e infra cloud productiva. Toolchain para builds locales: **Rust** (instalador) y **Docker** (backend).

## Stack tecnológico (decidido)

✅ **Frontend:** Vue 3 + TypeScript + Shadcn/Vue + Tailwind CSS + Pinia.
✅ **Backend:** Python (FastAPI o Django REST, por confirmar framework específico).
✅ **Empaquetado:** Tauri (decidido; andamiaje aún sin construir).
✅ **BBDD local:** SQLite + SQLCipher.

Ver [docs/STACK_TECH.md](docs/STACK_TECH.md) para referencia rápida o [docs/02-arquitectura.md](docs/02-arquitectura.md) para contexto completo.

## Alcance de pantallas

Fijado por **D-51** en 5 pantallas —inicio de sesión, CRUD Referencia, CRUD Productos, Facturas y Dashboard—, más lo que decisiones posteriores fueron agregando (Directorio D-71, Configuraciones acotada D-77, Caja/POS, y Nómina como módulo post-MVP D-97). Detalle en [docs/05-alcance-mvp-y-flujos.md](docs/05-alcance-mvp-y-flujos.md), §2.

> La vieja "primera iteración de 3 pantallas con sesión mock" (D-14/D-15) **ya no aplica**: D-51 fijó el alcance real y D-36 puso autenticación real (JWT). Si encuentras esa narrativa en algún documento, está desactualizada.

## Sistema de color de la interfaz

**90% fondos claros / 7% púrpura primario / 3% negro (texto/acento)** — interfaz clara y moderna. Púrpura primario **`#9B44C2`** y tipografía **Geist Sans** (A-08/A-09 resueltos). Los tokens se declaran en OKLCH en `frontend/src/style.css`; no pintes colores a mano en los componentes. Ver [docs/09-diseno-ui-ux.md](docs/09-diseno-ui-ux.md).

## Reglas del proyecto para agentes

- **No asumas decisiones estructurales sin verificar.** Consulta primero [docs/07-decisiones-y-puntos-abiertos.md](docs/07-decisiones-y-puntos-abiertos.md), que lista decisiones tomadas, puntos abiertos y preguntas sin resolver.
- **Zonas de alto riesgo** que exigen revisión y testing manual, no solo pruebas automáticas: cálculos financieros/redondeo, parseo de XML de proveedores y controles de seguridad.
- **Dinero con aritmética decimal exacta** (Decimal.js en cliente); nunca punto flotante.
- **Seguridad por diseño:** cifrado en reposo (SQLCipher), integridad verificable (HMAC + cadena de hash) y el servidor como autoridad final. Ver [docs/04-seguridad.md](docs/04-seguridad.md).

## Mantenimiento de la documentación

Si cambias una decisión o resuelves un punto abierto, actualiza el documento temático correspondiente en `docs/` **y** el registro en [docs/07-decisiones-y-puntos-abiertos.md](docs/07-decisiones-y-puntos-abiertos.md).
