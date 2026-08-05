# Notas para retomar — TiendAPI

_Última sesión: 2026-07-03. Backend apagado; el volumen de datos (`backend_tiendapi_pgdata`) se conservó, así que el usuario demo y los datos siguen ahí._

## Encender el backend (2 comandos)

```powershell
cd backend
docker compose up -d
```

- API: http://localhost:8000 · Swagger: http://localhost:8000/docs · Health: http://localhost:8000/health
- Levanta Postgres + API y aplica migraciones solo. Espera ~10 s y revisa `/health` → debe decir `"database":"connected"`.
- Apagar al terminar: `docker compose down` (los datos persisten; añade `-v` **solo** si quieres borrarlos).

## Usuario de prueba

- **demo@tiendapi.co / demo1234** (ya existe en el volumen).
- Si alguna vez arrancas con BBDD limpia, recréalo: `docker compose exec api python -m scripts.seed`

## Probar el login sin frontend (30 s)

`http://localhost:8000/docs` → `POST /auth/login` con el usuario demo → copia el `access_token` → botón **Authorize** → ya puedes llamar `/references`, `/bills`, etc.

## En qué quedamos

**Hecho:**
- **F0** — backend endurecido (CORS, logging, errores, health), Docker Compose, CI, e instalador Tauri (`.exe`).
- **F1** — **autenticación real**: `register` / `login` (JWT) / `me` / subusuarios (≤3 asientos). El `tenant_id` sale del token (A-12 cerrado). Validado en vivo.
- Arquitectura offline/resiliencia/maestro-esclavo/facturas append-only decidida y documentada.

**Lo que ibas a hacer tú (en Vue, sin que yo toque el frontend):**
- Conectar el login: `POST /auth/login` → guardar el token → mandar `Authorization: Bearer <token>` en las llamadas.
- Guía completa con el contrato: [docs/12](docs/12-guia-consumo-api-auth.md).

**Siguiente conmigo cuando quieras — F2 (integridad financiera):**
- El servidor recalcula los totales de factura (no confiar en el cliente) + regla de redondeo (A-06).
- Descuento de stock en la misma transacción.
- Firma HMAC + cadena de hash de facturas (D-07/D-35).

## Documentos clave

- Índice: [docs/00](docs/00-indice-maestro.md)
- Decisiones (incluye D-32…D-36, A-12 resuelto): [docs/07](docs/07-decisiones-y-puntos-abiertos.md)
- Infra dev + empaquetado: [docs/10](docs/10-infraestructura-dev-y-empaquetado.md)
- Informe offline/resiliencia/facturas: [docs/11](docs/11-offline-resiliencia-y-facturacion.md)
- Guía de integración del login: [docs/12](docs/12-guia-consumo-api-auth.md)

## Toolchain (ya instalado en esta máquina)

- Docker ✅ · Rust/Cargo ✅ (para el `.exe`) · Node 22 ✅ · Python 3.13 ✅
- Recompilar el instalador (si lo necesitas): `cd frontend && npm run tauri:build` (abre terminal nueva para que `cargo` esté en el PATH).
