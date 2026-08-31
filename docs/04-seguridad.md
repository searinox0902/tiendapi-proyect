# 04 — Seguridad

> **Contexto:** Modelo de amenazas y controles para un binario que corre en una máquina **no confiable** controlada por el cliente. Cárgalo para cifrado de BBDD, integridad de facturas, licenciamiento offline y hardening.

## 1. Principios de seguridad

El programa corre en un equipo que controla el propio cliente → debe asumirse un **entorno no confiable**. El objetivo realista **no** es hacer el sistema imposible de alterar (imposible en una máquina ajena), sino que **toda alteración sea detectable (a prueba de evidencia)** y que **el servidor sea siempre la autoridad final**.

Tres reglas guía:

1. **No confiar en el cliente:** todo lo crítico (estado de pago, integridad de facturas) se valida en el servidor al autenticar o sincronizar.
2. **Cifrar en reposo y firmar la integridad:** el cifrado impide leer/editar casualmente; las firmas permiten detectar cualquier cambio.
3. **El servidor manda:** cualquier discrepancia detectada al reconectar se corrige contra el servidor.

### 1.1 Hash de contraseñas — Argon2id (D-82)

Las contraseñas se guardan con **Argon2id**, en la configuración **mínima recomendada por OWASP**: `m=19 MiB, t=2, p=1` ([`backend/app/core/security.py`](../backend/app/core/security.py)).

Se bajó desde el default de `argon2-cffi` (64 MiB, t=3, p=4) por una queja de latencia real en el login, **medida antes de tocar nada**: el default daba mediana **286 ms con picos de 1683 ms** dentro del contenedor; la configuración actual da **42 ms**. El pico venía sobre todo de `parallelism=4` compitiendo por CPU — con `p=1` el tiempo además deja de variar.

⚠️ **Es el piso de lo aceptable, no un punto medio.** Bajar más sale de la recomendación. Argon2 es lento *a propósito*: es lo que encarece forzar las contraseñas si alguien se lleva la base — escenario nada teórico acá, porque el respaldo del proyecto (D-77) sale **sin cifrar** mientras SQLCipher (§2, D-06) no esté implementado. Si se quiere subir la exigencia, el candidato es la config *estándar* de OWASP (46 MiB, t=1, p=1), medida en 139 ms.

**Los hashes viejos se migran solos.** Argon2 guarda sus parámetros dentro del propio hash, así que una cuenta creada con la configuración anterior seguiría verificándose —y pagando su latencia— para siempre. `POST /auth/login` llama a `needs_rehash()` y reescribe el hash tras un login **correcto**, que es el único momento en que la contraseña en claro está disponible para volver a derivarlo. Verificado: el hash de la cuenta demo pasó de `$argon2id$v=19$m=65536,t=3,p=4$…` a `$argon2id$v=19$m=19456,t=2,p=1$…` en el primer login, y **no** se reescribe en un login fallido.

## 2. Integridad y cifrado de la BBDD local

SQLite por defecto es un archivo plano editable con cualquier visor. Se cifra con **SQLCipher (AES-256, cifrado transparente de toda la base)**, accesible desde Rust/Tauri → **cifrado de base completa**, no solo campos sueltos.

### Gestión de la clave
- **No** se guarda en texto plano ni dentro del ejecutable.
- Se almacena en el **almacén seguro del SO** (Windows DPAPI / Credential Manager, o el vault cifrado de Tauri).
- Puede **derivarse** de las credenciales del usuario + un secreto entregado por el servidor en la primera sesión autenticada → la base no se abre sin haber iniciado sesión al menos una vez.

### Integridad verificable (más allá del cifrado)
El cifrado da confidencialidad, pero quien tenga la clave aún podría modificar datos. Sobre los registros sensibles se añade integridad criptográfica:

- **Firma HMAC por registro:** cada factura y movimiento crítico lleva una firma con clave secreta; una firma inválida al leer/sincronizar delata manipulación.
- **Cadena de hash en facturas:** cada factura incluye el hash de la anterior (secuencia encadenada, tipo libro contable). Borrar o alterar una factura pasada **rompe la cadena** y se detecta.
- **Reconciliación en el servidor:** al sincronizar, el servidor compara hashes/firmas y marca discrepancias. Es la **garantía final** de integridad.

> Impacto en el esquema: requiere columnas de integridad (`hmac`, `prev_hash`, etc.) no presentes aún en [03 — Modelo de datos](03-modelo-datos.md).

## 3. Protección del pago/suscripción sin conexión

El derecho de uso se entrega como un **token de licencia firmado por el servidor** (verificable pero no falsificable ni extensible por el cliente). El token contiene: fecha **"pagado hasta"**, **ventana de gracia** y **fecha de próxima verificación**.

- Se permite operar **totalmente offline** durante un margen corto (p. ej. **2–3 días de gracia**) tras la validez del token.
- El sistema registra la posible fecha de corte y muestra **avisos crecientes** al acercarse, sin bloquear de golpe a quien paga y solo tiene el internet caído.
- Agotada validez + gracia sin verificación en línea exitosa → **modo restringido** (p. ej. solo lectura o bloqueo de nuevas facturas) con mensaje "reconéctate para continuar".
- En cada conexión exitosa, el servidor **renueva el token** y recalcula el estado real de pago, corrigiendo desfases.

> La gracia se apoya en tiempo → debe blindarse contra manipulación del reloj (sección 5).

## 4. Protección contra alteración de archivos

- **Firma de código (Authenticode):** ejecutable e instalador de Windows firmados; el SO detecta modificaciones del binario.
- **Actualizador firmado:** el updater de Tauri verifica cada paquete con firma **ed25519** contra una clave pública embebida antes de instalar; impide actualizaciones falsas o alteradas.
- **Datos y configuración:** el token de licencia ya viene firmado por el servidor; otros archivos sensibles se protegen con **HMAC** para detectar edición.
- **Principio general:** la integridad no depende de una verificación local (parcheable), sino de la **firma del servidor** y la **reconciliación al sincronizar**.

## 5. Protección contra manipulación del reloj

Como la gracia offline depende del tiempo, el ataque esperable es **retrasar el reloj** de la PC. Mitigaciones:

- **Tiempo anclado al servidor:** cada contacto (auth, sync, pago) trae una marca de tiempo firmada; se guarda la última hora confiable.
- **Marca de agua monotónica:** se persiste la **hora máxima jamás vista**. Si el reloj local es anterior, se considera manipulación → no se reinicia la gracia y puede pasar a modo restringido.
- **Contador de uso independiente del reloj:** contador monotónico de uso, de modo que retroceder el reloj no regale gracia nueva.
- **Autocorrección al reconectar:** el servidor recalcula el derecho real y marca al cliente si reporta tiempos imposibles.

> **Limitación honesta:** en una máquina que el usuario controla no se puede impedir el fraude de forma absoluta durante un offline prolongado. El diseño lo vuelve difícil y **autocorregible al reconectar**; por eso la gracia es **corta** y la verificación en línea, **periódica**.

## 6. Resumen de controles (matriz amenaza → control)

| Amenaza | Control | Mecanismo |
|---------|---------|-----------|
| Lectura/edición de la BBDD | Cifrado en reposo | SQLCipher (AES-256) + clave en almacén seguro del SO |
| Alteración de facturas/registros | Integridad verificable | Firma HMAC + cadena de hash + reconciliación en servidor |
| Uso sin pagar / caducidad | Licencia firmada | Token firmado con validez + gracia; verificación periódica |
| Modificación del ejecutable | Firma de código | Authenticode (Windows) + actualizador Tauri firmado (ed25519) |
| Manipulación del reloj | Tiempo anclado al servidor | Marca de tiempo firmada + marca de agua monotónica |

## 7. Integridad operativa: libro append-only (agregar / anular / nota crédito)

> Cómo se concilian dos objetivos que parecían opuestos: que el dueño pueda **registrar libremente la realidad** (D-34) y que la **cadena de hash siga detectando manipulación** (D-07). Decisión asociada: **D-35** en [07](07-decisiones-y-puntos-abiertos.md).

La cadena de hash de la sección 2 solo sirve si **alterar una factura pasada rompe la cadena y se detecta**. Por eso, editar una factura *en sitio* apagaría esa protección — que existe para proteger al dueño de que un empleado modifique ventas en silencio. La solución es tratar los registros financieros como un **libro contable: no se borra ni se sobrescribe, se agrega un asiento que corrige.**

- **"Editar" no existe como verbo.** Las únicas operaciones son **agregar**, **anular** y **corregir** (ver la tabla en [02](02-arquitectura.md), §9.4).
- **Anular** = un registro de anulación **vinculado** al original que **revierte los efectos** (inventario, caja), sin borrar nada. La factura original permanece en la cadena, intacta.
- **Corregir** = anular + emitir una factura nueva. Si la original **ya fue autorizada por la DIAN**, la corrección **obligatoria** es una **nota crédito** tramitada por el proveedor (D-09), porque la factura autorizada es **inmutable** ante el Estado.
- Como nada se sobrescribe, **la cadena de hash nunca se rompe por operación legítima** → la alarma de manipulación conserva su valor (no "suena siempre").

**Distinción de acceso vs. integridad:** restringir *quién* puede anular (p. ej. solo el maestro) es control de **acceso**; no sustituye a la integridad. Aunque solo el maestro pudiera editar, una edición destructiva rompería igual la firma. Por eso la respuesta correcta es *append-only*, no "editar con permiso".

### Idempotencia del registro fiscal (D-38)

El flujo DIAN (`maestro → servidor remoto → proveedor → registra → maestro`, ver [02](02-arquitectura.md), §9.7) **no es atómico** de punta a punta. Si el proveedor autoriza y el remoto registra, pero la **respuesta de vuelta al maestro se pierde**, un reintento ingenuo generaría una **segunda factura autorizada** — un error financiero/legal grave. Mitigación obligatoria: el maestro incluye un **id único de solicitud**; el servidor, ante un id ya procesado, **devuelve el mismo CUFE** en lugar de volver a autorizar. La numeración/CUFE la asigna la DIAN al autorizar (no un contador local), lo que además evita colisiones de identidad fiscal.
