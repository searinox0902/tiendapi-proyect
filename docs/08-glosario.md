# 08 — Glosario

> **Contexto:** Vocabulario compartido de negocio y técnico. Cárgalo para onboarding o para alinear terminología.

## Términos de negocio

| Término | Definición |
|---------|-----------|
| **Referencia** | Plantilla/"molde" de un producto (qué es, no cuánto hay). Punto fijo del catálogo. Entidad `Reference`. |
| **Ítem** | Existencia física concreta de una Referencia (stock, sucursal, precio actual, lote/proveedor). Entidad `Item`. |
| **Proveedor** | Quien vende productos al negocio. Entidad `Provider`. |
| **Cliente** | Quien compra al negocio. Entidad `Customer`. |
| **Factura** | Documento de venta (consecutivo, subtotal, IVA, total). Entidad `Bill`. |
| **Línea de factura** | Renglón de una factura (ítem, cantidad, precio, IVA, total). Entidad `BillItem`. |
| **NIT** | Número de Identificación Tributaria (Colombia). |
| **IVA** | Impuesto al Valor Agregado. Se maneja a nivel de catálogo y de línea de venta. |
| **DIAN** | Dirección de Impuestos y Aduanas Nacionales (Colombia). Autoridad de facturación electrónica. |
| **Multi-sucursal** | Operación con varias ubicaciones; soportada vía `location_id` en `Item`. |

## Términos técnicos

| Término | Definición |
|---------|-----------|
| **Desktop-first / local-first** | Arquitectura donde la BBDD local es la fuente de verdad y la operación no depende de internet. |
| **Tauri** | Framework de apps de escritorio (Rust + WebView del sistema). Alternativa liviana a Electron. |
| **SQLite** | Motor de BBDD local embebido; fuente de verdad operativa. |
| **SQLCipher** | Extensión de SQLite que cifra toda la base con AES-256. |
| **PostgreSQL** | BBDD central en servidor; destino de sincronización y respaldo. |
| **HMAC** | Firma criptográfica con clave secreta; detecta manipulación de registros. |
| **Cadena de hash** | Cada factura guarda el hash de la anterior (tipo libro contable); alterar una rompe la cadena. |
| **Authenticode** | Firma de código de Microsoft para binarios/instaladores de Windows. |
| **ed25519** | Esquema de firma usado por el actualizador de Tauri para validar paquetes. |
| **DPAPI / Credential Manager** | Almacén seguro de Windows para claves/secretos. |
| **Token de licencia** | Credencial firmada por el servidor con "pagado hasta", gracia y próxima verificación. |
| **Ventana de gracia** | Periodo corto de operación offline permitido tras vencer el token (borrador: 2–3 días). |
| **Marca de agua monotónica** | Hora máxima jamás vista, persistida para detectar retroceso del reloj. |
| **Decimal.js** | Librería JS para aritmética decimal exacta (evita errores de punto flotante). |
| **XML de proveedor** | Archivo que envía el proveedor; se parsea para crear/actualizar referencias. |
| **UBL 2.1** | Estándar de documento electrónico usado por la DIAN (relevante solo para el tercero facilitador). |
| **HID** | Human Interface Device; categoría de los escáneres de código de barras (funcionan como teclado). |
| **Aislamiento por cliente** | Cada cliente opera y sincroniza en un espacio propio e independiente (no multi-tenant compartido). |
