# GridBilling — API de facturación electrónica DIAN

Emite documentos DIAN e intégralos a tu POS o ERP. Facturación electrónica, nómina electrónica, eventos RADIAN, soporte adquisiciones, equivalente POS y notas de ajuste. Producto de GridSoft SAS.

[Documentación API](https://docs.gridbilling.gridsoft.co/) · [Ingresar](https://gridbilling.gridsoft.co/login)

[![GridBilling](https://gridbilling.gridsoft.co/img/logos/logo-gridbilling.png)](https://gridbilling.gridsoft.co/) [Documentos](https://gridbilling.gridsoft.co/#documentos) [API](https://gridbilling.gridsoft.co/#api) [Beneficios](https://gridbilling.gridsoft.co/#beneficios) [Cómo funciona](https://gridbilling.gridsoft.co/#como-funciona) [Docs](https://docs.gridbilling.gridsoft.co/)

[Ingresar](https://gridbilling.gridsoft.co/login) ☰

API de facturación electrónica DIAN

# Emite documentos DIAN e intégralos a tu software

GridBilling es la API de GridSoft SAS para facturación, nómina, RADIAN, adquisiciones, equivalente POS, notas de ajuste y RIPS salud. Rápida, clara y lista para tu POS o ERP.

[Empezar gratis](https://gridbilling.gridsoft.co/#empezar) [Ver documentación](https://docs.gridbilling.gridsoft.co/) [WhatsApp](https://wa.me/573134352726?text=Hola%20GridSoft%2C%20quiero%20informaci%C3%B3n%20sobre%20GridBilling%20(API%20de%20facturaci%C3%B3n%20electr%C3%B3nica%20DIAN).)

Integra desde JavaScript, PHP, Python, Java, C# y más.

![GridBilling](https://gridbilling.gridsoft.co/img/logos/logo-gridbilling-icon.png)

Todos los planes incluyen acceso a documentos DIAN

Documentos DIAN

## Factura electrónica por API, a tu medida

Un solo producto para emitir y controlar los documentos que tu operación necesita.

### Facturación Electrónica

Facturas válidas ante la DIAN con envío por email.

[Conocer más →](https://docs.gridbilling.gridsoft.co/)

### Nómina Electrónica

Nóminas de empleados según normativa DIAN.

[Conocer más →](https://docs.gridbilling.gridsoft.co/)

### Eventos RADIAN

Registro y reporte de eventos tributarios.

[Conocer más →](https://docs.gridbilling.gridsoft.co/)

### Soporte Adquisiciones

Registro de adquisiciones y facturación de compras.

[Conocer más →](https://docs.gridbilling.gridsoft.co/)

### Equivalente POS

Documentos equivalentes a tiquetes POS.

[Conocer más →](https://docs.gridbilling.gridsoft.co/)

### Notas de Ajuste

Corrección de facturas ya emitidas.

[Conocer más →](https://docs.gridbilling.gridsoft.co/)

### Factura sector salud

FE con health\_fields: usuarios, coberturas, MIPRES y copagos.

[Conocer más →](https://docs.gridbilling.gridsoft.co/)

### RIPS / Salud

Módulo SISPRO para IPS: pacientes, citas, consultas y envío RIPS.

[Conocer más →](https://docs.gridbilling.gridsoft.co/)

Integración API

## La API de facturación electrónica para tu software

Compatible con SaaS, ERP, PMS, CMS o POS. Tú envías el negocio en JSON; GridBilling arma el UBL 2.1, firma, transmite a la DIAN y te devuelve CUFE, PDF y estado.

### REST + JSON

Endpoints claros para emitir, consultar y rastrear documentos.

### Auth Bearer

Token por empresa. Sin sesiones complicadas en tu backend.

### UBL 2.1

Armamos y validamos el XML. Tú envías el negocio en JSON.

### Respuesta útil

CUFE/CUDE, PDF, XML y estado DIAN en la misma respuesta.

JavaScriptPHPPythonJavaC#GoRuby

Headers  Body JSON  Respuesta

POST/api/ubl2.1/invoice

|     |     |
| --- | --- |
| Method | POST |
| Content-Type | application/json |
| Authorization | Bearer <token\_de\_acceso> |
| Accept | application/json |

El token es el `api_token` de la empresa (tabla users / panel admin). Modo síncrono: `/api/ubl2.1/invoice`. Set de pruebas DIAN: `/api/ubl2.1/invoice/{testSetId}`.

### Ejemplo real: factura electrónica

Extraído de la colección Postman de GridBilling (una línea, IVA 19%, sin descuentos). Envías el JSON comercial; nosotros armamos UBL 2.1 y lo validamos ante la DIAN.

- `number / prefix / resolution_number` — Consecutivo y resolución DIAN de la empresa.
- `type_document_id: 1` — Factura de venta electrónica.
- `customer` — Adquiriente: NIT/CC, régimen, municipio y correo.
- `invoice_lines` — Ítems con cantidad, precio, IVA y descripción.
- `legal_monetary_totals` — Totales antes/después de impuesto y valor a pagar.
- `tax_totals` — Resumen de impuestos (ej. IVA 19%).

[Ver en documentación](https://docs.gridbilling.gridsoft.co/api/facturas/ejemplo-json/) [Descargar JSON](https://gridbilling.gridsoft.co/docs/examples/invoice-ubl21.example.json) [Descargar Postman](https://gridbilling.gridsoft.co/docs/GridBilling-API.postman_collection.json) [Hablar por WhatsApp](https://wa.me/573134352726?text=Hola%20GridSoft%2C%20necesito%20ayuda%20para%20integrar%20la%20API%20de%20GridBilling%20a%20mi%20software%20(POS%2FERP).)

Beneficios

## Por qué GridBilling

### Emisión rápida

Construcción, validación y transmisión de documentos electrónicos de forma segura.

### Normativa al día

Cumplimiento DIAN actualizado para facturación, nómina, RADIAN, soporte, POS y RIPS salud.

### Integración por API

Conecta tu POS, ERP o portal desde cualquier lenguaje con autenticación Bearer.

### Panel multi-empresa

Administra NITs, certificados, resoluciones y métricas desde un solo lugar.

Cómo funciona

## De tu sistema a la DIAN, paso a paso

No necesitas armar XML ni pelearte con firmas. Configuras una vez y tu software vende con normalidad.

01

### Crea tu cuenta

Ingresas al panel, registras la empresa emisora (NIT) y defines quién puede operar.

Aquí nace el acceso al admin y a la API.

02

### Configura DIAN

Cargas el certificado digital, la resolución de numeración y eliges ambiente (pruebas o producción).

Sin esto la DIAN no acepta documentos.

03

### Conecta tu software

Desde tu POS, ERP o backend llamas a la API con el token. Mandas JSON; nosotros armamos el UBL.

Un endpoint por tipo de documento.

04

### Emite y consulta

Recibes CUFE, PDF y estado. Puedes reenviar, consultar histórico y operar varios NITs.

Tu cliente vende; GridBilling habla con la DIAN.

### Flujo en producción

Tu POS / ERP

Envía la venta o nómina en JSON

→

GridBilling API

Valida, firma y transmite UBL 2.1

→

DIAN

Responde aceptación o rechazo

→

Tu sistema

Guarda CUFE, PDF y estado

En resumen: tu sistema manda el dato comercial → GridBilling lo convierte y lo valida ante la DIAN → te devolvemos el resultado listo para guardar o imprimir.

FAQ

## Preguntas frecuentes

¿Todos los planes incluyen documentos DIAN?−

Sí. Acceso a facturación, nómina, RADIAN, adquisiciones, equivalente POS, notas y módulo RIPS/salud según tu operación.

¿Puedo integrar GridBilling a mi POS o ERP?+

¿Quién desarrolla GridBilling?+

Empezar en 2 minutos

## Prueba gratis, paga solo cuando factures en serio

Primero integras en un ambiente de pruebas (Sandbox). Cuando tu software esté listo, compras documentos para producción.

1. 1

Crea tu cuenta

Te damos acceso al Sandbox gratis, sin límite de documentos de prueba.

2. 2

Integra tu software

Usa el token, Postman y la docs para emitir facturas de prueba DIAN.

3. 3

Pasa a producción

Cuando quieras facturar clientes reales, compras un paquete de documentos.


### Crear cuenta gratis

Solo necesitas nombre, correo y una contraseña. Te enviamos el acceso por email.

Tu nombre o empresaCorreoContraseña
Ver
Confirmar contraseña
Ver
Quiero mi acceso Sandbox

Al crear la cuenta aceptas recibir el token y las credenciales por correo.

### ¿Qué incluye el gratis?

- ✓ Ambiente Sandbox para integrar sin riesgo
- ✓ Documentos de prueba ilimitados
- ✓ Token de API y acceso al panel
- ✓ Misma API que usarás en producción

**Importante:** el Sandbox no sirve para facturar clientes reales. Eso se hace en producción, con un paquete de documentos.

### Comprar documentos

Solo en el panel de producción, menú **Cupo**.

Inicia sesión en producción y compra desde el panel: contador de documentos, planes Wompi e historial de pagos en un solo lugar.

[Entrar a producción →](https://api.gridbilling.gridsoft.co/login)

## ¿Listo para integrar facturación electrónica?

Crea tu cuenta gratis, prueba en Sandbox y compra cupo cuando pases a producción.

[Empezar gratis](https://gridbilling.gridsoft.co/#empezar) [Documentación API](https://docs.gridbilling.gridsoft.co/)

[![](https://gridbilling.gridsoft.co/img/logos/logo-gridbilling-icon.png)GridBilling](https://gridbilling.gridsoft.co/)

API de facturación electrónica DIAN · Un producto de GridSoft SAS.

[![GridSoft SAS](https://gridbilling.gridsoft.co/img/logos/logo-gridsoftsas.png)](https://www.gridsoft.co/)

[Documentos](https://gridbilling.gridsoft.co/#documentos) [API](https://gridbilling.gridsoft.co/#api) [Docs](https://docs.gridbilling.gridsoft.co/) [Admin](https://gridbilling.gridsoft.co/login) [WhatsApp](https://wa.me/573134352726?text=Hola%20GridSoft%2C%20tengo%20una%20duda%20sobre%20la%20documentaci%C3%B3n%20%2F%20ejemplos%20de%20la%20API%20GridBilling.)

© 2026 GridSoft SAS · GridBilling