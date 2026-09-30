# 01 — Requerimientos

**Estado:** Versión 1.0 — Etapa 0 · **Fecha:** 2026-09-04 · **Versión 1.1** — revisada en la auditoría de Etapa 0.1
**Fuente:** definición de alcance del proyecto entregada por el responsable.

## Cómo leer este documento

- Todo requisito deriva del alcance funcional declarado. **No se han inventado requisitos de negocio.**
- Cuando ha sido necesario un supuesto para poder formular un requisito, aparece marcado como
  **`SUPUESTO`** y está registrado en `knowledge/assumptions.md`. Un requisito así marcado enuncia una
  **necesidad real** cuyo **valor concreto** todavía no está confirmado: es el valor lo que es
  hipotético, no la necesidad. Si el negocio aporta otro valor, se ajusta el requisito sin rediseñar nada.
- Prioridad según MoSCoW: **Debe** (imprescindible para la primera versión útil) · **Debería**
  (importante, no bloqueante) · **Podría** (deseable) · **Futuro** (fuera de la primera versión).
- Los parámetros de negocio concretos (nivel de servicio objetivo, costos de faltante, políticas de
  compra) **no están definidos** y deberán ser aportados por el negocio; están marcados como
  pendientes en `knowledge/business-rules.md`.

### Convención de IDs

| Prefijo | Tipo |
|---|---|
| `RF-###` | Requisito funcional |
| `RNF-###` | Requisito no funcional |
| `RS-###` | Requisito de seguridad |
| `RML-###` | Requisito de Machine Learning |

---

## 1. Requisitos funcionales

### Dominio maestro

#### RF-001 — Administración de productos
- **Descripción:** El sistema debe permitir crear, consultar, actualizar y desactivar productos,
  identificados de forma única por SKU, con sus atributos maestros (nombre, descripción, unidad de
  medida, categoría, estado activo/inactivo).
- **Prioridad:** Debe
- **Criterio de aceptación:** Dado un usuario con permiso de escritura, cuando registra un producto
  con SKU no existente, el producto queda persistido y es recuperable por SKU y por identificador.
  Un SKU duplicado es rechazado con error de validación. La desactivación no elimina el histórico asociado.
- **Dependencias:** ninguna. La clasificación por categoría (`RF-002`, clase D) **enriquece** este
  requisito pero no lo condiciona: si RF-002 se retira, el producto conserva un atributo de categoría.

#### RF-002 — Administración de categorías
- **Descripción:** El sistema debe permitir clasificar productos en categorías para agregación,
  filtrado y análisis. `SUPUESTO`: jerarquía de un solo nivel en la primera versión (ASSUMPTION-009).
- **Clasificación:** `PROPUESTA` — las categorías no figuran en el alcance declarado. Se mantienen
  porque la agregación por categoría sostiene los indicadores de `RF-018` y el análisis de `RF-009`,
  pero **no son vinculantes**: si el negocio no clasifica su catálogo, basta un atributo en `RF-001`.
- **Prioridad:** Debería
- **Criterio de aceptación:** Un producto puede asociarse a una categoría; las consultas de inventario
  y predicción permiten filtrar y agregar por categoría.
- **Dependencias:** —

#### RF-005 — Administración de proveedores
- **Descripción:** El sistema debe permitir registrar y mantener proveedores con sus datos de
  identificación y su estado, y asociar qué productos suministra cada uno.
- **Prioridad:** Debe
- **Criterio de aceptación:** Un producto puede tener uno o varios proveedores; para cada relación
  producto–proveedor se pueden registrar condiciones propias (lead time acordado, MOQ, múltiplo de
  compra, costo unitario, si es proveedor preferente).
- **Dependencias:** RF-001

### Inventario y operación

#### RF-003 — Administración de inventarios
- **Descripción:** El sistema debe mantener el nivel de inventario vigente por producto y ubicación,
  incluyendo cantidad disponible y cantidad en tránsito.
  **PENDIENTE DE VALIDACIÓN — cantidad comprometida/reservada:** el alcance actual no contiene ningún
  proceso que genere compromisos (no hay órdenes de venta ni reservas), de modo que hoy ese dato no
  tendría origen. Se conserva en el modelo conceptual porque la posición de inventario lo requiere en
  cuanto exista tal proceso, pero **no se implementa mientras nadie lo alimente**.
- **Prioridad:** Debe
- **Criterio de aceptación:** Para cualquier producto se puede consultar su posición de inventario
  actual desglosada; el valor mostrado es consistente con la suma de los movimientos registrados.
- **Dependencias:** RF-001

#### RF-004 — Registro de movimientos de inventario
- **Descripción:** El sistema debe registrar cada movimiento que afecta al inventario (entrada por
  recepción, salida por consumo/venta, ajuste, devolución, traspaso), con fecha, cantidad, tipo,
  origen y referencia al documento que lo motivó.
- **Prioridad:** Debe
- **Criterio de aceptación:** El inventario vigente es reconstruible a partir del histórico de
  movimientos. Los movimientos son **inmutables**: una corrección se registra como un movimiento de
  ajuste nuevo, nunca modificando o borrando uno anterior.
- **Dependencias:** RF-001, RF-003

#### RF-006 — Registro de consumo / ventas
- **Descripción:** El sistema debe registrar el consumo o la venta histórica por producto y fecha,
  como insumo principal de la predicción de demanda.
- **Prioridad:** Debe
- **Criterio de aceptación:** Se puede consultar la serie temporal de consumo de un producto en un
  rango de fechas, con granularidad diaria agregable a semanal y mensual.
- **Dependencias:** RF-001

#### RF-007 — Registro de tiempos de entrega (lead time)
- **Descripción:** El sistema debe registrar, por relación producto–proveedor, el lead time acordado
  y los lead times **reales observados** (fecha de orden vs. fecha de recepción), permitiendo calcular
  su media y su variabilidad.
- **Prioridad:** Debe
- **Criterio de aceptación:** Para cada relación producto–proveedor con al menos una recepción
  registrada, el sistema expone lead time medio observado, desviación y número de observaciones,
  y distingue este valor del lead time acordado.
- **Dependencias:** RF-005, RF-008

#### RF-008 — Registro de órdenes de compra
- **Descripción:** El sistema debe permitir registrar órdenes de compra con su cabecera (proveedor,
  fechas de emisión, esperada y de recepción, estado) y sus líneas (producto, cantidad pedida,
  cantidad recibida, costo unitario).
- **Prioridad:** Debe
- **Criterio de aceptación:** Una orden puede recorrer los estados definidos (borrador, emitida,
  parcialmente recibida, recibida, cancelada); las cantidades pedidas y no recibidas de órdenes
  vigentes constituyen el **inventario en tránsito** usado por RF-012.
- **Dependencias:** RF-005, RF-001

### Análisis, predicción y decisión

#### RF-009 — Análisis de históricos
- **Descripción:** El sistema debe permitir analizar el histórico de consumo e inventario por
  producto: serie temporal, estadísticos descriptivos, variabilidad, periodos sin movimiento y
  detección de valores atípicos.
- **Prioridad:** Debe
- **Criterio de aceptación:** Para un producto y un rango de fechas, el sistema devuelve la serie
  agregada a la granularidad solicitada junto con media, desviación, coeficiente de variación y
  número de periodos con demanda cero.
- **Dependencias:** RF-006

#### RF-010 — Predicción de demanda futura
- **Descripción:** El sistema debe generar una predicción de demanda por producto para un horizonte
  definido, incluyendo una medida de incertidumbre.
- **Prioridad:** Debe
- **Criterio de aceptación:** Para un producto con histórico suficiente, el sistema devuelve la
  demanda estimada por periodo dentro del horizonte, un intervalo de predicción, la versión del
  modelo utilizado y la fecha de generación. Si el histórico es insuficiente, devuelve el resultado
  del método de respaldo indicándolo explícitamente.
- **Dependencias:** RF-006, RML-001

#### RF-011 — Cálculo de stock de seguridad
- **Descripción:** El sistema debe calcular el stock de seguridad por producto considerando la
  variabilidad de la demanda, la variabilidad del lead time y un nivel de servicio objetivo.
- **Prioridad:** Debe
- **Criterio de aceptación:** El cálculo es determinístico y reproducible; se documentan la fórmula
  aplicada, sus parámetros y su origen (`docs/06-motor-abastecimiento.md`). El nivel de servicio
  objetivo es configurable y **debe ser definido por el negocio** (pendiente de validación).
- **Dependencias:** RF-007, RF-009

#### RF-012 — Cálculo del punto de reorden
- **Descripción:** El sistema debe calcular el punto de reorden por producto como demanda esperada
  durante el lead time más stock de seguridad, y compararlo con la **posición de inventario de decisión**
  (`existencia física + tránsito efectivo − comprometido`, `docs/06` §4.2). **No** se usa el
  inventario *disponible* en esta suma: disponible ya descuenta lo comprometido, y sumarlo así lo
  restaría dos veces.
- **Prioridad:** Debe
- **Criterio de aceptación:** Dado un producto con inventario, lead time y predicción disponibles,
  el sistema indica si la posición de inventario está por debajo del punto de reorden y expone
  todos los términos intermedios del cálculo.
- **Dependencias:** RF-003, RF-007, RF-010, RF-011

#### RF-013 — Cálculo de riesgo de desabasto
- **Descripción:** El sistema debe estimar el riesgo de quedar sin inventario en el horizonte
  considerado y clasificarlo en niveles interpretables.
- **Prioridad:** Debe
- **Criterio de aceptación:** Para cada producto evaluado el sistema entrega un indicador de riesgo,
  su nivel (p. ej. crítico / alto / medio / bajo), la fecha estimada de agotamiento y los días de
  cobertura restantes. Los umbrales de clasificación son configurables y están **pendientes de
  validación por el negocio**.
- **Dependencias:** RF-010, RF-012

#### RF-014 — Detección de riesgo de sobreinventario
- **Descripción:** El sistema debe identificar productos cuyo inventario excede significativamente
  la demanda proyectada en el horizonte, señalando exceso de cobertura y capital inmovilizado.
- **Prioridad:** Debe
- **Criterio de aceptación:** El sistema lista los productos con cobertura superior al umbral
  configurado, indicando la cobertura en días y la cantidad excedente estimada.
- **Dependencias:** RF-010, RF-003

#### RF-015 — Generación de recomendaciones de compra
- **Descripción:** El sistema debe generar recomendaciones de compra que indiquen producto, cantidad
  sugerida, proveedor sugerido, fecha sugerida de emisión y urgencia, respetando restricciones del
  proveedor (MOQ, múltiplo de compra) cuando estén registradas.
- **Prioridad:** Debe
- **Criterio de aceptación:** Cada recomendación es **explicable**: expone el forecast utilizado y su
  versión de modelo, el inventario considerado, el lead time aplicado, el stock de seguridad, el
  punto de reorden y las restricciones aplicadas. Recalcular con los mismos insumos produce el mismo resultado.
- **Dependencias:** RF-010, RF-011, RF-012, RF-005
- **Restricción:** La recomendación **nunca ejecuta una compra**. La decisión final es humana.

#### RF-016 — Evaluación de comportamiento de proveedores
- **Clasificación:** `PROPUESTA`. El alcance declarado pide *administrar proveedores* y *registrar
  tiempos de entrega*, no evaluar su desempeño. La parte técnicamente necesaria —media y variabilidad
  del lead time observado, que alimentan el stock de seguridad— **ya está cubierta por RF-007**. El
  resto (cumplimiento en tiempo y en cantidad) es un indicador de gestión que nadie solicitó.
  **No es vinculante** hasta que el negocio lo confirme.
- **Descripción:** El sistema podría calcular indicadores de desempeño por proveedor a partir del
  histórico de órdenes: cumplimiento en tiempo, cumplimiento en cantidad, lead time medio y su variabilidad.
- **Prioridad:** Podría
- **Criterio de aceptación:** Para un proveedor con órdenes recibidas, el sistema expone porcentaje
  de entregas a tiempo, desviación media respecto a la fecha comprometida y variabilidad del lead time.
- **Dependencias:** RF-008, RF-007

### Presentación e interacción

#### RF-017 — Interfaz web
- **Descripción:** El sistema debe ofrecer una interfaz web que permita consultar productos,
  inventario, proveedores, predicciones, recomendaciones y riesgos.
- **Prioridad:** Debe
- **Criterio de aceptación:** Las vistas definidas en `docs/08-frontend.md` son navegables y muestran
  datos provenientes de la API. La parte del criterio relativa a **respetar los permisos del rol
  autenticado solo es verificable a partir de la Fase 8**, cuando existe autenticación real; durante la
  Fase 7 se trabaja con autenticación simulada y ese criterio queda explícitamente diferido.
- **Dependencias:** RF-001…RF-015, RS-001 (este último para la verificación completa del criterio)

#### RF-018 — Indicadores en Power BI
- **Descripción:** El sistema debe exponer datos aptos para su explotación en Power BI mediante
  vistas o modelos analíticos que soporten los KPIs definidos.
- **Prioridad:** Debería
- **Criterio de aceptación:** Existen objetos de datos documentados en `docs/11-power-bi.md` que
  permiten construir los KPIs de inventario, abastecimiento, proveedores y predicción sin lógica de
  negocio duplicada en el informe.
- **Dependencias:** RF-003, RF-010, RF-015

#### RF-019 — Explicaciones mediante IA generativa
- **Descripción:** El sistema debe generar explicaciones en lenguaje natural de las recomendaciones,
  riesgos y predicciones, a partir de cifras **ya calculadas** por el motor de abastecimiento.
- **Prioridad:** Debería
- **Criterio de aceptación:** La explicación es coherente con los valores entregados y no introduce
  cifras nuevas ni distintas de las recibidas. Toda respuesta indica su origen. Ver `docs/09-ia-generativa.md`.
- **Dependencias:** RF-015
- **Restricción:** Prohibido que el LLM realice cálculos determinísticos de inventario (ver RS-010).

#### RF-020 — Recuperación de información documental (Azure AI Search)
- **Descripción:** El sistema debe permitir consultar conocimiento documental de la organización
  (políticas de compra, contratos, manuales, catálogos de proveedores) mediante búsqueda e
  incorporarlo como contexto en las respuestas del asistente.
- **Prioridad:** Podría
- **Criterio de aceptación:** Una consulta en lenguaje natural devuelve fragmentos relevantes con
  **cita de su documento de origen**; las respuestas del asistente basadas en documentos incluyen esa referencia.
- **`SUPUESTO` determinante:** este requisito presupone que **existe documentación interna indexable**
  (ASSUMPTION-008, el supuesto de mayor riesgo del proyecto). Si no existe, el requisito no es
  realizable tal como está enunciado y debe replantearse el papel de Azure AI Search.
- **Dependencias:** ninguna sobre RF-019. La recuperación documental es independiente de la generación
  de explicaciones, y así lo refleja el roadmap (Fase 9 precede a Fase 10).

#### RF-021 — Asistente conversacional
- **Clasificación:** `PROPUESTA — PENDIENTE DE VALIDACIÓN`. El alcance pide *proporcionar explicaciones
  mediante Azure OpenAI* (`RF-019`), no una interfaz conversacional. Además, `CLAUDE.md` §1 afirma
  explícitamente que el sistema **no es un chatbot**, lo que sitúa este requisito en tensión con el
  propio principio del proyecto. Se conserva como opción **no vinculante**; si el negocio no lo
  solicita, se reduce a una superficie de consulta de `RF-020` o se retira.
- **Descripción:** El sistema podría ofrecer una interfaz conversacional que responda preguntas sobre
  el estado de inventario, riesgos y recomendaciones, obteniendo los datos de la API y no de la
  memoria del modelo.
- **Prioridad:** Podría
- **Criterio de aceptación:** El asistente responde únicamente con información obtenida de fuentes
  del sistema, respeta los permisos del usuario y responde "no dispongo de ese dato" cuando la
  información no está disponible.
- **Dependencias:** RF-019, RF-020, RS-004

### Datos y trazabilidad

#### RF-022 — Ingesta de datos
- **Descripción:** El sistema debe permitir cargar datos históricos y maestros desde archivos
  estructurados, con validación y reporte de errores, sin que el resto del sistema deba conocer el origen.
- **Prioridad:** Debe
- **Criterio de aceptación:** Una carga con registros inválidos reporta las filas rechazadas y su
  motivo, y no deja el sistema en estado inconsistente.
- **Dependencias:** RF-001, RF-006

#### RF-023 — Sustitución de datos sintéticos por datos reales
- **Descripción:** Los datos sintéticos usados en las primeras fases deben poder sustituirse por
  datos reales **sin rediseñar la aplicación**: mismo esquema, mismos contratos, misma lógica.
- **Prioridad:** Debe
- **Criterio de aceptación:** El origen de datos se marca a nivel de registro o de carga
  (`sintético` / `real`) y ninguna regla de negocio depende de que los datos sean sintéticos.
- **Dependencias:** RF-022
- **Relacionado:** ASSUMPTION-001

#### RF-024 — Trazabilidad de recomendaciones y predicciones
- **Descripción:** El sistema debe conservar el histórico de predicciones y recomendaciones
  generadas, con sus insumos y la versión de modelo utilizada.
- **Prioridad:** Debe
- **Criterio de aceptación:** Es posible reconstruir por qué el sistema recomendó una cantidad
  determinada en una fecha pasada, aunque el modelo se haya actualizado desde entonces.
- **Dependencias:** RF-010, RF-015

---

## 2. Requisitos no funcionales

#### RNF-001 — Separación de responsabilidades
- **Descripción:** Predicción (ML), reglas de abastecimiento e IA generativa deben residir en
  módulos independientes, con interfaces explícitas y sin dependencias cruzadas indebidas.
- **Prioridad:** Debe
- **Criterio de aceptación:** El motor de abastecimiento es ejecutable y testeable sin el modelo de
  ML (recibe un forecast como entrada) y sin ningún servicio de IA generativa.

#### RNF-002 — Reproducibilidad y determinismo
- **Descripción:** Con las mismas entradas y los mismos parámetros, los cálculos de abastecimiento
  deben producir siempre el mismo resultado.
- **Prioridad:** Debe
- **Criterio de aceptación:** Las pruebas del motor verifican salidas exactas; no interviene
  aleatoriedad no sembrada ni ningún LLM en la ruta de cálculo.

#### RNF-003 — Rendimiento de consulta
- **Descripción:** Las consultas interactivas de la interfaz deben responder en un tiempo aceptable
  para uso operativo. `SUPUESTO` (ASSUMPTION-011): objetivo inicial p95 < 2 s para listados
  paginados y detalle de producto, sobre el volumen definido en RNF-004.
- **Prioridad:** Debería
- **Criterio de aceptación:** Medición en pruebas de rendimiento sobre datos sintéticos representativos.

#### RNF-004 — Volumen de referencia
- **Descripción:** `SUPUESTO` (ASSUMPTION-012). Volumen de diseño inicial, a validar con el negocio:
  ~5.000 SKU activos, ~50 proveedores, 24–36 meses de histórico diario y hasta 3 ubicaciones, de las
  cuales la primera versión opera con una o con el inventario agregado (ASSUMPTION-006).
- **Prioridad:** Debería
- **Criterio de aceptación:** El sistema opera dentro de los objetivos de rendimiento con ese volumen.
  Un volumen mayor exige revisar el diseño, no romperlo.

#### RNF-005 — Ejecución del cálculo masivo
- **Clasificación:** B (derivado). Lo **necesario** es recalcular todo el catálogo (RF-010 y RF-015
  aplican a todos los productos, no a uno). Que se haga como proceso programado y separado de la API
  es la forma más simple de conseguirlo, no una exigencia añadida.
- **Descripción:** El recálculo de predicciones y recomendaciones para todo el catálogo debe poder
  ejecutarse sin bloquear la operación interactiva.
- **Prioridad:** Debe
- **Criterio de aceptación:** El proceso masivo se ejecuta de forma independiente de la API y su
  resultado queda persistido para consulta.

#### RNF-006 — Portabilidad y entorno reproducible
- **Descripción:** El sistema debe poder levantarse en local mediante contenedores, sin dependencia
  de servicios reales de Azure para el núcleo funcional.
- **Prioridad:** Debe
- **Criterio de aceptación:** Con Docker instalado, un desarrollador nuevo levanta backend, base de
  datos y frontend siguiendo la documentación; las integraciones de Azure usan implementaciones
  sustitutas locales.

#### RNF-007 — Mantenibilidad
- **Descripción:** Código tipado, formateado y verificado automáticamente; documentación actualizada
  con cada decisión técnica.
- **Prioridad:** Debe
- **Criterio de aceptación:** El pipeline de CI falla si el formato, el linting o el tipado no cumplen.

#### RNF-008 — Observabilidad
- **Descripción:** El sistema debe emitir logs estructurados, métricas básicas de uso y errores, y
  registrar la ejecución de los procesos de predicción y recomendación.
- **Clasificación:** `PROPUESTA` (clase D, `§5`) — **no vinculante**. Buena práctica que el equipo desea conservar; la observabilidad no figura en el alcance declarado.
- **Prioridad:** Debería
- **Criterio de aceptación:** Ante un fallo en producción es posible identificar petición, usuario
  (por identificador, no por datos personales), operación y causa.

#### RNF-009 — Disponibilidad
- **Descripción:** `SUPUESTO` (ASSUMPTION-013): sistema de apoyo a la decisión en horario laboral;
  no se requiere alta disponibilidad 24/7 en la primera versión. A validar con el negocio.
- **Prioridad:** Podría
- **Criterio de aceptación:** Objetivo de disponibilidad acordado y documentado antes del despliegue productivo.

#### RNF-010 — Degradación controlada
- **Descripción:** La indisponibilidad del modelo de ML, de Azure OpenAI o de Azure AI Search no debe
  impedir el funcionamiento del núcleo (inventario, reglas de abastecimiento).
- **Prioridad:** Debe
- **Criterio de aceptación:** Sin modelo disponible el sistema usa el baseline y lo señala; sin IA
  generativa la interfaz muestra los datos sin explicación narrativa, sin error bloqueante.

#### RNF-011 — Internacionalización de contenido
- **Descripción:** Interfaz y documentación de negocio en español; código, identificadores y esquema
  de base de datos en inglés.
- **Clasificación:** `PROPUESTA` (clase D, `§5`) — **no vinculante**. Es una convención de desarrollo (`CLAUDE.md` §9, `DT-017`), no un requisito del sistema.
- **Prioridad:** Debería
- **Criterio de aceptación:** Consistencia verificada en revisión de código.

#### RNF-012 — Usabilidad para el rol planificador
- **Descripción:** La interfaz debe permitir a un planificador identificar en una sola vista los
  productos que requieren acción, ordenados por urgencia. `SUPUESTO`: la existencia del rol
  *planificador* no está confirmada por el negocio (ASSUMPTION-010).
- **Prioridad:** Debería
- **Criterio de aceptación:** El dashboard presenta la lista de productos críticos priorizada, con
  acceso directo al detalle y a la explicación de cada recomendación.

#### RNF-013 — Auditabilidad de datos
- **Clasificación:** B (derivado de RF-024). Reconstruir por qué el sistema recomendó una cantidad en
  una fecha pasada exige que el histórico sobre el que se calculó **no haya cambiado desde entonces**.
  Sin inmutabilidad, la trazabilidad exigida por RF-024 y la reproducibilidad de RML-009 son imposibles.
  No es una política de auditoría añadida: es la condición que las hace ciertas.
- **Descripción:** Los movimientos de inventario y las órdenes de compra son registros históricos
  inmutables; las correcciones se realizan mediante nuevos registros.
- **Prioridad:** Debe
- **Criterio de aceptación:** No existen operaciones de borrado físico sobre datos históricos en la
  lógica de aplicación.

---

## 3. Requisitos de seguridad

#### RS-001 — Autenticación con Microsoft Entra ID
- **Descripción:** El acceso a la aplicación y a la API debe autenticarse mediante Microsoft Entra ID.
- **Prioridad:** Debe
- **Criterio de aceptación:** Una petición sin token válido a un endpoint protegido devuelve 401.
  El backend valida firma, emisor, audiencia y expiración del token.
- **Dependencias:** —

#### RS-002 — Autorización basada en roles
- **Descripción:** El sistema debe aplicar control de acceso por roles. Roles conceptuales iniciales:
  `ADMIN`, `PLANNER`, `ANALYST`, `VIEWER`. **Pendiente de validación** con el negocio.
- **Prioridad:** Debe
- **Criterio de aceptación:** Un usuario sin el rol requerido recibe 403; la comprobación ocurre en
  el backend y es independiente de lo que oculte la interfaz.
- **Dependencias:** RS-001

#### RS-003 — Validación en el servidor
- **Descripción:** Toda comprobación de permisos y toda validación de entrada deben realizarse en el
  backend, con independencia de las validaciones del frontend.
- **Prioridad:** Debe
- **Criterio de aceptación:** Peticiones construidas manualmente que omitan el frontend son
  igualmente rechazadas.

#### RS-004 — Aplicación de permisos al asistente de IA
- **Descripción:** El asistente conversacional y el flujo RAG no deben exponer información a la que
  el usuario autenticado no tendría acceso por la vía normal.
- **Prioridad:** Debe
- **Criterio de aceptación:** La recuperación de datos y documentos se filtra por la identidad y el
  rol del usuario que consulta.
- **Dependencias:** RS-002, RF-020

#### RS-005 — Gestión de secretos
- **Descripción:** Ningún secreto, clave, token, certificado ni cadena de conexión con credenciales
  puede almacenarse en el repositorio.
- **Prioridad:** Debe
- **Criterio de aceptación:** El repositorio solo contiene `.env.example` con valores ficticios; el
  CI incluye detección de secretos y falla si detecta uno.

#### RS-006 — Configuración por entorno
- **Descripción:** La configuración sensible se obtiene de variables de entorno y, en los entornos
  desplegados, de un **almacén de secretos gestionado**. Azure Key Vault es el candidato natural por
  coherencia con el stack, pero **no figura en la lista de tecnologías obligatorias** y por tanto no se
  fija aquí: ver `DT-022` (`PROPUESTA`). El diseño se expresa contra la interfaz `SecretProvider`.
- **Prioridad:** Debe
- **Criterio de aceptación:** Cambiar de entorno no exige modificar código.

#### RS-007 — Acceso a la base de datos con privilegio mínimo
- **Descripción:** La aplicación accede a PostgreSQL con un usuario de privilegios mínimos, distinto
  del propietario del esquema; las migraciones usan una credencial separada.
- **Clasificación:** `PROPUESTA` (clase D, `§5`) — **no vinculante**. Endurecimiento de despliegue recomendable; no deriva del alcance 19.
- **Prioridad:** Debería
- **Criterio de aceptación:** El usuario de aplicación no puede alterar el esquema.

#### RS-008 — Cifrado en tránsito
- **Descripción:** Toda comunicación entre componentes y con servicios externos debe usar TLS.
- **Prioridad:** Debe
- **Criterio de aceptación:** No se admite HTTP plano en entornos desplegados.

#### RS-009 — Auditoría de acciones sensibles
- **Descripción:** El sistema debe registrar quién ejecutó acciones sensibles (cambios de política,
  aprobación de recomendaciones, cargas de datos, cambios de rol) con marca de tiempo.
- **Clasificación:** `PROPUESTA` (clase D, `§5`) — **no vinculante**. El registro de auditoría no fue solicitado. Además, «aprobación de recomendaciones» y «cambios de política» presuponen flujos que el alcance no define.
- **Prioridad:** Debería
- **Criterio de aceptación:** El registro de auditoría es consultable y no modificable desde la aplicación.

#### RS-010 — Restricción del uso del LLM
- **Descripción:** El LLM no debe generar cifras de inventario, cantidades a comprar, puntos de
  reorden ni stock de seguridad, ni ejecutar acciones de escritura sobre el sistema.
- **Prioridad:** Debe
- **Criterio de aceptación:** Las cifras presentes en cualquier respuesta generada provienen de la
  API y son verificables contra ella. Existe una prueba que detecta cifras no presentes en el contexto entregado.
- **Dependencias:** RF-019

#### RS-011 — Protección frente a inyección de prompt
- **Descripción:** El contenido recuperado de documentos y los datos de entrada del usuario deben
  tratarse como **datos**, nunca como instrucciones para el modelo.
- **Prioridad:** Debe
- **Criterio de aceptación:** El contexto recuperado se delimita y se marca como no ejecutable en el
  prompt; existen casos de prueba con contenido malicioso incrustado.

#### RS-012 — Protección de datos en entornos no productivos
- **Descripción:** No se utilizan datos reales de negocio en desarrollo ni en pruebas sin anonimización aprobada.
- **Clasificación:** `PROPUESTA` (clase D, `§5`) — **no vinculante**. Hoy es además vacua: no hay datos reales (ASSUMPTION-001). «Anonimización aprobada» presupone un proceso de gobierno que nadie ha definido.
- **Prioridad:** Debería
- **Criterio de aceptación:** Los entornos no productivos usan datos sintéticos identificados como tales.

#### RS-013 — Gestión de dependencias
- **Clasificación:** dividida. **Fijar las versiones** es clase B (deriva de la reproducibilidad que
  exigen RNF-002 y RML-009). El **análisis automático de vulnerabilidades** es clase D: el alcance 20
  pide pruebas y CI/CD, no seguridad de la cadena de suministro. **No vinculante.**
- **Descripción:** Las dependencias deben estar fijadas por versión. Además, podrían revisarse
  automáticamente en busca de vulnerabilidades conocidas.
- **Prioridad:** Debería
- **Criterio de aceptación:** El CI ejecuta análisis de vulnerabilidades y reporta hallazgos críticos.

---

## 4. Requisitos de Machine Learning

#### RML-001 — Objetivo de predicción
- **Descripción:** La primera versión debe predecir la **demanda futura por producto (SKU)**.
  Variable objetivo: cantidad demandada por periodo. Granularidad, unidad temporal y horizonte
  se definen en `docs/05-motor-predictivo.md`.
- **Prioridad:** Debe
- **Criterio de aceptación:** El sistema produce, para cada SKU con histórico suficiente, la demanda
  estimada por periodo dentro del horizonte definido.

#### RML-002 — Baseline obligatorio
- **Descripción:** Debe existir un baseline simple e interpretable, siempre disponible, contra el
  cual se compara todo modelo candidato.
- **Prioridad:** Debe
- **Criterio de aceptación:** Ningún modelo se promueve a producción si no supera al baseline en la
  métrica primaria sobre el conjunto de validación temporal.

#### RML-003 — Validación temporal
- **Descripción:** La evaluación debe usar validación temporal (*rolling origin* / backtesting),
  nunca partición aleatoria.
- **Prioridad:** Debe
- **Criterio de aceptación:** Los conjuntos de entrenamiento y evaluación están separados por fecha
  de corte y el procedimiento está documentado y es reproducible.

#### RML-004 — Ausencia de fuga de información
- **Descripción:** Ninguna característica puede incorporar información no disponible en el momento
  de la predicción.
- **Prioridad:** Debe
- **Criterio de aceptación:** Existe una prueba automatizada que verifica el alineamiento temporal
  de las características respecto al instante de predicción.

#### RML-005 — Métricas y criterios de aceptación declarados
- **Descripción:** Las métricas de evaluación y sus umbrales deben declararse antes del
  entrenamiento y reportarse siempre junto al baseline.
- **Prioridad:** Debe
- **Criterio de aceptación:** El informe de evaluación incluye métrica primaria, métricas
  secundarias, resultado del baseline y decisión de aceptación o rechazo.

#### RML-006 — Cuantificación de la incertidumbre
- **Descripción:** La predicción debe acompañarse de una medida de incertidumbre utilizable por el
  motor de abastecimiento para el cálculo del stock de seguridad.
- **Prioridad:** Debe
- **Criterio de aceptación:** Cada predicción incluye un intervalo o una estimación del error, y el
  motor la consume de forma explícita.
- **Dependencias:** RF-011

#### RML-007 — Tratamiento de series con datos insuficientes
- **Descripción:** El sistema debe definir y aplicar un tratamiento explícito para productos nuevos,
  con histórico corto o con demanda intermitente.
- **Prioridad:** Debe
- **Criterio de aceptación:** Todo SKU obtiene una estimación por alguna vía documentada (modelo,
  método específico o baseline), y la salida indica cuál se utilizó y con qué nivel de confianza.

#### RML-008 — Versionado de modelos
- **Descripción:** Todo modelo utilizado en producción debe tener versión identificable, con sus
  métricas, datos de entrenamiento y fecha registrados.
- **Prioridad:** Debe
- **Criterio de aceptación:** Cada predicción almacenada referencia la versión de modelo que la
  generó, y esa versión es recuperable.
- **Dependencias:** RF-024

#### RML-009 — Reproducibilidad del entrenamiento
- **Descripción:** El entrenamiento debe ser reproducible: semilla, versión de datos, versión de
  código, hiperparámetros y entorno registrados.
- **Prioridad:** Debe
- **Criterio de aceptación:** Reejecutar el entrenamiento con los mismos insumos produce métricas
  equivalentes dentro de una tolerancia declarada.

#### RML-010 — Monitoreo y detección de deriva
- **Descripción:** El sistema debe monitorear la calidad de las predicciones en producción y detectar
  deriva de datos y de desempeño.
- **Clasificación:** `PROPUESTA` (clase D, `§5`) — **no vinculante**. Capacidad de MLOps no solicitada. Sin datos reales ni umbrales del negocio no es implementable todavía.
- **Prioridad:** Debería
- **Criterio de aceptación:** Existen métricas de error calculadas contra la demanda real observada y
  alertas cuando se superan los umbrales definidos.
- **Dependencias:** RML-005

#### RML-011 — Reentrenamiento
- **Descripción:** Debe existir un procedimiento definido de reentrenamiento (programado y por
  disparo ante deriva) con validación previa a la promoción.
- **Clasificación:** `PROPUESTA` (clase D, `§5`) — **no vinculante**. Proceso no solicitado; depende enteramente de RML-010, también clase D.
- **Prioridad:** Debería
- **Criterio de aceptación:** Un modelo reentrenado solo sustituye al vigente si supera al modelo en
  producción y al baseline en la evaluación.
- **Dependencias:** RML-010

#### RML-012 — Separación entre predicción y decisión
- **Descripción:** El modelo entrega demanda estimada e incertidumbre; **no** entrega cantidades a
  comprar ni decisiones de abastecimiento.
- **Prioridad:** Debe
- **Criterio de aceptación:** La interfaz del módulo de predicción no expone ninguna operación de
  decisión de compra.
- **Dependencias:** RNF-001

---

## 5. Clasificación de los requisitos por origen

*Añadida en la revisión de Etapa 0.1.* Todos los requisitos tienen el mismo formato, pero **no todos
tienen la misma autoridad**. Esta tabla dice de dónde viene cada uno.

| Clase | Significado | Fuerza normativa |
|---|---|---|
| **A — SOLICITADO** | Corresponde directamente a un punto del alcance declarado | **Vinculante** |
| **B — DERIVADO** | No está literalmente en el alcance, pero es técnicamente necesario para cumplir uno que sí lo está | **Vinculante** |
| **C — SUPUESTO** | Su contenido depende de un valor o hecho no confirmado por el negocio | Vinculante **la necesidad**, no el valor |
| **D — PROPUESTA** | Elección de diseño defendible, no exigida por el alcance ni necesaria técnicamente | **No vinculante** hasta validación |

**Regla:** un requisito de clase D **no obliga**. Puede retirarse sin incumplir el alcance. Aparece
aquí porque el equipo lo considera buena práctica, no porque alguien lo haya pedido.

### Requisitos funcionales

| ID | Clase | Origen |
|---|---|---|
| RF-001 | A | Alcance 1 — administrar productos |
| RF-002 | **D** | Categorías no figuran en el alcance; sostiene la agregación de RF-018 |
| RF-003 | A | Alcance 2 — administrar inventarios (salvo *reservado*, pendiente) |
| RF-004 | A | Alcance 3 — registrar movimientos |
| RF-005 | A | Alcance 5 — administrar proveedores |
| RF-006 | A | Alcance 4 — registrar consumo/ventas |
| RF-007 | A | Alcance 6 — registrar tiempos de entrega |
| RF-008 | A | Alcance 7 — registrar órdenes de compra |
| RF-009 | A | Alcance 8 — analizar históricos |
| RF-010 | A | Alcance 9 — predecir demanda futura |
| RF-011 | A | Alcance 13 — calcular stock de seguridad |
| RF-012 | A | Alcance 12 — calcular puntos de reorden |
| RF-013 | A | Alcance 10 — riesgo de desabasto |
| RF-014 | A | Alcance 11 — riesgo de sobreinventario |
| RF-015 | A | Alcance 14 — recomendaciones de compra |
| RF-016 | **D** | Desempeño de proveedor no solicitado; lo necesario ya está en RF-007 |
| RF-017 | A | Alcance 15 — interfaz web |
| RF-018 | A | Alcance 16 — indicadores en Power BI |
| RF-019 | A | Alcance 17 — explicaciones con Azure OpenAI |
| RF-020 | A + C | Alcance 18 — Azure AI Search; condicionado por ASSUMPTION-008 |
| RF-021 | **D** | Conversación no solicitada; en tensión con "no es un chatbot" |
| RF-022 | B | Sin ingesta no hay históricos que analizar ni predecir (alcance 4, 8, 9) |
| RF-023 | B | Deriva del uso declarado de datos sintéticos sustituibles |
| RF-024 | B | Sin el forecast que la originó, una recomendación pasada no es explicable (RF-015) |

### Requisitos no funcionales

| ID | Clase | Origen |
|---|---|---|
| RNF-001 | A | Principio arquitectónico declarado en el alcance |
| RNF-002 | B | Sin determinismo, los cálculos 12–14 no son verificables ni testeables |
| RNF-003 | **C** | Objetivo p95 < 2 s no aportado por el negocio (ASSUMPTION-011) |
| RNF-004 | **C** | Volumen de referencia no aportado por el negocio (ASSUMPTION-012) |
| RNF-005 | B | Recalcular todo el catálogo es necesario; el proceso programado es la forma más simple |
| RNF-006 | B | Docker es stack obligatorio; el CI exige ejecución sin credenciales de Azure |
| RNF-007 | A | Alcance 20 — automatizar pruebas y calidad |
| RNF-008 | **D** | Observabilidad no solicitada. Se conserva como buena práctica |
| RNF-009 | **C** | Nivel de disponibilidad no confirmado (ASSUMPTION-013) |
| RNF-010 | B | Consecuencia de depender de servicios externos y de la separación de capas |
| RNF-011 | **D** | Convención de idioma: pertenece a `CLAUDE.md`, no a los requisitos |
| RNF-012 | **C** | Presupone el rol *planificador* (ASSUMPTION-010) |
| RNF-013 | B | Sin histórico inmutable, la trazabilidad de RF-024 y la reproducibilidad de RML-009 son imposibles |

### Requisitos de seguridad

| ID | Clase | Origen |
|---|---|---|
| RS-001 | A | Alcance 19 — proteger el acceso con Entra ID |
| RS-002 | **C** | Los cuatro roles concretos no están confirmados (ASSUMPTION-010) |
| RS-003 | B | Sin validación en servidor, la protección del alcance 19 es inefectiva |
| RS-004 | B | Necesario para que los puntos 17 y 18 no eludan la protección del 19 |
| RS-005 | B | Repositorio en GitHub, CI/CD y credenciales de Azure lo exigen |
| RS-006 | B + D | La configuración por entorno es derivada; el almacén concreto es propuesta (`DT-022`) |
| RS-007 | **D** | Privilegio mínimo en base de datos: endurecimiento no solicitado |
| RS-008 | B | TLS es imprescindible para transportar tokens de Entra ID |
| RS-009 | **D** | Registro de auditoría no solicitado |
| RS-010 | A | Consecuencia directa del principio declarado: la IA generativa no calcula |
| RS-011 | B | El RAG del alcance 18 obliga a tratar el contenido recuperado como datos |
| RS-012 | **D** | Política de anonimización: gobierno de datos no definido por nadie |
| RS-013 | B + D | Fijar versiones es derivado (reproducibilidad); el escaneo de vulnerabilidades es propuesta |

### Requisitos de Machine Learning

| ID | Clase | Origen |
|---|---|---|
| RML-001 | A | Alcance 9 — predecir demanda por SKU |
| RML-002 | B | Sin baseline no puede afirmarse que la predicción aporte nada |
| RML-003 | B | La validación aleatoria invalidaría cualquier resultado en series temporales |
| RML-004 | B | Con fuga temporal, la predicción sería falsa por construcción |
| RML-005 | B | Sin métrica previa no hay criterio de aceptación posible |
| RML-006 | B | El stock de seguridad del alcance 13 requiere una medida de incertidumbre |
| RML-007 | B | Sin ello, los SKU nuevos no obtendrían reorden ni recomendación |
| RML-008 | B | Azure ML es stack obligatorio; sin versión no hay explicación reconstruible |
| RML-009 | B | Sin reproducibilidad, versiones y métricas no significan nada |
| RML-010 | **D** | Monitoreo de deriva: capacidad de MLOps no solicitada |
| RML-011 | **D** | Reentrenamiento automatizado: proceso no solicitado; depende de RML-010 |
| RML-012 | A | Principio arquitectónico declarado: la predicción no decide |
| **RML-013** | B | *(nuevo)* Evaluación de Nivel 2 — ver más abajo |

**Reparto sobre los 63 requisitos:** A = 24 · B = 24 · C = 6 · D = 12 (RF-002, RF-016, RF-021,
RNF-008, RNF-011, RS-007, RS-009, RS-012, RS-013 *parcial*, RML-010, RML-011) · **Inventados = 0**
tras esta revisión.

Los doce de clase D no se eliminan —varios son buenas prácticas que el equipo desea conservar—
pero **quedan marcados como no vinculantes, tanto aquí como en su propia entrada**. Su presencia con el verbo "debe" era el
principal defecto del documento: inflaba el compromiso del proyecto con exigencias que nadie pidió.

#### RML-013 — Evaluación del impacto sobre la decisión de abastecimiento

*(Definición completa del requisito nuevo introducido en la revisión 0.1; se enuncia aquí, junto a su
clasificación, para no alterar la numeración de §4.)*
- **Descripción:** La estrategia de evaluación debe medir, además del error de pronóstico, el efecto
  del forecast sobre las **decisiones de abastecimiento** resultantes, y comparar el forecast del
  modelo contra el baseline recorriendo el sistema completo (forecast → motor → recomendaciones).
- **Clase:** B (derivado). Sin esto no puede demostrarse que el motor predictivo cumple el alcance 9
  con utilidad: un modelo puede acertar más y hacer comprar peor.
- **Prioridad:** Debe
- **Criterio de aceptación:** El informe de evaluación incluye métricas de Nivel 2
  (`docs/05-motor-predictivo.md` §9.4) y la comparación end-to-end baseline vs. ML (§9.5), en igualdad
  de reglas y parámetros. **No se fija ningún valor objetivo**: la comparación es relativa al baseline.
- **Dependencias:** RML-001, RF-015 · **Relacionado:** `DT-020`

## 6. Trazabilidad

| Alcance funcional declarado | Requisitos |
|---|---|
| 1. Administrar productos | RF-001 |
| 2. Administrar inventarios | RF-003 |
| 3. Registrar movimientos | RF-004 |
| 4. Registrar consumo/ventas | RF-006 |
| 5. Administrar proveedores | RF-005 |
| 6. Registrar tiempos de entrega | RF-007 |
| 7. Registrar órdenes de compra | RF-008 |
| 8. Analizar históricos | RF-009 |
| 9. Predecir demanda futura | RF-010, RML-001…RML-012 |
| 10. Calcular riesgo de desabasto | RF-013 |
| 11. Detectar sobreinventario | RF-014 |
| 12. Calcular puntos de reorden | RF-012 |
| 13. Calcular stock de seguridad | RF-011 |
| 14. Generar recomendaciones de compra | RF-015 |
| 15. Interfaz web | RF-017 |
| 16. Indicadores en Power BI | RF-018 |
| 17. Explicaciones con Azure OpenAI | RF-019 |
| 18. Azure AI Search | RF-020 |
| 19. Microsoft Entra ID | RS-001, RS-002 |
| 20. Pruebas y CI/CD | RNF-007, RS-005, RS-013 |

**Requisitos sin correspondencia directa con un punto del alcance** (derivados, supuestos o propuestas
— ver §5): RF-002, RF-016, RF-021, RF-022, RF-023, RF-024, RML-013, todos los RNF salvo RNF-001 y
RNF-007, y todos los RS salvo RS-001, RS-002 y RS-010. Su justificación individual está en §5.

## 7. Elementos pendientes de definición por el negocio

Los siguientes valores **no se han inventado** y bloquean la parametrización definitiva:

1. Nivel de servicio objetivo por producto o categoría (afecta RF-011).
2. Umbrales de clasificación de riesgo de desabasto y de sobreinventario (RF-013, RF-014).
3. Política de revisión: continua o periódica, y su frecuencia (RF-012).
4. Costos de faltante y de mantener inventario (necesarios para la optimización económica y para dos
   métricas de Nivel 2).
5. Horizonte de cobertura deseado más allá del punto de reorden (`BR-X13`, afecta a RF-015).
6. Calendario laboral, festivos y estacionalidades conocidas del negocio — necesario además para fijar
   la conversión entre pronóstico semanal y lead time en días (`DT-019`).
7. Criterio de selección de proveedor cuando existen varios (costo, lead time, confiabilidad).
8. Mapeo de roles de Entra ID a los roles conceptuales del sistema (RS-002).
9. Volúmenes reales de catálogo, histórico y usuarios (RNF-004).
