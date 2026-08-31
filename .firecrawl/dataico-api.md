[Ir directamente al contenido](https://portaldelcliente.dataico.com/es/knowledge/documentaci%C3%B3n-t%C3%A9cnica-de-la-api-de-dataico-factura-electr%C3%B3nica#main-content)

EspañolTraducciones de Mostrar submenú de

[Iniciar sesión](https://portaldelcliente.dataico.com/_hcms/mem/login?redirect_url=https%3A%2F%2Fportaldelcliente.dataico.com%2Fes%2Fknowledge%2Fdocumentaci%25C3%25B3n-t%25C3%25A9cnica-de-la-api-de-dataico-factura-electr%25C3%25B3nica)

![facturaelectronica.dataico.comhs-fshubfslogoDataico2-1.png]](https://portaldelcliente.dataico.com/hs-fs/hubfs/social-suggested-images/facturaelectronica.dataico.comhs-fshubfslogoDataico2-1.png?height=40&name=facturaelectronica.dataico.comhs-fshubfslogoDataico2-1.png)

Abrir navegación principalCerrar navegación principal

- EspañolTraducciones de Mostrar submenú de

- [Iniciar sesión](https://portaldelcliente.dataico.com/_hcms/mem/login?redirect_url=https%3A%2F%2Fportaldelcliente.dataico.com%2Fes%2Fknowledge%2Fdocumentaci%25C3%25B3n-t%25C3%25A9cnica-de-la-api-de-dataico-factura-electr%25C3%25B3nica)

¿Cómo podemos ayudarte?


- No hay sugerencias porque el campo de búsqueda está vacío.

1. [Centro de Ayuda](https://portaldelcliente.dataico.com/es/knowledge?hsLang=es)
2. [Integración API DATAICO S.A.S](https://portaldelcliente.dataico.com/es/knowledge/integraci%C3%B3n-api-dataico-s-a-s?hsLang=es)
3. [Factura Electrónica.](https://portaldelcliente.dataico.com/es/knowledge/integraci%C3%B3n-api-dataico-s-a-s?hsLang=es#factura-electr%C3%B3nica)

# Documentación Técnica de la API de Dataico - Factura Electrónica

[Documentación: API DOCS Documentación Técnica de FE](https://app.dataico.com/api-docs)

* * *

**Autentificación**

Para la transmisión de FE, la API utiliza como método de autenticación los parámetros "Dataico\_account\_id" y "Auth-token". Para obtener estos datos de autenticación, sigue estos pasos:

**Haz clic en las opciones en la parte superior / selecciona "Configuración".**

![](https://portaldelcliente.dataico.com/hs-fs/hubfs/image-png-May-24-2024-06-56-59-5742-PM.png?width=670&height=316&name=image-png-May-24-2024-06-56-59-5742-PM.png)

![](https://portaldelcliente.dataico.com/hs-fs/hubfs/image-png-May-24-2024-06-58-26-4761-PM.png?width=670&height=316&name=image-png-May-24-2024-06-58-26-4761-PM.png)

* * *

**Numeración**

Para obtener los datos de autorización de tu numeración o consecutivo de facturación electrónica, sigue estos pasos:

**Ventas / Facturas > Numeraciones > \[Editar\]**

**![](https://portaldelcliente.dataico.com/hs-fs/hubfs/image-png-May-24-2024-06-59-13-7398-PM.png?width=670&height=214&name=image-png-May-24-2024-06-59-13-7398-PM.png)**

**![](https://portaldelcliente.dataico.com/hs-fs/hubfs/image-png-May-24-2024-06-59-32-8367-PM.png?width=670&height=203&name=image-png-May-24-2024-06-59-32-8367-PM.png)**

**![](https://portaldelcliente.dataico.com/hs-fs/hubfs/image-png-May-24-2024-07-00-25-6416-PM.png?width=670&height=304&name=image-png-May-24-2024-07-00-25-6416-PM.png)**

* * *

**Crear factura electrónica**

**Método**: POST

**Endpoints (URL):** https://api.dataico.com/direct/dataico\_api/v2/invoices

**Headers**

- Content-type : application/json
- Auth-token (Cuenta DATAICO)

**Ejemplo configuración en Postman**

![](https://portaldelcliente.dataico.com/hs-fs/hubfs/1-png-May-24-2024-07-01-16-4093-PM.png?width=636&height=275&name=1-png-May-24-2024-07-01-16-4093-PM.png)

**Estructura JSON estándar**

- [FE estructura básica](https://drive.google.com/file/d/1_xUiBtth2Y-5p5ZxqzKE5cB_o47hn_Wd/view?usp=sharing)
- [FE Consumidor final](https://drive.google.com/file/d/1z3m6toTmlmEJ_ToTaICfu52Ik8X3hz3M/view?usp=sharing)
- [FE IMP IVA %](https://drive.google.com/file/d/1OOVfkqYdRwPHYTINs2JmCjIlqEgvwQBH/view?usp=sharing)
- [FE IMP Bolsa plástica $](https://drive.google.com/file/d/1mHg0xA89l4BTcvMp92KwIaJjZAueDYYa/view?usp=sharing)
- [FE IMP Consumo %](https://drive.google.com/file/d/1c6ssYAgNVwawWmObPFvfQey8d0Gv9dt8/view?usp=sharing)
- [IMP\_CONSUMO\_LICOR $](https://drive.google.com/file/d/10k7y_Oja_qmG7MWyCWUXRE_1JHle5ls6/view?usp=sharing)
- [FE ICUI % - IBUA $](https://drive.google.com/file/d/1rS532xX3tZSDPgDkVtCQcGfRLpE-HKAH/view?usp=sharing)
- [FE RET\_FUENTE % - RET\_ICA %](https://drive.google.com/file/d/1lZIgHxU83hi-WQmM39ukCxfloW0ZWHxd/view?usp=sharing)
- [FE Descuentos (Ítems %, Global $)](https://drive.google.com/file/d/10UWCQV2zIpsEpJUJiu4rMCDKUdxvgVCl/view?usp=sharing)
- [FE Propina $](https://drive.google.com/file/d/1ZzRmKM58tSAtiKeo-DUvFAABH0QZhJ1K/view?usp=sharing)
- [FE Obsequio $](https://drive.google.com/file/d/1p0SCG0G6Tz-rMGC_osnOSeylv-DSnevV/view?usp=sharing)
- [FE Anticipo $](https://drive.google.com/file/d/1Ps4FbqPYFlm8ZGwnEy5wIX4e_xpePLcn/view?usp=sharing)
- [FE Mandato $](https://drive.google.com/file/d/12StKybO04g2zt0CtsU4oIrRZ_wLgedIt/view?usp=sharing)
- [FE Exportación US $](https://drive.google.com/file/d/13-GraCkenDEJ19NCJDAxrRVuEw1OBtmh/view?usp=sharing)
- [FE AIU (IVA)](https://drive.google.com/file/d/1TKttnL4yJ69CW4EBEqCAGxjONJAf886b/view?usp=sharing)
- [FE AIU (Sin IVA)](https://drive.google.com/file/d/1oPa9h_drqRe9-OqhDJI11xO4u8nfGeBB/view?usp=sharing)

* * *

**Recursos Adicionales**

+  [Código ciudades y departamentos de Colombia](https://docs.google.com/spreadsheets/d/1IW1Qh_toHykKFa-89V8haU8G5rrMTqux/edit?usp=sharing&ouid=117003031119157397152&rtpof=true&sd=true)

\+  [Código países](https://www.dian.gov.co/atencionciudadano/formulariosinstructivos/Formularios/2012/paises_2012.pdf)

\+  [Código unidades de medidas](https://docs.google.com/spreadsheets/d/1I41mDYG6BluRD2jdlgOJ6aRwGkHe5eEe/edit?usp=sharing&ouid=117003031119157397152&rtpof=true&sd=true)

\+  [Guía de Solución de Problemas API DATAICO FACTURA ELECTRÓNICA](https://portaldelcliente.dataico.com/es/knowledge/gu%C3%ADa-de-soluci%C3%B3n-de-problemas-api-dataico-factura-electr%C3%B3nica?hsLang=es)

\+  [Consultar factura](https://portaldelcliente.dataico.com/es/knowledge/documentaci%C3%B3n-t%C3%A9cnica-de-la-api-de-dataico-factura-electr%C3%B3nica-1?hsLang=es)

+  [Reenviar factura](https://portaldelcliente.dataico.com/es/knowledge/reenviar-a-la-dian-una-factura-existente-de-la-cuenta-dataico-con-el-estado-dian_no_enviado?hsLang=es)

+  [Enviar factura al cliente con una representación gráfica personalizada.](https://portaldelcliente.dataico.com/es/knowledge/reenviar-a-la-dian-una-factura-existente-de-la-cuenta-dataico-con-el-estado-dian_no_enviado?hsLang=es)

+  [Crear nota crédito](https://portaldelcliente.dataico.com/es/knowledge/crear-nota-cr%C3%A9dito?hsLang=es)

+  [Crear nota debito](https://portaldelcliente.dataico.com/es/knowledge/crear-nota-d%C3%A9bito?hsLang=es)

**Contacto**

Si después de seguir estos pasos tienes alguna duda o encuentras algún problema, no dudes en ponerte en contacto con nuestro equipo de soporte a través de nuestro **[Chat](https://app.dataico.com/) 💬.**

¿Te resultó útil este artículo?

SíNo

- [ ]
[Módulo de Terceros](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-terceros?hsLang=es#main-content)




  - [Conceptos](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-terceros?hsLang=es#conceptos)
- [ ]
[Módulo de Ventas](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-ventas?hsLang=es#main-content)




  - [Onboarding Facturación](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-ventas?hsLang=es#onboarding-facturaci%C3%B3n)
  - [Generales](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-ventas?hsLang=es#generales)
  - [Facturas](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-ventas?hsLang=es#facturas)
  - [Cotizaciones](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-ventas?hsLang=es#cotizaciones)
  - [Notas crédito](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-ventas?hsLang=es#notas-cr%C3%A9dito)
  - [Notas débito](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-ventas?hsLang=es#notas-d%C3%A9bito)
  - [Facturación electrónica](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-ventas?hsLang=es#facturaci%C3%B3n-electr%C3%B3nica)
  - [Onboarding POS Electrónico](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-ventas?hsLang=es#onboarding-pos-electr%C3%B3nico)
  - [Generalidades de Documento Equivalente POS Electrónico](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-ventas?hsLang=es#generalidades-de-documento-equivalente-pos-electr%C3%B3nico)
  - [Notas de Ajuste POS Electrónico](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-ventas?hsLang=es#notas-de-ajuste-pos-electr%C3%B3nico)
- [ ]
[Módulo de Contabilidad](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-contabilidad?hsLang=es#main-content)




  - [Onboarding y conceptos](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-contabilidad?hsLang=es#onboarding-y-conceptos)
  - [Configuración del módulo contable](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-contabilidad?hsLang=es#configuraci%C3%B3n-del-m%C3%B3dulo-contable)
  - [Reglas y automatización](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-contabilidad?hsLang=es#reglas-y-automatizaci%C3%B3n)
  - [Asientos y comprobantes](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-contabilidad?hsLang=es#asientos-y-comprobantes)
  - [Reportes financieros](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-contabilidad?hsLang=es#reportes-financieros)
  - [Certificados y exógena](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-contabilidad?hsLang=es#certificados-y-ex%C3%B3gena)
- [ ]
[Módulo de Nómina](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-n%C3%B3mina?hsLang=es#main-content)




  - [Onboarding y conceptos](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-n%C3%B3mina?hsLang=es#onboarding-y-conceptos)
  - [Configuración de Nómina](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-n%C3%B3mina?hsLang=es#configuraci%C3%B3n-de-n%C3%B3mina)
  - [Empleados, contratos y terminaciones](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-n%C3%B3mina?hsLang=es#empleados-contratos-y-terminaciones)
  - [Novedades y horas extras](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-n%C3%B3mina?hsLang=es#novedades-y-horas-extras)
  - [Liquidación de Nómina](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-n%C3%B3mina?hsLang=es#liquidaci%C3%B3n-de-n%C3%B3mina)
  - [Prestaciones Sociales](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-n%C3%B3mina?hsLang=es#prestaciones-sociales)
  - [Colillas de Pago](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-n%C3%B3mina?hsLang=es#colillas-de-pago)
  - [Nómina Electrónica](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-n%C3%B3mina?hsLang=es#n%C3%B3mina-electr%C3%B3nica)
- [ ]
[Módulo de Compras](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-compras?hsLang=es#main-content)




  - [Compras](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-compras?hsLang=es#compras)
  - [Documento Soporte](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-compras?hsLang=es#documento-soporte)
  - [Habilitar Documento Soporte](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-compras?hsLang=es#habilitar-documento-soporte)
  - [Eventos de Recepción](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-compras?hsLang=es#eventos-de-recepci%C3%B3n)
  - [Errores, notificaciones y rechazos de Eventos de Recepción](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-compras?hsLang=es#errores-notificaciones-y-rechazos-de-eventos-de-recepci%C3%B3n)
  - [Facturas Electrónicas de Compra](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-compras?hsLang=es#facturas-electr%C3%B3nicas-de-compra)
- [ ]
[Módulo de Cartera](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-cartera?hsLang=es#main-content)




  - [Onboarding](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-cartera?hsLang=es#onboarding)
  - [Cuentas por Cobrar y cuentas por Pagar](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-cartera?hsLang=es#cuentas-por-cobrar-y-cuentas-por-pagar)
  - [Bancos.](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-cartera?hsLang=es#bancos)
  - [Configuración Módulo de Cartera](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-cartera?hsLang=es#configuraci%C3%B3n-m%C3%B3dulo-de-cartera)
- [ ]
[Módulo de Productos e Inventarios](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-productos-e-inventarios?hsLang=es#main-content)




  - [Productos](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-productos-e-inventarios?hsLang=es#productos)
  - [Inventarios.](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-productos-e-inventarios?hsLang=es#inventarios)
  - [Ajuste de inventarios.](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-productos-e-inventarios?hsLang=es#ajuste-de-inventarios)
  - [Productos de compra.](https://portaldelcliente.dataico.com/es/knowledge/m%C3%B3dulo-de-productos-e-inventarios?hsLang=es#productos-de-compra)
- [Suscripciones](https://portaldelcliente.dataico.com/es/knowledge/suscripciones?hsLang=es)
- [x]
[Integración API DATAICO S.A.S](https://portaldelcliente.dataico.com/es/knowledge/integraci%C3%B3n-api-dataico-s-a-s?hsLang=es#main-content)




  - [Modelo de Integración API DATAICO S.A.S](https://portaldelcliente.dataico.com/es/knowledge/integraci%C3%B3n-api-dataico-s-a-s?hsLang=es#modelo-de-integraci%C3%B3n-api-dataico-s-a-s)
  - [Factura Electrónica.](https://portaldelcliente.dataico.com/es/knowledge/integraci%C3%B3n-api-dataico-s-a-s?hsLang=es#factura-electr%C3%B3nica)
  - [Guía de Solución de Problemas API DATAICO FE](https://portaldelcliente.dataico.com/es/knowledge/integraci%C3%B3n-api-dataico-s-a-s?hsLang=es#gu%C3%ADa-de-soluci%C3%B3n-de-problemas-api-dataico-fe)
  - [Nómina Electrónica.](https://portaldelcliente.dataico.com/es/knowledge/integraci%C3%B3n-api-dataico-s-a-s?hsLang=es#n%C3%B3mina-electr%C3%B3nica)
  - [Documento Soporte (DS)](https://portaldelcliente.dataico.com/es/knowledge/integraci%C3%B3n-api-dataico-s-a-s?hsLang=es#documento-soporte-ds)
  - [Eventos de Recepción (EV)](https://portaldelcliente.dataico.com/es/knowledge/integraci%C3%B3n-api-dataico-s-a-s?hsLang=es#eventos-de-recepci%C3%B3n-ev)
  - [Sector Salud](https://portaldelcliente.dataico.com/es/knowledge/integraci%C3%B3n-api-dataico-s-a-s?hsLang=es#sector-salud)
  - [POS ELECTRÓNICO](https://portaldelcliente.dataico.com/es/knowledge/integraci%C3%B3n-api-dataico-s-a-s?hsLang=es#pos-electr%C3%B3nico)
- [ ]
[Importaciones](https://portaldelcliente.dataico.com/es/knowledge/importaciones?hsLang=es#main-content)




  - [General](https://portaldelcliente.dataico.com/es/knowledge/importaciones?hsLang=es#general)
  - [Contabilidad](https://portaldelcliente.dataico.com/es/knowledge/importaciones?hsLang=es#contabilidad)
  - [Productos](https://portaldelcliente.dataico.com/es/knowledge/importaciones?hsLang=es#productos)
- [Preguntas frecuentes (FAQ)](https://portaldelcliente.dataico.com/es/knowledge/preguntas-frecuentes-faq?hsLang=es)
- [ ]
[Anexos Técnicos y Resoluciones](https://portaldelcliente.dataico.com/es/knowledge/anexos-t%C3%A9cnicos-y-resoluciones?hsLang=es#main-content)




  - [Resolución 000119 de 2024.](https://portaldelcliente.dataico.com/es/knowledge/anexos-t%C3%A9cnicos-y-resoluciones?hsLang=es#resoluci%C3%B3n-000119-de-2024)
  - [Anexo 1.9](https://portaldelcliente.dataico.com/es/knowledge/anexos-t%C3%A9cnicos-y-resoluciones?hsLang=es#anexo-1-9)
- [Recursos adicionales](https://portaldelcliente.dataico.com/es/knowledge/recursos-adicionales?hsLang=es)
- [Shopify](https://portaldelcliente.dataico.com/es/knowledge/shopify?hsLang=es)

[![Chill listening crop-3](https://portaldelcliente.dataico.com/hs-fs/hubfs/Lod%20DT.png?width=110&height=32&name=Lod%20DT.png)](https://www.dataico.com/)

Copyright © 2026, DATAICO S.A.S