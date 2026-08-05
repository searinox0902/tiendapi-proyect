# 01 — Visión de Negocio

> **Contexto:** Por qué existe el producto, a quién sirve, cómo compite y cómo genera ingresos. Cárgalo para decisiones de pricing, posicionamiento y priorización por valor.

## 1. Resumen ejecutivo

Emprendimiento de pequeña escala (proyecto paralelo) que ofrece **software de gestión comercial** —referencias, inventario y facturación— a **pequeños y medianos negocios locales de Medellín y su región**.

Posicionamiento: **cercanía y especialización por sector**, trato directo y crecimiento por recomendación entre negocios, frente a plataformas grandes percibidas como genéricas.

## 2. Problema a resolver

Los negocios locales usan software con fallas claras de usabilidad y de datos:

- Interfaces anticuadas y poco intuitivas; exceso de pantallas y clics para tareas simples.
- Falta de cálculos automáticos que agilicen la facturación diaria.
- Errores en el reconocimiento de referencias de producto.
- Lectura defectuosa de XML de proveedores → trabajo manual evitable.
- Software local sin respaldo: una falla del equipo detiene la venta del día.
- Soporte técnico lento, que no resuelve problemas reales.

**Meta de simplificación:** tareas que hoy toman muchas pantallas y clics pueden reducirse hasta en **~90%**.

## 3. Mercado objetivo y posicionamiento

- **Pequeños negocios (10–50 empleados):** distribuidoras, ferreterías, restaurantes, farmacias.
- **Negocios medianos (50–200 empleados):** incluyendo operación **multi-sucursal**.
- **Alcance inicial:** local (Medellín y alrededores), con expansión orgánica vía recomendación.

Particularidad del segmento: valoran que la solución venga **recomendada por otro negocio similar** y prefieren un proveedor que **adapte el sistema a su forma de trabajar** en vez de una plataforma genérica.

## 4. Competencia y precios de referencia (Colombia, 2026)

| Módulo | Alegra | Siigo |
|--------|--------|-------|
| Facturación electrónica | $17.900 – $179.900 COP/mes según ingresos | Precio bajo consulta; no público |
| Contabilidad | $219.900 – $279.900 COP/mes | Bajo consulta; ciclo anual obligatorio |
| Nómina electrónica | $29.900 – $259.000 COP/mes según empleados | Módulo adicional separado |
| POS | $25.900 – $199.900 COP/mes | Módulo adicional, precio bajo consulta |
| Modalidad de contrato | Mensual, sin permanencia | Anual, compromiso desde el inicio |

**Referencia de costo combinado:** una pyme con POS y ~5 empleados que necesite facturación + POS + nómina puede superar los **$3,2 – 4 millones COP/año** combinando módulos.

**Lectura estratégica:** Alegra y Siigo son robustos pero **genéricos** y exigen que el cliente se adapte a su lógica. La oportunidad propia es **especialización por tipo de negocio**, trato cercano, precio competitivo y onboarding personalizado.

## 5. Propuesta de valor

- Tecnología moderna (escritorio instalable), **accesible y liviana** incluso en equipos antiguos.
- Interfaz simplificada: menos pantallas, menos clics, **autocompletado de referencias**.
- **Lectura automática y confiable de XML** de proveedores.
- **Funcionamiento offline:** el negocio sigue facturando aunque se corte internet o falle un equipo.
- Soporte directo y cercano (no call center), con relación de confianza.
- **Especialización por sector**, ajustando el sistema al lenguaje y proceso real del negocio.

## 6. Modelo de negocio y proyección

- **Suscripción mensual por cliente:** $200.000 – $300.000 COP.
- **Aislamiento por cliente:** cada cliente con acceso propio e independiente (no multi-tenant compartido visible entre clientes). Ver implicaciones en [02 — Arquitectura](02-arquitectura.md) y [04 — Seguridad](04-seguridad.md).
- **Facturación electrónica DIAN** delegada a un proveedor tercero autorizado (ver [05 — Alcance MVP y flujos](05-alcance-mvp-y-flujos.md)).
- **Adquisición de clientes:** recomendación directa entre negocios del mismo sector o zona.

| N.º de clientes | Ingreso mensual aprox. | Lectura |
|-----------------|------------------------|---------|
| 10 clientes | $2.000.000 – $3.000.000 COP | Viable como proyecto paralelo |
| 20 clientes | $4.000.000 – $6.000.000 COP | Viable como ingreso principal |
| 30+ clientes | $6.000.000 – $9.000.000 COP | Requiere soporte/estructura adicional |
