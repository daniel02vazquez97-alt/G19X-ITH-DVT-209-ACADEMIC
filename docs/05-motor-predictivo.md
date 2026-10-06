# 05 — Motor predictivo (estrategia de Machine Learning)

**Estado:** Versión 1.0 — Etapa 0 (estrategia, no implementada) · **Fecha:** 2026-09-04 · **Versión 1.1** — revisada en la auditoría de Etapa 0.1 · **Versión 1.2** (2026-09-30) — §19, contrato de `ForecastProvider` para la Etapa 2 (`DT-046`); §§1–18 no cambian · **Versión 1.3** (2026-10-02) — `DT-046` `ACEPTADA`; §19.8 y §19.9, decisiones y criterios de cierre de U3 (`DT-056`, `DT-057`); nota de V1 en §6 · **Versión 1.4** (2026-10-02) — §19.10, registro de la implementación de U3; ninguna decisión cambia · **Versión 1.5** (2026-10-03) — `DT-P21` cerrada por `DT-058`: frecuencia de §2 leída como una ejecución de forecast por corte de recomendación; §19.7 · **Versión 1.6** (2026-10-05) — §20: protocolo y decisiones de la Fase 5 (`DT-071` a `DT-085`); notas en §2, §6, §8, §9.1, §10, §11 y §19.8. Fase 5 **no autorizada** (condiciones en §20.4) · **Versión 1.7** (2026-10-05) — §20.3: población por corte a la fecha (`DT-087`) y cortes no independientes (nota de `DT-079`) · **Versión 1.8** (2026-10-05) — §20.3: segmentación sobre la vida activa de cada serie (nota de `DT-077`) · **Versión 1.9** (2026-10-05) — §20: F5b autorizada (`DT-088`); OD-S1 a OD-S4 `ACEPTADA` · **Versión 1.10** (2026-10-05) — §20.1: F5b implementada, pendiente de revisión

> **No se implementa ningún modelo en esta etapa.** Este documento fija la estrategia, las reglas de
> evaluación y los criterios de aceptación **antes** de entrenar, para que la evaluación no se ajuste
> después al resultado obtenido.

---

## 1. Qué se predice

**Demanda futura por producto (SKU).** Nada más.

El motor predictivo **no** predice cuánto comprar, ni cuándo, ni a quién. Esa es la responsabilidad
del motor de abastecimiento (`docs/06-motor-abastecimiento.md`). Esta frontera es un requisito
arquitectónico (RML-012, RNF-001), no una preferencia de diseño.

## 2. Definición formal del problema

| Elemento | Definición |
|---|---|
| **Variable objetivo** | Cantidad demandada del producto en el periodo, en su unidad de medida |
| **Identificador de serie** | `(product_id, location_id)`. Con ubicación única (ASSUMPTION-006) equivale a `product_id` |
| **Unidad temporal** | Diaria como granularidad de almacenamiento; **semanal** como granularidad de modelado por defecto (ver §3) |
| **Horizonte** | Debe cubrir al menos *lead time + periodo de revisión*. **PENDIENTE DE VALIDACIÓN**: su valor depende de los lead times reales y de la política de revisión (`BR-X02`), ninguno definido. Valor de trabajo provisional: 8–12 semanas (ASSUMPTION-002) |
| **Frecuencia de generación** | Semanal para todo el catálogo; bajo demanda para un producto concreto. El **recálculo de recomendaciones es diario** y consume el forecast vigente (`docs/06`). *Desde el 2026-10-03 (`DT-058`, cierra `DT-P21`):* el forecast sigue siendo **semanal** como granularidad, con semanas ancladas en `as_of_date + 1`; lo que se hace por corte es la **ejecución**: cada recomendación con corte `t` consume el forecast con `as_of_date = t` (`forecast --as-of t` y después `recommend --as-of t`). U4 no lanza forecasts implícitamente, no desplaza ni reancla semanas y no convierte granularidades. En V1 solo existe el corte del dataset (`2025-12-31`), por lo que no se generan forecasts diarios |
| **Tipo de problema** | Pronóstico de series temporales, multiserie, con incertidumbre |
| **Salida** | Estimación puntual + intervalo de predicción + método usado + versión de modelo + `as_of_date` |

### Demanda, no venta

Lo que el histórico registra es **demanda satisfecha**. En periodos de desabasto, la demanda real fue
mayor. Si se entrena directamente sobre la venta observada, el modelo aprende que "la demanda cayó"
justo en los productos que más importan, y el sistema recomendará comprar de menos precisamente
donde ya falló.

Tratamiento: los periodos marcados con `is_stockout_affected` se consideran **censurados**. Opciones
a evaluar en la Fase 5 (decisión pendiente, `DT-011`): excluirlos de la métrica, imputarlos, o tratar
la observación como cota inferior. Sea cual sea la elegida, debe documentarse y ser explícita. *(2026-10-05: la Fase 5 compara (a) consumo tal cual, (b) exclusión e (c) imputación con el mismo protocolo, `DT-081`; la observación censurada no se evalúa en esta fase.)*

## 3. Granularidad

**Propuesta:** almacenar en diario, **modelar en semanal**.

Razones:
- La decisión de compra opera en escala de semanas (lead times de días a semanas), no de horas.
- La demanda diaria a nivel de SKU suele tener muchos ceros; agregar a semana reduce ruido sin
  perder la señal relevante para la decisión.
- Se conserva el detalle diario en la base para poder cambiar de granularidad sin volver a cargar datos.

**Excepción:** productos de muy alta rotación con lead time corto pueden justificar modelado diario.
Se evaluará con datos, no por adelantado. Estado: `PROPUESTA` (`DT-008`).

### 3.1 Conversión entre el pronóstico semanal y un lead time en días

Modelar en semanas y registrar los lead times en días crea un hueco que **debe cerrarse
explícitamente**: un lead time de 10 días no equivale a un número entero de semanas.

```
Lead time = 10 días        Forecast = F₁, F₂, F₃, … (semanal)
¿Cuál es la demanda esperada durante esos 10 días?
```

Si esta regla no está escrita, dos personas implementarán dos fórmulas y el sistema dará dos cifras
para la misma pregunta. Las alternativas, su comparación y la recomendación están en **`DT-019`**.

Resumen operativo:

- **Recomendación provisional:** prorrateo uniforme — semanas completas más la fracción proporcional
  de la siguiente. Con `L = 10 días`: `F₁ + (3/7)·F₂`.
- **Supuesto que introduce:** demanda uniforme dentro de la semana (`ASSUMPTION-019`). Si el negocio
  no opera todos los días, o el histórico diario muestra un perfil intra-semanal marcado, esta regla
  sesga y debe sustituirse por el prorrateo según ese perfil.
- **Estado:** `PENDIENTE DE VALIDACIÓN`, dependiente del calendario laboral (`BR-X06`).
- **Regla de implementación no negociable:** la conversión vive en **una sola función** del
  `supply_engine`. Ningún otro módulo, consulta ni informe la reimplementa.

## 4. Segmentación del catálogo

No todos los SKU admiten el mismo tratamiento. Antes de modelar se clasifica cada serie:

| Segmento | Criterio orientativo | Tratamiento previsto |
|---|---|---|
| **Regular** | Histórico suficiente, demanda frecuente, variabilidad moderada | Modelo principal |
| **Estacional** | Patrón estacional detectable | Modelo con componente estacional |
| **Intermitente** | Alta proporción de periodos con demanda cero | Métodos específicos para demanda intermitente (p. ej. Croston y variantes) — evaluar en Fase 5 |
| **Errático** | Frecuente pero con coeficiente de variación muy alto | Baseline robusto + intervalos amplios; confianza declarada baja |
| **Nuevo / histórico corto** | Menos de N periodos (N a definir con datos) | Analogía por categoría o baseline; confianza declarada baja |
| **Descontinuado** | Sin demanda reciente y producto inactivo | Excluido de la predicción |

Esta clasificación es en sí misma información útil para el planificador, y va en la salida.
La clasificación cuantitativa habitual en la literatura combina la frecuencia de la demanda con su
variabilidad; los umbrales concretos se calibrarán con datos reales, no se fijan aquí.

## 5. Variables potenciales y features

### 5.1 Disponibles desde el inicio

| Grupo | Ejemplos |
|---|---|
| **Rezagos (lags)** | Demanda de los periodos anteriores (1, 2, 4, 8, 52 semanas) |
| **Ventanas móviles** | Media, mediana, desviación y máximo de las últimas *k* semanas |
| **Tendencia** | Pendiente reciente, ratio entre ventanas corta y larga |
| **Calendario** | Semana del año, mes, trimestre, número de días hábiles, festivos (**pendiente**: calendario del negocio) |
| **Estacionalidad** | Índices estacionales, codificación cíclica (seno/coseno) |
| **Atributos del producto** | Categoría, clase de rotación, clase ABC, unidad de medida |
| **Contexto de disponibilidad** | Indicador de desabasto en el periodo (para censura, **no** como predictor directo del futuro) |

### 5.2 Deseables, sujetas a disponibilidad

Precio y promociones, eventos comerciales, cartera de pedidos, información de clientes, indicadores
externos. **Ninguna se asume disponible.** Si el negocio no las aporta, no se inventan.

### 5.3 Variables conocidas antes y después del momento de predicción

Distinción imprescindible para evitar fuga temporal. Una variable solo puede usarse como *feature* si
su valor está disponible **en el instante en que se genera la predicción**.

| Tipo | Definición | Ejemplos | Uso como feature |
|---|---|---|---|
| **Conocidas de antemano** (*known future*) | Su valor futuro se conoce con certeza en el momento de predecir | Calendario, día de la semana, mes, festivos declarados, promociones ya planificadas y comunicadas | ✅ Sí, incluso para periodos futuros |
| **Observadas hasta el corte** (*past observed*) | Solo se conocen hasta `as_of_date`; su valor futuro es desconocido | Demanda pasada, inventario, rezagos, medias móviles, lead times observados | ✅ Sí, pero **solo con valores anteriores al corte** |
| **Conocidas únicamente a posteriori** | Su valor se conoce después del periodo que se quiere predecir | Demanda realizada del periodo, si hubo desabasto en ese periodo, venta final, recepciones posteriores | ❌ **Nunca** como predictor |

**Trampa frecuente en este dominio:** el indicador de desabasto del periodo *t* pertenece a la tercera
categoría. Es legítimo usarlo para **tratar la observación de entrenamiento** como censurada
(`DT-011`), pero **no** como variable explicativa del futuro: en el momento de predecir no se sabe si
habrá desabasto. Confundir ambos usos produce un modelo excelente en evaluación e inútil en producción.

### 5.4 Reglas de construcción de features (RML-004)

1. Toda feature en el instante *t* usa exclusivamente información disponible **hasta** *t*.
2. Las ventanas móviles se calculan desplazadas: nunca incluyen el periodo que se predice.
3. Las agregaciones por categoría o global se calculan **dentro** de cada partición de entrenamiento,
   nunca sobre el dataset completo.
4. Toda normalización o escalado se ajusta solo con datos de entrenamiento.
5. Existe una prueba automatizada que verifica el alineamiento temporal. Si falla, no hay entrenamiento.

Regla práctica: si una feature no podría calcularse el lunes por la mañana con la información
existente ese lunes, no puede usarse.

### 5.5 Precaución de uso del dataset sintético — warm-up del generador

*Aplica **solo** al dataset sintético de la Fase 1. No es una regla de negocio ni un requisito nuevo
de ML: es una característica declarada del generador. Decisión: `DT-036` §5.*

El generador de inventario dimensiona el saldo de apertura de cada producto y su demanda reciente con
una **ventana congelada de los primeros `W = 28` días** de la serie. Durante esa ventana, y solo
durante ella, los eventos de abastecimiento del producto dependen de demanda posterior al día
simulado.

**Consecuencia práctica:** al entrenar sobre este dataset, **excluir los primeros `W` días de la serie
de cada producto** cuando se utilicen features derivadas de:

- órdenes de compra,
- inventario,
- tránsito,
- abastecimiento en general.

Fuera de esa ventana no aplica. Y **no aplica en ningún caso** a las features derivadas de la demanda
o del consumo: ambas series se generan sin mirar hacia delante, y no están afectadas.

Con datos reales esta precaución desaparece, porque desaparece el generador.

## 6. Baseline

**Obligatorio y permanente.** No es un trámite: es la referencia contra la que se juzga todo lo demás
y el mecanismo de respaldo cuando el modelo no está disponible (RNF-010).

Baselines a implementar:

| Baseline | Definición |
|---|---|
| **Naïve** | La demanda del próximo periodo es la del último |
| **Naïve estacional** | La demanda es la del mismo periodo del ciclo anterior |
| **Media móvil** | Media de las últimas *k* semanas |
| **Suavizado exponencial simple** | Ponderación decreciente del histórico |

El baseline de referencia oficial se elige entre estos según su desempeño global, y queda registrado
en `ModelVersion` con `is_baseline = true`.

> **V1 (U3, `DT-056`, 2026-10-02).** La media móvil de 13 semanas se registra como referencia
> provisional de V1. Esta elección es operativa y reversible y no implica que sea el baseline de mejor
> desempeño. La selección definitiva por desempeño corresponde a la Fase 5, con la regla de este
> apartado. En V1 las tres versiones de baseline llevan `is_baseline = true` y la condición de
> referencia queda en cada ejecución (`calculation_runs.reference_model_version_id`, `DT-057`).
>
> **Fase 5 (2026-10-05):** el baseline oficial se elige en la puerta G1, con la métrica primaria y antes de evaluar candidatos (`DT-071`, `DT-076`).

## 7. Modelos candidatos

Orden de exploración deliberadamente incremental (`DT-009`):

| Nivel | Familia | Cuándo considerarlo |
|---|---|---|
| 0 | Baselines (§6) | Siempre. Punto de partida y respaldo |
| 1 | Suavizado exponencial / ETS, ARIMA estacional | Series regulares con tendencia y estacionalidad claras |
| 2 | Métodos para demanda intermitente (Croston y variantes) | Segmento intermitente |
| 3 | Modelos de regresión global sobre features tabulares (árboles con boosting) | Cuando conviene un modelo único multiserie que aproveche atributos de producto |
| 4 | Modelos secuenciales / redes neuronales | **Solo** si los niveles anteriores se agotan y hay volumen de datos que lo justifique |

Criterio de parada: **si el nivel N no aporta mejora medible sobre el nivel N−1, no se avanza.**
La complejidad se paga en mantenimiento, tiempo de entrenamiento, explicabilidad y riesgo operativo.

Nota sobre el enfoque global: un único modelo entrenado sobre todas las series con el producto como
característica suele comportarse mejor que miles de modelos individuales cuando hay muchos SKU con
histórico corto, y es mucho más barato de operar. Es la dirección preferida para el nivel 3, pero
debe demostrarse contra el nivel 1, no asumirse.

## 8. Estrategia de validación temporal

**Partición aleatoria prohibida** (RML-003).

Esquema: **rolling origin / backtesting con ventana deslizante**.

```
Corte 1: entrena [t0 ................ T1] → evalúa (T1, T1+h]
Corte 2: entrena [t0 ................... T2] → evalúa (T2, T2+h]
Corte 3: entrena [t0 ...................... T3] → evalúa (T3, T3+h]
                                                   ...
```

Reglas:

1. Mínimo 3–5 cortes; el número final se fija con la longitud real del histórico.
2. Entre entrenamiento y evaluación se respeta un **gap** igual al horizonte, para simular la
   disponibilidad real de la información. *(Aclaración 2026-10-05, `DT-075`: no es una zona muerta; no se
   eliminan semanas entre entrenamiento y evaluación y cada horizonte `h` se evalúa contra su semana real.)*
3. La métrica reportada es la agregación sobre todos los cortes, **con su dispersión**. Un promedio
   sin dispersión oculta modelos inestables.
4. El último tramo del histórico se reserva como **holdout final**, usado una sola vez, al cerrar la
   selección de modelo. Si se usa para decidir, deja de ser holdout.
5. El mismo esquema se aplica al baseline y a todos los candidatos, sin excepción.
6. **La evaluación se realiza también al horizonte del intervalo de protección** (`L`, o `L + R`), no
   solo a un paso. Es el horizonte del que depende el stock de seguridad (`DT-010`), y el error
   acumulado sobre él no se deduce del error a un paso sin supuestos que hay que comprobar.

## 9. Métricas y evaluación

Declaradas **antes** de entrenar (RML-005).

La evaluación se organiza en **dos niveles** (`DT-020`). El Nivel 1 mide si el pronóstico acierta; el
Nivel 2 mide si produce **mejores decisiones de abastecimiento**. El Nivel 2 es el decisorio: es la
pregunta que el proyecto existe para responder.

### 9.1 Nivel 1 — calidad del pronóstico

| Métrica | Para qué sirve | Justificación de su inclusión |
|---|---|---|
| **MAE** | Error absoluto medio por serie | Interpretable en las unidades del producto; es lo que entiende un planificador |
| **RMSE** | Penaliza más los errores grandes | Un error grande aislado puede costar un desabasto; MAE lo diluye |
| **MASE** | Error escalado frente a un baseline ingenuo | Comparable entre series de escalas distintas y **definida cuando la demanda es cero**. Su valor frente a 1 dice directamente si el modelo supera al baseline |
| **RMSSE** | Variante escalada basada en el error cuadrático | Misma comparabilidad que MASE, penalizando más los errores grandes |
| **WAPE** | Error agregado ponderado por volumen | Refleja el impacto conjunto sobre el negocio, no el promedio entre SKU |
| **Sesgo (Bias / MPE)** | Error **con signo**, acumulado | **Imprescindible.** Un sesgo persistente a la baja produce desabastos crónicos aunque el error absoluto sea bajo. No lo detecta ninguna métrica de error absoluto |
| **Cobertura del intervalo** | % de observaciones dentro del intervalo declarado | Valida la incertidumbre, que es exactamente lo que consume el stock de seguridad (`DT-010`) |
| MAPE | Solo informativo | **Descartada como métrica de decisión** (`DT-021`): indefinida con demanda cero y asimétrica entre sobre y subestimación |

**Métrica primaria: PENDIENTE** (`DT-021`). No se fija aquí. Elegirla antes de conocer la composición
real del catálogo —qué proporción es intermitente, qué dispersión de escalas hay— sería fijar un
criterio de aceptación sin la información que lo justifica. `DT-021` define los cinco criterios que
deberá cumplir y las candidatas que los satisfacen (MASE, RMSSE, WAPE agregada).

Hasta esa decisión, el informe de evaluación reporta **el conjunto completo** y ninguna métrica se
presenta como criterio único. *(2026-10-05: la métrica primaria se fija en la puerta G1 de la Fase 5, antes de
evaluar candidatos y del *holdout*, con el procedimiento de `DT-078`; `DT-021` sigue abierta.)*

### 9.2 Reporte obligatorio de Nivel 1

1. Todas las métricas de §9.1, con su **dispersión entre cortes** (un promedio sin dispersión oculta
   modelos inestables).
2. **Desglose por segmento** (§4). Un modelo puede ser excelente en alta rotación e inútil en los SKU
   críticos, y el promedio global lo esconde.
3. El resultado del **baseline** en la misma evaluación, siempre.
4. Métricas al horizonte de un paso **y** al horizonte del intervalo de protección (§8, regla 6).

### 9.3 Por qué el Nivel 1 no basta

Un modelo puede reducir el error de pronóstico y **empeorar** el abastecimiento. Tres formas de que
ocurra, todas plausibles:

- Mejora el promedio pero introduce sesgo a la baja en los SKU críticos: menos error, más desabastos.
- Reduce el error puntual a costa de una incertidumbre peor calibrada; como el stock de seguridad se
  calcula a partir de esa incertidumbre, el resultado empeora.
- Mejora en los SKU de bajo valor, que son mayoría y dominan el promedio, y empeora en los pocos que
  concentran el impacto económico.

Si solo se mide el Nivel 1, estos casos pasan inadvertidos y se promueve un modelo peor.

### 9.4 Nivel 2 — calidad de la decisión de abastecimiento

Se miden sobre las recomendaciones que el motor produce a partir del forecast, en **simulación
retrospectiva** sobre el histórico.

| Métrica | Definición |
|---|---|
| **Tasa de desabasto** (*stockout rate*) | Proporción de SKU-periodo con demanda y sin existencia |
| **Nivel de servicio alcanzado** | Demanda satisfecha ÷ demanda total. Se reporta también, por separado, la proporción de ciclos sin agotamiento |
| **Inventario medio** | Existencia media a lo largo del periodo simulado, en unidades y en valor |
| **Exceso de inventario** | Inventario por encima del umbral de cobertura de política |
| **Rotación** | Consumo del periodo ÷ inventario medio |
| **Órdenes urgentes** | Órdenes que habrían tenido que emitirse con lead time inferior al normal |
| **Costo de inventario** | Requiere el costo de mantener inventario (`BR-X04`, pendiente) |
| **Costo de faltante** | Requiere el costo de faltante (`BR-X04`, pendiente) |

> **No se fija ningún valor objetivo.** El negocio no ha proporcionado ninguno, y este documento **no
> establece** metas del tipo "desabasto < 5 %" ni "nivel de servicio ≥ 95 %". Aquí se define
> **qué medir**, no cuánto hay que alcanzar. Los objetivos son `BR-X01` y siguientes, pendientes.
>
> Las dos últimas métricas solo son calculables cuando el negocio aporte los costos. Hasta entonces la
> comparación se hace en unidades físicas y en incidencias, que ya permiten decidir.

### 9.5 Comparación end-to-end: baseline frente a ML

Ningún modelo se promueve sin esta comparación (`DT-020`, criterio 9 de §10):

```mermaid
flowchart LR
    H[(Histórico hasta el corte)] --> B[Baseline Forecast]
    H --> M[ML Forecast]
    B --> SE1[Supply Engine<br/>mismas reglas, mismos parámetros]
    M --> SE2[Supply Engine<br/>mismas reglas, mismos parámetros]
    SE1 --> R1[Recomendaciones A]
    SE2 --> R2[Recomendaciones B]
    R1 --> S1[Simulación sobre el histórico]
    R2 --> S2[Simulación sobre el histórico]
    S1 --> C{Métricas de Nivel 2<br/>comparadas}
    S2 --> C
```

Condiciones para que la comparación sea válida:

1. **Lo único que cambia es el forecast.** Mismas reglas, mismos parámetros de política, mismos datos
   de inventario y lead time, misma versión del motor. Cualquier otra diferencia invalida la conclusión.
2. Ambas ramas se ejecutan sobre los **mismos cortes temporales** del backtesting.
3. Se reporta la diferencia **por segmento**, no solo agregada.
4. Se declara explícitamente si la mejora de Nivel 1 se traduce o no en mejora de Nivel 2. **Cuando no
   se traduce, ese hallazgo se documenta**: es información valiosa sobre el sistema, no un fracaso que
   ocultar.

Requisito de diseño que esto impone: `supply_engine` debe poder ejecutarse en modo simulación con un
proveedor de forecast intercambiable. Está contemplado en `DT-003` (interfaz `ForecastProvider`) y en
`DT-020`, y es la razón de que el motor sea una biblioteca pura.

## 10. Criterios de aceptación de un modelo

Un modelo pasa a producción **solo si cumple todo lo siguiente**:

1. Supera al baseline en la métrica primaria, de forma consistente en la mayoría de los cortes.
2. No degrada de manera significativa ningún segmento relevante frente al baseline.
3. El sesgo se mantiene dentro de la banda declarada (sin sesgo sistemático).
4. La cobertura del intervalo se aproxima al nivel nominal declarado.
5. Supera las pruebas de ausencia de leakage (RML-004).
6. Su entrenamiento es reproducible (RML-009).
7. Su tiempo de inferencia para todo el catálogo cabe en la ventana operativa del proceso batch.
8. Está registrado con versión, métricas, ventana de datos e hiperparámetros.
9. **Supera al baseline también en la evaluación de Nivel 2** (§9.4–9.5): produce decisiones de
   abastecimiento mejores o equivalentes, y no empeora ninguna métrica de Nivel 2 de forma
   significativa. Un modelo que mejora el error de pronóstico y empeora el servicio **no se promueve**.

Los **umbrales numéricos concretos** (p. ej. "MASE < X") **no se fijan aquí**, ni en Nivel 1 ni en
Nivel 2: fijarlos sin datos sería inventar un requisito. Se establecerán al cerrar la Fase 1 con el
dataset disponible y se registrarán como decisión (`PENDIENTE`, ver `DT-P04` y `DT-021`). *(Nota 2026-10-05: no se fijaron al cerrar la Fase 1. Se fijan en la puerta G1 de la
Fase 5 (`DT-078`, `DT-079`); los valores propuestos, incluido el 5 %, siguen `OPEN`.)*

El criterio 9 no exige alcanzar un valor absoluto, sino **superar o igualar al baseline** en las
mismas condiciones. Es una comparación relativa, que sí puede evaluarse sin objetivos del negocio.

## 11. Entrenamiento

- **Dónde:** local en fases tempranas; como *job* en Azure Machine Learning cuando el proyecto llegue
  a la Fase 6. La lógica de entrenamiento es la misma; cambia el ejecutor.
- **Reproducibilidad:** semilla fija, versión de datos, versión de código (commit), hiperparámetros y
  entorno registrados en cada ejecución.
- **Seguimiento:** experimentos y métricas registrados con MLflow. **No es una tecnología añadida al
  stack:** es el mecanismo de seguimiento nativo de Azure Machine Learning, que sí figura en el stack
  obligatorio, y por eso no requiere ADR propio. El seguimiento es el mecanismo de seguimiento
  soportado nativamente por Azure Machine Learning. *(2026-10-05, `DT-073`: sin MLflow en la Fase 5; versionado
  manual con `model_versions` e informes en `docs/reports/`, como prevé `docs/03` §16. MLflow llega con la Fase 6.)*
- **Datos:** solo información anterior al corte de entrenamiento. Prohibido reentrenar sobre el holdout.
- **Frecuencia inicial propuesta:** mensual, o por disparo ante deriva (§15).

## 12. Evaluación y promoción

```mermaid
flowchart LR
    D[Datos hasta corte] --> TR[Entrenamiento]
    TR --> BT[Backtesting rolling origin]
    BT --> CMP{¿Supera al baseline<br/>y cumple criterios §10?}
    CMP -->|No| REJ[status = REJECTED<br/>se conserva el registro]
    CMP -->|Sí| HO[Holdout final · uso único]
    HO --> OK{¿Se confirma?}
    OK -->|No| REJ
    OK -->|Sí| REG[Registro como candidato]
    REG --> APR[Aprobación humana]
    APR --> PRD[status = PRODUCTION]
```

La promoción a producción **requiere aprobación humana**. No hay promoción automática por métrica en
la primera versión: el costo de un modelo malo en producción (desabastos) supera al de una revisión manual.

## 13. Versionado

- Cada modelo entrenado genera un registro `ModelVersion` (`docs/04-modelo-datos.md`).
- Cada `Forecast` referencia la versión que lo generó. Una versión referenciada **nunca se elimina**.
- El registro local se sincroniza con el registro de modelos de Azure ML mediante `external_ref`.
- Estados: `TRAINING` → `EVALUATED` → (`PRODUCTION` | `REJECTED`) → `ARCHIVED`.
- Como máximo un modelo en `PRODUCTION` por objetivo de predicción.

## 14. Despliegue

- **Modo principal: inferencia por lotes.** El proceso programado genera las predicciones de todo el
  catálogo y las persiste. Es lo que la decisión de compra necesita: no requiere latencia baja.
- **Inferencia en línea:** solo si aparece una necesidad real (recálculo interactivo). Se expondría
  como *managed online endpoint* de Azure ML, detrás de la interfaz `ForecastProvider`.
- **Respaldo obligatorio:** si el modelo no está disponible o su calidad cae bajo el umbral, se usa el
  baseline y la salida lo indica con `method_used = BASELINE` (RNF-010). El sistema nunca se queda
  sin predicción, y nunca finge que la predicción degradada es normal.

## 15. Monitoreo

| Qué se vigila | Cómo |
|---|---|
| **Desempeño real** | Error de la predicción contra la demanda efectivamente observada, por segmento |
| **Sesgo acumulado** | Tendencia del error con signo a lo largo del tiempo |
| **Deriva de datos** | Cambio en la distribución de las features de entrada respecto a la ventana de entrenamiento |
| **Deriva de predicción** | Cambio en la distribución de las salidas |
| **Salud operativa** | Ejecuciones fallidas, SKU sin predicción, proporción de uso del baseline |
| **Cobertura del intervalo** | Proporción real de observaciones dentro del intervalo declarado |

Azure Machine Learning ofrece monitoreo de modelos en producción con señales de deriva de datos y de
degradación de desempeño; se usará esa capacidad en lugar de construir una propia. La verificación
de su configuración concreta se hará contra la documentación oficial vigente en la Fase 6.

**Alertas:** cuando una métrica supera su umbral, se notifica y se registra. Ninguna alerta dispara
por sí sola un cambio de modelo en producción.

## 16. Reentrenamiento

Disparadores:

1. **Programado:** frecuencia inicial propuesta mensual, ajustable con evidencia.
2. **Por deriva:** al superarse un umbral de deriva de datos o de degradación de desempeño.
3. **Por cambio estructural del negocio:** nuevas líneas de producto, cambio de proveedor relevante,
   cambio de política. Decisión humana.

El modelo reentrenado **no sustituye automáticamente** al vigente: pasa por la misma evaluación
(§12) y debe superar tanto al baseline como al modelo en producción (RML-011).

## 17. Riesgos específicos del componente predictivo

| Riesgo | Mitigación |
|---|---|
| Sobreajuste al dataset sintético | El dataset sintético no decide la arquitectura definitiva; revalidación obligatoria con datos reales |
| Fuga temporal que infla las métricas | Prueba automatizada de alineamiento; gap en el backtesting; holdout de uso único |
| Sesgo por desabasto (demanda censurada) | Marca `is_stockout_affected` y tratamiento explícito (§2) |
| Métricas engañosas en demanda intermitente | Métrica primaria robusta ante ceros; desglose por segmento |
| Modelo excelente en promedio e inútil en los SKU críticos | Evaluación por segmento obligatoria |
| Complejidad injustificada | Criterio de parada por nivel (§7) |
| Deterioro silencioso en producción | Monitoreo continuo y respaldo automático al baseline |

## 18. Fuera del alcance de este componente

- Predicción de precios o costos.
- Predicción de lead time (se trata estadísticamente en el motor de abastecimiento, no con ML, hasta
  que haya evidencia de que lo requiere).
- Optimización de la decisión de compra.
- Detección de anomalías como producto independiente (se usa internamente para limpiar el histórico).

## 19. Contrato de `ForecastProvider` (Etapa 2)

*Añadido el 2026-09-30. Decisión: `DT-046`, **`ACEPTADA` el 2026-10-02** al autorizar U3, junto con
`DT-056` (baselines) y `DT-057` (persistencia y ejecución); detalle en §19.8 y §19.9. **U3 está
implementada y validada** desde el 2026-10-02 (§19.10); no hay entrenamiento.
(Hasta el 2026-10-02 decía «`PROPUESTA` — diseñado, no implementado».)*

### 19.1 Frontera

```text
consumo diario hasta as_of_date ──►  ForecastProvider  ──►  demanda semanal estimada + incertidumbre
                                     (baseline o modelo)      + método + versión + as_of_date
```

El proveedor **solo** estima demanda. Su salida no contiene cantidades a comprar, puntos de reorden,
stock de seguridad, proveedores ni fechas de pedido (RML-012). El motor la consume como una entrada
más (`docs/06` §16).

### 19.2 Petición

| Campo | Contenido |
|---|---|
| Serie | `(product_id, location_id)`; con ubicación única equivale al producto (ASSUMPTION-006) |
| `as_of_date` | Último día cuya información se conoce, incluido (`docs/06` §16.2, `DT-P15`) |
| Histórico | Consumo **diario** con fecha ≤ `as_of_date`, con su `is_stockout_affected`. **El proveedor rechaza** una petición con cualquier fecha posterior: el corte se comprueba en el contrato, no se confía al llamador (RML-004) |
| Horizonte | Número de semanas. Debe cubrir el horizonte de cobertura más largo del motor: con las reglas V1, `⌈(LT_MAX_v1 + R_v1) / 7⌉ = ⌈97 / 7⌉ = 14` semanas. Es un valor **derivado**, no elegido, y supera las 8–12 semanas de `ASSUMPTION-002`: es la limitación que `V1-03` ya declara |
| Atributos | Opcionales (categoría, unidad), solo si el método los usa |

### 19.3 Respuesta

| Campo | Contenido |
|---|---|
| `as_of_date`, `granularity = WEEKLY` | — |
| `periods[]` | `period_start`, `period_end` (excluido), `predicted_quantity ≥ 0`, `lower_bound ≤ predicted ≤ upper_bound`, `confidence_level`. Periodo `k` = `[horizon_start + 7(k−1), horizon_start + 7k)` con `horizon_start = as_of_date + 1` (`DT-P15`, cerrada): semanas **ancladas en el primer día del horizonte**, no de calendario, para que `demand_over_horizon` sea exacta (`V1-04`) |
| `method_used` | `MODEL` · `BASELINE` · `INTERMITTENT_METHOD` (RML-007) |
| `confidence_flag` | Confianza declarada o «histórico insuficiente» |
| Versión | `model_version` → `model_versions` (el baseline también tiene versión, `is_baseline = true`) |

El histórico se agrega a semanas con la misma alineación, hacia atrás desde `as_of_date`:
`[as_of_date − 6, as_of_date]`, la anterior, etc. La agregación diaria → semanal del **histórico**
es parte del proveedor; la conversión semanal → días del **forecast** es exclusiva del motor
(`docs/06` §5.1).

### 19.4 Persistencia y trazabilidad

Cada ejecución es una `calculation_runs` de tipo `FORECAST` con `as_of_date`, `data_load_id` y
`model_version_id`; cada periodo es una fila de `forecasts` que **nunca** se sobrescribe (§3.14 de
`docs/04`). El forecast se persiste **antes** de que el motor lo consuma (`docs/03` §5.1). Desde
cualquier recomendación se llega a la versión de modelo y al dataset (`docs/04` §9.6).

### 19.5 Implementaciones

| Implementación | Cuándo | Nota |
|---|---|---|
| Local, en proceso: baselines (`US-050`) | U3 | Naïve, naïve estacional, media móvil. Siempre disponible; es el respaldo (RNF-010) |
| Modelo entrenado localmente | Fase 5 | Detrás de la misma interfaz; solo si supera al baseline en Nivel 1 y Nivel 2 (§10) |
| Endpoint de Azure ML | Fase 6 | Detrás de la misma interfaz; ante fallo, baseline con `method_used = BASELINE` |

### 19.6 Reglas que el contrato hace cumplir

1. `demand` (demanda latente) **no** es entrada ni *feature* del proveedor: no existe con datos
   reales (`DT-034`). Solo la lee la evaluación de Nivel 2 y el estudio de `DT-011`.
2. `is_stockout_affected` sirve para **tratar** la observación como censurada (`DT-011`), nunca como
   predictor del futuro (§5.3).
3. En el dataset sintético, la precaución de *warm-up* de §5.5 aplica a las *features* de
   abastecimiento, no a las de consumo.
4. Reproducible: mismo histórico, mismo `as_of_date`, misma versión → mismo forecast.

### 19.7 Pendiente

`DT-P17` quedó **cerrada** el 2026-10-02 por `DT-056` (§19.8). `DT-P21` (cómo se concilia el forecast semanal de §2 con el recálculo diario de recomendaciones cuando
las semanas se anclan en el primer día del horizonte) quedó **cerrada** el 2026-10-03 por `DT-058`: un
forecast por corte de recomendación, sin forecast implícito desde U4 (§2). Siguen abiertos: `DT-021` (métrica primaria) y `DT-P04` (umbrales de aceptación) siguen
abiertos y se cierran en la Fase 5 con el dataset 0.4.0; `DT-011` (tratamiento del desabasto) y `DT-P23`
(productos sin histórico suficiente) también siguen abiertos. RF-010 exige intervalo: **no se implementa
un baseline sin decidir antes cómo lo produce** —decidido en `DT-056`—.

### 19.8 Decisiones de U3 (`DT-056`, `DT-057`)

*Aceptadas el 2026-10-02 al autorizar U3. U3 quedó **implementada** el mismo día (§19.10). Etiquetas:
**Aceptado** = respaldado por una decisión aceptada o cerrada antes de U3; **Derivado** = se sigue de
reglas aceptadas; **Nueva** = decisión tomada al autorizar U3.*

| ID | Decisión | Contenido | Fuente | Tipo |
|---|---|---|---|---|
| D-01 | Referencia | La media móvil de 13 semanas se registra como referencia provisional de V1. Esta elección es operativa y reversible y no implica que sea el baseline de mejor desempeño. La selección definitiva por desempeño corresponde a la Fase 5 (§6) | US-050; `DT-056` | Nueva |
| D-02 | Intervalo | Cuantiles empíricos nearest-rank del error histórico del mismo método a cada horizonte; `L_h = max(0, F_h + min(q_lo, 0))`, `U_h = F_h + max(q_hi, 0)` | RF-010; `DT-010` (c)/(d) | Nueva |
| D-03 | `confidence_level` | `0.80`, con cuantiles del 10 % y el 90 %. Es el nivel nominal del intervalo: no constituye una garantía ni una medición empírica de cobertura, no es un nivel de servicio y no está calibrado; la calibración y validación de cobertura corresponden a la Fase 5. No se reutiliza `z_v1 = 1,65` | `DT-056` | Nueva |
| D-04 | Mínimo de errores | Con la regla de cuantiles nearest-rank 10/90 adoptada para el nivel nominal 0.80, mínimo operacional de 11 errores por horizonte para que exista al menos una observación en cada cola (`m = 11` → `q_lo = e_(2)`, `q_hi = e_(10)`). No es una estimación universal; la cobertura real se evalúa en la Fase 5 | D-03 | Derivado de D-02 y D-03 |
| D-05 | Longitud estacional | `L = 52` semanas | `DT-046` (anclaje) | Nueva |
| D-06 | Media móvil | `k = 13` semanas; sin reducir la ventana | §6 | Nueva |
| D-07 | Fórmulas y agregación | Semanas completas ancladas en `A`; naïve `F_h = Y_n`; estacional `F_h = Y_{n+h−52}`; media móvil `F_h = media(Y_{n−12} … Y_n)`; días sobrantes más antiguos descartados | `DT-046`; `DT-048` | Nueva (detalle) |
| D-08 | Mínimos y respaldo | Naïve 25 semanas, media móvil 37, naïve estacional 63; serie primaria: media móvil → naïve → sin forecast | RF-010; RML-007 | Nueva |
| D-09 | Sin histórico suficiente | Menos de 25 semanas: sin forecast, motivo en la ejecución; U1 devolverá `FORECAST_MISSING`; la estimación para este caso es `DT-P23` | RML-007; US-056 | Nueva |
| D-10 | Desabasto | El consumo observado puede subrepresentar la demanda potencial durante episodios de desabasto. En V1 se utiliza como proxy observable del consumo/demanda satisfecha, sin corrección ni imputación (`stockout_treatment = "NONE_RAW_CONSUMPTION_V1"`); `is_stockout_affected` viaja en la petición y no modifica el cálculo; cambiarlo exige versión nueva; `DT-011` sigue abierta | `DT-011`; `DT-P14` | Nueva (provisional) |
| D-11 | Catálogo | U3 pronostica productos activos y vigentes en `as_of_date`, con histórico contiguo; U1 realiza posteriormente su propia validación de vigencia sobre el horizonte concreto de la recomendación. Exclusiones con motivo (`INACTIVE_OR_OUT_OF_VALIDITY`, `INVALID_HISTORY`), sin imputar | `DT-049`; §4 | Nueva |
| D-12 | Precisión | `Fraction` interna; salida `Decimal` con 6 decimales, `ROUND_HALF_EVEN`; nunca `float` | `DT-051`; `DT-052` | Nueva |
| D-13 | `model_versions` | Una fila por baseline, `1.0.0`; campos de entrenamiento, métricas y `status` en `NULL` | `docs/04` §3.13; §13 | Nueva |
| D-14 | `calculation_runs` | Columnas de `DT-057`; `reference_model_version_id`; `config_sha256`; `summary` | `docs/04` §4 y §9.6 | Nueva |
| D-15 | `forecasts` | Clave única por ejecución; CHECK de orden y escala; inmutables | `docs/04` §3.14 y §9.6 | Nueva |
| D-16 | C9 | Una ejecución; tres series por producto; `is_primary` | `docs/04` §9.6 | Nueva |
| D-17 | C8 | `ALREADY_COMPUTED` con la misma `config_sha256`, sin escribir | Patrón de U2 | Nueva |
| D-18 | Frontera | `forecasting` puro; `runs` lee, registra y persiste (C4, C5) | `DT-043`; `DT-046` | Aclaración |
| D-19 | `as_of_date` | `python -m app.runs forecast --as-of AAAA-MM-DD`; primera ejecución `2025-12-31`; sin backtesting | `docs/03` §16.7 | Nueva |
| D-20 | Horizonte | 14 semanas; prevalece `DT-046` sobre `ASSUMPTION-002` (C3) | `V1-03`; `DT-048` | Derivado |
| D-21 | `confidence_flag` | `STANDARD` · `INSUFFICIENT_HISTORY` | `docs/04` §3.14 | Nueva |
| D-22 | Cierre de U3 | Criterios de §19.9 | `DT-047` | Nueva |

*Nota (2026-10-05): D-12 tiene una **enmienda acotada** por `DT-074`: `float` solo dentro de `ml/` y de un
proveedor de modelo, con frontera determinista a `Decimal`. Los baselines de U3 y el contrato siguen exactos.*

### 19.9 Criterios de cierre de U3

1. **Contrato:** 14 semanas ancladas en `A + 1`, rechazo de fechas `> A`, salida `Decimal`, sin `float`
   (`DT-046`).
2. **Baselines:** pruebas con valores calculados a mano para los tres; fronteras de 24/25, 36/37 y 62/63
   semanas; semana parcial más antigua descartada.
3. **Intervalos:** regla nearest-rank con `m = 11` y con `m` grande; recorte en 0; inclusión del punto con
   errores del mismo signo; series constante, de ceros e intermitente.
4. **Respaldo:** cadena media móvil → naïve → sin forecast; `confidence_flag` y motivos en `summary`.
5. **Leakage:** alterar el consumo posterior a `A` no cambia la salida; fechas `> A` rechazadas.
6. **Reproducibilidad:** dos ejecuciones dan salida idéntica; `0 ≤ L ≤ F ≤ U` y escala `≤ 6`.
7. **Pureza:** `forecasting` solo importa la biblioteca estándar (ni `db` ni `supply_engine`).
8. **Migración `0002`:** desde cero y sobre `0001`; idempotente; control `sha256`.
9. **Esquema:** restricciones, FK, índices parciales y *triggers* de inmutabilidad probados.
10. **Versionado:** tres filas en `model_versions`, registradas una vez; `hyperparameters` distintos para
    la misma versión → error.
11. **Ejecución real** sobre el dataset 0.4.0 con `A = 2025-12-31`: una ejecución `COMPLETED`; 95
    productos con forecast y 5 excluidos (`INACTIVE_OR_OUT_OF_VALIDITY`); 3 990 filas (95 × 3 × 14);
    1 330 primarias de la media móvil; ningún respaldo.
12. **Idempotencia y *rollback*:** la repetición da `ALREADY_COMPUTED` sin escribir; un fallo inyectado
    deja `FAILED` y ninguna fila de forecast.
13. **Trazabilidad:** `forecast → calculation_run → data_load` devuelve `ds-6c8ad65b4999`.
14. **Pruebas:** suite por defecto, integración contra PostgreSQL (local y Docker), U1 en verde y
    generador sin tocar.
15. **Compatibilidad con U1, solo en pruebas:** con las series primarias se construye el `Forecast` de U1
    y `evaluate()` no lanza `InvalidInputError` en ninguno de los 95 productos. Ninguna ruta de producción
    entre U1 y U3.

No se exige ninguna métrica de calidad del forecast: pertenecen a la Fase 5.

### 19.10 Implementación (U3, 2026-10-02)

*Registro de hechos de implementación. No cambia ninguna decisión de §19.8.*

| Pieza | Dónde |
|---|---|
| Contrato: `ForecastRequest` (validada al construirse), `build_request`, `ForecastResult`, `BaselineDefinition` | `backend/app/forecasting/contract.py` |
| Aritmética exacta (`Fraction`) y cuantización entera a 6 decimales *half-even* | `backend/app/forecasting/exact.py` |
| Semanas completas ancladas en `as_of_date` | `backend/app/forecasting/weekly.py` |
| Los tres baselines, sus versiones y la cadena primaria | `backend/app/forecasting/baselines.py` |
| Errores por horizonte, cuantiles nearest-rank y límites | `backend/app/forecasting/interval.py` |
| Proveedor (`forecast`, `LocalBaselineProvider`) | `backend/app/forecasting/provider.py` |
| Configuración, `config_sha256` y clave del bloqueo | `backend/app/runs/config.py` |
| Ejecución y persistencia | `backend/app/runs/forecast.py` · `python -m app.runs forecast --as-of AAAA-MM-DD` |
| Esquema | `backend/db/migrations/0002_forecast_tables.sql` (`docs/04` §9.10) |

**Uso**, desde `backend/` con `DATABASE_URL` definida: `python -m app.db migrate` y
`python -m app.runs forecast --as-of 2025-12-31`. Termina con 0 en `COMPLETED` y `ALREADY_COMPUTED`, y con 1
en `FAILED` o si la ejecución se rechaza antes de empezar (sin carga `COMPLETED`, fecha fuera del
`time_range` de la carga, esquema ausente o versión de baseline registrada con otra definición), caso en
el que no se escribe nada.

**Detalles técnicos concretados al implementar** (no normativos):

- **Población candidata:** productos × ubicaciones. Motivos de exclusión: `INACTIVE_OR_OUT_OF_VALIDITY` e
  `INVALID_HISTORY`, con el detalle `GAP`, `DUPLICATE_DATE`, `FUTURE_DATE` o `INCOMPLETE_HISTORY`. Sin
  forecast: `INSUFFICIENT_HISTORY`.
- **`summary`** (`jsonb`): `dataset_version`, `data_load_id`, `as_of_date`, `catalog_policy`, `reference`,
  `model_versions`, `candidates`, `eligible`, `excluded` (con motivo), `excluded_count`,
  `excluded_by_reason`, `forecasted`, `primary_by_model`, `series_by_model`, `fallback`, `fallback_count`,
  `no_forecast`, `no_forecast_count`, `unavailable_series`, `forecast_rows` y `primary_rows`. En una
  ejecución `FAILED`: `as_of_date` y `model_versions`; el error va en `error` (`type`, `message` y, si
  aplica, `sqlstate`).
- **`config_sha256`:** SHA-256 del JSON canónico (claves ordenadas, separadores compactos, UTF-8) de los
  modelos con sus `hyperparameters`, la referencia, la cadena primaria, el horizonte, la granularidad,
  `method_used`, `confidence_level`, la cuantización y la política de catálogo.
- **Bloqueo *advisory*:** clave de 64 bits con signo, tomada de los 8 primeros bytes del SHA-256 de
  `[FORECAST, as_of_date, data_load_id, config_sha256]`.
- **Registro de `model_versions`:** en su propia transacción, antes del bloqueo. Si el registro falla, no
  queda ninguna fila parcial.
- **Marcas de tiempo:** `generated_at` toma por defecto `transaction_timestamp()`, el mismo instante para
  todas las filas de una ejecución; `started_at` es el reloj de la base al empezar.
- **Identificadores:** una ejecución revertida consume el identificador de su intento; los `id` de
  `calculation_runs` pueden tener huecos.

**Resultados** (2026-10-02):

- **Ejecución real** con `as_of_date = 2025-12-31` sobre `ds-6c8ad65b4999`: `COMPLETED`, 95 productos con
  forecast, 5 excluidos, 3 990 filas, 1 330 primarias de la media móvil, ningún respaldo.
- **Repetición:** `ALREADY_COMPUTED`, con el mismo identificador y sin filas nuevas.
- **Fallo controlado** con corte 2025-12-30 en la base de desarrollo: `FAILED` y ninguna fila.
- **Mismos resultados** en el PostgreSQL 16 local y en el contenedor `postgres:16-alpine` de
  `infra/docker-compose.yml`.
- **Pruebas:** `tests/forecasting` (60) y `tests/runs` (7), en la suite por defecto; `tests/db/test_forecast_*`
  (32), en la de integración. Las pruebas de U2 se ampliaron solo para contar con la migración `0002`.

## 20. Fase 5 — protocolo de evaluación y decisiones (`DT-071` a `DT-085`)

*Añadido el 2026-10-05 en el cierre documental de la Fase 5. **La Fase 5 no está autorizada para
implementación, salvo F5a y F5b** (`DT-086`, `DT-088`): el resto depende de las decisiones que se enumeran en §20.4. Toda evidencia de la fase
es `SYNTHETIC` y debe revalidarse con datos REAL.*

### 20.1 Unidades y puertas

| Unidad | Contenido | Necesita |
|---|---|---|
| F5a | Backtesting, Nivel 1, segmentación, suavizado exponencial simple y comparación de baselines (sin candidatos). **Autorizada** (`DT-086`) | — |
| F5b | Simulador de Nivel 2 aplicado a los baselines. **Autorizada** (`DT-088`; OD-S1 a OD-S4 `ACEPTADA` en `DT-080`); implementada el 2026-10-05 en `ml/simulation/`, pendiente de revisión (`docs/reports/fase5-f5b-nivel2-sintetico.md`) | F5a |
| F5c | Modelos de niveles 1–2, estudio de `DT-011` e intervalos | F5a, F5b y G1 |
| F5d | Estudio de `DT-010` y, si procede, promoción e integración | F5c, G2 y G3 |

Las puertas G1 (antes de evaluar candidatos), G2 (*holdout* de uso único) y G3 (aprobación humana) están
definidas en `DT-071`.

### 20.2 Respuestas del contrato

| # | Pregunta | Respuesta |
|---|---|---|
| 1 | Qué se implementa en F5a–F5d | §20.1 y `DT-071` |
| 2 | De qué depende cada unidad | §20.1 |
| 3 | Dependencias de Python permitidas | Solo la biblioteca estándar en F5a–F5c; el nivel 3 exige una decisión nueva (`DT-073`) |
| 4 | Dónde se permite `float` | Solo en `ml/` y en un proveedor de modelo (`DT-074`) |
| 5 | Cómo se convierte `float` al contrato | `Decimal(x)` exacto, cuantizado a 6 decimales `ROUND_HALF_EVEN`, sin corregir valores inválidos (`DT-074`) |
| 6 | Cómo se hacen los 17 backtests | Semanas 64 a 128, cada 4 semanas, 14 semanas de horizonte y ventana expansiva (`DT-075`) |
| 7 | Qué pasa con el *holdout* | Corte 2025-09-24, uso único en G2, nunca para elegir nada (`DT-075`) |
| 8 | Qué métrica y cuándo se fija | Una de MASE, RMSSE o WAPE, fijada en G1 antes de evaluar candidatos; `DT-021` sigue `OPEN` (`DT-078`) |
| 9 | Cómo se acepta o rechaza un modelo | Nivel 1 mejora y Nivel 2 no se degrada; valores numéricos `OPEN` hasta G1 (`DT-079`) |
| 10 | Cómo funciona el simulador de Nivel 2 | `DT-080`; OD-S1 a OD-S4 `ACEPTADA` (`DT-088`): bucle cerrado; órdenes en `suggested_order_date` que llegan tras el `L` usado por el motor; demanda latente, ventas perdidas y desabasto por día con unidades faltantes; inventario medio relativo al baseline sin umbral absoluto |
| 11 | Cómo se trata el desabasto en la simulación | Ventas perdidas = demanda latente − consumo simulado; sin pedidos pendientes; inventario nunca negativo (`DT-080`) |
| 12 | Cómo se estudia `DT-011` | Estrategias (a), (b) y (c) con el mismo protocolo; la latente solo como verdad (`DT-081`) |
| 13 | Cómo se estudia `DT-010` | Alternativas (a)–(e) en simulación, sin tocar U1 (`DT-083`) |
| 14 | Cómo se calibran los intervalos | Nivel 0,80; variante por horizonte ajustada con cortes anteriores (`DT-082`) |
| 15 | Cómo se promueve un modelo | G2 más aprobación humana (G3); proveedor tras `ForecastProvider` (`DT-084`) |
| 16 | Cómo se versiona | `model_versions` con los estados existentes, sin migración `0004`, más informes en `docs/reports/` (`DT-073`, `DT-084`) |
| 17 | Qué pasa si ningún modelo gana | No se promueve nada; el baseline oficial sigue y se documenta el hallazgo (`DT-084`) |
| 18 | Cómo se mantiene el respaldo | Baseline con `method_used = BASELINE` por serie y siempre disponible (`DT-084`, `RNF-010`) |
| 19 | Qué evidencia es solo `SYNTHETIC` | Toda la de la Fase 5, en especial la que usa la demanda latente y los recortes de `DT-P23` |
| 20 | Qué decisiones quedan fuera de la Fase 5 | Niveles 3 y 4; cambios de U1 (nueva `engine_version`); `DT-P02` y Azure ML (Fase 6); costes (`BR-X04`); objetivos de servicio (`BR-X01`) |

### 20.3 Aclaraciones a secciones anteriores

- **§8, regla 2 («gap»):** no hay zona muerta; cada horizonte se evalúa contra su semana real (`DT-075`).
- **§9.1 y §10:** `DT-021` y `DT-P04` debían fijarse al cerrar la Fase 1 y no se fijaron. Se fijan en G1 con
  `DT-078` y `DT-079`.
- **§11:** sin MLflow en la Fase 5; el versionado es manual (`DT-073`).
- **§19.8, D-12:** enmienda acotada por `DT-074`; los baselines siguen exactos.
- **Nivel 1 con días imputados o excluidos:** la verdad nunca es un valor imputado; el consumo observado es censurado y se informa también sin las semanas con desabasto; la demanda latente, solo con datos `SYNTHETIC` (`DT-076` punto 2, `DT-081`).
- **§2 y `DT-011`:** la Fase 5 compara (a), (b) y (c); la alternativa (d) no se evalúa (`DT-081`).
- **Población por corte (`DT-075` punto 6):** se toma «a la fecha» del corte, por vigencia y sin `is_active`, que es
  una foto del final del dataset; la regla literal de U3 queda como alternativa comparada (`DT-087`, ACEPTADA).
  El `is_active` de los proveedores tampoco tiene historial: las series sin proveedor preferente activo quedan fuera
  de `L + R` y dentro de `h = 1`.
- **Cortes no independientes:** las ventanas de evaluación de cortes consecutivos se solapan (14 semanas cada 4);
  ver la nota de `DT-079`.
- **Segmentación (`DT-077`):** el «19 intermitentes» de la medición orientativa era un artefacto de contar como cero
  las semanas posteriores a `valid_to`; la segmentación definitiva se calcula sobre la vida activa de cada serie
  (nota de `DT-077`).
- **`DT-P23`:** el dataset 0.4.0 no tiene series cortas. Si hay que probar el comportamiento, se recortan series
  artificialmente, solo para validar el algoritmo y nunca como evidencia de comportamiento real.

### 20.4 Condiciones abiertas para autorizar la Fase 5

| Decisión | Contenido | Cuándo |
|---|---|---|
| OD-S1 a OD-S4 (`DT-080`) | **`ACEPTADA`** el 2026-10-05 (`DT-088`). Queda pendiente la discrepancia entre el punto 7 de `DT-080` (`expected_on`) y OD-S1 («llegadas reales») para las líneas abiertas al primer corte | Antes de cerrar F5b |
| `DT-077` | Umbrales de segmentación y criterio de estacionalidad | G1 |
| `DT-079` / `DT-P04` | 2/3 de los cortes, **5 %**, banda de sesgo, tolerancia de cobertura y tolerancia de «igual» en el Nivel 2 | G1 |
| `DT-078` / `DT-021` | Elección de la métrica primaria con el procedimiento aceptado | G1 |
| `DT-081` | Estimador de imputación y agregación de los días excluidos | G1 |
| `DT-076`, punto 7 | Detalle del suavizado exponencial simple | Revisión de F5a |
| `DT-083` | Vía para comparar las alternativas (c) y (d) de `DT-010`: U1 no las expone (bloqueo) | Antes del estudio de `DT-010` (F5d) |
