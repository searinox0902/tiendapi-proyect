# Stack Tecnológico — Referencia Rápida

> Hoja de referencia del stack decidido. Para contexto completo, ver [02 — Arquitectura](02-arquitectura.md) y [07 — Decisiones](07-decisiones-y-puntos-abiertos.md).

## Frontend (App Desktop)

| Componente | Tecnología | Versión | Rol |
|------------|-----------|---------|-----|
| **Framework** | Vue 3 (Composition API) | 3.x | Interfaz reactiva |
| **Lenguaje** | TypeScript | 5.x | Type safety |
| **Estado** | Pinia | 2.x | Gestión de estado |
| **Estilos** | Tailwind CSS + Shadcn/Vue | Latest | UI responsivo + componentes |
| **Validación** | VeeValidate + Zod | Latest | Validación de formularios |
| **HTTP** | Axios | 1.x | Cliente REST/API |
| **Offline** | IndexedDB (Dexie) + Service Worker | Latest | Persistencia local/web |
| **Cálculos** | Decimal.js | 10.x | Aritmética decimal exacta |
| **Empaquetado** | Tauri (Rust + WebView nativa) | 2.x | App de escritorio |

> ⚠️ **Crítico:** Cálculos financieros con Decimal.js, **nunca punto flotante**. Todo redondeo debe validarse manualmente.

## Backend (API & Lógica)

| Componente | Tecnología | Rol |
|------------|-----------|-----|
| **Lenguaje** | Python 3.11+ | Servidor de aplicación |
| **Framework** | FastAPI o Django REST (a confirmar) | API REST, parseo XML |
| **ASGI/WSGI** | Uvicorn (FastAPI) o Gunicorn (Django) | Servidor de aplicación |
| **Integración HID** | PyUSB / PySerial o librería de escáner | Lectura de códigos de barras |
| **Parseo XML** | lxml o ElementTree | Carga automática de catálogos |
| **Cálculos** | Decimal (Python stdlib) | Aritmética financiera |
| **Async/Sync** | AsyncIO + ORM (async SQLAlchemy si FastAPI) | Operaciones de base de datos |

> **Por confirmar:** FastAPI (más ligero, async nativo) vs. Django REST (más ecosystem).

## Bases de Datos

| Capa | Tecnología | Rol |
|------|-----------|-----|
| **Local (cliente)** | SQLite + SQLCipher (AES-256) | Fuente de verdad operativa, offline-first |
| **Central (servidor)** | PostgreSQL 14+ | Respaldo, sincronización, continuidad multi-equipo |

## Servicios en la Nube (thin layer)

| Servicio | Tecnología | Rol |
|----------|-----------|-----|
| **Auth/Sesiones** | JWT + Redis (opcional caché) | Validación de licencia y sesión |
| **Pago** | Stripe / MercadoPago (a confirmar) | Cobro de suscripción mensual |
| **Distribuidor de actualizaciones** | Tauri Updater + S3/CDN | Distribución segura de nuevas versiones |
| **Sincronización** | API REST + eventos (WebSocket opcional) | Replicación de cambios SQLite → PostgreSQL |

## Seguridad (aplicado en stack)

| Aspecto | Implementación |
|--------|-----------------|
| **Cifrado en reposo (local)** | SQLCipher (AES-256, transparente) |
| **Integridad de datos** | HMAC por registro + cadena de hash en facturas |
| **Firma de código** | Authenticode (Windows) + ed25519 (updater Tauri) |
| **Clave de DB local** | Windows DPAPI / Credential Manager / Tauri vault |
| **Token de licencia** | JWT / custom firmado por servidor con gracia offline |
| **Protección de reloj** | Marca de tiempo del servidor + marca de agua monotónica |

## Desarrollo

- **Control de versiones:** Git (GitHub)
- **CI/CD:** GitHub Actions (a configurar)
- **Testing:** Vitest (frontend) + pytest (backend)
- **Linting/Format:** ESLint + Prettier (frontend); Black + Ruff (backend)
- **IDE recomendado:** VS Code + extensiones (Volar para Vue, Python)

## Especificaciones de referencia

- **Protocolo:** REST con JSON; WebSocket (opcional, para sync en tiempo real)
- **Esquema de datos:** PostgreSQL; DDL en [03 — Modelo de datos](03-modelo-datos.md)
- **Documentación API:** OpenAPI 3.0 (generado por FastAPI/Swagger)

---

**Última actualización:** julio 2026 — decisiones finalizadas (D-12, D-13 en [07](07-decisiones-y-puntos-abiertos.md)).
