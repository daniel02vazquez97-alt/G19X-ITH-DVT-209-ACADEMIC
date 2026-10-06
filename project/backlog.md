# Backlog inicial (Scrum)

**Estado:** Versión 1.0 — Etapa 0 · **Fecha:** 2026-09-04 · **Versión 1.1** — revisada en la auditoría de Etapa 0.1 · **Versión 1.2** (2026-09-30) — correspondencia con las unidades de la Etapa 2 · **Versión 1.3** (2026-10-04) — US-048: interpretación de U6 (`DT-068`) · **Versión 1.4** (2026-10-05) — notas de la Fase 5 en US-050 a US-058 (`DT-071` a `DT-085`; no autorizada) · **Versión 1.5** (2026-10-05) — US-058: F5b autorizada (`DT-088`) · **Versión 1.6** (2026-10-05) — US-050 a US-058 tras G1 (`DT-089` a `DT-091`): cerradas o pendientes · **Versión 1.7** (2026-10-06) — F5c autorizada (`DT-092`): notas en US-051 a US-055 y US-058 · **Versión 1.8** (2026-10-06) — F5c implementada: notas en US-054, US-055 y US-058 · **Versión 1.9** (2026-10-06) — revisión de F5c: corrección en US-054 (SES cumple los criterios)

Backlog organizado en **Épicas → Historias de usuario → Tareas**.

## Convenciones

| Elemento | ID | Descripción |
|---|---|---|
| Épica | `EPIC-##` | Agrupación de valor, alineada con una o varias fases del roadmap |
| Historia | `US-###` | Necesidad expresada desde el punto de vista del usuario |
| Tarea | `T-###.#` | Trabajo técnico dentro de una historia |

**Prioridad:** `P0` (bloqueante) · `P1` (alta) · `P2` (media) · `P3` (baja)

**No se estiman horas ni puntos todavía**: no existe información suficiente sobre el equipo, su
velocidad ni la complejidad real. Estimar ahora produciría cifras falsas que después se usarían como
compromiso.

**Los criterios de aceptación son verificables.** Una historia sin criterio comprobable no está lista
para entrar en un sprint.

---

## EPIC-01 — Preparación del proyecto *(Fase 0 — entregables completos, pendiente de aprobación)*

Documentación base, reglas de trabajo y planificación.

| ID | Historia | Prioridad | Estado |
|---|---|---|---|
| US-001 | Como equipo, necesito documentación base y reglas de trabajo para desarrollar de forma ordenada | P0 | 🟡 Entregables completos, pendiente de aprobación |

**Criterios de aceptación (US-001):** existen los 32 archivos —los 31 enumerados en
`docs/reports/etapa-0-reporte.md` §1 más el reporte de la revisión 0.1—: `CLAUDE.md`, `AGENTS.md`, `README.md`, `.gitignore`, los
quince documentos numerados de `docs/` más cuatro auxiliares, los cuatro de `knowledge/`, los tres de
`project/` y el de `tests/`; son coherentes entre sí; los supuestos están marcados como tales;
ninguna hipótesis se presenta como requisito.

---

## EPIC-02 — Datos sintéticos e ingesta *(Fase 1)*

### US-010 — Diseño del dataset sintético
- **Descripción:** Como equipo de desarrollo, necesito un dataset que represente un escenario
  empresarial verosímil para poder construir y evaluar el sistema sin datos reales.
- **Prioridad:** P0
- **Criterios de aceptación:**
  - El dataset incluye los catorce escenarios previstos: alta y baja rotación, demanda estable,
    creciente y decreciente, estacionalidad, variabilidad, periodos de desabasto, exceso de
    inventario, proveedores confiables y con retrasos, distintos lead times, órdenes de compra e
    inventario en tránsito.
  - Cada escenario está documentado con sus parámetros y es identificable en los datos.
  - La generación es reproducible con semilla fija.
  - Los datos guardan coherencia interna: el inventario es consistente con los movimientos, y las
    órdenes con las recepciones.
- **Dependencias:** EPIC-01

**Tareas:** `T-010.1` especificación del dataset · `T-010.2` implementar el generador ·
`T-010.3` generar y validar coherencia · `T-010.4` informe de calidad del dataset

### US-011 — Ingesta y validación de datos
> **Etapa 2, unidad U2** (2026-09-30): diseño en `docs/04` §9 y `DT-044`; no implementada.

- **Descripción:** Como administrador, quiero cargar datos desde archivos con validación, para poder
  sustituir los sintéticos por reales sin cambiar el sistema.
- **Prioridad:** P0
- **Criterios de aceptación:** una carga con registros inválidos reporta cada fila rechazada y su
  motivo, y no deja el sistema inconsistente; toda carga registra su `data_origin`; el mismo proceso
  admite datos sintéticos y reales.
- **Dependencias:** US-010

### US-012 — Marcado de periodos de desabasto
- **Descripción:** Como científico de datos, necesito identificar los periodos afectados por desabasto
  para no entrenar el modelo con demanda censurada.
- **Prioridad:** P1
- **Criterios de aceptación:** los periodos con existencia cero y demanda quedan marcados con
  `is_stockout_affected`; la marca es verificable contra el histórico de inventario.
- **Dependencias:** US-010 · **Relacionado:** `DT-011`, ASSUMPTION-005

---

## EPIC-03 — Persistencia *(Fase 2)*

### US-020 — Esquema de base de datos
- **Descripción:** Como equipo, necesito el modelo de datos implementado con integridad garantizada.
- **Prioridad:** P0
- **Criterios de aceptación:** todas las entidades de `docs/04-modelo-datos.md` existen con sus
  restricciones; las migraciones se aplican desde cero de forma reproducible; el histórico es
  inmutable por diseño; las claves de negocio son únicas.
- **Dependencias:** EPIC-02

### US-021 — Reconstrucción y conciliación de inventario
- **Descripción:** Como responsable de datos, necesito que la posición de inventario almacenada sea
  reconciliable con el histórico de movimientos.
- **Prioridad:** P0
- **Criterios de aceptación:** existe un proceso que reconstruye la posición desde los movimientos;
  el valor reconstruido coincide con el almacenado para todo el catálogo; una discrepancia se reporta
  como incidencia, no se corrige silenciosamente.
- **Dependencias:** US-020

### US-022 — Vistas analíticas y fotografía diaria de inventario
- **Descripción:** Como analista, necesito estructuras de datos aptas para explotación analítica.
- **Prioridad:** P2
- **Criterios de aceptación:** existen las vistas que soportan el modelo dimensional de
  `docs/11-power-bi.md`; se genera una fotografía diaria de inventario; las vistas no exponen tablas operativas.
- **Dependencias:** US-020

---

## EPIC-04 — API de datos *(Fase 3)*

### US-030 — Consulta de productos e inventario
- **Descripción:** Como usuario, quiero consultar el catálogo y la posición de inventario.
- **Prioridad:** P0
- **Criterios de aceptación:** los endpoints de `docs/07-api.md` §2.2 y §2.4 responden conforme al
  contrato; la paginación y el filtrado funcionan; los errores siguen el formato uniforme; existe la
  especificación OpenAPI.
- **Dependencias:** EPIC-03

### US-031 — Consulta de proveedores y órdenes de compra
- **Prioridad:** P1
- **Criterios de aceptación:** endpoints de §2.6 y §2.7 operativos; el detalle de orden incluye líneas
  y recepciones; el tránsito se deriva correctamente de las órdenes vigentes.
- **Dependencias:** US-030

### US-032 — Registro de movimientos, consumo y recepciones
- **Prioridad:** P1
- **Criterios de aceptación:** los registros se crean y son inmutables; no existen endpoints de
  modificación ni borrado sobre ellos; una recepción actualiza el inventario y la cantidad recibida de
  la línea de orden. El **cálculo del lead time observado** a partir de esas recepciones pertenece a la
  Fase 4 (`US-047`), no a esta historia.
- **Dependencias:** US-030

### US-034 — Mantenimiento de datos maestros
- **Descripción:** Como administrador, quiero crear, actualizar y desactivar productos, categorías,
  proveedores y la relación producto–proveedor, para mantener el catálogo sin depender de cargas masivas.
- **Prioridad:** P1
- **Criterios de aceptación:** existen las operaciones de escritura de `docs/07-api.md` §2.2, §2.3 y
  §2.6; un SKU o código duplicado se rechaza; la desactivación **no elimina histórico**; las
  condiciones producto–proveedor (lead time acordado, MOQ, múltiplo, costo, preferente) son editables.
- **Dependencias:** US-030 · **Cubre:** RF-001, RF-002, RF-005
- *Añadida en la revisión 0.1: RF-001, RF-002 y RF-005 exigen "administrar" y el backlog solo cubría lectura.*

### US-035 — Creación y ciclo de vida de órdenes de compra
- **Descripción:** Como planificador, quiero crear órdenes de compra y hacer avanzar su estado, para
  que el inventario en tránsito refleje lo realmente pedido.
- **Prioridad:** P1
- **Criterios de aceptación:** una orden recorre los estados válidos y solo los válidos; las órdenes en
  `ISSUED` o `PARTIALLY_RECEIVED` aportan al tránsito total; una orden cancelada deja de aportar.
- **Dependencias:** US-031, US-034 · **Cubre:** RF-008 (creación y ciclo de estados)
- *Añadida en la revisión 0.1: `US-073` presuponía este endpoint, que no existía en ninguna épica.*

### US-033 — Análisis de históricos
- **Descripción:** Como analista, quiero consultar la serie histórica de un producto con sus estadísticos.
- **Prioridad:** P2
- **Criterios de aceptación:** el endpoint devuelve la serie en la granularidad pedida junto con media,
  desviación, coeficiente de variación y número de periodos en cero.
- **Dependencias:** US-030

---

## EPIC-05 — Motor de abastecimiento *(Fase 4)* — **núcleo de valor**

### US-040 — Cálculo de stock de seguridad y punto de reorden
- **Descripción:** Como planificador, necesito saber cuándo debo reponer cada producto.
- **Prioridad:** P0
- **Criterios de aceptación:**
  - El cálculo es **determinístico**: mismas entradas, mismo resultado, siempre.
  - Usa el lead time **observado**, no el acordado (regla propuesta `BR-P01`; si el negocio la
    refuta, cambia este criterio, no el diseño del motor).
  - Considera la variabilidad del lead time además de la de la demanda (`BR-P02`, propuesta).
  - Si falta un parámetro de política, **no calcula** y declara cuál falta.
  - Existen pruebas unitarias con valores calculados a mano.
- **Dependencias:** EPIC-04 · **Bloqueada por:** BR-X01, BR-X02 (parámetros del negocio)

- **Dependencias adicionales:** `US-050` (baseline), que es el proveedor de forecast del motor en la
  Fase 4. Sin él, `T-040.3` no tiene entrada.

**Tareas:** `T-040.1` `supply_engine` como biblioteca pura · `T-040.2` stock de seguridad ·
`T-040.3` demanda durante lead time (**incluye la conversión semanal→días de `DT-019`, en una única
función**) · `T-040.4` punto de reorden · `T-040.5` pruebas exhaustivas

### US-041 — Posición de inventario
- **Prioridad:** P0
- **Criterios de aceptación:** se distinguen `total_in_transit` (almacenado) y `effective_in_transit`
  (derivado en el cálculo, **sin columna nueva**), según `DT-012`; la comparación con el punto de
  reorden usa la posición **de decisión**; ambos valores se registran en `calculation_inputs`; hay
  pruebas del caso en que el tránsito total supera el ROP pero el efectivo no.
- **Dependencias:** EPIC-04

### US-042 — Cantidad recomendada con restricciones del proveedor
- **Prioridad:** P0
- **Criterios de aceptación:** se calcula la necesidad bruta, se aplican MOQ y múltiplo, y **se
  conservan ambos valores**; si el ajuste genera sobrecobertura, se señala el conflicto; sin proveedor
  activo, no se recomienda y se indica el dato faltante.
- **Dependencias:** US-040, US-041

### US-043 — Riesgo de desabasto
- **Prioridad:** P0
- **Criterios de aceptación:** cada producto recibe un nivel de riesgo, cobertura en días y fecha
  estimada de agotamiento; `CRITICAL` identifica correctamente el caso en que ya no se llega a tiempo.
- **Dependencias:** US-040 · **Bloqueada por:** BR-X03 (umbrales)

### US-044 — Riesgo de sobreinventario
- **Prioridad:** P1
- **Criterios de aceptación:** se listan los productos con cobertura por encima del umbral, con
  cantidad excedente y capital inmovilizado cuando hay costo disponible.
- **Dependencias:** US-040 · **Bloqueada por:** BR-X03

### US-045 — Desglose explicativo de la recomendación
- **Descripción:** Como planificador, necesito ver **por qué** el sistema recomienda esa cantidad,
  para poder confiar en ella.
- **Prioridad:** P0
- **Criterios de aceptación:** cada recomendación expone todos los términos de §13 de
  `docs/06-motor-abastecimiento.md`; puede reconstruirse a partir de lo almacenado, sin depender del
  estado actual del sistema.
- **Dependencias:** US-042

### US-046 — Proceso batch de recomendaciones
- **Prioridad:** P0
- **Criterios de aceptación:** genera recomendaciones para todo el catálogo; registra la ejecución con
  versiones y parámetros; no bloquea la API; es reejecutable sin duplicar resultados.
- **Dependencias:** US-042, US-045

### US-047 — Métricas de desempeño de proveedor
- **Prioridad:** P2
- **Criterios de aceptación:** cumplimiento en tiempo y cantidad, lead time medio y variabilidad,
  calculados desde el histórico de órdenes y recepciones.
- **Dependencias:** US-031

### US-048 — Explicación por plantilla determinística
- **Prioridad:** P2
- **Criterios de aceptación:** cada recomendación tiene una explicación en lenguaje natural generada
  por plantilla, **sin LLM**; todas sus cifras proceden del desglose almacenado.
- **Dependencias:** US-045 · **Relacionado:** `DT-018`
- *Interpretación (2026-10-04, `DT-068`, U6): `RECOMMEND` y `NO_NEED` → explicación narrativa; `NOT_CALCULABLE` →
  explicación estructurada (`reasons`, `reason_details`, `missing_policy_parameters`), con `narrative = null`.
  Contrato en `docs/09` §14.5.*

---

## EPIC-06 — Predicción de demanda *(Fase 5)*

### US-050 — Baseline de pronóstico
> **Se entrega en la Fase 4**, no en la 5: el motor de abastecimiento necesita un forecast para
> funcionar, y el baseline es ese primer forecast. Se lista en esta épica por afinidad temática.
- **Prioridad:** P0
- **Criterios de aceptación (Fase 4):** implementados **naïve, naïve estacional y media móvil**; el
  baseline de referencia queda registrado; **está siempre disponible como respaldo**; se expone tras la
  interfaz `ForecastProvider`.
- **Ampliación en Fase 5:** suavizado exponencial simple y elección del baseline oficial por desempeño.
- **Dependencias:** EPIC-03
- *Fase 5 (2026-10-05):* suavizado exponencial simple en F5a (`DT-076` punto 7, `PROPUESTA`); baseline oficial elegido en la puerta G1 (`DT-071`).
- *G1 (2026-10-05):* **cerrada.** Baseline oficial: media móvil de 13 semanas (`DT-089`), provisional con datos `SYNTHETIC`. SES, implementado en F5a, es el candidato más fuerte y no se promueve.

### US-051 — Segmentación del catálogo
- **Prioridad:** P1
- **Criterios de aceptación:** cada SKU queda clasificado en uno de los segmentos de
  `docs/05-motor-predictivo.md` §4; la clasificación es visible en la salida.
- **Dependencias:** US-050
- *Fase 5 (2026-10-05):* umbrales propuestos en `DT-077` (Syntetos-Boylan, provisionales), `OPEN` hasta G1; criterio de estacionalidad `OPEN`. F5a, autorizada (`DT-086`), calcula la clasificación provisional.
- *G1 (2026-10-05):* **pendiente** (F5c). G1 no fija los umbrales ni la estacionalidad de `DT-077`; la clasificación provisional de F5a solo informa y alimenta el criterio por segmento de `DT-091`.
- *F5c (2026-10-06):* en curso con F5c autorizada (`DT-092`): Syntetos-Boylan con ADI 1,32 y CV² 0,49 y criterio de estacionalidad de `DT-093` punto 7 (provisionales).

### US-052 — Pipeline de features sin fuga temporal
- **Prioridad:** P0
- **Criterios de aceptación:** ninguna feature usa información posterior al instante de predicción;
  existe una prueba automatizada que lo verifica; el escalado se ajusta solo con datos de entrenamiento.
- **Dependencias:** US-050
- *Fase 5 (2026-10-05):* features solo con datos `≤ as_of` en cada corte (`DT-075`); solo biblioteca estándar (`DT-073`).
- *G1 (2026-10-05):* **pendiente** (F5c): todavía no hay modelos con features. El backtesting de F5a ya usa solo datos `≤ as_of`.
- *F5c (2026-10-06):* en curso (`DT-092`): los modelos de F5c usan solo datos `≤ as_of` de cada corte y las estrategias de `DT-081` solo datos anteriores a la decisión (`DT-093` punto 8).

### US-053 — Backtesting con validación temporal
- **Prioridad:** P0
- **Criterios de aceptación:** *rolling origin* con al menos tres cortes y gap igual al horizonte; el
  holdout final se usa una sola vez; las métricas se reportan con su dispersión y por segmento.
- **Dependencias:** US-052
- *Fase 5 (2026-10-05):* 17 cortes (semanas 64 a 128, cada 4), horizonte de 14 semanas, sin zona muerta y *holdout* 2025-09-24 de uso único (`DT-075`); métricas en `DT-076`.
- *G1 (2026-10-05):* **cerrada** en cuanto al backtesting (F5a, sobre los baselines). El *holdout* no se ha usado y queda reservado para G2.
- *F5c (2026-10-06):* el backtesting de los 17 cortes se extiende a los candidatos de F5c; el *holdout* sigue sin usarse (`DT-092`).

### US-054 — Modelo de predicción de demanda
- **Prioridad:** P0
- **Criterios de aceptación:** supera al baseline en la métrica primaria de forma consistente; no
  degrada significativamente ningún segmento relevante; el sesgo está dentro de la banda declarada; el
  entrenamiento es reproducible.
- **Dependencias:** US-053
- *Fase 5 (2026-10-05):* niveles 1–2 en F5c; criterios en `DT-079` (valores `OPEN` hasta G1); métrica primaria según `DT-078`.
- *G1 (2026-10-05):* **pendiente** (F5c, sin autorizar). Métrica primaria MASE (`DT-090`); valores de aceptación provisionales en `DT-091`; la banda de sesgo sigue sin valor.
- *F5c (2026-10-06):* en curso (`DT-092`): Holt, Holt-Winters, Croston, SBA y TSB evaluados en Nivel 1 y Nivel 2 con los criterios de `DT-091` y `DT-093`, **sin promoción**.
- *F5c (2026-10-06, implementada, pendiente de revisión):* Nivel 1 y Nivel 2 de los cinco candidatos y tabla automática de criterios en `docs/reports/fase5-f5c-candidatos-sintetico.md`; ninguno de los cinco cumple el criterio de unidades faltantes de Nivel 2 frente a la media móvil 13 (`SYNTHETIC`). Sin promoción. *(Corregido en la revisión del 2026-10-06: SES cumple todos los criterios; con (b) y (c), también TSB.)*

### US-055 — Cuantificación de la incertidumbre
- **Prioridad:** P0
- **Criterios de aceptación:** cada predicción incluye un intervalo con nivel de confianza declarado;
  la cobertura observada se aproxima a la nominal; el intervalo queda **disponible** para el motor de
  abastecimiento como una de las fuentes candidatas de incertidumbre (`DT-010`, `PENDIENTE`), no como
  la fuente ya decidida.
- **Dependencias:** US-054 · **Relacionado:** `DT-010`
- *Fase 5 (2026-10-05):* protocolo en `DT-082` (nivel 0,80; calibración por horizonte solo con cortes anteriores); tolerancia de cobertura `OPEN` (`DT-079`).
- *G1 (2026-10-05):* **pendiente** (F5c). Hasta entonces la banda de U3 es nominal 0,80 y no está validada; la tolerancia de cobertura sigue sin valor.
- *F5c (2026-10-06):* en curso (`DT-092`): cobertura del intervalo actual frente a una variante calibrada por horizonte; calibrado si queda entre 0,75 y 0,85 (`DT-093` punto 6). Solo decide el rótulo de la banda.
- *F5c (2026-10-06, implementada, pendiente de revisión):* el intervalo actual de la media móvil 13 queda entre 0,75 y 0,85 en los 14 horizontes de los cortes tardíos; rótulo recomendado «nominal 0,80; cobertura comprobada solo con datos SYNTHETIC». La Fase 7 no cambia.

### US-056 — Tratamiento de series con datos insuficientes
- **Prioridad:** P1
- **Criterios de aceptación:** todo SKU obtiene una estimación por una vía documentada; la salida
  indica el método usado y la confianza; ningún SKU queda sin predicción sin explicación.
- **Dependencias:** US-051
- *Fase 5 (2026-10-05):* el dataset 0.4.0 no tiene series cortas; solo recortes artificiales para validar el algoritmo (`docs/05` §20.3). `DT-P23` sigue abierta.
- *G1 (2026-10-05):* **pendiente**; `DT-P23` sigue abierta.

### US-058 — Evaluación de abastecimiento y comparación baseline vs. ML
- **Descripción:** Como responsable técnico, necesito medir si el forecast del modelo produce **mejores
  decisiones de abastecimiento** que el baseline, y no solo un error de pronóstico menor.
- **Prioridad:** P0
- **Criterios de aceptación:**
  - El motor se ejecuta en **simulación retrospectiva** sobre el histórico con un proveedor de forecast
    intercambiable.
  - Se calculan las métricas de Nivel 2 de `docs/05-motor-predictivo.md` §9.4.
  - Se comparan las dos ramas —baseline y ML— con **idénticas reglas, parámetros y cortes temporales**;
    lo único que cambia es el forecast.
  - El informe declara si la mejora de Nivel 1 se traduce en mejora de Nivel 2, **también cuando no lo hace**.
  - **No se fija ningún valor objetivo**: la comparación es relativa al baseline.
- **Dependencias:** US-046, US-050, US-054 · **Cubre:** RML-013 · **Relacionado:** `DT-020`
- *Añadida en la revisión 0.1: la estrategia de evaluación de Nivel 2 no tenía ninguna historia que la ejecutara.*
- *Fase 5 (2026-10-05):* protocolo del simulador en `DT-080` (F5b); OD-S1 a OD-S4 `ACEPTADA` y F5b autorizada (`DT-088`): simulación retrospectiva en bucle cerrado de los cuatro baselines con U1 sin cambios, sin elegir baseline oficial ni métrica.
- *G1 (2026-10-05):* el simulador está hecho (F5b, `docs/05` §20.5). La comparación con un modelo de ML queda **pendiente** de F5c y F5d. Con SES, el Nivel 2 no muestra una mejora distinguible del ruido (`DT-089`).
- *F5c (2026-10-06):* en curso (`DT-092`): los candidatos de F5c se simulan como ramas nuevas con las mismas reglas; la comparación es informativa y no promueve nada.
- *F5c (2026-10-06, implementada, pendiente de revisión):* 17 ramas simuladas (nueve modelos y las estrategias (b) y (c) de cuatro); paridad con F5b comprobada.

### US-057 — Versionado y persistencia de predicciones
- **Prioridad:** P0
- **Criterios de aceptación:** cada predicción se persiste con `as_of_date`, versión de modelo y
  método; **nunca se sobrescribe** una predicción anterior.
- **Dependencias:** US-054
- *Fase 5 (2026-10-05):* estados de `model_versions` sin migración nueva y promoción con aprobación humana (`DT-084`).
- *G1 (2026-10-05):* **pendiente** (F5d): no hay modelo que versionar ni promover.

---

## EPIC-07 — MLOps en Azure *(Fase 6)*

| ID | Historia | Prioridad |
|---|---|---|
| US-060 | Entrenamiento como job en Azure ML con seguimiento MLflow | P2 |
| US-061 | Registro y versionado de modelos en Azure ML | P2 |
| US-062 | Monitoreo de deriva y de desempeño en producción | P2 |
| US-063 | Procedimiento de reentrenamiento con promoción aprobada por humano | P2 |

**Dependencias:** EPIC-06. **Requiere autorización para provisionar recursos.**

---

## EPIC-08 — Interfaz web *(Fase 7)*

| ID | Historia | Prioridad | Criterio de aceptación principal |
|---|---|---|---|
| US-070 | Estructura base y navegación | P1 | Navegación completa, estados de carga y error |
| US-071 | Dashboard con acciones priorizadas | P1 | Muestra productos críticos ordenados por urgencia y el estado del último recálculo |
| US-072 | Vistas de productos e inventario | P1 | Filtros, paginación en servidor, filtro "por debajo del punto de reorden" |
| US-073 | Vista de recomendaciones con acciones | P1 | Permite atender, descartar **con motivo** o convertir en orden |
| US-074 | Detalle de producto con desglose del cálculo | P1 | El componente `CalculationBreakdown` muestra todos los términos |
| US-075 | Vista de predicciones con incertidumbre | P2 | Banda de incertidumbre visible; confianza baja señalada como tal |
| US-076 | Vistas de proveedores y riesgos | P2 | Comparación lead time acordado vs. observado |

**Dependencias:** EPIC-04, EPIC-05. `US-075` depende además de `US-055` (intervalo de predicción,
EPIC-06): sin él no hay banda de incertidumbre que mostrar.

---

## EPIC-09 — Seguridad *(Fase 8)*

| ID | Historia | Prioridad | Criterio de aceptación principal |
|---|---|---|---|
| US-080 | Autenticación con Entra ID | P0 | Sin token válido, 401 en todo endpoint protegido |
| US-081 | Autorización por roles | P0 | Cada rol accede exactamente a lo previsto; matriz completa probada |
| US-082 | Gestión de secretos y configuración | P0 | Sin secretos en el repositorio; la verificación se ejecuta desde esta fase y se integra en el pipeline con `US-111` (Fase 13) |
| US-083 | Registro de auditoría | P2 | Las acciones sensibles quedan registradas y no son modificables |

**Dependencias:** EPIC-04, EPIC-08. **Bloqueada por:** validación de roles con el negocio.

---

## EPIC-10 — IA generativa *(Fases 9–10)*

| ID | Historia | Prioridad | Criterio de aceptación principal |
|---|---|---|---|
| US-090 *(Fase 9)* | Índice documental en Azure AI Search | P3 | Búsqueda híbrida con cita de origen y permisos aplicados en la consulta |
| US-091 *(Fase 10)* | Explicación con Azure OpenAI | P2 | Toda cifra de la respuesta existe en el contexto entregado |
| US-092 *(Fase 10)* | Asistente conversacional | P3 — requisito `RF-021` reclasificado como PROPUESTA | Responde solo con datos del sistema; admite no saber |
| US-093 *(Fase 10)* | Guardarraíles y verificación de salida | P0 (dentro de la épica) | Las pruebas de inyección de prompt y de fuga pasan |

**Dependencias:** EPIC-05, EPIC-09. **US-090 bloqueada** si no existe corpus documental (ASSUMPTION-008).

---

## EPIC-11 — Analítica *(Fase 11)*

| ID | Historia | Prioridad | Criterio de aceptación principal |
|---|---|---|---|
| US-100 | Modelo dimensional para Power BI | P2 | Esquema en estrella sobre vistas dedicadas |
| US-101 | Informes de inventario y abastecimiento | P2 | KPIs definidos, con fecha de actualización visible |
| US-102 | Informes de proveedores y de calidad del pronóstico | P3 | Incluye sesgo y cobertura del intervalo |
| US-103 | Coherencia de métricas con la aplicación | P1 | **Cada KPI coincide con su equivalente en la aplicación** |

**Dependencias:** EPIC-03, EPIC-05, EPIC-06.

---

## EPIC-12 — DevOps *(Fases 12–13)*

| ID | Historia | Prioridad | Criterio de aceptación principal |
|---|---|---|---|
| US-110 | Contenedores y entorno local | P1 | Un comando levanta el sistema **sin credenciales de Azure** |
| US-111 | Pipeline de integración continua | P1 | Falla ante lint, tipado, pruebas o secretos detectados |
| US-112 | Build y publicación de imágenes | P2 | Imágenes etiquetadas con versión y commit |
| US-113 | Despliegue automatizado con OIDC | P2 | **Sin secretos de larga vida**; staging y producción con aprobación |
| US-114 | Migraciones automatizadas | P2 | Aplicadas en el despliegue con credencial dedicada |

**Dependencias:** EPIC-04, EPIC-08.

---

## EPIC-13 — Calidad y entrega *(Fases 14–15)*

| ID | Historia | Prioridad | Criterio de aceptación principal |
|---|---|---|---|
| US-120 | Pruebas end-to-end de flujos críticos | P1 | Los cinco flujos de `docs/13-testing.md` §9 pasan |
| US-121 | Pruebas de rendimiento | P2 | Se cumplen los objetivos con volumen representativo |
| US-122 | Pruebas de seguridad integrales | P1 | Sin hallazgos abiertos de severidad alta |
| US-123 | Simulación retrospectiva del motor | P2 | Estima desabastos y sobreinventario evitables sobre el histórico |
| US-124 | Documentación operativa y de usuario | P1 | Manuales probados; documentación coincide con el sistema real |

**Dependencias:** todas las anteriores.

---

## Historias bloqueadas por decisiones del negocio

Estas historias **no pueden completarse** sin una definición externa. Están identificadas para que no
se desbloqueen inventando el valor que falta:

| Historia | Bloqueo | Referencia |
|---|---|---|
| US-040 | Nivel de servicio objetivo y política de revisión | BR-X01, BR-X02 |
| US-040 | Metodología del stock de seguridad no decidida | `DT-010` (`PENDIENTE DE VALIDACIÓN`) |
| US-042 | Horizonte de cobertura más allá del ROP | BR-X13 |
| US-042 | Conversión semanal→días sin confirmar (calendario laboral) | `DT-019`, BR-X06 |
| US-042 (parcial) | Criterio de selección entre proveedores | BR-X05 — **no bloquea**: `BR-P07` define el comportamiento provisional (proveedor preferente + alternativas visibles) |
| US-043, US-044 | Umbrales de clasificación de riesgo | BR-X03 |
| US-081 | Validación de roles y mapeo con Entra ID | ASSUMPTION-010 |
| US-090 | Existencia de corpus documental | ASSUMPTION-008 |
| US-101 | Licencia y capacidad de Power BI | `docs/11-power-bi.md` §8 |

## Sprint 1 propuesto

Cuando se autorice el inicio de la Etapa 1, el conjunto coherente y **sin bloqueos externos** es:

`US-010` (diseño del dataset) → `US-011` (ingesta) → `US-012` (marcado de desabasto)

Es autocontenido, no depende de ninguna decisión del negocio y produce el insumo de todo lo demás.

## Etapa 2 — correspondencia con las unidades de implementación

*Añadido el 2026-09-30.* El orden en que se construyen las historias está en `project/roadmap.md`
(tabla de unidades, `DT-047`: `ACEPTADA` en cuanto a U1, `PROPUESTA` para U2–U6). Las historias no cambian: las unidades las agrupan.
En particular, **US-040 (sin `σ_L`: V1 ignora `BR-P02`), US-041, US-042 y la parte de cálculo de US-045** forman U1 y se construyen
**sin** los bloqueos de negocio de la tabla anterior gracias a las reglas provisionales de `DT-031`,
que solo valen dentro del entorno sintético; **US-043 y US-044 siguen bloqueadas** por `BR-X03`.
