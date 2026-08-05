# 10 — Infraestructura de desarrollo y empaquetado

> **Contexto:** Cómo se levanta el entorno hoy (backend como servicio + BBDD), cómo se empaqueta el frontend como instalador de escritorio, y cómo se relaciona todo esto con la arquitectura objetivo. Cárgalo para poner a correr el proyecto en equipo, hacer builds del instalador o entender la diferencia entre "topología de desarrollo" y "topología objetivo". Decisiones asociadas: **D-29, D-30, D-31** en [07](07-decisiones-y-puntos-abiertos.md).

## 1. Dos topologías: NO confundirlas

Este es el punto más importante del documento.

### Topología OBJETIVO (la de [02 — Arquitectura](02-arquitectura.md), §8)

```
APP DESKTOP (Tauri)                         CLOUD (capa delgada)
  Vue 3 ── SQLite+SQLCipher   ──sync──►     FastAPI ── PostgreSQL
  (fuente de verdad, vía Rust)              (respaldo, auth, licencia)
```

- El desktop lee/escribe su **SQLite local** directamente (vía Rust). Es la fuente de verdad.
- FastAPI vive en la **nube** sobre **PostgreSQL**; es respaldo/sync/auth, no la BBDD operativa.

### Topología de DESARROLLO (la de HOY)

```
Frontend (Vite/Tauri)   Backend (Docker)
  Vue 3 + Pinia          FastAPI ── PostgreSQL
  (autocontenido,        (levantado con
   NO llama al backend)   docker compose)
```

- El frontend es **autocontenido** (Pinia = fuente de verdad, D-27) y **todavía no consume el backend**.
- El backend FastAPI + Postgres se levanta con Docker como servicio, para desarrollarlo y probarlo **por separado**.
- El instalador Tauri empaqueta **solo el frontend** (D-31). No embebe Python.

> **Regla:** el "backend embebido en el .exe" **no existe** en esta etapa y **no es** la arquitectura objetivo. Si en el futuro se embebe (sidecar PyInstaller), será una decisión explícita cuando comiencen las integraciones (fase F1).

## 2. Requisitos por rol

| Vas a… | Necesitas |
|--------|-----------|
| Correr el frontend (demo navegable) | Node ≥ 20 |
| Correr el backend + BBDD | Docker Desktop (recomendado) **o** Python ≥ 3.11 + Postgres local |
| Generar el instalador `.exe` | Node ≥ 20 + **Rust** (rustup) |

## 3. Levantar el backend (servicio central)

### Opción A — Todo con Docker (recomendada)

Desde `backend/`:

```bash
docker compose up -d          # levanta Postgres + API (aplica migraciones sola)
```

- API: http://localhost:8000 · Swagger: http://localhost:8000/docs · Health: http://localhost:8000/health
- El `Dockerfile` corre `alembic upgrade head` antes de arrancar uvicorn.

Solo la BBDD (para correr la API a mano con `--reload`):

```bash
docker compose up -d postgres
```

### Opción B — Python local (sin Docker para la API)

```bash
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1      # Windows PowerShell
pip install -r requirements-dev.txt
copy .env.example .env           # ajusta DATABASE_URL si hace falta
alembic upgrade head
uvicorn app.main:app --reload
```

### Health check

`GET /health` responde con el estado real de la BBDD:

```json
{ "status": "ok", "database": "connected", "environment": "development" }
```

Si Postgres no está accesible: `{ "status": "degraded", "database": "unreachable", ... }`.

## 4. Configuración (variables de entorno)

Definidas en `backend/app/core/config.py` y documentadas en `backend/.env.example`:

| Variable | Default | Rol |
|----------|---------|-----|
| `DATABASE_URL` | Postgres local | Conexión a la BBDD central |
| `ENVIRONMENT` | `development` | `development` \| `production` |
| `LOG_LEVEL` | `INFO` | Nivel de logging (a stdout) |
| `CORS_ORIGINS` | Vite + `tauri://localhost` | Orígenes permitidos (coma-separado) |
| `SECRET_KEY` | inseguro | Firma del **token de sesión/JWT** (auth real, F1). En producción: secreto fuerte vía env |
| `JWT_ALGORITHM` / `ACCESS_TOKEN_EXPIRE_MINUTES` | `HS256` / `720` | Algoritmo y expiración del access token |

## 5. Calidad: lint, tipos y tests

```bash
cd backend
ruff check .        # lint (config en pyproject.toml)
mypy app            # tipos (opcional)
pytest              # tests (requiere Postgres accesible)
```

Los tests actuales (`backend/tests/`) cubren el health check y el aislamiento por
tenant del endpoint de referencias (lista vacía + header requerido). Es una base
mínima para crecer, no cobertura completa.

### CI (GitHub Actions)

`.github/workflows/ci.yml` corre en cada push/PR: levanta un Postgres de servicio,
instala dependencias, pasa `ruff`, aplica migraciones y corre `pytest`. No necesita
Docker local: GitHub provee el Postgres.

## 6. Empaquetado del instalador (Tauri)

Envuelve el frontend **existente** como app instalable (D-29). No modifica el código Vue.

### Preparar (una vez)

1. Instala Rust: https://rustup.rs → `rustup default stable`
2. Instala deps del frontend (incluye la CLI de Tauri): `cd frontend && npm install`
3. Genera los iconos desde un PNG cuadrado:
   ```bash
   npx @tauri-apps/cli icon ./app-icon.png
   ```
   (crea `src-tauri/icons/` con todos los tamaños que pide `tauri.conf.json`)

### Desarrollo y build

Desde `frontend/`:

```bash
npm run tauri:dev     # ventana nativa con Vite en caliente (HMR)
npm run tauri:build   # genera el instalador NSIS
```

Instalador resultante:
`frontend/src-tauri/target/release/bundle/nsis/TiendAPI_0.1.0_x64-setup.exe`

### Nota

El `.exe` corre el frontend autocontenido: sirve para **ver y validar las pantallas y
flujos** con aspecto de programa instalado, sin backend ni red. Al abrir integraciones
reales se revisará el `base` de Vite y la política CSP de `tauri.conf.json`.

## 7. Workflow de desarrollo frontend — qué usar cuándo

**Decisión crítica:** hay tres formas de correr el frontend mientras desarrollas. Cada una es óptima para un caso diferente. **Lee esta sección si trabajas en Vue/frontend.**

### Opción A: Navegador + Vite dev server — **Usa esto el 95% del tiempo** ⭐

```bash
cd frontend
npm run dev
# → http://localhost:5173
```

**Características:**
| Aspecto | Detalle |
|--------|--------|
| 🔄 **Hot Module Reload (HMR)** | Cambias código → guardas → **aparece al instante** en el navegador (subsegundos), sin recargar |
| ⚡ **Velocidad** | Súper rápido; compilación incremental |
| 🛠️ **DevTools** | Inspeccionar elementos, consola, network, Vue DevTools |
| 📦 **No compila Rust** | No toca Tauri, Node es suficiente |
| 👁️ **Aspecto** | En una pestaña de navegador (localhost:5173), no en ventana nativa |

**Cuándo usarla:**
- ✅ Editar componentes Vue (`.vue`).
- ✅ Cambios en estilos Tailwind.
- ✅ Lógica de Pinia/stores.
- ✅ 95% del desarrollo diario.

**Ejemplo:** editas `frontend/src/views/RegisterReferenceView.vue`, guardas, y **al instante ves el cambio en http://localhost:5173**.

---

### Opción B: Ventana nativa Tauri + HMR — **Usa esto antes de cambios grandes** 

```bash
cd frontend
npm run tauri:dev
# → abre una ventana nativa ("TiendAPI") con Vite en caliente
```

**Características:**
| Aspecto | Detalle |
|--------|--------|
| 🪟 **Ventana nativa** | Tauri abre la app como `.exe`, no en navegador |
| 🔄 **HMR integrado** | Vite sigue recompilando; cambios se reflejan en la ventana |
| ⏱️ **Primer run** | Compila Rust (~2 min); luego HMR es tan rápido como Opción A |
| 🎨 **Tamaño real** | Ves la app en 1280×800 como será en producción |
| 🧪 **Testing nativo** | Valida que funcione en una ventana real (CSS, eventos, WebView) |

**Cuándo usarla:**
- ✅ Después de cambios grandes (nuevo componente, refactor importante).
- ✅ Antes de comprometerte a `npm run tauri:build`.
- ✅ Para validar que **se ve bien en una ventana nativa** (no solo navegador).
- ⚠️ No es para cambios rápidos (el primer run compila Rust, toma tiempo).

**Flujo típico:**
```
1. npm run dev              (iteración rápida, 30-40 min)
2. Guardas cambios grandes
3. npm run tauri:dev        (validar en ventana real)
4. ¿Se ve bien? → continúas en Opción A
5. ¿Listo para QA? → Opción C
```

---

### Opción C: Instalador NSIS — **Solo para release, NUNCA en desarrollo** ⛔

```bash
cd frontend
npm run tauri:build
# → genera TiendAPI_0.1.0_x64-setup.exe (~9 min)
```

**Características:**
| Aspecto | Detalle |
|--------|--------|
| ⏱️ **Tiempo** | ~9 min (Rust compila, NSIS ensambla) |
| 📦 **Artefacto** | El `.exe` instalador listo para compartir/distribuir |
| 🚫 **SIN HMR** | No recompila con cambios; el `.exe` está congelado |
| 📤 **Distribución** | Para tester, stakeholder, release final |

**⛔ NUNCA hagas esto:**
```bash
# ❌ MALO — No hagas esto cada vez que edites código
while true; do npm run tauri:build; done
```

**Cuándo usarla:**
- ✅ Cada **semana o 2 semanas** cuando hayas terminado features.
- ✅ Para compartir un `.exe` con QA/tester.
- ✅ Antes de un release.

---

### Tabla comparativa — ¿cuál elegir?

```
┌────────────────────┬──────────────────┬────────────────────┬──────────────────┐
│ Uso                │ Navegador (A)    │ Tauri dev (B)      │ Instalador (C)   │
├────────────────────┼──────────────────┼────────────────────┼──────────────────┤
│ Velocidad HMR      │ ⚡ subsegundos   │ ⚡ subsegundos*   │ ❌ sin HMR        │
│ Tiempo first run   │ 10s              │ ~2 min (Rust)      │ ~9 min            │
│ Requiere Rust      │ ❌ No            │ ✅ Sí              │ ✅ Sí             │
│ Ventana real       │ ❌ No (browser)  │ ✅ Sí              │ ✅ Sí             │
│ Desarrollo diario  │ ✅ MEJOR         │ 🟡 Ocasional       │ ❌ NO             │
│ Release / QA       │ ❌ No            │ ❌ No              │ ✅ MEJOR          │
└────────────────────┴──────────────────┴────────────────────┴──────────────────┘
* Después del primer run (que compila Rust)
```

---

### Recomendación: tu flujo diario

```
09:00 — Inicio del día
   ↓
npm run dev                    ← abre http://localhost:5173
   ↓
Edito componentes (LoginView, RegisterReferenceView, etc.)
Cambio estilos, lógica Pinia
   ↓ guardar
Veo cambios al instante (HMR)
   ↓ (30 min después)
npm run tauri:dev              ← validar en ventana real
   ↓
¿Se ve bien? Sí → continúo en npm run dev
   ↓ (1 semana después, features terminadas)
npm run tauri:build            ← genero el .exe final
   ↓
Comparto `TiendAPI_...-setup.exe` con QA/tester
```

---

### Conexión con el backend (F1+)

Cuando empieces a llamar el backend (fases F1+), **ambas opciones A y B** apuntan al mismo backend sin cambios de código:

```typescript
// frontend/src/api/config.ts (pseudocódigo)
export const API_BASE = 
  import.meta.env.DEV 
    ? 'http://localhost:8000'  // tanto npm run dev como npm run tauri:dev
    : 'http://localhost:8000'  // tauri:build también (antes de producción)
```

Configura el backend en `backend/.env`:
```bash
CORS_ORIGINS=http://localhost:5173,tauri://localhost
```

Con esto, en desarrollo:
- `npm run dev` → frontend en http://localhost:5173 llama a http://localhost:8000.
- `npm run tauri:dev` → frontend en ventana Tauri llama a http://localhost:8000.
- Ambos llaman al **mismo backend** sin reconfigurar nada.

## 8. Qué NO está hecho todavía (y a qué fase pertenece)

| Pendiente | Fase | Referencia |
|-----------|------|------------|
| ✅ Auth real (JWT, tenant desde token) — **hecho** | F1 | D-36, A-12 |
| Onboarding de Tenant atado a cobro (hoy `register` abierto) | F1+ | A-13 |
| Validación financiera en servidor + regla de redondeo | F2 | A-06, [04](04-seguridad.md) |
| Firma HMAC + cadena de hash de facturas | F2 | D-07, [04](04-seguridad.md) |
| Wiring frontend ↔ backend (integraciones) | F1+ | D-31 |
| Motor de sync + resolución de conflictos | F3 | A-01, [02](02-arquitectura.md) §7 |
| Token de licencia + anti-manipulación de reloj | F3 | D-08, [04](04-seguridad.md) |
| Infra cloud productiva (TLS, secretos, backups, deploy) | F4 | — |

> Las fases F1–F4 son el roadmap de integración real. Este documento cubre F0
> (cimientos de desarrollo/empaquetado). Ver el detalle de fases en el historial de
> decisiones y en [06 — Roadmap](06-equipo-riesgos-roadmap.md).
