# Reporte — ETAPA 0.1 · Auditoría y corrección de la Etapa 0

**Fecha:** 2026-09-04 · **Alcance:** revisión correctiva de la documentación de la Etapa 0.
**Naturaleza:** auditoría conservadora. No se rediseñó el proyecto ni se regeneró la documentación.

## Estado

> ## APROBADA CON OBSERVACIONES
>
> No quedan inconsistencias críticas. Las correcciones aplicadas resuelven los quince problemas
> encontrados. Las observaciones que impiden un **APROBADA** sin matices son **externas al equipo
> técnico**: doce parámetros que debe aportar el negocio y dos supuestos de alto riesgo sin confirmar.
> Ninguna de ellas puede resolverse escribiendo documentación.

---

## 1. Problemas encontrados

Severidad: **Crítica** (produciría un sistema incorrecto) · **Alta** (produciría implementaciones
divergentes o compromisos no pedidos) · **Media** (inconsistencia real sin consecuencia inmediata) ·
**Baja** (imprecisión).

### P-01 · DT-010 confundía cuatro conceptos distintos
- **Severidad:** Crítica · **Documento:** `docs/15-decisiones-tecnicas.md`, `docs/06-motor-abastecimiento.md` §6.4
- **Descripción:** La decisión trataba «variabilidad de la demanda», «error de pronóstico»,
  «incertidumbre declarada por el modelo» y «variabilidad del lead time» como si fueran intercambiables,
  y presentaba el uso del error de pronóstico como una dirección casi resuelta. Además, el documento
  daba por buena implícitamente la práctica de escalar el error de un paso por `√L`, que **no es una
  identidad general**: esa relación se deriva para el método naïve y bajo el supuesto explícito de
  residuos no correlacionados y varianza constante, supuestos que los errores multi-horizonte suelen
  incumplir. Aplicarla sin verificarla **subestimaría el stock de seguridad** justo donde más cuesta.

### P-02 · No existía regla para convertir el pronóstico semanal a un lead time en días
- **Severidad:** Crítica · **Documento:** `docs/05-motor-predictivo.md`, `docs/06-motor-abastecimiento.md`
- **Descripción:** `DT-008` decidía modelar en semanas; los lead times se registran en días. Con
  `L = 10 días` y un pronóstico semanal, **la demanda durante el lead time no estaba definida**. Es el
  caso de libro de dos desarrolladores implementando dos fórmulas distintas y el sistema devolviendo
  dos cifras para la misma pregunta, sin que ninguna prueba lo detecte.

### P-03 · `quantity_in_transit` mezclaba dos conceptos de dominio
- **Severidad:** Crítica · **Documento:** `docs/04-modelo-datos.md`, `docs/06-motor-abastecimiento.md` §4, `DT-012`
- **Descripción:** Se confundía el **tránsito total** (hecho sobre el mundo) con el **tránsito
  relevante para una decisión** (relativo al horizonte de esa decisión). La consecuencia práctica es un
  fallo silencioso grave: el sistema no recomienda comprar porque «ya viene en camino» algo que
  llegará tarde. `DT-012` lo describía como un «refinamiento previsto», no como una distinción conceptual.

### P-04 · No existía evaluación del impacto sobre la decisión de abastecimiento
- **Severidad:** Crítica · **Documento:** `docs/05-motor-predictivo.md`
- **Descripción:** El proyecto medía si el pronóstico acierta, no si **produce mejores decisiones de
  abastecimiento**. Un modelo puede reducir el error y empeorar el servicio —por sesgo a la baja en los
  SKU críticos, por una incertidumbre peor calibrada de la que depende el stock de seguridad, o por
  mejorar en los SKU que dominan el promedio y empeorar en los que concentran el impacto—. Sin
  evaluación de Nivel 2 esos casos pasan inadvertidos y se promueve un modelo peor.

### P-05 · No existía comparación end-to-end baseline vs. ML
- **Severidad:** Crítica · **Documento:** `docs/05-motor-predictivo.md`, `project/roadmap.md`
- **Descripción:** Consecuencia de P-04. Nada obligaba a recorrer el sistema completo con cada
  forecast y comparar los resultados. Es decir: no había forma de demostrar que el motor predictivo
  sirve, que es la pregunta que el proyecto existe para responder.

### P-06 · MASE fijada como métrica primaria sin datos
- **Severidad:** Alta · **Documento:** `docs/05-motor-predictivo.md` §9
- **Descripción:** MASE es una candidata razonable, pero designar la métrica primaria antes de conocer
  la composición del catálogo —qué proporción es intermitente, qué dispersión de escalas hay— es fijar
  un criterio de aceptación sin la información que lo justifica.

### P-07 · Un requisito inventado y catorce propuestas presentadas como obligatorias
- **Severidad:** Alta · **Documento:** `docs/01-requerimientos.md`
- **Descripción:** **RF-016** (evaluación de desempeño de proveedores) introducía una exigencia de
  negocio que nadie pidió; la parte técnicamente necesaria —media y variabilidad del lead time— ya
  estaba en RF-007. Era además el único RF ausente de la tabla de trazabilidad. Además, catorce
  requisitos que son elecciones de diseño defendibles pero no exigidas aparecían con el mismo verbo
  «debe» que el alcance confirmado, **inflando el compromiso del proyecto**.

### P-08 · RF-021 (asistente conversacional) contradecía el principio del proyecto
- **Severidad:** Alta · **Documento:** `docs/01-requerimientos.md`, `CLAUDE.md` §1
- **Descripción:** El alcance pide *explicaciones mediante Azure OpenAI*, no conversación, y
  `CLAUDE.md` afirma que el sistema **no es un chatbot**. El requisito estaba enunciado como obligación.

### P-09 · Cuatro requisitos funcionales sin historia de usuario
- **Severidad:** Alta · **Documento:** `project/backlog.md`
- **Descripción:** RF-002 (categorías) no aparecía en absoluto. RF-001 y RF-005 estaban cubiertos solo
  en lectura pese a exigir «administrar». RF-008 no tenía historia de creación de órdenes ni de ciclo
  de estados, pese a que `US-073` («convertir en orden», Fase 7) presuponía ese endpoint.

### P-10 · Azure Key Vault adoptado sin registrar la decisión
- **Severidad:** Media · **Documento:** `docs/01-requerimientos.md` RS-006, `docs/10-seguridad.md`, `docs/03-arquitectura.md`
- **Descripción:** Key Vault **no figura en la lista de tecnologías obligatorias** del alcance, y
  `CLAUDE.md` §5 exige justificar y registrar toda tecnología adicional relevante antes de adoptarla.
  Aparecía nombrado como decidido en tres documentos.

### P-11 · Dependencia RF-020 → RF-019 contraria al orden de fases
- **Severidad:** Media · **Documento:** `docs/01-requerimientos.md`
- **Descripción:** RF-020 (Azure AI Search, Fase 9) declaraba depender de RF-019 (Azure OpenAI,
  Fase 10). La recuperación documental es independiente de la generación de explicaciones.

### P-12 · `US-032` adelantaba trabajo de la Fase 4 y contradecía el criterio de la Fase 3
- **Severidad:** Media · **Documento:** `project/backlog.md`, `project/roadmap.md`
- **Descripción:** La historia introducía endpoints de escritura en una fase cuyo criterio de
  finalización hablaba solo de lectura, y atribuía a la Fase 3 el cálculo del lead time observado, que
  el roadmap sitúa en la Fase 4.

### P-13 · Alcance del baseline contradictorio entre fases
- **Severidad:** Media · **Documento:** `project/backlog.md`, `project/roadmap.md`
- **Descripción:** `US-050` exigía los cuatro baselines en la Fase 4, mientras el roadmap listaba como
  actividad de la Fase 5 «ampliación del conjunto de baselines iniciado en la Fase 4». No quedaba nada
  que ampliar.

### P-14 · `RF-003` exigía un dato sin origen posible
- **Severidad:** Media · **Documento:** `docs/01-requerimientos.md`, `docs/04-modelo-datos.md`
- **Descripción:** El requisito exigía mantener la «cantidad comprometida/reservada», pero ningún punto
  del alcance genera compromisos: no hay órdenes de venta ni reservas. Hoy el campo no tendría quien lo alimente.

### P-15 · Inconsistencias menores de estado y dependencias
- **Severidad:** Baja · **Documento:** `project/backlog.md`
- **Descripción:** El encabezado de `EPIC-01` declaraba la Fase 0 «completada» mientras los otros tres
  archivos la daban por pendiente de aprobación. `US-075` no declaraba su dependencia del intervalo de
  predicción (`US-055`, Fase 5). `US-082` tenía un criterio de aceptación verificable solo en la Fase 13.

---

## 2. Correcciones realizadas

| # | Archivo | Sección | Cambio | Motivo |
|---|---|---|---|---|
| 1 | `docs/15-decisiones-tecnicas.md` | DT-010 | Reescrita. Tabla que separa los cuatro conceptos; se explicita que el objeto a cubrir es el error **acumulado sobre el intervalo de protección**; cinco alternativas evaluadas; estado → **`PENDIENTE DE VALIDACIÓN`** | P-01 |
| 2 | `docs/06-motor-abastecimiento.md` | §6.4 | Reescrita en coherencia con DT-010; se declara que §6.1–6.2 son punto de partida, no fórmula oficial | P-01 |
| 3 | `docs/05-motor-predictivo.md` | §8 regla 6 | La validación temporal debe evaluar también **al horizonte del intervalo de protección** | P-01 |
| 4 | `docs/15-decisiones-tecnicas.md` | **DT-019** (nueva) | Conversión semanal→días: cuatro alternativas, recomendación (prorrateo uniforme), condición que la invalida, y **obligación de implementarla en una única función** | P-02 |
| 5 | `docs/05-motor-predictivo.md` · `docs/06-…` | §3.1 · §5.1 | Regla de conversión documentada en ambos con ejemplo numérico (`L=10` → `F₁ + (3/7)·F₂`) | P-02 |
| 6 | `docs/15-decisiones-tecnicas.md` | DT-012 | Reescrita: `total_in_transit` (hecho, almacenado) vs. `effective_in_transit` (relativo a la decisión, **derivado, sin columna nueva**) | P-03 |
| 7 | `docs/06-motor-abastecimiento.md` | §4.1–4.2 | Dos lecturas de la posición de inventario: contable y de decisión. La comparación con el ROP usa la de decisión | P-03 |
| 8 | `docs/04-modelo-datos.md` | §3.6 | `quantity_in_transit` = total; `effective_in_transit` explícitamente **no es columna** | P-03 |
| 9 | `docs/15-decisiones-tecnicas.md` | **DT-020** (nueva) | Evaluación en dos niveles y comparación end-to-end. Estado `ACEPTADA` | P-04, P-05 |
| 10 | `docs/05-motor-predictivo.md` | §9 completa | Reestructurada: §9.1 Nivel 1 justificado métrica a métrica · §9.3 por qué no basta · §9.4 Nivel 2 · §9.5 comparación end-to-end con diagrama y condiciones de validez | P-04, P-05 |
| 11 | `docs/05-motor-predictivo.md` | §10 | Nuevo criterio 9: superar al baseline **también en Nivel 2**; un modelo que mejora el error y empeora el servicio no se promueve | P-04 |
| 12 | `docs/15-decisiones-tecnicas.md` | **DT-021** (nueva) | Métrica primaria → `PENDIENTE`. Se fijan los cinco criterios de selección y las candidatas. **MAPE descartada como métrica de decisión** (`ACEPTADA`) | P-06 |
| 13 | `docs/01-requerimientos.md` | **§5 nueva** | Tabla de clasificación de los 63 requisitos por origen (62 originales más `RML-013`): A solicitado · B derivado · C supuesto · D propuesta, con regla explícita de que **D no obliga** | P-07 |
| 14 | `docs/01-requerimientos.md` | RF-016 | Reclasificado a `PROPUESTA`, prioridad → *Podría*. Se señala que lo necesario ya está en RF-007 | P-07 |
| 15 | `docs/01-requerimientos.md` | RF-021 | Reclasificado a `PROPUESTA — PENDIENTE DE VALIDACIÓN`, con la tensión con `CLAUDE.md` §1 explicitada | P-08 |
| 16 | `docs/01-requerimientos.md` | RF-002, RNF-012, RF-020 | RF-002 → `PROPUESTA`; RNF-012 marcado `SUPUESTO` (rol planificador); RF-020 marcado con ASSUMPTION-008 | P-07 |
| 17 | `project/backlog.md` | **US-034, US-035** (nuevas) | Mantenimiento de maestros y ciclo de vida de órdenes de compra | P-09 |
| 18 | `project/backlog.md` | **US-058** (nueva) | Evaluación de Nivel 2 y comparación baseline vs. ML | P-04, P-05 |
| 19 | `docs/01-requerimientos.md` | **RML-013** (nuevo) | Requisito derivado que respalda US-058. Sin valores objetivo | P-04 |
| 20 | `docs/15-decisiones-tecnicas.md` | **DT-022** (nueva) | Almacén de secretos gestionado como `PROPUESTA`; Key Vault deja de presentarse como decidido | P-10 |
| 21 | `docs/01-requerimientos.md` · `docs/03-…` | RS-006 · §4 | Redactados contra la interfaz `SecretProvider`, sin fijar producto | P-10 |
| 22 | `docs/01-requerimientos.md` | RF-020, RF-017 | Eliminada la dependencia RF-020→RF-019; en RF-017 se difiere explícitamente el criterio de permisos a la Fase 8 | P-11 |
| 23 | `project/roadmap.md` · `project/backlog.md` | Fase 3 · US-032 | La Fase 3 incluye endpoints de escritura y su criterio lo refleja; el lead time observado se atribuye a la Fase 4 | P-12 |
| 24 | `project/backlog.md` · `project/roadmap.md` | US-050 · Fases 4–5 | Baseline en Fase 4 = naïve, naïve estacional y media móvil; suavizado exponencial y elección del oficial en Fase 5 | P-13 |
| 25 | `docs/01-requerimientos.md` · `docs/04-…` | RF-003 · §3.6 | `quantity_reserved` marcado `PENDIENTE DE VALIDACIÓN`: se conserva en el modelo conceptual, no se implementa mientras nadie lo alimente | P-14 |
| 26 | `project/backlog.md` | EPIC-01, US-041, US-075, US-082, EPIC-10 | Estado de la Fase 0 alineado; US-041 reescrita para el tránsito efectivo; dependencias y fases corregidas | P-15, P-03 |
| 27 | `docs/03-arquitectura.md` | **§14 nueva** | Auditoría de proporcionalidad: los doce componentes con responsabilidad, necesidad, dependencia, integración y alternativa más simple | Encargo §4 |
| 28 | `docs/04-modelo-datos.md` | **§3.18 nueva** | Cadena de trazabilidad `Recommendation → Forecast → ModelVersion → datos → reglas`, verificada campo a campo | Encargo §14 |
| 29 | `docs/05-motor-predictivo.md` | **§5.3 nueva** | Variables conocidas de antemano / observadas hasta el corte / conocidas solo a posteriori, con la trampa del indicador de desabasto | Encargo §10 |
| 30 | `docs/13-testing.md` | §6.1 nueva | Pruebas de la propia evaluación de Nivel 2, incluida la prueba de sensibilidad del simulador | P-04 |
| 31 | `knowledge/assumptions.md` | ASSUMPTION-019, -020 | Demanda uniforme dentro de la semana; el histórico permite simulación retrospectiva | P-02, P-04 |
| 32 | `knowledge/sources.md` | §7bis, §7ter | Fuentes nuevas con su consecuencia y una advertencia sobre el peso de las secundarias | Encargo §20 |
| 33 | `project/roadmap.md` | Fases 4, 5, 7; bloqueos | Actividades y criterios actualizados; dependencia de la Fase 7 sobre la 5; bloqueos con `DT-019`/`BR-X06` | P-02, P-04, P-15 |
| 34 | `docs/11-power-bi.md` | §4.5 | Los KPIs de impacto se declaran coincidentes con las métricas de Nivel 2, con definición única en el glosario | P-04 |
| 35 | `docs/06-motor-abastecimiento.md` | §8, §12, §14, §15 | `IP_decisión` en la cantidad recomendada; validación por Nivel 2; tres casos límite nuevos; dos pendientes añadidos | P-02, P-03, P-04 |

---

## 3. Decisiones revisadas y mantenidas sin cambios

Se revisaron y se consideran **correctas tal como están**:

| ID | Decisión | Por qué se mantiene |
|---|---|---|
| `DT-001` | Separación ML / reglas / IA generativa | Es el principio que hace el sistema auditable. **No se encontró ninguna razón técnica excepcional para tocarlo.** La cadena ML → Forecast → Supply Engine → Recommendation → Azure OpenAI → Explanation se conserva íntegra |
| `DT-002` | Monolito modular, no microservicios | Proporcional al alcance. No se introdujo ningún componente de infraestructura adicional |
| `DT-003` | Dependencias de Azure tras interfaces propias | Es lo que permite desarrollar sin credenciales y degradar sin ellas. Reforzada por `DT-022` |
| `DT-004` | Datos sintéticos con marca de origen | Correcta |
| `DT-005` | Comunicación síncrona, sin mensajería | Correcta. Sigue sin haber necesidad |
| `DT-006` | Histórico inmutable | Correcta, y es la base de la trazabilidad verificada en §3.18 del modelo de datos |
| `DT-007` | Sin SQL generado por el LLM | Correcta |
| `DT-009` | Progresión de modelos con criterio de parada | Correcta, y refuerza la conclusión de la auditoría de arquitectura |
| `DT-011` | Demanda censurada: marcar el dato, método pendiente | Correcta. Es el ejemplo del tratamiento adecuado: se conserva la opción sin fijar el método |
| `DT-013` | Carpetas bajo `docs/` | Sin cambios; sigue `PROPUESTA` pendiente de confirmación |
| `DT-014` | Import en Power BI | Sin cambios; sigue `PROPUESTA` |
| `DT-015` | Sin promoción automática de modelos | Correcta, y **reforzada**: ahora la promoción exige también superar el Nivel 2 |
| `DT-016` | El sistema recomienda, no compra | Correcta. Confirmada por el alcance |
| `DT-017` | Idioma: documentación en español, código en inglés | Correcta |
| `DT-018` | Plantilla determinística antes que LLM | Correcta, y es un buen ejemplo del patrón «alternativa simple primero» |

**Ninguna decisión `PROPUESTA` se convirtió en definitiva.** El movimiento fue en la dirección
contraria: `DT-010` pasó de `PROPUESTA` a `PENDIENTE DE VALIDACIÓN` al descubrirse que la cuestión de
fondo es más abierta de lo que la redacción sugería.

---

## 4. Decisiones pendientes

Nada de esto debe fijarse todavía.

| ID | Qué falta decidir | De qué depende | Cuándo |
|---|---|---|---|
| `DT-010` | Metodología del stock de seguridad a partir de la incertidumbre | Datos + backtesting al horizonte + efecto en Nivel 2 | Fase 5 |
| `DT-019` | Regla de conversión semanal→días | Calendario laboral (`BR-X06`) | Fase 4 |
| `DT-021` | Métrica primaria de pronóstico | Composición real del catálogo | Fases 1 y 5 |
| `DT-011` | Método de tratamiento de la demanda censurada | Datos | Fase 5 |
| `DT-008` | Confirmación de la granularidad semanal | Datos, por segmento | Fase 5 |
| `DT-012` / `DT-P11` | Criterio de corte del tránsito efectivo y trato de órdenes vencidas | Criterio de negocio | Fase 4 |
| `DT-013` | Ubicación de `architecture/`, `decisions/`, `reports/` | Confirmación del responsable | Inmediata |
| `DT-014` | Import vs. DirectQuery en Power BI | Volumen y comportamiento reales | Fase 11 |
| `DT-022` | Producto de almacén de secretos | Destino de despliegue (`DT-P01`) | Fases 12–13 |
| `DT-P01`–`DT-P11` | Once decisiones diferidas | Ver tabla en `docs/15` | Varias |

---

## 5. Nuevos supuestos introducidos

Dos, ambos consecuencia de correcciones y ambos registrados con validación e impacto:

- **`ASSUMPTION-019` — Demanda uniforme dentro de la semana.** Sostiene la regla de prorrateo
  recomendada en `DT-019`. **Si es falso** —el negocio no opera todos los días, o el histórico muestra
  perfil intra-semanal— la conversión sesga sistemáticamente la demanda durante el lead time. Afecta a
  casi todos los productos, porque casi ningún lead time es múltiplo de 7.
- **`ASSUMPTION-020` — El histórico permite simulación retrospectiva.** Sostiene toda la evaluación de
  Nivel 2. **Si es falso**, la comparación baseline vs. ML solo sería posible sobre datos sintéticos y
  sus resultados no serían extrapolables, lo que habría que declarar en el informe de evaluación.

No se introdujo ningún requisito empresarial, umbral, costo, política, calendario, cantidad mínima ni
objetivo. **No se fijó ningún valor objetivo de Nivel 2** (del tipo «desabasto < 5 %»): se definió qué
medir, no cuánto alcanzar.

---

## 6. Fuentes utilizadas

Registradas en `knowledge/sources.md` §7bis y §7ter (consulta: 2026-09-04).

| Fuente | Qué sustenta |
|---|---|
| Hyndman & Athanasopoulos, *Forecasting: Principles and Practice* (3.ª ed.) §5.8 — https://otexts.com/fpp3/accuracy.html | Definiciones de MAE, RMSE, MAPE, MASE, RMSSE; los problemas de MAPE con valores cero y su asimetría; que los errores escalados se definen contra el naïve y por eso permiten comparar entre series → **`DT-021`** |
| Hyndman & Athanasopoulos, *Forecasting: Principles and Practice* (3.ª ed.) §5.5 — https://otexts.com/fpp3/prediction-intervals.html | Que `σ̂_h = σ̂·√h` está tabulada **para el método naïve** y **bajo residuos no correlacionados**, no como identidad general → **`DT-010`**, el hallazgo técnico central de esta revisión |
| *Bridging Forecast Accuracy and Inventory KPIs* (arXiv) — https://arxiv.org/abs/2601.21844 | Que precisión de pronóstico e indicadores de inventario no se corresponden directamente → **`DT-020`** |
| *Nonparametric Safety Stock Dimensioning* (arXiv) — https://arxiv.org/abs/2511.04616 | Enfoques no paramétricos basados en la distribución empírica del error → alternativa (d) de `DT-010` |

Las dos referencias de arXiv se citan como literatura de apoyo, **no como fundamento único de ninguna
decisión**. Las fuentes de Microsoft Learn, GitHub y Docker registradas en la Etapa 0 se revisaron y
siguen siendo válidas; no se añadieron ni se modificaron.

---

## 7. Verificación de los criterios de finalización

| Criterio | Estado |
|---|---|
| Arquitectura sin sobreingeniería evidente | ✅ Auditada componente a componente (`docs/03` §14). Sin microservicios, orquestador, mensajería ni caché distribuida |
| Requisitos correctamente clasificados | ✅ Los 63, en `docs/01` §5, y marcados también en su propia entrada. Cero inventados tras la revisión |
| Modelo de datos coherente | ✅ Revisado; dos precisiones (tránsito, `quantity_reserved`). Sin entidades nuevas |
| `DT-010` correctamente delimitada | ✅ `PENDIENTE DE VALIDACIÓN`, con los cuatro conceptos separados |
| Relación forecast semanal / lead time definida o marcada | ✅ `DT-019`, con alternativas, recomendación y estado pendiente |
| Inventario en tránsito conceptualmente definido | ✅ `total` vs. `effective`, sin columna nueva |
| Estrategia ML con target claro | ✅ Demanda por SKU y periodo; horizonte marcado pendiente |
| Validación temporal | ✅ Rolling origin, con la regla nueva de evaluar al horizonte de protección |
| Baseline | ✅ Definido, y ahora ubicado sin ambigüedad en la Fase 4 |
| Métricas de pronóstico | ✅ Justificadas una a una; primaria pendiente; MAPE descartada |
| Evaluación de abastecimiento | ✅ Nivel 2 en `docs/05` §9.4 |
| Comparación baseline vs. ML | ✅ `docs/05` §9.5, `US-058`, criterio 9 de aceptación |
| Trazabilidad de recomendaciones | ✅ Verificada campo a campo en `docs/04` §3.18 |
| Supuestos correctamente identificados | ✅ 20, con validación e impacto |
| Segunda revisión ejecutada tras las correcciones | ✅ Detectó diecinueve hallazgos adicionales —agrupados en quince entradas en §9—, todos corregidos |
| Propuestas no presentadas como definitivas | ✅ Verificado; `DT-010` incluso retrocedió a pendiente |
| Sin contradicciones importantes entre documentos | ✅ Segunda revisión ejecutada tras las correcciones |
| Roadmap coherente | ✅ Corregido, sin reorganizar |
| Backlog coherente | ✅ Cobertura completa de RF; dependencias corregidas |
| Reporte de Etapa 0.1 | ✅ Este documento |

## 9. Segunda revisión (posterior a las correcciones)

Tras aplicar las treinta y cinco correcciones se ejecutó una **segunda revisión cruzada** de los 31
documentos. Detectó **diecinueve hallazgos adicionales**, todos corregidos. Agrupados en quince entradas:

| # | Hallazgo | Corrección |
|---|---|---|
| S-01 | **Fórmula errónea:** `RF-012` y `docs/02` §5 expresaban la posición como «**disponible** + tránsito − comprometido». Como *disponible* ya descuenta lo comprometido, la expresión **lo restaba dos veces** | Reescrita como `existencia física + tránsito efectivo − comprometido`, con la advertencia explícita |
| S-02 | **Fórmula incoherente:** `docs/06` §7 definía el nivel objetivo como `S = D̂ × (L + R) + SS`, volviendo al producto por una media que §5 había descartado en favor de la suma del forecast | `S = DDLT_periódica + SS`, con `DDLT_periódica = Σ D̂ₜ sobre (L + R)` |
| S-03 | **Unidades sin regla:** `H_cobertura` se almacena en días (`target_coverage_days`) y el forecast está en semanas. `DT-019` cubría el lead time pero no este término | Declarado que atraviesa **la misma** función única de conversión. No hay una segunda regla |
| S-04 | La distinción tránsito total / efectivo se había aplicado en `docs/04`, `docs/06` §4 y `DT-012`, pero **seis documentos seguían usando la fórmula antigua**: glosario, `BR-006` (regla ✅ vinculante), notación de `docs/06` §3, desglose de §13, `docs/07`, `docs/13`, `CLAUDE.md` y `docs/11` | Alineados los ocho. El glosario define ahora ambos términos y ambas lecturas de la posición |
| S-05 | **Key Vault seguía presentado como decidido** en `docs/10` (cuatro lugares), `docs/02`, `docs/09` y `CLAUDE.md`, pese a que `DT-022` lo prohíbe expresamente | Sustituido por «almacén de secretos gestionado» con referencia a `DT-022` |
| S-06 | **La reclasificación de clase D estaba a medias:** `docs/01` §5 declaraba que no obligan, pero solo tres de los catorce lo decían en su propia entrada; cuatro conservaban «Prioridad: Debe» | Marcados los once restantes en su propia entrada; prioridad ajustada donde procedía |
| S-07 | **`BR-005` (regla ✅ vinculante) se fundaba en `RNF-013`, clasificado D (no vinculante)** | `RNF-013` **reclasificado a B**: sin histórico inmutable, la trazabilidad de `RF-024` y la reproducibilidad de `RML-009` son imposibles. No era una política de auditoría añadida. Igual con `RNF-005` |
| S-08 | **La variante (e) de `DT-010` se daba por decidida** en el glosario («el intervalo es lo que alimenta el stock de seguridad») y en el criterio de `US-055` | Reformulados como «una de las fuentes candidatas», con la calibración como condición previa |
| S-09 | `RF-001` (clase A, vinculante) declaraba depender de `RF-002` (clase D, retirable) | Dependencia eliminada y explicada |
| S-10 | La tabla de trazabilidad de `docs/01` §6 mapeaba `RF-002` y `RF-021` al alcance, contradiciendo su propia clasificación D | Corregida |
| S-11 | Pruebas de integración en la Fase 4 según `docs/12`, en la Fase 2 según `docs/13` y el roadmap | Unificadas en la Fase 2 |
| S-12 | El diagrama de fases del roadmap no tenía las aristas `F5→F7` ni `F4→F11` que el texto sí declaraba | Añadidas |
| S-13 | `docs/03` §14 afirmaba que «los doce componentes pertenecen al stack obligatorio», desmentido por su propia tabla (`supply_engine` es código propio; Azure AI Search está condicionado) | Reformulado con precisión |
| S-14 | `MLflow` se presentaba como decidido sin ADR, el mismo defecto que motivó `DT-022` para Key Vault | Aclarado que es el mecanismo nativo de Azure ML, que sí está en el stack obligatorio: no es tecnología añadida |
| S-15…S-19 | Seis conteos incorrectos (reparto de clases, número de requisitos, criterios, casos límite, archivos, «ocho primeros» del README), el nivel de encabezado de `docs/04` §3.18 y de `RML-013`, la numeración «4b» de `docs/01` §7, la fecha de `status.md` y la ausencia del reporte 0.1 en el índice de `docs/reports/` | Todos corregidos |

Dos de estos hallazgos —S-01 y S-02— son **errores de fórmula** que habrían producido cálculos
incorrectos. Ninguno de los dos existía antes de la Etapa 0.1: S-01 estaba en la documentación
original y S-02 también. Que aparecieran solo en la segunda pasada justifica el doble ciclo de revisión.

**Nota sobre `etapa-0-reporte.md`:** los conteos de aquel reporte (18 decisiones, 18 supuestos, 31
archivos) son **históricos y correctos para su fecha**. No se editan, conforme a la regla de
`docs/reports/README.md`. Las referencias vivas que los usaban como criterio —en `roadmap.md` y
`backlog.md`— sí se han actualizado.

## 8. Por qué «con observaciones» y no «aprobada»

Las tres razones son externas al trabajo técnico:

1. **Doce parámetros del negocio siguen sin definirse** (`knowledge/business-rules.md` §3). Sin ellos
   la Fase 4 no puede parametrizarse, por bien construido que esté el motor.
2. **`ASSUMPTION-008` sigue sin confirmar.** Si no existe corpus documental, Azure AI Search pierde su
   propósito y hay que replantear su lugar en el stack. Es el único riesgo de sobredimensionamiento
   identificado en toda la arquitectura.
3. **Tres decisiones técnicas quedan deliberadamente abiertas** (`DT-010`, `DT-019`, `DT-021`) porque
   cerrarlas ahora sería inventar. Que estén abiertas es correcto; que estén abiertas impide llamar
   «aprobada» sin matices a una etapa de preparación.

Ninguna de las tres se resuelve escribiendo más documentación.
