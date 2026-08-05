# Índice Maestro — Documentación del Proyecto

> **Proyecto:** Software de gestión comercial (referencias, inventario y facturación) para pymes locales de Medellín.
> **Estado:** Preliminar / pre-MVP (julio 2026).
> **Fuentes originales:** `specs/Informe_Consolidado.pdf`, `specs/Informe_Modelo_Datos.pdf` y `specs/Addendum_2026-07-01_MVP_Pantallas_UI.md`.

Esta documentación reorganiza los dos informes originales en documentos temáticos, atómicos y auto-contenidos, pensados para que una IA (o persona) cargue solo el contexto relevante a su tarea.

## Mapa de documentos

| # | Documento | Tema | Cárgalo cuando trabajes en… |
|---|-----------|------|------------------------------|
| ⚡ | [Stack tecnológico (referencia rápida)](STACK_TECH.md) | Frontend, backend, BBDD, cloud, seguridad | Necesitas saber rápidamente qué tecnologías se usan |
| 01 | [Visión de negocio](01-vision-negocio.md) | Problema, mercado, competencia, propuesta de valor, modelo de ingresos | Pricing, posicionamiento, priorización de features por valor |
| 02 | [Arquitectura general](02-arquitectura.md) | Desktop-first / local-first, stack frontend/backend, empaquetado, servicios cloud | Decisiones de infraestructura, stack, empaquetado, sincronización |
| 03 | [Modelo de datos](03-modelo-datos.md) | Entidades, relaciones, DDL (dbdiagram.io) | Esquema BBDD, migraciones, queries, ORM |
| 04 | [Seguridad](04-seguridad.md) | Cifrado, integridad, licencia offline, anti-manipulación de reloj | Cifrado SQLite, firma de facturas, licenciamiento, hardening |
| 05 | [Alcance MVP y flujos](05-alcance-mvp-y-flujos.md) | Objetivo del MVP, flujo principal, facturación DIAN | Definición de scope, roadmap funcional, integración e-invoicing |
| 06 | [Equipo, riesgos y roadmap](06-equipo-riesgos-roadmap.md) | Equipo, forma de trabajo, riesgos, próximos pasos | Planificación, gestión de riesgos |
| 07 | [Decisiones técnicas y puntos abiertos](07-decisiones-y-puntos-abiertos.md) | Registro de decisiones (ADR-lite) e inconsistencias por resolver | Cualquier decisión estructural pendiente |
| 08 | [Glosario](08-glosario.md) | Términos de negocio y técnicos | Onboarding, alinear vocabulario |
| 09 | [Diseño de interfaz y sistema de color](09-diseno-ui-ux.md) | Principios de UI, distribución de color (90/7/3), accesibilidad | Maquetar pantallas, definir tokens de Tailwind/Shadcn |
| 10 | [Infraestructura de desarrollo y empaquetado](10-infraestructura-dev-y-empaquetado.md) | Levantar backend+BBDD con Docker, CI, instalador Tauri, topología dev vs objetivo | Poner a correr el proyecto en equipo, hacer builds del `.exe`, entender la diferencia dev/objetivo |
| 11 | [Informe: Offline, resiliencia y facturación](11-offline-resiliencia-y-facturacion.md) | Operación sin red, maestro/esclavo, recuperación ante fallas, agregar/anular factura | Entender la operación real de un negocio, la resiliencia y el modelo de facturas append-only |
| 12 | [Guía: conectar el login del frontend a la API](12-guia-consumo-api-auth.md) | Contrato de auth (endpoints, token JWT, CORS) para consumir el backend desde Vue | Wirear el login/las llamadas autenticadas desde el frontend |
| API | [Referencia de API por módulo](api/README.md) | Endpoints HTTP documentados uno a uno (request/response/errores), por módulo del backend | Implementar o mantener un endpoint concreto; ver el contrato exacto de un módulo |

## Convenciones

- Cada documento empieza con un bloque **Contexto** (1–2 líneas) para que la IA sepa de inmediato de qué trata.
- Los puntos aún no decididos se marcan con **⚠️ ABIERTO** y se listan de forma central en el documento 07.
- Las referencias cruzadas usan enlaces relativos entre documentos.

## Estado de decisiones críticas

✅ **Stack finalizado:**
- **Frontend:** Vue 3 + TypeScript + Shadcn/Vue + Tailwind CSS + Pinia
- **Backend:** Python (FastAPI o Django REST, por confirmar)
- **Empaquetado:** Tauri (Rust + WebView nativa)
- **BBDD local:** SQLite + SQLCipher

Para detalles, ver [STACK_TECH.md](STACK_TECH.md) o [02 — Arquitectura](02-arquitectura.md).

✅ **Primera iteración del MVP (3 pantallas):** Inicio de sesión (mock, sin backend) → Registrar Referencia → Registrar Pago (con autocompletado de Referencia). Ver [05 — Alcance MVP y flujos](05-alcance-mvp-y-flujos.md), §2.

✅ **Sistema de color:** 90% fondos claros / 7% púrpura primario / 3% negro (texto/acento). Ver [09 — Diseño de interfaz](09-diseno-ui-ux.md).

✅ **Modelo de datos corregido:** se agregaron las entidades `Category` y `Location`, se unificó `nit`, se resolvió la ambigüedad de `iva` (`iva_percentage` + `iva_amount`), se estandarizó la precisión de los `decimal` y se añadieron columnas de integridad/sync (`hmac`, `prev_hash`, `updated_at`, `version`, `synced_at`). Ver [03 — Modelo de datos](03-modelo-datos.md), §6–§7.

✅ **Andamiaje del backend construido:** FastAPI + SQLAlchemy + Alembic + PostgreSQL (docker-compose), con modelos, migración inicial verificada y CRUD skeleton para las 8 entidades del negocio, más extensión multi-tenant (`Tenant` + `tenant_id`). Código en [`backend/`](../backend/); decisiones nuevas D-23 a D-25 en [07 — Decisiones](07-decisiones-y-puntos-abiertos.md); detalle del esquema implementado en [03 — Modelo de datos](03-modelo-datos.md), §9.

✅ **Frontend del MVP construido:** Vue 3 + TS + Tailwind + Pinia (Vite; Tauri pospuesto). Las 3 pantallas (login mock → Registrar Referencia → Registrar Pago con autocompletado y Decimal.js), verificadas en navegador. Autocontenido, no requiere backend. Código en [`frontend/`](../frontend/); decisiones D-26 a D-28 en [07 — Decisiones](07-decisiones-y-puntos-abiertos.md). Cómo correr todo: [`README.md`](../README.md).

✅ **Cimientos de infraestructura y empaquetado (F0):** backend endurecido (CORS, config por entorno, logging, manejo global de errores, health con estado de BBDD), levantable como servicio con **Docker Compose** (Postgres + API), **CI** en GitHub Actions (lint + migraciones + tests) y **scaffolding de Tauri** para generar el instalador `.exe` (empaqueta solo el frontend autocontenido). Decisiones **D-29 a D-31**; guía completa en [10 — Infraestructura y empaquetado](10-infraestructura-dev-y-empaquetado.md). **Pendiente (fases F1–F4):** auth real (stub, A-12), wiring frontend↔backend, validación financiera y firma HMAC/cadena de hash, sync, licencia e infra cloud productiva.
