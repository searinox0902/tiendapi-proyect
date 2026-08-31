[![API DIAN facturación electrónica Colombia | Facturalatam](https://facturalatam.com/api/images/latam.jpg)](https://facturalatam.com/api/index.html)

- [Cómo funciona](https://facturalatam.com/api/#como-funciona)
- [Funciones](https://facturalatam.com/api/#funciones)
- [Documentación](https://facturalatam.com/api/#documentacion)
- [Integrar](https://facturalatam.com/api/#integrar)
- [Instalar](https://facturalatam.com/api/#instalar)
- [Revender](https://facturalatam.com/api/#revender)
- [Documentación](https://documenter.getpostman.com/view/1431398/2sAY4uCido)

PARA DESARROLLADORES

# Integra la facturación electrónica DIAN en tu software

Emite facturas, nómina electrónica, documento soporte, POS electrónico y eventos RADIAN mediante API REST. Úsala en nuestros servidores o instálala con código fuente en tu propia infraestructura.


- [Probar la API](https://facturalatam.com/api/#prueba)
- [Ver documentación](https://documenter.getpostman.com/view/1431398/2sAY4uCido)

- +10.000 empresas
- 99,9 % de disponibilidad
- Código fuente disponible

**POST** api.facturapro.co/api/ubl2.1/invoice Copiar


Solicitud

```
curl --request POST \
  --url https://api.facturapro.co/api/ubl2.1/invoice \
  --header "Authorization: Bearer API_KEY" \
  --header "Content-Type: application/json" \
  --data @factura.json
```

Respuesta 200 OK

```
{
  "success": true,
  "message": "Procesado correctamente",
  "cufe": "872e9199c2f0a1...",
  "urlinvoicexml": "https://.../FES-990.xml",
  "urlinvoicepdf": "https://.../FES-990.pdf"
}
```

## ¿Cómo quieres utilizar la API?

Tres modelos distintos, con precios y condiciones distintas. Elige el tuyo y ve directo a lo que necesitas.

[**Integrarla en mi software** \\
Quiero conectar mi ERP, aplicación o plataforma mediante API REST, sobre la infraestructura de Facturalatam.\\
Probar la API](https://facturalatam.com/api/#integrar) [**Instalarla en mi servidor** \\
Quiero el código fuente y controlar directamente la infraestructura y los datos de mis clientes.\\
Ver licencias](https://facturalatam.com/api/#instalar) [**Revenderla con mi marca** \\
Quiero gestionar múltiples empresas desde una plataforma marca blanca y definir mis propios precios.\\
Ver planes de reventa](https://facturalatam.com/api/#revender)

CÓMO FUNCIONA

## Integra la API en tres pasos

1

Paso 1

### Configura la empresa

Registra el [certificado digital](https://facturalatam.com/api/#certificados), el software y la resolución autorizada por la DIAN.

certificado + resolución

2

Paso 2

### Envía el documento

Realiza una solicitud JSON desde tu ERP, ecommerce o aplicación.

POST /api/ubl2.1/invoice

3

Paso 3

### Recibe la validación

Obtén la respuesta de la DIAN, el CUFE, el XML y el PDF en una sola operación.

200 OK · cufe · xml · pdf

REQUISITO PREVIO

## Cada empresa necesita su propio certificado digital

Trabajamos bajo la modalidad de **software propio ante la DIAN**: cada empresa queda habilitada con su propio software y su propia resolución de numeración. Por eso el certificado digital es individual y no se comparte entre empresas.

- **Un certificado digital por empresa, sin excepción.** Es el que firma cada documento que envías a la DIAN.
- Aplica igual en las tres modalidades: API en nuestra nube, licencia instalada en tu servidor y planes de reventa.
- Si administras varias empresas como revendedor o distribuidor, necesitas un certificado por cada una de ellas.

Precio promocional

### Certificado digital DIAN

$99.900 COP

Vigencia 1 año

Mejor valor

$179.000 COP

Vigencia 2 años

- Excluido de IVA
- Emisión en hasta 1 día hábil tras validar la documentación
- Requisitos: RUT, cédula del representante legal y Cámara de Comercio con menos de 30 días para personas jurídicas

[Comprar certificado](https://facturalatam.com/certificados-digitales/)

Trámite de lunes a viernes, 9:00 a. m. a 6:00 p. m.

INTEGRACIONES

## Conéctala con las plataformas que ya usas

Miles de empresas en Colombia ya facturan a la DIAN a través de nuestra API, con integraciones listas para los principales sistemas del mercado.

+500Desarrolladores integrados

+10.000Empresas facturando

99.9%Disponibilidad de la API

24/7Emisión a la DIAN

[![Integración de facturación electrónica DIAN con Odoo](https://facturalatam.com/api/images/brands/a1.png)](https://facturalatam.com/odoo/)[![Integración de facturación electrónica DIAN con Dolibarr](https://facturalatam.com/api/images/brands/a2.jpeg)](https://gitlab.buho.la/free/dolibarr-electronic-invoice)[![Integración de facturación electrónica DIAN con WordPress](https://facturalatam.com/api/images/brands/3.png)](https://gitlab.com/carlomagno83/co-wordpress-2023)

FUNCIONES

## Todo lo que puedes emitir con la API

Los documentos electrónicos que emites ante la DIAN y, aparte, las capacidades técnicas con las que la API los genera y entrega.

### Documentos electrónicos

Factura electrónica de venta Notas crédito y débito Documento soporte Nómina electrónica POS electrónico Documentos equivalentes Servicios públicos Transporte Sector salud Eventos RADIAN

### Capacidades técnicas

Generación de XML UBL 2.1 Generación de PDF Firma digital CUFE y QR Envío por correo Validación DIAN Webhooks Procesamiento por lotes Almacenamiento externo

[Ver todos los endpoints](https://documenter.getpostman.com/view/1431398/2sAY4uCido#9cbfa4de-b8c6-4109-9d13-3523b7cf2037)

Camino 1 · Integrarla en mi software

## Conecta tu ERP o aplicación por API REST

Envías un JSON, nosotros generamos el XML UBL 2.1, lo firmamos y lo validamos ante la DIAN. Recibes el CUFE, el XML y el PDF en la misma respuesta. Sin infraestructura que mantener.

![Resultado en el panel de la API DIAN de facturación electrónica](https://facturalatam.com/api/images/panel2.png)![Request POST al endpoint de la API DIAN con el JSON del documento](https://facturalatam.com/api/images/insomnia.png)

api.facturapro.co

Arrastra para comparar: la petición que envías y el documento validado en el panel.

Panel demo En vivo

URL [api.facturapro.co](https://api.facturapro.co/)

Correoadmin@gmail.com

ContraseñaUVjo1wvfHG

[Entrar al panel demo](https://api.facturapro.co/)

[Ver documentación de la API](https://documenter.getpostman.com/view/1431398/2sAY4uCido) [Hablar con un desarrollador](https://wa.me/51930973902?text=Deseo%20integrar%20la%20API%20DIAN%20en%20mi%20software)

DOCUMENTACIÓN

## Dos documentos, dos propósitos

Uno te lleva del certificado a producción. El otro te dice exactamente qué enviar en cada endpoint.

[**Guía de inicio** \\
Instalación, configuración, habilitación ante la DIAN y paso a producción. Es la ruta que sigues una vez, en orden, hasta emitir tu primer documento real.\\
Abrir la guía](https://manual.facturalatam.com/apidian/instalacion) [**Referencia de la API** \\
Endpoints, parámetros, ejemplos de JSON y respuestas. Es lo que consultas a diario mientras programas, para saber qué campos lleva cada documento.\\
Abrir la referencia](https://documenter.getpostman.com/view/1431398/2sAY4uCido)

PRECIOS

## Primero elige quién administra la infraestructura

Esa decisión define qué planes te aplican. Elige una de las dos y te llevamos directo a sus precios.

[**Servidor propio Tú administras el servidor**\\
\\
- Recibes el código fuente y lo instalas en tu infraestructura\\
- Pago único de la licencia, sin mensualidad\\
- Mayor control técnico sobre servidor y datos\\
\\
Planes disponibles: **Community** y **Enterprise**\\
Ver licencias](https://facturalatam.com/api/#planes) [**Cloud Facturalatam Nosotros administramos la infraestructura**\\
\\
- Sin servidores que mantener ni actualizar\\
- Servicio mensual según la cantidad de empresas\\
- Menor complejidad operativa para empezar\\
\\
Planes disponibles: **Revendedor**, **Distribuidor**, **Socio** y **Mayorista**\\
Ver planes cloud](https://facturalatam.com/api/#revender)

Camino 2 · Instalarla en mi servidor

## Licencia para tu propia infraestructura

Código fuente completo: tú controlas el servidor, los datos y las actualizaciones. Pago único y licencia perpetua, sin mensualidad. Recuerda que cada empresa necesita [**su propio certificado digital**](https://facturalatam.com/api/#certificados).

Community · Código abierto

Gratis

Código abierto, para siempre

Los documentos base de la DIAN con el código fuente público en GitHub. Tú instalas, tú mantienes y la comunidad te acompaña.

[Ver la comparativa completa](https://facturalatam.com/api/#comparativa) [Descargar Community](https://github.com/facturalatam/apidian)

Recomendado

Enterprise

USD 200 / pago único

Licencia perpetua para tu servidor · incluye el primer año de soporte y actualizaciones

Todos los documentos DIAN, instalación asistida en tu servidor y marca blanca para revenderla. El pago incluye **1 año de soporte técnico y actualizaciones normativas DIAN**.

Renovación opcional: **USD 100/año**. Si no renuevas, la API sigue funcionando en tu infraestructura, solo deja de recibir actualizaciones.

[Ver la comparativa completa](https://facturalatam.com/api/#comparativa) [Obtener Enterprise](https://facturalatam.com/pagos.php?mount=200)

[Manual de instalación](https://manual.facturalatam.com/apidian/instalacion)

Comparativa

### Community vs Enterprise, línea por línea

Una sola tabla, sin letra pequeña. Cada fila enlaza a la fuente donde puedes comprobarla por tu cuenta: el repositorio público, la documentación de la API, el panel demo o el manual de instalación.

| Capacidad | Community Gratis | Enterprise USD 200 · pago único | Cómo verificarlo |
| --- | --- | --- | --- |
| Documentos electrónicos |
| Factura de venta | Incluido | Incluido | [Endpoint](https://documenter.getpostman.com/view/1431398/2sAY4uCido) |
| Notas crédito y débito | Incluido | Incluido | [Endpoint](https://documenter.getpostman.com/view/1431398/2sAY4uCido) |
| Documento soporte y notas de ajuste | Incluido | Incluido | [Endpoint](https://documenter.getpostman.com/view/1431398/2sAY4uCido) |
| Eventos RADIAN | Incluido | Incluido | [Endpoint](https://documenter.getpostman.com/view/1431398/2sAY4uCido) |
| Nómina electrónica | No incluido | Incluido | [Endpoint](https://documenter.getpostman.com/view/1431398/2sAY4uCido) |
| POS electrónico y documentos equivalentes | No incluido | Incluido | [Endpoint](https://documenter.getpostman.com/view/1431398/2sAY4uCido) |
| RIPS y Sector Salud | No incluido | Incluido | [Endpoint](https://documenter.getpostman.com/view/1431398/2sAY4uCido) |
| Facturación AIU | No incluido | Incluido | [Endpoint](https://documenter.getpostman.com/view/1431398/2sAY4uCido) |
| Extracción de facturas de compras | No incluido | Incluido | [Panel demo](https://api.facturapro.co/) |
| Entrega, soporte y licencia |
| Código fuente completo | Público en GitHub | Incluido con la licencia |  |
| Instalación en tu servidor | Por tu cuenta | Asistida por el equipo |  |
| Actualizaciones normativas DIAN | Vía comunidad | Incluidas el primer año |  |
| Soporte técnico dedicado | Comunidad | 1 año por Slack y WhatsApp |  |
| La API sigue funcionando sin renovar | Sí | Sí |  |
| Marca blanca para revender | No incluido | Incluido |  |
| Precio de la licencia | Gratis, para siempre | **USD 200** · pago único<br>incluye el primer año de soporte y actualizaciones |  |
| Renovación a partir del segundo año | No aplica | **USD 100/año** · opcional<br>solo para seguir recibiendo soporte y actualizaciones |  |

Comparación de capacidades entre las licencias Community y Enterprise de la API DIAN

Ambas licencias corren en tu propia infraestructura: tú controlas el servidor y los datos. Community es de código abierto y se mantiene con la comunidad. Enterprise añade el resto de documentos DIAN, la instalación asistida, el soporte y las actualizaciones normativas durante el primer año. **La licencia Enterprise es perpetua:** a partir del segundo año la renovación de USD 100/año es opcional y solo cubre soporte y actualizaciones; si decides no renovarla, tu API sigue funcionando con normalidad en tu servidor, únicamente deja de recibir las actualizaciones normativas de la DIAN.

Camino 3 · Revenderla con mi marca

## Planes para revendedores y distribuidores

Gestiona múltiples empresas desde un solo panel con **marca blanca**, sobre nuestra infraestructura. El precio va por la cantidad de empresas que administras: a más empresas, menor costo por empresa. Tú defines el precio de venta a tus clientes.

Revendedor

$99.900 COP/mes

Hasta 10 empresas

≈ $9.990 por empresa/mes

Hasta **5.000** documentos/mes emitidos

15 días de prueba gratis · sin tarjeta

- Panel multiempresa con marca blanca
- Todos los documentos DIAN
- Tú defines el precio a tus clientes

Probar gratis con Google


Distribuidor

$349.900 COP/mes

Hasta 50 empresas

≈ $7.000 por empresa/mes

Hasta **30.000** documentos/mes emitidos

- Todo lo del plan Revendedor
- Nómina y documentos equivalentes
- Soporte prioritario para tus clientes

[Empezar](https://wa.me/51930973902?text=Deseo%20el%20plan%20Distribuidor%20(hasta%2050%20empresas))

Más popularSocio

$999.900 COP/mes

Hasta 200 empresas

≈ $5.000 por empresa/mes

Hasta **150.000** documentos/mes emitidos

- API keys y subdominio por empresa
- Onboarding y capacitación
- Gestor de cuenta dedicado

[Empezar](https://wa.me/51930973902?text=Deseo%20el%20plan%20Socio%20(hasta%20200%20empresas))

Mejor valorMayorista

$2.900.000 COP/mes

Hasta 1.000 empresas

≈ $2.900 por empresa/mes

Hasta **1.000.000** documentos/mes emitidos

- Infraestructura dedicada y SLA
- Soporte técnico prioritario
- Condiciones y márgenes mayoristas

[Empezar](https://wa.me/51930973902?text=Deseo%20el%20plan%20Mayorista%20(hasta%201000%20empresas))

Precios en pesos colombianos, IVA no incluido. Marca blanca incluida en todos los planes. Trabajamos en modalidad de software propio ante la DIAN: cada empresa que administres necesita [**su propio certificado digital**](https://facturalatam.com/api/#certificados) y no está incluido en el plan. El límite de documentos es el total mensual emitido entre todas tus empresas; al superarlo puedes adquirir paquetes adicionales. ¿Gestionas más de 1.000 empresas o necesitas más volumen? [**Escríbenos por un plan mayorista a tu medida**](https://wa.me/51930973902?text=Deseo%20un%20plan%20mayorista%20a%20medida%20para%20revendedores).

Boletín

## Novedades de la DIAN y de la API, en tu correo

Cambios normativos, nuevas versiones de la API, guías de integración y avisos de mantenimiento. Un correo cuando hay algo importante, nunca spam.

Suscribirme


Al suscribirte aceptas nuestras [políticas de privacidad](https://facturalatam.com/api/#). Puedes darte de baja cuando quieras.

Cambios normativos DIAN Nuevas versiones de la API Guías de integración Avisos de mantenimiento

[![brand-logo](https://facturalatam.com/api/images/latam.jpg)](https://facturalatam.com/api/index.html)

Empresa de software especializada en facturación electrónica con altos estándares de calidad. Facturalatam es gestionado por el grupo Digital Buho SAS, con

**NIT 901846280 Medellín Colombia**

**© 2018 - 2026 [Facturalatam](https://facturalatam.com/). All Rights Reserved.**

**- [Terminos y condiciones](https://facturalatam.com/api/#)**
**- [Políticas de privacidad](https://facturalatam.com/api/#)**

**[![ChatGPT IA](https://facturalatam.com/api/images/chatgptico.png)](https://chatgpt.com/g/g-6757cbff7bf08191a45c4ee5ff55bc22-facturacion-electronica-dian-colombia "Hablar con IA entrenado para la API")**

**Hablar con IA para la APIDisponible 24 horas**

**[Asesor técnico WhatsApp](https://wa.me/51930973902?text=Hola%2C%20necesito%20soporte%20t%C3%A9cnico "Asesor técnico WhatsApp")**

**Asesor técnicoHorario de oficina**