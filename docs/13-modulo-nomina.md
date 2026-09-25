# 13 — Módulo de Nómina (mini-gestor)

> **Contexto:** Diseño funcional y de flujos UX/UI del módulo de Nómina para pymes colombianas. Alcance deliberadamente acotado: **calcula, documenta y da visibilidad; no dispersa pagos ni transmite a la DIAN.** Decisiones registradas en [07](07-decisiones-y-puntos-abiertos.md) como **D-97 a D-121** y puntos abiertos **A-34 a A-44**.
>
> **Estado:** diseño aprobado, sin implementar. Reemplaza la exclusión genérica de nómina en [05 §5](05-alcance-mvp-y-flujos.md).

---

## 1. Qué es y qué no es

**Es** un gestor de nómina para negocios de 3–50 empleados que hoy liquidan en Excel o le pagan a un contador por hacerlo. Resuelve: cuánto le pago a cada quien este período, cuánto me cuesta realmente, y cuánto llevo acumulado en prestaciones.

**No es** un ERP de recursos humanos. No hay reloj de marcación, ni control de asistencia, ni evaluación de desempeño, ni portal del empleado.

| Sí hace | No hace |
|---|---|
| Calcula devengados, deducciones y neto por empleado | Dispersa pagos a bancos |
| Genera el desprendible de pago imprimible | Transmite el documento soporte a la DIAN |
| Muestra el costo patronal total del período | Genera el archivo plano de PILA |
| Acumula provisiones (prima, cesantías, intereses, vacaciones) | Liquidación definitiva por terminación de contrato (ver A-37) |
| Guarda historial inmutable de períodos cerrados | Marcación de asistencia y portal del empleado |
| Liquida contratistas por prestación de servicios (camino de cálculo aparte, §4.3) | Emite la factura o el documento soporte del contratista |
| **Genera el papeleo laboral**: contratos, cartas, certificado laboral, resúmenes para el contador (§10.1) | Genera archivos máquina a máquina: plano bancario, PILA, transmisión DIAN (D-108) |
| Exporta a Excel/CSV para el contador | Firma electrónica del contrato |

### 1.1 El borde legal (importante)

El **documento soporte de pago de nómina electrónica** debe transmitirse a la DIAN dentro de los primeros 10 días hábiles del mes siguiente; es requisito para deducir la nómina en el impuesto de renta, y en 2026 aplica prácticamente a todo empleador. **Este módulo no lo transmite** (D-102).

Dos consecuencias obligatorias de diseño:

1. **La UI debe decirlo.** Al cerrar un período aparece una nota permanente: este módulo calcula y documenta la nómina; la transmisión del documento soporte a la DIAN es responsabilidad del empleador y no se realiza desde aquí. Sin ese aviso, el primer requerimiento de la DIAN al cliente se convierte en nuestro problema.
2. **Los datos se modelan con la estructura del anexo técnico de la DIAN desde el día uno** — agrupación de *devengados* y *deducidos*, identificación del trabajador, consecutivo, medio de pago. No se implementa la transmisión, pero cuando se implemente (o se delegue a un facilitador, igual que la facturación en [05 §4](05-alcance-mvp-y-flujos.md)) debe ser un adaptador, no una reescritura del modelo.

### 1.2 Orden de construcción (D-105)

**Se construye por rebanadas verticales completas según tipo de vinculación, no por capas.** La primera rebanada es **prestación de servicios de punta a punta**: alta -> contrato generado -> liquidación -> comprobante.

Por qué en ese orden:

- Es el **motor más simple** del módulo: `honorarios − retefuente − descuentos = neto`. Sin prestaciones, sin aportes patronales, sin auxilio de transporte, sin novedades de ausencia, sin provisiones.
- Es también el **contrato más simple** de plantear jurídicamente (§10), así que las dos piezas nuevas del módulo avanzan juntas sobre el caso fácil.
- Deja una rebanada **demostrable y usable por un cliente real** desde el primer entregable, en vez de tres capas a medias que no sirven para nada.
- Toda la plomería que exige —período, entradas, snapshot, inmutabilidad, desprendible, generador de documentos— es la **misma** que necesita el contrato laboral. La segunda rebanada solo agrega reglas de cálculo sobre infraestructura ya probada.

### 1.3 El techo de alcance: nivel 2, permanente (D-107)

Hay tres niveles posibles de ambición en un software de nómina, y son escalones muy desiguales:

| Nivel | Qué hace | Costo real |
|---|---|---|
| **1. Calcular** | Liquida, documenta y muestra el costo | Cero integración |
| **2. Preparar el pago** | Genera el archivo plano bancario, la planilla PILA y el documento soporte | **Archivo, no dinero.** Sin licencia, sin custodia de fondos, sin riesgo regulatorio |
| **3. Mover plata** | Dispersa desde la cuenta del cliente, concilia, hace tesorería | Partner de pagos y territorio de entidad vigilada. **No es un feature, es otro negocio** |

**El módulo se queda en el nivel 2, y eso es un techo permanente, no un aplazamiento.** El nivel 3 no está "para después": está descartado.

**Pero el nivel 2 hay que cortarlo por la mitad (D-108).** "Cercanía al dinero" resultó ser el eje equivocado; el que de verdad separa lo barato de lo caro es **quién es el destinatario del artefacto**:

| | Documentos **para personas** | Archivos **para sistemas** |
|---|---|---|
| Quién los recibe | Dueño, contador, empleado, banco como lector humano | Banco, operador PILA, DIAN — máquina a máquina |
| Ejemplos | Desprendible, certificado laboral, contrato, resumen para el contador, reporte de provisiones | Archivo plano bancario, planilla PILA, documento soporte DIAN |
| Especificación | La definimos nosotros | **La define un tercero**, cambia sin avisar y se valida automáticamente |
| Si sale mal | Alguien lo lee raro y se corrige | **Rechazo del sistema**, con consecuencia legal o financiera |
| Qué heredas | Nada | El *roadmap* y la superficie legal de un tercero |

**v1 se queda con toda la columna izquierda y nada de la derecha.** Esa columna derecha es justamente el terreno donde ya compiten plataformas maduras, con marco legal establecido y equipos dedicados a seguir cambios normativos; entrar ahí es pelear una guerra ajena. La columna izquierda, en cambio, es puro aprovechamiento de lo que un software que calcula puede regalarle a un negocio: nadie tiene que autorizarnos a imprimir un certificado laboral bien hecho.

**Esto reordena qué es el producto (D-109):** el módulo no es "un software de nómina" — es **el papeleo laboral de un negocio pequeño, resuelto**. El cálculo es el motor; los **documentos son el producto**. El generador de plantillas (§10) deja de ser un anexo simpático y pasa a ser la pieza central.

**Contexto que fija el techo:** el usuario objetivo es la tienda de barrio y el negocio mediano de pueblo, no la empresa de 200 empleados. Un negocio así **no dispersa sueldos por archivo bancario** — paga en efectivo o por transferencia suelta — y su PILA la hace el contador en su operador de siempre. Construir el archivo plano bancario para ese cliente sería resolver un problema que no tiene.

Cuatro razones, en orden de peso:

1. **Riesgo regulatorio y de responsabilidad.** Mover plata ajena implica custodia de fondos y responder por pagos fallidos. En el nivel 2 quien autoriza el pago en su banco es el cliente: nosotros generamos un archivo.
2. **Coherencia con la arquitectura.** Local-first y offline (D-01) es incompatible con dispersión bancaria, que exige internet y un tercero en línea. La dispersión sería el único pedazo del producto que no funciona sin red. En cambio, **generar un archivo funciona offline**; y la única pieza del nivel 2 que sí necesita red —la transmisión a la DIAN— es asíncrona y por lotes (10 días hábiles del mes siguiente), que es exactamente el modelo de [11](11-offline-resiliencia-y-facturacion.md).
3. **Es el mayor salto de valor por el menor costo.** El archivo plano bancario es tedioso pero completamente determinístico —cada banco tiene su formato— y le quita al cliente el trabajo manual que más odia. Sin tocar un peso.
4. **Posicionamiento.** "No tocamos tu plata" no es una limitación que haya que disculpar: frente a un dueño de pyme desconfiado es un argumento de venta.

**Tesorería, conciliación bancaria y flujo de caja quedan fuera para siempre**, y no por alcance sino por lugar: eso vive en el módulo contable consumiendo la nómina, no dentro de la nómina. Ningún competidor del segmento lo metió aquí, y tienen razón.

Nota de vocabulario: **la ARL no es un pago aparte** — va dentro de la PILA junto con salud, pensión, caja de compensación, SENA e ICBF. Una sola planilla, un solo pago. En el nivel 2 no se diseña "pago de ARL": se diseña la planilla PILA.

---

## 2. Principio rector: captura por excepción

**El período se abre precalculado y el usuario solo registra lo que se salió de lo normal.**

Nunca se marca asistencia. Si en una quincena de 15 días un empleado faltó 1 día, se registra **ese 1 día**, no los 14 restantes. La fórmula base es:

```
días_liquidados = días_del_período − Σ días de novedades de ausencia
```

con `días_del_período` = 15 (quincenal) o 30 (mensual), bajo convención **30/360**: el mes comercial siempre tiene 30 días y la quincena 15, independientemente del calendario real.

Esto no es una preferencia estética: es la razón de existir del módulo. En un negocio de 8 empleados, ~90% de los períodos son "todos trabajaron normal". El flujo feliz debe ser **abrir → revisar → cerrar en menos de 2 minutos**, con cero tecleo cuando no hubo novedades. Cualquier pantalla que obligue a confirmar empleado por empleado pierde contra la hoja de cálculo que el cliente ya tiene.

**Consecuencia de diseño:** la pantalla de liquidación arranca **completa y válida**, no vacía. El botón primario *Cerrar período* está habilitado desde el primer segundo.

---

## 3. Periodicidad quincenal y mensual — un solo algoritmo

El negocio elige la periodicidad en el wizard de arranque (§7.4) y puede cambiarla, con efecto desde el siguiente mes y nunca a mitad de mes. Las opciones son **semanal, quincenal y mensual** (D-110).

**Los días de corte los define el negocio (D-111):** una quincena puede ser 5 y 20, no necesariamente 1–15 y 16–fin. Es como opera el negocio real y no hay razón para imponerle nuestro calendario.

**Eso generaliza el cruce de mes.** Con cortes en 5 y 20, la quincena que va del 20 al 4 cruza el fin de mes igual que lo hace una semana. Cruzar meses deja de ser un caso raro de la periodicidad semanal y pasa a ser la norma: `month_anchor` (§3.2) tiene que ser una **regla general** —a qué mes pertenece un corte que cruza— y no un parche.

**Y cambia lo que la pantalla debe dibujar:** un mes deja de contener exactamente dos cortes. Con cortes en 5 y 20 se ven **tres tramos** — la cola del anterior, uno completo y el arranque del siguiente. El calendario y la franja de cortes renderizan *los tramos que tocan el mes*, no "los dos cortes del mes".

**El pago diario cabe dentro de este mismo concepto (A-43)**, sin invertir nada. Mientras exista una plantilla estable de gente que se espera que venga —el taller con "los muchachos"—, el default sigue siendo "vino" y lo que se registra sigue siendo la ausencia: cambia la **frecuencia de liquidación**, no la forma de capturar. Con liquidación diaria no se dibujan treinta barras verticales: la barra solo tiene sentido cuando el corte abarca varios días, y el estado de pago de cada día ya lo comunican los **tres tonos de la línea**. La frontera a vigilar no es el pago diario sino el **trabajo ocasional**, donde la ausencia deja de ser excepción y el modelo se invierte solo.

### 3.1 El problema

La quincena es una unidad de **pago**, pero la ley razona en **meses**. Estos topes y umbrales son mensuales y se rompen si se evalúan sobre una quincena aislada:

| Regla | Umbral mensual | Qué pasa si se evalúa por quincena |
|---|---|---|
| Piso del IBC | 1 SMMLV | Toda quincena cae bajo el piso y se infla artificialmente |
| Techo del IBC | 25 SMMLV | Nunca se alcanza; se cotiza de más en salarios altos |
| Fondo de Solidaridad Pensional (FSP) | desde 4 SMMLV | Nunca se dispara: un salario de 4 SMMLV "parece" de 2 en la quincena |
| Derecho a auxilio de transporte | hasta 2 SMMLV | Un salario de 3 SMMLV "parece" de 1,5 y cobra un auxilio que no le corresponde |

### 3.2 La solución (D-100)

**Se liquida siempre el mes acumulado y se resta lo ya liquidado en períodos anteriores del mismo mes.**

```
valor_a_pagar(período_n) = liquidación_mensual_acumulada(hasta período_n)
                         − Σ liquidación_de_períodos_anteriores_del_mismo_mes
```

Cada `PayrollPeriod` lleva un `month_anchor` (el mes calendario al que pertenece). El motor calcula el mes completo con todas las reglas legales aplicadas correctamente, y luego descuenta lo ya pagado.

**Regla de `month_anchor` para cortes que cruzan (D-111):** un corte pertenece al mes que contiene su **fecha de fin**, que es el mes en que se liquida y se paga. Con cortes en 5 y 20, el tramo del 20 de agosto al 4 de septiembre ancla en **septiembre**. Es la regla más simple que no requiere partir el corte, y coincide con el momento en que el dinero sale. Cuando llegue el motor legal habrá que revisarla contra el IBC, que es estrictamente mensual: puede exigir prorratear el corte entre los dos meses en vez de asignarlo entero. **Mientras el módulo esté en modo simple (§4.5) la regla basta.**

Por qué esto es lo correcto y no solo lo elegante:

- **Un solo camino de código.** En periodicidad mensual solo existe un período por mes, así que el sustraendo es cero y el algoritmo degenera al caso simple. No hay dos motores que mantener ni dos juegos de pruebas.
- **Los umbrales se evalúan donde la ley los define** (sobre el mes), no sobre una fracción.
- **Absorbe la novedad tardía.** Si el empleado tuvo horas extra en la primera quincena que nadie registró, al liquidar la segunda el mes se recalcula completo y la diferencia sale automáticamente, sin reabrir el período cerrado.
- **Cuadra con PILA.** El aporte a seguridad social se declara y paga mensualmente; el mes cerrado del módulo es la cifra que el contador necesita.

**Efecto visible al usuario:** en periodicidad quincenal, la segunda quincena suele traer un ajuste pequeño. La pantalla de liquidación debe mostrarlo como una línea explícita — *Ajuste del mes* — y no esconderlo dentro de otro concepto. Un ajuste sin explicación es un ticket de soporte.

---

## 4. Modelo de datos

`Employee` es una **entidad independiente** (D-98): no entra al Directorio junto a Clientes/Proveedores. Un empleado tiene ~20 campos propios, ciclo de vida propio (activo/retirado), datos sensibles (documento, cuenta bancaria, EPS/AFP) y no comparte ni una consulta con las entidades comerciales. Meterlo al Directorio por ahorrar una vista contamina las dos cosas.

| Entidad | Rol | Notas de diseño |
|---|---|---|
| `Employee` | Persona + condiciones contractuales vigentes | `status`: activo / retirado. Nunca se borra: los períodos cerrados lo referencian |
| `EmployeeSalaryHistory` | Historial de cambios salariales con fecha de vigencia | **Crítico:** pisar el salario rompe los períodos ya cerrados. El motor consulta el salario *vigente en la fecha del período* |
| `PayrollSettings` | Parámetros legales por vigencia (ver §9) | Versionados por rango de fechas, no un registro único mutable |
| `PayrollConcept` | Catálogo de conceptos con 3 banderas | Ver §4.1 |
| `PayrollPeriod` | La corrida. `periodicity`, `month_anchor`, `start/end`, `status` | Ver §8 |
| `PayrollEntry` | Una línea por empleado en el período | **Snapshot congelado** de devengados/deducciones/neto |
| `PayrollEntryLine` | Desglose concepto a concepto de una `PayrollEntry` | Es lo que se imprime en el desprendible y lo que alimentaría el anexo DIAN |
| `PayrollNovelty` | El delta del período (ausencia, hora extra, bonificación, descuento) | Ver §6 |
| `EmployeeAccrual` | Provisiones acumuladas por empleado (prima, cesantías, intereses, vacaciones) | Saldo corriente + movimientos |

### 4.1 El catálogo de conceptos: tres banderas

Es la pieza que evita que el motor se convierta en una cascada de `if`. Cada concepto declara:

| Bandera | Pregunta | Ejemplo donde importa |
|---|---|---|
| `kind` | ¿Devengado o deducción? | — |
| `is_salarial` | ¿Entra a la base prestacional (prima, cesantías, vacaciones)? | Una bonificación pactada como no salarial no provisiona |
| `affects_ibc` | ¿Entra a la base de seguridad social? | — |

El auxilio de transporte es el caso que demuestra por qué hacen falta las tres: es devengado, **sí** entra a la base de prima y cesantías, **no** entra al IBC de seguridad social, y solo lo recibe quien gana hasta 2 SMMLV. Con banderas es una fila de tabla; sin ellas es un `if` repetido en cinco lugares del motor.

Beneficio adicional: el negocio puede crear "Bonificación de ventas" o "Descuento de préstamo" desde Configuraciones, sin tocar código.

### 4.2 Jerarquía de configuración: qué es global y qué es por empleado

**Regla:** un ajuste es **global** si el negocio lo decide una vez y no lo vuelve a mirar; es **por empleado** si dos empleados del mismo negocio pueden diferir legítimamente. Cuando ambas son ciertas —la mayoría comparte un valor pero alguno se sale— el patrón es **default global + override por empleado, con el override escondido tras "opciones avanzadas"**. Así el taller de 8 empleados nunca ve el campo, y la empresa de 120 lo tiene sin necesidad de una versión distinta del producto.

| Nivel | Qué vive ahí | Frecuencia de cambio |
|---|---|---|
| **Negocio** | Periodicidad y día de pago · exoneración art. 114-1 (A-36) · caja de compensación · clase de riesgo ARL **por defecto** · catálogo de conceptos | Una vez, al configurar |
| **Parámetros legales** | SMMLV, auxilio de transporte, tasas, recargos, UVT, divisor de horas | **No se preguntan** — precargados por vigencia (§9) |
| **Empleado** | Tipo de vinculación (§4.3) · salario · fecha de ingreso · EPS/AFP · clase de riesgo ARL *si difiere del default* · tipo de contrato laboral | Al contratar y en cambios puntuales |
| **Período** | Novedades | Cada corrida |

**Periodicidad de pago: global, sin override en v1 (D-103, ampliada a semanal por D-110).** Dos periodicidades conviviendo significan dos corridas por mes, dos reconciliaciones y una PILA que hay que cuadrar a mano — y no existe el negocio pequeño que le pague a Juan quincenal y a María mensual. No es una puerta cerrada: como D-100 liquida sobre el **mes acumulado**, si algún día hace falta basta con anclar el período por empleado; el motor ya lo soporta estructuralmente.

**Clase de riesgo ARL: default global + override por empleado.** Legalmente depende del oficio de cada persona, pero en una ferretería casi todos son la misma clase. Caso de libro del patrón.

### 4.3 Tipos de vinculación

Hay dos cosas distintas que la conversación corriente mezcla bajo "tipo de contrato".

**(a) Tipo de contrato laboral — indefinido, término fijo, obra o labor.** Para liquidar la nómina **los tres son idénticos**: mismo salario, mismas prestaciones, mismas deducciones, mismos aportes patronales. La diferencia aparece únicamente al **terminar** el contrato (indemnización; en obra o labor el fin llega con la obra). Conclusión: es un **dato que se guarda en `Employee`, no un parámetro que ramifique el motor de cálculo** (D-104). Guardarlo ahora cuesta un campo y es prerrequisito de A-37.

**(b) Prestación de servicios — no es nómina.** Es vinculación civil, no laboral, y cambia el cálculo entero:

| | Contrato laboral | Prestación de servicios |
|---|---|---|
| Qué se paga | Salario | Honorarios |
| Prestaciones (prima, cesantías, vacaciones) | Sí | **No** |
| Salud y pensión | Deducción al empleado + aporte patronal | **El contratista cotiza por su cuenta**, sobre el 40% de sus ingresos |
| ARL, caja, SENA, ICBF | Sí | No (salvo riesgo IV–V) |
| Auxilio de transporte | Si aplica | No |
| Retención | Solo rentas de trabajo altas | **Retefuente por honorarios**, 10%/11% sobre pagos > 27 UVT |
| Documento ante la DIAN | Documento soporte de nómina | Factura del contratista, o documento soporte en adquisiciones a no obligados a facturar |
| Novedades de ausencia | Sí | No aplica — se paga lo contratado |

> **Advertencia de producto:** si hay subordinación, horario y exclusividad, opera el **contrato realidad** y un juez lo declara laboral con las prestaciones retroactivas. El módulo no debe presentar la prestación de servicios como una forma de "ahorrar prestaciones": es una vinculación distinta, no un contrato laboral barato.

**Diseño propuesto (pendiente de confirmación — A-39):** un discriminador `Employee.worker_type` (`laboral` | `prestacion_servicios`) que enruta a **dos estrategias de cálculo sobre el mismo `PayrollPeriod`**. Ambos aparecen en la misma corrida, la misma tabla y el mismo *total a pagar del período* — que es como el negocio lo vive: sale del mismo bolsillo el mismo día. Pero el motor los trata distinto y los documentos que genera difieren.

El camino del contratista es **más barato de implementar, no más caro**: `honorarios − retefuente − otros descuentos = neto`, sin prestaciones, sin aportes patronales, sin auxilio de transporte y sin novedades de ausencia. En la tabla de liquidación su fila muestra menos columnas: no se le enseña "auxilio de transporte: $0".


---

### 4.4 Modelo de novedades — dos tablas (D-112)

**No inventamos la taxonomía: ya existe.** El **anexo técnico de nómina electrónica de la DIAN** (v3.0, Resolución 000040 de 2024) define la estructura de *devengados* y *deducidos* y enumera los tipos de novedad. Es el vocabulario que el país entero usa, y adoptarlo cumple D-102 sin esfuerzo extra — modelamos según el anexo no para transmitir nosotros, sino para que el contador pueda.

**Pero el vocabulario no es el esquema.** El anexo tiene ~40 conceptos entre devengados y deducciones; eso no son 40 tablas ni 40 columnas. Es un catálogo.

**`novelty_type`** — el catálogo. Datos semilla, ampliables por el negocio desde Configuraciones.

| Campo | Para qué |
|---|---|
| `code` | `INCAPACIDAD_EPS`, `HORA_EXTRA_DIURNA`, `VACACIONES` |
| `label` | Lo que ve el usuario. **Lo elige el negocio** cuando crea conceptos propios — ver la nota de nombres abajo |
| `unit` | `dias` · `horas` · `monto` |
| `effect` | `devengado` · `deduccion` · `ninguno` |
| `consumes_day` | **Decide si sale como avatar en el calendario** (§7) |
| `is_salarial` | ¿Entra a base prestacional? (§4.1) |
| `affects_ibc` | ¿Entra a base de seguridad social? (§4.1) |
| `dian_code` | El mapeo al anexo técnico |

Las tres banderas del medio son las de §4.1; `dian_code` es lo único que agrega esta sección.

**`novelty`** — los hechos. Una sola tabla para todo:

```
id · employee_id · type_code · start_date · end_date · quantity · note
```

`quantity` no necesita declarar de qué es: el `type_code` ya trae la unidad desde el catálogo.

#### Lo que deliberadamente NO lleva

| Ausencia | Por qué |
|---|---|
| Campo `status` | Se deriva: futuro = programado, pasado = ocurrido. Cancelar = borrar. La inmutabilidad la impone el corte cerrado (§8), no la novedad |
| Flujo de aprobación | En una tienda el dueño **es** quien aprueba; registrar ya es aprobar. Pendiente/aprobado es ceremonia de empresa grande |
| Una tabla por tipo | Vacaciones, incapacidades y horas extra son la misma forma: alguien, un rango, una cantidad |
| Entidad "vacaciones programadas" | Es una `novelty` con fechas futuras. Nada más |
| Entidad "trabajadores del día" | Es una **consulta**: activos menos los que tienen novedad con `consumes_day` esa fecha. Guardarlo sería duplicar la verdad y abrir la puerta a que se contradiga |

Los dos últimos son el punto: **ni la programación ni la presencia agregan nada al modelo.** Son lo mismo que ya hace la línea de continuidad del calendario — derivar en vez de almacenar.

#### Set inicial: 13 tipos

**Consumen día** (avatar en el calendario): incapacidad EPS · incapacidad ARL · licencia de maternidad/paternidad · licencia remunerada · licencia no remunerada · vacaciones · ausencia injustificada · permiso por horas

**No consumen día** (marcador discreto): hora extra diurna · hora extra nocturna · recargo nocturno · bonificación · descuento o préstamo

Los dos últimos **no se capturan desde el calendario** sino al liquidar (D-121): una bonificación o un descuento no le pasan a nadie *un día* — son ajustes de un pago, y anclarlos a una fecha era arbitrario. Siguen siendo conceptos del catálogo; lo que cambia es dónde se registran.

#### Nota sobre los nombres de los conceptos

El registro que genera este módulo **es evidencia**. Un histórico que muestre "el dueño le pagó la salud a Juan durante ocho meses" es el tipo de documento que sostiene un **contrato realidad** en un pleito laboral, con prestaciones retroactivas.

No es razón para no construirlo — sí lo es para que **el negocio elija el nombre de sus conceptos** en vez de imponérselo nosotros. No es lo mismo *"Aporte a salud del empleado"* que *"Auxilio para seguridad social"*: el primero nombra una relación laboral, el segundo una ayuda. Es exactamente lo que permite el catálogo configurable, y es una razón de peso para que lo sea.

### 4.5 Modo simple vs. modo legal (D-113)

`PayrollSettings.calc_mode`: **`simple` | `legal`**, por negocio.

En **modo simple** no hay IBC, ni prestaciones, ni aportes patronales, ni topes: cada línea de concepto lleva un **valor que el usuario teclea**. Es lo que necesita un taller que hoy paga en efectivo y quiere empezar a dejar registro.

**El motor legal no reemplaza la captura manual: es una capa de autorelleno encima.** Misma tabla, mismo campo `quantity`, misma pantalla — lo único que cambia es quién llena el número. En modo legal el motor lo **propone** y el usuario puede pisarlo, que es la regla de override ya declarada innegociable en §6.

Por eso construir el modo simple primero **no es trabajo botado**: es el cimiento, y lo legal se le monta encima sin migrar nada. Cambiar de modo no toca los períodos ya cerrados.

---

## 5. Motor de cálculo

Zona de alto riesgo según [CLAUDE.md](../CLAUDE.md): aritmética decimal exacta (Decimal.js en cliente, `Decimal` en backend), nunca punto flotante. Toda cifra intermedia se persiste; nada se recalcula al vuelo sobre un período cerrado.

### 5.1 Devengados

| Concepto | Fórmula | Regla |
|---|---|---|
| Salario básico | `salario_mensual × días_liquidados / 30` | |
| Auxilio de transporte | `auxilio_mensual × días_con_derecho / 30` | Solo si `salario_mensual ≤ 2 SMMLV`. Ver A-34 sobre suspensión en incapacidad/vacaciones |
| Horas extra y recargos | `valor_hora × horas × (1 + %recargo)` | `valor_hora = salario_mensual / divisor_horas_mes` (parámetro, ver A-35) |
| Bonificaciones / comisiones | monto capturado | Salarial o no salarial según el concepto |

### 5.2 Deducciones al empleado

| Concepto | Base | Tasa |
|---|---|---|
| Salud | IBC | 4% |
| Pensión | IBC | 4% |
| Fondo de Solidaridad Pensional | IBC | 1% desde 4 SMMLV, escalonado hasta 2% |
| Otros (préstamos, libranzas, embargos) | — | monto capturado |

**IBC** = suma de conceptos con `affects_ibc = true`. Excluye el auxilio de transporte. Piso 1 SMMLV, techo 25 SMMLV, ambos evaluados sobre el mes (§3.2).

**Validación, no bloqueo:** las deducciones voluntarias no deberían dejar el neto por debajo del 50% del salario. Cuando se cruza el umbral, la UI muestra advertencia ámbar en la fila y en el diálogo de cierre — pero **no impide cerrar**: hay excepciones legales y el usuario es quien responde por su caso.

### 5.3 Aportes patronales (informativos — costo del empleador, no se descuentan)

Salud 8,5% · Pensión 12% · ARL 0,522%–6,96% según clase de riesgo · Caja de compensación 4% · SENA 2% · ICBF 3%.

**Exoneración art. 114-1 ET:** los empleadores contribuyentes de renta están exonerados de salud (8,5%), SENA e ICBF por empleados que devenguen menos de 10 SMMLV — que en una pyme típica son todos. Aplicarla o no cambia el costo patronal reportado en más del 13%, así que no puede quedar implícita: es una casilla de configuración por negocio (A-36).

### 5.4 Provisiones (el mayor valor por unidad de esfuerzo)

Pura aritmética de acumulación, sin transmisión ni integración con nadie — encaja exacto con "informativo y de gestión", y es la cifra que el dueño de pyme nunca sabe y que le explota en junio y diciembre.

| Provisión | Tasa | Base |
|---|---|---|
| Prima de servicios | 8,33% | Salario + auxilio de transporte |
| Cesantías | 8,33% | Salario + auxilio de transporte |
| Intereses sobre cesantías | 12% anual | Saldo de cesantías acumulado |
| Vacaciones | 4,17% | Solo salario (sin auxilio de transporte) |

Se acumulan en `EmployeeAccrual` en cada cierre de período y se muestran como saldo corriente en el detalle del empleado y como total en el dashboard del módulo. En v1 **no se pagan desde el módulo** (ver A-38).

---

## 6. Catálogo de novedades (v1)

| Tipo | Unidad | Efecto sobre el cálculo |
|---|---|---|
| Incapacidad general (EPS) | rango de fechas | Reduce días trabajados; paga al 66,67% (días 1–2 a cargo del empleador, desde el 3 a cargo de la EPS); no puede quedar bajo el SMMLV proporcional |
| Incapacidad laboral (ARL) | rango de fechas | Paga al 100% a cargo de la ARL |
| Licencia remunerada (maternidad, paternidad, luto) | rango de fechas | Paga al 100% |
| Licencia no remunerada | rango de fechas | Descuenta salario; se mantiene la obligación de cotizar |
| Vacaciones | rango de fechas | Paga salario; descuenta del saldo acumulado de vacaciones |
| Ausencia injustificada | días | Descuenta salario y auxilio de transporte |
| Hora extra / recargo | horas + tipo | Suma según §5.1 |
| Bonificación / comisión | monto | Salarial o no salarial según el concepto |
| Descuento / préstamo | monto | Deducción |

**Regla de UX no negociable:** el valor calculado de toda novedad es **editable con override manual y campo de razón**. Las incapacidades reales casi nunca cuadran con la fórmula (transcripciones de la EPS, prórrogas, pagos parciales), y un sistema que no deja corregir se abandona en la primera. El override queda en el registro de auditoría y se marca visualmente en el desprendible.

---

## 7. Pantallas y flujos

Reutiliza los patrones ya construidos. Nada aquí exige un componente nuevo salvo la tabla de liquidación.

| Ruta | Pantalla | Patrón existente que reusa |
|---|---|---|
| `/nomina` | **Períodos** — card del período abierto arriba, histórico debajo | `pages/invoices/InvoicesView.vue` |
| `/nomina/empleados` | **Empleados** — tabla + `CreateEmployeeDialog` | `pages/directory/DirectoryView.vue` + `DataTable` |
| `/nomina/empleados/:id` | **Detalle del empleado** — condiciones, historial salarial, pagos, provisiones | `pages/Items/ItemDetailView.vue` |
| `/nomina/periodo/:id` | **Liquidación** — la pantalla central | nueva |
| `/nomina/periodo/:id/empleado/:eid` | **Desprendible de pago** (imprimible) | `pages/invoices/InvoiceDocument.vue` |
| Configuraciones → pestaña *Nómina* | Periodicidad, ajustes del negocio, catálogo de conceptos | `pages/settings/SettingsView.vue` |
| `/nomina/inicio` | **Wizard de arranque** (una sola vez, §7.4) | nueva |

El módulo entra al sidebar y al `ModuleNavSelect` como una entrada más de `config/navigation`.

### 7.1 Flujo principal — la corrida del período

```
[Períodos] ──"Abrir período"──> [Liquidación]  (ya precalculada, válida, cerrable)
                                     │
                     ┌───────────────┼────────────────┐
                     ▼               ▼                ▼
              agregar novedad   ver desglose    editar override
                (diálogo)        (fila expande)   (con razón)
                     │
                     ▼
            "Cerrar período" ──> [diálogo de confirmación con resumen]
                                     │  neto a pagar · aportes patronales
                                     │  costo total · nº de empleados
                                     │  advertencias (deducciones >50%, etc.)
                                     │  aviso DIAN (§1.1)
                                     ▼
                              período CERRADO (inmutable)
                                     │
                                     ▼
                      desprendibles + resumen para el contador
```

### 7.2 La pantalla de Liquidación

Es donde se gana o se pierde el módulo.

- **Tabla:** filas = empleados; columnas = *Devengado · Deducciones · **Neto***. La fila expande para ver el desglose concepto a concepto.
- **Barra fija inferior** con los totales del período: neto a pagar, aportes patronales, **costo total**. El costo total es la cifra que el dueño no conoce y por la que paga el módulo.
- **Un solo botón primario:** *Cerrar período*. Habilitado desde el inicio (§2).
- **Acciones por fila:** agregar novedad · ver desprendible · marcar como pagado.
- **Las novedades se capturan en diálogo desde la fila**, nunca en una pantalla aparte. Navegar fuera de la tabla por cada incapacidad es exactamente lo que devuelve al usuario al Excel.
- **Empleados sin novedades no piden confirmación.** Se ven, están calculados, y no estorban.

### 7.3 Alta de empleado

Formulario en tres bloques, en este orden: **Identificación** (nombre, documento, fecha de nacimiento) → **Contrato** (tipo, fecha de ingreso, cargo, salario, periodicidad de pago, clase de riesgo ARL) → **Afiliaciones y pago** (EPS, AFP, caja de compensación, medio de pago). Solo el primer bloque y el salario son obligatorios para poder liquidar; el resto se puede completar después, con un indicador de "perfil incompleto" en la tabla. Bloquear el alta hasta tener la EPS es fricción sin beneficio: el negocio quiere pagar hoy.

### 7.4 Wizard de arranque (una sola vez)

El módulo no sirve hasta que exista configuración, y una pestaña de ajustes en blanco es una pésima primera impresión. La primera entrada a `/nomina` abre un wizard de tres pasos; después, lo mismo vive como pestaña en Configuraciones y casi nunca se vuelve a tocar.

| Paso | Qué pregunta |
|---|---|
| 1. **Cómo pagas** | Periodicidad (semanal / quincenal / mensual) y **los días de corte** (ej. 5 y 20) |
| 2. **Tu empresa frente a la ley** | ¿Contribuyente de renta? (exoneración art. 114-1, A-36) · caja de compensación · clase de riesgo ARL predominante |
| 3. **Tu gente** | Alta rápida de empleados, o seguir con la lista vacía |

**Principio: nunca preguntar lo que el sistema puede saber.** El SMMLV, el auxilio de transporte, las tasas de aportes, los recargos y la UVT son idénticos para todos los negocios del país y ya vienen precargados por vigencia (§9). Preguntárselos al usuario es pedirle que haga nuestro trabajo y, peor, convertirlo en la fuente de un error legal. El wizard solo pregunta lo que **varía entre negocios**.

---

## 8. Estados e inmutabilidad

Reusa el patrón ya implementado en `Bill` (`fiscal_status` + anulación, migraciones `0009`/`0010`) y la filosofía de integridad de [04](04-seguridad.md).

```
borrador ──> en_revisión ──> cerrada ──> pagada
                                │
                                └──> anulada (con motivo, sin borrar)
```

- **Un período cerrado no se edita.** Nunca.
- **Corrección** = anular y reliquidar, o —lo más común— dejar que el siguiente período del mismo mes absorba la diferencia por el mecanismo de §3.2.
- **Las cifras del período cerrado son snapshot**, no consultas vivas. Si en septiembre alguien sube el salario de un empleado, la quincena de marzo debe seguir mostrando exactamente lo que se pagó en marzo. Esto es lo que hace `EmployeeSalaryHistory` obligatorio y no un lujo.
- Un empleado retirado **no se borra**: cambia a `status = retirado` y sigue apareciendo en los períodos históricos que lo referencian.

---

## 9. Parámetros legales — cero valores en el código

Todos los valores de esta sección viven en `PayrollSettings`, **versionados por rango de vigencia**. Ninguno se escribe en el código fuente.

No es purismo. Entre 2025 y 2027 hay tres cambios legales escalonados en curso por la Ley 2466 de 2025 y la Ley 2101 de 2021:

| Cambio | Antes | Ahora | Después |
|---|---|---|---|
| Jornada semanal | 44 h (jul 2025) | **42 h desde el 15 de julio de 2026** | — |
| Recargo dominical/festivo | 80% (jul 2025) | **90% desde julio de 2026** | 100% en julio de 2027 |
| Inicio de la jornada nocturna | 10:00 p.m. | **7:00 p.m.** | — |

Un módulo con estos números incrustados nace roto y hay que recompilarlo cada julio.

**Parámetros de 2026 (valores de referencia — deben confirmarse con contador antes de implementar):**

| Parámetro | Valor 2026 |
|---|---|
| SMMLV | $1.750.905 |
| Auxilio de transporte | $249.095 |
| Tope de derecho a auxilio de transporte | 2 SMMLV |
| Salud / pensión empleado | 4% / 4% |
| FSP | desde 4 SMMLV, 1%–2% escalonado |
| Salud / pensión patronal | 8,5% / 12% |
| ARL | 0,522%–6,96% según clase de riesgo |
| CCF / SENA / ICBF | 4% / 2% / 3% |
| Recargo nocturno | 35% |
| Hora extra diurna / nocturna | 25% / 75% |
| Recargo dominical y festivo | 90% (desde julio 2026) |
| Divisor de horas mes | ver A-35 |
| UVT | $52.374 |
| Retefuente por honorarios (prestación de servicios) | 10% no declarantes / 11% declarantes, sobre pagos > 27 UVT ($1.414.098) |
| Retefuente por servicios generales | 4% / 6% |

---

## 10. Generación de documentos

### 10.1 Catálogo de documentos

Es el corazón del módulo (D-109), no un accesorio. Agrupado por destinatario, que es como el negocio lo vive:

**Para el empleado**

| Documento | Cuándo | Nota |
|---|---|---|
| Desprendible de pago (colilla) | Cada período | §7 |
| **Certificado laboral** | A pedido | El documento más pedido de todos — bancos, arriendos, trámites. Hoy el dueño lo escribe a mano o simplemente no lo da |
| Constancia y liquidación de vacaciones | Al salir a vacaciones | Sale del saldo acumulado (§5.4) |
| Paz y salvo | Al terminar | Ligado a A-37 |

**Para el contador** — el usuario secundario que hoy recibe la información por WhatsApp y en desorden

| Documento | Nota |
|---|---|
| Resumen del período | Devengados, deducciones y aportes, por empleado y consolidado |
| **Resumen mensual con los IBC ya calculados** | **Es lo que necesita para hacer la PILA en su operador de siempre.** No generamos la planilla: le entregamos los números cuadrados para que él la haga. ~90% del valor con 0% del riesgo |
| Reporte de provisiones acumuladas | Prima, cesantías, intereses, vacaciones (§5.4) |
| Libro de nómina | Histórico de períodos cerrados |
| **Exportable a Excel/CSV** | No opcional: el contador vive en Excel. Es la integración real con él |

**Para el dueño**

| Documento | Nota |
|---|---|
| Contratos desde plantilla | §10.2 en adelante |
| **Cartas laborales** | Aumento de salario, terminación, llamado de atención, autorización de descuento, permiso. Un dueño de tienda no sabe redactarlas y se mete en problemas cuando improvisa |
| Costo del período, del mes y del año | La cifra que justifica la compra |

Las cartas laborales usan **el mismo motor de plantillas que los contratos**, así que su costo marginal es casi cero una vez el generador existe. Es la mejor razón para construir bien el generador antes que cualquier otra cosa.

**No hay una sección "Documentos".** Cada documento se genera desde donde vive su dato —el empleado, el período— y queda en el historial de esa entidad. Una bandeja central de documentos es un mueble que nadie visita.

**Caso frontera (A-42):** el *certificado de ingresos y retenciones* es para una persona, pero tiene **formato oficial de la DIAN** (formulario 220). Cae justo en la línea de D-108 y queda fuera hasta decidirlo.

### 10.2 Por qué los contratos encajan aquí y no son un módulo aparte

Para poder liquidar, el módulo **ya captura casi todos los campos que un contrato necesita**: partes, documentos de identidad, fecha de inicio, duración, valor, periodicidad de pago, objeto o cargo. El contrato es en buena medida un **render de datos que el sistema ya tiene** — costo marginal bajo, valor percibido alto: hoy la pyme le paga a un abogado o copia un Word prestado de un conocido.

Además reordena el ciclo de vida para mejor. Hoy el flujo es *alta de empleado -> liquidar*; con plantillas es **generar contrato -> el empleado queda creado**. Una sola captura de datos, dos salidas. Por eso no vive en una sección propia: se entra desde el alta del empleado ("Generar contrato" al terminar) y desde el detalle del empleado (historial de contratos generados).

### 10.3 Los límites que evitan que esto se vuelva un procesador de texto

- **Campos rellenables + bloques de cláusula activables. Sin edición libre del cuerpo.** Es exactamente el "semi-personalizado" correcto. Si el cliente necesita redactar, exporta a `.docx` y termina en Word — no construimos un editor de texto enriquecido.
- **Sin firma electrónica.** Es un producto regulado aparte (Ley 527). Se genera PDF, se imprime y se firma a mano.
- **Plantillas versionadas**, con la fecha de su revisión jurídica registrada.
- **El contrato generado es inmutable**, misma filosofía que el período cerrado (§8): si el salario cambia en septiembre, el contrato firmado en marzo debe seguir diciendo lo que decía. Se guarda el snapshot de los valores renderizados, no una consulta viva.

### 10.4 Modelo y reuso

| Entidad | Rol |
|---|---|
| `ContractTemplate` | Tipo, versión, fecha de revisión jurídica, cuerpo con marcadores, cláusulas opcionales |
| `GeneratedContract` | Empleado + plantilla/versión + snapshot de valores + PDF + fecha. **Inmutable** |

Reusa dos cosas que ya existen en el proyecto: el **logo del negocio** ya se guarda desde Configuraciones (`pages/settings/BusinessImageCard.vue`), y `pages/invoices/InvoiceDocument.vue` ya es el patrón de documento imprimible con identidad del negocio.

**Cláusulas opcionales para prestación de servicios:** confidencialidad · propiedad intelectual · no competencia · cesión del contrato · terminación anticipada · exclusividad (⚠️ bandera de contrato realidad, ver §10.5).

### 10.5 Checklist de idoneidad (A-41)

**El riesgo:** hacer que generar contratos de prestación de servicios cueste un clic **industrializa la exposición legal del cliente** si los usa para gente que en realidad trabaja subordinada. Seríamos la herramienta que volvió trivial el contrato realidad.

**La propuesta:** tres preguntas antes de generar — ¿cumple horario fijo? ¿trabaja exclusivamente para ti? ¿le das órdenes sobre *cómo* hacer el trabajo? Si contesta que sí a varias, la UI advierte *esto probablemente es un contrato laboral* y ofrece la plantilla laboral en su lugar.

Convierte un pasivo en funcionalidad: es información genuinamente útil para un dueño de pyme que no distingue las figuras, y es el tipo de detalle que hace que confíe en el producto. Cuesta fricción en un flujo que queremos rápido — de ahí que quede como punto abierto y no como decisión.

### 10.6 Riesgo jurídico (A-40)

Generar contratos roza la asesoría jurídica: si una plantilla está mal, el perjudicado es el cliente y el señalado somos nosotros. Requisitos mínimos **antes de publicar**, no después:

1. Revisión y visto bueno de **abogado laboralista** por cada plantilla, con fecha registrada.
2. Aviso visible en el documento y en la UI: es una **plantilla base** y no reemplaza asesoría jurídica.
3. Registro de qué versión de plantilla se usó en cada contrato generado (ya cubierto por `GeneratedContract`).

---

## 11. Alcance: qué entra, qué llega después y qué nunca

La distinción importa: mezclar "todavía no" con "nunca" en una sola lista es lo que deja la puerta abierta al scope creep. El techo permanente está fijado en el **nivel 2** (§1.3, D-107).

### 11.1 v1 — nivel 1 (calcular y documentar)

Liquidación por período (quincenal o mensual), novedades por excepción, provisiones acumuladas y **todo el catálogo de documentos para personas** (§10.1): desprendible, certificado laboral, contratos y cartas laborales desde plantilla, resúmenes para el contador con export a Excel. **Primera rebanada: prestación de servicios** (D-105).

### 11.2 Fuera de v1, no descartado

- **Liquidación definitiva por terminación de contrato** (A-37) — el candidato más fuerte a *fast-follow*: es frecuente, dolorosa, y es puro documento para personas.
- **Pago efectivo de prima y cesantías** desde el módulo (A-38); en v1 solo se acumulan.
- Salario integral.
- Certificado de ingresos y retenciones (A-42), si se resuelve el caso frontera de formato oficial.

### 11.3 Nunca — archivos máquina a máquina y movimiento de dinero

Todo lo de la columna derecha de D-108: artefactos cuya especificación la define un tercero, cambia sin avisar y se valida automáticamente.

- **Archivo plano bancario** para dispersión de sueldos. *(El cliente objetivo no lo necesita: paga en efectivo o por transferencia suelta.)*
- **Planilla PILA.** En su lugar, el resumen mensual con los IBC calculados para que el contador la haga en su operador (§10.1).
- **Transmisión del documento soporte de nómina a la DIAN** (§1.1). El modelado según el anexo técnico se mantiene, pero por otra razón: para que **el contador** pueda hacerlo, no nosotros.
- **Dispersión bancaria real**: mover plata desde la cuenta del cliente.
- **Tesorería, conciliación bancaria y flujo de caja.** Viven en el módulo contable consumiendo la nómina, no aquí.
- **Firma electrónica** de los contratos generados (§10.2) — producto regulado aparte, Ley 527.
- **Edición libre del cuerpo de las plantillas** de contrato: si el cliente necesita redactar, exporta `.docx`.
- **Emisión de la factura o del documento soporte en adquisiciones a no obligados a facturar** por cuenta del contratista. *(La liquidación del contratista sí entra, y va primera.)*
- **Portal del empleado, marcación de asistencia y gestión de desempeño.** Esto último es la línea que separa un mini-gestor de nómina de un ERP de recursos humanos.

---

## 12. Contrato con el backend

> Escrito desde el prototipo de calendario ya construido (`frontend/src/pages/payroll/`), que corre con estado local y datos de maqueta. Esta sección dice **qué tiene que entregar el backend** para reemplazarlo sin tocar las pantallas.

### 12.1 Lo que se almacena y lo que se deriva

Es la distinción que más fácil se pierde al conectar, y la que más caro cuesta equivocar: **si se almacena algo que debía derivarse, aparecen dos versiones de la verdad que tarde o temprano se contradicen.**

| Se **almacena** | Se **deriva**, nunca se guarda |
|---|---|
| Empleado y sus condiciones | Días trabajados |
| Novedades (rango, tipo, cantidad) | Horas de jornada por persona-día |
| Marcadores (horas extra) | Si el día fue laborable |
| Días que el negocio cerró | Si el día está liquidado |
| Anotaciones libres del día | Costo del día |
| Configuración de pago | Qué tramos de corte tocan un mes |
| Pagos y su cobertura (D-114) | El estado de un corte |

La regla que lo gobierna es **D-99**: nunca se registra presencia, solo la excepción. Todo lo de la columna derecha sale de aplicar esa resta.

### 12.2 Campos que el prototipo ya espera

Sobre el modelo de §4.4, esto es lo que el frontend consume hoy:

**Empleado**

| Campo | Para qué |
|---|---|
| `dailyCost` | Costo del día y total del período |
| `vacationBalance` | Saldo al conceder vacaciones (D-119) |
| `workerType` | `employee` \| `contractor` — el contratista no aparece en la grilla de días |

**Novedad**

| Campo | Nota |
|---|---|
| `start` / `end` | Rango; iguales cuando es de un día |
| `span` | `full_day` \| `half_day` \| `hours` |
| `hours` | **Obligatorio con `span: "hours"`** (D-118) |
| `attachmentName` | Soporte de incapacidad o permiso — el backend recibirá el archivo |

**Marcador** — solo horas extra (D-121); `quantity` son las horas, estructuradas y no solo dentro del texto del label. Bonificaciones y descuentos llegan por la liquidación, no por acá.

**Configuración** — `periodicity`, `cutDays`, `weekStartsOn`, `hoursPerDay`, `calcMode`.

### 12.3 Las tres costuras

Puntos donde el prototipo tiene hoy una implementación provisional y el backend entra a reemplazarla. Están marcados en el código.

| Costura | Hoy | Con backend |
|---|---|---|
| **`isSettledFor(employeeId, day)`** en `usePayrollCalendar.ts` | Devuelve si el corte cerró — igual para todos, así que el todo-o-nada de D-117 aún no distingue | Mira la **cobertura del pago** por persona (D-114). Es lo único que cambia para que la línea diga la verdad |
| **Festivos** en `payroll.mock.ts` | Lista fija de 2026 escrita a mano | Paquete de festivos colombianos o tabla propia — la Ley Emiliani mueve doce festivos al lunes y varios dependen de la Pascua |
| **Estado local** en `PayrollView.vue` | `ref`s sembrados del mock, solo el mes actual | Store de Pinia contra la API. **El shape ya coincide**: se sustituye la fuente, no las pantallas |

### 12.4 Lo que el prototipo muestra y todavía no es verdad

Honestidad sobre lo que se ve en pantalla, para que nadie lo tome por funcionalidad terminada:

- **El costo excluye a todo el que tenga novedad**, y eso legalmente es falso: las vacaciones se pagan, la incapacidad al 66,67% desde el tercer día, un permiso remunerado se paga. Es el motor legal, que por D-113 no existe — la UI lo rotula *"Referencial — sin reglas de ley todavía"*.
- **El conteo de días de vacaciones es de calendario, no de hábiles** (D-119).
- **El adjunto solo guarda el nombre del archivo**: no hay backend que lo reciba.
- **El saldo de vacaciones está sembrado**; el real sale de `EmployeeAccrual` (§5.4), que alimenta el cierre de período.
- **Solo el mes actual tiene datos.** Los demás quedan vacíos a propósito, para poder ver el estado vacío — que es el 90% de los casos reales.

### 12.5 Una trampa de implementación que se va a repetir

Encadenar diálogos de Reka (Radix) **cerrando uno y abriendo otro en el mismo tick** deja `pointer-events: none` pegado en el `body`: el modal que queda se ve pero no recibe clics.

**La solución que quedó (D-120): un solo diálogo montado a la vez.** Los diálogos van con `v-if` sobre un único estado; abrir uno desde otro es asignar el nombre y Vue desmonta el anterior antes de montar el nuevo. Nada de alternar props `open` con un retardo calculado a ojo —esa fue la primera corrección y dejaba 20 ms con dos diálogos vivos— y nada de "volver" al modal de abajo al cerrar: cerrar cierra, y quien quiera el anterior lo abre otra vez.

Aplica a cualquier pantalla del proyecto que encadene modales, no solo a Nómina. Regla corta: **si dos diálogos pueden estar montados al mismo tiempo, algo va a salir mal tarde o temprano.**

---

## 13. Registro de decisiones

Detalle completo en [07 — Decisiones y puntos abiertos](07-decisiones-y-puntos-abiertos.md).

| ID | Decisión |
|---|---|
| D-97 | El módulo de Nómina entra al roadmap post-MVP; corrige la exclusión genérica de [05 §5](05-alcance-mvp-y-flujos.md) |
| D-98 | `Employee` es entidad independiente, fuera del Directorio |
| D-99 | Captura **por excepción**, sin marcación de asistencia |
| D-100 | Ambas periodicidades con un solo algoritmo: mes acumulado menos lo ya liquidado |
| D-101 | El módulo **calcula** (no solo registra); parámetros legales versionados, cero valores en código |
| D-102 | v1 **no transmite** a la DIAN, pero modela los datos según el anexo técnico + aviso en la UI |
| D-103 | Jerarquía de configuración **negocio → empleado → período**; periodicidad **global sin override** en v1; ARL con **default global + override** |
| D-104 | El tipo de contrato laboral (indefinido / fijo / obra o labor) es **dato, no parámetro de cálculo**: los tres liquidan igual y solo difieren al terminar |
| D-105 | Cierra A-39: **prestación de servicios entra a v1 y es la primera rebanada**; se construye por rebanadas verticales por tipo de vinculación, no por capas |
| D-106 | **Generador de contratos desde plantilla** dentro del módulo, con límites duros: sin edición libre, sin firma electrónica, plantillas versionadas con revisión jurídica, documento generado inmutable |
| D-107 | **Techo de alcance permanente en el nivel 2** (preparar el pago). El nivel 3 —mover dinero, tesorería, conciliación— queda **descartado, no aplazado** |
| D-108 | **Refina D-107: el eje no es la cercanía al dinero sino el destinatario del artefacto.** Entran los **documentos para personas**; quedan fuera los **archivos máquina a máquina** (plano bancario, PILA, transmisión DIAN), cuya especificación define un tercero |
| D-109 | **Los documentos son el producto, el cálculo es el motor.** El generador de plantillas (§10) pasa de anexo a pieza central del módulo |
| D-110 | Amplía D-103: periodicidad **semanal / quincenal / mensual**, fijada en el wizard de arranque |
| D-111 | **Los días de corte los define el negocio** (ej. 5 y 20). Cruzar el fin de mes pasa a ser la norma, y un mes puede mostrar **tres tramos** de corte, no dos |
| D-112 | **Modelo de novedades en dos tablas** (`novelty_type` + `novelty`), con el vocabulario del anexo técnico DIAN. Sin `status`, sin aprobación, sin tabla por tipo: programación y presencia se **derivan** |
| D-113 | **`calc_mode: simple \| legal` por negocio.** El motor legal es una **capa de autorelleno** sobre la captura manual, no un reemplazo — mismo campo, mismo esquema |
| D-114 | **La unidad de liquidación es el pago, no el corte.** Se puede liquidar un rango arbitrario en cualquier momento; el corte queda como rango por defecto, ritmo del aviso y agrupación de reporte |
| D-115 | **El "..." actúa, la celda lee.** Detalle del día como modal; el avatar abre esa novedad. La grilla muestra excepciones, el detalle muestra a todo el equipo |
| D-116 | **Un solo modal para crear, editar y quitar.** Se autocompleta con lo registrado; "Laboró normal" o cantidad en 0 **quitan** la novedad |
| D-117 | **La línea describe el pago, no el corte**: primario = liquidado (todo o nada), gris medio = laborado, gris claro = por venir. **Con una persona enfocada, su novedad manda** y la línea toma el color del tipo |
| D-118 | **Horas de buena fe**: se asume jornada completa y solo las novedades la reducen. `hoursPerDay` configurable, nunca 8 fijo |
| D-119 | **Campos por contexto**: rango con mínimo en el día de entrada, adjunto en incapacidad y permiso, saldo de vacaciones con advertencia |
| D-120 | **Un solo diálogo montado a la vez** (`v-if`), sin retardo ni memoria del modal de abajo — cerrar cierra, y el anterior se abre otra vez si hace falta |
| D-121 | **Bonificación y descuento salen del calendario.** No son hechos de un día sino ajustes de un pago: se capturan al liquidar. En el día solo quedan las horas extra como marcador |

| ID | Punto abierto |
|---|---|
| A-34 | ¿El auxilio de transporte se suspende en incapacidad y vacaciones? |
| A-35 | Divisor de horas mes para el valor de la hora ordinaria bajo jornada de 42 h |
| A-36 | Exoneración de parafiscales (art. 114-1 ET): ¿configurable por negocio o asumida? |
| A-37 | Liquidación definitiva por terminación de contrato: ¿v1.5 o v2? |
| A-38 | Provisiones: ¿solo informativas, o se pagan desde el módulo en junio/diciembre? |
| ✅ A-39 | ¿Entra la **prestación de servicios** a v1? -> **RESUELTO** (D-105): sí, y va primero |
| A-40 | **Validación jurídica de las plantillas de contrato** — ¿quién las revisa y avala? Bloqueante para publicar §10 |
| A-41 | ¿Se implementa el **checklist de idoneidad** antes de generar un contrato de prestación de servicios? (protección real vs. fricción en un flujo que queremos rápido) |
| A-42 | Caso frontera de D-108: ¿el **certificado de ingresos y retenciones** (formulario 220) entra como documento para personas, o queda fuera por ser formato oficial de un tercero? |
| A-43 | **Pago diario** — cabe en el concepto actual mientras la plantilla sea estable. La frontera real es el **trabajo ocasional**, donde la ausencia deja de ser excepción |
| A-44 | **Solape de pagos: ¿se bloquea o se advierte?** Bloquea la implementación de D-114. Recomendación: **bloquear** — pagar dos veces el mismo día no tiene lectura legítima |
