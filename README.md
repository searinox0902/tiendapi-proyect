# TiendAPI

Software de gestión comercial (referencias, inventario y facturación) para pymes locales de Medellín. Arquitectura **desktop-first / local-first**.

> **Estado:** pre-MVP. Documentación en [`docs/`](docs/) (empieza por [docs/00-indice-maestro.md](docs/00-indice-maestro.md)). Fuentes originales en [`specs/`](specs/).

> 🚀 **¿Primera vez con el repo?** [`ARRANQUE.md`](ARRANQUE.md) lo pone todo a correr en
> cuatro comandos, con el usuario de acceso y la semilla del catálogo de repuestos.

## Estructura

```
tiendapi-proyect/
├── docs/         Documentación temática (arquitectura, modelo de datos, seguridad, MVP…)
├── specs/        Fuentes originales (PDFs + addendum)
├── backend/      API central — FastAPI + SQLAlchemy + Alembic + PostgreSQL
└── frontend/     App MVP — Vue 3 + TypeScript + Tailwind + Pinia (Vite; Tauri más adelante)
```

## Primera iteración del MVP (3 pantallas)

1. **Inicio de sesión** — sesión mock (cualquier usuario/clave; sin backend de auth).
2. **Registrar Referencia** — alta manual de producto.
3. **Registrar Pago** — se ingresa un SKU; si la referencia existe se **autocompleta** y los totales se calculan con Decimal.js.

En esta iteración el **frontend es autocontenido** (Pinia como fuente de verdad): no necesita el backend para funcionar.

---

## Cómo ejecutar

### Frontend (la demo navegable del MVP)

Requiere **Node.js ≥ 20**.

```bash
cd frontend
npm install
npm run dev
```

Abre la URL que imprime Vite (por defecto http://localhost:5173).

Otros scripts:

```bash
npm run build        # build de producción (incluye type-check con vue-tsc)
npm run type-check   # solo chequeo de tipos
npm run preview      # sirve el build de producción
```

### Backend (API central)

Guía completa en [docs/10 — Infraestructura y empaquetado](docs/10-infraestructura-dev-y-empaquetado.md).

**Opción A — todo con Docker (recomendada):** requiere **Docker Desktop**.

```bash
cd backend
docker compose up -d      # levanta Postgres + API, aplica migraciones sola
```

**Opción B — Python local:** requiere **Python ≥ 3.11** (Postgres vía `docker compose up -d postgres` o local).

```bash
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows (PowerShell); en Unix: source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env               # ajusta DATABASE_URL si hace falta
alembic upgrade head
uvicorn app.main:app --reload
```

- API: http://localhost:8000 · Swagger: http://localhost:8000/docs · Health: http://localhost:8000/health

> **Autenticación (F1):** los endpoints exigen un **token Bearer (JWT)**. Flujo: `POST /api/v1/auth/register` (crea negocio + propietario) → `POST /api/v1/auth/login` (devuelve `access_token`) → usar `Authorization: Bearer <token>`. El `tenant_id` se deriva del token (cierra A-12). Para datos de prueba: `python -m scripts.seed` crea `demo@tiendapi.co` / `demo1234`, y
`python -m scripts.seed_catalog` carga sobre ese negocio las **1.015 Referencias reales**
de repuestos de moto (ver [`ARRANQUE.md`](ARRANQUE.md)). Pendiente: firma HMAC/cadena de hash de facturas (F2).

### Empaquetar el instalador de escritorio (Tauri) — *pendiente*

⚠️ **Todavía no está construido:** no hay `frontend/src-tauri/` ni el script `tauri:build`.
Los comandos de abajo son el plan (D-29 a D-31), no algo que funcione hoy. Envolverá el
frontend existente como `.exe` instalable, sin tocar el código Vue. Detalle en
[docs/10](docs/10-infraestructura-dev-y-empaquetado.md), §6.

```bash
cd frontend
npm install
npx @tauri-apps/cli icon ./app-icon.png   # una vez: genera los iconos
npm run tauri:build                        # genera el instalador NSIS
```

---

## Comandos rápidos (resumen)

| Objetivo | Comando |
|----------|---------|
| Correr el MVP (frontend) | `cd frontend && npm install && npm run dev` |
| Levantar backend + BBDD (Docker) | `cd backend && docker compose up -d` |
| Solo Postgres | `cd backend && docker compose up -d postgres` |
| Migrar BBDD | `cd backend && alembic upgrade head` |
| Correr la API (local) | `cd backend && uvicorn app.main:app --reload` |
| Tests / lint del backend | `cd backend && pytest` · `ruff check .` |
| Empaquetar instalador (Tauri) | ⚠️ pendiente — el andamiaje no está en el repo |
