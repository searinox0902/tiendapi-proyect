# 06 — Equipo, Riesgos y Roadmap

> **Contexto:** Quién construye, cómo se trabaja, qué puede salir mal y qué sigue. Cárgalo para planificación y gestión de riesgos.

## 1. Equipo y forma de trabajo

- **Líder de proyecto / Frontend Sr.:** maquetación, integración de funcionalidades, UX.
- **Backend Sr. (colaboración ocasional):** API, parseo XML, cálculos, base de datos.
- **Arquitecto (asesoría puntual):** validación del esquema de datos y decisiones estructurales.
- **Desarrollo asistido por IA** para el código base, con **revisión y testing manual obligatorio** antes de producción — especialmente en:
  - Cálculos financieros.
  - Parseo de XML.
  - Controles de seguridad.

## 2. Riesgos a vigilar

| Riesgo | Naturaleza | Documento relacionado |
|--------|-----------|------------------------|
| Validación de demanda real (aún sin clientes confirmados, solo hipótesis por observación directa) | Negocio | [01](01-vision-negocio.md) |
| Equipo pequeño y de colaboración ocasional; el soporte crece con cada cliente nuevo | Operativo | [01](01-vision-negocio.md) |
| Variabilidad real entre los XML de distintos proveedores (cada uno con estructura distinta) | Técnico | [05](05-alcance-mvp-y-flujos.md) |
| Precisión en cálculos financieros: todo redondeo debe validarse **manualmente**, no solo con pruebas automáticas | Técnico crítico | [02](02-arquitectura.md), [03](03-modelo-datos.md) |
| Casos borde en sincronización offline → online (corte a mitad de una factura) | Técnico | [02](02-arquitectura.md) |
| Rendimiento de tablas con alto volumen de referencias en catálogos grandes | Técnico | [03](03-modelo-datos.md) |
| Posible resistencia al cambio de negocios acostumbrados al software actual | Negocio | [01](01-vision-negocio.md) |

## 3. Próximos pasos (roadmap inmediato)

1. ~~Montar **prototipos en Figma** de la primera iteración del MVP.~~ **Hecho y superado:** las pantallas se construyeron directamente en Vue; el alcance vigente es el de D-51 → ver [05](05-alcance-mvp-y-flujos.md), §2, y sistema de color en [09](09-diseno-ui-ux.md).
2. Definir el **esquema de datos definitivo** junto al arquitecto → ver [03](03-modelo-datos.md).
3. Obtener **2–3 XML reales** de proveedores locales para validar el parseo.
4. **Cerrar la decisión de stack de backend.** ⚠️ Ver contradicción en [07](07-decisiones-y-puntos-abiertos.md) *(el informe la enuncia como "Node.js vs. Java" pero §8.3 ya declara Python)*.
5. Definir la **política de resolución de conflictos** y la **ventana de gracia offline** → ver [02](02-arquitectura.md) y [04](04-seguridad.md).
6. **Cotizar el proveedor tercero** de facturación electrónica antes de fijar el precio final → ver [05](05-alcance-mvp-y-flujos.md).
7. Construir el **MVP de escritorio (Tauri + SQLite)** con los controles de seguridad descritos → ver [04](04-seguridad.md).

## 4. Módulos funcionales (roadmap de producto)

> **No confundir con las fases F1–F4** de [10 — Infraestructura de desarrollo y empaquetado](10-infraestructura-dev-y-empaquetado.md) §8, que son el roadmap de **integración técnica** (auth, wiring, integridad financiera, sync). Esto es el roadmap de **funcionalidad de negocio**: qué construye el usuario final, en qué orden. Ambos ejes se cruzan (ej. Módulo 2 depende de que F2 — validación financiera — esté avanzada), pero no son la misma lista.

- **Módulo 1 — Núcleo operativo (en curso):** Referencias (catálogo), Productos/Ítem (existencia real vinculada a una Referencia — ver [03](03-modelo-datos.md) §1.3) y Caja Registradora (venta rápida multi-línea, acumulación en tiempo real → `Bill`/`BillItem`). Es el ciclo diario del negocio. Incluye Category jerárquica + constructor libre + import/export + seeds por tipo de negocio (D-41 a D-44 en [07](07-decisiones-y-puntos-abiertos.md)) — no depende de DIAN, puede avanzar en paralelo.
- **Módulo 2 — Integración DIAN:** construir el flujo real de facturación electrónica ya decidido arquitectónicamente (D-09, D-38) — hoy solo está el diseño, falta la integración con el proveedor tercero (A-03).
- **Módulo 3 — Compatibilidad de producto (diferido, arranca después de un Módulo 2 sólido):** wizard de selección guiada por atributos técnicos (ej. "Moto → Aceites → Yamaha → Modelo → compatibles") para que un empleado sin experiencia venda con el conocimiento de un experto del sector. Registrado como punto abierto **A-22** en [07](07-decisiones-y-puntos-abiertos.md), con la secuencia acordada: arranca rígido y acotado a un solo vertical validado (repuestos de vehículo), se generaliza (JSON + wizard configurable) solo si 2+ verticales pagando lo piden. Se posiciona como feature de plan superior — a diferencia de Category (Módulo 1), que es libre en todos los planes (D-44).
