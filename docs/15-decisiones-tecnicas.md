# 15 — Decisiones técnicas (ADR)

**Estado:** Versión 1.0 — Etapa 0 · **Fecha:** 2026-09-04 · **Versión 1.1** — revisada en la auditoría de Etapa 0.1 · **Versión 1.2** (2026-09-18) — `DT-024` a `DT-030`, preparación del Componente 2 · **Versión 1.3** (2026-09-19) — `DT-031`, reglas mínimas de V1 · **Versión 1.4** (2026-09-21) — cierre de las reglas V1: `DT-031` pasa a `ACEPTADA` con trece reglas · **Versión 1.5** (2026-09-21) — `DT-032` y `DT-033`, decisiones que el Componente 2 tenía que tomar al implementarse · **Versión 1.6** (2026-09-21) — tabla canónica de identificadores de componente en `DT-030` · **Versión 1.7** (2026-09-23) — `DT-034` y `DT-035`, demanda latente persistente y sus políticas de generación · **Versión 1.8** (2026-09-24) — `DT-036` y `DT-037`, políticas sintéticas de inventario y comportamiento de proveedores; **enmienda de `DT-027`** (restricción 3) y cierre del pendiente de `data_origin` de `DT-026` · **Versión 1.9** (2026-09-24) — `DT-038` y `DT-039`, contratos de salida de los Componentes 4 y 5, tras la auditoría pre-implementación; cierre de los pendientes de `DT-034` (recorte de la demanda y contrato de `consumption.csv`) y correcciones a `DT-036` y `DT-037` · **Versión 1.10** (2026-09-26) — cierre de D-01: `DT-040` (publicación atómica del dataset, W1), regla general de incremento de `generator_version` en `DT-033`, y actualizaciones de `DT-036`, `DT-038` y `DT-039` (A2, B2, `expected_at`, autoría de los identificadores) · **Versión 1.11** (2026-09-26) — implementación del Componente 4: enmienda de `DT-037` §3 (D-C4-1, reparto de la entrega partida) y actualización de `DT-038` (D-C4-2 precondiciones, D-C4-3 lead time y disparo diario, flujos pseudoaleatorios, `metrics` pendiente) · **Versión 1.12** (2026-09-27) — cierre de D-01, opción A: elegibilidad de las órdenes `CANCELLED` sintéticas respecto de `valid_to` (`DT-039` §5.2) · **Versión 1.13** (2026-09-28) — implementación del Componente 5 (`DT-039` §13), sin cambios en ninguna regla · **Versión 1.14** (2026-09-28) — implementación del Componente 6 (`DT-037` §6, decisiones A1 y A2) y corrección de texto en `DT-040` §3 · **Versión 1.15** (2026-09-29) — implementación de W1 (`DT-040` §9, detalles pendientes resueltos) y `generator_version` 0.3.0 · **Versión 1.16** (2026-09-29) — `DT-041`, contrato e implementación del Componente 7 (sin integrar en W1); notas de redacción en `DT-030` y `DT-031` (`V1-07`, `V1-08`) · **Versión 1.17** (2026-09-29) — `DT-042`, validador del dataset e informe de calidad; integración de C7 y C8 en W1 (`DT-040`); `generator_version` 0.4.0 (`DT-033`); formas de `scenario_assignment` y `quality_report` (`DT-025`); `metrics` de `DT-038` §12 cerrado · **Versión 1.18** (2026-09-30) — Etapa 2, arquitectura y fundación: `DT-043` a `DT-047` (todas `PROPUESTA`) y pendientes `DT-P13` a `DT-P21` · **Versión 1.19** (2026-09-30) — autorización de U1: `DT-043` y `DT-045` `ACEPTADA`, `DT-047` `ACEPTADA` en cuanto a U1; `DT-P15` y `DT-P20` cerradas; `DT-P14` abierta en parte y **bloquea U1** · **Versión 1.20** (2026-10-01) — `DT-P14` **cerrada** con el estimador poblacional, `INSUFFICIENT_HISTORY` para `n = 0` y la evaluación exacta B3 (`docs/06` §16.6); ninguna fórmula V1 cambia · **Versión 1.21** (2026-10-01) — cierre del contrato de U1: `DT-048` a `DT-052` `ACEPTADA` (aclaraciones A-1 en `DT-050` y A-2 en `DT-051`), y pendiente `DT-P22`; ninguna fórmula V1 ni regla B3 cambia · **Versión 1.22** (2026-10-01) — `DT-P22` `ACEPTADA` (opción (a)): `PRODUCT_OUT_OF_VALIDITY` cubre también la vigencia que termina dentro del horizonte; cierre de `DT-049`; ninguna fórmula V1 ni regla B3 cambia · **Versión 1.23** (2026-10-01) — `DT-053` (frontera de la salida parcial) y `DT-054` (sin monotonía global de `S` frente a `L` en V1), tras el audit de pre-codificación de U1; ninguna fórmula cambia · **Versión 1.24** (2026-10-01) — `DT-044` `ACEPTADA` (cantidades en `numeric`; `quantity_on_hand ≥ 0` compatible con `BR-X09`/`V1-13`); `DT-047` aceptada para U2; `DT-055` (entorno técnico de U2) · **Versión 1.25** (2026-10-02) — U3 autorizada para implementación: `DT-P17` cerrada por `DT-056` (baselines V1); `DT-046` `ACEPTADA`; `DT-057` (persistencia y ejecución del forecast); `DT-047` aceptada para U3; pendiente nueva `DT-P23` · **Versión 1.26** (2026-10-03) — cierre documental de U4 y autorización para implementación (no implementada): `DT-058` a `DT-063` `ACEPTADA`; `DT-P18` cerrada por `DT-059` y `DT-P21` por `DT-058`; `DT-047` aceptada para U4; nota en `DT-P16`, que sigue abierta · **Versión 1.27** (2026-10-03) — U4 implementada y validada: registro de la implementación en `DT-047` y en `DT-058` a `DT-063`; ninguna decisión cambia · **Versión 1.28** (2026-10-03) — U5 autorizada para implementación (no implementada): `DT-064` (dependencias), `DT-065` (autenticación local), `DT-066` (contrato de lectura) y `DT-067` (historia, desviación poblacional) `ACEPTADA`; `DT-047` aceptada para U5 · **Versión 1.29** (2026-10-03) — U5 implementada y validada: registro de la implementación en `DT-047` y en `DT-064` a `DT-067`; ninguna decisión cambia · **Versión 1.30** (2026-10-04) — U6 autorizada para implementación (no implementada): `DT-068` (entrega y contrato de la explicación) y `DT-069` (presentación, verificación y degradación de cifras) `ACEPTADA`; `DT-047` aceptada para U6 · **Versión 1.31** (2026-10-04) — U6 implementada y validada: registro de la implementación en `DT-047`, `DT-068` y `DT-069`; ninguna decisión cambia · **Versión 1.32** (2026-10-05) — Fase 7 autorizada para implementación (no implementada): `DT-070` (alcance, stack y versiones, autenticación local, contrato con la API, formato regional, proxy, partición F7a–F7d e integración con `main`) `ACEPTADA`; separada de `DT-047` · **Versión 1.33** (2026-10-05) — Fase 7 implementada: estado e implementación de `DT-070` · **Versión 1.34** (2026-10-05) — Fase 5, cierre documental (no autorizada): `DT-071` a `DT-085` (partición y puertas, `ml/`, dependencias, enmienda acotada de D-12, backtesting, Nivel 1, segmentación `PROPUESTA`, regla de `DT-021`, criterios `PROPUESTA`, simulador de Nivel 2 con decisiones `OPEN`, estudios de `DT-011` y `DT-010`, intervalos, promoción y Git); notas en `DT-010`, `DT-011`, `DT-021`, `DT-056`, `DT-P03`, `DT-P04` y `DT-P23`; `DT-086` autoriza F5a por separado; propuestas del responsable para OD-S1 a OD-S4, criterio serie-corte en `DT-078`, aclaración del Nivel 1 con días imputados y bloqueo de U1 para `DT-010` (`DT-083`) · **Versión 1.35** (2026-10-05) — `DT-087` `ACEPTADA` (población por corte a la fecha, enmienda de interpretación de `DT-075` punto 6); notas en `DT-075` y `DT-079` tras la revisión de F5a · **Versión 1.36** (2026-10-05) — notas en `DT-073` (JSON versionado como resumen) y `DT-077` (el «19 intermitentes» era un artefacto de `valid_to`) · **Versión 1.37** (2026-10-05) — `DT-088` autoriza F5b; OD-S1 a OD-S4 `ACEPTADA` en `DT-080` con sus refinamientos · **Versión 1.38** (2026-10-05) — `DT-080`: decisiones del responsable al cerrar F5b; nota en `DT-078` (las candidatas ordenan igual por serie-corte) · **Versión 1.39** (2026-10-05) — G1: `DT-089` (baseline oficial), `DT-090` (MASE) y `DT-091` (valores de aceptación), `ACEPTADA` y provisionales (`SYNTHETIC`); notas en `DT-010`, `DT-011`, `DT-021` (cerrada por `DT-090`), `DT-077`, `DT-079`, `DT-081`, `DT-P03` y `DT-P04` · **Versión 1.40** (2026-10-06) — `DT-092` autoriza F5c; `DT-093`, criterios complementarios de G1 (horizonte L + R, cortes comparables, tolerancias, banda de sesgo, cobertura, segmentación y estacionalidad, estimadores de `DT-081`, ajuste de modelos, Holt-Winters con 104 semanas y sustitución en el simulador); notas en `DT-071`, `DT-077` a `DT-082`, `DT-090` y `DT-091` · **Versión 1.41** (2026-10-06) — `DT-092`: registro de la implementación de F5c (pendiente de revisión); ninguna decisión cambia · **Versión 1.42** (2026-10-06) — revisión de F5c: `DT-093` puntos 12 a 14 (interpretaciones aceptadas, sensibilidad de cadencia, tabla de criterios con SES y por estrategia); nota en `DT-081` (conclusión provisional y propuesta de (b)) · **Versión 1.43** (2026-10-06) — `DT-094` (alcance de cierre de la Etapa 2: stack completo por unidades U7 a U16, Azure for Students, Bicep, corpus sintético) y `DT-095` (U7, Docker: autorizada; implementación pendiente de revisión) · **Versión 1.44** (2026-10-06) — `DT-096` (U8, CI con GitHub Actions: autorizada; implementación pendiente de revisión) y digests de las imágenes base en `DT-095`, pendientes de verificación externa · **Versión 1.45** (2026-10-06) — `DT-097` (U9, capa analítica de solo lectura y migración `0004`: autorizada; implementación pendiente de revisión)

Registro de decisiones arquitectónicas. Formato: ID, decisión, contexto, alternativas, razón,
consecuencias, estado.

## Estados

| Estado | Significado |
|---|---|
| `ACEPTADA` | Decisión tomada y vigente. Cambiarla requiere un nuevo ADR |
| `PROPUESTA` | Dirección razonada pero **no confirmada**. Es una hipótesis, no un requisito |
| `PENDIENTE` | Decisión identificada y deliberadamente **no tomada** todavía |
| `RECHAZADA` | Evaluada y descartada; se registra para no volver a debatirla sin nueva información |
| `SUPERSEDIDA` | Sustituida por otro ADR |

> Solo se marcan como `ACEPTADA` las decisiones que se derivan directamente del alcance dado por el
> responsable del proyecto o que son consecuencia necesaria de él. Todo lo demás es `PROPUESTA` o
> `PENDIENTE`. Confundir una hipótesis con una decisión firme es el error que este registro evita.

---

## DT-001 — Separación estricta entre predicción ML, reglas de negocio e IA generativa

- **Decisión:** El sistema mantiene tres capas con responsabilidades disjuntas. El modelo de ML solo
  estima demanda e incertidumbre; las reglas determinísticas calculan las cifras de abastecimiento;
  la IA generativa solo explica resultados ya calculados. Ningún LLM interviene en la ruta de cálculo.
- **Contexto:** Requisito explícito del alcance del proyecto. Es viable técnicamente pedirle a un LLM
  que recomiende cantidades de compra.
- **Alternativas:** (a) LLM como orquestador que calcula y decide. (b) Modelo de ML que predice
  directamente la cantidad a comprar. (c) Separación estricta.
- **Razón:** Las cifras de inventario deben ser exactas, reproducibles, auditables y defendibles. Un
  LLM no ofrece determinismo ni trazabilidad. Un modelo que predice la cantidad a comprar mezcla la
  incertidumbre estadística con la política de negocio y hace imposible ajustar una sin reentrenar la otra.
- **Consecuencias:** `supply_engine` es una biblioteca pura, testeable con casos exactos. Mayor
  disciplina de diseño. Toda recomendación es explicable término a término. El LLM aporta comprensión, no cálculo.
- **Estado:** `ACEPTADA`

## DT-002 — Monolito modular en el backend

- **Decisión:** Backend único en FastAPI con módulos internos de frontera clara, en lugar de microservicios.
- **Contexto:** Equipo pequeño, alcance en definición, sin requisitos de escala independiente.
- **Alternativas:** (a) Microservicios por dominio. (b) Monolito modular. (c) Funciones sin servidor.
- **Razón:** Los microservicios aportan escalado y despliegue independientes a cambio de complejidad
  operativa, latencia de red y consistencia distribuida. Nada en el alcance actual lo justifica. La
  modularidad interna preserva la opción de extraer un servicio más adelante si aparece la necesidad.
- **Consecuencias:** Despliegue y depuración simples. Exige disciplina en las fronteras de módulo. Se
  acepta la posibilidad de una extracción futura.
- **Estado:** `ACEPTADA`

## DT-003 — Dependencias de Azure encapsuladas tras interfaces propias

- **Decisión:** Azure ML, Azure OpenAI, Azure AI Search y Key Vault se consumen a través de interfaces
  propias (`ForecastProvider`, `TextGenerator`, `DocumentRetriever`, `SecretProvider`) con
  implementación local sustituta.
- **Contexto:** Etapa 0 prohíbe configurar servicios reales de Azure. Además, el sistema debe ser
  ejecutable y testeable en local (RNF-006) y degradar sin ellos (RNF-010).
- **Alternativas:** (a) Uso directo de los SDK en la lógica de negocio. (b) Encapsulación tras interfaces.
- **Razón:** Permite desarrollar y probar sin costos ni credenciales, aísla los cambios de API de los
  servicios (la superficie de Azure OpenAI ya ha cambiado de forma relevante) y hace posible la
  degradación controlada.
- **Consecuencias:** Una capa de indirección adicional, justificada. Pruebas sin red. Sustitución de
  proveedor acotada a una implementación.
- **Estado:** `ACEPTADA`

## DT-004 — Datos sintéticos en las primeras fases, con marca de origen

- **Decisión:** Se trabajará con datos sintéticos; toda entidad cargada lleva `data_origin`
  (`SYNTHETIC` / `REAL`) y ninguna regla de negocio depende de ese valor.
- **Contexto:** No hay datos reales disponibles (ASSUMPTION-001), y deben poder sustituirse sin
  rediseñar la aplicación (RF-023).
- **Alternativas:** (a) Esperar a datos reales. (b) Sintéticos sin marca. (c) Sintéticos con marca de origen.
- **Razón:** Esperar bloquea el proyecto. Sin marca de origen, mezclar sintéticos y reales corrompe el
  entrenamiento de forma indetectable.
- **Consecuencias:** Un campo adicional en las entidades cargadas. Ninguna métrica obtenida con datos
  sintéticos puede presentarse como evidencia de desempeño real.
- **Estado:** `ACEPTADA`

## DT-005 — Comunicación síncrona; sin mensajería asíncrona

- **Decisión:** Toda la comunicación entre componentes es síncrona. Los procesos largos se resuelven
  con un patrón de trabajo asíncrono sobre la propia base de datos (`202` + consulta de estado), sin
  intermediario de mensajería.
- **Contexto:** El sistema tiene procesos largos (recálculo, cargas) pero no eventos entre servicios
  independientes.
- **Alternativas:** (a) Cola de mensajes. (b) Orquestador de flujos. (c) Síncrono con seguimiento en base de datos.
- **Razón:** Una cola introduce un componente que operar, monitorear y depurar, y resuelve un problema
  que hoy no existe. Regla anti-sobreingeniería.
- **Consecuencias:** Menos piezas móviles. Si aparecen múltiples consumidores o necesidades de
  reintento sofisticado, se revisará esta decisión.
- **Estado:** `ACEPTADA`

## DT-006 — Histórico inmutable (append-only)

- **Decisión:** `InventoryMovement`, `Consumption` y `PurchaseOrderReceipt` no se actualizan ni se
  borran. Las correcciones se registran como nuevos hechos.
- **Contexto:** El sistema debe ser auditable y las predicciones y recomendaciones pasadas
  reconstruibles (RF-024, RNF-013).
- **Alternativas:** (a) Registros editables. (b) Editables con tabla de auditoría. (c) Inmutables.
- **Razón:** Si el histórico cambia, el entrenamiento deja de ser reproducible y una recomendación
  pasada no puede explicarse. Un ajuste registrado como hecho conserva además la información de que
  hubo una corrección, que en sí misma es un dato de calidad.
- **Consecuencias:** Mayor volumen. La posición de inventario se mantiene como estado calculado y debe
  conciliarse periódicamente.
- **Estado:** `ACEPTADA`

## DT-007 — Sin generación de SQL libre a partir de lenguaje natural

- **Decisión:** El asistente de IA no genera SQL. Las preguntas sobre datos se resuelven con un
  conjunto acotado de consultas predefinidas y parametrizadas.
- **Contexto:** El asistente debe responder preguntas sobre datos estructurados (CU-3).
- **Alternativas:** (a) *Text-to-SQL* con ejecución directa. (b) Consultas predefinidas parametrizadas.
- **Razón:** El SQL generado por un modelo es una superficie de ataque y, sobre todo, una fuente de
  respuestas **plausibles pero incorrectas** que nadie revisa. Un JOIN mal planteado devuelve un número
  creíble y equivocado.
- **Consecuencias:** Menor flexibilidad en las preguntas admitidas; el catálogo de consultas crece con
  el uso. Se gana seguridad y corrección verificable.
- **Estado:** `ACEPTADA`

## DT-008 — Granularidad semanal para el modelado

- **Decisión:** Almacenar el consumo en granularidad diaria y modelar en semanal.
- **Contexto:** La decisión de compra opera en escala de semanas; la demanda diaria por SKU suele tener muchos ceros.
- **Alternativas:** (a) Diaria. (b) Semanal. (c) Mensual.
- **Razón:** La semanal equilibra ruido y señal para el horizonte de decisión. Conservar el detalle
  diario permite cambiar de criterio sin recargar datos.
- **Consecuencias:** Menor resolución temporal en el pronóstico. Revisable por segmento con datos
  reales. **Consecuencia no trivial:** obliga a definir cómo se convierte un pronóstico semanal en
  demanda esperada sobre un lead time expresado en días — problema tratado por separado en `DT-019`,
  que esta decisión no puede dar por resuelto.
- **Estado:** `PROPUESTA` — a confirmar en la Fase 5 con datos.

## DT-009 — Progresión incremental de modelos con criterio de parada

- **Decisión:** Explorar los modelos por niveles (baseline → estadísticos → métodos para demanda
  intermitente → modelos tabulares globales → redes neuronales) y detenerse cuando un nivel no aporte
  mejora medible sobre el anterior.
- **Contexto:** Existe presión implícita hacia modelos sofisticados en proyectos con etiqueta de "IA".
- **Alternativas:** (a) Empezar por deep learning. (b) Elegir un modelo y ajustarlo. (c) Progresión con criterio de parada.
- **Razón:** La complejidad se paga en mantenimiento, tiempo de entrenamiento, explicabilidad y riesgo.
  Solo se justifica con mejora demostrada. Con muchas series de histórico corto, los métodos simples
  suelen ser competitivos.
- **Consecuencias:** Resultados útiles antes. Posible techo de desempeño si se detiene demasiado
  pronto; mitigado por la evaluación por segmento.
- **Estado:** `ACEPTADA`

## DT-010 — Fuente de la incertidumbre para el stock de seguridad

- **Decisión:** El **error de pronóstico observado** es una fuente legítima —y probablemente la más
  pertinente— de información sobre la incertidumbre que el stock de seguridad debe cubrir.
  **La metodología exacta para convertirlo en un valor de stock de seguridad queda PENDIENTE**: se
  determinará con datos, mediante backtesting, y se juzgará por su efecto sobre las métricas de
  abastecimiento, no solo sobre el error de pronóstico.

- **Contexto — cuatro conceptos que no deben confundirse.** La versión anterior de esta decisión los
  trataba de forma imprecisa. Son magnitudes distintas, con orígenes y usos distintos:

  | # | Concepto | Qué es | De dónde sale |
  |---|---|---|---|
  | 1 | **Variabilidad de la demanda** (`σ_D`) | Dispersión del fenómeno observado alrededor de su media | Serie histórica de consumo |
  | 2 | **Error de pronóstico** | Dispersión de los fallos del sistema al predecir, **a un horizonte dado** | Residuos del backtesting |
  | 3 | **Incertidumbre declarada por el modelo** | Intervalo de predicción que el propio modelo emite | Salida del modelo; **puede estar mal calibrada** |
  | 4 | **Variabilidad del lead time** (`σ_L`) | Dispersión del tiempo de entrega | Histórico de recepciones |

  Los cuatro son diferentes. (1) mide cuánto varía el mundo; (2) mide cuánto nos equivocamos al
  anticiparlo; (3) es lo que el modelo *cree* que se equivoca, que no es lo mismo que lo que se
  equivoca; (4) es independiente de los tres anteriores y entra en el cálculo por su propia vía.

- **Punto técnico determinante.** Lo que el stock de seguridad debe cubrir es el error **acumulado
  sobre el intervalo de protección** (`L`, o `L + R` en revisión periódica), no el error a un paso.
  Escalar el error de un paso multiplicándolo por `√L` **no es una identidad general**: en la
  literatura de referencia esa relación (`σ_h = σ·√h`) se deriva explícitamente para el método naïve
  y **bajo el supuesto de residuos no correlacionados y de varianza constante**, supuestos que los
  errores multi-horizonte suelen violar. Aplicarla sin comprobarla subestimaría el stock de seguridad
  justo donde más importa.

- **Alternativas:**
  | | Enfoque | Observación |
  |---|---|---|
  | (a) | Desviación histórica de la demanda (`σ_D`) | Sobreestima cuando el modelo predice bien una demanda variable |
  | (b) | Error de un paso escalado por `√L` | Descansa en supuestos que hay que verificar, no asumir |
  | (c) | Error **acumulado** sobre el intervalo de protección, estimado por backtesting a ese horizonte | Mide directamente lo que se quiere cubrir |
  | (d) | Cuantiles empíricos de la distribución de errores acumulados (no paramétrico) | No exige normalidad; adecuado en demanda asimétrica o intermitente |
  | (e) | Intervalo declarado por el modelo (concepto 3) | Solo válido si se verifica su calibración contra la cobertura observada |

- **Razón:** (c) y (d) son conceptualmente las más defendibles porque estiman la magnitud que
  realmente se quiere proteger, y (d) además evita el supuesto de normalidad, que no se sostiene en
  demanda intermitente. Pero **ninguna puede elegirse sin datos**: la comparación exige un backtesting
  al horizonte del intervalo de protección que todavía no existe.

- **Consecuencias:**
  1. El backtesting debe evaluarse **al horizonte del intervalo de protección**, no solo a un paso
     (afecta al diseño de la validación temporal, `docs/05-motor-predictivo.md` §8).
  2. La **calibración del intervalo** pasa a ser una métrica de primera clase, no un extra.
  3. La elección se decide comparando el efecto sobre las **métricas de Nivel 2** (`DT-020`):
     desabastos, inventario medio, nivel de servicio. Una fuente de incertidumbre que reduce el error
     de pronóstico pero empeora el servicio no es la correcta.
  4. Hasta que se decida, `docs/06-motor-abastecimiento.md` §6 documenta la formulación estándar como
     **punto de partida verificable**, no como fórmula oficial.

- **Estado:** `PENDIENTE DE VALIDACIÓN` — se resuelve en la Fase 5, con datos y con evaluación de
  Nivel 2. **Ninguna de las variantes (a)–(e) es todavía la fórmula del proyecto.**

- **Nota (2026-10-05):** la Fase 5 compara (a)–(e) solo en simulación, sin modificar U1 (`DT-083`); si una gana, el cambio del motor es una unidad posterior con nueva `engine_version`. Estado sin cambios.

- **Nota (2026-10-05, G1):** G1 no cambia esta decisión. El estudio de (a)–(e) sigue en F5d (`DT-083`) y sigue bloqueado: U1 solo implementa (a) (`V1-05`), y comparar (c) y (d) exige una unidad posterior de U1 (U1b en la decisión del responsable). Estado sin cambios.

## DT-011 — Tratamiento de la demanda censurada por desabasto

- **Decisión:** Marcar los periodos afectados por desabasto (`is_stockout_affected`) y darles un
  tratamiento explícito en el entrenamiento. El método concreto se decidirá con datos.
- **Contexto:** El histórico registra demanda satisfecha, no demanda real. Durante un desabasto, la
  demanda observada es una cota inferior.
- **Alternativas:** (a) Ignorarlo. (b) Excluir esos periodos. (c) Imputar. (d) Tratar como observación censurada.
- **Razón:** Ignorarlo enseña al modelo que la demanda cayó justo cuando faltó producto, sesgándolo a
  la baja precisamente en los SKU más críticos y perpetuando el desabasto. Elegir el método sin datos
  sería prematuro; **marcar el dato ahora** es lo que mantiene abiertas todas las opciones.
- **Consecuencias:** Un campo adicional que la ingesta debe poder derivar. Decisión de método diferida
  a la Fase 5.
- **Estado:** `PENDIENTE` (el marcado del dato es `ACEPTADA`; el método de tratamiento, pendiente)

- **Nota (2026-10-05):** protocolo de la Fase 5 en `DT-081`: se comparan (a) consumo tal cual, (b) exclusión y (c) imputación; (d) no se evalúa en la Fase 5. La demanda latente solo es verdad de evaluación y no existe con datos REAL. Estado sin cambios.

- **Nota (2026-10-05, G1):** G1 no fija el estimador de imputación ni la agregación de los días excluidos (`DT-081`); el estudio pertenece a F5c. Los baselines siguen con el consumo tal cual (alternativa (a), `DT-056` D-10). Estado sin cambios.

## DT-012 — Tránsito total frente a tránsito efectivo

- **Decisión:** Distinguir **conceptualmente** dos magnitudes que la versión anterior mezclaba:
  - **`total_in_transit`** — todo lo pedido y aún no recibido. Es un **hecho** sobre el mundo,
    independiente de cualquier decisión. Es lo que almacena `Inventory.quantity_in_transit`.
  - **`effective_in_transit`** — la parte de ese tránsito que se espera recibir **dentro del intervalo
    de protección de la decisión que se está evaluando**. Es una magnitud **relativa a una decisión**.

  `effective_in_transit` es un valor **derivado, calculado por `supply_engine`** en cada evaluación.
  **No se añade ninguna columna a la base de datos.**

- **Contexto:** Una orden cuya llegada se espera después del agotamiento previsto no evita el
  desabasto, pero sí eleva la posición de inventario y suprime la recomendación. Ese es un fallo
  silencioso: el sistema no recomienda comprar porque "ya viene en camino" algo que llegará tarde.

- **Por qué son conceptos distintos y no dos formas de contar lo mismo:** la misma orden es efectiva
  para un producto con lead time largo y no efectiva para otro con lead time corto, y puede dejar de
  serlo mañana sin que nada haya cambiado en la orden. Depende del horizonte de quien pregunta. Un
  valor que depende de la pregunta no es un estado del inventario.

- **Alternativas:**
  | | Enfoque | Observación |
  |---|---|---|
  | (a) | Usar solo el tránsito total | Produce el fallo silencioso descrito |
  | (b) | Almacenar también el efectivo como columna | Congela un valor que depende del horizonte: sería incorrecto casi siempre, y añadiría estado que hay que reconciliar |
  | (c) | Almacenar el total; derivar el efectivo en el cálculo | Cada decisión usa el valor que le corresponde, sin duplicar estado |

- **Razón:** (c). Es la única que respeta la naturaleza de cada magnitud. Además evita añadir una
  columna "por si acaso", que la regla anti-sobreingeniería del proyecto prohíbe.

- **Consecuencias:**
  1. `Inventory.quantity_in_transit` conserva su significado actual: **tránsito total**. No cambia el
     modelo de datos.
  2. `supply_engine` recibe las líneas de orden pendientes con su fecha esperada y calcula el efectivo.
  3. La recomendación almacena **ambos valores** en `calculation_inputs`, de modo que el planificador
     vea que hay tránsito que no se ha contado y por qué.
  4. La posición de inventario tiene entonces dos lecturas —contable (con el total) y de decisión (con
     el efectivo)— y la documentación debe decir siempre cuál usa (`docs/06-motor-abastecimiento.md` §4).

- **Pendiente de definir en la Fase 4:** la fecha de corte exacta y el tratamiento de las órdenes ya
  atrasadas (una orden vencida y no recibida, ¿cuenta como efectiva?). Requiere criterio de negocio.

- **Estado:** `PROPUESTA` — la distinción conceptual es firme; el criterio de corte, pendiente.

## DT-013 — Ubicación de `architecture/`, `decisions/` y `reports/` dentro de `docs/`

- **Decisión:** Estas tres carpetas se sitúan bajo `docs/` en lugar de en la raíz del repositorio.
- **Contexto:** La estructura solicitada las enumeraba junto a `docs/`, `project/` y `knowledge/`,
  sin especificar el nivel.
- **Alternativas:** (a) En la raíz. (b) Dentro de `docs/`.
- **Razón:** Su contenido es documentación técnica; agruparlo bajo una sola raíz mantiene la raíz del
  repositorio despejada para el código que llegará en fases posteriores (`backend/`, `frontend/`,
  `ml/`, `infra/`). La instrucción admitía modificación con razón técnica clara.
- **Consecuencias:** Las rutas son `docs/architecture/`, `docs/decisions/`, `docs/reports/`. Revisable
  si el responsable prefiere la raíz.
- **Estado:** `PROPUESTA` — pendiente de confirmación del responsable.

## DT-014 — Modo de conexión de Power BI

- **Decisión:** Usar modo *Import* con actualización programada como opción por defecto, sobre vistas
  analíticas dedicadas.
- **Contexto:** El volumen de referencia es moderado y los indicadores no requieren tiempo real.
- **Alternativas:** (a) Import. (b) DirectQuery. (c) Modelo compuesto.
- **Razón:** Import ofrece mejor rendimiento y flexibilidad de modelado; DirectQuery añade carga sobre
  la base operativa y restricciones de modelado que no se justifican sin necesidad de latencia baja.
- **Consecuencias:** Los informes reflejan el estado de la última actualización; la fecha debe ser visible.
- **Estado:** `PROPUESTA` — revisar en la Fase 11.

## DT-015 — Sin promoción automática de modelos a producción

- **Decisión:** La promoción de un modelo a producción requiere aprobación humana, aunque supere todos
  los criterios automáticos.
- **Contexto:** El pipeline puede evaluar y decidir por métrica.
- **Alternativas:** (a) Promoción automática por métrica. (b) Aprobación humana.
- **Razón:** El costo de un modelo malo en producción son desabastos y sobreinventario reales. Una
  métrica puede mejorar por un artefacto de datos. El costo de una revisión humana mensual es
  despreciable frente a ese riesgo.
- **Consecuencias:** Ciclo de actualización algo más lento. Requiere un responsable identificado.
- **Estado:** `ACEPTADA`

## DT-016 — El sistema recomienda; no ejecuta compras

- **Decisión:** El sistema no emite órdenes de compra automáticamente. La conversión de una
  recomendación en orden es siempre una acción humana explícita.
- **Contexto:** Requisito del alcance (RF-015) y condición de adopción.
- **Alternativas:** (a) Ejecución automática con umbrales. (b) Automática con aprobación. (c) Siempre humana.
- **Razón:** El sistema desconoce restricciones que el comprador sí conoce (negociaciones en curso,
  situación del proveedor, decisiones comerciales). Además, la aceptación o el descarte con motivo son
  el mecanismo principal de retroalimentación para mejorar las reglas.
- **Consecuencias:** El sistema no elimina trabajo de decisión; lo hace mejor informado. Se obtiene un
  registro valioso de discrepancias entre el motor y el criterio humano.
- **Estado:** `ACEPTADA`

## DT-017 — Documentación de negocio en español, código en inglés

- **Decisión:** Documentación de proyecto y de dominio en español; código, identificadores, esquema de
  base de datos y comentarios en inglés.
- **Contexto:** Equipo hispanohablante; ecosistema técnico en inglés.
- **Alternativas:** (a) Todo en español. (b) Todo en inglés. (c) Separación por ámbito.
- **Razón:** La documentación debe ser accesible a los interesados de negocio; el código debe ser
  coherente con las librerías y convenciones del ecosistema. Mezclar idiomas dentro del código produce
  identificadores híbridos difíciles de mantener.
- **Consecuencias:** El glosario debe mapear los términos entre ambos idiomas.
- **Estado:** `ACEPTADA`

## DT-018 — Explicación por plantilla determinística antes que por LLM

- **Decisión:** La primera implementación de la explicación de recomendaciones usará un generador
  determinístico por plantilla; Azure OpenAI se incorporará después, tras la misma interfaz.
- **Contexto:** La explicación es un caso de uso de alta prioridad, y Azure no puede configurarse todavía.
- **Alternativas:** (a) Esperar a Azure OpenAI. (b) Plantilla determinística primero.
- **Razón:** Obliga a que el desglose del cálculo sea completo y correcto antes de añadir lenguaje
  natural. Si la explicación no puede escribirse con una plantilla, faltan datos en la recomendación.
  Además, aporta valor sin costo ni dependencia externa.
- **Consecuencias:** Trabajo adicional que después se sustituye, compensado por un contrato validado y
  una vía de degradación ya construida (RNF-010).
- **Estado:** `ACEPTADA`

## DT-019 — Conversión entre el pronóstico semanal y un lead time expresado en días

- **Decisión:** **Pendiente.** Se documentan las alternativas y se recomienda una, pero la elección
  requiere el calendario laboral del negocio (`BR-X06`), que no está definido.

- **Contexto:** `DT-008` modela en semanas; los lead times se registran en días. Un lead time de 10
  días no equivale a un número entero de semanas, de modo que **la demanda esperada durante el lead
  time no se deduce del pronóstico semanal sin una regla explícita**. Sin esa regla, dos personas
  implementarán dos fórmulas distintas y el sistema producirá dos cifras para la misma pregunta.

- **Alternativas:**

  | | Regla | Cómo se calcula con `L = 10 días` y forecast semanal `F₁, F₂, …` | Observación |
  |---|---|---|---|
  | (a) | **Prorrateo uniforme** | `F₁ + (3/7)·F₂` — semanas completas más la fracción proporcional de la siguiente | Simple y continua. Supone demanda uniforme dentro de la semana (`ASSUMPTION-019`) |
  | (b) | **Prorrateo por perfil intra-semanal** | Reparte cada `Fₖ` según el patrón día-de-semana observado en el histórico diario, y suma los 10 días | Más fiel si hay perfil semanal marcado. Requiere estimar y mantener el perfil |
  | (c) | **Redondeo conservador al alza** | `F₁ + F₂` (⌈10/7⌉ = 2 semanas completas) | Sesga sistemáticamente al alza el inventario. Simple pero caro |
  | (d) | **Modelar en diario los SKU afectados** | No hay conversión | Resuelve el problema eliminándolo, a costa de renunciar a `DT-008` en esos SKU |

- **Recomendación:** **(a) como definición por defecto**, porque el detalle diario se conserva en la
  base (`DT-008`) y (b) puede sustituirla más adelante **sin cambiar la interfaz de la función**. (c)
  se descarta salvo que el negocio pida explícitamente un sesgo conservador. (d) queda como excepción
  por segmento, coherente con la excepción ya prevista en `docs/05-motor-predictivo.md` §3.

- **Condición que invalida la recomendación:** si el negocio no opera todos los días de la semana, o
  si el histórico muestra un perfil intra-semanal marcado, (a) sesga el resultado y (b) pasa a ser la
  opción correcta. Por eso depende de `BR-X06`.

- **Consecuencia de implementación (obligatoria):** la conversión vive en **una única función** del
  `supply_engine` —conceptualmente `demand_over_horizon(forecast, start_date, days)`— que es el
  **único** punto del sistema autorizado a traducir entre granularidades. Ningún otro módulo, consulta
  SQL, informe de Power BI ni pantalla puede reimplementarla. La regla aplicada y el valor resultante
  se registran en `calculation_inputs` de la recomendación.

- **Estado:** `PENDIENTE DE VALIDACIÓN` — depende de `BR-X06` (calendario laboral). La recomendación
  (a) **no es todavía la fórmula del proyecto**; se confirma en la Fase 4.

## DT-020 — Evaluación en dos niveles y comparación end-to-end

- **Decisión:** El proyecto evalúa en **dos niveles** y considera el **Nivel 2 como decisorio**:
  - **Nivel 1 — calidad del pronóstico:** ¿acierta el forecast? (métricas de error, `docs/05` §9)
  - **Nivel 2 — calidad de la decisión:** ¿el forecast produce **mejores decisiones de
    abastecimiento**? (desabastos, nivel de servicio alcanzado, inventario medio, exceso, órdenes
    urgentes, costo — `docs/05` §9.4)

  Además, ningún modelo se promueve sin una **comparación end-to-end**:

  ```
  Baseline Forecast → Supply Engine → Recomendaciones → métricas de Nivel 2
                                  vs
  ML Forecast       → Supply Engine → Recomendaciones → métricas de Nivel 2
  ```

- **Contexto:** Es perfectamente posible que un modelo reduzca el error de pronóstico y **empeore** el
  resultado de abastecimiento —por ejemplo, si mejora el promedio pero introduce sesgo a la baja en los
  SKU críticos, o si reduce el error puntual a costa de una incertidumbre peor calibrada, de la que
  depende el stock de seguridad—. Sin Nivel 2 ese caso pasa inadvertido y se promueve un modelo que
  produce más desabastos.

- **Alternativas:** (a) Evaluar solo el error de pronóstico. (b) Evaluar solo el resultado de
  abastecimiento. (c) Ambos niveles, con el Nivel 2 como decisorio.

- **Razón:** (a) mide un medio y lo confunde con el fin. (b) no permite diagnosticar **por qué** falla
  una decisión ni mejorar el modelo. (c) conserva la capacidad de diagnóstico del Nivel 1 y sitúa el
  criterio de aceptación donde está el objetivo real del proyecto.

- **Consecuencias:**
  1. El motor de abastecimiento debe poder ejecutarse **en modo simulación retrospectiva** sobre el
     histórico, con un forecast intercambiable. Es un requisito de diseño de `supply_engine`, no un extra.
  2. Los criterios de aceptación de un modelo (`docs/05` §10) incluyen el Nivel 2.
  3. Se mide, no se fija un objetivo: **no se establece ningún valor objetivo** (del tipo
     "desabasto < 5 %") porque el negocio no lo ha proporcionado. Se define **qué medir**, no cuánto.

- **Estado:** `ACEPTADA` — es la única forma de responder a la pregunta que el proyecto debe
  responder: si el motor predictivo sirve para abastecer mejor.

## DT-021 — Selección de la métrica primaria de pronóstico

- **Decisión:** **No se fija todavía la métrica primaria.** Se fija el **procedimiento** para elegirla
  y se descarta explícitamente una candidata.

- **Contexto:** La versión anterior de `docs/05-motor-predictivo.md` §9 designaba MASE como "métrica
  primaria propuesta". Es una candidata razonable, pero elegir la métrica primaria antes de conocer la
  composición real del catálogo —qué proporción es intermitente, qué dispersión de escalas hay— es
  fijar un criterio de aceptación sin la información que lo justifica.

- **Descartada de forma firme:** **MAPE no puede ser métrica de decisión.** Queda indefinida cuando la
  demanda es cero —situación frecuente y esperada en este catálogo— y penaliza de forma asimétrica la
  sobre y la subestimación, lo que en abastecimiento sesga sistemáticamente hacia el desabasto. Se
  admite únicamente como cifra informativa.

- **Criterios que deberá cumplir la métrica primaria:**
  1. Definida y estable cuando la demanda es cero.
  2. Comparable entre series de escalas distintas (el catálogo mezcla unidades y volúmenes).
  3. Interpretable frente al baseline: debe dejar claro si el modelo aporta o no.
  4. Coherente con el Nivel 2 (`DT-020`): su mejora debe correlacionar con mejores decisiones.
  5. Robusta a valores atípicos, o acompañada de una métrica que lo sea.

- **Candidatas que cumplen los criterios 1–3:** MASE y RMSSE (errores escalados frente a un baseline
  ingenuo, definidos precisamente para permitir la comparación entre series). WAPE como métrica
  agregada ponderada por volumen. La elección entre ellas se hará con datos.

- **Consecuencias:** hasta la decisión, el informe de evaluación reporta **el conjunto** de métricas de
  `docs/05` §9 y ninguna se presenta como criterio único de aceptación.

- **Estado:** `PENDIENTE` — se decide al cerrar la Fase 1 (composición del catálogo) y confirmar en la
  Fase 5. El descarte de MAPE como métrica de decisión sí es `ACEPTADA`.

- **Nota (2026-10-05):** no se decidió al cerrar la Fase 1. `DT-078` fija el procedimiento: elección en la puerta G1 de la Fase 5, antes de evaluar candidatos y del *holdout*, sin cambio posterior. La métrica sigue `PENDIENTE`.

- **Nota (2026-10-05, G1): cerrada por `DT-090`.** La métrica primaria es **MASE**, decisión del responsable en G1 (no un desempate heredado), provisional con datos `SYNTHETIC`. El procedimiento de `DT-078` queda como referencia; cambiar la métrica exige una DT nueva y repetir la evaluación. El descarte de MAPE no cambia.

## DT-022 — Almacén de secretos gestionado

- **Decisión:** La configuración sensible se obtiene de un **almacén de secretos gestionado** en los
  entornos desplegados. **Azure Key Vault es el candidato natural**, por coherencia con el resto del
  stack, pero no se fija todavía como obligatorio.

- **Contexto:** `docs/10-seguridad.md` y `RS-006` nombraban Azure Key Vault directamente. Key Vault
  **no figura en la lista de tecnologías obligatorias** del alcance, y la regla del proyecto exige
  justificar y registrar toda tecnología adicional relevante antes de adoptarla (`CLAUDE.md` §5).

- **Alternativas:** (a) Variables de entorno del servicio de cómputo. (b) *Secrets* de GitHub como
  única fuente. (c) Almacén gestionado (Azure Key Vault u otro).

- **Razón:** (a) y (b) sirven en desarrollo y CI pero no ofrecen rotación, auditoría de acceso ni
  integración con identidad administrada. (c) es lo indicado en producción. La elección concreta del
  producto depende del destino de despliegue, que es `DT-P01` y también está pendiente.

- **Consecuencias:** el diseño se expresa contra la interfaz `SecretProvider` (`DT-003`), de modo que
  el producto concreto es sustituible. Ningún documento debe presentar Key Vault como decidido.

- **Estado:** `PROPUESTA` — se confirma junto con `DT-P01` en las Fases 12–13.

## DT-023 — Clasificación en tres niveles de las situaciones de §25 del dataset

> **Documento completo:** [`docs/decisions/DT-023-clasificacion-escenarios.md`](decisions/DT-023-clasificacion-escenarios.md).
> Vive como archivo propio porque incluye la matriz de las 26 situaciones, que no cabe aquí sin
> inflar el registro.

- **Decisión:** Las **26 situaciones mínimas obligatorias** de `knowledge/dataset-specification.md`
  §25 **no son 26 valores del enum `Scenario`**. Se reparten en tres niveles:

  | Nivel | Qué es | Dónde vive | Cuántas de las 26 |
  |---|---|---|---|
  | **A — Ejes de generación** | Comportamientos que el generador produce deliberadamente | Enum `Scenario` y `scenarios.required` | 13 |
  | **B — Atributos y estados** | Campos del modelo que deben tomar valores variados | Entidades de `docs/04-modelo-datos.md` | 9 |
  | **C — Propiedades emergentes** | Situaciones que surgen de combinar entidades | Las verifica el **validador (Componente 8)** | 4 |

  13 + 9 + 4 = 26.

  En consecuencia se amplía el enum de **14 a 16** valores: `LOW_INVENTORY` (§10.2) y
  `PARTIAL_DELIVERY` (§12.3), ambos ejes de Nivel A que el generador sí puede producir.

  **Las dos cifras no son la misma.** El enum tiene **16 valores**: los **13** que corresponden a
  situaciones de §25 más **tres** —`HIGH_ROTATION`, `LOW_ROTATION` y `MULTIPLE_LEAD_TIMES`— que no
  son filas de §25 y están respaldados por otras secciones (ADR §7). «26» cuenta situaciones de la
  especificación; «16» cuenta valores del enum.

- **Contexto:** Una auditoría detectó que §25 exige 26 situaciones y el enum tenía 14, con quince sin
  representación. Había que determinar si el enum estaba incompleto o si ambas listas describían
  cosas distintas.

- **Alternativas:** (a) Ampliar el enum a 26. (b) Dejarlo en 14 y verificar §25 en otro lugar.
  (c) Tres niveles. (d) Aplazar la decisión al Componente 7.

- **Razón:** La especificación **ya usa tres niveles**; §25 es una tabla-resumen que los mezcla. §32
  agrupa los escenarios en familias, no en una lista plana; §35 pide «distribución de escenarios» y
  «cantidad de productos por patrón de demanda» como ítems **separados**; §26 se solapa con §25 y
  llama a esas mismas situaciones *casos límite para pruebas*.
  **El argumento decisivo:** cuatro de las 26 dependen de reglas pendientes — `DT-P11` (corte del
  tránsito efectivo), `BR-X03` (umbrales de clasificación de riesgo), `BR-P10` (productos
  descontinuados), `DT-011` (demanda censurada). **Una etiqueta obliga a decidir:** marcar un SKU como
  `TRANSIT_EFFECTIVE_INSUFFICIENT` exigiría saber qué cuenta como «efectivo», que es justo lo que
  `DT-P11` mantiene abierto y lo que §3.5, §27 y §37 de la especificación prohíben fijar.

- **Consecuencias:** El validador del Componente 8 recibe un contrato explícito (comprobar las
  **cuatro** propiedades de Nivel C: situaciones 8, 12, 18 y 20). El Componente 7 sabe qué puede
  asignar: los 16 valores del enum, nada más. A cambio,
  la correspondencia entre §25 y los tres niveles hay que mantenerla en la matriz del ADR.
  **Qué la invalidaría:** que se cierren `DT-P11`, `BR-X03`, `BR-P10` y `DT-011`; entonces cabría
  reconsiderar si las situaciones de Nivel C se promueven a ejes.

- **No resuelve:** si §25 debe ampliarse con `HIGH_ROTATION` y `LOW_ROTATION`, presentes en el enum,
  en `docs/02` §8, en el roadmap y en §10.4 de la propia especificación, pero ausentes de la tabla
  §25. La discrepancia queda documentada en el ADR §7, **sin modificar §25**.

- **Estado:** `ACEPTADA`

---

> **`DT-024` a `DT-030` — bloque de preparación del Componente 2 (2026-09-18).** Las siete decisiones
> siguientes resuelven los bloqueantes B-1 a B-7 identificados en la auditoría del Componente 2
> (2026-09-17). Se tomaron juntas porque se condicionan entre sí, y todas afectan al mismo contrato.
> **Ninguna implementa nada: el Componente 2 no está implementado.**

## DT-024 — Formato de salida del dataset: un CSV por entidad

> **Documento completo:** [`docs/decisions/DT-024-contrato-salida-componente-2.md`](decisions/DT-024-contrato-salida-componente-2.md).
> Vive como archivo propio porque incluye el contrato de columnas de las cinco entidades maestras.

- **Decisión:** El dataset sintético se materializa como **un archivo CSV independiente por
  entidad** (`categories.csv`, `products.csv`, `suppliers.csv`, `product_suppliers.csv`,
  `locations.csv`), más un `manifest.json` con la metadata de generación (`DT-025`). **JSON no es el
  formato de los datos de las entidades.** El ADR fija además las convenciones sin las cuales «CSV»
  no sería un contrato: UTF-8 sin BOM, separador `,`, RFC 4180, LF, cabecera obligatoria, nulos como
  campo vacío, fechas ISO-8601, booleanos en minúscula e importes con dos decimales.

- **Contexto:** §40 de `knowledge/dataset-specification.md` condiciona la implementación del
  generador a que se definan antes la «estructura física de los archivos generados» y el «formato de
  intercambio». La auditoría del Componente 2 verificó que **ningún documento los definía**
  (bloqueante **B-1**). Sin ellos el Componente 2 no tiene salida que producir.

- **Alternativas:** (a) Un CSV por entidad. (b) Un único JSON con las cinco colecciones.
  (c) Parquet. (d) Aplazarlo al implementar.

- **Razón:** El destino declarado es PostgreSQL (Fase 2) y el modelo de `docs/04` es relacional: una
  entidad, una tabla. El CSV por entidad es la representación más directa de esa forma y la que menos
  transformación exige en la ingesta. Pesó además el costo de dependencias: `CLAUDE.md` §17 prohíbe
  instalar dependencias innecesarias y hoy solo existe PyYAML; CSV se escribe con la biblioteca
  estándar, Parquet no. (b) se descartó porque obligaría a aplanar el documento en la ingesta.

- **Consecuencias:** Contrato verificable sin ejecutar nada; carga directa con `COPY`; cero
  dependencias nuevas. A cambio, el CSV no lleva tipos y la corrección depende de respetar las
  convenciones, lo que se mitiga con la validación del Componente 8. **Tarea pendiente:** `.gitignore`
  ignora `*.csv` pero no `manifest.json`; hay que excluir el directorio de salida antes de la primera
  generación (`CLAUDE.md` §13.7). No se modifica ahora porque todavía no existe ningún archivo generado.

- **No decide:** los tipos SQL ni el esquema físico de PostgreSQL (Fase 2); ni las columnas de los
  componentes 3 a 8.

- **Estado:** `ACEPTADA`

## DT-025 — `manifest.json`: la metadata de generación vive fuera de las entidades

> **Documento completo:** [`docs/decisions/DT-025-manifest-metadata-generacion.md`](decisions/DT-025-manifest-metadata-generacion.md).

- **Decisión:** La metadata de generación se escribe en un **único `manifest.json`** junto a los CSV.
  **Ninguna entidad de negocio lleva metadata de generación**, y en particular **no se añade un campo
  `scenario` a `Product`, `Supplier`, `Category`, `ProductSupplier` ni `Location`**. Campos
  obligatorios desde el Componente 2: `dataset_version`, `generator_version`, `seed`, `generated_at`,
  `time_range`, `data_origin`, `config` (el `to_dict()` íntegro de `DatasetConfig`), `components` y
  `files`. `scenario_assignment` y `quality_report` los aportan los Componentes 7 y 8.

- **Contexto:** §19 exige poder identificar «semilla utilizada; versión del generador; escenario
  sintético asociado» y §33 añade `dataset_version` y `generated_at`. `DataLoad` (`docs/04` §4) no
  contiene ninguno de esos campos, ni ninguna otra entidad (bloqueante **B-4**).

- **Alternativas:** (a) Archivo `manifest.json` separado. (b) Campos de generación en cada entidad.
  (c) Ampliar `DataLoad`. (d) Un CSV de metadata.

- **Razón:** La propia §19 cierra la salida fácil: «La información adicional de generación no debe
  confundirse con información empresarial». Un archivo separado la mantiene separada por
  construcción. (b) tiene además un problema de futuro: un campo `scenario` en `Product` no tendría
  ningún valor posible con datos reales y quedaría huérfano en el esquema definitivo, contra `BR-007`
  y `DT-004`. (c) mezclaría generación con ingesta, que son responsabilidades distintas.

- **Consecuencias:** §19 y §33 quedan satisfechas sin tocar el modelo de negocio, y `DatasetConfig.to_dict()`
  gana un consumidor real. A cambio, hay un archivo más cuya coherencia con los CSV hay que mantener,
  mitigado con `files[].sha256`. Los campos no reproducibles del manifiesto son `generated_at` y los
  que dependen del conjunto de componentes ejecutados (`files`, `components`, `generator_version`);
  los archivos de datos sí son idénticos byte a byte.

- **No decide:** los valores de `dataset_version` ni `generator_version`; ni el contenido de
  `scenario_assignment` y `quality_report`.

- **Actualización del 2026-09-29.** Ambos campos quedan definidos como campos del manifiesto:
  `scenario_assignment` en `DT-041` §4 y `quality_report` en `DT-042` §5 (no un archivo aparte).

- **Estado:** `ACEPTADA`

## DT-026 — `data_origin` en las cinco entidades maestras

- **Decisión:** `Category`, `Product`, `Supplier`, `ProductSupplier` y `Location` llevan el campo
  `data_origin` (`SYNTHETIC` / `REAL`), igual que las entidades históricas. La marca es **por
  registro** y no debe confundirse con la metadata de generación, que vive en `manifest.json`
  (`DT-025`).

- **Contexto:** `docs/04` §5.2 establece que «toda entidad con datos cargados lleva `data_origin`», y
  `DT-004`, §19 y §34 de la especificación lo refuerzan. Pero las fichas §§3.1–3.5 **no lo listaban**:
  el campo solo aparecía en `InventoryMovement` y `Consumption`. La auditoría del Componente 2 registró
  la contradicción como bloqueante **B-2**, porque determina el esquema de las cinco colecciones.

- **Alternativas:** (a) Añadirlo a las cinco fichas. (b) Restringir la regla §5.2 a las entidades
  históricas. (c) Dejar la contradicción y decidir al implementar.

- **Razón:** (b) rompería §34 —«Todos los registros sintéticos deben identificarse correctamente como
  `SYNTHETIC`»— y `BR-007`, que exige poder sustituir datos sintéticos por reales sin rediseñar nada.
  Si un `Product` no lleva marca de origen, un catálogo mixto es indistinguible, que es justo el
  riesgo que `CLAUDE.md` §10.9 prohíbe. (c) es lo que bloqueó al componente.

- **Consecuencias:** Una columna más en cada una de las cinco entidades y en sus CSV. La regla
  transversal §5.2 pasa a ser cierta literalmente **para las cinco entidades maestras**.
  **Pendiente registrado** (auditoría de consistencia, 2026-09-18): las fichas de `PurchaseOrder`,
  `PurchaseOrderItem`, `PurchaseOrderReceipt` e `InventoryPolicy` **seguían sin listar `data_origin`**
  pese a ser entidades cargadas que la especificación exige en el dataset. Es el mismo defecto que
  motivó B-2, desplazado a los Componentes 5 y 6.

  **Pendiente cerrado el 2026-09-24**, antes de autorizar los Componentes 4 y 5. Se añade
  `data_origin` a `PurchaseOrder` (§3.9), `PurchaseOrderItem` (§3.10), `PurchaseOrderReceipt` (§3.11)
  y también a `Inventory` (§3.6), que no figuraba en el pendiente y tenía la misma carencia.
  **`InventoryPolicy` queda deliberadamente fuera**: no es un dato cargado ni forma parte del dataset
  sintético —ningún componente del generador la escribe—, de modo que RF-023 no la sustituye. El
  criterio general queda enunciado en `docs/04` §5.2 y en §34 de la especificación: lleva
  `data_origin` la entidad que se carga como histórico; no lo llevan las salidas calculadas del
  sistema.

- **No decide:** ninguna regla de negocio depende de este valor (`DT-004`, `BR-007`); sigue siendo
  solo trazabilidad y limpieza.

- **Estado:** `ACEPTADA`

## DT-027 — Vigencia de `Product`: `valid_from` y `valid_to`

> **Documento completo:** [`docs/decisions/DT-027-vigencia-producto.md`](decisions/DT-027-vigencia-producto.md).

- **Decisión:** `Product` incorpora `valid_from` (fecha, obligatorio) y `valid_to` (fecha, nulo =
  vigente sin fecha de fin prevista). Son campos de **dominio**, distintos de `created_at` /
  `updated_at`, que siguen siendo auditoría técnica y **no se reutilizan** como sustituto.

- **Contexto:** §7.2 de la especificación pide «fechas de creación o vigencia» y §20 exige que «el
  consumo ocurra dentro del periodo de existencia del producto». `docs/04` §3.2 solo ofrecía
  `created_at` / `updated_at`, etiquetados «Auditoría»: §20 no era comprobable (bloqueante **B-3**).

- **Alternativas:** (a) Añadir `valid_from` / `valid_to`. (b) Reutilizar `created_at`. (c) Derivar la
  vigencia del histórico. (d) Usar solo `is_active`.

- **Razón:** (b), (c) y (d) hacen imposible la validación de §20, cada una por un motivo distinto:
  (b) mide otra cosa —con una carga histórica, `created_at` es la fecha de la carga—, (c) es circular
  porque §20 quiere validar el histórico *contra* la vigencia, y (d) no tiene resolución temporal.
  Pesó además la coherencia interna: `InventoryPolicy` (§3.12) ya usa `valid_from` / `valid_to` para
  su vigencia, de modo que no se introduce vocabulario nuevo.

- **Consecuencias:** §20 pasa a ser comprobable y `created_at` recupera su significado. A cambio, dos
  columnas más en la entidad más usada y una validación más para el Componente 8. **La relación entre
  `is_active` y la vigencia queda deliberadamente sin definir**: depende de `BR-P10`, regla propuesta
  y no confirmada, y fijarla ahora sería convertir una hipótesis en requisito.

- **No decide:** ninguna política de altas y bajas de productos; ni añade vigencia a las otras cuatro
  entidades maestras, que ninguna sección exige.

- **Enmienda del 2026-09-24 (restricción 3).** El diseño del Componente 4 (`DT-036`) hizo aflorar una
  contradicción: un producto dado de baja con una orden en vuelo recibe mercancía después de su
  `valid_to`, y la restricción 3 original —«todo evento asociado al producto ocurre dentro del
  intervalo de vigencia»— lo prohibía. El responsable aprobó acotar la restricción con **una única
  excepción**: una orden emitida **dentro** de la vigencia completa su ciclo causal, de modo que sus
  recepciones y los movimientos `RECEIPT` derivados pueden ocurrir después de `valid_to`, conservando
  la trazabilidad con la orden. **No** autoriza demanda, consumo, órdenes nuevas ni ningún otro
  movimiento posterior a `valid_to`, ni cancelar la orden, truncar el movimiento o convertir la
  recepción en un ajuste. La decisión original **no se sustituye**: el ADR completo registra la
  trazabilidad original → enmienda → nueva restricción 3, y §34 de la especificación queda
  sincronizada.

- **Estado:** `ACEPTADA` — enmendada el 2026-09-24

## DT-028 — Políticas de generación sintética del Componente 2

> **Documento completo:** [`docs/decisions/DT-028-politicas-generacion-sintetica.md`](decisions/DT-028-politicas-generacion-sintetica.md).
> Vive como archivo propio porque contiene los conjuntos, rangos y pesos concretos, con la
> advertencia de lectura que los identifica como sintéticos.

- **Decisión:** Seis políticas sintéticas deterministas para las entidades maestras: valores
  comerciales de `ProductSupplier` (**B-5**), asignación producto ↔ proveedor (**B-6**), distribución
  ponderada de productos por categoría (**B-7**), nomenclatura neutra, vocabulario de
  `unit_of_measure` y vocabulario de `Location.type`. **Todos sus valores son `synthetic generation
  parameters`: parámetros técnicos del generador, no políticas comerciales de la organización.**

- **Contexto:** El modelo exige escribir `moq`, `order_multiple`, `unit_cost` y
  `agreed_lead_time_days`, y ninguna fuente define valor, rango ni regla. Lo mismo con el número de
  proveedores por producto, el reparto entre categorías y la proporción de productos inactivos. Sin
  ellos, §16, §13 y §25 no son satisfacibles.

- **Alternativas:** (a) Políticas sintéticas documentadas, fijas en el Componente 2. (b) Esperar al
  negocio. (c) Añadirlas a `DatasetConfig`. (d) Valores aleatorios sin rango declarado.

- **Razón:** §3.5 de la especificación autoriza expresamente usar valores sintéticos para construir
  escenarios técnicos «siempre que se identifiquen explícitamente como tales», y el ADR es esa
  identificación. (b) se descarta porque **pediría al negocio una decisión que no le corresponde**:
  nadie acuerda el MOQ de un producto que no existe, y §37 excluye «costos reales» del alcance.
  (c) se descarta porque §32 no lista estos parámetros entre los mínimos del generador, y ampliar el
  contrato del Componente 1 por un componente inexistente sería especular (`CLAUDE.md` §6.2).

- **Consecuencias:** B-5, B-6 y B-7 resueltos y ocho escenarios de §25 y tres casos límite de §26
  pasan a ser construibles. Los valores quedan en un solo documento, etiquetados, de modo que se sabe
  exactamente qué sustituir cuando haya datos reales. A cambio, son constantes del código y cambiarlos
  exige regenerar; y el ADR impone **cinco** precondiciones —`product_count ≥ category_count`,
  `product_count ≥ 4`, `supplier_count ≥ 3`, `supplier_count < R` y `period.days ≥ 2`— que el
  Componente 2 debe rechazar explícitamente en vez de degradar el dataset en silencio. Las dos
  últimas las añadió la auditoría de consistencia del 2026-09-18.

- **No decide:** ninguna política empresarial; ni lógica de selección o scoring de proveedores
  (`BR-X05` pendiente, `BR-P07` propuesta); ni la asignación de escenarios a SKU (Componente 7).

- **Estado:** `ACEPTADA`

## DT-029 — Alcance del Componente 2: lo que no genera

- **Decisión:** El Componente 2 genera **exclusivamente** las cinco entidades maestras. No escribe:

  | Elemento | Por qué |
  |---|---|
  | `abc_class`, `rotation_class` | `docs/04` §3.2 los declara **derivados**, y dependen del consumo, que no existe todavía. Sus umbrales «se calibrarán con datos reales» (`docs/05` §4) |
  | `shelf_life_days` | `docs/04` §8.4 («¿Existen productos con vida útil?») sigue sin responder. Queda `NULL` |
  | `Supplier.currency` | `docs/04` §8.5 («¿Se requiere multi-moneda?») sigue sin responder. Queda `NULL` |
  | `Supplier.contact_info` | §7.3 no lo exige y `CLAUDE.md` §9.7 prohíbe datos de proveedores en desarrollo. Queda `NULL` |
  | Cualquier campo `scenario` | Los 16 ejes permanecen separados de las entidades maestras (`DT-023`, `DT-025`) |
  | `created_at` / `updated_at` | Auditoría técnica del registro: los fija la ingesta, no el generador |
  | `Category.parent_id` | Jerarquía plana mientras rija `ASSUMPTION-009` |
  | `Product.description` | §7.2 pide «nombre **o** descripción»; basta `name` |

  Además, **el Componente 2 rechaza con error explícito una configuración con `location_count > 1`**.

- **Contexto:** La auditoría advirtió un riesgo concreto: que el Componente 2 escriba
  `rotation_class` a partir del eje asignado, contaminando una entidad maestra con información que
  pertenece al histórico. Por otro lado, `_check_scale` acepta cualquier `location_count` positivo,
  de modo que una configuración con 5 ubicaciones valida sin error pese a contradecir `ASSUMPTION-006`
  y a que `DT-P09` está aplazada.

- **Alternativas:** (a) Registrar la exclusión y que el Componente 2 falle ante `location_count > 1`.
  (b) Rellenar los campos derivados con valores provisionales. (c) Restringir `location_count` en
  `config.py`. (d) Que el Componente 2 genere N ubicaciones silenciosamente.

- **Razón:** (b) presentaría como dato lo que es una suposición, y un `abc_class` provisional acabaría
  citado como real. (d) produciría un dataset que contradice el alcance sin avisar, que es la peor de
  las opciones. (c) se descarta por **dónde vive la limitación**: `location_count` es un parámetro de
  escala legítimo del contrato de configuración; lo que no soporta multi-ubicación es *esta versión
  del generador*, no la configuración. Restringirlo en `config.py` pondría la restricción en la capa
  equivocada y habría que retirarla al cerrar `DT-P09`. **Por eso `config.py` no se modifica.**

- **Consecuencias:** `products.csv` y `suppliers.csv` tienen columnas permanentemente vacías, lo que
  es información honesta: el generador no produjo ese dato. El esquema del archivo sigue siendo el de
  la entidad. Queda registrado para una tarea posterior que, si se implementa el Componente 2, debe
  incluir la comprobación de `location_count` y su prueba.

- **No decide:** `DT-P09` (multi-ubicación) sigue aplazada; `docs/04` §8.4 y §8.5 siguen abiertas.

- **Estado:** `ACEPTADA`

## DT-030 — Determinismo por sub-semillas derivadas de la semilla común

- **Decisión:** Cada componente del generador deriva su propio flujo pseudoaleatorio mediante una
  sub-semilla determinista:

  ```text
  sub_seed(id) = int.from_bytes(sha256(f"{seed}:{id}".encode("utf-8")).digest()[:8], "big")
  ```

  donde `seed` se serializa como el entero en base 10 sin relleno, e `id` es el **identificador
  canónico** del componente: una cadena ASCII corta, en minúsculas, estable y **distinta de su
  número**. El del Componente 2 es `catalog`.

  La comprobación práctica de la reproducibilidad es: **misma configuración + misma semilla + misma
  versión del generador → archivos de datos idénticos byte a byte**. El manifiesto difiere en
  `generated_at` y en los campos que dependen del conjunto de componentes ejecutados (`files`,
  `components`, `generator_version`). Cada sub-semilla usada queda registrada en `manifest.json`
  (`DT-025`).

  **Tabla canónica de identificadores** (aprobada por el responsable el 2026-09-21, antes de que el
  Componente 3 extraiga nada):

  | # | Componente | Identificador | Estado |
  |---|---|---|---|
  | 1 | `DatasetConfig` | **ninguno** | Implementado. No extrae del flujo pseudoaleatorio, luego no tiene sub-semilla que derivar |
  | 2 | Catalog Generator | `catalog` | Implementado. **Sin cambios**: ya estaba en uso |
  | 3 | Demand Generator | `demand` | Pendiente |
  | 4 | Inventory Simulator | `inventory` | Pendiente |
  | 5 | Purchase Order Generator | `orders` | Pendiente |
  | 6 | Supplier Behaviour Generator | `supplier_behaviour` | Pendiente |
  | 7 | Scenario Assignment | `scenarios` | Pendiente |
  | 8 | Dataset Validator **+ informe de calidad** | `validator` | Pendiente |

  Vive en `data/synthetic/generator/rng.py` como `COMPONENT_IDS`, con una constante por componente, y
  cada identificador está fijado por una prueba contra la fórmula de arriba.

  **Por qué la tabla tenía que fijarse ahora.** La sub-semilla es función de la cadena, de modo que un
  identificador decidido *después* de que un componente haya generado datos cambiaría esos datos. Con
  el Componente 3 sin empezar, se está a tiempo; el Componente 2 no se ve afectado porque conserva
  `catalog`, y se comprobó que sus cinco CSV salen byte a byte idénticos tras el cambio.

  **El informe de calidad es parte del Componente 8, no un noveno componente.** Lo sostienen cuatro
  fuentes: `DT-023` («Validador del dataset (**Componente 8**)», y su §Consecuencias 2), `DT-025`
  (`quality_report` → «**Componente 8**»), `project/status.md` («Dataset Validator **+ informe de
  calidad**») y `DT-031` (los casos de prueba 12 y 13 → «Componente 8 (validador)»). La ambigüedad que
  este ADR registraba venía de la prosa de `CLAUDE.md` §17 —corregida el 2026-09-21 al implementar el
  Componente 2—, no de ninguna decisión: **ninguna decisión aceptada propuso nunca un noveno
  componente.**

  El único identificador con guion bajo es `supplier_behaviour`, y es deliberado: `supplier` a secas se
  confundiría con la entidad maestra que ya genera el Componente 2, y `behaviour` a secas no dice de
  quién. Los patrones son sustantivos cortos, independientes del nombre del archivo que cada componente
  escriba, para que renombrar un archivo no toque los datos.

  Lo que **sigue pendiente** y no decide esta tabla: si `quality_report` se escribe dentro de
  `manifest.json` o como archivo aparte. `DT-025` lo aplaza expresamente al autorizar el Componente 8.

  **Nota del 2026-09-29 (`DT-041` §2, decisión C7/C8-13).** Un componente que no sortea registra
  igualmente su sub-semilla en `manifest.components`, por uniformidad de la entrada: el Componente 7
  (`scenarios`) la registra y **no la usa**. La excepción de la fila 1 de la tabla se refiere a
  `DatasetConfig`, que no figura en `components`.

- **Contexto:** §3.3 exige que «una misma configuración y una misma semilla produzcan el mismo
  dataset», y `CLAUDE.md` §6.7 prohíbe la aleatoriedad no sembrada. Pero si todos los componentes
  comparten un único flujo pseudoaleatorio, **implementar un componente nuevo altera los datos que
  producían los anteriores**, porque cambia el número de extracciones previas. La auditoría lo
  registró como decisión técnica pendiente.

- **Alternativas:** (a) Sub-semillas derivadas por hash del nombre del componente. (b) Un único flujo
  compartido. (c) Sub-semillas por desplazamiento (`seed + 1`, `seed + 2`…). (d) Una semilla por
  componente en `dataset_config.yaml`.

- **Razón:** (b) es exactamente el problema. (c) depende del **orden** en que se numeren los
  componentes: insertar uno en medio renumera el resto y cambia todo lo posterior. (d) multiplica la
  configuración por ocho sin ganar nada. (a) solo depende de la semilla y del nombre, de modo que
  añadir un componente no altera la sub-semilla de ninguno de los existentes. Se usa SHA-256 explícito
  y no `hash()` de Python, que varía entre ejecuciones con `PYTHONHASHSEED`.

- **Consecuencias:** Los componentes son independientes entre sí en cuanto a aleatoriedad, y el orden
  de generación deja de ser parte del contrato reproducible. El orden **de las filas** sí lo es, y
  `DT-024` lo fija como ascendente por clave. Cuesta una función de tres líneas y una entrada más en
  el manifiesto.

- **No decide:** el algoritmo pseudoaleatorio concreto. Lo fijó **`DT-032`** al implementar el
  Componente 2: un contador sobre SHA-256, sin `random`.

- **Estado:** `ACEPTADA`

---

## DT-031 — V1: reglas mínimas funcionales del cálculo de abastecimiento

> **Documento completo:** [`docs/decisions/DT-031-reglas-minimas-v1.md`](decisions/DT-031-reglas-minimas-v1.md).
> Vive como archivo propio porque contiene trece reglas con su fórmula, ejemplo y ruta de reemplazo.

- **Decisión:** Se adopta un conjunto de **trece reglas técnicas provisionales** que hacen calculable
  la cadena `Forecast → Inventory → Supply Engine → Recommendation` sobre el dataset sintético, sin
  fijar ninguna política empresarial: necesidad bruta (`V1-01`), posición de inventario (`V1-02`),
  horizonte de cobertura (`V1-03`), demanda sobre el horizonte (`V1-04`), stock de seguridad
  (`V1-05`), MOQ y múltiplo (`V1-06`), escenarios mínimos de demostración (`V1-07`), alcance del
  validador (`V1-08`), lead time observado (`V1-09`, con `V1-09.1` ventana de 12 y `V1-09.2` techo de
  90 días), elección de proveedor (`V1-10`), **sin diferenciación ABC (`V1-11`)**, **sin
  sobre-recepción (`V1-12`)** y **sin inventario negativo (`V1-13`)**.

  **Revisión del 2026-09-19** (decisiones A–F del responsable): se confirman los ocho componentes de
  la Fase 1 sin cambios, `R_v1 = 7`, `z_v1 = 1,65` y la independencia de `MOQ` y `order_multiple`; y
  se **sustituye el lead time acordado por el observado** en el horizonte de cobertura, con fallback
  al acordado mientras no haya histórico suficiente. Además se cierran cuatro reglas pendientes
  —`BR-X05`, `BR-X07`, `BR-X08`, `BR-X09`— con interpretaciones técnicas, no con políticas.

  **Cierre del 2026-09-21.** El responsable confirma `V1-09` (mínimo de tres observaciones),
  `V1-09.1` (ventana de doce, ordenada por fecha de finalización), `V1-09.2` (techo de 90 días con
  marca `LEAD_TIME_CAPPED` y trazabilidad del valor sin topar) y `V1-10` (proveedor preferente
  activo; sin él, no se recomienda), y añade `V1-11`, `V1-12` y `V1-13`, que explicitan las tres
  interpretaciones que ya cerraban `BR-X07`, `BR-X08` y `BR-X09`. `V1-11` **no elimina** `abc_class`
  ni `rotation_class` del modelo: los deja fuera del cálculo. El conjunto queda cerrado.

- **Contexto:** Trece reglas de negocio siguen pendientes (`knowledge/business-rules.md` §3) y cuatro
  decisiones técnicas están sin cerrar (`DT-010`, `DT-019`, `DT-P05`, `DT-P11`). Sin alguna forma de
  puentearlas, `raw_need` no es calculable y no puede construirse ni probarse el flujo completo. La
  auditoría del 2026-09-19 verificó que «necesidad» aparece en la especificación con **seis
  redacciones distintas** y que el glosario no define ninguna.

- **Alternativas:** (a) Un conjunto acotado de reglas provisionales, declaradas y reemplazables —ocho
  en la versión inicial, trece tras el cierre del 2026-09-21—. (b) Esperar a que el
  negocio cierre las trece reglas. (c) Implementar el generador sin definir el cálculo y decidir al
  llegar al motor.

- **Razón:** (b) bloquea el proyecto por tiempo indefinido y pide al negocio decisiones que no
  necesita tomar para un dataset sintético. (c) es lo que produjo los bloqueantes B-1 a B-7. La vía
  (a) tiene un rasgo que la hace defendible: **diez de las trece reglas ya estaban documentadas** y
  solo necesitaban nombre y parámetros. `V1-01` es literalmente la rama periódica de `docs/06` §§7-8;
  `V1-02` es `docs/06` §4.2 sin cambios; `V1-04` es la recomendación provisional de `DT-019`;
  `V1-06` es `docs/06` §8 Paso 2; `V1-08` recoge invariantes ya enunciadas en §§20, 21 y 34 de la
  especificación; `V1-09` implementa `BR-P01`; `V1-10` adopta `BR-P07`; y `V1-11`, `V1-12` y `V1-13`
  se apoyan respectivamente en `DT-029`, en §21 y en §26 junto con `docs/06` §14. Solo `V1-03`,
  `V1-05` y `V1-07` introducen algo nuevo, y las tres lo declaran.

- **Consecuencias:** La cadena queda calculable de extremo a extremo. Se cierra la cuestión **C** de
  la auditoría anterior: «MOQ > necesidad» pasa de no computable a computable. Se corrige una
  contradicción interna de `docs/06` §14 anterior a este bloque de trabajo. El glosario gana la
  definición de «necesidad bruta» con sus tres alias.
  **Costos:** dos parámetros sin respaldo del negocio (`R_v1 = 7`, `z_v1 = 1,65`, registrados como
  `ASSUMPTION-021` y `ASSUMPTION-022`); V1 elige implícitamente revisión periódica; y V1 mide la
  incertidumbre sobre la demanda y no sobre el error de pronóstico (`ASSUMPTION-023`), porque sin
  modelo entrenado la segunda no existe.
  **La consecuencia que más importa:** ninguna salida de V1 puede presentarse como recomendación de
  negocio. `BR-009` sigue rigiendo sin excepción fuera del entorno sintético.

- **No resuelve:** ninguna de las trece reglas pendientes de `business-rules.md` §3 —cuatro tienen
  una interpretación técnica de V1, que no es una confirmación del negocio—; ni `DT-010`, `DT-019`,
  `DT-P05` ni `DT-P11`. Tampoco si `MOQ` debe ser múltiplo de `order_multiple` (parte de negocio de
  la cuestión **B**). La cuestión **A** (descomposición de componentes) la resolvió el responsable el
  2026-09-19, no este ADR.

- **Cobertura de pruebas:** los trece casos de prueba enumerados en el cierre **no son ejecutables
  hoy y no se han escrito**: once pertenecen al motor de abastecimiento (Fase 4, no autorizada) y dos
  al Componente 8 (validador, no iniciado). El ADR los registra uno a uno con su dueño para que
  lleguen con su componente. La suite actual sigue siendo de 54 pruebas de `DatasetConfig`.

- **Notas de redacción del 2026-09-29 (`DT-041`).** `V1-07`: el Componente 7 **registra** las
  decisiones de C3 y C6 y **mide** los ejes emergentes; no «asigna». `V1-08`: el validador no clasifica
  sobreinventario según `BR-X03`; la cobertura de `OVERSTOCK` y de la situación 18 usa solo el
  criterio sintético de `DT-041`. Ninguna regla V1 cambia.

- **Estado:** `ACEPTADA` **como conjunto de reglas de V1** (2026-09-21). El matiz es necesario y está
  desarrollado en el ADR: lo aceptado es «estas son las reglas que rigen V1», **no** «estas son las
  políticas de la organización». Ninguna de las trece reglas pendientes de `business-rules.md` §3
  queda confirmada, y los parámetros `R_v1`, `z_v1`, `N_v1`, `N_MIN_v1` y `LT_MAX_v1` siguen siendo
  técnicos y provisionales. Desde su creación el 2026-09-19 y hasta ese cierre el estado fue `PROPUESTA`; el cambio se justifica en
  que el responsable decidió expresamente estas reglas, y `CLAUDE.md` §8 solo prohíbe marcar
  `ACEPTADA` lo que **todavía es una hipótesis** — provisional no es hipotético.

---

## DT-032 — Algoritmo pseudoaleatorio: flujo contador sobre SHA-256

- **Decisión:** El flujo pseudoaleatorio del generador es un **contador sobre SHA-256**. Cada
  extracción calcula

  ```text
  raw = int.from_bytes(sha256(f"{sub_seed}:{label}:{counter}").digest()[:8], "big")
  ```

  y avanza el contador. El `label` separa flujos independientes dentro de un mismo componente
  —`moq`, `unit-cost`, `agreed-lead-time`…—, de modo que cambiar el número de extracciones de uno
  no desplaza los valores de otro. Los enteros acotados se obtienen por **muestreo con rechazo**,
  no por módulo. Las permutaciones son Fisher-Yates escrito a mano.

  Vive en `data/synthetic/generator/rng.py`, junto a la derivación de sub-semillas de `DT-030`.

- **Contexto:** `DT-030` fija cómo se deriva la sub-semilla de cada componente, pero declara
  expresamente que «no decide el algoritmo pseudoaleatorio concreto». §44 de la especificación va
  más lejos y lo registra como un **límite conocido**: la sub-semilla sí es estable entre versiones
  de Python y plataformas porque solo depende de SHA-256, pero «el flujo pseudoaleatorio derivado de
  ella **no lo está necesariamente**, porque la implementación de las funciones de la biblioteca
  estándar puede cambiar entre versiones». Y añade: «fijar el algoritmo pseudoaleatorio concreto es
  trabajo del Componente 2». Esta decisión es ese trabajo.

- **Alternativas:** (a) Flujo contador sobre SHA-256. (b) `random.Random(sub_seed)` de la biblioteca
  estándar. (c) `numpy.random.Generator` con un *bit generator* de estabilidad declarada.

- **Razón:** (b) es lo natural y es exactamente lo que §44 advierte. `random.Random.random()` es
  estable en la práctica, pero `shuffle`, `randrange` y `choice` han cambiado de implementación entre
  versiones de Python más de una vez, y la documentación oficial solo garantiza la reproducibilidad
  «dentro de una misma versión». El invariante de §44 es **igualdad byte a byte**, no «casi siempre
  igual». (c) añadiría NumPy, y `CLAUDE.md` §17 prohíbe dependencias innecesarias: hoy la única
  dependencia externa del proyecto es PyYAML.

  (a) cuesta unas quince líneas y convierte cada extracción en una **función pura de
  `(sub_seed, label, counter)`**. Eso cierra el límite de §44 en lugar de documentarlo: el mismo
  dataset sale idéntico en cualquier Python 3.11+, en cualquier plataforma, indefinidamente.
  Verificado además con `PYTHONHASHSEED` distinto en cada ejecución.

  El muestreo con rechazo no es purismo: `raw % bound` sobre-representa los valores bajos cuando
  `bound` no divide 2⁶⁴. El sesgo es pequeño, pero es real y evitable por el coste de un bucle que
  casi siempre termina en la primera pasada.

- **Consecuencias:** El generador no usa `random` en ninguna parte. El coste es un SHA-256 por
  extracción —irrelevante a esta escala: el catálogo completo son unas 700 extracciones—. El límite
  conocido de §44 deja de aplicar al flujo; sigue aplicando, por definición, a cualquier código
  futuro que use `random`, de modo que la regla operativa es: **en el generador no se usa `random`**.

- **No decide:** nada sobre las distribuciones estadísticas de los Componentes 3 en adelante. Si la
  demanda necesita una normal o una Poisson, habrá que derivarlas de este flujo uniforme y
  registrarlo; esta decisión solo fija la fuente de uniformes.

- **Estado:** `ACEPTADA`

## DT-033 — Esquema de versionado del dataset y del generador

- **Decisión:** Dos campos del manifiesto, con naturalezas distintas:

  | Campo | Valor | Quién lo fija |
  |---|---|---|
  | `generator_version` | Versión semántica del generador. **`0.1.0`** con el Componente 2 | Constante del código, se sube a mano |
  | `dataset_version` | `ds-` + los 12 primeros hex de `sha256(config_canónica + "\|" + generator_version)` | **Derivado**, nunca asignado |

  La configuración canónica es `DatasetConfig.to_dict()` serializado como JSON con claves ordenadas
  y sin espacios. `dataset_version` **no incluye `generated_at`**: nombra al dataset, no a la
  ejecución.

  Criterio para `generator_version`: **sube la minor cuando el generador produce datos distintos para
  la misma configuración y semilla** —un componente nuevo, una política cambiada, un orden de
  extracción distinto—. Es la versión de la *salida observable*, no la del código fuente.

- **Contexto:** `DT-025` define los dos campos como obligatorios desde el Componente 2 y su regla 5
  aplaza expresamente el esquema: «no se fijan valores concretos de `dataset_version` ni
  `generator_version`; su esquema de versionado se decidirá al implementar el generador, porque hoy
  no existe ninguna versión que registrar». Hoy ya existe.

- **Alternativas:** (a) `dataset_version` derivada por hash. (b) Un contador manual (`v1`, `v2`…).
  (c) Una marca de tiempo. (d) Un UUID por ejecución.

- **Razón:** (b) no tiene ninguna de las dos propiedades que hacen útil al campo: nada obliga a
  nadie a subirlo, y dos datasets distintos pueden acabar con el mismo número. (c) y (d) cambian en
  cada ejecución, de modo que regenerar el mismo dataset produciría un identificador distinto y el
  campo dejaría de poder compararse — justo lo contrario de lo que §3.3 pide.

  (a) es **reproducible** —regenerar el mismo dataset da el mismo identificador— y **cambia
  exactamente cuando cambian los datos**, porque sus dos entradas son los dos términos del invariante
  de §44: configuración y versión del generador. La semilla entra por la configuración, que la
  contiene.

- **Consecuencias:** `dataset_version` es comparable entre ejecuciones y entre máquinas, y sirve como
  huella del dataset sin tener que leer los cinco `sha256` de `files`. El precio es que no es legible
  para un humano: `ds-a4e50751841e` no dice nada por sí solo. Se acepta porque el manifiesto lleva al
  lado la configuración íntegra, que sí lo dice todo.

  Consecuencia operativa que conviene no olvidar: **al añadir el Componente 3 hay que subir
  `generator_version`**. Si no se sube, dos datasets con contenidos distintos declararán el mismo
  `dataset_version`, y el invariante de §44 —que menciona la versión del generador precisamente por
  esto— dejaría de cumplirse.

  Hay un tercer número, distinto de los dos anteriores: **`components[].version`**, la versión de cada
  componente por separado. `DT-028` §8 se apoya en ese campo para saber qué políticas sintéticas
  produjeron un dataset, y esa es una pregunta sobre *el Componente 2*, no sobre el generador entero.
  Hoy vale `0.1.0` igual que `generator_version` porque solo hay un componente; se mantienen separados
  precisamente para que dejen de confundirse cuando haya varios.

- **Regla operativa de incremento — añadida el 2026-09-26.** El criterio de arriba («datos distintos
  para la misma configuración y semilla») se concreta así, para que pueda aplicarse de forma
  reproducible. **Es la única regla de incremento del generador**: `DT-036` §8 y `DT-039` §12 remiten
  aquí, y ya no existe ninguna enumeración cerrada de parámetros.

  **Artefacto publicado** de una ejecución con una configuración dada:

  1. el **conjunto de archivos de datos** del directorio publicado, por nombre;
  2. el **contenido byte a byte** de cada archivo de datos —columnas, orden de columnas, filas,
     valores, formato, orden de filas e identificadores—, que el propio manifiesto registra en
     `files[].sha256`;
  3. **`manifest.json`**, excluidos `generated_at` (fuera por diseño, §44 y `DT-025` regla 4) y
     `generator_version`, `dataset_version` y `components[].version`, que son **consecuencia** del
     cambio y no causa: incluirlos haría la regla circular.

  > **Se incrementa la versión *minor* de `generator_version` cuando un cambio en el generador —en
  > cualquier módulo, parámetro o literal, no solo en `policies.py`— altera el artefacto publicado de
  > al menos una configuración aceptada tanto antes como después del cambio.**

  **La versión depende del artefacto, no del archivo donde vive el parámetro.** Verificado en el
  código: además de las políticas de `policies.py`, alteran el artefacto los identificadores
  canónicos de `rng.py` (entran en `sub_seed`), las etiquetas de flujo aleatorio de `catalog.py` y
  `demand.py`, las tuplas de columnas y nombres de archivo, y las funciones de formato de `writer.py`.
  Una regla limitada a `policies.py` no los cubriría.

  **No requieren incremento** —ejemplos verificados en el código—:

  | Tipo | Ejemplo | Por qué |
  |---|---|---|
  | Precondición de configuración | `DEMAND_MIN_PRODUCTS` (usado solo en la comprobación de P-6) | Cambia qué configuraciones se aceptan; el artefacto de una configuración aceptada antes y después es idéntico |
  | Comprobación de cobertura | `ORDER_MULTIPLE_LARGE_THRESHOLD` (usado solo en la comprobación final del Componente 2) | No genera ningún valor; decide si un catálogo ya generado pasa la comprobación |
  | Constante declarativa | `DEMAND_QUANTITY_IS_INTEGER` (no la lee ningún módulo del generador) | Cambiarla no altera ningún byte |
  | Refactorización interna | Renombrados privados, comentarios, reorganización sin alterar el orden de extracción | Artefacto idéntico |

  Los dos primeros casos se **registran** igualmente en el ADR del componente, porque cambian el
  dominio de lo reproducible aunque no cambien ningún artefacto.

  **Casos límite.** Cambiar el orden de filas o la asignación de identificadores **sí** requiere
  incremento, y además es un cambio de contrato que exige su propio ADR. Cambiar cómo
  `DatasetConfig.to_dict()` normaliza la configuración **sí** lo requiere: altera `manifest.config`
  aunque los datos no cambien. Un cambio que solo afecta a configuraciones antes rechazadas **no** lo
  requiere: no existía ningún artefacto con el que colisionar. Cambiar la **fórmula** de
  `dataset_version` queda fuera de esta regla: altera la semántica de la identidad, no un dato, y
  necesita su propio ADR. Corregir un error que altera los datos **sí** requiere incremento.

  **Procedimiento de verificación.** Sin incrementar la versión, se genera el artefacto de cada
  configuración de referencia antes y después del cambio, y se comparan el conjunto de archivos,
  `files[]` y el resto del manifiesto con las exclusiones indicadas. **Cualquier diferencia obliga a
  incrementar.** La igualdad es **evidencia, no prueba**: si el cambio afecta a una rama que ninguna
  configuración de referencia ejercita, se añade una que la ejercite o se incrementa por precaución.
  El procedimiento se aplica al decidir un incremento, no en cada ejecución de las pruebas.

  **Configuraciones de referencia** *(auditadas el 2026-09-26)*:

  | | Configuración | Qué ejercita |
  |---|---|---|
  | R1 | `data/synthetic/config/dataset_config.yaml` | La escala por defecto y el periodo completo: régimen proporcional de las canceladas, productos descatalogados con órdenes en vuelo, pares con demanda reciente nula, productos sin proveedor, sobreinventario por MOQ |
  | R2 | Fixture `SMALL` de `test_demand.py` (12 productos, 4 proveedores, 3 categorías, 59 días) | Los suelos de uno de todas las mezclas y el suelo de `K`, a coste mínimo |
  | R3 | **Escala ancha**: la de `test_ordering_survives_a_scale_that_overflows_the_width` de `test_catalog.py` (1 200 productos, 1 000 categorías) con el periodo de `SMALL` | El **ensanchado de códigos** de `DT-028` §4, que R1 y R2 no alcanzan, recorriendo todo el pipeline a coste moderado |

  *La propuesta anterior incluía la configuración por defecto de `test_catalog.py`. Se descarta por
  **redundante**: su `BASE_CONFIG` es idéntica, campo por campo, a `dataset_config.yaml` —verificado—.*

  **Ramas que ninguna configuración de referencia puede ejercitar**, y que deben cubrir pruebas
  unitarias: más de una ubicación (el Componente 2 rechaza `location_count > 1`, `DT-029`); productos
  con `valid_from` posterior al inicio del periodo (el Componente 2 no los genera, `DT-028` §7.2); el
  fallo B2 (no produce artefacto por diseño); y un `order_number` de más de seis dígitos, que exigiría
  un millón de órdenes.

- **Historial de `generator_version`.** 0.1.0 (C2) · 0.2.0 (C3) · 0.3.0 (C6 + C4 + C5 por W1) ·
  **0.4.0 (2026-09-29): C7 + C8 integrados en W1**, en un único incremento (decisión C7/C8-11,
  `DT-042` §9). Con 0.4.0 el artefacto cambia en el manifiesto —`scenario_assignment`,
  `quality_report` y dos componentes— y **no** en los datos: los doce CSV de la configuración
  vigente son byte a byte los de 0.3.0. `dataset_version` pasa de `ds-269a698250db` a
  `ds-6c8ad65b4999`.

- **No decide:** cómo se versiona el **código** del repositorio (etiquetas de Git, releases). Es
  trabajo de la Fase 12 (`docs/12-devops.md`) y no tiene por qué coincidir con `generator_version`.

- **Estado:** `ACEPTADA`

## DT-034 — `Demand`: la demanda latente se persiste, separada del consumo observado

> **Documento completo:** [`docs/decisions/DT-034-demanda-latente-persistente.md`](decisions/DT-034-demanda-latente-persistente.md).

- **Decisión:** El generador persiste **dos series**: `demand.csv` (**demanda latente** — lo que se
  habría demandado si el inventario nunca hubiera limitado nada), que produce el **Componente 3**; y
  `consumption.csv` (**demanda satisfecha**, con `is_stockout_affected`), que produce el
  **Componente 4**.

  ```text
  C2 → products.csv, locations.csv → C3 → demand.csv → C4 → consumption.csv
  ```

  `demand.csv` **no es un intermedio desechable**: es un dataset persistente con contrato de columnas,
  entrada en `manifest.json` y `sha256`. Se añade la entidad `Demand` a `docs/04` §3.7-bis. El
  Componente 3 **no escribe `consumption.csv`**, no conoce las existencias y no lleva
  `is_stockout_affected`.

  El ADR fija además tres cosas que estaban sin enunciar: el periodo es **semiabierto** `[start, end)`;
  la serie es **densa** (una fila por día vigente, con `quantity = 0` los días sin demanda); y
  `quantity` es **entero** para toda unidad de medida en V1.

- **Contexto:** `docs/04` §3.8 advierte que lo registrado es la demanda **satisfecha** y que durante un
  desabasto la real fue mayor, de modo que un modelo entrenado sobre ella «aprende que la demanda bajó»
  justo en los productos más críticos. El modelo tenía una sola entidad para las dos cosas, lo que
  dejaba la circularidad demanda→inventario→desabasto→consumo sin dueño y, sobre todo, dejaba el sesgo
  **reconocido pero no medible**.

- **Alternativas:** (a) C3 persiste la latente y C4 la transforma. (b) C3 la produce en memoria y solo
  C4 escribe. (c) C3 escribe `consumption.csv` y C4 lo reescribe. (d) Ambos generan desabastos.

- **Razón:** (a) es la única que **hace medible el sesgo por censura** en lugar de advertirlo.
  `DT-011` está pendiente de método y exige decidirlo «con datos»; con ambas series en disco ese método
  puede evaluarse comparando lo entrenado contra la verdad, cosa imposible en (b) y (c). El dataset
  sintético es además el **único** lugar donde la demanda latente es conocible: con datos reales no lo
  será nunca. (d) se descarta sin más: dos componentes dueños de la misma verdad.

- **Consecuencias:** Una entidad nueva en el modelo; el archivo más grande del dataset (108 235 filas,
  ~3,5 MB con la escala vigente, no versionado); y una entidad **sin equivalente con datos reales**,
  que conviene que nadie lea como registro histórico. A cambio, C3 y C4 quedan disjuntos y la Fase 5
  puede entrenar sobre la definición correcta de demanda.

- **No decide:** `DT-011`, que sigue pendiente de método.

- **Pendientes cerrados el 2026-09-24:** el contrato de `consumption.csv` está en `DT-038` §4, y el
  mecanismo de recorte quedó fijado por decisión del responsable como
  `consumption = min(demanda latente, existencia antes del consumo)`, **por día y sin backlog**: la
  demanda no satisfecha se pierde y `lost_sales` es derivable, no almacenada.

- **Estado:** `ACEPTADA`

## DT-035 — Políticas sintéticas de generación de demanda

> **Documento completo:** [`docs/decisions/DT-035-politicas-generacion-demanda.md`](decisions/DT-035-politicas-generacion-demanda.md).

- **Decisión:** El Componente 3 genera la demanda con políticas sintéticas documentadas, al amparo de
  §3.5 de la especificación y siguiendo el patrón de `DT-028`. **Dos ejes ortogonales**: cada producto
  recibe una **forma** de las seis de §8 y una **rotación** de las dos de `DT-023` §7.2, cada eje con
  su propia mezcla que suma 100 % y con suelo de un producto por clase.

  | Forma | % | | Rotación | % |
  |---|--:|---|---|--:|
  | `STABLE_DEMAND` | 30 | | `HIGH_ROTATION` | 30 |
  | `GROWING_DEMAND` | 15 | | `LOW_ROTATION` | 70 |
  | `DECLINING_DEMAND` | 15 | | | |
  | `SEASONAL_DEMAND` | 20 | | | |
  | `INTERMITTENT_DEMAND` | 10 | | | |
  | `ERRATIC_DEMAND` | 10 | | | |

  Mecanismo: `cantidad(t) = max(0, redondeo(nivel · tendencia(t) · estación(t) · ruido(t)))`, todo en
  **aritmética entera en por mil**, sin un solo flotante. La estacionalidad usa una **onda triangular
  y no un seno**, porque `math.sin` lo calcula la `libm` de la plataforma y sus últimos bits no están
  garantizados entre versiones — lo que desharía la identidad byte a byte de `DT-032` para cada
  producto estacional. `INTERMITTENT_DEMAND` sigue una ruta propia: sus ceros son días sin evento, no
  un nivel que redondea a cero. Precondición **P-6**: `product_count ≥ 6`.

- **Contexto:** §8 describe las seis formas **cualitativamente** y no fija ninguna fórmula ni ningún
  número; §32 lista cinco parámetros que el generador «deberá permitir controlar» y les asigna cero
  valores. El nivel base de demanda —sin el cual no hay serie— no lo nombra nadie. Sin esto, C3 no es
  implementable.

- **Alternativas:** (a) Políticas sintéticas documentadas, constantes del componente. (b) Preguntar al
  negocio. (c) Añadirlas a `DatasetConfig` ahora. (d) Valores aleatorios sin rango.

- **Razón:** (a), por §3.5 y por el precedente de `DT-028`. (b) pediría al negocio volúmenes de un
  catálogo que no existe, y §6 ya dice que el dataset «no debe pretender representar el volumen real».
  Cada número se eligió para que el comportamiento sea **falsable midiendo la serie**: el ruido
  errático es cuatro veces el estable, los niveles de rotación están separados por un orden de
  magnitud, y la intermitencia tiene mecanismo propio. Un generador que produjera ruido plano bajo los
  ocho nombres pasaría una comprobación de etiquetas y fallaría todas las pruebas de comportamiento.

- **Consecuencias:** Los ocho comportamientos son verificables sobre los datos — con la escala vigente,
  CV estable 0,06 frente a errática 0,36; creciente termina en 1,53× y decreciente en 0,46×;
  intermitente con 85 % de ceros frente a 0 %; autocorrelación anual estacional 0,46 frente a −0,00; y
  rotación alta 41,7 unidades/día frente a 3,0 de la baja. A cambio, son constantes del código y P-6
  hace inatendibles algunas configuraciones válidas.

- **No decide:** ninguna política empresarial; ni el contrato de `demand.csv` (`DT-034`); ni la
  asignación de escenarios, que es del Componente 7; ni `DT-P12`.

- **Estado:** `ACEPTADA`

## DT-036 — Políticas sintéticas de inventario y reabastecimiento

> **Documento completo:** [`docs/decisions/DT-036-politicas-sinteticas-inventario.md`](decisions/DT-036-politicas-sinteticas-inventario.md).

- **Decisión:** El Componente 4 simula el ciclo causal completo —existencia → disparo → orden → lead
  time → recepción → movimiento → existencia— con políticas sintéticas documentadas, al amparo de
  §3.5 de la especificación y siguiendo el patrón de `DT-028` y `DT-035`. Viven en `policies.py`,
  **no** en `dataset_config.yaml`.

  ```text
  on_hand_base(i) = ceil( d̄_i × (L_i + M) )        W = 28   M = 7   C = 21
  on_hand(i)      = ceil( on_hand_base(i) × factor )   AJUSTADO 750‰ · NORMAL 1000‰ · HOLGADO 1500‰
  disparo:  on_hand_después_del_consumo + quantity_in_transit ≤ s(t)     mezcla 30 / 40 / 30
  s(t)      = ceil( d̄_recent(t) × L_i )
  raw_need  = Q = ceil( d̄_recent(t) × C )
  si raw_need ≤ 0: NO HAY ORDEN                                          (guarda de V1-06)
  Q_final   = ceil( max(raw_need, MOQ) / order_multiple ) × order_multiple
  ```

  `d̄_i` y `d̄_recent` se calculan como **racional exacto**, por par `(product_id, location_id)` y sin
  redondeo intermedio.

  Fija además: el **saldo de apertura** como movimiento `ADJUSTMENT` con
  `reference_type = INITIAL_INVENTORY`, `reference_id` vacío y `reason_code = OPENING_BALANCE`; el
  **warm-up** de `W` días de `d̄_recent`, continuo con la ventana móvil en su punto de empalme; la
  regla de los **cinco productos sin proveedor activo** (`L_i` de su relación inactiva, solo para
  dimensionar la apertura); la **convención temporal** de documentos y movimientos, con los campos de
  auditoría **vacíos**; y la versión destino de `GENERATOR_VERSION` para el lote C6 + C4 + C5,
  **`0.3.0`**. La regla de cuándo incrementar la versión es la **regla general de `DT-033`**, basada en
  el artefacto publicado; *la enumeración de parámetros que tenía `DT-036` §8 quedó retirada el
  2026-09-26*.

  *Correcciones del 2026-09-24, tras la auditoría pre-implementación:* se incorpora la guarda
  `raw_need ≤ 0` de `V1-06`, que faltaba; se sustituye `inventory_on_order` por el nombre canónico
  `quantity_in_transit`; se fija que el disparo se evalúa **después** del consumo del día; y se
  retira `updated_at` de los campos con instante, por coherencia con `DT-024`.

- **Contexto:** §§10, 11 y 14 de la especificación describen qué situaciones de inventario deben poder
  observarse, sin una sola fórmula ni un solo número. `docs/06` sí las tiene, pero son las del motor
  real y dependen de un pronóstico que en la Fase 1 no existe y de parámetros de negocio pendientes
  (`BR-X01`, `BR-X02`, `BR-X13`, `DT-010`, `DT-P05`).

- **Alternativas:** (a) Políticas sintéticas documentadas. (b) Reutilizar las fórmulas de `docs/06`.
  (c) Añadir `W`, `M`, `C` a `DatasetConfig`. (d) Generar inventario sin bucle causal.

- **Razón:** (a), por §3.5 y por precedente. (b) exigiría inventar parámetros de negocio **y** borraría
  la frontera entre el generador y el motor. (c) reabriría el Componente 1, cerrado. (d) la prohíbe
  §14: «No se debe generar tránsito artificial independiente de las órdenes de compra».

- **Consecuencias:** El Componente 4 es implementable sin inventar ningún parámetro de negocio, y
  `inventory.csv` queda reconstruible desde `inventory_movements.csv`. A cambio, los parámetros son
  constantes del código que el manifiesto no registra —de ahí la regla de `GENERATOR_VERSION`—, seis
  productos quedarán con sobreinventario permanente por MOQ y cinco sin proveedor terminarán en cero.
  Ambas cosas son correctas y están declaradas para que no se lean como defectos.

- **No decide:** ninguna política empresarial. **`s` no es un punto de reorden, `Q` no es una
  recomendación de compra y `C` no es `target_coverage_days`.** No escribe `InventoryPolicy`, no
  altera `DT-031`, no asigna escenarios (Componente 7) y no fija ningún porcentaje obligatorio de
  desabasto.

- **Estado:** `ACEPTADA`

## DT-037 — Comportamiento sintético de proveedores

> **Documento completo:** [`docs/decisions/DT-037-comportamiento-sintetico-proveedores.md`](decisions/DT-037-comportamiento-sintetico-proveedores.md).

- **Decisión:** El Componente 6 entrega **perfiles deterministas por proveedor** y nada más. **No
  escribe ningún archivo** (§42.1: sería metadata de generación en una entidad de negocio) y **no
  conoce ninguna orden**; figura en `manifest.components` con cero archivos. Dos ejes ortogonales,
  patrón de `DT-035`:

  | Puntualidad | `on_time_permille` | retraso | % | | Integridad | `partial_permille` | % |
  |---|--:|---|--:|---|---|--:|--:|
  | `PUNCTUAL` | 900 | 1–3 d | 40 | | `COMPLETE` | 0 | 70 |
  | `IRREGULAR` | 650 | 1–7 d | 40 | | `SPLIT` | 250 | 30 |
  | `LATE` | 250 | 3–14 d | 20 | | | | |

  En `SPLIT`, la primera recepción se lleva entre 400 ‰ y 800 ‰ y el faltante llega entre 1 y 10 días
  después, con `q1 + q2 = Q_final` exacto. **C4 aplica estos parámetros a órdenes concretas**, porque
  la decisión depende de la orden y C6 no conoce ninguna.

- **Contexto:** §12 describe los tres comportamientos de proveedor de forma puramente cualitativa y no
  contiene un solo número; §13 exige variación suficiente sin decir cuánta. Sin estos parámetros, C6
  no es implementable y C4 no puede fechar ninguna recepción.

- **Alternativas:** (a) Dos ejes ortogonales documentados. (b) Un eje con cinco perfiles combinados.
  (c) Que C6 escriba `supplier_behaviour.csv`. (d) Que C6 genere las recepciones. (e) Derivar el
  comportamiento de un atributo real del proveedor.

- **Razón:** (a), por §3.5 y por el precedente inmediato de `DT-035`. (c) la prohíbe §42.1; (d) haría
  de C6 una segunda simulación; (e) exigiría inventar una calificación de proveedor que el negocio no
  ha definido.

- **Consecuencias:** `RELIABLE_SUPPLIER`, `DELAYED_SUPPLIER` y `PARTIAL_DELIVERY` quedan cubiertos por
  **construcción del reparto** (4/4/2 y 7/3 con diez proveedores), y el lead time observado pasa a
  existir y a diferir del acordado. **Tres limitaciones conocidas de V1, declaradas y no corregidas:**
  no hay entregas anticipadas (O-1); `LEAD_TIME_CAPPED` no se ejercita, porque el observado máximo es
  58 días frente al techo de 90 (O-2); y la cobertura debe medirse sobre productos, no sobre
  proveedores (O-3).

- **No decide:** ningún nivel de servicio, acuerdo comercial ni calificación de proveedor; no describe
  a ningún proveedor real; no genera órdenes, recepciones, movimientos, tránsito ni inventario; no
  modifica `V1-09` ni su techo.

- **Implementación del 2026-09-28.** El Componente 6 queda implementado en
  `generator/supplier_behaviour.py` (`DT-037` §6), sin cambiar ninguna regla. **A1:** no escribe
  archivos de datos y añade él mismo su entrada a `manifest.components`. **A2:** importa
  `SupplierProfile` de `generator/inventory.py`, solo el tipo. No está conectado a `__main__`: el
  lote C6 → C4 → C5 se conecta con W1 (`DT-040`), y `generator_version` sigue en 0.2.0.

- **Enmienda del 2026-09-26 (D-C4-1, opción O1).** La primera recepción de una entrega partida pasa a
  `q1 = min(Q_final − 1, max(1, ceil(Q_final × split / 1000)))`, con `q2 = Q_final − q1`. Sin la cota,
  `Q_final` de 2 a 4 con `split = 800` daba una segunda recepción de cero unidades. Ningún valor
  aprobado cambia; para `Q_final ≥ 5` dentro de 400–800 ‰ el resultado es el mismo que antes.

- **Estado:** `ACEPTADA`

## DT-038 — Contrato de salida del Componente 4

> **Documento completo:** [`docs/decisions/DT-038-contrato-salida-c4.md`](decisions/DT-038-contrato-salida-c4.md).

- **Decisión:** El Componente 4 tiene contrato de salida propio, con el patrón de `DT-024`. Fija las
  columnas, tipos, nulabilidad, claves de negocio, orden de filas, identificadores y precisión de
  `consumption.csv`, `inventory_movements.csv` e `inventory.csv`, y la estructura en memoria que
  entrega al Componente 5. Cierra además seis puntos que no estaban escritos en ninguna parte:

  | Punto | Regla |
  |---|---|
  | Unidad de cálculo | El par `(product_id, location_id)`, nunca el producto aislado |
  | Orden causal del día | recepciones → demanda → consumo → **disparo, después del consumo** → orden |
  | Consumo | `min(demanda latente, existencia antes del consumo)`, **sin backlog**; `lost_sales` derivable |
  | Signo de los movimientos | `ADJUSTMENT` de apertura y `RECEIPT` positivos; `ISSUE` negativo |
  | Referencias | `INITIAL_INVENTORY` (sin `reference_id`), `PURCHASE_ORDER_RECEIPT`, `CONSUMPTION` |
  | Identificadores | Los asigna C4 para las seis entidades, con clave de ordenamiento total y desempate explícito |

  `consumption.csv` es **densa**, con la misma rejilla que `demand.csv`. `inventory.csv` es un
  **snapshot final**, una fila por par, reconstruible desde los movimientos. Incorpora la guarda
  `raw_need ≤ 0` de `V1-06`, el corte del periodo y el contrato del directorio de salida.

- **Contexto:** `DT-024` cubre solo las cinco entidades maestras y `DT-034` solo `demand.csv`; §41.3
  de la especificación declaraba el resto pendiente «al autorizar cada uno». La auditoría
  pre-implementación del 2026-09-24 lo encontró como bloqueante: la regla de identificadores de
  `DT-024` **no tiene orden al que referirse** mientras la clave de negocio de cada entidad nueva no
  esté declarada, lo que dejaba la reproducibilidad del `id` colgando del orden del bucle.

- **Alternativas:** (a) Un ADR de contrato por componente. (b) Ampliar `DT-024`. (c) Dejar los
  contratos en el código. (d) Heredar implícitamente las reglas de `DT-024`.

- **Razón:** (a). (d) es la que la auditoría descartó con evidencia; (b) alteraría una decisión
  aceptada cuyo alcance es otro componente; (c) contradice `CLAUDE.md` §8.

- **Consecuencias:** El Componente 8 tiene contra qué validar y los casos degenerados —consumo cero,
  apertura cero, `d̄_recent` cero— tienen regla escrita. A cambio, la asignación de identificadores en
  seis pasos obliga a completar la simulación antes de escribir: el generador deja de poder escribir
  en streaming.

- **No decide:** ninguna política de negocio; ni el contrato del Componente 5 (`DT-039`); ni estados
  de orden que `docs/04` §3.9 no tenga.

- **Actualización del 2026-09-26 (D-01).** `SimulatedOrder` **ya no lleva `order_number`**: lo forma
  el Componente 5 (decisión A2), y el Componente 4 no conoce ninguna política de cancelaciones.
  `expected_on` es la única fuente de la fecha comprometida y el Componente 5 la copia. Se corrige la
  autoría de los identificadores: C4 numera todo lo causal y sus propias entidades; **no** las filas
  sintéticas que crea C5. Y §13 pasa a remitir a `DT-040`: ningún componente escribe en `output/`.

- **Actualización del 2026-09-26 (implementación de C4).** **D-C4-2 = P1**: precondiciones P-C4-2
  (`period.days ≥ W`) y P-C4-3 (cada producto vigente al menos `W` días del periodo); si fallan, la
  generación falla y la ventana nunca se acorta, rellena ni extrapola (§16). **D-C4-3**: `L` es el
  lead time acordado de la relación preferente activa, sin `V1-09` ni `R_v1`; `M` solo interviene en
  la apertura; el disparo se evalúa todos los días (§§3 y 7). Se documentan los flujos
  pseudoaleatorios del componente (§17). El miembro `metrics` de `SimulationResult` queda **pendiente**:
  remite a una «`DT-036` §17 del acuerdo» que no existe, y no se implementa (§12).

- **Cierre del 2026-09-29.** `metrics` de §12 no se implementará: el Componente 4 no cambia y el
  Componente 8 deriva de los archivos lo que el informe necesita (decisión C7/C8-09, `DT-042`).

- **Estado:** `ACEPTADA`

## DT-039 — Contrato de salida del Componente 5

> **Documento completo:** [`docs/decisions/DT-039-contrato-salida-c5.md`](decisions/DT-039-contrato-salida-c5.md).

- **Decisión:** El Componente 5 **materializa y no simula**. Fija las columnas, tipos, claves, orden
  de filas y estados de `purchase_orders.csv`, `purchase_order_items.csv` y
  `purchase_order_receipts.csv`; conserva literalmente los identificadores que le pasa el
  Componente 4 y numera, a continuación, solo las filas sintéticas que él mismo crea; y **forma el
  `order_number` de todas las órdenes** como `"PO-" + id` con relleno de ceros de ancho
  `max(6, dígitos del id más alto de la ejecución)`, ensanchable con la misma regla de `DT-028` §4.
  `issued_at` y `expected_at` se **copian** de lo que calculó el Componente 4; no se recalculan.

  **Órdenes `CANCELLED` sintéticas.** §14 de la especificación exige que el dataset contenga órdenes
  canceladas y ninguna política las generaba. Se adopta un conjunto **acotado, no causal y separado**:
  el Componente 5 copia una plantilla de entre las órdenes causales y emite una gemela con
  `status = CANCELLED`, sin recepciones y sin movimientos, gobernada por
  `ORDERS_CANCELLED_PERMILLE` y `ORDERS_CANCELLED_CLOSE_LAG_DAYS` en `policies.py` y por la
  sub-semilla `orders`. Son **neutras para el inventario por construcción**: `docs/04` §3.9 limita el
  tránsito a `ISSUED` y `PARTIALLY_RECEIVED`. **`DRAFT` no se emite**, porque ninguna sección lo
  exige.

- **Contexto:** sin contrato, los tres archivos de órdenes quedaban sin columnas, sin `order_number`
  y sin autoridad única sobre los identificadores; y la exigencia de órdenes canceladas de §14 no
  tenía ningún mecanismo, de modo que el implementador solo podía incumplir la especificación o
  inventar una probabilidad de cancelación.

- **Alternativas:** (a) C5 materializa y las canceladas se copian de una plantilla causal. (b) C4
  cancela causalmente. (c) C5 calcula la cantidad con `V1-06`. (d) No emitir ninguna cancelada.
  (e) Emitir también `DRAFT`.

- **Razón:** (a). (b) exigiría una condición de cancelación, es decir una regla de negocio que nadie
  ha declarado; (c) convertiría a C5 en un segundo simulador; (d) incumple §14; (e) amplía sin
  necesidad.

- **Consecuencias:** el dataset cubre las cuatro situaciones de órdenes de §14 y la frontera «C4
  calcula, C5 materializa» pasa a ser comprobable. A cambio, las órdenes canceladas son el único dato
  del dataset que no procede del bucle causal, y `currency` y `total_amount` quedan vacíos.

- **No decide:** ninguna regla de negocio. `ORDERS_CANCELLED_PERMILLE` **no es una tasa de
  cancelación de ninguna organización**.

- **Actualización del 2026-09-26 (D-01).** El responsable aprobó `ORDERS_CANCELLED_PERMILLE = 20` y
  `ORDERS_CANCELLED_CLOSE_LAG_DAYS = 1` como parámetros sintéticos de cobertura; `closed_at` **no se
  recorta nunca**. Regla **B2**: si `K > 0` y no hay ninguna orden elegible —incluido `N = 0`—, el
  Componente 5 lanza `GeneratorError`, la ejecución falla y **no hay promoción** (`DT-040`), de modo
  que `output/` queda intacto. Con `0 < elegibles < K` se emiten tantas como elegibles haya.
  `expected_at` pasa a figurar entre los campos que la orden gemela copia de su plantilla.

- **Actualización del 2026-09-27 (cierre de D-01, opción A).** Una orden causal solo es elegible como
  plantilla si su cierre previsto, `issued_on + ORDERS_CANCELLED_CLOSE_LAG_DAYS`, cumple a la vez
  `< end_date` (condición existente, estricta) y `<= valid_to` del producto, o `valid_to` nulo. Es una
  restricción sintética de elegibilidad, aplicada **antes** de calcular `K` y de seleccionar; B2 se
  aplica sobre el conjunto resultante. `closed_at` sigue siendo `issued_at + 1 día`, sin recorte.
  **`DT-027` no cambia**: la cancelación sintética no usa la excepción de recepciones en vuelo.
  Autoridad: `DT-039` §5.2, punto 1.

- **Implementación del 2026-09-28.** El Componente 5 queda implementado en `generator/orders.py`
  (`DT-039` §13), sin cambiar ninguna regla: universo de plantillas filtrado primero, después `K`
  (sobre el número de órdenes causales, acotado por el de elegibles), B2 y `cancelled-selection`;
  gemelas con `closed_at = issued_at + 1 día` sin recorte; `order_number` para todas. No está
  conectado a `__main__` porque el Componente 6 no existe; `generator_version` sigue en 0.2.0.

- **Estado:** `ACEPTADA`

## DT-040 — Publicación atómica del dataset: workspace de ejecución y promoción final

> **Documento completo:** [`docs/decisions/DT-040-publicacion-atomica-dataset.md`](decisions/DT-040-publicacion-atomica-dataset.md).

- **Decisión (W1):** cada ejecución completa del generador trabaja en su propio workspace,
  `data/synthetic/tmp/<id_de_ejecución>/`, y `data/synthetic/output/` solo cambia cuando el
  orquestador **promociona el workspace entero**, después de que todos los componentes hayan
  terminado y la verificación final haya pasado. Ningún componente escribe en `output/`; los
  componentes no cambian de interfaz, porque ya reciben el directorio como parámetro, y el modelo de
  archivos intermedios se mantiene. La promoción es un **renombrado de directorios** en el mismo
  sistema de archivos, nunca una copia archivo a archivo. `tmp/` es la convención del `.gitignore`
  existente para directorios temporales.

  > Un dataset solo se considera **publicado** cuando la ejecución completa ha terminado bien y su
  > workspace ha sido promocionado.

- **Contexto:** la regla B2 de `DT-039` exige que un fallo por cero órdenes elegibles no publique
  nada, pero C2, C3 y C4 escribían en `output/` antes de que C5 pudiera evaluarla. El resultado era
  un dataset parcial en un directorio vacío, o un dataset **mezclado** —contra la regla 5 de
  `DT-038` §13— en un directorio con un dataset anterior, que además se perdía.

- **Alternativas:** (W1) workspace y promoción al final. (W2) Todo en memoria y escritura al final.
  (W3) Escribir en `output/` y borrar lo escrito si algo falla.

- **Razón:** W1. W2 refactoriza la entrada de C3 y C4, que leen de disco. W3 no es atómica y no
  recupera un dataset anterior ya sobrescrito.

- **Consecuencias:** fallar implica no publicar, y un dataset válido anterior sobrevive a cualquier
  ejecución fallida. A cambio, el disco aloja dos datasets durante una ejecución, `output/` no existe
  durante un instante de la promoción y no se admiten ejecuciones concurrentes sobre el mismo
  `output/`.

- **Pendiente de confirmación:** si el dataset sustituido se elimina tras una promoción correcta, y si
  el workspace de una ejecución fallida se conserva para diagnóstico. Ambos propuestos, no aprobados.

- **Implementación del 2026-09-29.** W1 queda implementado en `generator/pipeline.py` y
  `__main__.py` lo usa: comprobación previa de `output/`, workspace `tmp/<uuid>/`, C2 → C3 → C6 → C4
  → C5, verificación final (versiones, conjunto de archivos, `sha256`, filas, cabeceras, existencia
  sin negativos) y promoción por los renombrados de §5. **Detalles pendientes resueltos por el
  responsable:** el `.anterior` se elimina tras una promoción correcta y el workspace de una
  ejecución fallida también se elimina (no se conserva). La promoción **no** es atómica: entre (a) y
  (b) `output/` no existe un instante, y si fallan (b) y (c) el dataset anterior queda íntegro en
  `tmp/<id>.anterior/`. `GENERATOR_VERSION` pasa a **0.3.0** (`DT-036` §8, regla de `DT-033`).

- **Corrección de texto del 2026-09-28.** `DT-040` §3 hablaba de «Componentes C2 a C5»; ahora nombra
  los cinco del flujo aprobado, C2, C3, C6, C4 y C5, y precisa que C6 solo añade su entrada al
  manifiesto. Sin cambios en la decisión.

- **Integración de C7 y C8 (2026-09-29, `DT-042` §8).** El flujo es C2 → C3 → C6 → C4 → C5 → C7 →
  C8 → verificación → promoción. `verify` exige además `scenario_assignment` y un `quality_report`
  sin fallos, y `COMPONENT_VERSIONS` lista los siete componentes.

- **Estado:** `ACEPTADA` (con dos detalles de operación pendientes de confirmación)

## DT-041 — Scenario Assignment: contrato del Componente 7

> **Documento completo:** [`docs/decisions/DT-041-asignacion-escenarios-c7.md`](decisions/DT-041-asignacion-escenarios-c7.md).

- **Decisión:** el Componente 7 (`scenarios`, versión `0.1.0`) **registra** en
  `manifest.scenario_assignment` los 16 ejes de nivel A de `DT-023`, en el orden canónico del enum,
  cada uno con seis campos —`unit`, `basis`, `criterion`, `source`, `suppliers`, `products`—, y
  **mide** los ejes que emergen de la simulación. No escribe ningún CSV, no sortea, no genera ni
  corrige datos y no etiqueta el nivel C.
  - **Forma y rotación:** la decisión de C3, reconstruida con `build_demand` y aceptada solo si la
    demanda reconstruida coincide byte a byte (`sha256`) con `demand.csv` y con su entrada del
    manifiesto.
  - **Proveedores:** unidad primaria `supplier` (el perfil de C6); `products` son la evidencia de
    manifestación que exige §12. `RELIABLE = PUNCTUAL ∧ COMPLETE`, `DELAYED = LATE`,
    `PARTIAL = SPLIT`; `IRREGULAR` no recibe etiqueta.
  - **Observados:** `STOCKOUT` e `IN_TRANSIT` con los datos almacenados; `MULTIPLE_LEAD_TIMES` con
    `DT-028` §1.6.3; `LOW_INVENTORY` y `OVERSTOCK` con criterios marcados
    **`SYNTHETIC_COVERAGE_CRITERION`**, que no son reglas de negocio ni cierran `BR-X03`.
  - **Nivel C:** criterios de detección de las situaciones 8, 12, 18 y 20 en una función pura que C7
    no publica; los reportará el Componente 8.
  - **Vacío:** se registra (`[]`), no falla; `null` significa «no aplicable». Comprobar
    `scenarios.required` es del Componente 8.

- **Contexto:** `DT-025` aplazó la forma de `scenario_assignment` a la autorización de C7; `DT-035` y
  `DT-037` dejaron escrito que registrar las decisiones de C3 y C6 es de C7. La auditoría C7/C8 del
  2026-09-29 cerró las decisiones C7/C8-01 a 14.

- **Alternativas:** archivo aparte; índice producto → escenarios o recuentos; devolver los perfiles
  desde C3; inferir la forma del CSV; umbrales de N días; cobertura de proveedores por producto
  servido. Todas descartadas (documento completo).

- **Razón:** es la única forma que respeta `DT-025` y `DT-023`, no modifica C2–C6 y no introduce
  ningún número nuevo.

- **Consecuencias:** C7 queda implementado y probado **sin integrarse en W1**: `generate_into` no lo
  ejecuta, `GENERATOR_VERSION` sigue en 0.3.0 y el dataset publicado no cambia. La integración y la
  subida única a 0.4.0 llegan con el Componente 8.

- **Integración del 2026-09-29:** C7 se ejecuta en W1 después de C5 y antes de C8, con
  `generator_version` 0.4.0 (`DT-042`).

- **Estado:** `ACEPTADA`

## DT-042 — Dataset Validator e informe de calidad: contrato del Componente 8

> **Documento completo:** [`docs/decisions/DT-042-validador-dataset-quality-report.md`](decisions/DT-042-validador-dataset-quality-report.md).

- **Decisión:** el Componente 8 (`validator`, versión `0.1.0`) valida el **dataset materializado en
  el workspace** —los doce CSV y `manifest.json`— con un catálogo de **51 comprobaciones** en 16
  familias (manifiesto, formato, origen, identidad, referencias, comerciales, recepciones,
  canceladas, `order_number`, inventario, consumo, temporal, maestros, escenarios, cobertura y nivel
  C). Solo si todas pasan escribe `manifest.quality_report` con los veinte ítems de §35; si alguna
  falla, lanza `GeneratorError` con **todos** los hallazgos y no escribe nada. No repara, no genera,
  no re-selecciona y no sortea. El informe es determinista, sin flotantes ni campos volátiles, con
  `anomalies: []` y la limitación declarada. C7 y C8 se integran en W1 y `generator_version` sube
  una sola vez a **0.4.0**.
- **Contexto:** `DT-023`, `DT-025`, `DT-030` y `V1-08` encargaron al Componente 8 la validación, el
  nivel C y el informe; la auditoría C7/C8 cerró las decisiones restantes.
- **Alternativas:** informe en archivo aparte; validar objetos en memoria; publicar con avisos;
  catálogo de anomalías propio. Descartadas (documento completo).
- **Consecuencias:** ningún dataset que incumpla un contrato llega a `output/`; un dataset publicado
  siempre muestra `failed = 0`. Con escalas muy pequeñas la cobertura depende de la semilla y C8 puede
  rechazar la ejecución (es visible y no silencioso).
- **Estado:** `ACEPTADA`

---

> **`DT-043` a `DT-047` — Etapa 2, arquitectura y fundación del sistema principal (2026-09-30).** Las
> cinco se toman juntas porque fijan los contratos entre los mismos componentes. **Todas están en
> `PROPUESTA`** hasta que el responsable las apruebe; ninguna implementa nada. El detalle vive en los
> documentos oficiales de cada tema, no en archivos aparte.

## DT-043 — Estructura del código de la Etapa 2 y puertos locales

- **Decisión:** Un único proyecto Python, `backend/`, como monolito modular (`DT-002`), con un paquete
  por responsabilidad real: `supply_engine`, `ingestion`, `db`, `forecasting`, `runs`, `api`, `genai`.
  `frontend/`, `ml/` e `infra/` se crean con la unidad que los usa. Sin carpetas genéricas
  (`services/`, `repositories/`, `adapters/`, `domain/`…); cada puerto vive en el paquete que lo usa.
  Se añade un puerto a los de `DT-003`: **`TokenValidator`**, con un doble de desarrollo que solo se activa
  en local y en pruebas y se niega a arrancar en cualquier entorno desplegado, para que la API sea autenticada por defecto sin Entra ID (RNF-006). El
  código del sistema **no importa el generador**: consume su contrato. Las ejecuciones (carga,
  forecast, recomendaciones) son comandos batch; la API de V1 es de solo lectura. Dependencias por
  unidad: U1 ninguna; U2 un controlador de PostgreSQL y un PostgreSQL local en contenedor, y
  migraciones como **SQL versionado con un ejecutor mínimo propio**, sin ORM ni herramienta de
  migraciones; U5 FastAPI y Pydantic, ya en el stack. **Cada dependencia se autoriza al abrir su unidad.**
  *(U5, 2026-10-03: versiones exactas, servidor y cliente de pruebas en `DT-064`.)*
- **Contexto:** El repositorio no tiene código de aplicación. La Etapa 2 exige una estructura pequeña
  que no dé carpetas vacías ni capas sin consumidor (`CLAUDE.md` §6.2).
- **Alternativas:** (a) La estructura sugerida `backend/app/{api,domain,db,services,config}`.
  (b) Paquetes por responsabilidad. (c) El motor como proyecto instalable aparte. (d) Microservicios.
- **Razón:** (a) crea `domain/` y `services/` sin decir qué contienen, que es exactamente lo que se
  quiere evitar; el único dominio con reglas propias es el motor, y tiene nombre. (c) añade empaquetado
  y versionado sin que exista un segundo consumidor fuera del backend; `ml/` puede importarlo desde el
  mismo proyecto. (d) está descartado por `DT-002`. (b) hace visible la arquitectura de `docs/03` en el
  árbol de carpetas.
- **Consecuencias:** Las reglas de dependencia de `docs/03` §16.4 se verifican con pruebas. Un nuevo
  puerto (`TokenValidator`). A cambio, las lecturas de la API consultan `db` directamente; si aparece un
  segundo caso de uso con orquestación, se revisa.
- **Estado:** `ACEPTADA` (2026-09-30): el responsable la da por aprobada al autorizar U1 («la estructura ya aprobada en `DT-043`/`DT-045`»). Detalle: `docs/03` §16, `docs/10` §15.

## DT-044 — Ingesta del dataset sintético en PostgreSQL y modelo físico mínimo

- **Decisión:** Una base PostgreSQL contiene **un solo linaje** de datos: la carga de un *snapshot*
  de dataset se niega si la base ya contiene otro `dataset_version`, y es un **no-op** si contiene el
  mismo con los mismos `sha256`. La carga es **todo o nada**, en una transacción, con validación previa
  (manifiesto, `quality_report` en `PASS`, archivos, `sha256`, filas, cabeceras del contrato) y
  posterior (recuentos, reconciliación de inventario y tránsito, recepciones, referencias polimórficas,
  origen homogéneo). Se conservan los `id` del dataset como claves primarias; una tabla por archivo con
  sus columnas; cantidades en `numeric`; `data_origin` por registro y el manifiesto íntegro en
  `data_loads`. Se crean solo las tablas con consumidor (`docs/04` §9.2); `InventoryPolicy`,
  `RiskAssessment`, `SupplierPerformance`, `AuditLog` y `AppUser` se difieren con su motivo.
- **Contexto:** RF-022, RF-023, US-011 y el criterio de la Fase 2 («la posición almacenada coincide con
  la reconstruida»). La Etapa 1 terminó con el generador; la ingesta, que el roadmap situaba en la
  Fase 1, pasa a la Etapa 2 por instrucción del responsable (2026-09-30).
- **Alternativas:** (a) Un linaje por base. (b) Varios datasets en la misma base con `dataset_id` en
  cada fila y claves compuestas. (c) Sustituir el contenido al cargar otro dataset. (d) Cargar las
  filas válidas y rechazar las demás.
- **Razón:** (b) multiplica las claves de todo el esquema y hace posible mezclar SYNTHETIC y REAL en la
  misma base, que `CLAUDE.md` §10.9 solo admite con bandera de origen; el linaje único lo evita por
  construcción. (c) borra histórico (RNF-013). (d) deja el inventario irreconciliable, que
  es el estado inconsistente que RF-022 prohíbe. (a) es la más simple y responde de forma única a «¿con
  qué datos se calculó?».
- **Consecuencias:** Cambiar de dataset es cambiar de base (en desarrollo, recrearla con las
  migraciones). Las cargas incrementales de datos reales se diseñan cuando exista una fuente real.
  `numeric` en cantidades no decide `docs/04` §7; lo deja abierto sin exigir rediseño.
- **Ratificación al aceptarla (2026-10-01, decisión del responsable).**
  - *Cantidades:* las cantidades físicas de los CSV se almacenan como `numeric` **sin precisión fija**;
    no se usa `integer`. El dataset 0.4.0 solo trae enteros, pero el contrato admite cantidades
    racionales (`docs/06` §16.12) y `integer` obligaría a una migración estructural.
  - *`quantity_on_hand ≥ 0`:* compatible con el estado documental de `BR-X09`, cerrada para V1 por
    `V1-13` («no se permite inventario negativo; es incidente de datos»). Si el negocio la cierra de
    otro modo, es una migración (`docs/04` §9.3).
  - El resto del texto se acepta sin cambios. Implementación: U2 (`DT-055`).
- **Estado:** `ACEPTADA` (2026-10-01, decisión del responsable al abrir U2). Detalle: `docs/04` §9.

## DT-045 — Contrato de implementación del motor de abastecimiento V1

- **Decisión:** `supply_engine` expone una evaluación pura por producto–ubicación y fecha de corte
  explícita, con una función por regla de `DT-031`. Recibe **todas** las relaciones con proveedor y
  elige él (`V1-10`); recibe el consumo, las líneas abiertas, las observaciones de lead time, el
  inventario al corte, el forecast y un conjunto de parámetros. Devuelve `outcome` (`RECOMMEND`,
  `NO_NEED`, `NOT_CALCULABLE`), razones, marcas y el desglose completo de `docs/06` §13. Los
  parámetros V1 son **reglas del motor** que viajan en `policy_snapshot` con `policy_set =
  V1_PROVISIONAL`, no filas de `InventoryPolicy`. `urgency` queda nula y `reorder_point` persiste el
  nivel objetivo `S`. El motor no lee `data_origin`.
- **Contexto:** `DT-031` fijó las reglas; faltaba la forma en que se implementan sin que el motor
  dependa de la base, de la API ni del LLM (RNF-001, RNF-002).
- **Alternativas:** (a) El motor lee la base. (b) El motor recibe la relación ya elegida. (c) El motor
  recibe todas las relaciones y elige. (d) Parámetros V1 en `InventoryPolicy`.
- **Razón:** (a) rompe la pureza que exige `docs/06` §1. (b) saca `V1-10` del motor y lo reparte entre
  llamadores. (d) desfigura la entidad: `z_v1` no es un nivel de servicio y `N_v1`, `N_MIN_v1` y
  `LT_MAX_v1` no tienen campo; además presentaría como política lo que `DT-031` dice que no lo es.
- **Consecuencias:** El motor se prueba sin nada más que Python. Los bordes temporales se cerraron
  con `DT-P15` y los tres casos de §14 con `DT-P20`. Los tres detalles de `V1-05` que quedaban
  abiertos se cerraron con `DT-P14` el 2026-10-01.
- **Cierre de `DT-P14` (2026-10-01).** `σ_H` con estimador poblacional; `n = 0` → `NOT_CALCULABLE`
  (`INSUFFICIENT_HISTORY`), `n = 1` → `σ_H = 0`. Estrategia **B3**: todos los términos racionales
  exactos, `z_v1 = 33/20`, y toda decisión que depende de `σ_H` —`RECOMMEND` / `NO_NEED`, `Q_moq`,
  `ceil`, `Q_final`, marcas— por comparación algebraica exacta de `x = P + √B/D`, sin tolerancias; la
  raíz decimal (28 cifras significativas, `ROUND_HALF_EVEN`, correctamente redondeada) solo se usa
  para **informar**. Entradas numéricas: entero, decimal finito o racional; `float`, NaN e infinito
  se rechazan (`docs/13` §3.1). Es la forma de evaluar `V1-01`, `V1-04`, `V1-05`, `V1-06` y `V1-09`, no
  una regla nueva. Texto normativo: `docs/06` §16.6.
- **Corrección del 2026-09-30 (`DT-P15`).** La versión inicial llamaba `review_date = as_of_date + 1`
  a la fecha de decisión y de emisión sugerida. `DT-031` llama a `as_of_date` «la fecha de la
  decisión»; se corrige: la decisión y la emisión sugerida son `as_of_date`, y `as_of_date + 1` es solo
  el primer día del horizonte (`horizon_start`). Ninguna cifra cambia.
- **Cierre del contrato de U1 (2026-10-01).** Los detalles que §16.3 a §16.5 dejaban abiertos se
  cierran en `DT-048` a `DT-052` (`docs/06` §16.11) y en `DT-P22`; no queda ningún punto abierto.
- **Estado:** `ACEPTADA` (2026-09-30, al autorizar U1). Detalle: `docs/06` §16.

## DT-046 — Contrato de `ForecastProvider` y semanas ancladas en el primer día del horizonte

- **Decisión:** El proveedor de forecast recibe el consumo diario hasta `as_of_date` —y rechaza
  cualquier fecha posterior— y devuelve periodos semanales **anclados en `horizon_start = as_of_date +
  1`**, con intervalo, método, confianza y versión de modelo. El horizonte de V1 es el derivado de las
  reglas del motor: 14 semanas. La demanda latente no es entrada ni *feature*.

  **Frontera (aceptada el 2026-10-02, al autorizar U3).** `ForecastProvider` es una biblioteca **pura**
  en `backend/app/forecasting/`, que solo usa la biblioteca estándar: no importa `db` ni
  `supply_engine`, no accede a PostgreSQL, no persiste, no conoce `data_loads`, no calcula métricas de
  evaluación y no decide compras.
  - **Recibe** un `ForecastRequest` ya preparado: `product_id`, `location_id`, `as_of_date`,
    `history_start` y la serie diaria **contigua** de consumo —cantidades `int`, `Decimal` finito o
    `Fraction`, nunca `float`— con sus banderas `is_stockout_affected`, todo con fecha `≤ as_of_date`.
  - **Devuelve** un `ForecastResult`: por cada baseline calculable, su definición (`name`, `version`,
    `hyperparameters`) y los 14 periodos `(period_start, period_end, predicted_quantity, lower_bound,
    upper_bound)` en `Decimal`; los baselines no calculables, con su motivo; y la serie primaria con su
    `confidence_flag` (`DT-056`).
  - Valida su entrada (contigüidad, fechas `≤ as_of_date`, tipos) y los invariantes de su salida antes
    de devolverla.
  - Leer la base, construir la petición, registrar `model_versions`, crear `calculation_runs` y persistir
    `forecasts` corresponde a `backend/app/runs/` (`DT-057`).
- **Contexto:** `V1-04` suma semanas completas desde el inicio del horizonte; con semanas de
  calendario, la primera sería parcial y la fórmula dejaría de ser la de `DT-019`. Al autorizar U3 se
  resolvieron dos contradicciones documentales sin decisión de negocio: el flujo conceptual de `docs/03`
  §5.1 (Etapa 0), en el que `forecast_service` lee y guarda en PostgreSQL, y la firma conceptual
  `predict(sku, horizon, as_of)` de `docs/03` §4. Prevalecen `docs/03` §16 (`DT-043`, `ACEPTADA`), más
  específico y posterior, y este contrato.
- **Alternativas:** (a) Semanas ISO de calendario. (b) Semanas ancladas en el primer día del horizonte.
  Para la frontera: (c) proveedor con acceso directo a la base; (d) proveedor puro que recibe la serie
  preparada.
- **Razón:** (b) hace exacta `demand_over_horizon` sin una segunda regla de conversión; (a) exigiría
  prorratear la primera semana, que es justo lo que `docs/06` §5.1 prohíbe reimplementar. (d) permite
  probar los baselines sin PostgreSQL, respeta las reglas de dependencia de `docs/03` §16.4 y deja
  sustituir el baseline por un modelo (Fases 5 y 6) detrás de la misma interfaz; (c) acoplaría el
  cálculo a la base.
- **Consecuencias:** Los periodos de un forecast dependen de su `as_of_date`; dos forecasts con cortes
  distintos no comparten periodos. Es coherente con que un forecast nunca se sobrescribe. **Queda
  abierto** cómo se concilia con `docs/05` §2 (forecast semanal, recálculo diario de recomendaciones):
  generar un forecast por cada corte de recomendación, o que `demand_over_horizon` admita un inicio
  desplazado con el mismo prorrateo uniforme. Es `DT-P21`, antes de U4 *(resuelto el 2026-10-03 por `DT-058`: un forecast por corte de recomendación, sin desplazamiento)*. El horizonte de 14 semanas
  prevalece en V1 sobre el valor de trabajo de 8–12 semanas de `ASSUMPTION-002` (`docs/05` §2), como ya
  reconoce `docs/05` §19.2; `ASSUMPTION-002` sigue vigente como supuesto.
- **Estado:** `ACEPTADA` (2026-10-02, al autorizar U3; hasta entonces `PROPUESTA`). Detalle: `docs/05`
  §19.

## DT-047 — Orden de implementación de la Etapa 2 y primera unidad

- **Decisión:** U1 motor V1 puro → U2 PostgreSQL + ingesta del 0.4.0 → U3 forecast baseline → U4
  ejecución de recomendaciones persistida → U5 API de solo lectura → U6 explicación por plantilla;
  después, interfaz (Fase 7), ML (Fase 5), Power BI (Fase 11), Entra ID (Fase 8), IA generativa real
  (Fases 9–10), contenedores y CI/CD (Fases 12–13). **Primera unidad: el motor V1.**
- **Contexto:** El roadmap ordena Fase 2 → Fase 3 → Fase 4. La parte pura de la Fase 4 no depende
  técnicamente de las Fases 2 y 3 (RNF-001); sí dependen de ellas su persistencia, su proceso batch y
  sus endpoints, que siguen después.
- **Alternativas:** (a) Motor primero. (b) PostgreSQL + ingesta primero. (c) API primero.
- **Razón:** Ambas (a) y (b) están en el camino crítico hacia la primera recomendación trazable y
  ninguna depende de la otra. (a) no necesita ninguna dependencia ni infraestructura nueva, sus **reglas**
  están cerradas y aceptadas (`DT-031`, once casos de prueba con dueño «motor») —su contrato de
  implementación, `DT-045`, está propuesto y le faltan `DT-P14`, `DT-P15` y `DT-P20` *(las tres cerradas
  después: `DT-P15` y `DT-P20` el 2026-09-30, `DT-P14` el 2026-10-01)*—, es la máxima
  prioridad de pruebas (`CLAUDE.md` §12.6) y fija qué datos debe proveer la base. (b) necesita
  autorizar un controlador de PostgreSQL, un entorno de base local y el mecanismo de migraciones, y
  arrastra más decisiones abiertas. (c) no tiene nada que servir.
- **Consecuencias:** El valor llega primero como biblioteca probada, no como pantalla. U2 puede
  prepararse en paralelo en cuanto se autoricen sus dependencias.
- **Autorización de U3 (2026-10-02).** U3 = `backend/app/forecasting/` (contrato de `DT-046`,
  baselines de `DT-056`) + ejecución de forecast en `backend/app/runs/` + migración `0002` (`DT-057`).
  Sin dependencias nuevas: `forecasting` solo usa la biblioteca estándar y `runs`, el grupo opcional
  `db` de `DT-055`. U1 y U2 no se modifican y no se crea ninguna ruta de producción entre U1 y U3.
  **Autorizar U3 significa que su implementación puede comenzar; U3 no está implementada.** Criterios
  de cierre: `docs/05` §19.9.
- **Autorización de U4 (2026-10-03).** U4 = `backend/app/runs/recommendation.py`,
  `recommendation_inputs.py` y `recommendation_config.py` + migración `0003` (`recommendations` y las
  columnas `forecast_run_id` y `engine_version` de `calculation_runs`) + subcomando
  `python -m app.runs recommend --as-of AAAA-MM-DD`, según `DT-058` a `DT-063`. U1, U2 y U3 no cambian
  su comportamiento; solo se amplían de forma aditiva `runs/__main__.py` y las pruebas de esquema y de
  migraciones de U2/U3. Sin dependencias nuevas. **Autorizar U4 significa que su implementación puede
  comenzar; U4 no está implementada y no existe código funcional de U4.** El siguiente paso es la
  implementación. Criterios de cierre: `docs/06` §16.13.4.
- **Implementación de U4 (2026-10-03).** Implementada y validada el mismo día, sin cambiar ninguna
  decisión: `backend/app/runs/recommendation.py`, `recommendation_inputs.py` y `recommendation_config.py`,
  migración `0003` y subcomando `recommend`. Ejecución real con `ds-6c8ad65b4999` y corte `2025-12-31`:
  `COMPLETED`, 100 evaluaciones (50 `RECOMMEND`, 40 `NO_NEED`, 10 `NOT_CALCULABLE`, los diez esperados);
  repetición `ALREADY_COMPUTED`; *rollback* verificado. 295 pruebas por defecto y 113 de integración en
  verde, en local y en Docker. Los diez criterios de `docs/06` §16.13.4 se cumplen. Detalle: `docs/06`
  §16.13.5.
- **Autorización de U5 (2026-10-03).** U5 = `backend/app/api/` (aplicación, `TokenValidator`, roles,
  errores, `correlation_id`, paginación, `provenance`, esquemas y routers de los trece endpoints de
  `docs/07` §7.2) + `backend/app/db/read/` (consultas de solo lectura, ampliación aditiva de `app/db`) +
  `.env.example` + grupos opcionales `api` y `test` de `backend/pyproject.toml`, según `DT-064` a
  `DT-067` y `docs/07` §7.4. U1 a U4 no cambian. No queda ninguna decisión abierta necesaria para
  implementar U5; `DT-P16`, `DT-P11`, `DT-P13`, `DT-P23` y `BR-X03` siguen abiertas y no la bloquean.
  **Autorizar U5 significa que su implementación puede comenzar; U5 no está implementada.** Criterios de
  cierre: `docs/07` §7.5.
- **Implementación de U5 (2026-10-03).** Implementada y validada el mismo día, sin cambiar ninguna
  decisión: `backend/app/api/`, `backend/app/db/read/`, `.env.example` y los grupos `api` y `test`. U1 a U4
  no cambian. 295 pruebas por defecto, 56 de la API, 142 de integración y 582 del generador en verde, en
  local y en Docker. Los veinte criterios de `docs/07` §7.5 se cumplen.
- **Autorización de U6 (2026-10-04).** U6 = `backend/app/genai/` (`ExplanationContext`, `Fact`, `TextGenerator`
  con la plantilla determinista `template/1.0.0`, presentación de cifras, verificación y degradación
  RS-010), solo con la biblioteca estándar, + el endpoint 14
  `GET /api/v1/recommendations/{recommendation_id}/explanation` en `backend/app/api/` + una lectura aditiva
  de `unit_of_measure` en `backend/app/db/read/`, según `DT-068` y `DT-069` (`ACEPTADA`) y `docs/09` §14.5.
  U1 a U4 no cambian; de U5 solo se amplían, de forma aditiva, la superficie de `api` y sus pruebas
  (13 → 14 endpoints); ninguna respuesta existente cambia. Sin dependencias nuevas. Siguen abiertas, sin
  bloquear U6: `DT-P16`, `DT-P11`, `DT-P13`, `DT-P23` y `BR-X03`. **Autorizar U6 significa que su
  implementación puede comenzar; U6 no está implementada.** Criterios de cierre: `docs/09` §14.6.
- **Implementación de U6 (2026-10-04).** Implementada y validada el mismo día, sin cambiar ninguna decisión:
  `backend/app/genai/`, el endpoint 14 y la lectura aditiva de `unit_of_measure`. U1 a U4 no cambian; de U5
  solo se ampliaron `app.py`, `db/read/recommendations.py`, `schemas.py` y, en sus pruebas, la lista de
  endpoints y el test de OpenAPI (13 → 14). Las 100 evaluaciones reales se explican sin ninguna `DEGRADED`.
  353 pruebas en la suite por defecto (295 + 58 de `tests/genai`), 56 de la API sin base, 151 de integración (142 + 9 de `test_api_explanation.py`), 146 de U1 y 582 del generador en verde, en local y en Docker. Los doce criterios de `docs/09` §14.6 se cumplen.
- **Estado:** `ACEPTADA` en cuanto a U1 (autorizada el 2026-09-30), a U2 (autorizada el 2026-10-01), a U3 (autorizada el 2026-10-02; implementada y validada el mismo día), a U4 (autorizada el 2026-10-03; implementada y validada el mismo día) y a U5 (autorizada el 2026-10-03; implementada y validada el mismo día) y a U6 (autorizada el 2026-10-04; implementada y validada el mismo día).

## DT-048 — Cobertura del forecast y significado de `FORECAST_TOO_SHORT`

- **Decisión:** Con `q, r = divmod(H, 7)`, el motor necesita `K(H) = q + (1 si r > 0) = ⌈H/7⌉` semanas
  de forecast. Forecast ausente → `NOT_CALCULABLE` con `FORECAST_MISSING`; forecast con `m < K(H)`
  semanas, incluido `m = 0` → `NOT_CALCULABLE` con `FORECAST_TOO_SHORT`; con `m ≥ K(H)`, `DDH` por
  `V1-04` con `F_1 … F_K(H)`, y las semanas restantes no influyen. Con `r = 0`, `F_{q+1}` no se exige.
  No se trunca `H`, no se extrapola y no se rellena con ceros. `forecast.start_date = as_of_date + 1`
  es obligatorio; una semana parcial o mal alineada es `InvalidInputError` (`DT-052`).
- **Contexto:** `docs/06` §16.5 nombraba `FORECAST_TOO_SHORT` («no cubre `H`») sin definir «cubrir».
- **Alternativas:** (a) Exigir `K(H)` semanas. (b) Exigir siempre `q + 1`. (c) Calcular con la cobertura
  disponible (truncar o extrapolar).
- **Razón:** (a) es la cobertura literal de los periodos de §16.2 y da el mismo valor que `V1-04`, cuyo
  término `(r/7)·F_{q+1}` vale 0 con `r = 0`. (b) rechazaría forecasts que cubren `H`. (c) inventaría
  demanda (`BR-009`) y cambiaría `V1-03` o `V1-04`.
- **Consecuencias:** `K(97) = 14` coincide con el horizonte derivado de `docs/05` §19.2. El *fallback* al
  baseline sigue siendo del llamador. `FORECAST_MISSING` y `FORECAST_TOO_SHORT` son excluyentes, y la
  segunda solo se evalúa si `H` es calculable.
- **Pruebas mínimas:** `m = K − 1`, `m = K`, `m > K` (el resto no influye); `r = 0` con `m = q`; `m = 0`;
  forecast ausente; `start_date` desplazado → error; valor negativo → error; sin proveedor, la razón no
  se emite.
- **Estado:** `ACEPTADA` (2026-10-01, decisión del responsable). Ninguna fórmula V1 cambia. Detalle:
  `docs/06` §16.11.1.

## DT-049 — Vigencia del producto y horizonte que cruza `valid_to`

- **Decisión:** `vigente(as_of) ⇔ valid_from ≤ as_of_date ∧ (valid_to es nulo ∨ as_of_date ≤
  valid_to)`. `is_active = false` → `PRODUCT_INACTIVE`; no vigente → `PRODUCT_OUT_OF_VALIDITY`: dos
  razones independientes, sin prioridad y acumulables. Si el producto está vigente en `as_of_date` y
  `as_of_date ≤ valid_to < as_of_date + H`, el resultado es `NOT_CALCULABLE` con `PRODUCT_OUT_OF_VALIDITY`
  (cierre de `DT-P22`, abajo), **sin** recortar `H` (`H = L + R`, `V1-03`), sin modificar `L` ni `DDH`,
  sin extrapolar, sin recomendación parcial y **sin crear una razón nueva**. `valid_to < valid_from` es `InvalidInputError`.
- **Contexto:** Solo `as_of_date > valid_to` se derivaba de lo documentado. Faltaban `as_of < valid_from`,
  los extremos, la relación con `is_active` y el horizonte que cruza `valid_to`.
- **Alternativas para el cruce:** (a) Sin efecto. (b) Una marca nueva. (c) `NOT_CALCULABLE`. (d) Recortar
  `H`.
- **Razón:** Elegida (c) por el responsable el 2026-10-01. Después de `valid_to` no hay demanda ni
  consumo (`docs/04` §3.2, restricción 3; especificación §34), y un horizonte que la cruza sumaría
  demanda que el modelo de datos excluye. (a) la habría contado; (b) ampliaba el contrato; (d) cambia
  `V1-03` y `V1-04`. La independencia de las dos razones sale de `DT-027` («Relación con `is_active`:
  deliberadamente no se define») y de `BR-P10`, que sigue propuesta.
- **Consecuencias:** El cruce solo es evaluable si `H` es calculable. Sin efecto sobre el dataset 0.4.0:
  los productos activos tienen `valid_to` nulo y los inactivos ya están fuera de vigencia en
  2025-12-31. *(Al registrarse, el contenido de `reasons` en el caso del cruce quedó abierto como
  `DT-P22`: la lista de §16.5 es cerrada, esta decisión excluía una razón nueva y ninguna existente
  describía el caso. Se cerró el mismo día; ver el punto siguiente.)*
- **Cierre de `DT-P22` (2026-10-01, decisión del responsable, opción (a)).**
  - *Problema que resolvía:* qué razón acompaña al `NOT_CALCULABLE` cuando el producto está vigente en
    `as_of_date` pero su vigencia termina dentro del horizonte.
  - *Decisión:* se reutiliza `PRODUCT_OUT_OF_VALIDITY` y se amplía formalmente su significado:
    **el producto no es válido durante todo el periodo requerido por la evaluación U1**, de
    `as_of_date` a `as_of_date + H`.
  - *Caso A:* `as_of_date < valid_from` o (`valid_to` no nulo ∧ `as_of_date > valid_to`) →
    `NOT_CALCULABLE` con `PRODUCT_OUT_OF_VALIDITY`.
  - *Caso B (cruce de `valid_to`):* `valid_to` no nulo ∧ `as_of_date ≤ valid_to` ∧ `valid_to <
    as_of_date + H` → `NOT_CALCULABLE` con `PRODUCT_OUT_OF_VALIDITY`. Solo es evaluable si `H` es
    calculable; el caso A se evalúa siempre.
  - *Sin razón nueva:* la causa es exclusivamente `PRODUCT_OUT_OF_VALIDITY`; no se crea otra ni se
    reutiliza otra distinta. Si se cumplen los dos casos, la razón aparece una sola vez.
  - *Sin adaptación del horizonte:* `H` no se recorta, no se modifica y no se recalcula; tampoco se
    recorta el forecast, se recalcula `DDH` con un horizonte menor, se extrapola ni se rellena el
    periodo faltante, y el caso no pasa a ser calculable.
  - *Ejemplo normativo:* `valid_to = 2025-03-31`, `as_of_date = 2025-03-20`, `H = 37` →
    `as_of_date + H = 2025-04-26 > valid_to` → `NOT_CALCULABLE`, `reasons = (PRODUCT_OUT_OF_VALIDITY,)`;
    no se usa un horizonte reducido de 11 días.
  - *Alternativas descartadas:* (b) `reasons` vacío, que dejaría un `NOT_CALCULABLE` sin explicación;
    (c) una razón nueva, que esta decisión excluía.
- **Pruebas mínimas:** los extremos `valid_from − 1`, `valid_from`, `valid_to − H`, `valid_to − H + 1`,
  `valid_to`, `valid_to + 1`; `valid_to` nulo; las cuatro combinaciones de `is_active` y vigencia;
  `valid_to < valid_from` → error; el ejemplo normativo de `DT-P22` → `reasons =
  (PRODUCT_OUT_OF_VALIDITY,)`; los casos A y B simultáneos → la razón una sola vez; caso B con `H` no
  calculable → no se evalúa.
- **Estado:** `ACEPTADA` (2026-10-01, decisión del responsable), completa desde el cierre de `DT-P22` el
  mismo día. Detalle: `docs/06` §16.11.2.

## DT-050 — Orden total de las observaciones de lead time

- **Decisión:** Las observaciones del proveedor elegido con `completed_on ≤ as_of_date` se ordenan por
  `completed_on` descendente y, si empatan, por `issued_on` ascendente (antes, el lead time más largo);
  la ventana de `V1-09.1` son las `N` primeras. Un empate total no requiere un tercer criterio, porque
  produce el mismo lead time; el resultado no depende del orden de la entrada. `completed_on <
  issued_on` es `InvalidInputError`.
- **Contexto:** `V1-09.1` toma «las 12 más recientes por fecha de finalización»; un empate en la frontera
  podía cambiar la mediana y, con ella, `L`, `H`, `σ_H`, `SS`, `raw_need` y `Q_final`.
- **Alternativas:** (a) `issued_on` ascendente. (b) `issued_on` descendente. (c) Incluir todos los
  empatados. (d) Un identificador de línea.
- **Razón:** Elegida (a) por el responsable. Es coherente con `DT-031` §`V1-09`, pregunta 3 («un día de
  más en el lead time es el error seguro») y pregunta 1 («el comportamiento prudente»). (c) rompe «las
  12»; (d) no tiene significado y no está en la entrada (§16.3).
- **Consecuencias:** Precisa `V1-09.1` sin modificarla; el dataset 0.4.0 no tiene empates en la frontera.
- **Aclaración A-1 (2026-10-01) — techo de `LT_MAX`.** `L = min(L_source, LT_MAX)` sea cual sea la
  procedencia de `L_source`, observada o `AGREED_FALLBACK`; `LEAD_TIME_AGREED_FALLBACK` y
  `LEAD_TIME_CAPPED` pueden coexistir, y el valor sin topar es `L_source`. Es la lectura literal del
  pseudocódigo de `V1-09`, que aplica el techo después de las dos ramas, y la que presupone `docs/05`
  §19.2 (14 semanas = horizonte más largo del motor). `DT-031` no se modifica. Ejemplo: acordado 120 sin
  observaciones suficientes → `L = 90`, ambas marcas.
- **Pruebas mínimas:** empate en la posición 12 (10 × 5 y 20 × 6, más A de 21 días y B de 10 días → `L =
  20`); la entrada permutada da el mismo `L`; empate total; otro proveedor o `completed_on > as_of` →
  ignorada; lead time negativo → error; acordado 90 (sin tope), 91 (tope) y fallback con tope.
- **Estado:** `ACEPTADA` (2026-10-01, decisión del responsable), con la aclaración A-1. Detalle:
  `docs/06` §16.11.3.

## DT-051 — Contrato técnico de U1: tipos, aritmética, salida, orden y versión

- **Decisión:**
  1. **Tipos públicos** (Python ≥ 3.11, solo biblioteca estándar): `datetime.date` (se rechaza
     `datetime.datetime`); identificadores `int` opacos; `bool` estricto; cantidades de entrada `int` ·
     `Decimal` finito · `Fraction` (se rechazan `float`, NaN, infinito, `bool` y `str`); días y enteros
     de política `int`; colecciones `tuple`; enumeraciones `StrEnum`; salida en dataclasses congeladas.
     Bloques de entrada: `as_of_date`, `product`, `supplier_relations`, `inventory`, `open_lines`,
     `lead_time_observations`, `consumption`, `forecast`, `policy`.
  2. **Aritmética:** `Fraction` es la representación canónica del cálculo exacto; toda entrada se
     convierte a `Fraction` sin pérdida. `Decimal` solo representa los valores que `docs/06` §16.6 punto
     7 manda informar con 28 cifras significativas, se obtiene del valor exacto, no participa en ninguna
     decisión y nunca vuelve a entrar en un cálculo. Sin `float`.
  3. **`S = DDH + SS`** se añade a la lista de §16.6 punto 7: exacto si es racional y, si no, `Decimal`
     de 28 cifras con `ROUND_HALF_EVEN`, obtenido de su valor exacto. Cierra un vacío; ninguna fórmula
     B3 cambia.
  4. **`missing_policy_parameters`:** `tuple[PolicyParameter, ...]` con `R`, `z`, `N`, `N_MIN`,
     `LT_MAX`, en ese orden; vacío si y solo si `MISSING_POLICY_PARAMETER` no está en `reasons`; con
     varios faltantes, una sola razón y todos en la tupla; `policy_set` no forma parte. No es un código
     de error.
  5. **Orden canónico** de `reasons` y de `flags`: el de las listas de §16.5, con las condiciones de las
     marcas de §16.11.4.
  6. **`NOT_CALCULABLE`:** se conservan los términos y las marcas calculados válidamente; lo demás vale
     `None`.
  7. **`engine_version = "0.1.0"`**, constante, en formato `MAJOR.MINOR.PATCH`, sin fechas, *hash* ni datos
     de ejecución. PATCH: ninguna salida observable cambia; MINOR: alguna entrada válida produce una
     salida distinta sin romper el contrato; MAJOR: cambio incompatible del contrato o de los tipos.
- **Contexto:** `docs/06` §16.3 y §16.5 fijaban campos, pero no tipos, versión ni orden. `BR-009`,
  `docs/06` §14 y `docs/13` §3.1 exigen indicar qué parámetro falta, y la salida no tenía dónde. §16.6
  punto 7 omitía `S`, que es un término del desglose y se persiste como `reorder_point`.
- **Alternativas:** `Fraction` solo interna (la salida necesitaría pares o cadenas para valores como
  `680/7`); desglose vacío con `NOT_CALCULABLE`; `engine_version` `1.0.0`; orden alfabético.
- **Razón:** Decisión del responsable (2026-10-01). El orden de §16.5 ya es semántico y evita reescribir
  las listas; el criterio de versión es el de `generator_version` (`DT-033`); `0.x` refleja
  `V1_PROVISIONAL`.
- **Consecuencias:** El contrato público queda cerrado (`DT-P22` cerrada el 2026-10-01). La serialización byte a byte la
  hace quien persiste (U4). Las decisiones de persistencia de racionales no decimales siguen siendo de
  U4.
- **Aclaración A-2 (2026-10-01) — `abc_class`.** La entrada no contiene `abc_class` ni
  `rotation_class`, y no se añaden campos opcionales para ignorarlos. `V1-11` se cumple de forma
  estructural, y el caso 11 de `DT-031` se verifica comprobando que ningún tipo de entrada tiene esos
  atributos y que el paquete no los nombra. `DT-031` no se modifica.
- **Pruebas mínimas:** rechazo de cada tipo prohibido; `Decimal("2.5")` equivale a `Fraction(5, 2)`;
  con `A` no cuadrado, `σ_H`, `SS`, `S`, `raw_need` y `Q_moq` son `Decimal` y `Q_final` es exacto; con `A`
  cuadrado, todo es exacto; orden con tres o más razones; varios parámetros faltantes; coexistencia de
  marcas; salida parcial con `NOT_CALCULABLE`; entradas permutadas → resultados iguales;
  `engine_version` igual a la constante; las dos comprobaciones de A-2.
- **Estado:** `ACEPTADA` (2026-10-01, decisión del responsable). Detalle: `docs/06` §16.11.4 y §16.6 punto 7.

## DT-052 — Entrada inválida: `InvalidInputError` y orden de validación

- **Decisión:** `InvalidInputError(ValueError)` es la única excepción del contrato, con `field: str`
  (ruta del contrato, con índices de posición y nunca identificadores) y un mensaje en inglés que
  describe la regla incumplida, sin el valor recibido; `str(error)` = `"<field>: <mensaje>"`. Sin código
  de error. Todo se valida antes de calcular, y solo se lanza el **primer** error: fase 1 (tipo, finitud
  y signo, en el orden de bloques de `DT-051`, de campos de §16.3 y de índices) y fase 2, en este orden:
  (a) `valid_to ≥ valid_from`; (b) como máximo una relación activa y preferente; (c) `(purchase_order_id,
  item_id)` únicos; (d) `Σ quantity_pending = total_in_transit`; (e) `completed_on ≥ issued_on`; (f)
  coherencia del consumo (`start_date ≥ valid_from` y, si no está vacío, último día =
  `min(as_of_date, valid_to)`); (g) `forecast.start_date = as_of_date + 1`; (h) `policy_set =
  V1_PROVISIONAL` y valores iguales a los de `DT-031`. **`on_hand < 0` no es entrada inválida**:
  `NOT_CALCULABLE` con `NEGATIVE_ON_HAND`. El resto de cantidades negativas sí lo son.
- **Contexto:** `docs/13` §3.1 exige un «error explícito» sin forma, y §16.3 prohíbe códigos nuevos. Había
  que separar la entrada inválida de `NOT_CALCULABLE`, y definir los huecos de consumo y la relación con
  `total_in_transit`.
- **Alternativas:** Acumular todos los errores; tratar un día de consumo ausente como 0; confiar en
  `total_in_transit` sin comprobarlo; tratar `on_hand < 0` como error.
- **Razón:** Decisión del responsable (2026-10-01). Un solo error en orden canónico es determinista. El
  consumo es denso (`DT-038` §4: «una fila con `quantity = 0` no es una fila ausente»). `total_in_transit`
  es por definición `Σ` del pendiente de las mismas líneas (`docs/06` §4.1). `order_multiple ≥ 1` es la
  precondición de §16.6 punto 5. Como máximo un preferente activo es el contrato de `DT-024`. Los
  valores V1 solo cambian con un ADR (`DT-031`), y B3 fija `z = 33/20`. `on_hand < 0` es la regla
  específica de `V1-13`, `docs/06` §16.5 y el caso 13 de `DT-031`.
- **Consecuencias:** `docs/13` §3.1 recoge la excepción de `on_hand`. La conciliación de
  `Inventory.quantity_in_transit` con la base sigue siendo de U2; U1 solo comprueba la coherencia
  interna. Los mensajes no contienen valores ni identificadores (`CLAUDE.md` §9.4).
- **Pruebas mínimas:** una por cada regla de las fases 1 y 2; con dos errores, se lanza el primero; los
  mensajes no contienen el valor; `on_hand` negativo devuelve un resultado y no lanza; serie corta →
  `INSUFFICIENT_HISTORY`.
- **Estado:** `ACEPTADA` (2026-10-01, decisión del responsable). Detalle: `docs/06` §16.11.5.

## DT-053 — Frontera de la salida parcial con `NOT_CALCULABLE` (P-1)

- **Decisión:** Con `NOT_CALCULABLE`, U1 conserva las magnitudes **descriptivas** calculadas
  válidamente antes de la frontera que impide la decisión (`L`, `H`, tránsito, posiciones, `DDLT`,
  `DDH`, `σ_H`, `SS`, `S`, componentes de B3), siempre que sus precondiciones se cumplan y el cálculo no
  reinterprete, recorte ni modifique el horizonte. Las magnitudes de **decisión** (`raw_need`, `Q_moq`,
  `Q_final`) solo existen con `reasons == ()`; `MOQ_APPLIED` y `ORDER_MULTIPLE_ROUNDING` solo con
  `RECOMMEND`. Por razón:
  - `PRODUCT_INACTIVE` excluye el producto del cálculo operativo;
  - el caso A de `PRODUCT_OUT_OF_VALIDITY` registra la razón sin `H` y no fabrica ninguna evaluación
    parcial;
  - el caso B conserva `H = L + R` y las magnitudes descriptivas sobre el horizonte completo;
  - `NEGATIVE_ON_HAND` conserva las magnitudes independientes de la decisión, pero no las que dependen
    de `on_hand` (posiciones de inventario y `P`).
- **Contexto:** El audit de pre-codificación de U1 (2026-10-01) encontró que «se conserva lo que pudo
  calcularse» (`DT-051`) podía leerse como autorización para informar cantidades de pedido con
  `NOT_CALCULABLE`, en contra de §16.11.2 («no se calcula una recomendación parcial») y de `BR-P10`.
- **Alternativas:** (a) Informar todo lo aritméticamente calculable. (b) Desglose vacío. (c) Frontera
  entre magnitudes descriptivas y de decisión.
- **Razón:** Elegida (c) por el responsable. (a) produciría una recomendación parcial; (b) perdería la
  trazabilidad que `DT-051` quiso conservar.
- **Consecuencias:** Con exclusión (`PRODUCT_INACTIVE` o caso A) no se produce `H`, de modo que las
  razones que lo necesitan no son evaluables (`docs/06` §16.11.4); las demás se evalúan siempre. Es una
  decisión de **alcance e interpretación** del contrato: ninguna fórmula V1 ni regla B3 cambia.
- **Pruebas mínimas:** con cualquier `NOT_CALCULABLE`, `raw_need`, `Q_moq` y `Q_final` son `None`;
  `PRODUCT_INACTIVE` sin magnitudes; `NEGATIVE_ON_HAND` con magnitudes descriptivas; el caso A sin `H`;
  el caso B con `H` completo, `DDH` sin modificar y sin términos de recomendación; las marcas de decisión
  solo con `RECOMMEND`.
- **Estado:** `ACEPTADA` (2026-10-01, decisión del responsable). Detalle: `docs/06` §16.11.6.

## DT-054 — Sin monotonía global de `S` frente a `L` en V1 (P-2)

- **Decisión:** Se retira para V1 la propiedad «`L₂ ≥ L₁ ⇒ S₂ ≥ S₁`». No se implementa ni se prueba como
  invariante. Se prueban `H = L + R` y, con `R = 7`, `H ≥ 7`, además de las dependencias que se siguen
  directamente de las fórmulas.
- **Contexto:** `docs/06` §16.8 y `docs/13` §3.1 pedían monotonía del punto de reorden frente al lead
  time. En V1, `σ_H` se recalcula sobre ventanas de `H = L + R` días y no es monótona en `H`.
  Contraejemplo auditado: consumo alternante `0, 2, …` y forecast `(10, 0, …)`; con `L: 0 → 1`,
  `H: 7 → 8`, `σ_H: 1 → 0` y `S: 11,65 → 10`.
- **Alternativas:** (a) Acotar la propiedad a `σ_H` fijo. (b) Limitarla a `DDH` frente a `L`. (c)
  Retirarla para V1.
- **Razón:** Elegida (c) por el responsable: la propiedad no se sigue de las fórmulas aceptadas, y
  forzarla exigiría cambiarlas.
- **Consecuencias:** `V1-03`, `V1-04`, `V1-05`, B3, `DDH`, `σ_H`, `SS` y `S` no cambian. El contraejemplo
  puede conservarse como prueba de regresión que documenta que la monotonía global no es un
  invariante de V1. Es una decisión de **alcance** del contrato, no un cambio de fórmula.
- **Estado:** `ACEPTADA` (2026-10-01, decisión del responsable). Detalle: `docs/06` §16.11.7.

## DT-055 — Entorno técnico de U2: PostgreSQL, `psycopg`, migraciones SQL y Docker

- **Decisión:**
  1. **PostgreSQL 16** es la base de desarrollo e integración.
  2. **`psycopg` 3** (`psycopg[binary]==3.3.6`) es el único controlador, declarado como dependencia
     **opcional** del grupo `db` de `backend/pyproject.toml`. `dependencies` sigue vacío: U1 no gana
     ninguna dependencia y sigue siendo una biblioteca pura.
  3. **Migraciones SQL versionadas y explícitas** en `backend/db/migrations/NNNN_nombre.sql`, aplicadas
     en orden por un ejecutor mínimo propio (`app.db.migrations`). Cada migración se aplica en su propia
     transacción y queda registrada en `schema_migrations` con su `sha256`; una migración aplicada cuyo
     archivo cambia es un error. Sin ORM y sin Alembic (`DT-043`).
  4. **Entorno local con Docker:** `infra/docker-compose.yml` levanta `postgres:16-alpine` solo en
     `127.0.0.1`, con autenticación `trust` y **sin contraseña**: no se versiona ninguna credencial
     (`CLAUDE.md` §9). La conexión se lee de la variable `DATABASE_URL`.
  5. **Pruebas en dos suites:** `backend/tests/ingestion` no necesita base y forma parte de la suite por
     defecto; `backend/tests/db` es la suite de integración contra un PostgreSQL real, se ejecuta de
     forma explícita y **falla** —no se salta— si falta `U2_TEST_ADMIN_DSN` (`docs/13` §14).
- **Contexto:** `DT-043` prevé para U2 «un controlador de PostgreSQL y un PostgreSQL local en
  contenedor, y migraciones como SQL versionado con un ejecutor mínimo propio», y deja cada
  dependencia a la autorización de su unidad (`docs/04` §9.8).
- **Alternativas:** controlador `psycopg2` o `asyncpg`; Alembic o un ORM; PostgreSQL instalado en el
  sistema; dependencia obligatoria en `dependencies`.
- **Razón:** `psycopg` 3 es el controlador mantenido de referencia y su `COPY` carga las tablas grandes
  sin una capa extra; la API de U1 no lo necesita, de ahí el grupo opcional. Las migraciones SQL a mano
  bastan para un esquema de trece tablas y no añaden herramientas. Docker hace reproducible la versión
  de PostgreSQL.
- **Consecuencias:** Instalación de U2: `pip install -e "backend[db]"` (o el controlador fijado).
  `docs/03` §16.6 situaba las migraciones dentro de `app/db/`; pasan a `backend/db/migrations/`, fuera
  del paquete Python, por instrucción del responsable. Detalle de uso: `docs/04` §9.9.
- **Estado:** `ACEPTADA` (2026-10-01, decisión del responsable al abrir U2).

## DT-056 — Baselines V1 de U3: definición, intervalo, histórico mínimo y respaldo

*Cierra `DT-P17`. Notación: `A` = `as_of_date`; `d(t)` = consumo diario; `Y_1 … Y_n` = semanas completas
del histórico en orden cronológico, con `Y_n` la que termina en `A`; `F_h`, `L_h`, `U_h` = punto,
límite inferior y límite superior de la semana `h` del horizonte, `h = 1 … 14`. Tabla de decisiones
D-01 a D-22 y criterios de cierre: `docs/05` §19.8 y §19.9.*

- **Decisión:**
  1. **Histórico.** `consumption.quantity` diario y **contiguo**, solo con fecha `≤ A`, desde el primer
     día con fila `S`. Se agrega en semanas completas ancladas en `A`: `n = ⌊(A − S + 1) / 7⌋` y
     `Y_j = Σ d(t)` para `t ∈ [A − 7(n − j) − 6, A − 7(n − j)]`, `j = 1 … n`. Los `(A − S + 1) mod 7`
     días más antiguos se descartan. Nada posterior a `A` interviene (RML-004).
  2. **Horizonte.** 14 semanas; la semana `h` es `[A + 1 + 7(h − 1), A + 1 + 7h)` (`DT-046`, `DT-048`).
  3. **Baselines.**
     - Naïve: `F_h = Y_n` para todo `h`.
     - Naïve estacional, con `L = 52` semanas: `F_h = Y_{n+h−52}`; usa `Y_{n−51} … Y_{n−38}`.
     - Media móvil, con `k = 13`: `F_h = (Y_{n−12} + … + Y_n) / 13` para todo `h`. No se reduce la ventana.
  4. **Intervalo: cuantiles empíricos del error histórico a cada horizonte.** Desde cada origen `t` del
     histórico (se conocen `Y_1 … Y_t`) el mismo método predice la semana `t + h`: naïve `Y_t`;
     estacional `Y_{t+h−52}`, con `t ≥ 53 − h`; media móvil `media(Y_{t−12} … Y_t)`, con `t ≥ 13`. El
     error es `e = Y_{t+h} − ŷ_{t,h}`, y `E_h` reúne los de todos los orígenes válidos con `t + h ≤ n`.
     Con `E_h` ordenado, `e_(1) ≤ … ≤ e_(m)`, la regla **nearest-rank** sin interpolación da
     `q_lo = e_(⌈m/10⌉)` y `q_hi = e_(⌈9m/10⌉)`, y
     `L_h = max(0, F_h + min(q_lo, 0))`, `U_h = F_h + max(q_hi, 0)`. Se cumple siempre
     `0 ≤ L_h ≤ F_h ≤ U_h`: el `min` y el `max` amplían el intervalo hasta incluir el punto cuando todos
     los errores tienen el mismo signo.
  5. **`confidence_level = 0.80`.** `confidence_level = 0.80` es el nivel nominal del intervalo. No
     constituye una garantía ni una medición empírica de cobertura. La calibración y validación de
     cobertura corresponden a la Fase 5. Tampoco es un nivel de servicio. No se reutiliza
     `z_v1 = 1,65`: es un parámetro del motor para el stock de seguridad de U1 (`DT-031` §`V1-05`), y el
     método de este intervalo no usa ningún `z`.
  6. **Mínimo de errores.** Con la regla de cuantiles nearest-rank 10/90 adoptada para el nivel nominal
     0.80, se exige un mínimo operacional de 11 errores por horizonte (`m ≥ 11` para cada `h = 1 … 14`)
     para que exista al menos una observación en cada cola. Con `m = 11`, `q_lo = e_(2)` y
     `q_hi = e_(10)`: queda una observación extrema fuera del intervalo en cada cola. 11 es un mínimo
     operacional de esta regla concreta, no una estimación universal; la cobertura real se evaluará en
     la Fase 5.
  7. **Histórico mínimo**, para producir punto e intervalo en las 14 semanas: naïve, 25 semanas completas
     (`m_h = n − h`); media móvil, 37 (`m_h = n − h − 12`); naïve estacional, 63 (`m_h = n − 52`).
  8. **Referencia provisional y respaldo.** La media móvil de 13 semanas se registra como referencia
     provisional de V1. Esta elección es operativa y reversible y no implica que sea el baseline de mejor
     desempeño. La selección definitiva por desempeño corresponde a la Fase 5. Cadena de la serie
     **primaria** de cada producto: media móvil → naïve → sin forecast. Naïve estacional no forma parte
     de la cadena. `confidence_flag`: `STANDARD` en general; `INSUFFICIENT_HISTORY` en la serie primaria
     que procede del respaldo naïve. Un producto sin ningún baseline calculable (menos de 25 semanas) no
     recibe forecast; el motivo queda en la ejecución (`DT-057`) y la estimación para ese caso es
     `DT-P23`.
  9. **Desabasto: tratamiento provisional de V1.** El consumo observado puede subrepresentar la demanda
     potencial durante episodios de desabasto. En V1 se utiliza como proxy observable del
     consumo/demanda satisfecha, sin corrección ni imputación: `consumption.quantity` bruto, sin excluir
     días. `stockout_treatment = "NONE_RAW_CONSUMPTION_V1"`. `is_stockout_affected` viaja en la petición
     (`docs/05` §19.2), pero V1 no la usa para modificar el cálculo. Cambiar este tratamiento exige una
     versión nueva de cada baseline. La solución metodológica definitiva sigue siendo `DT-011`, que **no**
     se cierra. `demand` nunca se usa (`DT-034`).
  10. **Catálogo.** U3 pronostica productos activos y vigentes en `as_of_date`
      (`is_active = true` y `valid_from ≤ A ≤ valid_to`, o `valid_to` nulo). U1 realiza posteriormente su
      propia validación de vigencia sobre el horizonte concreto de la recomendación (`DT-049`,
      `DT-P22`). Los inactivos o fuera de vigencia se excluyen con el motivo
      `INACTIVE_OR_OUT_OF_VALIDITY`; un producto con huecos en el histórico, o sin fila el día `A`, se
      excluye con el motivo `INVALID_HISTORY` y no se imputa. En el dataset 0.4.0, los 5 productos
      descontinuados no tienen consumo después del 2025-04-02 y no se usan para generar forecasts
      posteriores a esa fecha.
  11. **Precisión.** Cálculo en `Fraction` exacta. `F_h`, `L_h` y `U_h` se cuantizan una sola vez, a la
      salida del proveedor, al múltiplo de `10⁻⁶` más cercano con `ROUND_HALF_EVEN` y aritmética entera,
      y se devuelven como `Decimal`. Nunca `float`. Sin redondeo a enteros ni reglas por unidad
      (`EACH`, `BOX`, `KG`): no hay reglas de fraccionamiento documentadas. La cuantización es monótona y
      conserva `0 ≤ L_h ≤ F_h ≤ U_h`.
  12. **Versiones.** Cada baseline es una versión `1.0.0` con todos estos valores en `hyperparameters`
      (`DT-057`); cambiar cualquiera exige una versión nueva.
- **Contexto:** `DT-P17` bloqueaba U3. RF-010 exige intervalo, versión y fecha de generación, y respaldo
  señalado; RML-007 exige que el método y la confianza consten; US-050 pide en la Fase 4 naïve, naïve
  estacional y media móvil, con la referencia registrada, y aplaza a la Fase 5 la elección por
  desempeño (`docs/05` §6).
- **Alternativas:** intervalo normal con `σ` a un paso escalado por `√h`, o con un `σ` por horizonte;
  nivel del 95 %; reutilizar `z_v1`; longitud estacional de 365 días; `k` = 4 u 8; excluir o imputar
  los días con desabasto; redondear a enteros; persistir racionales exactos.
- **Razón:** El intervalo empírico es exacto, no supone ninguna distribución (`DT-010`, alternativas
  (c) y (d)) y funciona igual con ceros e intermitencia; el `√h` es la relación que `DT-010` advierte
  que no es general. 52 semanas es un número entero de periodos del forecast: la semana `h` menos 52
  cae sobre una semana histórica completa, sin prorratear; 365 días exigiría una segunda regla de
  conversión. `k = 13` es un trimestre (`52/4`) y su ventana es comparable al horizonte. La referencia
  provisional es una elección operativa: la media móvil exige menos histórico que naïve estacional (37
  frente a 63 semanas) y su definición no depende de una única semana; no hay todavía evaluación de
  desempeño que permita compararlos. El consumo bruto es el que usa U1 para `σ_H` (`DT-P14`); excluir
  días rompería las semanas completas y la imputación es el método que `DT-011` aplaza. Ningún valor es
  una política de negocio.
- **Consecuencias:** En V1, U1 no consume el intervalo: calcula el stock de seguridad con la
  variabilidad del consumo (`DT-031` §`V1-05`); el uso del intervalo por el motor (RML-006) sigue para
  la Fase 5 (`DT-010`). Los productos con desabasto intenso pueden quedar subestimados, limitación
  declarada hasta `DT-011`. Con el dataset 0.4.0 en `A = 2025-12-31`, los 95 productos elegibles tienen
  156 semanas: no hay respaldos. `DT-011`, `DT-P23`, `DT-021`, `DT-P04` y la elección de la referencia
  por desempeño siguen abiertos.
- **Estado:** `ACEPTADA` (2026-10-02, decisión del responsable al autorizar U3). Detalle: `docs/05`
  §19.8.

- **Enmienda acotada (2026-10-05, `DT-074`):** el punto 11 (precisión, D-12) sigue rigiendo para los baselines, el contrato, la persistencia y la API. Solo `ml/` y un proveedor de modelo pueden usar `float` internamente, con frontera determinista a `Decimal` de 6 decimales `ROUND_HALF_EVEN`.

## DT-057 — Persistencia y ejecución del forecast de U3

- **Decisión:**
  1. **Migración `0002`** con tres tablas, siguiendo `DT-055`:
     - `model_versions`: clave única `(name, version)` y `created_at` técnico. Una fila por baseline
       (`baseline.naive`, `baseline.seasonal_naive`, `baseline.moving_average`; `version = 1.0.0`;
       `algorithm` = `NAIVE`, `SEASONAL_NAIVE`, `MOVING_AVERAGE`; `is_baseline = true`). En los
       baselines, `trained_at`, `training_data_from`, `training_data_to`, `metrics`,
       `baseline_metrics`, `status` y `external_ref` son `NULL`: no hay entrenamiento ni evaluación, y
       el ciclo de vida de `docs/05` §13 es el de «cada modelo entrenado». CHECK
       `is_baseline = (status IS NULL)`. `hyperparameters` (`jsonb`, obligatorio) lleva la definición
       completa de `DT-056`.
     - `calculation_runs`: `run_type` (`FORECAST` · `RECOMMENDATION`), `status` (`COMPLETED` ·
       `FAILED`), `as_of_date`, `data_load_id` (FK, la carga `COMPLETED`), `reference_model_version_id`
       (FK, obligatoria en `FORECAST`; sustituye al `model_version_id` propuesto en `docs/04` §9.6),
       `config_sha256`, `summary` (`jsonb`: recuentos, productos excluidos o sin forecast con su motivo,
       respaldos y versiones ejecutadas), `error` (solo en `FAILED`), `started_at`, `finished_at`.
       Índice único parcial `(run_type, as_of_date, data_load_id, config_sha256) WHERE status =
       'COMPLETED'`. Las columnas propias de U4 se añaden con U4.
     - `forecasts`: `calculation_run_id`, `product_id`, `location_id`, `model_version_id` (FK),
       `as_of_date`, `generated_at`, `period_start`, `period_end` (`= period_start + 7`),
       `granularity`, `predicted_quantity`, `lower_bound`, `upper_bound` (`numeric`, CHECK
       `0 ≤ lower ≤ predicted ≤ upper` y escala `≤ 6`), `confidence_level` (CHECK `0 < c < 1`),
       `method_used`, `confidence_flag` (`STANDARD` · `INSUFFICIENT_HISTORY`), `is_primary`. Clave única
       por ejecución `(calculation_run_id, model_version_id, product_id, location_id, period_start)` y
       único parcial `(calculation_run_id, product_id, location_id, period_start) WHERE is_primary`.
     - *Triggers* que rechazan `UPDATE` y `DELETE` en `forecasts` y en `calculation_runs`.
  2. **Una ejecución por llamada** (C9): un único `calculation_run` persiste, por producto elegible,
     las series de los tres baselines calculables, cada una con su `model_version_id`, y marca con
     `is_primary` la que debe consumir U4 (la referencia o su respaldo, `DT-056`).
  3. **Idempotencia** (C8): con el mismo `as_of_date`, la misma carga y la misma `config_sha256` (huella
     del JSON canónico de modelos, referencia, horizonte, cuantización y política de catálogo) que una
     ejecución `COMPLETED`, el resultado es `ALREADY_COMPUTED`: se devuelve su id y no se escribe nada.
     Otra configuración crea otra ejecución. Las `FAILED` no bloquean.
  4. **Ejecución:** `python -m app.runs forecast --as-of AAAA-MM-DD`, una fecha por llamada, validada
     dentro de `[time_range.start, time_range.end)` de la carga `COMPLETED`; fuera de ese rango se
     rechaza sin escribir. Bloqueo *advisory* propio; todo en una transacción; ante fallo, *rollback* y
     fila `FAILED` en otra transacción. `runs` registra cada `model_versions` en su primer uso; si existe
     con otros `hyperparameters`, es un error que obliga a subir la versión. Primera ejecución real:
     `2025-12-31`. Sin backtesting.
- **Contexto:** `docs/04` §9.6 proponía las columnas de trazabilidad y dejaba dos huecos: la clave única
  conceptual de `docs/04` §3.14 no contempla ejecuciones (C8) y una ejecución con tres baselines no cabe
  en un único `model_version_id` (C9).
- **Alternativas:** una ejecución por baseline; persistir solo la serie primaria; rechazar la repetición
  o duplicar las filas; mantener la clave de §3.14; marcar la referencia en `model_versions.status`.
- **Razón:** Una ejecución es un hecho trazable y la salida es determinista, de modo que repetirla no
  añade información. La clave por ejecución evita choques entre configuraciones que comparten una
  versión. Persistir las tres series cumple US-050 («implementados» y disponibles) y sirve a la API
  (`docs/07` §7). La referencia vive en la ejecución y deja libre la regla de «como máximo un
  `PRODUCTION`» para el modelo de la Fase 5.
- **Consecuencias:** En el modelo físico, la clave única de `docs/04` §3.14 queda sustituida por la
  clave por ejecución. Con el dataset 0.4.0 en `2025-12-31`: 95 productos, 3 990 filas (95 × 3 × 14),
  1 330 primarias, 5 excluidos. U4 decide la correspondencia entre las filas y el `forecast_id` de U1
  y de `recommendations`, y qué ejecución consume *(decidido el 2026-10-03: `DT-060` y `DT-061`)*. `forecasts`, `model_versions` y `calculation_runs`
  no llevan `data_origin` (`docs/04` §5.2).
- **Estado:** `ACEPTADA` (2026-10-02, decisión del responsable al autorizar U3). Detalle: `docs/04`
  §9.10.

## DT-058 — Un forecast por corte de recomendación

- **Decisión:** una ejecución de recomendaciones con corte `t` consume solo el forecast cuyo
  `as_of_date` es exactamente `t`. La secuencia es `python -m app.runs forecast --as-of t` y después
  `python -m app.runs recommend --as-of t`, ambas explícitas: **U4 no lanza el forecast**. En V1, `t`
  debe ser el último día de la carga `COMPLETED` (`upper(time_range) − 1`, el `2025-12-31` para
  `ds-6c8ad65b4999`), porque `inventory` es la instantánea al corte; cualquier otra fecha se rechaza
  sin escribir. La simulación retrospectiva (inventario reconstruido desde los movimientos) queda
  para la Fase 5.
- **Contexto:** `docs/05` §2 pedía «forecast semanal, recálculo diario». `DT-046` ancla las semanas
  en `as_of_date + 1` y U1 exige `forecast.start_date = as_of_date + 1` (`DT-052` (g)). `DT-046` dejaba
  dos salidas abiertas (`DT-P21`).
- **Alternativas:** (a) forecast por corte; (b) forecast vigente desplazado `d` días dentro de U1;
  (c) reanclaje de las semanas en U4.
- **Razón:** (b) reabre U1 (validación (g) y `demand_over_horizon`, `engine_version` MINOR) y, con 14
  semanas (98 días) y `H ≤ 97`, cualquier `d ≥ 2` produce `FORECAST_TOO_SHORT` en los lead times
  largos, lo que obligaría a ampliar el horizonte de U3. (c) crea un segundo punto de conversión de
  granularidad, prohibido por `docs/06` §5.1 y `DT-019`, y separa las cantidades usadas de las
  persistidas en `forecasts`. (a) no cambia U1 ni U3 y conserva la exactitud de `V1-04`.
- **Consecuencias:** «recálculo diario» (`docs/05` §2) se lee como nueva instantánea → ejecución de
  forecast → ejecución de recomendaciones con el mismo corte. El forecast sigue siendo semanal; lo
  que se hace por corte es la ejecución. En V1, con un solo corte posible, **no se generan forecasts
  diarios**. Con 14 semanas y `LT_MAX = 90`, `FORECAST_TOO_SHORT` no puede ocurrir en V1.
- **Estado:** `ACEPTADA` (2026-10-03, decisión del responsable al autorizar U4); implementada y validada el mismo día (`docs/06` §16.13.5). Cierra `DT-P21`.
  Detalle: `docs/06` §16.13.

## DT-059 — Persistencia de las evaluaciones: `recommendations`

- **Decisión:**
  1. **Una fila inmutable por evaluación**, única por `(calculation_run_id, product_id, location_id)`,
     para los tres `outcome`. `RECOMMEND` lleva sus magnitudes (`recommended_quantity > 0`,
     `raw_quantity > 0`, `suggested_order_date = as_of_date`). `NO_NEED` se persiste con
     `raw_quantity = 0` y **no** equivale a la ausencia de fila. `NOT_CALCULABLE` es una evaluación
     válida con `reasons`, las marcas que correspondan y `NULL` en lo que U1 no calculó (`DT-053`). Un
     fallo de la ejecución es `calculation_runs.status = 'FAILED'` y no deja recomendaciones:
     **`NOT_CALCULABLE ≠ FAILED`**.
  2. **Columnas:** `id`, `calculation_run_id`, `product_id`, `location_id`, `as_of_date`, `outcome`,
     `reasons`, `flags`, `missing_policy_parameters` (`text[]` en el orden canónico de U1),
     `forecast_id` (nulo si y solo si `FORECAST_MISSING ∈ reasons`), `suggested_supplier_id`,
     `suggested_order_date`, `recommended_quantity` (`q_final`), `raw_quantity` (`raw_need`),
     `reorder_point` (`S`), `safety_stock`, `lead_time_used_days`, `demand_during_lead_time`,
     `inventory_position_at_calc` (`IP_decisión`), `policy_set` (`CHECK (policy_set =
     'V1_PROVISIONAL')`), `policy_snapshot`, `calculation_inputs`, `engine_version` y `generated_at`
     (`transaction_timestamp()`). `CHECK` por `outcome` y *trigger* de inmutabilidad.
  3. **Sin `status`, `resolved_*`, `urgency` ni entidad de resolución en V1.** El `outcome` es un
     resultado técnico inmutable; la decisión humana es un flujo separado que se modelará cuando exista
     quien la escriba.
  4. **Representación.** En JSON: `int` como decimal; `Fraction` con desarrollo decimal finito como
     decimal exacto; `Fraction` periódica como `"p/q"` (por ejemplo `"270/7"`); `Decimal` aproximado
     de U1 (28 cifras significativas) con su nombre en `approximate_terms` y los componentes B3
     (`n`, `S1`, `S2`, `A`, `B`, `D`, `P`) para reconstruirlo. En `numeric`: exacto cuando es posible y,
     para un racional periódico, 28 cifras significativas `ROUND_HALF_EVEN` calculadas desde el valor
     exacto. Nunca `float`.
  5. **`calculation_inputs`** = desglose completo con los nombres de U1 + bloque `forecast`
     (`forecast_run_id`, `forecast_id`, modelo `{name, version}`, `method_used`, `confidence_flag`,
     `start_date` y las 14 cantidades copiadas) + `input_sha256`.
  6. **`input_sha256`** es el SHA-256 de la representación JSON canónica y normalizada de
     `EvaluationInput` utilizada para persistencia. Las identidades técnicas autogeneradas de U3
     (`forecast_id`, `model_version_id`) se representan por la identidad semántica del modelo (`name`,
     `version`), de modo que la huella verifica las entradas semánticas utilizadas y no depende de IDs
     técnicos generados por la base. Las colecciones van en orden canónico, los identificadores
     conservados del dataset sí entran y no entran `generated_at` ni ids de ejecución. La huella sirve
     para **verificar** que las entradas releídas son las mismas; **no** reconstruye las entradas por
     sí sola.
- **Contexto:** `docs/04` §3.16 mezcla el resultado calculado con el seguimiento humano; `docs/07`
  §7.2 condicionaba la consulta de `NO_NEED` y `NOT_CALCULABLE` a `DT-P18`; `DT-051` deja a U4 la
  persistencia de los racionales no decimales.
- **Alternativas:** solo `RECOMMEND`; dos tablas; `status` mutable en la misma fila; guardar la
  entrada completa en lugar de su huella.
- **Razón:** cumple «todo el catálogo» (US-046) y la explicabilidad (US-045); un hecho calculado no se
  muta (mismo criterio que `forecasts`, `DT-057`); no se crean columnas sin consumidor (`docs/04` §9.2).
- **Consecuencias:** `/products/{id}/recommendation` devuelve siempre la evaluación. La
  reconstrucción del contexto se hace desde la carga inmutable, las reglas de lectura versionadas
  (`input_rules_version`) y `calculation_inputs`; `input_sha256` verifica que las entradas releídas
  coinciden.
- **Estado:** `ACEPTADA` (2026-10-03, decisión del responsable al autorizar U4); implementada y validada el mismo día (`docs/06` §16.13.5). Cierra `DT-P18`.
  Detalle: `docs/04` §9.11.

## DT-060 — `forecast_id`: forecast lógico y fila de anclaje

- **Decisión:** el **forecast lógico** es la serie `(forecast_run_id, product_id, location_id)` con
  `is_primary = true`: 14 filas con `period_start = as_of_date + 1 + 7(k−1)`, el mismo
  `model_version_id`, `granularity = WEEKLY` y `method_used = BASELINE`; si no se cumple, la
  ejecución termina en `FAILED`. **`forecast_id`** es el `id` de la fila h=1, que **ancla la serie
  lógica**: no significa que la recomendación use una sola semana, sino las `K(H)` que necesita. El
  mismo valor va en `Forecast.forecast_id` de U1 y en `recommendations.forecast_id`. `model_version`
  de U1 = `model_version_id` de la serie; `weekly_quantities` = las 14 `predicted_quantity` en orden.
  Las 14 cantidades se copian en `calculation_inputs`. Sin serie primaria: `forecast = None` y U1
  devuelve `FORECAST_MISSING`.
- **Contexto:** `docs/04` §3.16 prevé un solo `forecast_id`; `DT-057` persiste 14 filas por serie y
  deja a U4 la correspondencia.
- **Alternativas:** entidad padre en U3; array de 14 ids; referencia compuesta.
- **Razón:** no reabre U3, conserva una clave foránea válida (un índice único parcial no puede ser
  destino de una clave foránea) y la copia hace la recomendación autoexplicativa.
- **Estado:** `ACEPTADA` (2026-10-03, decisión del responsable al autorizar U4); implementada y validada el mismo día (`docs/06` §16.13.5).

## DT-061 — Ejecución de forecast consumida: `forecast_run_id`

- **Decisión:** `calculation_runs.forecast_run_id` (FK a `calculation_runs(id)`), obligatoria si y
  solo si `run_type = 'RECOMMENDATION'`; en `RECOMMENDATION`, `reference_model_version_id` es nulo. U4
  consume exclusivamente la ejecución `FORECAST` `COMPLETED` con el mismo `as_of_date`, el mismo
  `data_load_id` y el `config_sha256` de U3 vigente en el código (única por el índice parcial de U3).
  Nunca «la última» ni por `generated_at`; nunca ejecuciones `FAILED`, configuraciones antiguas, otra
  carga ni series no primarias. Si no existe, U4 rechaza sin escribir y no lanza el forecast. La
  coherencia de la FK (tipo, estado, corte y carga) se verifica en código, dentro de la transacción,
  y en pruebas.
- **Razón:** selección explícita y determinista; la configuración de U3 identifica unívocamente la
  ejecución.
- **Estado:** `ACEPTADA` (2026-10-03, decisión del responsable al autorizar U4); implementada y validada el mismo día (`docs/06` §16.13.5).

## DT-062 — Versión del motor, política e idempotencia de la ejecución de recomendaciones

- **Decisión:**
  1. **`engine_version`:** `calculation_runs.engine_version` (obligatoria si y solo si
     `RECOMMENDATION`) y `recommendations.engine_version` toman la constante `ENGINE_VERSION` de U1
     (valor actual `"0.1.0"`, que U4 no fija en su código); la ejecución y sus filas deben coincidir.
  2. **Política:** `policy_set = "V1_PROVISIONAL"`, único valor y sin nombres equivalentes. U4
     consume `V1_PROVISIONAL_PARAMETERS` de U1 (`R = 7`, `z = 33/20`, `N = 12`, `N_MIN = 3`,
     `LT_MAX = 90`) y no redefine sus valores. `policy_snapshot` =
     `{"policy_set":"V1_PROVISIONAL","R":7,"z":"1.65","N":12,"N_MIN":3,"LT_MAX":90}`, con `z` como
     decimal exacto, nunca `float`. Sin `policy_version`.
  3. **Idempotencia:** `config_sha256` = SHA-256 del JSON canónico de `run_type = "RECOMMENDATION"`,
     `engine_version`, la política completa con `policy_set = "V1_PROVISIONAL"`,
     `forecast_config_sha256`, `forecast_selection`, `catalog_policy = "ALL_PRODUCT_LOCATIONS"`,
     `input_rules_version` y la representación (28 cifras, `ROUND_HALF_EVEN`); sin *timestamps*, ids
     autogenerados, `generated_at` ni estado humano. Con una `COMPLETED` igual en `(RECOMMENDATION,
     as_of_date, data_load_id, config_sha256)`: `ALREADY_COMPUTED`, sin escribir nada.
  4. **Concurrencia:** bloqueo *advisory* sobre esa identidad.
  5. **Atomicidad:** una transacción; ante cualquier fallo, incluido `InvalidInputError`, *rollback* y
     fila `FAILED` en otra transacción, con `product_id` y `location_id` en el error.
  6. **`data_origin`:** la ejecución exige una carga `SYNTHETIC` (`DT-063`); U1 no lee
     `data_origin`.
- **Razón:** misma pauta que `DT-057`; las versiones y la política forman parte de la identidad de la
  salida (`DT-051`).
- **Estado:** `ACEPTADA` (2026-10-03, decisión del responsable al autorizar U4); implementada y validada el mismo día (`docs/06` §16.13.5).

## DT-063 — U4 V1 solo se ejecuta sobre cargas `SYNTHETIC`

- **Decisión:** `python -m app.runs recommend` rechaza la ejecución, sin escribir nada, si
  `data_loads.data_origin` de la carga `COMPLETED` no es exactamente `'SYNTHETIC'` (también si es
  `NULL`). El motor sigue sin leer `data_origin` (`DT-045`, `docs/06` §16.7).
- **Contexto:** `DT-031` §V1-05 puentea la política solo dentro del entorno sintético y exige que,
  con datos reales, rija `BR-009`. `DT-P16` pregunta cómo impedirlo sin que el motor lea
  `data_origin` y **no lo decide**. U4 es el primer componente que aplica `V1_PROVISIONAL` a datos
  persistidos.
- **Alternativas:** (a) rechazar la ejecución si la carga no es `SYNTHETIC`; (b) evaluar las cargas
  `REAL` sin los parámetros puenteados (`R`, `z`), para obtener `NOT_CALCULABLE` con
  `MISSING_POLICY_PARAMETER`; (c) no poner guarda.
- **Razón:** (c) permitiría aplicar en silencio una política provisional a datos reales. (b) es un
  posible mecanismo definitivo, pero elegirlo es precisamente `DT-P16`. (a) es la restricción mínima
  que hace cumplir `DT-031` sin decidir `DT-P16`. No viola `BR-007`: no altera ninguna regla de
  cálculo; es una precondición de alcance de la ejecución.
- **Consecuencias:** con datos `REAL`, U4 V1 no produce recomendaciones hasta que se decida
  `DT-P16`. Con `DT-044` (un linaje por base), una carga `REAL` sería otra base; el dataset 0.4.0 no
  se ve afectado. Cuando se decida `DT-P16`, `DT-063` se revisa o se sustituye. **`DT-P16` sigue
  abierta.**
- **Estado:** `ACEPTADA` (2026-10-03, decisión del responsable al autorizar U4); implementada y validada el mismo día (`docs/06` §16.13.5).

## DT-064 — Dependencias de U5: API y pruebas

- **Decisión:** dos grupos opcionales nuevos en `backend/pyproject.toml`; `dependencies = []` y
  `db = ["psycopg[binary]==3.3.6"]` no cambian:
  - `api = ["fastapi==0.141.1", "starlette==1.3.1", "pydantic==2.13.5", "uvicorn==0.52.4"]`
    (`uvicorn` sin extras);
  - `test = ["httpx2==2.13.1"]`, cliente del `TestClient` de Starlette.

  Instalación de U5: `pip install -e ".[db,api,test]"`. Ninguna otra dependencia: ni SQLAlchemy, ni
  `psycopg_pool`, ni `pydantic-settings`, ni `python-dotenv`, ni bibliotecas JWT, ni ORM, ni
  observabilidad, ni límite de tasa.
- **Contexto:** `DT-043` autoriza las dependencias al abrir cada unidad y nombra FastAPI y Pydantic para
  U5 (`CLAUDE.md` §5). Ejecutar la API exige un servidor ASGI y probarla, el cliente del `TestClient`;
  ninguno estaba nombrado. FastAPI no fija límite superior para Starlette.
- **Alternativas:** FastAPI 0.142.x; `fastapi[standard]`; sin servidor; `httpx==0.28.1` para las
  pruebas.
- **Razón:** FastAPI 0.142.x añade `opentelemetry-api` como dependencia obligatoria y era de la semana de
  la consulta; `[standard]` arrastra CLI, plantillas y *multipart* sin consumidor; sin servidor la API no
  se ejecuta. Starlette se fija en 1.3.1, la versión vigente al publicarse FastAPI 0.141.1, porque la
  línea 1.x cambia deprisa. El `TestClient` de Starlette 1.3.1 importa `httpx2` y solo recurre a `httpx`
  como alternativa obsoleta, con `StarletteDeprecationWarning`; por eso las pruebas usan
  `httpx2==2.13.1` y no `httpx`.
- **Verificación (2026-10-03, PyPI; datos externos, no decisiones del proyecto):** FastAPI 0.141.1
  (`starlette>=0.46.0`, `pydantic>=2.9.0`, Python ≥ 3.10); Starlette 1.3.1 (`anyio>=3.6.2,<5`; extra
  `full` con `httpx2>=2.0.0`); Pydantic 2.13.5 (`pydantic-core==2.46.5`); uvicorn 0.52.4; `httpx2`
  2.13.1 (Python ≥ 3.10, publicado el 2026-09-23, no retirado). La resolución sin instalar
  (`uv pip compile`, Python 3.11) de las cinco versiones junto con `psycopg[binary]==3.3.6` da 18
  paquetes sin conflicto (transitivos: `annotated-doc`, `annotated-types`, `anyio`, `click`, `h11`,
  `httpcore2`, `idna`, `pydantic-core`, `truststore`, `typing-extensions`, `typing-inspection`,
  `psycopg-binary`). Inspección estática de las ruedas: todos los nombres que usa
  `starlette/testclient.py` 1.3.1 (`Client`, `BaseTransport`, `ByteStream`, `Request`, `Response`,
  `USE_CLIENT_DEFAULT`, `_client.UseClientDefault` y los alias de `_types`) existen en `httpx2` 2.13.1.
  La prueba en ejecución llega con la implementación (criterio 1 de `docs/07` §7.5).
- **Consecuencias:** `supply_engine` sigue sin dependencias; cambiar cualquiera de estas versiones exige
  una decisión nueva.
- **Estado:** `ACEPTADA` (2026-10-03, decisión del responsable al autorizar U5); implementada y validada el mismo día (`docs/07` §7.5).

## DT-065 — Autenticación local de U5: `TokenValidator` de desarrollo, `APP_ENV` y roles

- **Decisión:**
  1. Puerto `TokenValidator` en `app/api`: `validate(token) → Identity{subject_id, roles}`; un token no
     válido lanza un error que la API traduce a 401. La Fase 8 sustituye la implementación (Entra ID),
     no el puerto.
  2. `DevTokenValidator`: tokens **opacos** `^dev-[A-Za-z0-9_-]{16,64}$`, sin JWT, sin firma y sin
     expiración (`exp`/`nbf` son de Entra ID, `docs/10` §2.3). Registro token → `{subject_id, roles}`:
     en las pruebas, construido en el código; en local, la variable `DEV_AUTH_IDENTITIES` (JSON) de un
     `.env` ignorado por Git, cargado por el shell o por `env_file` de Docker (la aplicación solo lee
     `os.environ`). `subject_id` con `^[a-z0-9-]{1,64}$`; `roles` no vacío y dentro de `VIEWER`,
     `ANALYST`, `PLANNER`, `ADMIN`. Un registro inválido o vacío impide arrancar. Comparación en tiempo
     constante; los tokens nunca se registran (`docs/10` §4).
  3. `APP_ENV` obligatorio, sin valor por defecto, con vocabulario `local | dev | staging | prod`.
     Solo `local` (que incluye las pruebas) arranca la API con el validador de desarrollo; `dev`,
     `staging`, `prod`, la variable ausente o cualquier otro valor la hacen negarse a arrancar: no hay
     validador de Entra ID hasta la Fase 8.
  4. Autorización: una dependencia por endpoint exige que los roles de la identidad intersequen los
     permitidos por `docs/07` §7.2, sin jerarquía implícita (§7.1). Sin cabecera: 401
     `AUTHENTICATION_REQUIRED`; esquema distinto de `Bearer`, token mal formado o desconocido: 401
     `INVALID_TOKEN`; ambos con `WWW-Authenticate: Bearer`. Rol no permitido: 403 `FORBIDDEN`.
- **Contexto:** `docs/10` §15 pide identidades ficticias que solo se activen en local y en pruebas y que
  se nieguen a arrancar en `dev`, `staging` y `prod`; el vocabulario de `APP_ENV` de `docs/10` §6 no
  tenía `local`, aunque `docs/12` §5 define el entorno Local.
- **Alternativas:** JWT local firmado; tokens que declaran sus propios roles; activación implícita sin
  `APP_ENV`.
- **Razón:** lo mínimo que satisface `docs/10` §15 sin inventar criptografía y sin poder activarse por
  accidente en un entorno desplegado.
- **Estado:** `ACEPTADA` (2026-10-03, decisión del responsable al autorizar U5); implementada y validada el mismo día (`docs/07` §7.5).

## DT-066 — Contrato de lectura de la API V1: ejecución por defecto, `provenance` y convenciones

- **Decisión:**
  1. **Ejecución por defecto** de `/forecasts`, `/products/{id}/forecast`, `/recommendations` y
     `/products/{id}/recommendation`: la carga actual (la única `data_loads` `COMPLETED`, `DT-044`) →
     entre sus ejecuciones del tipo correspondiente con `status = 'COMPLETED'`, el mayor `as_of_date` →
     a igualdad, el mayor `id`. Nunca por `generated_at` ni `finished_at`; nunca `FAILED`. Sin
     ejecución: 404 `RUN_NOT_FOUND`. Un `run_id` explícito debe existir, ser del tipo esperado y estar
     `COMPLETED`; si no, 404 `RUN_NOT_FOUND`. `provenance.run_id` dice siempre cuál se usó.
  2. **Forecasts:** solo la serie primaria (`is_primary`, la que consume U4, `DT-060`), paginada por
     serie, con el modelo `{name, version}` de cada serie; las series no primarias no se exponen en V1.
  3. **Recomendaciones:** las tres `outcome` se consultan; `NO_NEED` y `NOT_CALCULABLE` nunca son 404 ni
     error técnico (`DT-059`). El detalle devuelve el desglose tal como se guardó.
  4. **`provenance`** en toda respuesta con forecast o recomendación: `data_origin`, `dataset_version`,
     `generator_version`, `data_load_id`, `as_of_date`, `run_id`; `model_version` en forecasts;
     `engine_version`, `policy_set` y `forecast_run_id` en recomendaciones; `notices`.
     `SYNTHETIC_DATA` si y solo si `data_loads.data_origin = 'SYNTHETIC'`; `V1_PROVISIONAL_POLICY` si y
     solo si `policy_set = 'V1_PROVISIONAL'` (solo en recomendaciones); en ese orden; ningún otro código.
  5. **Errores** con el formato de `docs/07` §1 y los códigos de §7.4, incluido 405 para escrituras;
     sin trazas, SQL, hosts ni valores recibidos.
  6. **`X-Correlation-ID`**: se acepta el del cliente si cumple `^[A-Za-z0-9._-]{8,64}$`; si no, el
     servidor genera un UUID4. Va en la cabecera de toda respuesta, en el cuerpo de todo error y en el
     log JSON de cada petición.
  7. **Paginación** de §1 (`page ≥ 1`, `page_size` 1–200, por defecto 50) con desempate por `id`; página
     fuera de rango → 200 con `items` vacío.
  8. **Números:** `Decimal` como texto JSON; ningún `float`.
  9. **Solo lectura:** consultas de SQL escrito a mano en `app/db/read/` (`docs/03` §16.2), conexión por
     petición con `read_only = True` (una escritura falla con SQLSTATE 25006); `api` no importa
     `supply_engine`, `forecasting` ni `runs`; ningún `GET` recalcula.
  10. **`/health`**: `{status, version}`, público y sin tocar PostgreSQL. `/docs` y `/openapi.json`
      públicos en `local`; `/redoc` desactivado; esquema de seguridad `HTTPBearer`.
  11. **CORS y límite de tasa:** aplazados (Fase 7 y Fases 12–14), sin configuración ni dependencia.
- **Contexto:** `docs/07` §7.2 fijaba «la última ejecución `FORECAST` completada» sin desempate y no
  daba regla ni 404 para las recomendaciones; §1 y §7.1 dejaban por concretar `correlation_id`,
  `provenance` y la representación numérica.
- **Alternativas:** última por `finished_at`/`generated_at`; `run_id` obligatorio; reproducir la
  configuración vigente de U4 (exigiría `api → runs`, prohibido por `docs/03` §16.4).
- **Razón:** la regla depende solo del estado de la base, ignora `FAILED` y otras cargas y es la misma
  para forecasts y recomendaciones.
- **Estado:** `ACEPTADA` (2026-10-03, decisión del responsable al autorizar U5); implementada y validada el mismo día (`docs/07` §7.5).

## DT-067 — Historia de consumo de `/products/{id}/history` (US-033, RF-009)

- **Decisión:**
  1. Fuente: solo `consumption` (demanda satisfecha), nunca `demand`; `occurred_on` sin conversión de
     zona; sin corrección por desabasto (`DT-011` sigue abierta); `stockout_days` por periodo cuenta
     los días con `is_stockout_affected`.
  2. Rango `date_from`–`date_to` inclusivo y opcional (por defecto, la primera y la última fecha con
     consumo del producto); `date_from > date_to` → 400 `INVALID_DATE_RANGE`.
  3. `granularity` `daily | weekly | monthly`, por defecto `weekly`; semanas ISO de calendario (lunes a
     domingo) y meses de calendario; `period_end` exclusivo.
  4. Cada periodo: `period_start`, `period_end`, `days`, `days_observed`, `quantity` (Σ consumo),
     `stockout_days`, `complete`. Un día sin fila es «no observado» y no cuenta como cero; un periodo es
     completo si cae entero dentro del rango y todos sus días están observados.
  5. Estadísticos solo sobre los n periodos completos: `periods_used = n`; `mean = Σqᵢ/n`;
     **`std_dev` = desviación estándar poblacional** `√(Σ(qᵢ − mean)²/n)`, sin corrección de Bessel ni
     desviación muestral; `cv = std_dev/mean` (nulo si `mean = 0`); `zero_periods` = periodos completos
     con `quantity = 0`. Con n = 1, `std_dev = 0`; con n = 0, todos nulos.
  6. Cálculo exacto (`Fraction`); la raíz en `Decimal` con 28 cifras; se informa con 6 decimales
     `ROUND_HALF_EVEN`.
- **Contexto:** RF-009, US-033 y `docs/07` piden media, desviación, coeficiente de variación y periodos en
  cero sin fijar estimador, periodos ni tratamiento de huecos.
- **Alternativas:** desviación muestral (n − 1); semanas ancladas en el corte (como el proveedor de U3,
  `docs/05` §19); rellenar huecos con cero.
- **Razón:** la desviación poblacional describe el conjunto observado que se usa, es la misma que usa U1
  (`DT-P14`, `σ_H` poblacional) y queda definida con n = 1. Las semanas ISO son estables aunque cambie el
  rango; rellenar huecos inventaría datos.
- **Estado:** `ACEPTADA` (2026-10-03, decisión del responsable al autorizar U5); implementada y validada el mismo día (`docs/07` §7.5).

## DT-068 — Entrega y contrato de la explicación por plantilla (U6)

- **Decisión:**
  1. **Entrega.** `GET /api/v1/recommendations/{recommendation_id}/explanation`: un recurso hijo de la
     recomendación, de solo lectura, determinista e idempotente. No se usa
     `POST /api/v1/assistant/explain/{recommendation_id}` (`docs/07` §2.12): `/assistant/*` queda reservado
     al asistente con LLM de la Fase 10. Es una **ampliación** de la superficie aceptada: U5 = 13 endpoints
     (`DT-066`, `docs/07` §7.4), U6 añade el **endpoint 14**. Ninguna respuesta de U5 cambia.
  2. **Autenticación y roles.** `Authorization: Bearer` con el `TokenValidator` de U5 (`DT-065`); los
     cuatro roles `VIEWER`, `ANALYST`, `PLANNER` y `ADMIN`, sin jerarquía, los mismos del detalle
     `GET /api/v1/recommendations/{id}` (`docs/07` §3: «Asistente de IA — Explicaciones» para los cuatro).
     401 y 403 exactamente como en U5; 404 `RECOMMENDATION_NOT_FOUND`; 422 con un `recommendation_id` no
     válido. Formato de error, `X-Correlation-ID` y conexión de solo lectura: los de `DT-066`. Sin 503:
     la plantilla no depende de ningún servicio externo.
  3. **Respuesta 200**: `{recommendation_id, run_id, outcome, explanation {generator, status, narrative,
     warning}, facts[], flags[], reasons[], reason_details[], missing_policy_parameters[], provenance}`.
     `facts[]` = `{key, value, display, unit}`; `reason_details[]` = `{code, text}`; `provenance` es el
     bloque de recomendaciones de `DT-066` (con `notices`). `status`: `VERIFIED` (narrativa generada y
     verificada), `DEGRADED` (narrativa descartada, `DT-069`) o `NOT_APPLICABLE` (`NOT_CALCULABLE`).
  4. **`ExplanationContext`** inmutable con `kind = RECOMMENDATION_EXPLANATION`, `recommendation_id`,
     `run_id`, `outcome`, `facts`, `flags`, `reasons`, `missing_policy_parameters`, `lead_time_source`,
     `unit_of_measure` y `provenance`. No es una copia del `RecommendationDetail`. Se construye **solo**
     con valores persistidos: la fila de `recommendations` (`calculation_inputs.breakdown`, columnas
     `flags`, `reasons`, `missing_policy_parameters`), el contexto de la ejecución (`DT-066`) y
     `products.unit_of_measure`. U6 **lee → transforma → explica**; nunca recalcula ni llama a U1.
  5. **`facts[]`**: vocabulario cerrado, en este orden: `q_final`, `raw_need`, `safety_stock`,
     `target_level`, `lead_time_days`, `uncapped_lead_time_days`, `review_period_days`,
     `coverage_horizon_days`, `demand_over_horizon`, `inventory_position_decision`,
     `inventory_position_accounting`, `total_in_transit`, `effective_in_transit`, `moq`,
     `order_multiple`, `q_moq`, `on_hand`, `reserved` (claves de `calculation_inputs.breakdown`). Contiene
     **exactamente** las cifras que la plantilla del `outcome` puede usar (`docs/09` §14.5): sin la frase
     condicionada, sin su cifra. `unit` ∈ `QUANTITY` · `DAYS` · `FACTOR` (`FACTOR` existe en el
     vocabulario y ningún hecho de V1 lo usa). Fuera de `facts[]`: `a`, `b`, `d`, `p`, `s1`, `s2`,
     `sigma_window_count`, `lead_time_observation_count`, `z`, `sigma_h`, `demand_over_lead_time`,
     `forecast_id` y demás ids, `effective_lines`, `weekly_quantities`, `as_of_date`, `horizon_start` y
     `engine_version`.
  6. **Unidad de medida.** `api` lee `products.unit_of_measure` del producto de la recomendación con
     `db/read` y la entrega como metadato `unit_of_measure` del contexto; no es una cifra ni entra en
     `facts[]`. La narrativa escribe las cantidades seguidas del código tal como está en `products`
     (`EACH`, `BOX`, `KG`), nunca el genérico «unidades». U4 no cambia.
  7. **Plantillas** en `backend/app/genai/templates.py`, con `string.Template` de la biblioteca estándar:
     una por `RECOMMEND` y otra por `NO_NEED`, frases fijas por marca, por razón y de provisionalidad.
     Texto normativo en `docs/09` §14.5. Sin motores de plantillas, archivos, base de datos ni servicios.
  8. **`NOT_CALCULABLE`**: `narrative = null`, `facts = []`, `status = NOT_APPLICABLE`; se conservan
     `reasons`, `reason_details` (frase fija sin cifras por razón, en el orden canónico de `docs/06`
     §16.11.4), `missing_policy_parameters` y `provenance`.
  9. **US-048** («cada recomendación tiene una explicación») se interpreta así: `RECOMMEND` y `NO_NEED` →
     explicación narrativa; `NOT_CALCULABLE` → explicación estructurada, `narrative = null`.
  10. **Versionado:** `explanation.generator = "template/1.0.0"` (SemVer, mismo criterio que
      `engine_version`, `DT-051`); todo cambio de texto que altere la narrativa sube la versión. Sin
      `template_id` ni `explanation_version`: el `outcome` elige la plantilla y la explicación no se persiste.
  11. **Inmutabilidad:** `@dataclass(frozen=True, slots=True)`, colecciones `tuple`, valores `str` o
      enumeraciones de texto; ningún `dict` ni `list` dentro del contexto; el contexto copia sus entradas.
      La serialización HTTP es de `api`.
  12. **Arquitectura:** `api → genai`; `genai` no importa `api`, `db`, `psycopg`, `supply_engine`,
      `forecasting` ni `runs`, no recibe conexiones ni funciones de cálculo y solo usa la biblioteca
      estándar. Sin dependencias nuevas.
  13. **Fuera de U6:** LLM, RAG, Azure OpenAI, embeddings, AI Search, `DocumentRetriever`, prompts, chat,
      generación libre, explicaciones personalizadas, persistencia de explicaciones y CU-2 a CU-5; también
      **prioridad, riesgo, urgencia y «qué ocurre si no se actúa»** de CU-1 (`docs/09` §4), que dependen
      de `BR-X03`, abierta.
- **Contexto:** `docs/09` §14 fijaba el flujo, la frontera y la verificación, pero no la vía de entrega
  (`docs/07` §2.12 frente a §7.3 y §7.4), el conjunto exacto de cifras (§14.2 frente a `docs/06` §13), la
  unidad de medida ni el caso `NOT_CALCULABLE`. Dossier de U6 (2026-10-04), alternativas A1, A2, B y C.
- **Alternativas:** A1 `POST /assistant/explain` (contradice la V1 de solo lectura); B, un campo en el
  detalle (cambia dos respuestas de U5 y acopla a ellas un generador futuro con costo y fallos, contra
  RNF-010); C, solo el módulo (US-048 sin consumidor; contradice `docs/07` §7.3).
- **Razón:** la explicación por plantilla es una representación derivada de una recomendación
  persistida: un `GET` sobre ella es la forma de solo lectura, idempotente y de menor exposición, y no
  toca ninguna respuesta existente.
- **Consecuencias:** `docs/07` §7.2 pasa a 14 rutas (13 implementadas por U5; la 14 llega con U6);
  `tests/api` (`ENDPOINTS`, OpenAPI con 14 rutas) y la matriz de roles se amplían en la implementación;
  `db/read` recibe una lectura aditiva para `unit_of_measure`.
- **Estado:** `ACEPTADA` (2026-10-04, decisión del responsable al autorizar U6); implementada y validada el mismo día (`docs/09` §14.6).

## DT-069 — Presentación, verificación y degradación de cifras (U6, RS-010)

- **Decisión:**
  1. **`Fact`** = `{key, value, display, unit}`. `value` es la cadena persistida en
     `calculation_inputs.breakdown`, sin tocar. `display` es la **única** representación que puede
     aparecer en la narrativa; se calcula **una sola vez**, al construir el contexto.
  2. **`display`**, desde `value`, sin `float`:
     - entero (`"242"`): tal cual;
     - racional `"p/q"` o decimal exacto: `Fraction` exacto → 6 decimales `ROUND_HALF_EVEN`;
     - término aproximado (`approximate_terms`, `Decimal` de 28 cifras, `docs/06` §16.13.3): ese `Decimal`
       → 6 decimales `ROUND_HALF_EVEN`;
     - después se eliminan los ceros finales y el punto si queda solo (`1.650000` → `1.65`, `2.500000` →
       `2.5`, `3.000000` → `3`); el cero es `0`, sin signo;
     - separador decimal `.`, sin separador de miles. Es la misma precisión de `DT-067` y de los forecasts
       de U3; no se crea ninguna nueva.
  3. **Regla crítica:** el renderizador y el verificador usan exactamente la misma cadena `display`. No
     existe una segunda operación de redondeo ni una comparación numérica.
  4. **Cifra narrativa:** toda coincidencia maximal de `-?\d+(?:\.\d+)?` en el texto final. Es válida si y
     solo si es **igual, como cadena**, al `display` de algún `Fact` del contexto. Sin tolerancia y sin
     volver a convertir a número.
  5. **Plantillas:** ningún dígito ni `%` literal; ni fechas, ni SKU, ni versiones, ni identificadores,
     ni números escritos con letras. Las únicas cifras de la narrativa salen de placeholders de
     `facts[]`. Los placeholders de texto (`unit_of_measure`, procedencia del plazo) no contienen dígitos.
     A la izquierda de un placeholder numérico no hay dígito, `.` ni `-`; a la derecha no hay dígito, y
     un `.` solo puede ir seguido de espacio o del fin del texto. Las restas se escriben con palabras.
  6. **Degradación (RS-010, RNF-010):** si alguna cifra no es válida, el verificador lanza la excepción
     interna `UnverifiedFigureError`; el servicio responde **HTTP 200** con `status = DEGRADED`,
     `narrative = null` y `warning = NARRATIVE_UNVERIFIED`, y conserva `facts`, `flags`, `reasons`,
     `reason_details`, `missing_policy_parameters` y `provenance`. No devuelve el texto rechazado, ni una
     traza, ni un error HTTP. Registra el evento con su `correlation_id`. El aviso no se añade a
     `provenance.notices` ni la modifica.
     *(Aclaración de la implementación, 2026-10-04: la degradación cubre **solo** cifras ajenas en el texto
     generado. Una violación interna del contrato —un hecho que la plantilla necesita y falta, la unidad o la
     procedencia del plazo ausentes o desconocidas, un `outcome` desconocido— no es RS-010: lanza
     `ExplanationError` y la API responde el 500 `INTERNAL_ERROR` uniforme de `DT-066`. Con los datos que
     garantizan las restricciones de U4 no ocurre.)*
  7. **Prueba RS-010:** un `TextGenerator` de prueba que introduce una cifra ajena (por ejemplo `999`, una
     fecha, un SKU y un `-5` sin hecho) produce `DEGRADED` con los datos conservados.
  8. **Provisionalidad:** los avisos son exactamente los de `DT-066` (`SYNTHETIC_DATA`,
     `V1_PROVISIONAL_POLICY`) en `provenance.notices`. Con narrativa, una frase fija al final dice que las
     cifras son provisionales y que no constituyen una recomendación de negocio definitiva (`docs/09`
     §14.5). Con `NOT_CALCULABLE` o `DEGRADED` no hay narrativa y la provisionalidad queda solo en
     `notices`. Ningún aviso nuevo.
- **Contexto:** U4 persiste enteros, decimales exactos, racionales `"p/q"` y `Decimal` de 28 cifras
  (`docs/06` §16.13.3); copiarlos al texto lo haría ilegible, y `docs/09` §8 y §14.3 exigían verificar sin
  definir qué es una cifra ni cómo se degrada.
- **Alternativas:** cifras literales; 2 decimales (precisión nueva); comparación numérica con tolerancia;
  error HTTP al degradar.
- **Razón:** una sola cadena para mostrar y verificar elimina los falsos positivos por redondeo; la
  igualdad exacta de cadenas no admite ambigüedad; responder 200 con los datos cumple RNF-010.
- **Consecuencias:** las comparaciones entre cifras mostradas pueden diferir en la sexta cifra decimal
  de las exactas; por eso las plantillas no hacen aritmética en el texto. Una futura LLM (Fase 10) que
  escriba números con letras no la detectaría este verificador: se revisará entonces.
- **Estado:** `ACEPTADA` (2026-10-04, decisión del responsable al autorizar U6); implementada y validada el mismo día (`docs/09` §14.6).

## DT-070 — Fase 7: interfaz React V1 (alcance, stack, autenticación local y contrato con la API)

- **Decisión** (Fase 7 = `frontend/`, consumidor de la API V1 de solo lectura; no cambia U1–U6):
  1. **Alcance (F7-01).** Sí: US-070 (estructura y navegación), US-072 sin el filtro «por debajo del punto
     de reorden» (`docs/07` §7.3), US-073 **sin acciones** (lista y detalle), US-074 (detalle con
     `CalculationBreakdown`), US-048 (explicación de U6) e historial de consumo (RF-009). US-075 **parcial**:
     forecast, banda nominal, `confidence_flag`, método y modelo, con historia y forecast separados y sin
     afirmar que la incertidumbre está validada; su cierre depende de US-055 (Fase 5). No: US-071 (dashboard
     priorizado) y US-076 (riesgos y proveedores), acciones sobre recomendaciones, administración,
     asistente y exportación. Nada que dependa de `BR-X03` (riesgo, prioridad, urgencia, cobertura, «qué
     ocurre si no se actúa»). `GET /runs/{run_id}` solo como enlace desde `provenance.run_id` para PLANNER y
     ADMIN.
  2. **Routing (F7-02).** URLs estables por vista; filtros, paginación y selección en la URL, nunca solo en
     memoria de React.
  3. **Autenticación (F7-03).** La de U5 (`DT-065`): el usuario pega un token `dev-…`, se valida con
     `GET /api/v1/me` y se guarda **solo en memoria**; al recargar se vuelve a autenticar; logout descarta el
     token; cada petición lleva `Authorization: Bearer`; 401 → login; 403 → se conserva la sesión. Sin
     `sessionStorage`, `localStorage`, MSAL, Entra ID, OAuth ni OIDC (Fase 8). Ningún token en el código, en
     variables de build ni en el repositorio. Un `AuthProvider` aísla el mecanismo para sustituirlo en la
     Fase 8 sin tocar las vistas.
  4. **Roles (F7-04).** Copia explícita de la matriz de `docs/07` §7.2 (los cuatro roles en todo salvo
     `/history`: ANALYST, PLANNER, ADMIN; `/runs`: PLANNER, ADMIN), sin jerarquía, con los `roles` de `/me`.
     La navegación oculta lo no autorizado; un 403 del backend muestra «Sin permiso para ver esto» sin
     cerrar sesión. La seguridad sigue en el backend (`docs/10` §2, RS-003).
  5. **Layout (F7-05).** `AppShell` con navegación, contenido y estados globales de carga y error. La
     navegación muestra solo lo disponible: Productos, Inventario, Recomendaciones, Predicciones (y el
     historial dentro del detalle de producto). Dashboard priorizado, Riesgos, Proveedores, Administración y
     Asistente no aparecen como funcionalidad activa.
  6. **Diseño visual (F7-06).** Neutro y sobrio, sin identidad corporativa definitiva, con tokens de diseño
     centralizados; interfaz en español; estado nunca solo por color; esqueletos durante la carga; unidades
     siempre visibles.
  7. **Estado (F7-07).** Estado del servidor con la librería de *data fetching*; sesión en un contexto de
     React; filtros, paginación y selección en la URL; el resto, local al componente. Sin Redux ni Zustand.
  8. **Cliente de API (F7-08).** Fino, sin recalcular nada, con base **relativa `/api`**. Tipos **generados
     desde el OpenAPI** de la API (`openapi-typescript`, a partir de `GET /openapi.json` de la API local);
     el archivo generado se versiona y se regenera con un script de npm cuando cambie el contrato; no se
     duplica el contrato a mano.
  9. **Errores (F7-09).** Un `ErrorState` común: 401 → login; 403 → «Sin permiso para ver esto»; 404 → «no
     encontrado» o estado vacío según el endpoint (p. ej. producto sin forecast o sin evaluación en la
     ejecución); 400/422 → filtro o entrada inválida, sin mostrar el valor; 500 → mensaje genérico; 503 →
     servicio no disponible. Siempre el `correlation_id` cuando exista; nunca trazas ni detalles técnicos.
  10. **Paginación (F7-10).** `page ≥ 1`, `page_size` 1–200 (50 por defecto); la UI usa `items`, `total`,
      `page`, `page_size` del backend y nunca recalcula `total`; al cambiar un filtro, `page = 1`.
  11. **Filtros (F7-11).** Solo los que la API admite: productos (`search`, `is_active`, `sort`,
      `category_id` como identificador explícito), inventario (`product_id`, `category_id`, `sort`),
      recomendaciones (`outcome`, `product_id`, `category_id`, `supplier_id`, `run_id`, `sort`), forecasts
      (`product_id`, `category_id`, `run_id`). **No** se construyen selectores completos de categorías ni de
      proveedores ni se fabrica un catálogo en el frontend: la API no tiene `/categories` ni `/suppliers` y
      la Fase 7 no los crea. Una experiencia que necesite un catálogo completo queda pendiente de una fase o
      decisión futura.
  12. **Forecast (F7-12).** Los 14 periodos con `predicted_quantity`, `lower_bound`, `upper_bound`,
      `confidence_level`, `method_used`, `confidence_flag` y `model_version`. Banda rotulada «nominal 0.80»
      (el valor de `confidence_level`); aviso explícito con `INSUFFICIENT_HISTORY`. Historia y forecast
      visualmente separados (semanas ISO frente a semanas ancladas en el corte, `DT-067`, `DT-056`), sin
      continuidad aparente. El componente depende solo de esos campos, no de la media móvil ni de otro
      algoritmo.
  13. **Recomendaciones (F7-13).** Las tres `outcome` con `reasons`, `reason_details`, `flags`,
      `missing_policy_parameters`, `provenance`, `policy_snapshot` y desglose. Orden por los campos que la API
      admite, y la vista lo dice. Sin urgencia, prioridad, riesgo ni acciones.
  14. **Explicación (F7-14).** Solo `GET /api/v1/recommendations/{id}/explanation` (`DT-068`), nunca
      `POST /assistant/*`. `VERIFIED`: narrativa, `facts`, `generator` y `notices`. `DEGRADED`: «Explicación no
      disponible», conservando `facts`, desglose, `warning` y `provenance`. `NOT_APPLICABLE`:
      `reason_details` sin narrativa. No es un chat ni un asistente.
  15. **Desglose (F7-15).** Dos niveles. Principal: `facts[].display` del servidor (`DT-069`) con sus
      unidades. «Detalles técnicos del cálculo», desplegable: los demás términos de
      `calculation_inputs.breakdown` cuando existan, en su **representación exacta** del backend (`value`,
      racional `p/q` o `Decimal` textual), sin `float`, sin recalcular y sin reinterpretar fórmulas; un
      término nulo se muestra como «no calculado». Así el `CalculationBreakdown` es completo (US-074).
  16. **Provenance (F7-16).** `SYNTHETIC_DATA` y `V1_PROVISIONAL_POLICY` visibles de forma permanente en
      forecast, recomendaciones y explicación cuando vienen en `notices`; ningún aviso nuevo. Productos e
      inventario muestran su `data_origin` por fila.
  17. **Responsive (F7-17).** Escritorio como escenario principal, tableta soportada, móvil para consulta
      (`docs/08` §9, ASSUMPTION-018); los puntos de corte se fijan en la implementación dentro de esa regla.
  18. **Accesibilidad (F7-18).** HTML semántico, teclado, foco visible, etiquetas, ARIA cuando haga falta,
      contraste suficiente, estado no solo por color y alternativa textual de los gráficos. Sin afirmar
      ninguna certificación (WCAG).
  19. **Pruebas (F7-19).** Vitest + Testing Library (con jsdom). Cubren componentes, carga, vacío, errores,
      autenticación, roles, filtros, paginación, recomendaciones, explicación, forecast, provenance y la
      ausencia de fórmulas de negocio en el cliente. E2E aplazada (`DT-P07`).
  20. **Stack y versiones (F7-20)**, fijadas a versión exacta (RS-013) en `package.json`, con
      `package-lock.json` versionado; verificadas en el registro de npm y en nodejs.org el 2026-10-05, sin
      instalar:

      | Paquete | Versión | Nota de compatibilidad |
      |---|---|---|
      | Node.js | 24 LTS «Krypton», **≥ 24.15.0** (referencia 24.21.0) | Activa hasta el 2026-10-20; mantenimiento hasta el 2028-04-30. Mínimo por `jsdom` (`^24.15.0`) y `react-router` (`>=22.22.0`) |
      | npm | **11.19.0** (la incluida en Node 24.21.0) | `packageManager` en `package.json` |
      | `react`, `react-dom` | 19.3.0 | |
      | `typescript` | **5.9.3** | No 6.x/7.x: `typescript-eslint` 8.71.0 exige `<6.1.0` y `openapi-typescript` 7.13.0 exige `^5.x` |
      | `vite` | 8.3.2 | Node `^20.19.0 \|\| >=22.12.0` |
      | `@vitejs/plugin-react` | 6.1.1 | `vite ^8` |
      | `react-router` | 8.4.0 | `react >=19.2.7` |
      | `@tanstack/react-query` | 5.104.1 | `react ^18 \|\| ^19` |
      | `recharts` (+ `react-is` 19.3.0) | 3.10.1 | Gráfico con banda (área de rango); `react ^19` |
      | `vitest` | 5.0.3 | `vite ^8`; Node `^22.12 \|\| ^24 \|\| >=26` |
      | `jsdom` | 30.1.2 | Entorno de pruebas |
      | `@testing-library/react` | 16.3.3 | con `@testing-library/dom` 10.4.2 |
      | `@testing-library/jest-dom` | 7.0.1 | `vitest >=0.32` |
      | `@testing-library/user-event` | 14.6.7 | |
      | `@types/react`, `@types/react-dom` | 19.3.0 | |
      | `eslint` | 10.12.0 | con `@eslint/js` 10.0.1 |
      | `typescript-eslint` | 8.71.0 | `eslint ^10`, `typescript <6.1.0` |
      | `eslint-plugin-react-hooks` | 7.1.1 | `eslint ^10` |
      | `prettier` | 3.9.9 | |
      | `openapi-typescript` | 7.13.0 | Generación de tipos (punto 8) |

      Cualquier otra dependencia, o cualquier cambio de versión, exige una decisión nueva.
  21. **Integración con `main` (F7-21).** Antes de la primera rama de la Fase 7: PR obligatorio
      `feat/u1-supply-engine` → `main`, revisado, integrado con un **merge commit normal** que conserva los
      commits de U1–U6 y sus hashes, citados en `project/status.md`. Sin *rebase*, sin *squash* y sin
      `force push`: excepción puntual a la preferencia de `docs/12` §2.2 por el historial lineal, salvo que el
      responsable decida formalmente actualizar las referencias y cambiar la política. Después, cada unidad
      de la Fase 7 en su propia rama `feature/frontend-<unidad>` desde `main` actualizado.
  22. **Formato regional (F7-22).** Locale **`es-MX`**; zona horaria de negocio **`America/Mexico_City`**
      (decisión del responsable, 2026-10-05). La API sigue en UTC; la conversión solo se hace al presentar.
      Las fechas sin hora (`as_of_date`, `period_start`…) se muestran sin conversión de zona; las marcas de
      tiempo (`generated_at`, `last_movement_at`, `started_at`…) se convierten de UTC a `America/Mexico_City`.
      Cifras sin `float`: se muestran el `display` del servidor o el texto exacto, **sin separador de miles**,
      para que coincidan carácter a carácter con la narrativa verificada de U6 (`DT-069`); el separador
      decimal de `es-MX` (`.`) coincide con el de la API. Una cifra que la API entrega sin `display`
      (p. ej. `raw_quantity` en la lista) se presenta con la misma regla de `DT-069` (6 decimales
      `ROUND_HALF_EVEN` sobre el texto, sin ceros finales), solo como presentación y nunca para decidir.
  23. **CORS (F7-23).** Proxy del servidor de desarrollo de Vite: el frontend llama a `/api` y el proxy lo
      reenvía a `127.0.0.1:8000`. FastAPI no cambia ni activa CORS en esta fase (cierra el aplazamiento de
      `DT-066` punto 11 para el desarrollo local). En el futuro (Fase 12): frontend estático + proxy inverso
      en el mismo origen `/api` (`docs/12` §3).
  24. **Partición (F7-24).** F7a — base, navegación, autenticación local y cliente de API (US-070) · F7b —
      productos e inventario (US-072) · F7c — recomendaciones, desglose y explicación (US-073, US-074,
      US-048) · F7d — predicciones e historial (US-075, RF-009). Cada unidad con su rama, su PR y su
      trazabilidad; ninguna mezcla trabajo de las Fases 5, 8, 10, 11, 12 o 13.
- **Contexto:** dossier de la Fase 7 (2026-10-05), veredicto «READY WITH CONDITIONS». `docs/08` §1–§10 se
  escribió para el sistema completo con Entra ID; `docs/08` §11 fijó las vistas V1 pero citaba una ruta de
  explicación ya obsoleta; `DT-066` aplazó CORS a la Fase 7; ningún documento fijaba el stack del frontend,
  la autenticación local de la interfaz ni el formato regional.
- **Alternativas:** token en `sessionStorage` o selector de identidades; CORS en FastAPI (cambia U5);
  servir la interfaz desde FastAPI; formatear el desglose en el cliente; TypeScript 6/7 (incompatible con
  el linter y el generador); *squash* o *rebase* para la integración (rompe los hashes citados).
- **Razón:** la interfaz V1 es un consumidor fiel de un contrato de solo lectura ya validado: no añade
  reglas, no toca el backend y deja cada pieza externa (Entra ID, CORS de producción, ML) detrás de una
  frontera que sus fases sustituyen.
- **Consecuencias:** U1–U6 no cambian. `docs/08` §12 registra las diferencias con §1–§10. Las Fases 8
  (`AuthProvider`), 12 (build estático, `/api` relativa) y 13 (lint, tipos y pruebas sin interacción)
  heredan estas decisiones.
- **Estado:** `ACEPTADA` (2026-10-05, decisión del responsable al autorizar la Fase 7). **Fase 7
  implementada e integrada en `main` el 2026-10-05** (PR #2 a #5; detalle en *Implementación*). Separada de `DT-047`, que cubre U1–U6. Siguen
  abiertas, sin bloquear la Fase 7: `DT-P16`, `DT-P11`, `DT-P13`, `DT-P23`, `BR-X03`, `DT-P08`, `DT-P07`,
  `DT-010`, `DT-011`, `DT-021`, `DT-P03` y `DT-P04`.

- **Implementación (2026-10-05):**
  1. ramas encadenadas (`feature/frontend-shell` → `products` → `recommendations` → `forecasts`) en lugar de salir cada una de `main` (punto 21), por decisión del responsable; se integraron en orden como PR #2 a #5 con merge commit normal (`44280ce`, `198df24`, `1ad2916`, `22f1805`), sin *squash* ni *rebase*.
  2. «cifras sin `float`» (puntos 8 y 22): única excepción `frontend/src/charts/chartValues.ts`, que convierte a número solo para la geometría del gráfico de Recharts (punto 20); tablas, ayudas emergentes y textos muestran el texto exacto de la API, y una prueba limita `Number()` a ese módulo.
  3. decisiones del responsable dentro de la Fase 7: detalle de producto por secciones (maestro, inventario y proveedores; evaluación del motor; predicción; historial para ANALYST, PLANNER y ADMIN) y `/inventario/:id` como vista propia con las líneas abiertas.
  4. `/inventory` y `/recommendations` no devuelven la unidad de medida: las listas lo dicen y los detalles la toman de `/products/{id}`.
  5. los enteros del contrato (identificadores, `page`, `total`, días) se tipan como `number`; solo las cantidades `Decimal` son texto. La regla `display` del cliente normaliza los enteros igual que `app.genai` (`-0` → `0`).
  6. validación en Node 24.21.0 y npm 11.19.0 sobre `main`: lint, `tsc`, Prettier, 148 pruebas (Vitest + Testing Library) y build; el paquete pesa 774 kB por Recharts (carga diferida pendiente).

## DT-071 — Fase 5: alcance, partición F5a–F5d y puertas de decisión

- **Decisión:**
  1. **Alcance.** Fase 5 = predicción de demanda con ML **local** sobre el dataset 0.4.0 (`docs/05` §4–§12),
     sin Azure ML (Fase 6). Separada de `DT-047` (U1–U6) y de `DT-070` (Fase 7). No modifica U1, U3, U4, la API
     ni la interfaz salvo lo que una unidad autorizada diga expresamente.
  2. **Unidades:**
     - **F5a** — backtesting (`DT-075`), Nivel 1 (`DT-076`), segmentación (`DT-077`), suavizado exponencial
       simple (ampliación de US-050) y comparación de los baselines. Solo baselines: ningún modelo candidato.
     - **F5b** — simulador de Nivel 2 (`DT-080`, US-058) aplicado a los baselines.
     - **F5c** — modelos de los niveles 1 y 2 de `docs/05` §7 (ETS/Holt-Winters; Croston, SBA y TSB), estudio de
       `DT-011` (`DT-081`) e intervalos (`DT-082`, US-055).
     - **F5d** — estudio de `DT-010` (`DT-083`) y, solo si un modelo cumple los criterios, promoción e integración
       tras `ForecastProvider` (`DT-084`, US-054, US-057).
  3. **Dependencias:** F5b necesita F5a (cortes, baselines, Nivel 1); F5c necesita F5a, F5b y la puerta G1;
     F5d necesita F5c.
  4. **Puertas** (decisiones del responsable, registradas antes de seguir):
     - **G1** — tras F5a y F5b, **antes de evaluar ningún candidato de F5c** y sin tocar el *holdout*: métrica
       primaria (`DT-078`), valores de aceptación (`DT-079`), umbrales de segmentación (`DT-077`), baseline
       oficial (`docs/05` §6) y estimador de imputación (`DT-081`).
     - **G2** — al final de F5c/F5d: uso **único** del *holdout* (`DT-075`) con los criterios ya fijados.
     - **G3** — aprobación humana explícita de cualquier promoción (`DT-084`).
  5. **Niveles 3 y 4** de `docs/05` §7 (boosting, redes) quedan fuera de F5a–F5c y requieren una decisión
     posterior específica (`DT-073`).
- **Contexto:** dossier de la Fase 5 (2026-10-05, «READY WITH CONDITIONS»), corregido por el responsable.
- **Alternativas:** una sola unidad con modelos y simulador a la vez; empezar por los modelos.
- **Razón:** el instrumento que decide (Nivel 2) existe antes que cualquier modelo productivo, y las reglas de
  evaluación se fijan antes de ver candidatos.
- **Estado:** `ACEPTADA` (2026-10-05) en cuanto a partición, dependencias y puertas. **La Fase 5 no está
  autorizada para implementación**, salvo **F5a**, autorizada por separado en `DT-086`: el resto depende de las
  decisiones que se enumeran en `docs/05` §20.4.
- **Nota (2026-10-06):** **F5c autorizada** por `DT-092`, con los criterios complementarios de G1 de `DT-093`, registrados antes
  de evaluar ningún candidato. F5d, G2 y G3 siguen sin autorizar.

## DT-072 — Fase 5: ubicación del código

- **Decisión:** `ml/` (raíz del repositorio, `docs/03` §16.2) contiene entrenamiento, evaluación, backtesting,
  simulación de Nivel 2 y experimentación controlada. Usa `app.forecasting` y `app.supply_engine` como
  bibliotecas y lee los datos en solo lectura; **no** persiste resultados en las tablas de producción. Un modelo
  promovido se integra después en `backend/app/forecasting/` tras `ForecastProvider` (`DT-046`), nunca en U1 ni
  en U4.
- **Estado:** `ACEPTADA` (2026-10-05).

## DT-073 — Fase 5: dependencias y versionado

- **Decisión:**
  1. F5a–F5c usan **solo la biblioteca estándar** de Python ≥ 3.11. No se instalan numpy, pandas, statsmodels,
     scikit-learn ni MLflow, y `pyproject.toml` no cambia.
  2. El nivel 3 (boosting) exige una decisión nueva con dependencias y versiones fijadas.
  3. **Versionado:** `model_versions` (`docs/04` §3.13, esquema de `0002`) más informes reproducibles en
     `docs/reports/` (Markdown y JSON con `dataset_version`, commit, configuración y semillas). **Sin MLflow en
     la Fase 5**: `docs/03` §16 ya prevé entrenar en local y versionar a mano; el seguimiento con MLflow de
     `docs/05` §11 se aplaza a la Fase 6.
- **Estado:** `ACEPTADA` (2026-10-05).
- **Nota (2026-10-05, F5a; el texto anterior no cambia):** el JSON versionado en `docs/reports/` es un **resumen**:
  metadatos (dataset, versión de U1, commit, Python, semillas, comando y fecha), configuración, huella
  `results_sha256` y agregados entre cortes. Los datos por corte y por serie no se versionan: se regeneran de forma
  determinista en `ml/out/` (ignorado por Git) con el comando del informe, y la huella permite comprobarlo.

## DT-074 — Enmienda acotada de D-12 (`DT-056` punto 11): `float` solo dentro del componente ML

- **Decisión:**
  1. **La regla general no cambia.** U1, los baselines de U3, el contrato de `ForecastProvider`, la persistencia
     y la API siguen sin `float`: `Fraction` o `Decimal` exactos y salida con 6 decimales `ROUND_HALF_EVEN`.
  2. **Excepción, exclusivamente** (a) dentro de `ml/` y (b) dentro de un proveedor de modelo, experimental o
     promovido, en `backend/app/forecasting/`. No se extiende a ninguna otra unidad.
  3. **Frontera determinista:** `float` del modelo → `Decimal(x)` (conversión exacta del binario, nunca desde
     texto formateado) → cuantización a 6 decimales `ROUND_HALF_EVEN` → contrato de `ForecastProvider` y
     persistencia. Ningún `float` cruza la frontera ni se persiste como resultado contractual.
  4. La conversión **no corrige** valores: uno no finito o que viole el contrato (`predicted_quantity ≥ 0`,
     `lower ≤ predicted ≤ upper`) es un fallo de esa serie, que pasa al respaldo del baseline y lo declara
     (`RNF-010`). Cualquier recorte, por ejemplo a cero, tiene que formar parte declarada del método y de su versión.
  5. **Reproducibilidad:** mismo código, mismos datos, misma versión de Python y orden de operación fijo; semilla
     fija si hubiera aleatoriedad.
- **Estado:** `ACEPTADA` (2026-10-05). Enmienda **acotada** de D-12; los baselines de U3 permanecen exactos.

## DT-075 — Fase 5: protocolo de backtesting

- **Decisión:**
  1. **Semanas** ancladas como en U3 (`DT-046`): la semana `n` termina en `2025-12-31 − 7·(156 − n)`; hay 156
     semanas completas y se descartan los 4 días más antiguos.
  2. **17 cortes de desarrollo**, al final de las semanas 64, 68, …, 128 (`as_of` de 2024-03-27 a 2025-06-18),
     cada 4 semanas, con horizonte de **14 semanas**. El último corte evalúa hasta la semana 142 (2025-09-24).
  3. **Entrenamiento** en cada corte con toda la historia `≤ as_of` (ventana expansiva); todo ajuste de
     parámetros usa solo datos `≤ as_of`.
  4. **Holdout final:** corte 2025-09-24, que evalúa las semanas 143–156 (hasta 2025-12-31). Se usa **una sola
     vez**, en G2. **Prohibido** usarlo para elegir hiperparámetros, modelos, métrica, intervalos o umbrales.
  5. **«Gap»** (aclara `docs/05` §8 regla 2): no se eliminan semanas entre entrenamiento y evaluación. Cada
     horizonte `h` se evalúa directamente contra la semana real `as_of + h`, y ninguna información posterior
     al corte entra en el cálculo.
  6. **Población por corte:** la que U3 consideraría (activos y vigentes, historia contigua, `DT-056` D-11). Si
     a un método le falta historia, se usa la cadena de respaldo de U3 y se informa aparte.
- **Estado:** `ACEPTADA` (2026-10-05).
- **Nota (2026-10-05, `DT-087`):** el punto 6 se interpreta «a la fecha» del corte: vigencia en `as_of` sin
  `is_active`, que es una foto del final del dataset. La regla literal de U3 queda como alternativa comparada.
- **Nota (2026-10-05):** el entrenamiento y la evaluación de un mismo corte no se solapan; las ventanas de evaluación
  de cortes consecutivos sí (14 semanas cada 4). Ver la nota de `DT-079`.

## DT-076 — Fase 5: evaluación de Nivel 1

- **Decisión:**
  1. **Métricas** de `docs/05` §9.1: MAE, RMSE, MASE, RMSSE, WAPE, sesgo con signo y cobertura del intervalo;
     MAPE solo informativa (`DT-021`).
  2. **Verdad:** el consumo observado agregado a semanas ancladas, que es lo único disponible con datos REAL. La
     comparación contra la demanda latente es exclusiva del estudio de `DT-011` (`DT-081`; `docs/05` §19.6).
     *Aclaración (2026-10-05, decisión del responsable):* aunque el entrenamiento use días excluidos o imputados
     (estrategias (b) y (c) de `DT-081`), la verdad de evaluación **nunca** es un valor imputado. El consumo
     observado es una cota inferior en los días con desabasto (observación censurada), por lo que el Nivel 1 se
     informa sobre todas las semanas y, por separado, sobre las semanas sin ningún día con desabasto. La
     comparación contra la demanda latente solo es posible con datos `SYNTHETIC`.
  3. **Horizontes:** `h = 1` y el horizonte de protección `L + R` días por producto (`L` = lead time que U1
     usaría en ese corte, `R = 7`). La demanda prevista en ese intervalo se obtiene con
     `supply_engine.rules.demand_over_horizon` (`DT-019`, función única), y la real es el consumo de esos días.
  4. **Escala de MASE y RMSSE:** error medio (absoluto o cuadrático) del naïve a un paso dentro del
     entrenamiento de cada corte.
  5. **Reporte:** por corte; agregado con su dispersión (desviación entre cortes, mínimo y máximo); por segmento
     (`DT-077`); y siempre junto al baseline.
  6. El **baseline oficial** (`docs/05` §6) se elige en G1 con la métrica primaria, no antes.
  7. **Suavizado exponencial simple** (ampliación de US-050): `α` elegido en una rejilla 0,05–0,95 con paso 0,05,
     minimizando el error cuadrático a un paso dentro del entrenamiento del corte; intervalo con la regla
     nearest-rank de `DT-056`.
- **Estado:** `ACEPTADA` (2026-10-05) en los puntos 1–6. El punto 7 es `PROPUESTA` y se confirma al revisar F5a.

## DT-077 — Fase 5: segmentación del catálogo (US-051)

- **Decisión propuesta:**
  - **Rasgos por serie**, solo con datos `≤ as_of`: ADI, CV² de las semanas no nulas, proporción de ceros,
    longitud y estado del producto.
  - **Umbrales:** ADI ≥ 1,32 → intermitente o irregular; CV² ≥ 0,49 → errático o irregular (Syntetos-Boylan).
  - **Nuevo o histórico corto:** menos semanas que el mínimo del método (25, `DT-056`).
  - **Descontinuado:** inactivo o fuera de vigencia (`DT-056` D-11).
- **Estacional:** no hay criterio documentado. Queda `OPEN`.
- **Contexto:** `docs/05` §4 aplaza los umbrales «a los datos». Medición del 2026-10-05 sobre el dataset
  0.4.0 con esos umbrales: 80 series suaves, 19 intermitentes y 1 irregular (orientativo, `SYNTHETIC`).
- **Estado:** `PROPUESTA` — **`OPEN` hasta G1**. F5a calcula los rasgos e informa la clasificación propuesta,
  marcada como provisional.
- **Nota (2026-10-05, revisión de F5a):** el «19 intermitentes» de la medición orientativa era un artefacto: contaba
  como cero las semanas posteriores a `valid_to` de los 5 productos descontinuados, que mientras están vigentes son
  suaves (`DT-087`). La segmentación definitiva se calcula sobre la vida activa de cada serie, con datos `≤ as_of`;
  en los cortes de F5a resultan 85 suaves, 14 intermitentes y 1 irregular mientras esos 5 están vigentes.
- **Nota (2026-10-05, G1; el estado no cambia):** G1 no fija los umbrales ni el criterio de estacionalidad, que
  pertenecen a F5c (`DT-089` punto 3). La clasificación provisional de F5a se usa para informar y para el criterio
  por segmento de `DT-091`.
- **Nota (2026-10-06, F5c):** umbrales y criterio de estacionalidad fijados para F5c en `DT-093` punto 7 (provisionales,
  `SYNTHETIC`). Esta DT no cambia de texto.

## DT-078 — Fase 5: regla de fijación de la métrica primaria (`DT-021`)

- **Decisión:**
  1. La métrica primaria se fija en **G1**: después de F5a y F5b (solo baselines), **antes** de evaluar ningún
     candidato de F5c y antes del *holdout*.
  2. **Candidatas:** MASE, RMSSE y WAPE agregada (`DT-021`).
  3. **Evidencia admisible en G1:** la composición del catálogo (`DT-077`), el comportamiento de las tres
     métricas sobre los baselines en los 17 cortes y su alineación con el Nivel 2 entre variantes de baseline
     (F5b). El Nivel 2 **valida** la alineación; no permite cambiar la métrica después.
  4. Una vez fijada, la métrica **no se cambia** por resultados de candidatos ni del *holdout*. Un cambio exige
     una DT nueva y repetir la evaluación completa.
  5. **Criterio a nivel serie-corte** (añadido por el responsable el 2026-10-05: con 3 o 4 baselines, Spearman
     entre modelos resuelve poco). Para cada par de variantes de baseline y cada par (serie, corte) se comprueba
     si la métrica candidata y el Nivel 2 de esa serie en las 14 semanas siguientes al corte prefieren la misma
     variante. Se informa la proporción de acuerdos, sin contar los empates, junto al Spearman entre modelos. El
     indicador de Nivel 2 por serie es **`PROPUESTA`**: las unidades faltantes (demanda perdida) de la serie en esa
     ventana (OD-S3).
- **Razón:** evita elegir la métrica según convenga después de ver los resultados (`docs/05` §9, RML-005).
- **Estado:** `ACEPTADA` (2026-10-05) como procedimiento. **`DT-021` sigue `PENDIENTE` (`OPEN`)**: esta decisión
  fija cuándo y cómo se elige, no cuál.
- **Nota (2026-10-05, F5b):** en cada horizonte cada serie-corte tiene un único error agregado, y la escala de MASE y
  RMSSE es la misma para todas las variantes de esa serie-corte; por eso MASE, RMSSE y WAPE ordenan las variantes
  igual **por construcción**, y el criterio serie-corte del punto 5 no puede discriminar entre ellas (no es un
  hallazgo de los datos). La elección entre las candidatas se apoya en el resto de la evidencia del punto 3.
- **Nota (2026-10-06, F5c):** desde F5c el cruce informativo se informa con tolerancia de inventario 0 y +5 % (`DT-093`
  punto 4).

## DT-079 — Fase 5: criterios de aceptación de un modelo (`DT-P04`)

- **Decisión:**
  1. **Estructura** (`docs/05` §10, `DT-020`): Nivel 1 mejora en la métrica primaria y Nivel 2 no se degrada →
     candidato. Si el Nivel 1 mejora pero el Nivel 2 no, el modelo **no se promueve** y se documenta.
  2. **Valores propuestos**, provisionales para el dataset `SYNTHETIC` y a revalidar con datos REAL:
     - (a) mejora en el agregado de los 17 cortes y en al menos 2/3 de ellos (≥ 12 de 17);
     - (b) ningún segmento empeora más de un **5 %** relativo en la métrica primaria;
     - (c) Nivel 2 igual o mejor que el baseline en tasa de desabasto y nivel de servicio.
  3. **Sin propuesta respaldada:** la banda de sesgo admisible (`docs/05` §10, criterio 3), la tolerancia de
     cobertura del intervalo (criterio 4) y la tolerancia de «igual» en el Nivel 2.
- **Estado:** punto 1 `ACEPTADA` (2026-10-05). Puntos 2 y 3 son `PROPUESTA` y **`OPEN` hasta G1**. **El 5 % no
  está aceptado**: requiere la aprobación expresa del responsable. `DT-P04` sigue abierta.
- **Nota (2026-10-05, revisión de F5a; el estado no cambia):** las ventanas de evaluación de cortes consecutivos se
  solapan (14 semanas cada 4, `DT-075`), así que los 17 cortes **no** son observaciones independientes. La regla de
  «al menos 2/3 de los cortes» del punto 2 (a) no constituye evidencia independiente: cuenta cortes que comparten
  semanas evaluadas. Se tendrá en cuenta al fijar los valores en G1.
- **Nota (2026-10-05, G1):** el responsable fija valores provisionales en `DT-091`:
  - 5 % por segmento, con un mínimo de 10 productos para bloquear;
  - mejora en el agregado y en 2/3 de los cortes comparables;
  - inventario +5 %;
  - «igual» con unidades faltantes no peores en más del 2 % y *fill rate* no peor en más de 0,2 puntos.

  La banda de sesgo y la tolerancia de cobertura siguen sin valor.
- **Nota (2026-10-06, F5c):** la banda de sesgo y la tolerancia de cobertura quedan fijadas en `DT-093` puntos 5 y 6; los
  cortes comparables, en el punto 3.

## DT-080 — Fase 5: simulador de Nivel 2 (protocolo mínimo reproducible)

- **Decisión** (puntos derivados de documentación aceptada):
  1. **Periodo de desarrollo:** del corte de la semana 64 (2024-03-27) al 2025-09-24. El tramo del *holdout*
     (2025-09-25 a 2025-12-31) solo se simula en G2.
  2. **Frecuencia:** una decisión cada 7 días (`R = 7`, `V1-03`) en cada `as_of` semanal, después del consumo
     del día (orden diario de `DT-038`).
  3. **Forecast por rama:** el de su método, con ese `as_of` y 14 semanas (`DT-046`). La rama de referencia usa
     el baseline de referencia vigente.
  4. **Motor:** U1 V1 **sin cambios**, la misma `engine_version` y la política `V1_PROVISIONAL` en ambas ramas.
     **Lo único que cambia es el forecast** (`docs/05` §9.5).
  5. **Estado inicial** en el primer corte, reconstruido sin inventar nada:
     - `on_hand` = suma de los movimientos con `occurred_at ≤ t` (`DT-038`);
     - `reserved = 0` (el dataset 0.4.0 no tiene reservas);
     - líneas abiertas con las reglas del adaptador de U4 (`docs/06` §16.13.2);
     - observaciones de lead time anteriores al corte.
  6. **Día simulado** (orden de `DT-038`):
     - recepciones del día;
     - demanda latente del día (`demand.csv`);
     - consumo simulado = mín(disponible, demanda);
     - **demanda perdida** = demanda − consumo (glosario; ventas perdidas, sin pedidos pendientes);
     - si es día de revisión, decisión.
     El inventario nunca es negativo (`V1-13`). El simulador distingue la demanda latente (verdad de
     simulación) del consumo observado (histórico).
  7. **Líneas abiertas históricas** al primer corte: se reciben en su `expected_on` (regla del adaptador), igual
     en ambas ramas.
  8. **Demanda latente:** solo verdad de simulación; nunca entrada del forecast ni del motor (`DT-034`,
     `docs/05` §19.6).
  9. **Métricas** de `docs/05` §9.4, en unidades:
     - tasa de desabasto;
     - nivel de servicio (demanda satisfecha ÷ demanda total) y proporción de ciclos sin agotamiento, con ciclo
       = periodo de revisión de 7 días;
     - inventario medio en unidades y en valor (`unit_cost` del proveedor preferente);
     - rotación.
     **Sin costes** de inventario ni de faltante mientras `BR-X04` siga abierta. El Nivel 2 mide la calidad de
     la decisión, no el error del forecast.
  10. **Determinismo y pruebas:** sin aleatoriedad, salvo lo que fije OD-S2; dos ejecuciones dan el mismo
      resultado; pruebas de `docs/13` §6.1, incluida la de sensibilidad.
- **Decisiones materiales** (`PROPUESTA` del responsable, 2026-10-05, **pendientes de su confirmación**, antes de F5b):
  - **OD-S1 — Historia que ven el forecast y el motor:** **bucle cerrado**. Cada rama ve su propio consumo simulado
    desde el primer corte (y el observado antes de él), de modo que su forecast y su `σ` (`V1-05`) reflejan sus
    propios desabastos. *(El dossier recomendaba el bucle abierto.)*
  - **OD-S2 — Órdenes simuladas:** se colocan en `suggested_order_date` y llegan tras el lead time realizado, igual
    en ambas ramas. Mientras no llegan, cuentan como tránsito en las decisiones siguientes. Sin cancelaciones ni
    entregas parciales.
  - **OD-S3 — Desabasto:** se mide **por día**; se agrega por semana solo para informar. Se añaden las **unidades
    faltantes** (demanda perdida) como métrica.
  - **OD-S4 — Exceso de inventario:** sin umbral absoluto. El **inventario medio en unidades, relativo al
    baseline**, actúa como restricción de no degradación.
- **Decisiones materiales aceptadas** (2026-10-05, decisión del responsable con `DT-088`; sustituyen a la
  `PROPUESTA` anterior):
  - **OD-S1 — Bucle cerrado.** Cada rama ve su propia historia simulada (consumo simulado y ventas perdidas) y su
    propio inventario. Estado inicial en el primer corte: `on_hand` reconstruido desde `inventory_movements`,
    `reserved = 0` y las órdenes reales abiertas a esa fecha como eventos exógenos, idénticos en todas las ramas.
    Las órdenes reales emitidas después del primer corte se descartan.
  - **OD-S2 — Órdenes simuladas.** Una decisión cada 7 días, después del consumo del día (orden de `DT-038`). Cada
    recomendación `RECOMMEND` coloca una orden en su `suggested_order_date` (la fecha de decisión, como en U4) que
    llega tras `lead_time_used_days`, el `L` que el propio motor usó en esa recomendación; igual regla en todas las
    ramas. Sin cancelaciones ni entregas parciales; cuenta como tránsito en las decisiones siguientes. Esto aísla
    el efecto del forecast, pero **no mide la variabilidad del proveedor**, y el informe lo declara.
  - **OD-S3 — Desabasto.** Demanda de la simulación = demanda latente (`demand.csv`), solo con datos `SYNTHETIC`;
    ventas perdidas = demanda latente − consumo simulado; inventario nunca negativo. Día con desabasto = día con
    ventas perdidas > 0. Métricas en unidades: días con desabasto, unidades faltantes y nivel de servicio por
    unidades (*fill rate*), además de las del punto 9.
  - **OD-S4 — Inventario.** Sin umbral absoluto de exceso. Se informa el inventario medio (disponible al final del
    día, en unidades) por rama y relativo al baseline; la tolerancia de la restricción de no degradación sigue
    `OPEN` (G1, `DT-079`).
  - **Comunes:** U1 V1 sin cambios y la misma `engine_version` en todas las ramas; solo cambia el forecast. Cada
    decisión semanal recalcula el forecast con la historia simulada de la rama (cadencia configurable,
    provisional). Periodo: del primer corte (semana 64) al 2025-09-24, informado completo y sin las 8 primeras
    semanas de calentamiento (configurable, provisional). Población: vigencia al corte (`DT-087`); Nivel 2 solo
    para productos con `L + R` (proveedor preferente activo); las demás series se cuentan y se listan. Ramas: los
    cuatro baselines de F5a. Sin costes (`BR-X04`). `Decimal` exacto en la simulación y en la llamada a U1
    (`DT-074`); `float` solo dentro de los modelos y de las métricas.
- **Decisiones del responsable al cerrar F5b** (2026-10-05, `ACEPTADA`):
  1. **Órdenes reales abiertas al primer corte** (93 en el dataset 0.4.0): llegan en su `expected_on` (punto 7); las
     vencidas (`expected_on` anterior al corte) llegan el día siguiente al corte. La alternativa con las recepciones
     reales (`python -m ml simulate --open-lines ACTUAL_RECEIPTS`) queda configurable. La redacción «llegadas reales»
     de OD-S1 era imprecisa: la regla es determinista, no usa información posterior al corte y es igual en todas las
     ramas.
  2. A U1 se le pasa `is_active = True` y la vigencia decide (`DT-087`).
  3. Las observaciones de lead time son solo las de órdenes reales emitidas hasta el primer corte; las órdenes
     simuladas no generan observaciones, lo que evita la circularidad con `lead_time_used_days`.
  4. Quedan aceptados como **provisionales**: recálculo semanal del forecast, 8 semanas de calentamiento,
     tolerancia de inventario 0 en el cruce informativo de `DT-078`, segmento fijado al primer corte y SES marcado
     como `MODEL` ante U1.
- **Estado:** puntos 1–10 `ACEPTADA` (2026-10-05). OD-S1 a OD-S4 **`ACEPTADA`** (2026-10-05, `DT-088`), con los
  refinamientos anteriores y las decisiones de cierre de F5b.
- **Nota (2026-10-06, F5c; cambio provisional):** para los modelos de F5c los parámetros se reoptimizan cada 4 decisiones
  semanales y el estado se actualiza cada semana (`DT-093` punto 9). Una rama sin modelo elegible usa el baseline
  oficial y se cuenta (`DT-093` punto 11).

## DT-081 — Fase 5: protocolo del estudio de `DT-011` (desabasto)

- **Decisión:**
  1. **Estrategias:** (a) consumo tal cual (lo actual, `DT-056` D-10); (b) excluir del entrenamiento los días con
     desabasto; (c) imputar la demanda de esos días. La alternativa (d) de `DT-011` (observación censurada)
     **no se evalúa en la Fase 5**.
  2. Las tres se evalúan con el mismo backtesting (`DT-075`), la misma simulación (`DT-080`) y los mismos modelos.
  3. **Medición:**
     - Nivel 1 contra el consumo observado y, **solo en este estudio**, contra la demanda latente, con la
       aclaración de `DT-076` punto 2: los días imputados o excluidos solo cambian el entrenamiento, nunca la
       verdad; el consumo observado se informa también sin las semanas con desabasto, porque es censurado;
     - Nivel 2;
     - por segmento;
     - robustez (estabilidad entre cortes).
  4. **La demanda latente es solo verdad de evaluación**, nunca entrada. Con datos REAL no existe y el estudio no
     podrá repetirse del mismo modo.
  5. El resultado es una **recomendación**; la decisión queda trazada en `DT-011`.
- **Abiertos:** el estimador de imputación de (c) y la agregación semanal de (b) cuando se excluyen días.
- **Estado:** puntos 1–5 `ACEPTADA` (2026-10-05). Los dos abiertos son **`OPEN` hasta G1**. `DT-011` sigue
  `PENDIENTE`.
- **Nota (2026-10-05, G1; el estado no cambia):** G1 no fija los dos abiertos, que pertenecen a F5c (`DT-089`
  punto 3).
- **Nota (2026-10-06, F5c):** estimadores provisionales de (b) y (c) y tratamiento del desabasto extremo en `DT-093`
  punto 8.
- **Nota (2026-10-06, revisión de F5c; el estado no cambia):**
  - **Conclusión provisional** (solo `SYNTHETIC`): las estrategias (b) y (c) reducen las unidades faltantes entre un
    15 % y un 24 % en los modelos estudiados, con un inventario medio entre un 1,7 % y un 2,1 % mayor.
  - Adoptar una en producción exige una unidad propia que cambie U3 y una DT nueva.
  - **PROPUESTA del desarrollador** (pendiente de decisión del responsable): preferir (b). La diferencia con (c) está
    dentro del ruido, (b) no necesita un estimador con parámetros propios y la API ya expone `days_observed` y
    `stockout_days`.
  - Detalle en `docs/05` §20.6 y §20.7.

## DT-082 — Fase 5: intervalos (US-055)

- **Decisión:**
  1. El nivel nominal se mantiene en 0,80 (`DT-056` D-03).
  2. Se compara el intervalo actual (nearest-rank 10/90 del error por horizonte) con una variante calibrada por
     horizonte cuyos parámetros se ajustan solo con errores de cortes anteriores a cada `as_of`.
  3. La cobertura se mide en los 17 cortes, por horizonte y por segmento. El *holdout* solo en G2: no se
     promueve una calibración porque mejore el *holdout*.
  4. La tolerancia de cobertura es parte de `DT-079` (`OPEN`).
- **Estado:** `ACEPTADA` (2026-10-05).
- **Nota (2026-10-06, F5c):** tolerancia de cobertura de 0,75 a 0,85 por horizonte, medida en los cortes tardíos; decide
  el rótulo de la banda, no la promoción (`DT-093` punto 6).

## DT-083 — Fase 5: estudio de `DT-010` (stock de seguridad) en simulación

- **Decisión:**
  1. Las alternativas (a)–(e) de `DT-010` se comparan solo dentro de `ml/`, en la simulación de Nivel 2, con las
     funciones públicas de U1 y **sin modificar U1** ni duplicar sus fórmulas. Si alguna no puede componerse sin
     tocar U1, se detiene y se pide una decisión.
  2. Si una alternativa gana, **U1 no cambia en la Fase 5**: el cambio es una unidad posterior separada (nueva
     `engine_version`, autorización y pruebas).
- **Verificación de U1 (2026-10-05, pedida por el responsable):**
  - `supply_engine.evaluate()` aplica solo `V1-05`: `SS = z·σ_H`, donde `σ_H` es la desviación poblacional de
    las ventanas de `H` días de consumo. Equivale a la alternativa (a) de `DT-010` aplicada al horizonte. No
    admite otra fuente de incertidumbre.
  - (c), el error acumulado del backtesting, podría expresarse con las funciones públicas
    `rules.sigma_components` y `rules.safety_stock_components`, pero **no hay forma de inyectarla** en
    `evaluate()`.
  - (d), los cuantiles empíricos, **no está expuesta**.
  - Recomponer la decisión fuera de `evaluate()` duplicaría la orquestación de `engine.py`, lo que el punto 1
    prohíbe.
- **Bloqueo previo al estudio de `DT-010`:** para comparar (c) y (d) hace falta una decisión: una variante de U1
  con entrada de incertidumbre (nueva `engine_version`, autorización y pruebas) u otra vía que el responsable
  apruebe. No afecta a F5a, F5b ni F5c.
- **Estado:** `ACEPTADA` (2026-10-05). `DT-010` sigue `PENDIENTE DE VALIDACIÓN`.

## DT-084 — Fase 5: promoción, estados de `model_versions` y respaldo

- **Decisión:**
  1. **Estados** con el esquema actual (`0002`): `status` ∈ {`TRAINING`, `EVALUATED`, `PRODUCTION`, `ARCHIVED`,
     `REJECTED`}, y `NULL` solo en los baselines (`model_versions_baseline_status_ck`). **No se crea la
     migración `0004`.**
  2. **Transiciones:** `TRAINING` → `EVALUATED` → (`PRODUCTION` | `REJECTED`); `PRODUCTION` → `ARCHIVED`.
  3. **«Como máximo un modelo en `PRODUCTION`»** (`docs/05` §13) lo garantiza la promoción, en una transacción;
     una restricción en la base exigiría una migración y una decisión aparte.
  4. **Promoción:** requiere G2 (criterios de `DT-079` cumplidos en los cortes y confirmados en el *holdout* de
     uso único) y **aprobación humana explícita** (G3). Nunca es automática.
  5. **Integración:** proveedor en `backend/app/forecasting/` tras `ForecastProvider`, con `method_used` `MODEL` o
     `INTERMITTENT_METHOD`, la frontera de `DT-074` y persistencia sin sobrescritura (US-057).
  6. **Respaldo:** sin modelo, o si falla una serie, se usa el baseline con `method_used = BASELINE`
     (`RNF-010`). El baseline es permanente.
  7. **Si ningún modelo gana:** no se promueve nada, sigue el baseline oficial de G1 y el resultado se documenta
     en `docs/reports/` como hallazgo válido.
  8. **Toda evidencia de la Fase 5 es `SYNTHETIC`** y debe revalidarse con datos REAL.
- **Estado:** `ACEPTADA` (2026-10-05).

## DT-085 — Fase 5: Git

- **Decisión:**
  - Rama corta por unidad desde `main` actualizado: `feature/ml-<unidad>`.
  - Un PR por unidad, con **merge commit** normal, sin *squash*, *rebase* ni *force push*.
  - No se reescribe historia publicada ni se desarrolla sobre ramas documentales.
  - Extiende a la Fase 5 la práctica de merge commit de `DT-070` punto 21; `docs/12` §2.2 lo registra.
- **Estado:** `ACEPTADA` (2026-10-05).

## DT-086 — Autorización de F5a

- **Decisión:** **F5a autorizada para implementación.** Comprende:
  - los baselines de U3, llamados desde U3 sin reimplementarlos;
  - el suavizado exponencial simple **provisional** (`DT-076` punto 7);
  - el backtesting (`DT-075`);
  - las métricas de Nivel 1 (`DT-076`);
  - la segmentación provisional (`DT-077`).
- **Límites:**
  - No elige el baseline oficial, la métrica primaria ni los umbrales de aceptación.
  - **No lee el *holdout*** (corte 2025-09-24 y su ventana).
  - No escribe en la base, no toca `backend/` ni `frontend/` y usa solo la biblioteca estándar.
  - Lo marcado `PROPUESTA` u `OPEN` se implementa configurable, con el valor propuesto y la etiqueta «provisional».
- **Sigue sin autorizar:** G1, OD-S1 a OD-S4 y el resto de la Fase 5 (F5b, F5c, F5d).
- **Estado:** `ACEPTADA` (2026-10-05, decisión del responsable).

## DT-087 — Fase 5: población por corte «a la fecha» (enmienda de interpretación de `DT-075` punto 6)

- **Contexto:** `DT-075` punto 6 fija la población de cada corte como «la que U3 consideraría (activos y vigentes)».
  U3 (`DT-056` punto 10) usa `is_active = true` y la vigencia en `as_of_date`. En el dataset, `products.is_active`
  es una foto del final del periodo publicado: no tiene historial. Aplicada a cortes pasados, excluye en los 17 cortes
  los 5 productos descontinuados el 2025-04-02 (21, 26, 37, 56 y 61), que en 14 de ellos estaban vigentes y
  consumían. Eso introduce información del futuro (se sabe en 2024 qué productos se descontinuarán en 2025) y
  sesgo de supervivencia (solo se evalúan las series que sobrevivieron).
- **Decisión:**
  1. En el backtesting de la Fase 5, la población de cada corte es la de los productos **vigentes en la fecha del
     corte** (`valid_from ≤ A ≤ valid_to`, o `valid_to` nulo), **sin** `is_active`. Es el valor por defecto de `ml/`.
  2. La **regla literal de U3** (`is_active` y vigencia) se conserva como alternativa configurable y cada ejecución
     la compara con la regla por defecto.
  3. El `is_active` de los **proveedores** tampoco tiene historial: no se infiere ni se reconstruye. Las series sin
     proveedor preferente activo quedan fuera del horizonte `L + R` (U1 se detendría antes de calcular `H`), se cuentan
     y se listan en el informe, y sí entran en las vistas de `h = 1`.
  4. U3 y U1 no cambian: esta decisión solo interpreta `DT-075` punto 6 para la evaluación retrospectiva.
- **Alternativa considerada:** la regla literal de U3 en todos los cortes. Se descarta como valor por defecto porque
  usa un dato posterior al corte, y se mantiene para cuantificar su efecto.
- **Razón:** información del futuro y sesgo de supervivencia (`CLAUDE.md` §10, regla 2; `docs/05` §8).
- **Consecuencias:**
  - En el dataset 0.4.0 la población pasa de 95 series en los 17 cortes a 100 hasta el corte 2025-03-26 y a 95
    desde el 2025-04-23. Mientras están vigentes, los 5 productos son «suaves».
  - La medición orientativa de `DT-077` (80 suaves, 19 intermitentes y 1 irregular) cuenta esos 5 productos como
    intermitentes. Ese resultado se reproduce si las semanas posteriores a `valid_to` cuentan como cero en el
    calendario de 156 semanas (ADI entre 1,33 y 1,37). En los cortes de F5a, con la historia hasta cada corte,
    la composición es 85 suaves, 14 intermitentes y 1 irregular, más 5 descontinuados desde abril de 2025.
  - El informe de F5a (`docs/reports/fase5-f5a-backtest-sintetico.md`) compara las dos reglas. Con datos
    `SYNTHETIC`, el efecto en las métricas medias es pequeño; no se usa para elegir modelo ni métrica.
  - Con datos REAL, la vigencia histórica pasa a ser un requisito de los datos maestros.
- **Estado:** `ACEPTADA` (2026-10-05, decisión del responsable en la revisión de F5a).

## DT-088 — Autorización de F5b

- **Decisión:** **F5b autorizada para implementación**: simulador de Nivel 2 (US-058, `DT-080`) aplicado a los
  cuatro baselines de F5a (naïve, naïve estacional, media móvil de 13 semanas y SES provisional). Cierra OD-S1 a
  OD-S4 con los refinamientos registrados en `DT-080`.
- **Límites:**
  - No elige el baseline oficial, la métrica primaria ni umbrales o tolerancias de aceptación.
  - **No lee el *holdout***: nada posterior al 2025-09-24 (consumo, demanda latente, movimientos ni órdenes).
  - No escribe en la base, no toca `backend/` ni `frontend/` y usa solo la biblioteca estándar.
  - Lo `PROPUESTA` u `OPEN` se implementa configurable, con el valor propuesto y la etiqueta «provisional».
- **Sigue sin autorizar:** G1, F5c, F5d y el resto de la Fase 5.
- **Estado:** `ACEPTADA` (2026-10-05, decisión del responsable).

## DT-089 — Fase 5: G1 — baseline oficial y candidato más fuerte

- **Decisión:**
  1. **Baseline oficial: media móvil de 13 semanas** (`k = 13`, `DT-056`), la que U3 calcula y la API sirve, en
     aritmética exacta. Es la elección de `docs/05` §6 y `DT-076` punto 6 (ampliación de US-050). Hasta ahora era
     solo la referencia operativa de V1 (`DT-056` D-01). Es la referencia contra la que se juzgarán los candidatos
     de F5c (`DT-079`, `DT-091`) y el respaldo permanente (`DT-084` punto 6).
  2. **SES** (`DT-076` punto 7) es el **candidato más fuerte observado y no se promueve**:
     - **Nivel 1:** mejor. MASE en `L + R` de 0,669 frente a 0,800; en `h = 1`, 0,886 frente a 0,983.
     - **Nivel 2:** dentro del ruido. Periodo completo: 3 860 frente a 3 882 unidades faltantes, los mismos 255
       días con desabasto e inventario medio relativo de 0,991. Sin las 8 semanas de calentamiento el orden de
       las unidades faltantes se invierte (1 180 frente a 1 166), y también en el segmento suave (3 364 frente a
       3 277).
     - **Para promoverlo** haría falta una unidad nueva con `float` en el proveedor (`DT-074`) y su respaldo al
       baseline (`DT-084` punto 6, `RNF-010`), además de G2 y G3.
  3. `DT-077` (umbrales de segmentación y criterio de estacionalidad) y `DT-081` (estimador de imputación y
     agregación de los días excluidos) **no cambian**: la estacionalidad y la imputación pertenecen a F5c.
- **Contexto:**
  - `DT-071` punto 4 asigna cinco decisiones a G1:
    - el baseline oficial, en esta DT;
    - la métrica primaria, en `DT-090`;
    - los valores de aceptación, en `DT-091`;
    - los umbrales de segmentación y el estimador de imputación, que quedan sin cambios.
  - Entre los tres baselines exactos de U3, la media móvil es la mejor en MASE de `L + R` (0,800; naïve 0,951,
    naïve estacional 1,292) y en unidades faltantes (3 882; 5 137 y 11 953). En `h = 1` empata en la práctica
    con el naïve (0,983 frente a 0,981).
  - Cifras completas en `docs/05` §20.5.
- **Razón:** es el baseline que el sistema ya sirve, en aritmética exacta y sin cambios de código. La mejora de
  Nivel 1 de SES no se traduce en una mejora de Nivel 2 distinguible del ruido (`docs/05` §10, `DT-079` punto 1).
- **Consecuencias:**
  - G1 no autoriza F5c ni F5d. Siguen pendientes de autorización y de las condiciones abiertas de `docs/05` §20.4.
  - G2 no se ha usado: el *holdout* sigue sin leerse.
- **Estado:** `ACEPTADA` (2026-10-05, decisión del responsable en G1, tomada en la revisión de F5b y formalizada con el
  envío del prompt de G1). **Provisional:** vale solo con datos `SYNTHETIC` y se revalida con datos REAL (`docs/05` §17).

## DT-090 — Fase 5: métrica primaria de pronóstico (`DT-021`) — MASE

- **Decisión:** la métrica primaria de Nivel 1 es **MASE**. Es una **decisión del responsable en G1**, no un
  desempate heredado de ningún documento.
- **Razón (del responsable):**
  1. Es independiente de la escala (criterio 2 de `DT-021`).
  2. Es estándar para series con ceros e intermitentes (criterio 1).
  3. La evidencia de F5a y F5b no permite distinguirla de RMSSE ni de WAPE por serie y corte. Cada serie-corte
     tiene un único error agregado por horizonte, así que las tres ordenan las variantes igual por construcción
     (nota de `DT-078`).
- **Alcance:**
  - Definición y escala de `DT-076` puntos 1 y 4, tal como las calcula F5a.
  - RMSSE, WAPE, sesgo y el resto de `docs/05` §9.1 se siguen informando como métricas complementarias.
  - MAPE sigue descartada como métrica de decisión (`DT-021`).
- **Consecuencias:**
  - `DT-021` queda cerrada con una nota que remite aquí.
  - El procedimiento de `DT-078` queda como referencia. Su punto 4 sigue vigente: la métrica no se cambia por
    resultados de candidatos ni del *holdout*, y cambiarla exige una DT nueva y repetir la evaluación completa.
- **Estado:** `ACEPTADA` (2026-10-05, decisión del responsable en G1, tomada en la revisión de F5b y formalizada con el
  envío del prompt de G1). **Provisional:** vale solo con datos `SYNTHETIC` y se revalida con datos REAL (`docs/05` §17).
- **Nota (2026-10-06):** MASE se juzga en `L + R`; `h = 1` es una vista secundaria informativa (`DT-093` punto 1).

## DT-091 — Fase 5: valores provisionales de aceptación (`DT-079`, `DT-P04`)

- **Decisión:** valores del punto 2 de `DT-079` y de la tolerancia de «igual» de su punto 3.
  1. **Segmentos:** ningún segmento empeora más de un **5 %** relativo en la métrica primaria (MASE, `DT-090`).
     - Solo bloquea un segmento con **al menos 10 productos**.
     - Uno menor (en F5a, el irregular, con 1 serie) se informa sin bloquear.
  2. **Agregado y cortes:** mejora en el agregado y en **al menos 2/3 de los cortes comparables**.
     - Los cortes se solapan y no son observaciones independientes (nota de `DT-079`).
     - El recuento indica consistencia; no es evidencia independiente.
  3. **Nivel 2, inventario:** el inventario medio admite como máximo un **+5 %** relativo al baseline (OD-S4,
     `DT-080`).
  4. **Nivel 2, «igual»:** las unidades faltantes no empeoran más de un **2 %** relativo y el *fill rate* no
     empeora más de **0,2 puntos** porcentuales (0,002 en proporción).
- **Siguen sin valor:**
  - la banda de sesgo admisible (`docs/05` §10, criterio 3);
  - la tolerancia de cobertura del intervalo (criterio 4, `DT-082`).

  Como `DT-071` punto 4 fija los criterios antes de evaluar candidatos, son condiciones abiertas para autorizar
  F5c (`docs/05` §20.4).
- **Alcance:**
  - Se aplican a los candidatos de F5c frente al baseline oficial (`DT-089`).
  - La tolerancia de inventario 0 del cruce informativo de `DT-078` (decisiones de cierre de F5b en `DT-080`) no
    cambia: es un parámetro de ese indicador, no un criterio de aceptación.
- **Estado:** `ACEPTADA` (2026-10-05, decisión del responsable en G1, tomada en la revisión de F5b y formalizada con el
  envío del prompt de G1). **Provisional:** vale solo con datos `SYNTHETIC` y se revalida con datos REAL (`docs/05` §17). `DT-P04` queda cerrada en estos valores; la banda de sesgo y la tolerancia de cobertura siguen
  abiertas.
- **Nota (2026-10-06):** «0,2 puntos» = 0,2 puntos porcentuales; cortes comparables, mínimo de 5 cortes y resultado no
  concluyente en `DT-093` puntos 2 y 3.

## DT-092 — Autorización de F5c

- **Decisión:** **F5c autorizada para implementación**:
  - modelos de los niveles 1–2 en `ml/`: Holt de tendencia aditiva, Holt-Winters aditivo, Croston, SBA y TSB;
  - solo biblioteca estándar, con `float` acotado a `ml/` (`DT-074`);
  - estudio de `DT-011` con las estrategias (a), (b) y (c) (`DT-081`);
  - medición y calibración de intervalos (US-055, `DT-082`).
- **Límites:**
  - Evalúa solo con los 17 cortes de backtesting de `DT-075` y el simulador de Nivel 2 de `DT-088`.
  - **No lee el *holdout*.**
  - No promueve ningún modelo.
  - No toca `backend/` ni `frontend/`.
- **Sigue sin autorizar:** `DT-010`, la unidad posterior de U1 (U1b, nombre provisional), F5d, G2 y G3.
- **Estado:** `ACEPTADA` (2026-10-06, decisión del responsable con el envío del prompt de F5c).
- **Implementación (2026-10-06, pendiente de revisión):** `ml/candidates.py` y `ml/f5c/`, con
  `python -m ml candidates`.
  - Informe `docs/reports/fase5-f5c-candidatos-sintetico.md`, `SYNTHETIC`; huella igual en Python 3.11 y 3.13.
  - Sin *holdout*, sin promoción y sin cambios en `backend/` ni `frontend/`.
  - La paridad con F5a y F5b está comprobada: sus archivos de detalle recalculados coinciden.
  - Resumen en `docs/05` §20.7. Ninguna decisión cambia.

## DT-093 — Fase 5: criterios complementarios de G1 para F5c

*Registrada antes de evaluar ningún candidato (`DT-071` punto 4). Todas las reglas son decisiones del
responsable, `ACEPTADA` y **provisionales**: valen solo con datos `SYNTHETIC` y se revalidan con datos REAL.*

- **Decisión:**
  1. **(a) Horizonte de la métrica primaria:** MASE (`DT-090`) en `L + R`; `h = 1` es una vista secundaria
     informativa.
  2. **(b) «0,2 puntos»** de `DT-091` = 0,2 puntos porcentuales (0,002 de *fill rate*).
  3. **(c) Cortes comparables** (`DT-091` punto 2):
     - son los del conjunto común de `DT-075`: todos los modelos comparados son elegibles y hay dato real completo;
     - se exige mejora en al menos 2/3 de ellos, redondeando hacia arriba, y un mínimo de 5 cortes;
     - con menos de 5 cortes comparables el resultado se declara **no concluyente**.
  4. **(d) Tolerancias de inventario:**
     - el +5 % de `DT-091` es el criterio de aceptación;
     - la tolerancia 0 queda solo en el cruce informativo de `DT-078`, que desde F5c también se informa con +5 %.
  5. **(e) Banda de sesgo** (`docs/05` §10, criterio 3): el sesgo relativo medio del candidato en `L + R` no sale de
     ±0,10 en el agregado. En cada segmento con al menos 10 productos no empeora en más de 0,05 respecto al baseline
     oficial.
  6. **(f) Cobertura de intervalos** (US-055, `DT-082`):
     - el nivel nominal sigue en 0,80;
     - el intervalo se considera calibrado si su cobertura empírica, por horizonte y medida en los cortes tardíos,
       queda entre 0,75 y 0,85;
     - no es criterio de promoción del punto: solo decide el rótulo de la banda.
  7. **(g) Segmentación** (`DT-077`):
     - Syntetos-Boylan con ADI 1,32 y CV² 0,49, calculada solo con datos de entrenamiento y sobre la vida activa de
       cada serie (`valid_from` a `valid_to`);
     - **estacionalidad:** la serie es estacional si tiene al menos 104 semanas de entrenamiento y la autocorrelación
       en el retardo 52 supera 1,96/√n (n = semanas de entrenamiento);
     - en F5c no hay selección automática de modelo por serie: cada modelo se evalúa sobre todas las series
       elegibles y se compara por segmento.
  8. **(h) Estimadores de `DT-081`:**
     - **(c) imputación:** cada día con desabasto se imputa con el consumo diario medio de los días sin desabasto de
       las 8 semanas anteriores; si en esa ventana no hay días sin desabasto, se deja el consumo tal cual;
     - **(b) exclusión:** se excluyen los días con desabasto; la demanda semanal se estima como consumo de los días
       observados × 7 / `days_observed`, y las semanas sin ningún día observado se omiten;
     - **desabasto extremo:** las series con más del 50 % de días con desabasto en el entrenamiento se informan
       aparte y no cuentan en la comparación de estrategias.
  9. **(i) Ajuste de modelos** (configurable):
     - rejillas de parámetros pequeñas, error cuadrático a un paso dentro del entrenamiento y desempate por el
       parámetro menor, como el SES de F5a;
     - los parámetros se reoptimizan en cada corte de backtesting y, en el simulador, cada 4 decisiones semanales,
       actualizando el estado cada semana;
     - esto **modifica de forma provisional** la cadencia de reentrenamiento de `DT-080` (nota en `DT-080`).
  10. **Holt-Winters** (periodo 52) solo es elegible con al menos 104 semanas de entrenamiento. Es un valor del
      responsable; `DT-075` no lo fija. Consecuencias:
      - en el backtesting solo entra en los cortes de las semanas 104 a 128 (7 de 17);
      - ninguna serie puede ser estacional antes de la semana 104.
  11. **Simulador sin modelo elegible:** cuando una rama no tiene pronóstico porque el modelo aún no es elegible
      (Holt-Winters antes de 104 semanas), usa en esa decisión los puntos del baseline oficial (media móvil de 13
      semanas, `DT-089`). La sustitución se cuenta y se informa, igual que la de un valor inválido.
- **Detalles de implementación:** los que estas reglas no fijan son `PROPUESTA` del agente, configurables y marcados
  «provisional». Se listan en el informe de F5c y quedan pendientes de confirmación.
- **Estado:** puntos 1–10 `ACEPTADA` (2026-10-06, decisión del responsable con el envío del prompt de F5c). Punto 11
  `ACEPTADA` (2026-10-06, conformidad del responsable con la propuesta del agente). **Provisional:** vale solo con
  datos `SYNTHETIC` y se revalida con datos REAL (`docs/05` §17).
- **Ampliación (2026-10-06, revisión de F5c; decisiones del responsable, `ACEPTADA` y provisionales, `SYNTHETIC`):**
  12. **Interpretaciones** que la primera versión dejaba como `PROPUESTA` del agente:
      - (a) los cortes comparables se toman por par, cada modelo frente a la media móvil 13;
      - (b) el tamaño de un segmento es la media de series por corte comparable;
      - (c) el sesgo se compara en valor absoluto;
      - (d) el Nivel 2 se juzga en el periodo completo, y el periodo sin calentamiento se informa;
      - (e) SES y los baselines conservan la cadencia de F5b y los candidatos reoptimizan cada 4 decisiones.
  13. **Sensibilidad de cadencia** (reproducible, en el mismo comando del informe; huella del detalle `28ce7c4f…`):
      con reoptimización semanal, TSB queda en 3 973 unidades faltantes, Croston en 4 025 y Holt en 5 658, frente a
      3 882 de la media móvil 13. Ninguno cumple el +2 %; la conclusión del punto 12 (e) no cambia.
  14. **Tabla de criterios:** incluye a SES (`DT-089`) y se calcula también bajo cada estrategia de `DT-081`, con la
      media móvil 13 bajo la misma estrategia como referencia; la sensibilidad del umbral de segmento se informa con
      9 y 11. SES cumple todos los criterios que deciden con (a); SES y TSB, con (b) y (c). Es un hecho del cálculo:
      no recomienda ni promueve nada (`DT-084`).

## DT-094 — Alcance de cierre de la Etapa 2: el stack completo, por unidades U7 a U16

- **Decisión:**
  1. **Alcance.** La Etapa 2 incluye las Fases 6 y 8 a 15: todo el stack de `docs/02` §12 (Azure Machine Learning,
     Azure OpenAI, Azure AI Search, Microsoft Entra ID, Power BI, Docker y GitHub Actions) está dentro del alcance.
     Queda sin efecto la clasificación de esos servicios como «posteriores al MVP» de la auditoría de cierre de alcance
     (2026-10-06), que no llegó a registrarse.
  2. **Base que no se pierde.** El sistema local (U1–U6 y la Fase 7) es la base. Ninguna integración puede quitar la
     ejecución completa en local, sin Azure y sin credenciales (RNF-006): cada servicio entra detrás de su puerto de
     `docs/03` §16.5 y conserva su implementación local.
  3. **Unidades y orden** (cada una con su propia autorización y sus criterios; esta decisión fija el alcance, **no
     autoriza** ninguna unidad):

     | Bloque | Unidad | Fase | Contenido |
     |---|---|---|---|
     | A — Base sin Azure | U7 | 12 | Imágenes, `docker compose` del sistema completo, healthchecks (`DT-095`) |
     | | U8 | 13 (CI) | Pipeline de GitHub Actions: suites existentes, detección de secretos, permisos mínimos |
     | | U9 | 11 (datos) | Vistas analíticas en PostgreSQL, rol de solo lectura, migración `0004` |
     | B — Base de Azure | U10 | 6, 8 y 13 | Grupo de recursos, región, etiquetas, presupuesto y alerta, Key Vault (`DT-022`), federación OIDC para GitHub, en Bicep |
     | | U11 | 8 | Entra ID: registros de aplicación, app roles, MSAL, validación de tokens, `APP_ENV=dev` |
     | C — Despliegue | U12 | 13 (CD) | Destino de cómputo (`DT-P01`), PostgreSQL gestionado, registro de imágenes, despliegue a `dev` por OIDC |
     | D — Servicios | U13 | 10 | Azure OpenAI tras `TextGenerator`, con la verificación de cifras y la degradación a la plantilla |
     | | U14 | 6 | Azure ML: workspace, *command job* sobre `ml/` sin cambios, MLflow, registro versionado de la media móvil 13 |
     | | U15 | 9 | Azure AI Search con corpus sintético (punto 7) |
     | | U16 | 11 | Power BI: modelo dimensional, cinco informes, `DT-014`, `DT-P10` |
     | E — Cierre | — | 14 y 15 | QA integral y entrega |
  4. **Suscripción y gasto.** Azure for Students con 100 USD de crédito; **presupuesto de planificación: 50 USD**, con
     el objetivo de quedar bastante por debajo. Un presupuesto de Azure alerta; **no apaga** nada salvo que exista una
     automatización explícita y segura. Cada unidad de Azure declara qué recursos crea, si generan costo, el costo
     estimado, si tienen consumo continuo, cómo se desmontan y cómo se verifica que quedaron desmontados. No se activan
     cargas permanentes, entrenamiento, modelos generativos ni recursos premium sin una autorización explícita posterior.
  5. **Infraestructura como código: Bicep**, parametrizado al menos por `environment` (`dev`), región, nombre del
     proyecto, etiquetas, presupuesto e identificadores. Sin contraseñas, claves, secretos, tokens ni cadenas de
     conexión con secretos.
  6. **Región.** Se fija en U10 después de verificar en Microsoft Learn la disponibilidad de todos los servicios del
     stack, las restricciones regionales y el costo. Mexico Central es candidata inicial, no supuesta. No se
     despliega nada para descubrir disponibilidad.
  7. **`ASSUMPTION-008`: corpus sintético.** Documentos de demostración del dominio (políticas y procedimientos de
     abastecimiento, recepción e inventario, manuales ficticios, guía de uso, preguntas frecuentes) con metadato
     `source_type=SYNTHETIC`, que no inventan reglas de negocio contrarias a la documentación. Ningún documento real,
     personal ni confidencial.
  8. **Credenciales.** CI solo con OIDC; en ejecución, identidad administrada o Entra ID antes que claves; ningún
     secreto de larga vida en GitHub. El agente no pide, almacena, copia ni imprime credenciales; el aprovisionamiento
     real lo ejecuta el responsable con su propia sesión.
  9. **Límites de la Fase 5 que siguen vigentes:** la media móvil 13 sigue siendo el baseline oficial, sin cambios;
     no se promueve SES ni otro modelo; no se ejecutan G2, G3 ni F5d; la estrategia (b) de `DT-011` no se implementa
     sin autorización; `ml/` sigue con solo la biblioteca estándar y el SDK de Azure ML y MLflow viven fuera de `ml/`.
  10. **Clasificación documental:** MVP local funcional (sin Azure) · stack de Azure (servicios tras los puertos) ·
      experimental (F5c y otros estudios) · posterior (G2, G3 y promoción de modelos).
  11. **Unidad completada** = implementación, pruebas, integración funcionando, degradación cuando corresponda,
      documentación actualizada y evidencia reproducible. Escribir el código no basta.
- **Contexto:** la auditoría de cierre de alcance del 2026-10-06 clasificó los servicios de Azure como posteriores al
  MVP; el responsable la corrigió: `README.md` y el roadmap definen el stack y la Etapa 2 no se cierra sin él. El
  principio 4 del roadmap («Azure al final») ya se cumple: el sistema local está completo.
- **Alternativas:** Azure fuera del alcance (descartada por el responsable); Terraform u otra herramienta (descartada:
  necesita estado externo); documentos reales para RAG (descartada: no hay corpus autorizado).
- **Consecuencias:** `DT-P01`, `DT-P02`, `DT-P08`, `DT-P10`, `DT-014` y `DT-022` se cierran en la unidad que las
  necesita, no antes. Las restricciones de `CLAUDE.md` §17 «No configurar servicios reales de Azure» y «No crear
  credenciales» siguen vigentes hasta la autorización de U10, que debe levantarlas de forma explícita y acotada.
- **Estado:** `ACEPTADA` (2026-10-06, decisión del responsable con el prompt «Implementación de la Etapa 2 por bloques»).

## DT-095 — U7: contenedores y sistema local completo con Docker

- **Decisión:** **U7 autorizada** (Fase 12, bloque A de `DT-094`), sin Azure y sin credenciales. Objetivo: levantar el
  sistema completo en local con un solo comando, con PostgreSQL, API e interfaz `healthy` y los datos, el forecast y
  las recomendaciones cargados.
- **Contrato de implementación** (`PROPUESTA` del desarrollador, pendiente de revisión; detalle de uso en `docs/12` §3.4):
  1. **Imágenes** (`infra/docker/`, contexto de construcción en la raíz): `backend` (API V1 y procesos por lotes sobre
     la misma base, `docs/12` §3.1), `frontend` (build de React y nginx) y `dataset` (ejecuta el generador 0.4.0 **sin
     modificarlo** para publicar el dataset en un volumen; el sistema sigue consumiendo el contrato del dataset). La
     base de datos usa la imagen oficial de PostgreSQL.
  2. **Bases fijadas por versión exacta**, comprobadas contra `docker-library/official-images` el 2026-10-06:
     `python:3.11.17-slim-trixie` (Python 3.11, la línea con la que se validó el backend; `requires-python >= 3.11`),
     `node:24.21.0-trixie-slim` (la referencia de `DT-070`), `nginx:1.30.5-alpine` (línea estable) y
     `postgres:16.15-alpine3.24` (antes `16-alpine`, misma versión 16.15; `DT-055`). *(Al implementarse U7, sin digest:
     el registro no era accesible desde el entorno de verificación.)*
     **Digests** (2026-10-06, U8): el del índice multiplataforma de cada etiqueta, tomado de `docker-library/repo-info`
     (`repos/<imagen>/remote/<etiqueta>.md`), el repositorio de metadatos que publican los mantenedores de las imágenes
     oficiales. Quedan fijados en los Dockerfiles y en `infra/docker-compose.yml`:
     `python:3.11.17-slim-trixie@sha256:0dd364ba7e10242f07755449e3a3d0e35f9efd987952737b90def6709ab0c5ce`,
     `node:24.21.0-trixie-slim@sha256:173f125896c3b47ddf056734c7ea789d04595a6a08769a8f78e0df642781fb66`,
     `nginx:1.30.5-alpine@sha256:0985e772fb9f729e6fa0980da05fca5d9c468e870eed43071545afa9d2e27d94` y
     `postgres:16.15-alpine3.24@sha256:721873c34ceb9f8d8fc265984940dc982404c105f19ad51be9fdc5970a6080ea`.
     **Pendiente de verificación externa:** el entorno del agente no alcanza el registro y no ha descargado ninguna imagen
     por digest. La primera ejecución del job `docker` de CI (`DT-096`), o una construcción en Docker Desktop, los
     confirma; si alguno no existiera, la construcción falla en lugar de usar otra imagen.
  3. **Dependencias de Python** leídas de `backend/pyproject.toml` (grupos `db` y `api`, sin `test`), sin ninguna
     nueva. Las transitivas no están bloqueadas: el proyecto no tiene archivo de bloqueo (punto abierto).
  4. **nginx** como servidor estático y proxy inverso de `/api/` en el mismo origen (`DT-070` punto 23): sin CORS,
     usuario sin privilegios (uid 101), puerto 8080, PID y temporales en `/tmp`, rutas del navegador servidas por
     `index.html`.
  5. **Entrada de la API** `infra/docker/serve_api.py`: el mismo comportamiento que `python -m app.api` (rechazo fuera
     de `APP_ENV=local`, `LOG_LEVEL`), pero escucha en todas las interfaces **dentro** del contenedor. U5 no cambia:
     usa sus funciones públicas `load_settings` y `create_app`.
  6. **`infra/docker-compose.yml`**: `postgres` sin perfil (el uso de U2 no cambia) y `dataset`, `init`, `api` y
     `frontend` en el perfil `app`. Puertos solo en `127.0.0.1` (5432, 8000 y 8080); autenticación `trust`, sin
     contraseña. `init` encadena migraciones, ingesta, `forecast` y `recommend` con `RUN_AS_OF = 2025-12-31` (`DT-058`)
     y es idempotente (`ALREADY_LOADED`, `ALREADY_COMPUTED`). `api` toma de `.env.example` las identidades ficticias de
     `DT-065` y fija `APP_ENV=local`; cambiarlas exige un `infra/docker-compose.override.yml` local, ignorado por Git y pasado con un segundo `-f`.
  7. **Endurecimiento:** usuario sin privilegios en todas las imágenes finales, `HEALTHCHECK` en `backend` y
     `frontend` (`NONE` en `dataset`, de una sola ejecución), `.dockerignore` en forma de lista de permitidos (ningún
     `.env`, dato ni metadato de Git entra en el contexto), etiquetas OCI con versión y `VCS_REF`.
  8. **Pruebas:** `infra/tests/test_container_config.py` (14 comprobaciones estáticas, solo biblioteca estándar) e
     `infra/docker/smoke.py` (recorrido frontend → API → PostgreSQL por el mismo origen que el navegador).
- **Verificación (2026-10-06, pendiente de revisión).** El entorno del agente no alcanza ningún registro de
  contenedores, así que la composición se construyó y ejecutó con **imágenes base sustitutas** de la misma versión
  —Python 3.11.17, PostgreSQL 16.15, Node 24.19.0 con npm 11.19.0 y nginx 1.24—, preparadas solo para la verificación
  y fuera del repositorio, sobre una copia del árbol con fin de línea CRLF, como en Windows. Resultado:
  - `dataset` generó `ds-6c8ad65b4999`, el mismo que el publicado;
  - `init` aplicó `0001` a `0003`, cargó la carga 1, y el forecast y las recomendaciones dieron lo mismo que en la
    validación de U3 y U4: 3 990 filas y 1 330 primarias; 100 evaluaciones, con 50 `RECOMMEND`, 40 `NO_NEED` y
    10 `NOT_CALCULABLE`;
  - `postgres`, `api` y `frontend` quedaron `healthy`;
  - `smoke.py` pasó 8 de 8 comprobaciones;
  - la interfaz, recorrida en Chromium por `127.0.0.1:8080` con un token `dev-…`, mostró la lista y el detalle con la
    explicación, sin errores de consola;
  - un segundo `up` reutilizó el dataset y dio `ALREADY_LOADED` y `ALREADY_COMPUTED`;
  - `up -d` sin perfil sigue levantando solo PostgreSQL;
  - procesos sin root (uid 10001 y 101) e imágenes sin `.env` ni claves;
  - la API rechaza arrancar sin `APP_ENV` o con `APP_ENV=dev`.

  Además, la suite por defecto (353) y la de la API (56) siguen en verde: `backend/`, `frontend/`, `ml/` y el
  generador no cambian. **Falta la construcción con las imágenes oficiales** en la máquina del responsable o en el CI de U8.
- **Puntos abiertos:** confirmación de los digests contra el registro (punto 2; job `docker` de `DT-096`); bloqueo de
  dependencias transitivas; tamaño de las imágenes oficiales sin medir; aviso conocido de paquete de 774 kB de la
  interfaz (`docs/08`).
- **Estado:** autorización `ACEPTADA` (2026-10-06, decisión del responsable con el prompt «Implementación de la Etapa 2
  por bloques»); implementación pendiente de revisión.

## DT-096 — U8: integración continua con GitHub Actions

- **Decisión:** **U8 autorizada** (Fase 13, bloque A de `DT-094`): CI del repositorio completo sin Azure ni
  credenciales, y verificación de las imágenes oficiales de U7. No cubre U9, U10, Azure, despliegues ni cambios en
  U1–U6, `ml/` o el generador.
- **Decisiones del responsable para U8:** ningún linter de Python (ni Ruff, ni Black, ni otro; el proyecto no define
  uno y no es deuda bloqueante); el frontend conserva sus comprobaciones (ESLint, Prettier, `tsc`); Python 3.11.16 y
  Node 24.21.0 con npm 11.19.0.
- **Contrato de implementación** (`PROPUESTA` del desarrollador, pendiente de revisión; `docs/12` §4.5):
  1. **Un workflow**, `.github/workflows/ci.yml`, en `pull_request`, `push` a `main` y `workflow_dispatch`, con
     `concurrency` que cancela ejecuciones superadas de la misma rama. Runner `ubuntu-24.04`.
  2. **Permisos mínimos:** `contents: read` para todo el workflow; `actions/checkout` con
     `persist-credentials: false`; ningún secreto de GitHub, ninguna escritura, **sin OIDC** (llega con U10/U12).
  3. **Acciones oficiales fijadas por SHA de commit**, verificadas en la API de GitHub el 2026-10-06:
     `actions/checkout` v7.0.1 (`3d3c42e5aac5ba805825da76410c181273ba90b1`), `actions/setup-python` v7.0.0
     (`5fda3b95a4ea91299a34e894583c3862153e4b97`) y `actions/setup-node` v7.0.0
     (`820762786026740c76f36085b0efc47a31fe5020`). Python 3.11.16 figura en `actions/python-versions` para
     Ubuntu 24.04 x64; el job del frontend comprueba que npm sea 11.19.0.
  4. **Ocho jobs** independientes, cada uno con el comando oficial de su suite y sin fijar números de pruebas:

     | Job | Qué ejecuta |
     |---|---|
     | `secret-scan` | `python infra/ci/secret_scan.py` |
     | `ml` | publica el dataset; `PYTHONPATH=backend python -m unittest discover -s ml/tests -t .` |
     | `backend` | publica el dataset; suite por defecto **sin dependencias opcionales** (`backend/`: `discover -s tests -t .`) |
     | `api` | grupos `db`, `api` y `test`; `discover -s tests/api -t tests/api` |
     | `integration` | servicio PostgreSQL efímero; publica el dataset; `python -m app.db migrate`; `discover -s tests/db -t tests/db` |
     | `generator` | PyYAML; `discover -s data/synthetic/tests -t .` |
     | `frontend` | `npm ci`, ESLint, `tsc`, Prettier (`format:check`, ya definido en `package.json`), Vitest y build |
     | `docker` | pruebas estáticas de `infra/tests`; construcción de las imágenes de U7; `up` del perfil `app`; espera a `healthy`; `smoke.py`; registros si falla; `down -v` siempre |
  5. **Dataset:** los jobs que lo necesitan lo publican con el generador 0.4.0 sin modificarlo y comprueban
     `ds-6c8ad65b4999` en el manifiesto; nada se versiona.
  6. **Dependencias:** las del backend salen de `backend/pyproject.toml` con `infra/ci/backend_requirements.py`, que
     falla con un grupo desconocido o con una versión no fijada con `==`; PyYAML, de `data/synthetic/requirements.txt`;
     el frontend, de `package-lock.json` con `npm ci`. Caché solo de npm (`setup-node`, con clave en el lockfile); pip
     sin caché. Ninguna dependencia nueva en el proyecto. Las transitivas de Python siguen sin bloquear (punto abierto).
  7. **PostgreSQL de integración:** contenedor de servicio del job, `postgres:16.15-alpine3.24` por digest, con `trust`
     como en `DT-055` (sin contraseña); se destruye con el job.
  8. **Detección de secretos** con `infra/ci/secret_scan.py` (solo biblioteca estándar, 8 pruebas en
     `infra/tests/test_secret_scan.py`):
     - **qué revisa:** los archivos que Git confirmaría (versionados y no ignorados);
     - **archivos prohibidos**, espejo de `.gitignore`: `.env`, `.env.*` salvo `.env.example`, claves, certificados y
       archivos de credenciales;
     - **patrones:** claves privadas, credenciales de Azure (clave de cuenta de almacenamiento, `SharedAccessKey`,
       firma SAS, secreto de cliente de Entra ID, claves de servicio), tokens de GitHub, AWS, Google y Slack, JWT,
       cadenas de conexión con contraseña y asignaciones de secretos; los marcadores de documentación no cuentan;
     - **nunca imprime el valor encontrado.**

     Limitaciones: revisa el estado actual, no el historial de Git, y es heurístico. Se descartó gitleaks o
     trufflehog: binario o acción de terceros como dependencia nueva.
  9. **Job `docker`:** es la única verificación automática de U7 con las imágenes oficiales y sus digests. Reutiliza
     `infra/docker-compose.yml` y `smoke.py` sin duplicar lógica. Coste estimado: unos 3 a 5 minutos por ejecución, en
     paralelo con los demás jobs.
- **Defecto del repositorio encontrado, no corregido** (`backend/` queda fuera de U8):
  - **Síntoma:** la instalación documentada en `backend/pyproject.toml`, `pip install -e ".[db]"`, falla en un entorno
    limpio con setuptools actual: «Multiple top-level packages discovered in a flat-layout: ['db', 'app']».
  - **Impacto:** solo esa instrucción de instalación. Ni CI ni las imágenes dependen de ella.
  - **Corrección mínima propuesta** (requiere autorización): declarar el paquete en `backend/pyproject.toml`, por ejemplo
    `[tool.setuptools.packages.find]` con `include = ["app*"]`, o cambiar la instrucción documentada.
- **Verificación (2026-10-06):**
  - `actionlint` 1.7.12, con `shellcheck`: sin hallazgos.
  - Cada job se reprodujo en una copia limpia con fin de línea LF, como la que obtiene un checkout en Linux:
    - `ml`: 129 pruebas en verde;
    - `backend`: 353 en verde, sin dependencias opcionales y sin omitidas con el dataset publicado;
    - `api`: 56;
    - `integration`: migraciones aplicadas y 152 pruebas en verde contra un PostgreSQL 16.15 efímero;
    - `generator`: 582;
    - `frontend`: lint, `tsc`, Prettier, 148 pruebas y build;
    - `docker`: build, `healthy` y smoke 8/8;
    - detector de secretos: 0 hallazgos en el repositorio;
    - `infra/tests`: 22 pruebas (14 de contenedores y 8 del detector).
  - Los jobs de Python corrieron con Python 3.11.17 en la copia limpia; las suites del backend y de `infra/`, además, con
    3.11.16 en la máquina del responsable.
  - El frontend corrió con Node 24.19.0 y npm 11.19.0, la versión de Node disponible en el entorno.
  - El job `docker` usó imágenes base sustitutas sin digest, porque el entorno no alcanza el registro.
  - **No ejecutado:** una ejecución real en GitHub Actions, que confirmará también los digests de `DT-095`.
- **Estado:** autorización `ACEPTADA` (2026-10-06, decisión del responsable con el prompt «U8 CI + verificación final de
  U7»); implementación pendiente de revisión.

## DT-097 — U9: capa analítica de solo lectura en PostgreSQL (migración `0004`)

- **Decisión:** **U9 autorizada** (Fase 11, datos; bloque A de `DT-094`). Alcance: vistas analíticas, rol de solo
  lectura y migración `0004`. **Fuera de U9:** Power BI (Desktop o Service), RLS, publicación, Import o
  DirectQuery (`DT-014`, `DT-P10`) y todo lo de Azure. Esos puntos pertenecen a U16.
- **Contrato de implementación** (`PROPUESTA` del desarrollador, pendiente de revisión; catálogo en `docs/11` §10 y
  definiciones en `knowledge/glossary.md`, «Indicadores analíticos»):
  1. **Esquema propio `analytics`**, separado de las tablas operativas de `public`. Contiene 13 vistas simples, sin
     tablas ni vistas materializadas:
     - carga vigente: `data_load`;
     - seis dimensiones: `dim_date`, `dim_product`, `dim_category`, `dim_supplier`, `dim_location` y
       `dim_model_version`;
     - seis hechos: `fact_consumption`, `fact_inventory_current`, `fact_inventory_daily`,
       `fact_purchase_order_line`, `fact_forecast` y `fact_recommendation`.

     Son las del modelo en estrella de `docs/11` §3 que el dataset 0.4.0 permite calcular (`docs/11` §9).
  2. **Solo hechos y valores ya calculados.** Ninguna fórmula del motor se reimplementa (`docs/11` §1). Las lecturas
     que coinciden con U4 usan su misma regla: fecha esperada de la línea o de la cabecera, línea abierta, y
     observación de lead time = línea completamente recibida y fechada por su última recepción (V1-09). Los instantes
     se pasan a fecha en UTC (`docs/04` §9.7).
  3. **`fact_inventory_daily`** reconstruye la existencia al cierre de cada día como suma acumulada de los movimientos,
     la misma regla con la que la ingesta reconcilia `inventory`. El último día coincide con la instantánea en los
     100 pares del dataset.
  4. **Rol `analytics_reader`:**
     - sin `LOGIN`, `SUPERUSER`, `CREATEDB`, `CREATEROLE`, `REPLICATION` ni `BYPASSRLS`;
     - `CONNECT` sobre la base, `USAGE` sobre `analytics` y `SELECT` sobre sus vistas; nada sobre `public`;
     - privilegios por defecto en `analytics`: las vistas que añadan migraciones posteriores son legibles sin otro
       `GRANT`;
     - las vistas se ejecutan con los privilegios de su propietario, así que el rol no lee ninguna tabla.

     El rol es del clúster y se crea solo si no existe. La cuenta con la que se conecte Power BI se crea **fuera del
     repositorio**, con su secreto en el almacén (`DT-022`), como miembro del rol (U16).
  5. **Migración `0004_analytics_views.sql`** con el ejecutor existente: una transacción, sha en
     `schema_migrations`. Sin mecanismo de reversión, como `0001`–`0003`. El procedimiento del proyecto es una
     migración nueva; quitar la capa entera es `DROP SCHEMA analytics CASCADE`, sin tocar ninguna tabla.
- **Interpretaciones** (`PROPUESTA`; `docs/11` §4 no las fija):
  - **cumplimiento en tiempo:** por línea completamente recibida (última recepción ≤ fecha esperada), con la
    granularidad de V1-09, no por recepción;
  - **cumplimiento en cantidad:** Σ recibido ÷ Σ pedido en líneas de órdenes cerradas (`RECEIVED` o `CANCELLED`);
  - **«nivel de servicio alcanzado»** de `docs/11` §4.5 = tasa de satisfacción (*fill rate*) del glosario, solo con
    datos `SYNTHETIC`, porque usa la demanda latente.
- **Fuera de U9** (`docs/11` §9):
  - valor de inventario y capital inmovilizado: falta la regla de valoración;
  - cobertura: `DT-P19`;
  - productos críticos y sobreinventario: `BR-X03`;
  - recomendaciones abiertas, conversión y descarte: V1 no tiene resolución (`DT-059`);
  - inventario sin movimiento: N sin definir;
  - error, sesgo y cobertura del intervalo, y su evolución por versión: no hay observaciones después del único
    corte, y las métricas de la Fase 5 viven en `ml/`;
  - concentración de proveedor, compras urgentes e impacto en el stock de seguridad: sin definición operativa.

  Quedan para U16 con su decisión.
- **Consecuencias:**
  - una migración futura que borre o cambie columnas usadas por las vistas tendrá que recrear las vistas afectadas:
    PostgreSQL impide borrar una tabla con vistas dependientes;
  - por la misma dependencia, una prueba de U3 que borra tablas para simular un esquema ausente borra antes el esquema
    `analytics`;
  - dos pruebas de U4 dejan de fijar la lista completa de migraciones (ahora termina en `0004`), como ya hizo U4 con
    la de U3;
  - las consultas de U2 a U6 no cambian.
- **Limitación conocida:** por el privilegio por defecto `TEMPORARY` de `PUBLIC` en la base, el rol podría crear tablas
  temporales de sesión. No cambian el esquema ni persisten. Revocarlo afectaría a todos los roles; queda para la
  configuración de entornos desplegados (U12).
- **Verificación (2026-10-06):** `backend/tests/db/test_analytics.py`, 25 pruebas:
  - **migración:** desde cero y sobre `0003` con datos, sin cambiar las tablas operativas, e idempotente; también en
    una segunda base del mismo clúster;
  - **esquema:** columnas, tipos y solo vistas;
  - **valores:** con datos de prueba calculados a mano (conversión UTC, saldo inicial, la fecha de la línea sustituye
    a la de la cabecera); con `ds-6c8ad65b4999`, sin duplicados en el grano de cada vista. Coinciden con las tablas
    (3 990 forecasts, 1 330 primarios, 100 evaluaciones 50/40/10), con la posición contable de la API y con las
    observaciones de lead time de U4;
  - **seguridad:** el rol lee las 13 vistas y ninguna tabla. Se le rechaza escribir, `TRUNCATE`, crear, borrar o
    renombrar objetos, conceder permisos y ejecutar las migraciones. Las vistas posteriores en `analytics` son
    legibles y las tablas nuevas en `public`, no.

  Suite de integración completa: 177 pruebas en verde con PostgreSQL 16.15; con PostgreSQL 16.2, las de U9. Dos
  mutaciones de la migración (un `GRANT` sobre `public` y un lead time desplazado) hacen fallar sus pruebas.
- **Estado:** autorización `ACEPTADA` (2026-10-06, decisión del responsable con el prompt «U9: Vistas analíticas
  PostgreSQL + rol de solo lectura»); implementación pendiente de revisión.

## Decisiones deliberadamente NO tomadas

| ID | Tema | Se decidirá en | Por qué no ahora |
|---|---|---|---|
| `DT-P01` | Servicio de cómputo en Azure (App Service / Container Apps / AKS) | Fase 12–13 | Requiere carga real y presupuesto |
| `DT-P02` | Inferencia en línea vs. solo por lotes | Fase 5–6 | Depende del tiempo de cálculo real |
| `DT-P03` | Algoritmo concreto del modelo de producción | Fase 5 | Se decide con datos, no por preferencia *(2026-10-05: se decide en F5c/F5d con los criterios de `DT-079`; niveles 3–4 fuera, `DT-071`.)* *(2026-10-05, G1: sigue sin decidir. La referencia es el baseline oficial, la media móvil de 13 semanas (`DT-089`), con MASE (`DT-090`) y los valores de `DT-091`.)* |
| `DT-P04` | Umbrales numéricos de aceptación del modelo | Fase 1–5 | Fijarlos sin datos sería inventar un requisito *(2026-10-05: valores propuestos en `DT-079`, incluido el 5 %, `OPEN` hasta la puerta G1.)* *(2026-10-05, G1: valores provisionales `ACEPTADA` en `DT-091`, solo con datos `SYNTHETIC`; siguen abiertas la banda de sesgo y la tolerancia de cobertura.)* |
| `DT-P05` | Política de revisión (continua o periódica) | Definición del negocio | Es una decisión de negocio, no técnica |
| `DT-P06` | Estrategia de particionamiento en PostgreSQL | Fase 2, si el volumen lo exige | No justificado con el volumen de referencia |
| `DT-P07` | Herramientas de E2E y de pruebas de carga | Fases 7 y 14 | Dependen del stack ya construido |
| `DT-P08` | Modelo de Azure OpenAI y región | Fase 10 | Depende de costo, cumplimiento y disponibilidad |
| `DT-P09` | Multi-ubicación / multi-almacén | Fase posterior | ASSUMPTION-006 pendiente de validación |
| `DT-P10` | Seguridad a nivel de fila en Power BI | Fase 11 | Depende del modelo de permisos del negocio |
| `DT-P11` | Criterio de corte del tránsito efectivo (órdenes atrasadas) | Fase 4 | Requiere criterio de negocio (`DT-012`). Es además la razón de que la situación 12 de §25 sea Nivel C y no un eje (`DT-023`) |
| `DT-P12` | Si §25 debe incluir «alta rotación» y «baja rotación» como filas | Pendiente del responsable | Decisión sobre la especificación, no sobre el Componente 1 (`DT-023` §7) |
| `DT-P13` | Mutabilidad de `PurchaseOrder` y `PurchaseOrderItem`: `RNF-013` los llama «registros históricos inmutables»; `docs/04` §1 los clasifica como mutables con auditoría, `DT-006` no los incluye entre los *append-only* y `docs/07` prevé cambiar su estado | Antes de cualquier escritura de órdenes (`US-035`) | **Contradicción entre documentos**; no se resuelve unilateralmente. No afecta a U1–U5, que no escriben órdenes |
| `DT-P14` | ✅ **CERRADA (2026-10-01).** Detalles de `V1-05`: definición, serie (consumo), ventanas móviles diarias de `H` días y todo el histórico hasta el corte (desde la documentación, 2026-09-30); estimador **poblacional**; `n = 0` → `INSUFFICIENT_HISTORY`, `n = 1` → `σ_H = 0`; evaluación exacta **B3**, con 28 cifras significativas y `ROUND_HALF_EVEN` solo para informar (decisión del responsable, 2026-10-01; `docs/06` §16.6 y §16.9) | — | Ninguna fórmula V1 cambia |
| `DT-P15` | ✅ **CERRADA (2026-09-30).** `as_of_date` inclusivo y fecha de la decisión; horizonte `as_of_date + 1 … as_of_date + H`; tránsito efectivo con `as_of_date < expected_on ≤ as_of_date + H`; emisión sugerida = `as_of_date` (`docs/06` §16.2) | — | Resuelta con `DT-031` §`V1-02`, §`V1-03`, §`V1-09`, `docs/05` §5.3 y `DT-038` §3 |
| `DT-P16` | Cómo se impide aplicar `V1_PROVISIONAL` a datos `REAL` sin que el motor lea `data_origin` (`BR-009` frente a `BR-007`). *Nota del 2026-10-03:* mientras no se decida, `DT-063` impide que U4 ejecute `V1_PROVISIONAL` sobre una carga no `SYNTHETIC`; no decide el mecanismo definitivo para datos `REAL` | Antes de la primera carga de datos reales | No hay datos reales todavía. **Sigue abierta** |
| `DT-P17` | ✅ **CERRADA (2026-10-02) por `DT-056`.** Intervalo por cuantiles empíricos nearest-rank 10/90 del error histórico a cada horizonte, con `confidence_level = 0.80` como nivel nominal (no calibrado); longitud estacional de 52 semanas; `k = 13`; media móvil como referencia provisional, elección operativa y reversible, no por desempeño. *Problema original:* método del intervalo del baseline (RF-010 lo exige), `k` de la media móvil, longitud estacional y baseline de referencia | — | Decisión del responsable al autorizar U3 |
| `DT-P18` | ✅ **CERRADA (2026-10-03) por `DT-059`.** Se persiste una fila por evaluación, única por `(calculation_run_id, product_id, location_id)`, con `outcome` `RECOMMEND`, `NO_NEED` (con `raw_quantity = 0`) o `NOT_CALCULABLE` (con sus `reasons`). El `outcome` es un resultado técnico inmutable; el `status` humano es un flujo separado que no se crea en V1 (sin `status`, `resolved_*` ni `urgency`). Un fallo de la ejecución (`FAILED`) no es un `outcome`: `NOT_CALCULABLE ≠ FAILED`. *Problema original:* persistencia de las evaluaciones sin recomendación y relación entre `outcome` y el `status` humano de `Recommendation` | — | Decisión del responsable al autorizar U4 |
| `DT-P19` | Indicadores de riesgo sin clasificación (cobertura en días, fecha estimada de agotamiento): definición operativa de «demanda diaria estimada» | Antes de ofrecer riesgos | `docs/06` §9 no la define; `BR-X03` sigue pendiente para los niveles |
| `DT-P20` | ✅ **CERRADA (2026-09-30).** Rige V1 para «demanda estimada cero», «lead time cero» y «`σ = 0`», sin reglas añadidas y sujetos a revisión si el negocio cambia la política (`docs/06` §16.10) | — | Decisión del responsable al autorizar U1 |
| `DT-P21` | ✅ **CERRADA (2026-10-03) por `DT-058`.** Opción A: cada corte de recomendación consume el forecast cuyo `as_of_date` es exactamente ese corte (`forecast --as-of t` y después `recommend --as-of t`). El forecast sigue siendo semanal, con semanas ancladas en `as_of_date + 1`; lo que se ejecuta por corte es la **ejecución** de forecast. U1 no cambia, las semanas de U3 no se desplazan ni se reanclan y U4 no convierte granularidades ni lanza forecasts. *Problema original:* forecast semanal frente a recálculo diario con semanas ancladas en el primer día del horizonte | — | Decisión del responsable al autorizar U4 |
| `DT-P22` | ✅ **ACEPTADA (2026-10-01), opción (a).** `PRODUCT_OUT_OF_VALIDITY` significa que el producto no es válido durante todo el periodo requerido por la evaluación U1: cubre `as_of_date` fuera de vigencia y `valid_to` no nulo con `as_of_date ≤ valid_to < as_of_date + H`. En ambos casos `NOT_CALCULABLE`, sin razón nueva y sin recortar `H` ni el forecast (`DT-049`, `docs/06` §16.11.2). *Problema original:* contenido de `reasons` cuando el horizonte cruza `valid_to`, con una lista cerrada y sin razón aplicable | — | Decisión del responsable; detectada al registrar `DT-049` |
| `DT-P23` | Estimación para productos sin histórico suficiente para ningún baseline (menos de 25 semanas completas, `DT-056`): RML-007 exige que todo SKU obtenga una estimación por una vía documentada; en V1 no se genera forecast, el motivo queda en la ejecución (`DT-057`) y U1 devolverá `FORECAST_MISSING` | Fase 5 (`US-056`) o antes de la primera carga de datos `REAL` | Exige una analogía por categoría o un método específico que no están definidos; en el dataset 0.4.0 no ocurre *(2026-10-05: el dataset 0.4.0 no tiene series cortas; solo recortes artificiales para validar el algoritmo, nunca como evidencia real, `docs/05` §20.3.)* |
