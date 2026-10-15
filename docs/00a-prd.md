# PRD — Motor Predictivo de Abastecimiento de Inventarios

## 1. Control del documento

| Campo | Valor |
|---|---|
| Propósito | Describir **qué producto** se construye, qué problema resuelve, para quién, con qué capacidades y bajo qué restricciones, con trazabilidad a los requisitos oficiales, las decisiones, los módulos y las pruebas |
| Estado | **Aprobado por el propietario** (2026-10-14), con los límites del MVP registrados en `docs/00b-mvp.md` §1 y §4 |
| Última actualización | 2026-10-14: revisión y aprobación del propietario |
| Documento hermano | [`docs/00b-mvp.md`](00b-mvp.md): límites de la primera versión y cómo se acepta |
| Ubicación | `docs/00a-prd.md`, y no `docs/01-prd.md`: los prefijos `01` y `02` ya pertenecen a `01-requerimientos.md` y `02-propuesta-tecnica.md`. El sufijo `a` lo sitúa justo después de la guía maestra y antes de los requisitos |

**Qué es y qué no es este documento:**

- Es una **vista de producto**. Los requisitos normativos siguen siendo los de
  [`docs/01-requerimientos.md`](01-requerimientos.md), con sus identificadores oficiales (`RF`, `RNF`, `RS`, `RML`) y su
  clasificación por origen (A solicitado, B derivado, C supuesto, D propuesta no vinculante, §5).
- **No crea identificadores nuevos ni requisitos nuevos.** Cuando un requisito cambie, se cambia en `docs/01` y aquí
  solo se actualiza el estado.
- **No sustituye** a las decisiones (`docs/15`), a los contratos de las unidades ni al estado vivo
  (`project/status.md`). Si difiere de ellos, mandan ellos (jerarquía de [`docs/00-guia-maestra.md`](00-guia-maestra.md)
  §0).

### 1.1 Fuentes autoritativas

| Tema | Fuente | Estado de la fuente |
|---|---|---|
| Alcance declarado y requisitos | [`docs/01-requerimientos.md`](01-requerimientos.md) (v1.1, revisión 0.1) | Requisitos A/B vinculantes; C vinculantes en la necesidad, no en el valor; D no vinculantes |
| Problema, solución y riesgos | [`docs/02-propuesta-tecnica.md`](02-propuesta-tecnica.md) §1–§3, §13–§15 | Propuesta técnica de la Etapa 0 |
| Alcance de la Etapa 2 y clasificación del MVP | `DT-094` en [`docs/15-decisiones-tecnicas.md`](15-decisiones-tecnicas.md) | `ACEPTADA` (2026-10-06) |
| Contratos de U1–U6 e interfaz | `DT-043`–`DT-070`; `docs/04` §9, `docs/05` §19, `docs/06` §16, `docs/07` §7, `docs/08` §12, `docs/09` §14 | `ACEPTADA` |
| Modelo oficial y evaluación | `DT-089`–`DT-093`; [`docs/05`](05-motor-predictivo.md) §20 | `ACEPTADA`, solo con datos `SYNTHETIC` |
| Despliegue de `dev` | `DT-098`–`DT-100` | `ACEPTADA`; U12 cerrada el 2026-10-13 con verificaciones pendientes aceptadas por el responsable |
| Reglas y parámetros de negocio | [`knowledge/business-rules.md`](../knowledge/business-rules.md), [`knowledge/assumptions.md`](../knowledge/assumptions.md) | Muchos parámetros **pendientes del negocio** |
| Estado y evidencia | [`project/status.md`](../project/status.md), [`docs/reports/`](reports/README.md) | Vivo |

### 1.2 Decisiones pendientes que afectan al producto

| Tema | Referencia | Efecto si sigue abierto |
|---|---|---|
| Umbrales de clasificación de riesgo y urgencia | `BR-X03` | RF-013, RF-014 y RNF-012 no se pueden construir |
| Parámetros de política del negocio (nivel de servicio, revisión, costos, horizonte de cobertura, selección de proveedor) | `docs/01` §7; `knowledge/business-rules.md` §3 | Las recomendaciones siguen siendo `V1_PROVISIONAL` (`DT-031`) |
| Validación de los cuatro roles | `ASSUMPTION-010`, RS-002 | Los roles funcionan, pero su significado de negocio no está confirmado |
| Aplicar `V1_PROVISIONAL` a datos reales | `DT-P16` (`DT-063` lo impide mientras tanto) | Sin datos reales en el motor (RF-023 parcial) |
| Tratamiento del desabasto en el forecast | `DT-011` | Limitación declarada de V1 |
| Promoción de un modelo y validación de la banda | F5d, G2, G3 (sin autorizar; `DT-094` punto 9) | MA13 sigue como baseline oficial |
| Validación de la matriz C01–C15 de U12 | [`docs/reports/u12-cierre-evidencias.md`](reports/u12-cierre-evidencias.md) §1 | Usada por el responsable para cerrar U12 el 2026-10-13 (revisión 7) |

---

## 2. Resumen ejecutivo

El producto es un **sistema de apoyo a la decisión de reposición de inventarios**. A partir del histórico de consumo,
del inventario, de las órdenes de compra abiertas y de las condiciones de cada relación producto–proveedor, el sistema:

1. **pronostica la demanda** semanal de cada producto (SKU), con un intervalo de incertidumbre;
2. **evalúa** con reglas deterministas si conviene pedir, cuánto y cuándo, y a qué proveedor;
3. **explica** cada resultado término a término y lo presenta en una API y en una interfaz web.

Pronosticar y decidir son **dos responsabilidades distintas** (RNF-001, RML-012):

- el pronóstico estima la demanda y su incertidumbre, y no decide nada;
- el motor de abastecimiento convierte ese pronóstico y el estado del inventario en una recomendación reproducible;
- la capa de explicación describe las cifras, sin calcularlas (RS-010).

**La decisión de compra sigue siendo humana:** el sistema recomienda, no ejecuta compras (`docs/02` §2).

**Resultado esperado para el usuario:** saber qué productos necesitan reposición, con una cantidad y una fecha
sugeridas, y poder reconstruir por qué se sugirió cada una (RF-015, RF-024).

**Hoy** el producto funciona con un **dataset sintético** y con reglas **provisionales** (`V1_PROVISIONAL`). Sus
recomendaciones demuestran el mecanismo, pero **no son recomendaciones de negocio** (`DT-031`, `docs/07` §7.1.4).

---

## 3. Problema y objetivos del producto

### 3.1 Problema

Las decisiones de abastecimiento suelen tomarse con información fragmentada y heurísticas: se compra «lo de siempre»,
se reacciona cuando el inventario ya está bajo y se asume constante un lead time que varía. Consecuencias
(`docs/02` §1):

- desabasto en lo que rota;
- sobreinventario en lo que no rota;
- coste logístico por compras urgentes;
- **falta de trazabilidad**: no se puede reconstruir por qué se compró una cantidad.

El problema de fondo no es la falta de datos, sino la ausencia de un mecanismo sistemático que convierta el histórico
en una decisión **defendible, repetible y auditable**.

### 3.2 Objetivos

| Objetivo | Cómo lo aborda el producto | Requisitos |
|---|---|---|
| Reducir el riesgo de desabasto | Punto de reorden y cantidad recomendada a partir del pronóstico y de la posición de inventario | RF-012, RF-015 |
| Reducir el sobreinventario | Detección de cobertura excesiva | RF-014 (**pendiente**, `BR-X03`) |
| Reducir el coste logístico de comprar de forma reactiva | Recomendación anticipada con fecha sugerida de pedido | RF-015 |
| Sustituir la intuición por evidencia auditable | Desglose de cada cálculo, versión del modelo y del motor, huella de entradas | RF-024, RNF-002, RNF-013 |

### 3.3 Valor esperado y métricas de negocio

**Por definir por el propietario.** Las fuentes no fijan:

- empresa cliente ni sector;
- volúmenes reales (RNF-004, `ASSUMPTION-012`);
- costes de faltante o de mantener inventario (`docs/01` §7);
- porcentajes de ahorro ni indicadores de retorno.

La única evaluación cuantitativa existente es **relativa al baseline** y sobre datos `SYNTHETIC` (RML-013, `DT-091`).
No es una medida de valor de negocio.

---

## 4. Usuarios y roles

### 4.1 Perfiles funcionales

Derivados de [`docs/08`](08-frontend.md) §2 y [`docs/10`](10-seguridad.md) §3.1. **No hay personas ni departamentos
reales identificados.**

| Perfil | Necesidad | Actividades en el producto actual |
|---|---|---|
| Planificador / comprador | Ver qué comprar, entender por qué y decidir | Consultar recomendaciones, su desglose y su explicación; consultar inventario, pronóstico y ejecuciones. **Registrar la decisión no existe en V1** (`DT-059`) |
| Analista | Analizar históricos, calidad del pronóstico y proveedores | Consultar el historial de consumo y sus estadísticos, el pronóstico y las recomendaciones. El desempeño de proveedores no existe (RF-016, `BR-X05`) |
| Administrador | Mantener maestros, políticas, cargas y usuarios | En V1 no hay administración en la interfaz. Las cargas y los cálculos son comandos batch (`docs/03` §16.7). Los usuarios y roles se gestionan en Entra ID (`deploy-u11.ps1`) |
| Consulta | Consultar estado de inventario y riesgos | Consultar productos, inventario, pronóstico y recomendaciones. **Riesgos no existe** (`BR-X03`) |

### 4.2 Roles técnicos de autorización

`VIEWER`, `ANALYST`, `PLANNER` y `ADMIN` son **app roles** de Entra ID validados en el backend (RS-002, RS-003,
`DT-099`). Son una **propuesta pendiente de validación con el negocio** (`ASSUMPTION-010`, `docs/10` §3.1). No hay
jerarquía: cada endpoint enumera los roles que admite (`docs/07` §7.1.3).

| Permiso | Fuente | Demostrado |
|---|---|---|
| `/health` pública; todo `/api/v1/*` exige token | `docs/07` §7.1–§7.2 | **Pruebas automatizadas** (`backend/tests/api`); **[AZ-U]** en Azure: sin token → 401 (Verify y smoke, U12) |
| Los cuatro roles leen productos, inventario, pronóstico, recomendaciones y explicación | `docs/07` §7.2 | Pruebas (`test_entra.test_role_matrix`); prueba real local 5/5 de U11 (`DT-099`) |
| Historial de consumo: `ANALYST`, `PLANNER`, `ADMIN` | `docs/07` §7.2 | Ídem |
| Detalle de ejecución (`/runs/{id}`): `PLANNER`, `ADMIN` | `docs/07` §7.2 | Ídem |
| Sin rol → 403 en todo salvo `/me` | `docs/10` §3.2 | Prueba real local de U11 (caso 4) |
| **Matriz completa en el entorno desplegado de Azure** | README de U12 §6 | **[AZ-U]** (registrado el 2026-10-11): los cuatro roles y el usuario sin rol, con «Coincide» = `sí` en todas las filas (informe de U12 §2.1). Sin sesión: 401 `AUTHENTICATION_REQUIRED`, aceptado por el responsable para C11 (2026-10-13) |
| Permisos de escritura (registrar, resolver, recalcular) | `docs/10` §3.1 | **No existen**: V1 es de solo lectura (`docs/07` §7.3) |

---

## 5. Alcance funcional del producto

### 5.1 Capacidades

| Capacidad | Descripción | Módulo | Requisitos |
|---|---|---|---|
| Ingesta y validación de datos | Carga atómica e idempotente de un dataset publicado, con validación previa y posterior y marca de origen | U2 | RF-022, RF-023, RNF-013 |
| Consulta de datos operativos | Productos, inventario con líneas abiertas, condiciones de proveedor, historial de consumo con estadísticos | U2 (datos), U5 (consulta) | RF-001, RF-003–RF-009 |
| Pronóstico de demanda | Baselines (naïve, naïve estacional, **MA13** oficial), 14 semanas desde `as_of + 1`, intervalo nominal 0,80, respaldo explícito | U3 | RF-010, RML-001, RML-002, RML-006–RML-008 |
| Evaluación de abastecimiento | Reglas V1: stock de seguridad, punto de reorden, posición de inventario, tránsito efectivo, MOQ y múltiplo; `RECOMMEND` / `NO_NEED` / `NOT_CALCULABLE` | U1 | RF-011, RF-012, RNF-001, RNF-002 |
| Recomendaciones de reposición | Ejecución batch por corte; filas inmutables con huella de entradas y versiones | U4 (con U1) | RF-015, RF-024, RNF-005 |
| API de consulta | 14 endpoints `GET`, autenticados por defecto, con `provenance` | U5 | RF-017 (fuente de datos), RS-001–RS-003 |
| Explicación de recomendaciones | Narrativa por plantilla, verificada contra las cifras; degradación explícita | U6 | RF-019 (parcial), RS-010 |
| Interfaz web | Vistas de solo lectura sobre la API | Fase 7 | RF-017 |
| Autenticación y autorización | Entra ID en `dev`; identidades ficticias en `local` | U5, U11 | RS-001–RS-003, RS-006 |
| Analítica | Esquema `analytics` (vistas) para Power BI; Power BI no existe aún | U9 (U16 pendiente) | RF-018 (parcial) |
| Operación | Contenedores, CI y despliegue de `dev` en Azure | U7, U8, U10–U12 | RNF-006, RNF-007, RS-005, RS-008 |

### 5.2 Recorrido real de los datos

Según los contratos de [`docs/03`](03-arquitectura.md) §16.3 y la guía maestra §A.3. **No sigue la numeración de las
unidades:**

1. El **generador sintético** publica el dataset `ds-6c8ad65b4999` (CSV más manifiesto).
2. **U2** lo valida y lo carga en PostgreSQL. Una repetición da `ALREADY_LOADED`.
3. **U3** (`forecast --as-of t`) lee el consumo ≤ `t` y persiste el pronóstico.
4. **U4** (`recommend --as-of t`) lee inventario, órdenes, recepciones, consumo y el pronóstico **del mismo corte**.
   Construye la entrada pura de **U1** y persiste el resultado. U1 no lee ni escribe datos.
5. **U5** expone los resultados persistidos **sin recalcular**. **U6** construye la explicación a partir de esos
   resultados.
6. La **interfaz** consume la API por el mismo origen. **U9** expone vistas analíticas para un Power BI futuro.

La demanda latente del dataset (`demand.csv`) **nunca** entra al cálculo ni a la API (`DT-034`, `docs/07` §7.1.5).

---

## 6. Requisitos funcionales

Se usan los **identificadores oficiales** de `docs/01`. La necesidad, la descripción completa y el criterio literal están
en `docs/01`; aquí se resumen el criterio verificable y el **estado en el producto actual**.

**Estados:**

- **Implementado**: cumple el criterio en V1, con evidencia;
- **Parcial**: cumple una parte; el resto está aplazado por una decisión citada;
- **Pendiente**: requisito vinculante sin implementar;
- **Propuesto**: clase D, no vinculante.

«Aprobado» describe la fuerza normativa (clase A/B/C), no el estado de implementación.

| ID | Requisito (necesidad) | Clase y prioridad | Módulos | Criterio verificable (resumen de `docs/01`) | Estado en el producto | Evidencia o motivo |
|---|---|---|---|---|---|---|
| RF-001 | Administración de productos | A · Debe | U2, U5 | Alta con SKU único, rechazo de duplicados, desactivación sin borrar histórico | **Parcial**: consulta implementada; alta, edición y desactivación aplazadas | `docs/07` §7.3 (escrituras aplazadas) |
| RF-002 | Categorías | D · Debería | U2, U5 | Asociación y filtro o agregación por categoría | **Propuesto**; filtro por `category_id` implementado | `docs/07` §7.2 |
| RF-003 | Posición de inventario | A · Debe | U2, U5 | Posición desglosada consistente con los movimientos | **Implementado** | Invariantes de U2 (`docs/04` §9.9); `/inventory` |
| RF-004 | Movimientos inmutables | A · Debe | U2 | Inventario reconstruible desde los movimientos; correcciones como ajustes | **Parcial**: cargados e inmutables; registro de movimientos nuevos aplazado | `docs/04` §9.9; `docs/07` §7.3 |
| RF-005 | Proveedores y condiciones | A · Debe | U2, U5 | Varias relaciones producto–proveedor con lead time acordado, MOQ, múltiplo, coste y preferente | **Parcial**: condiciones cargadas y consultables; administración aplazada | `/products/{id}`; `docs/07` §7.3 |
| RF-006 | Consumo | A · Debe | U2, U5 | Serie por rango con granularidad diaria, semanal o mensual | **Implementado** (registro por ingesta) | `/products/{id}/history`, `DT-067` |
| RF-007 | Lead time | A · Debe | U2, U4 | Lead time medio observado, desviación y observaciones, distinto del acordado | **Parcial**: el motor usa el lead time observado (`DT-050`, `ASSUMPTION-024`); la API no expone esos estadísticos por relación | `docs/07` §7.2 (solo `agreed_lead_time_days`) |
| RF-008 | Órdenes de compra | A · Debe | U2, U4, U5 | Estados de la orden; el pendiente de órdenes vigentes forma el tránsito | **Parcial**: órdenes cargadas, tránsito usado por el motor, líneas abiertas consultables; transiciones de estado aplazadas | `/inventory/{id}`; `docs/06` §16.13 |
| RF-009 | Análisis de históricos | A · Debe | U5 | Serie agregada más media, desviación, CV y periodos en cero | **Implementado** | `DT-067`; `backend/tests/api/test_history.py` |
| RF-010 | Predicción de demanda | A · Debe | U3 | Demanda por periodo, intervalo, versión del modelo y fecha; respaldo si el histórico es insuficiente | **Implementado** con baselines; intervalo **nominal**, no calibrado | `docs/05` §19.9–§19.10 |
| RF-011 | Stock de seguridad | A · Debe | U1 | Cálculo determinista y documentado; nivel de servicio configurable, definido por el negocio | **Implementado con parámetro provisional** (`z_v1`, `ASSUMPTION-022`); nivel de servicio pendiente del negocio | `docs/06` §16; 146 pruebas de U1 |
| RF-012 | Punto de reorden | A · Debe | U1, U4 | Indica si la posición está bajo el punto de reorden y expone los términos | **Implementado** | Desglose de `/recommendations/{id}` |
| RF-013 | Riesgo de desabasto | A · Debe | — | Indicador, nivel, fecha de agotamiento y cobertura | **Pendiente**: bloqueado por `BR-X03` | `docs/06` §16.7 |
| RF-014 | Riesgo de sobreinventario | A · Debe | — | Productos con cobertura sobre un umbral | **Pendiente**: necesita un umbral de política (`BR-X03`) | `docs/06` §16.7 |
| RF-015 | Recomendaciones de compra | A · Debe | U1, U4, U5 | Explicable término a término; mismo resultado con los mismos insumos | **Implementado** (`V1_PROVISIONAL`) | `docs/06` §16.13.4; 100 evaluaciones en local y en Azure **[AZ-U]** |
| RF-016 | Desempeño de proveedores | D · Podría | — | Entregas a tiempo, desviación y variabilidad | **Propuesto**; no implementado (`BR-X05`) | — |
| RF-017 | Interfaz web | A · Debe | Fase 7 | Vistas navegables con datos de la API; permisos según el rol | **Implementado** en local; Entra ID validado en local (U11) y, en Azure, inicio de sesión y matriz de autorización (**[AZ-U]**, registrado el 2026-10-11). La revisión de las vistas desplegadas (C12) queda como **pendiente aceptado** en el cierre de U12 (P1) | `docs/08` §12.1; informe de U12 (C10–C12) |
| RF-018 | Indicadores en Power BI | A · Debería | U9, U16 | Objetos de datos documentados que permiten los KPIs sin lógica duplicada | **Parcial**: vistas de U9; Power BI (U16) sin autorizar | `docs/11` §10 |
| RF-019 | Explicaciones con IA generativa | A · Debería | U6, U13 | Coherente con los valores, sin cifras nuevas, con origen indicado | **Parcial**: el criterio lo cumple la plantilla determinista de U6; Azure OpenAI (U13) sin autorizar | `docs/09` §14.6 |
| RF-020 | Recuperación documental (AI Search) | A + C · Podría | U15 | Fragmentos con cita del documento de origen | **Parcial**: recuperación y corpus de demostración sintético implementados; despliegue Search y corpus empresarial pendientes de costo y validación (`DT-094`, punto 7) | [`docs/09`](09-ia-generativa.md) §14.7; `feature/u15-ai-search` |
| RF-021 | Asistente conversacional | D · Podría | — | Responde solo con fuentes del sistema | **Propuesto**; no implementado | — |
| RF-022 | Ingesta de datos | B · Debe | U2 | Reporta filas rechazadas y no deja estado inconsistente | **Implementado** | `docs/04` §9.9; `backend/tests/ingestion`, `tests/db` |
| RF-023 | Sustitución por datos reales | B · Debe | U2, U4 | Origen marcado por carga; ninguna regla depende de que los datos sean sintéticos | **Parcial**: `data_origin` por carga; `DT-063` impide `V1_PROVISIONAL` sobre datos no sintéticos hasta decidir `DT-P16`; no hay datos reales (`ASSUMPTION-001`) | `DT-063` |
| RF-024 | Trazabilidad | B · Debe | U3, U4, U5 | Reconstruir por qué se recomendó una cantidad en una fecha pasada | **Implementado** | `input_sha256`, `forecast_id` y versiones (`DT-059`–`DT-062`); `provenance` |

**Requisitos de ML** (`docs/01` §4) que el producto ya cumple con baselines:

- RML-001, RML-002 (MA13 oficial, ningún modelo promovido), RML-007 (respaldo y `method_used`), RML-008
  (`model_versions`) y RML-012: **implementados**.
- RML-003, RML-004 (`ml/tests/test_leakage.py`), RML-005 (`DT-090`, `DT-091`) y RML-013 (Nivel 2, F5b y F5c):
  **implementados en la evaluación experimental, solo `SYNTHETIC`**.
- RML-006: **parcial**. Hay intervalo en cada predicción, pero el motor V1 mide la incertidumbre sobre la demanda, no
  sobre el error del pronóstico (`ASSUMPTION-023`).
- RML-009: parcial; aplica a F5a–F5c, sin modelo entrenado en producción.
- RML-010 y RML-011 (D): propuestos.

---

## 7. Requisitos no funcionales

Solo los respaldados por `docs/01` y las decisiones. Donde no hay umbral aprobado, se dice.

| ID | Restricción | Estado | Evidencia o umbral |
|---|---|---|---|
| RNF-001 | Separación predicción / decisión / explicación | **Implementado** | `backend/tests/supply_engine/test_purity.py`; reglas de `docs/03` §16.4 |
| RNF-002 | Reproducibilidad y determinismo | **Implementado** | `Decimal`, sin aleatoriedad; misma `input_sha256` en local y Docker (`docs/06` §16.13.5) |
| RNF-003 | Rendimiento de consulta | **Pendiente de definición y medición** | El valor de `docs/01` es `SUPUESTO` (`ASSUMPTION-011`); no hay pruebas de rendimiento |
| RNF-004 | Volumen de referencia | **Por definir por el propietario** | `ASSUMPTION-012`. El dataset tiene 100 productos (no es un volumen de negocio) |
| RNF-005 | Cálculo masivo independiente de la API | **Implementado** | `python -m app.runs forecast` / `recommend`; job de *bootstrap* en Azure |
| RNF-006 | Entorno reproducible sin credenciales | **Implementado** | U7 (`docker compose … --profile app`), job `docker` de CI |
| RNF-007 | CI que falla por formato, *lint* o tipado | **Parcial** | Frontend con ESLint, `tsc` y Prettier; en Python no hay *linter*, por instrucción del responsable (`CLAUDE.md` §6.10, `DT-096`) |
| RNF-008 | Observabilidad | **Propuesto** (D) | `X-Correlation-ID` (`DT-066`); sin Log Analytics en `dev` (`DT-100`) |
| RNF-009 | Disponibilidad | **Por definir por el propietario** | `ASSUMPTION-013`; `dev` escala a cero |
| RNF-010 | Degradación controlada | **Parcial** | Respaldo del pronóstico (MA13 → naïve → sin pronóstico) y degradación de la explicación (`DT-069`); la degradación desde un modelo de ML o un LLM llega con U13/U14 |
| RNF-011 | Consistencia de idioma del contenido (D) | **Propuesto** | Convención de `CLAUDE.md` §6.9; la interfaz usa `es-MX` (`DT-070`) |
| RNF-012 | Vista priorizada para el planificador | **Pendiente** | Bloqueada por `BR-X03` |
| RNF-013 | Sin borrado físico de históricos | **Implementado por diseño** | API de solo lectura; filas de evaluación inmutables (`DT-059`). No hay una prueba dedicada identificada |
| RS-001–RS-003 | Entra ID, roles en el backend, validación en el servidor | **Implementado** | `tests/api` (`test_entra`); **[AZ-U]** 401 sin token en Azure (smoke) y matriz real de los cuatro roles y sin rol (registrada el 2026-10-11) |
| RS-005, RS-006 | Secretos fuera del repositorio; configuración por entorno | **Implementado** | `infra/ci/secret_scan.py` en CI; `APP_ENV` |
| RS-007 | Privilegio mínimo en la base (D) | **Propuesto, implementado** | `mpa_app` solo `SELECT` (`DT-100` punto 4) |
| RS-008 | Cifrado en tránsito | **Implementado en `dev`** | **[AZ-U]** Verify: frontend y api solo HTTPS, TLS obligatorio en PostgreSQL |
| RS-009 | Auditoría de acciones sensibles (D) | **Propuesto**; no implementado | V1 no tiene acciones de escritura que auditar |
| RS-012 | Datos no productivos sintéticos (D) | **Propuesto, cumplido de hecho** | Solo hay datos `SYNTHETIC` (`ASSUMPTION-001`) |
| RS-010 | El LLM no produce cifras | **Implementado** (sin LLM todavía) | `backend/tests/genai/test_verification.py` |
| RS-004, RS-011 | Permisos y protección frente a *prompt injection* en asistente y RAG | **Pendiente**: no hay asistente ni RAG | Fases 9–10 (U13, U15) |
| RS-013 | Versiones fijadas (B) y escaneo de vulnerabilidades (D) | **Parcial** | Versiones fijadas e imágenes por digest; sin escaneo |

**SLA, latencias, concurrencia y escalabilidad:** no hay ninguno aprobado. **Por definir por el propietario.**

---

## 8. Datos y modelos predictivos

| Aspecto | Situación |
|---|---|
| Dataset | `ds-6c8ad65b4999`, generador 0.4.0, semilla `20260913`, del 2023-01-01 al 2026-01-01. 100 productos, 10 categorías, 10 proveedores, una ubicación (`ASSUMPTION-006`). Lo publica el generador de `data/synthetic/` |
| Origen | **`SYNTHETIC`** en el manifiesto y por carga (`data_origin`). **No hay datos reales** (`ASSUMPTION-001`) |
| Validación | Componente 8: **51/51 comprobaciones**, `quality_report` `PASS` (`DT-042`). La ingesta de U2 vuelve a validar antes y después de cargar |
| Sintético frente a real | El sintético demuestra el mecanismo, no el fenómeno. Riesgos de sobreajuste al generador y de calidad de datos reales (`docs/02` R-01, R-02). **Ninguna métrica sintética es evidencia de desempeño con datos reales** (`docs/02` §14) |
| Modelo oficial | **MA13**, la media móvil de 13 semanas de U3: baseline oficial (`DT-089`). Respaldo naïve y, si no basta, sin pronóstico, de forma explícita |
| Evaluación | *Backtesting* con corte por fecha (`DT-075`); Nivel 1 (error) y Nivel 2 (efecto en las decisiones, `DT-080`); métrica primaria **MASE** (`DT-090`); umbrales provisionales (`DT-091`). Todo `SYNTHETIC` |
| Experimental | F5c: Holt, Holt-Winters, Croston, SBA y TSB. SES es el candidato fuerte, **no promovido**. F5d, G2 y G3 sin autorizar; el *holdout* no se ha usado |
| Selección de modelos | Ninguno se promueve sin superar al baseline (RML-002) y sin una decisión formal (`DT-084`, `DT-094` punto 9) |
| No calculables | Producto sin histórico suficiente → `INSUFFICIENT_HISTORY` / respaldo (`DT-056`). Evaluación sin datos válidos → `NOT_CALCULABLE` con `reasons` (`DT-053`). En el corte de referencia: 95 productos con pronóstico, 5 excluidos por vigencia, 10 evaluaciones `NOT_CALCULABLE` |
| Limitaciones | Banda 0,80 nominal, no calibrada. Desabasto no corregido en el pronóstico (`DT-011`). Incertidumbre sobre la demanda (`ASSUMPTION-023`). Sin calendario laboral (`BR-X06`). SKU independientes (`docs/02` §14) |
| Calidad predictiva real | **No medida.** No hay validación con datos reales |

---

## 9. Arquitectura y dependencias

Vista funcional. El detalle técnico está en [`docs/03`](03-arquitectura.md) §16 y en la guía maestra §A–§C.

| Capacidad | Módulo de negocio | Soporte |
|---|---|---|
| Datos de entrada | Generador (upstream congelado), U2 | PostgreSQL 16 (`DT-055`) |
| Pronóstico | U3 (`app.forecasting`, `app.runs`) | — |
| Decisión | U1 (`app.supply_engine`), ejecutada por U4 | — |
| Consulta | U5 (`app.api`, `app.db.read`) | Entra ID (U11) |
| Explicación | U6 (`app.genai`) | — |
| Presentación | Interfaz (Fase 7, `frontend/`) | nginx en la imagen `frontend` |
| Analítica | U9 (vistas) | Power BI (U16, sin autorizar) |
| Ejecución reproducible | — | U7 (Docker), U8 (CI) |
| Entorno desplegado | — | U10 (base de Azure), U11 (Entra), U12 (Container Apps, ACR, PostgreSQL gestionado) |

**Dependencias externas.** Están encapsuladas tras puertos (`docs/03` §16.5, `DT-094` punto 2):

- **Desplegadas en `dev`:** PostgreSQL, Entra ID, Azure OpenAI (U13) y Azure ML (U14).
- **Implementada en rama:** Azure AI Search (U15), sin despliegue mientras se evalúa la opción compatible de menor costo; el corpus empresarial sigue bajo `ASSUMPTION-008`.

---

## 10. Fuera de alcance y evolución futura

**Fuera del producto** (`CLAUDE.md` §3, `docs/02` §3):

- compras automáticas sin aprobación humana;
- integración con un ERP concreto;
- optimización de transporte;
- gestión de almacén (WMS);
- *pricing*;
- MRP multinivel;
- finanzas y contabilidad.

**Dentro del alcance de la Etapa 2** (`DT-094`, cada unidad requiere su propia autorización):

- **Implementadas y verificadas en `dev`:** U13 Azure OpenAI tras `TextGenerator`; U14 Azure ML (registro versionado de MA13).
- **U15 AI Search:** implementación sintética en rama; despliegue pendiente de evaluar la opción compatible de menor costo y obtener decisión. **Pendiente de autorización:** U16 Power BI.
- **Posteriores:** QA y entrega.

`DT-094` punto 1 los mantiene **dentro** del alcance de la Etapa 2. **No** forman parte del MVP local funcional (punto
10); ver [`docs/00b-mvp.md`](00b-mvp.md) §1.

**Aplazado por decisión dentro de V1:**

- escrituras y administración (`docs/07` §7.3);
- resolución humana de recomendaciones (`DT-059`);
- riesgo, urgencia y dashboard priorizado (`BR-X03`);
- vista de proveedores;
- asistente.

**Posterior:**

- promoción de modelos, G2 y G3;
- estrategia (b) de `DT-011`;
- `staging` y `prod`.

---

## 11. Riesgos, supuestos y dependencias

| Riesgo | Fuente | Situación |
|---|---|---|
| Datos reales de peor calidad que los sintéticos | `docs/02` R-01 | Abierto: no hay datos reales |
| Sobreajuste al generador | `docs/02` R-02 | Mitigado: MA13 como baseline y sin promoción |
| Faltan parámetros de negocio | `docs/02` R-03 | Abierto: `V1_PROVISIONAL` |
| LLM usado como calculadora | `docs/02` R-04 | Mitigado: RS-010 y U6 sin LLM |
| Costes de Azure | `docs/02` R-05, `DT-094` punto 4 | Azure for Students: USD 100 de crédito total; se conserva el umbral de planificación de USD 50 y se priorizan opciones sin costo o de consumo controlado. Search U15 aún requiere validar compatibilidad y precio regional |
| El planificador no confía en la recomendación | `docs/02` R-08 | Mitigado: desglose y explicación |
| La evidencia de Azure la aporta el responsable y no está versionada | Informe de U12 §0 | Aceptado y etiquetado como [AZ-U] |

**Supuestos** (todos en [`knowledge/assumptions.md`](../knowledge/assumptions.md), revocables):

| Supuesto | Contenido |
|---|---|
| `ASSUMPTION-001` | Datos sintéticos |
| `ASSUMPTION-006` | Ubicación única |
| `ASSUMPTION-010` | Cuatro roles |
| `ASSUMPTION-011` | Rendimiento |
| `ASSUMPTION-012` | Volumen |
| `ASSUMPTION-013` | Disponibilidad |
| `ASSUMPTION-021` | Revisión semanal |
| `ASSUMPTION-022` | `z_v1` = 1,65 |
| `ASSUMPTION-023` | Incertidumbre sobre la demanda |
| `ASSUMPTION-024` | Lead time observado |

Ninguno es un requisito.

**Dependencias:**

- **Del negocio:** los parámetros de política (`docs/01` §7).
- **Del propietario:** cada autorización de unidad y la sesión de Azure para las pruebas reales (`CLAUDE.md` §17).

---

## 12. Trazabilidad y preguntas abiertas

### 12.1 Cadena de trazabilidad

| Requisitos | Decisiones | Módulo | Pruebas y evidencia | MVP | Roadmap |
|---|---|---|---|---|---|
| RF-022, RF-023, RNF-013 | `DT-044`, `DT-055`, `DT-063` | U2 | `tests/ingestion`, `tests/db`; *bootstrap* idempotente | `00b-mvp` MVP-01 | U2 |
| RF-010, RML-001/002/006/007/008 | `DT-046`, `DT-056`, `DT-057`, `DT-089` | U3 | `tests/forecasting`, `tests/db`; `docs/05` §19.9 | MVP-02 | U3 |
| RF-011, RF-012, RNF-001, RNF-002 | `DT-031`, `DT-045`, `DT-048`–`DT-054` | U1 | `tests/supply_engine` (146) | MVP-03 | U1 |
| RF-015, RF-024, RNF-005 | `DT-058`–`DT-063` | U4 | `tests/runs`, `tests/db`; `docs/06` §16.13.4 | MVP-03, MVP-04 | U4 |
| RF-003, RF-006, RF-009, RS-001–RS-003 | `DT-064`–`DT-067`, `DT-099` | U5, U11 | `tests/api`, `tests/db/test_api_*`; `docs/07` §7.5 | MVP-05, MVP-07 | U5, U11 |
| RF-019 (parcial), RS-010 | `DT-068`, `DT-069` | U6 | `tests/genai`; `docs/09` §14.6 | MVP-06 | U6 |
| RF-017 | `DT-070` | Fase 7 | Vitest (176); prueba real de U11 | MVP-07 | Fase 7 |
| RNF-006, RNF-007, RS-005 | `DT-095`, `DT-096` | U7, U8 | CI en verde en `main` | MVP-08 | U7, U8 |
| RF-018 (parcial) | `DT-097` | U9 | `tests/db` (vistas) | Fuera del núcleo del MVP | U9, U16 |
| RS-008 y despliegue | `DT-098`–`DT-100` | U10–U12 | Informe de U12 (C01–C15) | Objetivo separado (`00b-mvp` §1) | U10–U12 |

Los criterios del MVP (MVP-01…) están en [`docs/00b-mvp.md`](00b-mvp.md) §6.

### 12.2 Preguntas abiertas que afectan al producto

1. **Resuelto (2026-10-14):** RF-013/RF-014, urgencia y la vista priorizada quedan fuera del MVP mientras siga abierto `BR-X03`; permanecen como requisitos pendientes del producto.
2. **Resuelto (2026-10-14):** las escrituras de RF-001, RF-004, RF-005 y RF-008 quedan fuera del MVP; para esta versión basta la ingesta batch.
3. ¿Se confirman los cuatro roles y su alcance (`ASSUMPTION-010`)?
4. ¿Qué parámetros de política aporta el negocio para dejar de ser `V1_PROVISIONAL` (`docs/01` §7)?
5. **Resuelto (2026-10-14):** el propietario aprobó este PRD y el MVP como base para futuras sesiones, con los límites descritos en `docs/00b-mvp.md`.
