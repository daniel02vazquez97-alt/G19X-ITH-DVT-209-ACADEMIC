# MVP — Motor Predictivo de Abastecimiento de Inventarios

## 0. Control del documento

| Campo | Valor |
|---|---|
| Propósito | Delimitar la **primera versión funcional** y fijar **cómo se acepta**. El «qué producto y por qué» está en el PRD ([`docs/00a-prd.md`](00a-prd.md)) |
| Estado | **Aprobado por el propietario** (2026-10-14), con el alcance vigente de §1 y §4. Actualizado el 2026-10-20: estado de U13–U16 en §1.1, §4 y §8. **Cerrado para la revisión el 2026-10-21** (§8) |
| Fuente principal del alcance | `DT-094` (`ACEPTADA`, 2026-10-06), puntos 2, 9, 10 y 11 |
| Fuentes de los criterios | Criterios de cierre ya existentes: [`docs/05`](05-motor-predictivo.md) §19.9 (U3), [`docs/06`](06-motor-abastecimiento.md) §16.13.4 (U4), [`docs/07`](07-api.md) §7.5 (U5), [`docs/09`](09-ia-generativa.md) §14.6 (U6), [`docs/08`](08-frontend.md) §12.1 (Fase 7), `DT-095` (U7) |
| Estado vivo | [`project/status.md`](../project/status.md). Si este documento lo contradice, manda `status.md` y este documento se corrige |

---

## 1. Definición del MVP

### 1.1 Qué dice la decisión aprobada

`DT-094` (`ACEPTADA`) separa cuatro clases de trabajo (punto 10):

| Clase de `DT-094` | Qué incluye | Relación con este documento |
|---|---|---|
| **MVP local funcional (sin Azure)** | El sistema local: U1–U6 y la Fase 7 son «la base que no se pierde» (punto 2), ejecutable sin Azure y sin credenciales (RNF-006) | **Es el MVP de este documento** |
| Stack de Azure | Servicios tras los puertos (U10–U16) | **Objetivo separado**, dentro del alcance de la Etapa 2 |
| Experimental | F5c y otros estudios | Fuera del MVP |
| Posterior | G2, G3 y promoción de modelos | Fuera del MVP |

`DT-094` punto 1 dejó **sin efecto** que los servicios de Azure fueran «posteriores al MVP». Siguen **dentro del
alcance de la Etapa 2**, pero el punto 10 los clasifica **aparte** del MVP local funcional. Por eso:

- **El MVP funcional no se amplía** con U10–U16. El despliegue de `dev` (U12) demuestra que el mismo sistema funciona
  en Azure. Es un hito propio, con su matriz de cierre en
  [`docs/reports/u12-cierre-evidencias.md`](reports/u12-cierre-evidencias.md).
- **Las unidades de servicio** U13 (Azure OpenAI), U14 (Azure ML), U15 (AI Search) y U16 (Power BI) no forman parte del
  MVP. U13 y U14 están implementadas y verificadas en `dev`. U15 está desplegada y verificada en `dev` (Search Free, solo
  Entra ID, 2026-10-18) y la usa el **asistente documental U15b** (`DT-103`), un extra fuera del MVP: una pregunta sobre
  los documentos sintéticos se responde con fragmentos citados; sin Azure, con el corpus local y solo los fragmentos.
  La aplicación muestra además la referencia del modelo registrado en Azure ML (`DT-104`). **U16 no se implementa en
  esta entrega:** el alcance se cierra aquí (retroalimentación de la revisión del 2026-10-20).

### 1.2 Definición operativa

**MVP = el recorrido completo** dataset → ingesta → pronóstico → evaluación → recomendaciones → API → explicación →
interfaz. Funciona en local con un solo comando, sin Azure ni credenciales, sobre el dataset `SYNTHETIC` 0.4.0 y con
reglas `V1_PROVISIONAL`, y es reproducible, trazable y de solo lectura.

### 1.3 Decisiones de alcance del propietario (2026-10-14)

El propietario revisó y aceptó la definición operativa y los límites de este MVP:

- RF-013/RF-014, urgencia y la vista priorizada quedan fuera del MVP mientras los umbrales de negocio `BR-X03` sigan pendientes. Son requisitos pendientes del producto, no requisitos eliminados.
- Las escrituras de RF-001, RF-004, RF-005 y RF-008 quedan fuera del MVP; el recorrido usa ingesta batch.
- U7–U9 se clasifican como soporte del sistema, no como capacidades funcionales adicionales del MVP. U7 sigue siendo el medio de ejecución verificable del criterio MVP-08; CI (U8) y analítica (U9) no amplían el alcance funcional.
- El alcance aceptado es el recorrido y los criterios MVP-01…MVP-09 descritos aquí. Los parámetros de negocio y la validación de los roles siguen abiertos en el producto y no se convierten por esta aprobación en valores confirmados.

---

## 2. Usuarios y recorrido principal

**Usuarios:** los perfiles de consulta, análisis y planificación del PRD §4, con los roles técnicos `VIEWER`,
`ANALYST`, `PLANNER` y `ADMIN`. En el MVP local se autentican con identidades **ficticias** de desarrollo
(`APP_ENV=local`, `DT-065`); con Entra ID, en `dev` (U11).

**Recorrido demostrable**, el mismo que ejecuta `docker compose -f infra/docker-compose.yml --profile app up --build -d`:

| Paso | Qué ocurre | Módulo | Resultado observable |
|---|---|---|---|
| 1 | Se publica el dataset sintético | Generador | `ds-6c8ad65b4999`, `quality_report` `PASS` |
| 2 | Se aplican las migraciones y se carga el dataset | U2 | Carga `COMPLETED`; una repetición da `ALREADY_LOADED` |
| 3 | Pronóstico al corte `2025-12-31` | U3 | 95 productos, 3 990 filas; repetición `ALREADY_COMPUTED` |
| 4 | Evaluación y recomendaciones al mismo corte | U4 + U1 | 100 evaluaciones: 50 `RECOMMEND`, 40 `NO_NEED`, 10 `NOT_CALCULABLE` |
| 5 | Consulta autenticada | U5 | 14 endpoints `GET`; 401 sin token y 403 sin rol |
| 6 | Explicación de una recomendación | U6 | Narrativa `VERIFIED` con `facts[]`, sin cifras nuevas |
| 7 | Presentación | Interfaz | Productos, inventario, detalle, predicciones, recomendaciones con desglose y explicación, ejecución (`PLANNER`/`ADMIN`), con avisos visibles de dato sintético y política provisional |

---

## 3. Alcance incluido

| Capacidad | Módulo | Resultado esperado | Estado real | Evidencia | Limitaciones conocidas |
|---|---|---|---|---|---|
| Dataset de demostración | Generador | Dataset reproducible y validado | **Completado** | 51/51 comprobaciones (`DT-042`); 582 pruebas del generador | Sintético; upstream congelado |
| Ingesta validada | U2 | Carga todo o nada, idempotente, con filas rechazadas reportadas | **Completado** | `docs/04` §9.9; `tests/ingestion`; `tests/db` | Una ubicación; sin escrituras posteriores |
| Pronóstico con baseline oficial | U3 | MA13 y respaldos, 14 semanas, intervalo | **Completado** | `docs/05` §19.9 (criterios cumplidos) | Banda nominal 0,80 sin calibrar; desabasto sin corregir (`DT-011`) |
| Evaluación de abastecimiento | U1 | Reglas V1 deterministas con desglose | **Completado** | 146 pruebas; `docs/06` §16.12 | Parámetros `V1_PROVISIONAL` (`DT-031`); sin `σ_L`, riesgo ni calendario |
| Recomendaciones persistidas y trazables | U4 | Una fila inmutable por evaluación con `input_sha256` | **Completado** | `docs/06` §16.13.4 (criterios cumplidos, en local y Docker) | Solo cargas `SYNTHETIC` (`DT-063`) |
| API de consulta | U5 | 14 endpoints de solo lectura con `provenance` | **Completado** | `docs/07` §7.5 (20 criterios cumplidos) | Sin escrituras ni `/risks` |
| Explicación | U6 | Plantilla verificada con degradación | **Completado** | `docs/09` §14.6 (criterios cumplidos); 100 evaluaciones sin `DEGRADED` | Sin LLM (U13 fuera del MVP) |
| Interfaz | Fase 7 | Vistas de solo lectura sin reglas de negocio | **Completado** | `docs/08` §12.1; Vitest (176 pruebas, 2026-10-10 **[CC]**) | Sin dashboard, riesgos, acciones, proveedores ni administración |
| Ejecución reproducible en un comando | U7 | Sistema completo `healthy` y smoke correcto, sin credenciales | **Implementado y en CI** | Job `docker` en verde en `main` `62f25ca` (run 38035570538) **[CI]** | La revisión formal de U7 sigue marcada como pendiente (guía §H, K-04) |

---

## 4. Fuera de alcance

| Elemento | Clasificación | Fuente |
|---|---|---|
| Riesgo de desabasto, sobreinventario, urgencia y dashboard priorizado (RF-013, RF-014, RNF-012) | **Aprobado, pendiente**: bloqueado por `BR-X03`. No se elimina del producto | `docs/06` §16.7, `docs/08` §12 |
| Alta, edición y registro de maestros, movimientos, órdenes y recepciones (escrituras de RF-001, RF-004, RF-005 y RF-008) | **Aprobado, aplazado** en V1 | `docs/07` §7.3 |
| Resolución humana de recomendaciones (atender, descartar o convertir) | Aplazado | `DT-059` |
| Desempeño de proveedores (RF-016) | Propuesta no vinculante | `docs/01` §5, `BR-X05` |
| Azure OpenAI, Azure ML, AI Search, Power BI (U13–U16) | Stack de Azure, **fuera del MVP**. U13, U14 y U15 desplegadas y verificadas en `dev`; U15b (asistente documental) y U14b (referencia del modelo de Azure ML) como extras; U16 no se implementa en esta entrega | `DT-094` puntos 3 y 10; `DT-101` a `DT-104` |
| Despliegue en Azure `dev` (U10–U12) | **Objetivo separado** del MVP funcional | `DT-094` punto 10; informe de U12 |
| Modelos experimentales (SES y los candidatos de F5c), F5d, G2, G3, promoción y uso del *holdout* | Experimental o posterior | `DT-094` puntos 9 y 10 |
| Estrategia (b) de `DT-011` | Sin autorizar | `DT-094` punto 9 |
| Datos reales; validación predictiva con datos reales | No realizado; **no es un requisito del MVP** según las decisiones vigentes | `ASSUMPTION-001`, `DT-063`, `DT-P16` |
| Pruebas de rendimiento, SLA y disponibilidad | Sin umbral aprobado (RNF-003, RNF-004 y RNF-009 son `SUPUESTO`) | `docs/01` §5 |
| `staging` y `prod` | Sin decidir | `DT-100` |

---

## 5. Baseline y limitaciones

- **MA13 es el baseline oficial de pronóstico** (`DT-089`) y el que usa el MVP. Ningún otro modelo se promueve sin una
  decisión formal (`DT-084`, `DT-094` punto 9).
- **Toda la evaluación es `SYNTHETIC`.** Los resultados de F5a–F5c (MASE, Nivel 2) demuestran el protocolo, **no** el
  rendimiento con datos reales.
- La demostración del MVP sobre datos sintéticos prueba que **el mecanismo funciona**: cálculo correcto, reproducible,
  trazable y explicado. **No** prueba que las recomendaciones sean buenas para un negocio real.

**Riesgos que introduce:**

- sobreajuste al generador (`docs/02` R-02);
- calidad de datos reales desconocida (R-01);
- parámetros de política provisionales (R-03).

**Qué evidencia los resolvería:**

- una carga de datos reales con su `data_origin`, que exige decidir `DT-P16`;
- los parámetros de política del negocio (`docs/01` §7);
- un *backtesting* y un Nivel 2 sobre esos datos.

**Nada de esto es un requisito nuevo del MVP:** las decisiones vigentes no lo exigen.

---

## 6. Criterios de aceptación del MVP

Reutilizan los criterios de cierre existentes. **Ninguno introduce umbrales** de precisión, ahorro, velocidad o
disponibilidad. Las etiquetas de evidencia son las de [`docs/00-guia-maestra.md`](00-guia-maestra.md) §G.2.

**Estados:**

- **Cumplido**: hay evidencia de que se cumplió el criterio de origen;
- **Pendiente de evidencia**;
- **Pendiente**.

| ID | Requisito que verifica | Procedimiento | Resultado esperado | Fuente autoritativa | Evidencia disponible | Estado |
|---|---|---|---|---|---|---|
| MVP-01 | RF-022, RF-023 (marca de origen), RNF-013 | `python -m app.db migrate` y `python -m app.ingestion <dataset>`, dos veces; suites `tests/ingestion` y `tests/db` | 1.ª `COMPLETED`; 2.ª `ALREADY_LOADED` sin escribir; las invariantes en verde | `docs/04` §9.9 | U2 validada (2026-10-01); `tests/db` 177 OK y *bootstrap* ×2 **[CC]** (2026-10-10) | **Cumplido** |
| MVP-02 | RF-010, RML-001/002/006/007 | `python -m app.runs forecast --as-of 2025-12-31`, dos veces | 95 productos, 5 excluidos, 3 990 filas, 1 330 primarias de MA13; la 2.ª da `ALREADY_COMPUTED` | `docs/05` §19.9 (criterios 1–12) | U3 validada (2026-10-02); repetido **[CC]** 2026-10-10 | **Cumplido** |
| MVP-03 | RF-011, RF-012, RF-015, RNF-001, RNF-002 | `python -m app.runs recommend --as-of 2025-12-31`; suite `tests/supply_engine` | 100 evaluaciones (50/40/10), con la misma `input_sha256` en ejecuciones independientes | `docs/06` §16.13.4 | U4 validada en local y Docker (2026-10-03); 146 pruebas de U1 | **Cumplido** |
| MVP-04 | RF-024 | Desde `/recommendations/{id}`, recuperar el pronóstico, la versión del motor, la política y la carga | Todos los insumos identificados en `provenance` y en el desglose | `docs/06` §16.13.4; `DT-059`–`DT-062` | Criterios de U4 cumplidos | **Cumplido** |
| MVP-05 | RS-001–RS-003, RF-009, RF-017 (fuente de datos) | `tests/api` y `tests/db/test_api_*`; recorrido de los 14 endpoints | Matriz 14 × 4 más petición sin token; 401, 403, 404, 405 y 422; ninguna escritura | `docs/07` §7.5 (20 criterios) | Cumplidos (2026-10-03/04); `tests/api` 95 OK **[CC]** 2026-10-10 | **Cumplido** |
| MVP-06 | RS-010, RF-019 (criterio de coherencia) | `tests/genai`; endpoint 14 sobre las 100 evaluaciones | `VERIFIED` sin cifras ajenas al contexto; degradación ante una discrepancia | `docs/09` §14.6 | Cumplido (2026-10-04): 100 sin `DEGRADED` | **Cumplido** |
| MVP-07 | RF-017 | `npm run lint`, `typecheck`, `format:check`, `test` y `build`; navegación sobre la API local | Vistas de `docs/08` §12 con datos de la API y avisos `SYNTHETIC_DATA` / `V1_PROVISIONAL_POLICY` visibles | `docs/08` §12.1, `DT-070` | Fase 7 integrada (PR #2–#5); Vitest 176 OK **[CC]** 2026-10-10 | **Cumplido** |
| MVP-08 | RNF-006, RNF-005 | `docker compose -f infra/docker-compose.yml --profile app up --build -d` y `python infra/docker/smoke.py` | Servicios `healthy`; smoke frontend → API → PostgreSQL correcto, sin credenciales | `DT-095`, `docs/12` §3.4 | Job `docker` de CI en verde en `main` `62f25ca` **[CI]**, con las bases oficiales por digest; verificación de U7 con imágenes base sustitutas (`DT-095`) | **Cumplido** |
| MVP-09 | Manejo de errores (RF-010, RF-015, `DT-066`) | Casos `INSUFFICIENT_HISTORY`, `NOT_CALCULABLE`, ejecución inexistente y entrada inválida | Resultado explícito con `reasons`, nunca un 404 para `NO_NEED`/`NOT_CALCULABLE`; errores con formato uniforme y `X-Correlation-ID` | `docs/07` §7.5 (criterios 7, 10 y 11); `DT-053` | Cubierto por los criterios de U4 y U5 | **Cumplido** |
| MVP-10 | Aceptación formal del MVP | Revisión del propietario de este documento y del PRD, y decisión sobre §1.3 y §4 | MVP aceptado, o lista de cambios | Decisión explícita del propietario en esta sesión: límites actuales aceptados; riesgos/urgencia y escrituras fuera; U7–U9 como soporte | Respuesta del propietario del 2026-10-14 | **Cumplido** |

**Matriz C01–C15 de U12.** Es una matriz de **seguimiento derivada** del objetivo separado de despliegue, en estado
`PROPUESTA`. **No es un criterio del MVP** ni un requisito preexistente.

---

## 7. Definición de «terminado»

Estados distintos, no equivalentes (`DT-094` punto 11 y guía §G.2):

| Estado | Significa | Ejemplo en el proyecto |
|---|---|---|
| Código implementado | Existe y compila | — |
| Pruebas automatizadas aprobadas | Suites en verde (local o CI) | `tests/api` 95 OK |
| Prueba de integración local | Contra PostgreSQL real o Docker | `tests/db`; smoke de U7 |
| Despliegue realizado | El sistema corre en un entorno desplegado | U12: `u12-dev` `Succeeded` **[AZ-U]** |
| Validación real del entorno desplegado | Pruebas reales en ese entorno: Verify, E2E, redespliegue y fallos | U12 **cerrada el 2026-10-13** con pendientes aceptados: Verify 20/20, matriz de autorización E2E, sin token → 401, redespliegue y pruebas de fallo **[AZ-U]**; pendientes P1–P5 del informe de U12 §4 (vistas, idempotencia detallada, imagen inexistente) |
| Documentación y evidencia de aceptación | Criterios con evidencia y estado documentados y aceptados | MVP-01…09 documentados; MVP-10 aceptado por el propietario el 2026-10-14 |

**El MVP está «terminado»** cuando MVP-01…MVP-09 están cumplidos **y** MVP-10 (aceptación del propietario) está
cumplido.

---

## 8. Estado del MVP a 2026-10-14

| Categoría | Contenido |
|---|---|
| Completado | MVP-01 a MVP-10, con la evidencia de §6 y la aprobación del propietario |
| Implementado, pendiente de evidencia | Nada dentro del MVP. Fuera de él: verificaciones pendientes aceptadas de U12 (informe de U12 §4, P1–P5) |
| Pruebas bloqueadas | Ninguna del MVP. Las de U12 en Azure no se pueden ejecutar desde Claude Code Cloud: sin Azure CLI ni credenciales, red bloqueada a `*.azurecontainerapps.io`, sin navegador. Las ejecuta el responsable |
| Experimental | F5c (candidatos), SES sin promover; todo `SYNTHETIC` |
| Decisiones pendientes | `BR-X03`; validación de roles (`ASSUMPTION-010`); parámetros de política; `DT-P16`; corpus empresarial (`ASSUMPTION-008`) |
| Próximo hito concreto | El MVP y el PRD están aceptados. *(Actualización 2026-10-20:)* U15 y el asistente U15b están verificados en `dev`; el alcance se cierra y el trabajo pasa a la entrega: README, capturas y demo local sin Azure. U16 no se implementa. *(Cierre 2026-10-21:)* **MVP cerrado para la revisión**: demo local probada en un clon limpio (`SMOKE OK` 9/9), U14b desplegada y verificada, imágenes `2e079c4` en `dev` con Verify 20/20 y cuatro capturas en `docs/img/`. Sin trabajo nuevo pendiente dentro del MVP |

**El MVP está aceptado**: MVP-01…MVP-09 tienen evidencia documentada y MVP-10 fue aprobado por el propietario el 2026-10-14.

---

## 9. Riesgos y plan mínimo de cierre

**Aceptación:** MVP-10 está cumplido. El propietario resolvió las decisiones de alcance de §1.3; `BR-X03`, los parámetros de negocio y la validación de roles siguen abiertos para el producto, pero no bloquean la aceptación de este MVP.

**Plan mínimo:**

1. Conservar esta decisión de alcance en `project/status.md` y `project/roadmap.md`.
2. Antes de desplegar U15, comparar Free, Serverless Developer (preview) y Basic con precios de la región y confirmar Entra ID sin claves; no provisionar hasta decidir y autorizar el costo. Validar el corpus empresarial requerido por `ASSUMPTION-008` antes de usar documentos reales.

**Lo que no debe ampliar el MVP:**

- cerrar U12;
- U13–U16;
- promoción de modelos;
- datos reales;
- rendimiento.

Son objetivos posteriores o separados, cada uno con su propia autorización (`DT-094` punto 3).

**Riesgos:**

| Riesgo | Mitigación |
|---|---|
| Confundir la demostración sintética con una validación real | §5 y avisos visibles en la API y en la interfaz |
| Ampliar el MVP por arrastre del stack | §1 y la regla de la guía maestra |
| Requisitos «Debe» aprobados que no entran en V1 sin una decisión explícita | §1.3 y PRD §12.2 |
