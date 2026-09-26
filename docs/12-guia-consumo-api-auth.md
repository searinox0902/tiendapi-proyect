# 12 — Guía: conectar el login del frontend a la API (auth real)

> **Contexto:** Contrato para que el **frontend** consuma la autenticación real del backend (F1, D-36). Es material de referencia para implementar la integración en Vue; **no** modifica el frontend. El backend ya está listo y verificado (CORS incluido).

## 1. Antes de empezar

- **Backend arriba:** desde `backend/`, `docker compose up -d`. API en `http://localhost:8000` (Swagger en `/docs`).
- **Usuario de prueba:** `python -m scripts.seed` crea **`demo@tiendapi.co` / `demo1234`**.
- **CORS:** ya permitido para `http://localhost:5173` (Vite) y `tauri://localhost` (el `.exe`). No hay que configurar nada más en el navegador.
- **URL base sugerida en el frontend:**
  ```ts
  const API_BASE = import.meta.env.DEV ? "http://localhost:8000" : "http://localhost:8000";
  // en producción se cambia por el dominio real del backend
  ```

## 2. Endpoints de autenticación

| Método | Ruta | Body (JSON) | Respuesta | Errores |
|--------|------|-------------|-----------|---------|
| `POST` | `/api/v1/auth/register` | `{ business_name, full_name, email, password }` | `201` → usuario propietario | `409` email ya existe |
| `POST` | `/api/v1/auth/login` | `{ email, password }` | `200` → `{ access_token, token_type }` | `401` credenciales inválidas |
| `GET` | `/api/v1/auth/me` | — (requiere token) | `200` → usuario actual | `401` sin/mal token |
| `POST` | `/api/v1/auth/users` | `{ full_name, email, password, role }` | `201` → subusuario | `403` no owner · `409` límite de 3 asientos |

**Todos los demás endpoints** (`/references`, `/bills`, …) requieren el token: sin él responden `401`; con él, el backend deriva el `tenant_id` **del token** (no de ningún header). El frontend **no** maneja `tenant_id` — solo el token.

## 3. Flujo de login (patrón a implementar)

1. El usuario envía email + password → `POST /auth/login`.
2. Guardas el `access_token` (JWT). Expira en **12 h**.
3. En cada petición protegida envías el header:
   ```
   Authorization: Bearer <access_token>
   ```
4. Si una petición responde `401`, el token venció o es inválido → vuelves a la pantalla de login.

### Ejemplo de referencia (fetch) — para el login

```ts
async function login(email: string, password: string): Promise<string> {
  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error("Credenciales inválidas"); // 401
  const data = await res.json();
  return data.access_token;
}

// Petición autenticada:
async function getMe(token: string) {
  const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("No autenticado");
  return res.json();
}
```

> Si prefieres **Axios** (está en el stack decidido, STACK_TECH), el patrón es el mismo: un interceptor que agrega `Authorization: Bearer <token>` a cada request y que redirige al login ante un `401`.

## 4. Dónde guardar el token

- **Simple para empezar:** en memoria (un store de Pinia) + `localStorage` para que sobreviva a recargas.
- **Nota de seguridad:** el JWT da acceso al negocio mientras no expire; en el `.exe` (Tauri) vive solo en la máquina del usuario. Para el MVP, `localStorage` es aceptable; el endurecimiento (dónde persistir el token en el desktop) es tema de fases posteriores ([04 — Seguridad](04-seguridad.md)).

## 5. La costura con lo que ya existe

Los stores de Pinia exponen la firma pensada como **costura** para el backend (D-27: `addReference`/`findBySku`, etc.). Conectar el login fue: llamar a `/auth/login`, guardar el token, y mandar el header `Authorization` en las llamadas de datos. El resto de pantallas no cambió de forma.

## 6. Estado: hecho (D-15 y A-10 cerrados)

**Ya no hay sesión mock.** El backend ofrece auth real (D-36) y el frontend la consume: `frontend/src/stores/auth.ts` llama a `POST /auth/login`, guarda el `access_token` en `localStorage` y lo manda como Bearer. Esto cerró D-15 y el punto abierto A-10. Lo que sigue abajo es la referencia del contrato, no trabajo pendiente.

> **Prueba rápida sin frontend:** `http://localhost:8000/docs` → `POST /auth/login` con el usuario demo → copia el `access_token` → botón **Authorize** → ya puedes llamar los endpoints protegidos desde Swagger.
