# API — Auth (`/api/v1/auth`)

> **Contexto:** Autenticación real del backend online (F1, D-36). Reemplaza el stub `X-Tenant-ID` y la sesión mock del frontend (D-15) — el `tenant_id` de cada request se deriva del **JWT**, nunca de un header enviado por el cliente (cierra A-12). Código: [`backend/app/api/v1/auth.py`](../../backend/app/api/v1/auth.py), [`backend/app/schemas/auth.py`](../../backend/app/schemas/auth.py), [`backend/app/models/user.py`](../../backend/app/models/user.py).

## Entidad `User` (inglés, código)

| Campo | Tipo | Notas |
|---|---|---|
| `id` | `uuid` | PK |
| `tenant_id` | `uuid` | FK a `Tenant`; negocio al que pertenece el asiento |
| `email` | `string` | **único global** (`uq_users_email`) — el login resuelve un solo usuario sin ambigüedad |
| `password_hash` | `string` | hash **argon2**, nunca se expone en las respuestas |
| `full_name` | `string` | — |
| `role` | `string` | `owner` \| `member` |
| `is_active` | `bool` | default `true`; un usuario inactivo no puede loguearse |
| `created_at` | `datetime` | heredado de `TimestampMixin` |

**Regla de negocio (D-32):** máximo **3 asientos** (`User`) por `Tenant`.

---

## `POST /api/v1/auth/login`

Autentica un usuario existente por **email + contraseña** y devuelve un **JWT** de sesión. Es el endpoint básico del MVP — no requiere token previo.

### Request

```json
{ "email": "demo@tiendapi.co", "password": "demo1234" }
```

| Campo | Tipo | Requerido | Nota |
|---|---|---|---|
| `email` | `string` (`EmailStr`) | sí | validado como email por Pydantic |
| `password` | `string` | sí | texto plano en el request; se compara contra el hash argon2 almacenado |

### Response `200 OK`

```json
{ "access_token": "eyJhbGciOiJIUzI1NiIs...", "token_type": "bearer" }
```

| Campo | Tipo | Nota |
|---|---|---|
| `access_token` | `string` | JWT firmado **HS256** |
| `token_type` | `string` | siempre `"bearer"` |

**Claims del JWT** (`app/core/security.py`): `sub` (id del `User`), `tenant_id`, `iat`, `exp`. Expira en **12 horas** (`settings.access_token_expire_minutes`, configurable por entorno).

### Errores

| Status | Causa |
|---|---|
| `401 Unauthorized` | el email no existe, o la contraseña no coincide con el hash (`verify_password`) — **mismo mensaje genérico** en ambos casos, para no filtrar qué emails existen |
| `403 Forbidden` | el usuario existe y la contraseña es correcta, pero `is_active = false` |
| `422 Unprocessable Entity` | `email` no es un email válido, o falta algún campo (validación automática de Pydantic) |

### Reglas de negocio

- `tenant_id` **no** viaja en el body ni en headers del login — se deriva del `User` autenticado y queda embebido en el token (D-36, cierra A-12).
- Todas las llamadas a otros endpoints (`/references`, `/items`, `/bills`, …) exigen `Authorization: Bearer <access_token>`; sin él, `401`.

### Ejemplo

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@tiendapi.co","password":"demo1234"}'
```

---

## `POST /api/v1/auth/register`

Bootstrap de un negocio nuevo: crea el `Tenant` y su usuario **propietario** en una sola llamada. **Abierto en el MVP** (sin gate de cobro — punto abierto A-13).

### Request

| Campo | Tipo | Requerido |
|---|---|---|
| `business_name` | `string` | sí |
| `full_name` | `string` | sí |
| `email` | `string` (`EmailStr`) | sí |
| `password` | `string` | sí |

### Response `201 Created` → `UserRead`

`id`, `tenant_id`, `email`, `full_name`, `role` (`"owner"`), `is_active`, `created_at`. **Nunca** incluye `password_hash`.

### Errores

| Status | Causa |
|---|---|
| `409 Conflict` | el `email` ya está registrado (unicidad global) |
| `422 Unprocessable Entity` | body inválido |

---

## `GET /api/v1/auth/me`

Devuelve el `User` autenticado actual. Requiere `Authorization: Bearer <access_token>`. Uso típico: el frontend lo llama al arrancar la app para validar que el token sigue vivo y precargar el nombre/rol del usuario.

| Status | Caso |
|---|---|
| `200 OK` | → `UserRead` del usuario del token |
| `401 Unauthorized` | sin token, token inválido o expirado |

---

## `POST /api/v1/auth/users`

Crea un **subusuario** (asiento adicional) dentro del negocio del usuario autenticado. Solo el `owner` puede llamarlo.

### Request

| Campo | Tipo | Requerido | Nota |
|---|---|---|---|
| `full_name` | `string` | sí | — |
| `email` | `string` (`EmailStr`) | sí | único global |
| `password` | `string` | sí | — |
| `role` | `string` | no | `"owner"` \| `"member"`; cualquier otro valor cae a `"member"` |

### Errores

| Status | Causa |
|---|---|
| `403 Forbidden` | quien llama no es `owner` |
| `409 Conflict` | límite de **3 asientos** alcanzado (D-32), o el email ya existe |
| `401 Unauthorized` | sin token válido |
