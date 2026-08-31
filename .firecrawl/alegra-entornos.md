---
updatedAt: 2025-09-16T20:48:13.000Z
---

Fetch the complete documentation index at: https://e-provider-docs.alegra.com/llms.txt. Use this file to discover all available pages before exploring further. Append .md to any documentation page URL to get its markdown version.

# Entornos

En esta página encontrarás las url de los diferentes entornos en los que puedes usar la API.

| Entorno    | Url                                                | Descripción                                                                                                                                                                          |
| :--------- | :------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Sandbox    | <https://sandbox-api.alegra.com/e-provider/col/v1> | Este es el entorno de pruebas que apunta al ambiente de habilitación de la DIAN, por ende en este entorno podrás hacer pruebas de cualquier tipo sin ningún problema ni restricción. |
| Producción | <https://api.alegra.com/e-provider/col/v1>         | Este es el entorno de producción que apunta al entorno de producción de la DIAN.                                                                                                     |

> 📘 Emisión en ambiente sandbox
>
> Los documentos emitidos en el entorno sandbox quedarán rechazados si el NIT no ha realizado el proceso de habilitación y seleccionado a Alegra como su proveedor.
>
> **Los errores por este motivo son:**
>
> * Regla: 92, Rechazo: El Emisor del Documento no se encuentra Habilitado en la Plataforma.
> * Regla: NIE033, Rechazo: Debe ir el NIT del Empleador sin guiones ni DV.
>
> Para realizar pruebas de documentos aceptados en el ambiente sandbox puedes usar el NIT (900559088) y DV (2) de Alegra con un prefijo único para evitar respuestas de error por documento con número duplicado.

> 👍 Recomendación
>
> Te recomendamos habilitar la comunicación al ambiente de producción únicamente cuando hayas validado tu integración, debido a que Producción ya es el entorno real de la DIAN y cualquier envío será considerado como información verídica.

> 📘 Independencia entre los Entornos
>
> Es importante tener en cuenta que nuestros entornos de prueba y producción son completamente independientes entre sí. Esta independencia garantiza que las acciones y procesos llevadas a cabo en un entorno no tendrán ningún impacto en el otro.
>
> En otras palabras, cualquier proceso realizado en el ambiente sandbox, ya sea la gestión de compañías, la habilitación de compañías o la emisión de comprobantes, permanece completamente aislado y no afecta de ninguna manera al entorno de producción. Del mismo modo, las operaciones realizadas en el entorno de producción no influyen en el entorno de prueba.