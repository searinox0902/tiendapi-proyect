# Referencia de API — por módulo

> **Contexto:** Documentación de los endpoints HTTP del backend (`backend/app/api/v1/`), un archivo por módulo. **Entidades y código en inglés** (fiel al código fuente); **prosa y explicaciones en español**. Se completa de forma incremental a medida que cada módulo se documenta — no todos existen todavía.

## Convención de cada archivo

- **Ruta base** del módulo y para qué sirve (1-2 líneas).
- Un bloque por endpoint: método + ruta, descripción, tabla de **request** (campo/tipo/requerido/nota), tabla de **response**, tabla de **errores** (status + causa), reglas de negocio relevantes (con link a la decisión en [07](../07-decisiones-y-puntos-abiertos.md) que las originó) y un ejemplo `curl`.
- Todo endpoint documentado debe existir ya en el código (`backend/app/api/v1/`) — esto es referencia de lo implementado, no diseño especulativo.

## Módulos

| Módulo | Archivo | Estado |
|---|---|---|
| Auth | [auth.md](auth.md) | ✅ documentado |
| Referencias (`Reference`) | — | pendiente |
| Productos (`Item`) | — | pendiente |
| Facturas (`Bill`/`BillItem`) | — | pendiente |
| Categorías (`Category`) | — | pendiente |
| Proveedores (`Provider`) | — | pendiente |
| Clientes (`Customer`) | — | pendiente |
| Ubicaciones (`Location`) | — | pendiente |

> Nota: [12 — Guía de consumo de auth](../12-guia-consumo-api-auth.md) es una guía de integración orientada al frontend (cómo conectar el login en Vue); este `docs/api/` es la **referencia de contrato** endpoint por endpoint. Se complementan, no se duplican.
