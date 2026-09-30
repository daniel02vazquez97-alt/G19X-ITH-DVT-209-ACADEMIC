# Supuestos del proyecto

**Estado:** Versión 1.0 — Etapa 0 · **Fecha:** 2026-09-04 · **Versión 1.1** — revisada en la auditoría de Etapa 0.1

Registro de todo lo que se ha dado por cierto **sin confirmación del negocio**.

**Un supuesto no es un requisito.** Todos son revocables: si el negocio contradice uno, se actualiza
este documento, los documentos afectados y, si procede, el ADR correspondiente.

Cada supuesto indica **cómo se valida** y **qué se rompe** si resulta falso. Sin esas dos columnas,
un registro de supuestos es una lista de deseos.

**Estados:** `VIGENTE` · `VALIDADO` · `REFUTADO` · `OBSOLETO`

---

## ASSUMPTION-001 — Uso de datos sintéticos

- **Supuesto:** Se trabajará con datos sintéticos porque no se dispone todavía de datos reales de la empresa.
- **Origen:** Declarado explícitamente en el alcance del proyecto.
- **Impacto:** Fases 1 a 5. Ninguna métrica obtenida con datos sintéticos puede presentarse como
  evidencia de desempeño con datos reales.
- **Validación:** Confirmar cuándo y en qué formato estarán disponibles los datos reales.
- **Si es falso:** Si hay datos reales antes de lo previsto, se acorta la Fase 1 y se revalida todo lo posterior.
- **Estado:** `VIGENTE`

## ASSUMPTION-002 — Horizonte de predicción

- **Supuesto:** El horizonte relevante para la decisión de compra es del orden de *lead time + periodo
  de revisión*. Valor inicial de trabajo: 8–12 semanas.
- **Origen:** Práctica estándar de gestión de inventarios.
- **Impacto:** `docs/05-motor-predictivo.md`, diseño del dataset, evaluación del modelo.
- **Validación:** Confirmar los lead times reales y la frecuencia de compra del negocio.
- **Si es falso:** Cambia el horizonte de entrenamiento y evaluación; no cambia la arquitectura.
- **Estado:** `VIGENTE`

## ASSUMPTION-003 — Existe histórico suficiente

- **Supuesto:** Existirá histórico de consumo suficiente (orientativamente 24–36 meses) para detectar
  estacionalidad anual en una parte relevante del catálogo.
- **Origen:** Necesidad metodológica: sin dos ciclos completos no puede estimarse estacionalidad anual.
- **Impacto:** Viabilidad de modelos estacionales; segmentación del catálogo.
- **Validación:** Inventariar la profundidad real del histórico disponible.
- **Si es falso:** Gran parte del catálogo cae en el segmento "histórico corto"; se prioriza el
  baseline y los métodos robustos, y se reduce la ambición del modelado.
- **Estado:** `VIGENTE`

## ASSUMPTION-004 — El consumo registrado aproxima la demanda

- **Supuesto:** El consumo histórico registrado es una aproximación válida de la demanda, salvo en los
  periodos de desabasto, que se marcan como censurados.
- **Origen:** Necesidad metodológica.
- **Impacto:** Entrenamiento del modelo; interpretación de las métricas.
- **Validación:** Comprobar si existen registros de demanda no satisfecha, pedidos rechazados o
  sustituciones de producto.
- **Si es falso:** Si hay demanda no satisfecha no registrada, todo el histórico está sesgado a la
  baja de forma no corregible con los datos disponibles.
- **Estado:** `VIGENTE`

## ASSUMPTION-005 — Es posible identificar los periodos de desabasto

- **Supuesto:** Se puede determinar, desde el histórico de inventario, en qué periodos un producto
  estuvo agotado.
- **Origen:** Requisito de `DT-011`.
- **Impacto:** Marca `is_stockout_affected`; tratamiento de la demanda censurada.
- **Validación:** Verificar que el histórico de inventario tiene granularidad suficiente.
- **Si es falso:** No puede corregirse el sesgo por desabasto, y debe advertirse explícitamente en la
  interpretación de las predicciones.
- **Estado:** `VIGENTE`

## ASSUMPTION-006 — Ubicación única en la primera versión

- **Supuesto:** La primera versión opera con una sola ubicación de inventario o con el inventario agregado.
- **Origen:** Simplificación para evitar complejidad prematura. La entidad `Location` se modela desde
  el inicio para no rediseñar el esquema después.
- **Impacto:** Identificador de serie de predicción; motor de abastecimiento; interfaz.
- **Validación:** Confirmar cuántos almacenes o ubicaciones gestiona el negocio.
- **Si es falso:** El identificador de serie pasa a ser `(producto, ubicación)`; aparecen decisiones
  de asignación y traspaso entre ubicaciones, que hoy están fuera de alcance.
- **Estado:** `VIGENTE`

## ASSUMPTION-007 — Un solo proveedor por orden de compra

- **Supuesto:** Cada orden de compra corresponde a un único proveedor.
- **Origen:** Práctica habitual.
- **Impacto:** Modelo de datos de órdenes.
- **Validación:** Confirmar con el proceso de compras real.
- **Si es falso:** Cambio menor en el modelo de datos.
- **Estado:** `VIGENTE`

## ASSUMPTION-008 — Existencia de corpus documental

- **Supuesto:** Existe documentación interna (políticas de compra, contratos, manuales) susceptible de
  ser indexada para el flujo RAG.
- **Origen:** El alcance incluye Azure AI Search para recuperación documental.
- **Impacto:** Viabilidad del caso de uso CU-4 (`docs/09-ia-generativa.md`).
- **Validación:** Inventariar la documentación existente, su formato y su volumen.
- **Si es falso:** **Azure AI Search pierde su propósito principal.** Habría que reconsiderar su
  inclusión en el stack o redefinir su uso (p. ej. búsqueda sobre catálogos y fichas de producto).
- **Estado:** `VIGENTE` — **es el supuesto con mayor riesgo de resultar falso.**

## ASSUMPTION-009 — Jerarquía de categorías de un solo nivel

- **Supuesto:** Una jerarquía plana de categorías es suficiente para la primera versión.
- **Origen:** Simplificación. El campo `parent_id` se contempla para permitir la extensión.
- **Impacto:** Modelo de datos; agregaciones en Power BI.
- **Validación:** Confirmar la estructura real del catálogo.
- **Si es falso:** Cambio acotado, ya previsto en el diseño.
- **Estado:** `VIGENTE`

## ASSUMPTION-010 — Cuatro roles de usuario

- **Supuesto:** Los roles `ADMIN`, `PLANNER`, `ANALYST` y `VIEWER` cubren las necesidades iniciales.
- **Origen:** Propuesta del alcance del proyecto, marcada como pendiente de validación.
- **Impacto:** `docs/10-seguridad.md`, matriz de autorización de la API, interfaz.
- **Validación:** Revisar con el negocio la estructura organizacional real y los grupos de Entra ID.
- **Si es falso:** Se ajusta la matriz de autorización; si se requiere autorización por ámbito de
  datos (categoría, ubicación), el cambio es más profundo y afecta a todas las consultas.
- **Estado:** `VIGENTE`

## ASSUMPTION-011 — Objetivos de rendimiento

- **Supuesto:** p95 < 2 s para listados paginados y detalle de producto.
- **Origen:** Valor razonable para una aplicación de apoyo a la decisión. **No aportado por el negocio.**
- **Impacto:** Diseño de consultas, índices, paginación; pruebas de rendimiento.
- **Validación:** Confirmar expectativas reales de los usuarios.
- **Si es falso:** Se ajustan los objetivos; podría requerir caché o materialización de agregados.
- **Estado:** `VIGENTE`

## ASSUMPTION-012 — Volumen de referencia

- **Supuesto:** ~5.000 SKU activos, ~50 proveedores, 24–36 meses de histórico diario y hasta 3
  ubicaciones registradas; la primera versión opera sobre una sola o sobre el agregado (ASSUMPTION-006).
- **Origen:** Estimación para poder dimensionar el diseño. **No aportada por el negocio.**
- **Impacto:** Diseño de base de datos, decisión Import vs. DirectQuery en Power BI, tiempos del proceso batch.
- **Validación:** Solicitar las cifras reales del catálogo y del histórico.
- **Si es falso:** Un volumen sustancialmente mayor (p. ej. 100.000 SKU) obligaría a revisar
  particionamiento, estrategia de inferencia y modo de conexión de Power BI. La arquitectura no
  cambiaría, pero sí varias decisiones de implementación.
- **Estado:** `VIGENTE`

## ASSUMPTION-013 — Disponibilidad en horario laboral

- **Supuesto:** Es un sistema de apoyo a la decisión de uso en horario laboral; no requiere alta
  disponibilidad continua en la primera versión.
- **Origen:** Naturaleza del sistema. **No confirmado.**
- **Impacto:** Arquitectura de despliegue, redundancia, ventanas de mantenimiento, costo.
- **Validación:** Confirmar con el negocio.
- **Si es falso:** Aumenta el costo y la complejidad de infraestructura.
- **Estado:** `VIGENTE`

## ASSUMPTION-014 — Destino de despliegue en Azure diferido

- **Supuesto:** La elección del servicio de cómputo (App Service, Container Apps u otro) puede
  aplazarse a las Fases 12–13 sin comprometer el diseño, gracias al uso de contenedores.
- **Origen:** Decisión de no comprometer una arquitectura sin requisitos de carga ni presupuesto.
- **Impacto:** `docs/12-devops.md`.
- **Validación:** Confirmar restricciones corporativas de infraestructura y presupuesto.
- **Si es falso:** Si existen restricciones corporativas obligatorias (red privada, servicio impuesto),
  deben conocerse antes para adaptar el diseño.
- **Estado:** `VIGENTE`

## ASSUMPTION-015 — Los datos maestros son razonablemente estables

- **Supuesto:** El catálogo de productos y proveedores no cambia de forma masiva y continua; las altas
  y bajas son incrementales.
- **Origen:** Necesario para que un modelo entrenado siga siendo aplicable.
- **Impacto:** Frecuencia de reentrenamiento; tratamiento de productos nuevos.
- **Validación:** Analizar la tasa histórica de altas y bajas de SKU.
- **Si es falso:** Con un catálogo muy volátil, la mayoría de los SKU tendría histórico corto y el
  peso recaería en métodos de analogía por categoría más que en modelos por serie.
- **Estado:** `VIGENTE`

## ASSUMPTION-016 — La unidad de medida es estable por producto

- **Supuesto:** La unidad de medida de un producto no cambia a lo largo del histórico, o los cambios
  están documentados y son convertibles.
- **Origen:** Necesidad metodológica.
- **Impacto:** Validez del histórico de consumo e inventario.
- **Validación:** Comprobar si ha habido cambios de unidad o de empaque en el histórico.
- **Si es falso:** Series con saltos artificiales que el modelo interpretaría como cambios de demanda.
  Requiere normalización previa del histórico.
- **Estado:** `VIGENTE`

## ASSUMPTION-017 — Existe información de costos

- **Supuesto:** Se dispone de costo unitario por producto o por relación producto–proveedor.
- **Origen:** Necesario para valorar el inventario y el capital inmovilizado.
- **Impacto:** KPIs de valor de inventario y de capital inmovilizado; priorización económica.
- **Validación:** Confirmar disponibilidad y calidad del dato de costo.
- **Si es falso:** Los indicadores monetarios no pueden calcularse; el sistema seguiría funcionando en
  unidades, pero perdería la capacidad de priorizar por impacto económico.
- **Estado:** `VIGENTE`

## ASSUMPTION-018 — Uso principal en escritorio

- **Supuesto:** Los usuarios trabajarán principalmente desde ordenadores de escritorio.
- **Origen:** Naturaleza de la tarea de planificación.
- **Impacto:** Diseño del frontend y prioridades de responsividad.
- **Validación:** Confirmar si hay uso en almacén con dispositivos móviles.
- **Si es falso:** Cambian las prioridades de diseño de la interfaz.
- **Estado:** `VIGENTE`

## ASSUMPTION-019 — Demanda uniforme dentro de la semana

- **Supuesto:** Al convertir un pronóstico semanal en demanda esperada sobre un lead time expresado en
  días, la demanda se reparte de forma uniforme entre los días de la semana.
- **Origen:** Necesidad operativa creada por `DT-008` (modelar en semanas) frente a lead times en días.
  Es el supuesto que sostiene la regla de prorrateo uniforme recomendada en `DT-019`.
- **Impacto:** Cálculo de la demanda durante el lead time (`docs/06` §5.1), y por tanto del punto de
  reorden, del stock de seguridad y de la cantidad recomendada. Afecta a **todos** los productos cuyo
  lead time no sea múltiplo de 7 días, es decir, a casi todos.
- **Validación:** Analizar el perfil intra-semanal del histórico diario de consumo, y confirmar el
  calendario laboral del negocio (`BR-X06`).
- **Si es falso:** Si el negocio no opera todos los días, o el histórico muestra un perfil semanal
  marcado, el prorrateo uniforme **sesga sistemáticamente** la demanda durante el lead time: al alza si
  el lead time cae en días de baja actividad, a la baja si cae en días de alta. La corrección es
  sustituirlo por prorrateo según el perfil observado, alternativa (b) de `DT-019`, sin cambiar la
  interfaz de la función que hace la conversión.
- **Estado:** `VIGENTE`

## ASSUMPTION-020 — El histórico permite simulación retrospectiva

- **Supuesto:** El histórico disponible permite reconstruir, para una fecha pasada, el estado de
  inventario, las órdenes vigentes y los lead times conocidos en ese momento, de modo que el motor de
  abastecimiento pueda ejecutarse "como si fuera" esa fecha.
- **Origen:** Requisito de la evaluación de Nivel 2 y de la comparación end-to-end (`DT-020`, RML-013).
- **Impacto:** Viabilidad de toda la evaluación de Nivel 2. Sin ella, la única evaluación posible es la
  del error de pronóstico, y el proyecto no podría demostrar que mejora las decisiones.
- **Validación:** Comprobar que el histórico de movimientos y de órdenes es completo y con fechas
  fiables (`occurred_at` frente a `recorded_at`), y que la posición de inventario es reconstruible.
- **Si es falso:** La comparación baseline vs. ML solo podría hacerse sobre datos sintéticos, donde el
  estado sí es reconstruible por construcción. Los resultados no serían extrapolables a datos reales y
  habría que decirlo explícitamente en el informe de evaluación.
- **Estado:** `VIGENTE`

## ASSUMPTION-021 — Revisión periódica semanal como supuesto de trabajo de V1

- **Supuesto:** Mientras `BR-X02` siga pendiente, V1 calcula como si la política fuera de **revisión
  periódica** con un periodo de **7 días**. El horizonte de cobertura es entonces
  `lead time + 7 días` (`DT-031` §V1-03).
- **Origen:** Necesidad operativa. `ASSUMPTION-002` ya establece que el horizonte relevante es *lead
  time + periodo de revisión*; `docs/06` §5 fija que bajo revisión periódica el intervalo de
  protección es `L + R`. El valor 7 se elige porque el modelado es semanal (`DT-008`) y alinear la
  revisión con la granularidad del pronóstico evita una conversión adicional.
- **Impacto:** `docs/06` §§5, 7 y 8; todo el cálculo de V1; el diseño de los componentes del
  generador que produzcan órdenes.
- **Validación:** Preguntar al negocio con qué frecuencia revisa y emite pedidos hoy (`BR-X02`).
- **Si es falso:** Si la revisión es **continua**, la fórmula de V1 vuelve a la rama de `docs/06` §8
  con `H_cobertura` explícito (`BR-X13`) y `DT-031` §V1-03 se retira. Si es periódica con otra
  frecuencia, solo cambia el valor de `R_v1`. En ninguno de los dos casos cambia la estructura del
  cálculo ni la arquitectura.
- **Estado:** `VIGENTE` — **valor técnico provisional, no una política de la organización.**

## ASSUMPTION-022 — `z_v1 = 1,65` como parámetro técnico provisional

- **Supuesto:** Mientras `BR-X01` siga pendiente, V1 usa `z_v1 = 1,65` para calcular el stock de
  seguridad (`DT-031` §V1-05).
- **Origen:** Necesidad de que `raw_need` sea calculable. Bajo normalidad corresponde nominalmente a
  un ~95 % de probabilidad de no agotar en un ciclo. **No es un nivel de servicio comprometido con
  nadie**, y `docs/06` §6.3 advierte de dos cosas que este supuesto no resuelve: el supuesto de
  normalidad no se sostiene en demanda intermitente ni asimétrica, y existen dos definiciones de
  nivel de servicio que no son intercambiables.
- **Impacto:** Stock de seguridad, y por tanto punto de reorden y cantidad recomendada, en todo el
  entorno sintético.
- **Validación:** Obtener del negocio el nivel de servicio objetivo **y su definición** (`BR-X01`).
- **Si es falso:** Cambia una constante. Ningún otro elemento del cálculo se ve afectado. Lo que **no**
  cambia con una constante es la limitación de fondo: `DT-010` sigue sin decidir qué incertidumbre
  debe cubrirse, y esa decisión sí puede cambiar la fórmula.
- **Estado:** `VIGENTE` — **parámetro técnico provisional. `BR-009` sigue rigiendo fuera del entorno
  sintético: sin `BR-X01`, no hay stock de seguridad calculable en producción.**

## ASSUMPTION-023 — En V1 la incertidumbre se mide sobre la demanda, no sobre el error de pronóstico

- **Supuesto:** V1 calcula el stock de seguridad a partir de la **variabilidad de la demanda agregada
  al horizonte** (`σ_H`), medida directamente sobre ventanas móviles del histórico.
- **Origen:** `docs/06` §6.4 señala que la fuente más pertinente es el **error de pronóstico**, no la
  variabilidad de la demanda. Pero el error de pronóstico exige residuos de backtesting, que exigen un
  modelo entrenado, que es la Fase 5. **En V1 no existe modelo**, de modo que esa fuente no está
  disponible. Se mide `σ_H` directamente y **no se escala por `√L`**, precisamente porque §6.4
  advierte de que ese escalado no es una identidad general.
- **Impacto:** Magnitud del stock de seguridad. Si el modelo acaba prediciendo bien una demanda muy
  variable, V1 **sobreestima** el stock necesario — que es exactamente lo que §6.4 anticipa.
- **Validación:** Al existir un modelo entrenado, comparar en la Fase 5 el efecto de cada fuente de
  incertidumbre sobre las métricas de **Nivel 2** (`DT-020`), como `DT-010` establece.
- **Si es falso:** El stock de seguridad de V1 no es comparable con el definitivo. No invalida el
  dataset ni la arquitectura: invalida la **cifra**, que es provisional por construcción.
- **Estado:** `VIGENTE` — provisional hasta que se cierre `DT-010`.

## ASSUMPTION-024 — Parámetros del lead time observado en V1

- **Supuesto:** El lead time observado representativo de un par producto–proveedor es la **mediana de
  las últimas 12 observaciones válidas**, con un mínimo de **3** para considerarlo utilizable y un
  techo de **90 días** (`DT-031` §V1-09). Una observación es un `PurchaseOrderItem` completamente
  recibido, fechado por su última recepción.
- **Origen:** Necesidad operativa tras la decisión del responsable (2026-09-19) de usar el lead time
  observado en lugar del acordado. Los tres valores son la elección más simple que permite la
  evolución pedida —pocos datos → estimación inicial; más recepciones → recálculo— sin introducir
  ningún método estadístico. La mediana se elige **en lugar de la media** porque es robusta y actúa
  a la vez como tratamiento de valores anómalos, evitando inventar un criterio de detección.
- **Impacto:** Horizonte de cobertura, y con él la demanda sobre el horizonte, el stock de seguridad
  y la cantidad recomendada de todo par con histórico suficiente.
- **Validación:** Con el dataset generado, comprobar si 12 observaciones son suficientes para que la
  mediana sea estable y si 3 es un mínimo razonable. Es una comprobación empírica, no una pregunta
  al negocio.
- **Si es falso:** Si 12 resulta demasiado corto, la estimación oscila; si demasiado largo, tarda en
  reflejar un cambio de comportamiento del proveedor. En ambos casos cambia **una constante**. Si el
  techo de 90 días se alcanza con frecuencia, la señal no es que el techo esté mal sino que el
  horizonte de pronóstico de `ASSUMPTION-002` se queda corto.
- **Confirmación del 2026-09-21:** el responsable confirmó los tres valores (`N_v1 = 12`,
  `N_MIN_v1 = 3`, `LT_MAX_v1 = 90`) y el requisito de **registrar que el valor fue topado**
  (`LEAD_TIME_CAPPED`) conservando el valor sin topar en la trazabilidad. Lo confirmado es **la regla
  técnica de V1**: el techo de 90 días **no es una política comercial de la organización** y no debe
  presentarse como un lead time máximo acordado con ningún proveedor.
- **Estado:** `VIGENTE` — **parámetros técnicos provisionales**, confirmados como reglas de V1 el
  2026-09-21 (`DT-031` §`V1-09`, `V1-09.1`, `V1-09.2`).

## ASSUMPTION-025 — Lead time de una relación inactiva para dimensionar el saldo de apertura

- **Supuesto:** Para un producto **sin relación proveedor activa y preferente**, el
  `agreed_lead_time_days` de una relación existente aunque esté inactiva y no sea preferente es un
  valor **aceptable para dimensionar exclusivamente su saldo de apertura** en el dataset sintético
  (`DT-036` §6). Si hay varias relaciones y ninguna es activa+preferente, se usa la de `supplier_id`
  menor; si no existe ninguna relación, la generación **falla por precondición** y no se inventa un
  lead time por defecto.
- **Origen:** El catálogo vigente tiene cinco productos en esa situación —ids 3, 20, 57, 71 y 74—,
  cada uno con exactamente una relación `is_preferred = false`, `is_active = false`. La regla
  aprobada exige que tengan inventario inicial, consuman y lleguen a cero; la fórmula del saldo de
  apertura necesita un `L_i`, y ese es el único que existe en el repositorio. La alternativa era
  inventar un lead time por defecto, que sí sería un parámetro de negocio inventado
  (`CLAUDE.md` §7.4).
- **Impacto:** El saldo de apertura de cinco de cien productos, y con él la fecha en que cada uno
  llega a cero. Ninguna orden, ninguna recepción y ninguna elección de proveedor dependen de este
  valor: `V1-10` queda intacta porque para estos productos nunca se emite una orden.
- **Validación:** No es una pregunta al negocio. Se comprueba sobre el dataset generado: que los
  cinco productos tengan saldo de apertura, no generen ninguna orden ni ninguna recepción, y
  permanezcan en cero tras agotarse.
- **Si es falso:** Cambia únicamente la magnitud del saldo inicial de cinco productos sintéticos.
  **No es un supuesto de alto riesgo** y por eso no figura en la tabla de mayor riesgo: no sostiene
  ninguna regla de negocio, ninguna cifra del motor ni ninguna decisión de modelado.
- **Estado:** `VIGENTE` — **técnica del generador sintético**, confirmada por el responsable el
  2026-09-24. **No es una regla del motor real de abastecimiento** y no debe presentarse como un lead
  time acordado con ningún proveedor.

---

## Cómo gestionar los supuestos

1. Al detectar un nuevo supuesto durante el desarrollo, **registrarlo aquí antes de construir sobre él.**
2. Al validarlo con el negocio, cambiar el estado a `VALIDADO` y anotar la fuente y la fecha.
3. Al refutarlo, cambiar a `REFUTADO`, documentar la realidad y **actualizar todos los documentos
   afectados** en el mismo cambio.
4. Nunca convertir un supuesto en requisito sin confirmación explícita (`CLAUDE.md` §6, regla 4).

## Supuestos de mayor riesgo

Ordenados por impacto si resultaran falsos:

| ID | Supuesto | Qué se rompe |
|---|---|---|
| `ASSUMPTION-008` | Existe corpus documental | Azure AI Search pierde su propósito principal |
| `ASSUMPTION-004` | El consumo aproxima la demanda | Todo el histórico está sesgado |
| `ASSUMPTION-003` | Hay histórico suficiente | Se reduce drásticamente la ambición del modelado |
| `ASSUMPTION-012` | Volumen de referencia | Cambian varias decisiones de implementación |
| `ASSUMPTION-006` | Ubicación única | Aparece un dominio completo de decisiones de asignación |
| `ASSUMPTION-020` | El histórico permite simulación retrospectiva | La evaluación de Nivel 2 no sería posible con datos reales |
| `ASSUMPTION-019` | Demanda uniforme dentro de la semana | Sesgo sistemático en la demanda durante el lead time |
| `ASSUMPTION-021` | Revisión periódica semanal (V1) | Cambia el horizonte de cobertura y, con él, toda cifra de V1 |
| `ASSUMPTION-023` | La variabilidad de la demanda aproxima la incertidumbre (V1) | El stock de seguridad de V1 no es comparable con el definitivo |
| `ASSUMPTION-024` | Parámetros del lead time observado (V1) | Cambian constantes, no la estructura del cálculo |
