# 13 — Estrategia de testing

**Estado:** Versión 1.0 — Etapa 0 (estrategia, **no implementada**) · **Fecha:** 2026-09-04 · **Versión 1.1** — revisada en la auditoría de Etapa 0.1 · **Versión 1.2** (2026-09-30) — §14, capas de prueba de la Etapa 2; §§1–13 no cambian · **Versión 1.3** (2026-10-01) — §3.1: aclaración de `InvalidInputError` y excepción de `on_hand < 0` para U1 (`DT-052`) · **Versión 1.4** (2026-10-01) — §3.1: sin monotonía global del punto de reorden frente al lead time en U1 (`DT-054`) · **Versión 1.5** (2026-10-01) — §14: dónde viven las suites de U2 (`DT-055`) · **Versión 1.6** (2026-10-03) — §14: pruebas exigibles de U4 (autorizada, no implementada; `DT-058` a `DT-063`) · **Versión 1.7** (2026-10-03) — §14: pruebas exigibles de U5 (autorizada, no implementada; `DT-064` a `DT-067`) y rutas públicas de la capa API · **Versión 1.8** (2026-10-03) — §14: U5 implementada; registro de sus suites · **Versión 1.9** (2026-10-04) — §14: pruebas exigibles de U6 (autorizada, no implementada; `DT-068` y `DT-069`) · **Versión 1.10** (2026-10-04) — §14: U6 implementada; registro de sus suites · **Versión 1.11** (2026-10-05) — §14: capa «Interfaz» de la Fase 7 (autorizada, no implementada; `DT-070`)

---

## 1. Principio rector

**Se prueba con más intensidad donde un error cuesta más.**

En este sistema, el error más caro no es una pantalla mal alineada: es una recomendación de compra
incorrecta que produce un desabasto o inmoviliza capital. De ahí la prioridad:

```
supply_engine  >  API + datos  >  pipeline de ML  >  ingesta  >  frontend
```

El motor de abastecimiento es **puro y determinístico**, lo que significa que puede probarse de forma
exhaustiva con casos calculados a mano. Es la parte más fácil de probar y la que más lo merece: no
aprovecharlo sería un desperdicio.

## 2. Pirámide de pruebas

```
        ╱╲          E2E (pocas, flujos críticos)
       ╱  ╲
      ╱────╲        Integración (API + base de datos)
     ╱      ╲
    ╱────────╲      Unitarias (muchas, rápidas, deterministas)
```

Regla práctica: las pruebas unitarias deben ejecutarse en segundos. Una suite lenta se acaba
ejecutando poco, y entonces deja de proteger.

## 3. Unit testing

**Objetivo:** verificar unidades de lógica de forma aislada, rápida y determinista.

### 3.1 Motor de abastecimiento — prioridad máxima

Pruebas con **valores exactos calculados a mano**, no aproximaciones.

Cobertura obligatoria:

| Grupo | Casos |
|---|---|
| **Posición de inventario** | `IP_decisión = OH + IT_efectivo − RSV` y `IP_contable` con `IT_total`, en todas las combinaciones; tránsito **efectivo** mayor que el ROP; y el caso inverso: tránsito **total** mayor que el ROP con efectivo insuficiente |
| **Demanda durante lead time** | Demanda constante y variable; lead time cero, fraccionario y largo |
| **Stock de seguridad** | Solo variabilidad de demanda; solo de lead time; ambas; `σ_D = 0`; `σ_L = 0` |
| **Punto de reorden** | Revisión continua y periódica |
| **Cantidad recomendada** | Sin restricciones; con MOQ; con múltiplo; con ambos; MOQ mayor que la necesidad |
| **Riesgos** | Cada nivel de clasificación en sus fronteras exactas |
| **Casos límite** | Los catorce de `docs/06-motor-abastecimiento.md` §14 |
| **Parámetros faltantes** | Sin nivel de servicio definido → no calcula y **declara qué falta**; nunca sustituye por un valor por defecto |
| **Entradas inválidas** | Cantidades negativas, fechas incoherentes, unidades incompatibles → error explícito. En U1, el error es `InvalidInputError` con su catálogo y orden de validación (`docs/06` §16.11.5, `DT-052`). **Excepción normativa específica de U1:** `on_hand < 0` no es entrada inválida, sino `NOT_CALCULABLE` con `NEGATIVE_ON_HAND` (`V1-13`, `docs/06` §16.5); el resto de cantidades negativas sigue siendo error. V1 no tiene campo de unidad, de modo que «unidades incompatibles» no aplica a U1 |

**Propiedades a verificar** (además de los casos puntuales): monotonía —a mayor variabilidad, mayor
stock de seguridad; a mayor lead time, mayor punto de reorden—; no negatividad de toda cantidad
recomendada; y determinismo estricto: la misma entrada produce siempre la misma salida. **En U1 (V1)**, la
monotonía del punto de reorden frente al lead time **no se exige**: `σ_H` depende de `H = L + R` y no es
monótona en `H`; se prueban `H = L + R` y `H ≥ 7` (`DT-054`, `docs/06` §16.11.7).

### 3.2 Resto de módulos

| Módulo | Qué se prueba |
|---|---|
| Cálculo de lead time observado | Agregación desde recepciones; órdenes parciales; órdenes canceladas |
| Métricas de proveedor | Cumplimiento en tiempo y cantidad; ventanas sin órdenes |
| Validaciones de dominio | Reglas de transición de estado, unicidad, coherencia de unidades |
| Utilidades de fechas y periodos | Conversión entre granularidades; semanas a caballo entre meses |

## 4. Integration testing

**Objetivo:** verificar que los componentes funcionan juntos: aplicación, base de datos y transacciones.

- Base de datos **real** en contenedor (no simulada): las diferencias de comportamiento son
  precisamente lo que estas pruebas deben detectar.
- Estado inicial conocido por prueba; sin dependencia del orden de ejecución.
- Casos: persistencia y recuperación de entidades, integridad referencial, reconstrucción del
  inventario desde los movimientos, cálculo del tránsito desde órdenes vigentes, migraciones aplicadas
  desde cero y sobre un esquema existente.
- Verificación clave: **la posición de inventario almacenada coincide con la reconstruida desde el
  histórico de movimientos.** Una discrepancia aquí es un defecto grave, no un redondeo.

## 5. API testing

**Objetivo:** verificar el contrato tal como lo ve un cliente.

| Grupo | Casos |
|---|---|
| **Contrato** | Esquema de respuesta conforme a OpenAPI; tipos y campos obligatorios |
| **Validación** | Entradas inválidas → 400/422 con mensaje útil |
| **Autenticación** | Sin token → 401; token expirado → 401; audiencia incorrecta → 401 |
| **Autorización** | Cada rol contra cada endpoint; sin rol → 403. Recorrer la matriz completa |
| **Paginación y ordenación** | Límites, valores extremos, coherencia de `total` |
| **Errores** | Formato uniforme; **sin filtración** de trazas ni detalles internos |
| **Idempotencia** | Repetición de operaciones idempotentes |
| **Asíncronas** | Ciclo completo `202` → consulta de estado → resultado; conflicto por ejecución duplicada |
| **Degradación** | Servicios externos caídos → respuesta degradada, no error 500 |

**Prueba de seguridad recurrente:** para cada endpoint, comprobar que un usuario con rol insuficiente
recibe 403 **aunque el frontend nunca le mostraría el botón**. La autorización se verifica en el
servidor y las pruebas deben demostrarlo.

## 6. ML testing

Las pruebas de ML **no verifican una métrica exacta** (que depende de los datos y cambia con cada
reentrenamiento), sino **propiedades e invariantes** que deben cumplirse siempre.

| Categoría | Qué se verifica |
|---|---|
| **Ausencia de leakage** | Ninguna feature en *t* usa información posterior a *t*. Prueba con datos construidos donde una fuga sería detectable de forma inequívoca |
| **Corrección temporal** | Los cortes del backtesting no se solapan; el gap se respeta; el holdout no se usa en entrenamiento |
| **Forma de la salida** | Un valor por periodo y serie; cantidades no negativas; `lower ≤ punto ≤ upper` |
| **Superación del baseline** | El modelo candidato supera al baseline en el conjunto de evaluación |
| **Reproducibilidad** | Dos ejecuciones con la misma semilla y los mismos datos producen métricas equivalentes |
| **Robustez** | Series con pocos datos, con ceros, constantes, con un único punto → no lanza excepción y declara su método |
| **Respaldo** | Sin modelo disponible, se usa baseline y `method_used` lo refleja |
| **Metadatos** | Toda predicción lleva versión de modelo, `as_of_date` y método |
| **Pipeline de features** | Transformaciones deterministas; ajuste de escalado solo con datos de entrenamiento |

### 6.1 Pruebas de la evaluación de Nivel 2

La evaluación de Nivel 2 (`DT-020`, `docs/05-motor-predictivo.md` §9.4–9.5) es código, y su corrección
determina si se promueve o no un modelo. Se prueba como cualquier otra lógica crítica:

| Qué se verifica | Cómo |
|---|---|
| **Igualdad de condiciones** | Las dos ramas de la comparación (baseline y ML) usan idénticas reglas, parámetros de política y cortes temporales. Una prueba alimenta ambas con el **mismo** forecast y comprueba que los resultados son idénticos: si difieren, algo más está cambiando |
| **Ausencia de información futura en la simulación** | La simulación retrospectiva en la fecha *t* no usa inventario, órdenes ni lead times posteriores a *t* |
| **Reproducibilidad** | Dos ejecuciones de la misma simulación producen las mismas métricas |
| **Cálculo de las métricas** | Cada métrica de Nivel 2 se verifica con un escenario pequeño construido a mano y resultado conocido |
| **Sensibilidad** | Un forecast deliberadamente sesgado a la baja debe producir **más** desabastos en la simulación. Si no lo hace, la simulación no está midiendo lo que dice medir |

Esta última es la prueba más valiosa: comprueba que el instrumento de medición funciona antes de
usarlo para tomar decisiones sobre qué modelo va a producción.

**Pruebas de regresión de datos:** verificar que la calidad de los datos de entrada cumple lo esperado
(rangos, nulos, duplicados, continuidad temporal) antes de entrenar. Un modelo entrenado sobre datos
corruptos no falla: produce basura convincente.

## 7. Security testing

| Categoría | Qué se verifica |
|---|---|
| **Secretos** | Detección automática en CI; el pipeline falla si encuentra uno |
| **Dependencias** | Análisis de vulnerabilidades conocidas |
| **Autenticación** | Tokens manipulados, sin firmar, expirados, con audiencia o emisor incorrectos → rechazados |
| **Autorización** | Matriz completa rol × endpoint; intentos de acceso a recursos ajenos |
| **Inyección** | SQL en parámetros; entradas maliciosas en campos de texto |
| **Inyección de prompt** | Instrucciones incrustadas en documentos indexados y en la pregunta del usuario → ignoradas |
| **Fuga por el asistente** | Un usuario no debe obtener, vía el asistente, datos o documentos fuera de su alcance |
| **Verificación de salida del LLM** | Respuestas con cifras ajenas al contexto → detectadas y degradadas |
| **Cabeceras y CORS** | Configuración correcta; sin comodines en producción |
| **Errores** | Sin filtración de información interna |

Las pruebas de inyección de prompt y de fuga por el asistente son específicas de este sistema y no
deben omitirse: son la contrapartida de haber incorporado un LLM.

## 8. Performance testing

| Escenario | Criterio |
|---|---|
| Listados paginados y detalle de producto | Objetivo p95 < 2 s con el volumen de referencia (ASSUMPTION-011/012) |
| Consulta de recomendaciones con filtros | Dentro del mismo objetivo |
| Proceso batch completo | Cabe en la ventana operativa definida |
| Inferencia de todo el catálogo | Dentro del tiempo del proceso batch |
| Carga masiva de datos | Volumen esperado sin agotar memoria |
| Consultas concurrentes | Comportamiento estable con la concurrencia prevista |

Se ejecutan sobre datos sintéticos representativos, no sobre un catálogo de juguete: probar el
rendimiento con cincuenta productos no informa de nada.

## 9. End-to-end testing

Pocas, sobre los flujos que realmente importan. Son lentas y frágiles; se reservan para lo crítico.

| Flujo | Recorrido |
|---|---|
| **Revisión diaria del planificador** | Login → dashboard → recomendación → desglose → convertir en orden |
| **Ciclo de vida del inventario** | Registrar consumo → cae la posición → se genera recomendación → orden → recepción → sube el inventario |
| **Carga de datos** | Subir archivo → validación → resultado con rechazos → datos disponibles |
| **Recálculo** | Disparar → seguimiento → resultados actualizados |
| **Autorización** | Un `VIEWER` no accede a acciones de `PLANNER`, ni por interfaz ni por API |

## 10. Qué se prueba en cada fase

| Fase | Pruebas introducidas |
|---|---|
| 1 — Datos | Validación del generador de datos y de la calidad del dataset |
| 2 — PostgreSQL | Integración: esquema, migraciones, integridad, reconstrucción de inventario |
| 3 — FastAPI | Contrato, validación, errores, paginación |
| 4 — Motor de abastecimiento | **Unitarias exhaustivas** con casos calculados a mano y casos límite |
| 5 — ML | Leakage, corrección temporal, forma de salida, baseline, reproducibilidad |
| 6 — Azure ML | Integración con el endpoint; respaldo al baseline ante fallo |
| 7 — React | Componentes, estados vacíos y de error, flujos principales |
| 8 — Entra ID | Autenticación y autorización completas |
| 9–10 — IA generativa | Fidelidad, citas, abstención, inyección de prompt, fuga |
| 11 — Power BI | Coherencia entre los KPIs del informe y los de la aplicación |
| 12–13 — DevOps | El pipeline falla cuando debe fallar |
| 14 — QA | End-to-end, rendimiento, seguridad integral |

## 11. Prácticas transversales

1. **Determinismo.** Sin dependencia del reloj real (tiempo inyectable), sin aleatoriedad no sembrada,
   sin dependencia del orden de ejecución.
2. **Sin red en pruebas unitarias.** Azure OpenAI, AI Search y Azure ML se sustituyen por dobles.
3. **Datos de prueba explícitos.** Constructores de datos legibles; el caso debe entenderse leyéndolo.
4. **Un motivo de fallo por prueba.** Una prueba que puede fallar por cinco razones no diagnostica nada.
5. **Nombres descriptivos.** El nombre de la prueba explica qué se espera y bajo qué condición.
6. **Toda corrección de defecto añade una prueba** que habría detectado ese defecto.
7. **Cobertura como señal, no como objetivo.** Un 90 % de cobertura con aserciones triviales es peor
   que un 60 % con pruebas significativas sobre la lógica crítica.

## 12. Ejecución

| Momento | Alcance |
|---|---|
| Durante el desarrollo | Pruebas del módulo afectado |
| Antes de proponer un cambio | Suite unitaria completa |
| En cada Pull Request | Unitarias + integración + seguridad |
| En `main` | Todo lo anterior + build |
| Programado (nocturno/semanal) | End-to-end, rendimiento, análisis de dependencias |

**Regla innegociable:** no se reporta trabajo terminado con pruebas en rojo. Si una prueba falla y no
puede arreglarse dentro del alcance, se reporta como bloqueo (`AGENTS.md` §6).

## 13. Pendiente de definición

- Objetivos numéricos definitivos de rendimiento (dependen del volumen real).
- Umbral de cobertura exigido en CI, por módulo.
- ¿Se requiere una revisión de seguridad externa antes de producción?
- Herramientas concretas de E2E y de carga (se elegirán en las Fases 7 y 14).

## 14. Etapa 2 — capas de prueba por unidad

*Añadido el 2026-09-30 (`DT-047`). Mismo principio de §1: más pruebas donde el error cuesta más.*

| Capa | Qué se prueba | Necesita | Unidad |
|---|---|---|---|
| Dominio | `supply_engine`: los once casos de motor de `DT-031`, los casos de `docs/06` §14 en su versión V1 (`docs/06` §16.8), propiedades (determinismo, no negatividad, monotonía) y que el paquete solo importa la biblioteca estándar | Python | U1 |
| Contrato de datos | Ingesta frente al dataset 0.4.0 real y frente a copias alteradas (cabecera, `sha256`, filas, `quality_report`, vocabularios) | Python | U2 |
| ETL / integración | Carga completa en PostgreSQL **real**; repetir la carga es un no-op; otro `dataset_version` se rechaza; reconciliación de inventario y tránsito; ninguna fila si falla | PostgreSQL local en contenedor | U2 |
| Contrato de forecast | Forma y rango de la salida, rechazo de histórico posterior a `as_of_date`, reproducibilidad | Python | U3 |
| Integración de ejecuciones | Base → forecast → motor → recomendaciones persistidas; cadena de trazabilidad completa hasta `dataset_version` | PostgreSQL local | U3–U4 |
| API | Esquema OpenAPI, formato de error, paginación, **matriz rol × endpoint**, ninguna ruta sin autenticación salvo `/health` y, solo en `local`, `/docs` y `/openapi.json` (`docs/07` §1, `DT-066`) | PostgreSQL local + `TokenValidator` de desarrollo | U5 |
| Interfaz | Componentes, carga, vacío, errores (401 → login, 403 en el sitio, 404, 422, 500 con `correlation_id`), autenticación simulada, roles, filtros y paginación en la URL, recomendaciones y `CalculationBreakdown`, los tres estados de la explicación, forecast con banda nominal y aviso `INSUFFICIENT_HISTORY`, `notices` visibles y **ausencia de fórmulas de negocio en el cliente**. E2E aplazada (`DT-P07`) | Node + Vitest + Testing Library (jsdom); sin red ni backend real | Fase 7 (`DT-070`) |
| IA generativa | La verificación detecta una cifra ajena al contexto (RS-010) y degrada; plantillas, `display`, `facts[]`, inmutabilidad, determinismo y ausencia de IA, base y recálculo (detalle al final de esta sección, `DT-068`, `DT-069`) | Python; endpoint con PostgreSQL local | U6 |

**Reglas de ejecución:** `unittest`, que es la convención vigente del repositorio (instalar `pytest`
no está autorizado). Las pruebas que necesitan PostgreSQL forman una **suite separada** que se ejecuta
explícitamente; no se «saltan» cuando falta la base, fallan. Ninguna prueba usa red, Azure ni el reloj
del sistema: `as_of_date` es siempre explícito (§11).

*Implementación en U2 (2026-10-01, `DT-055`):* la capa «Contrato de datos» está en
`backend/tests/ingestion` (suite por defecto, sin base; las pruebas que leen el dataset se saltan solo si
el dataset 0.4.0 no está publicado) y la capa «ETL / integración», en `backend/tests/db` (sin
`__init__.py`, fuera de la suite por defecto): `U2_TEST_ADMIN_DSN=… python3 -m unittest discover -s
tests/db -t tests/db`, desde `backend/`. Cada prueba crea su propia base temporal y altera solo copias
temporales del dataset.

*Pruebas exigibles de U4 (2026-10-03, `DT-058` a `DT-063`; U4 autorizada, **no implementada**; criterios
de cierre en `docs/06` §16.13.4):*

- **Adaptador, suite por defecto sin base** (`backend/tests/runs`): reglas de lectura de `docs/06`
  §16.13.2 (fechas UTC, `expected_on` de la cabecera, pendiente `> 0`, observación solo con la línea
  completa, consumo denso y hueco → error, orden canónico); serie primaria de 14 filas → `Forecast` con
  `forecast_id` = fila h=1, y error con menos filas, filas no contiguas o versiones mezcladas;
  representación (decimal finito, `"p/q"`, `Decimal` aproximado, 28 cifras `ROUND_HALF_EVEN` calculadas
  a mano); `config_sha256` determinista y sensible a `engine_version`, a la política
  (`policy_set = "V1_PROVISIONAL"`), a la configuración de U3 y a `input_rules_version`; `input_sha256`
  sobre la representación JSON canónica y normalizada (independiente del orden de entrada y de
  `forecast_id` y `model_version_id`, sustituidos por `{name, version}` del modelo).
- **Integración, PostgreSQL** (`backend/tests/db`): migración `0003` (columnas, `CHECK`, inmutabilidad);
  ejecución completa con una fila por candidato e invariantes por `outcome`; las 10 `NOT_CALCULABLE`
  esperadas con el dataset 0.4.0; **trazabilidad** hasta `dataset_version`; **idempotencia**
  (`ALREADY_COMPUTED`; otra `engine_version` → otra ejecución); selección del forecast (se ignoran
  `FAILED`, otras configuraciones y series no primarias; sin ejecución válida → rechazo sin escribir);
  **rollback** (un `InvalidInputError` inyectado o un error de base → `FAILED` y cero recomendaciones);
  rechazo de un corte distinto del último día y de una carga no `SYNTHETIC` (`DT-063`);
  **reconstrucción y verificación de entradas** (volver a evaluar desde la base da la misma
  serialización canónica y el mismo `input_sha256`); `demand` nunca se lee.
- **Regresión:** las suites de U1, U2 y U3 siguen en verde; las pruebas de esquema y de migraciones de
  U2/U3 solo se amplían de forma aditiva.

*Pruebas exigibles de U5 (2026-10-03, `DT-064` a `DT-067`; U5 implementada y validada el mismo día; criterios de
cierre en `docs/07` §7.5). El `TestClient` usa `httpx2==2.13.1` (`DT-064`).*

- **Sin base** (`backend/tests/api`, con la capa `db/read` sustituida por un doble): validador de
  desarrollo (formatos, registro inválido al arrancar, ningún token en los logs); `APP_ENV` (`dev`,
  `staging`, `prod`, ausente y desconocido no arrancan); matriz completa de roles de los 13 endpoints con
  401 sin token y 403 por rol; `X-Correlation-ID` aceptado, generado y propagado; formato de error y
  códigos 400, 401, 403, 404, 405, 422, 500 y 503; paginación y desempate; `Decimal` como texto, sin
  `float`; avisos de `provenance`; estadísticos de la historia calculados a mano con **desviación estándar
  poblacional** (semanas ISO, meses, periodos parciales, huecos, n = 0, n = 1 con `std_dev = 0`,
  `mean = 0`); OpenAPI; recorrido de todas las rutas registradas (ninguna responde sin token salvo
  `/health`, `/docs` y `/openapi.json`); imports prohibidos (`supply_engine`, `forecasting`, `runs`);
  ausencia de cabeceras CORS.
- **Integración** (`backend/tests/db/test_api_*`, PostgreSQL real con el dataset 0.4.0, forecast y
  recomendaciones): los 13 endpoints; ejecución por defecto con varias ejecuciones, una `FAILED` ignorada,
  `run_id` explícito y 404; las tres `outcome`; `provenance`; historia real; líneas abiertas iguales a las
  del adaptador de U4; paginación y orden.
- **Solo lectura:** tras recorrer todos los endpoints, filas por tabla y contadores
  `n_tup_ins/upd/del` de `pg_stat_user_tables` sin cambios (con `pg_stat_force_next_flush()`), y una
  escritura forzada a través de `db/read` rechazada con SQLSTATE 25006.
- **Regresión:** suites de U1–U4 y del generador en verde, en local y en Docker.

*Implementación (2026-10-03).* `backend/tests/api` (56 pruebas, sin `__init__.py`, fuera de la suite por defecto,
que debe pasar sin dependencias opcionales, como ya ocurre con `backend/tests/db`; se ejecuta con
`python -m unittest discover -s tests/api -t tests/api` y los grupos `api` y `test`). El proyecto tiene, por
tanto, tres suites de backend: por defecto (`discover -s tests -t .`), API (`discover -s tests/api -t tests/api`)
e integración (`discover -s tests/db -t tests/db`, que recoge también `test_api_*`). En lugar de un doble de `db/read`,
las pruebas sin base apuntan a un PostgreSQL inalcanzable: los rechazos (401, 403, 422) no abren conexión y
las rutas permitidas responden 503, lo que demuestra que la autorización precede a la base. `backend/tests/db/test_api_read.py`
(21, dataset 0.4.0 con forecast y recomendaciones) y `test_api_runs.py` (8, ejecuciones construidas a mano para
`DT-066`). Todas en verde en local y en Docker.


*Pruebas exigibles de U6 (2026-10-04, `DT-068` y `DT-069`; U6 implementada y validada el 2026-10-04; criterios de cierre en
`docs/09` §14.6). Solo `unittest`; `genai` se prueba sin base y sin red.*

- **Sin base** (`backend/tests/genai`, en la suite por defecto: `genai` solo usa la biblioteca estándar):
  - `RECOMMEND`: texto exacto de `docs/09` §14.5 para casos fijos (con y sin cada marca); `facts[]` exactamente
    los de la tabla por `outcome`, en orden; toda cifra verificada; frases de marca en orden canónico;
    `provenance` y `notices` intactos.
  - `NO_NEED`: plantilla propia, sin `q_final`, `moq`, `order_multiple` ni `q_moq`; verificación; frase de
    provisionalidad.
  - `NOT_CALCULABLE`: `narrative = null`, `facts = []`, `status = NOT_APPLICABLE`, `reason_details` en orden
    canónico y sin cifras, `missing_policy_parameters`.
  - **`display` y redondeo:** entero, decimal exacto, racional `p/q` y `Decimal` aproximado de 28 cifras →
    cadena calculada a mano (6 decimales `ROUND_HALF_EVEN`, sin ceros finales, `0` sin signo); sin `float`; la
    misma cadena se renderiza y se verifica.
  - **Regex y literales:** ninguna plantilla ni frase contiene dígitos ni `%`; la cifra narrativa es la
    coincidencia maximal de `-?\d+(?:\.\d+)?` y se compara como cadena.
  - **RS-010 / `DEGRADED`:** un `TextGenerator` de prueba que introduce `999`, una fecha, un SKU y `-5` →
    `UnverifiedFigureError` → `DEGRADED`, `narrative = null`, `warning = NARRATIVE_UNVERIFIED`, datos
    conservados, sin texto rechazado y con un registro que lleva el `correlation_id`.
  - **Provisionalidad:** frase final según `notices` (las cuatro combinaciones); `notices` sin cambios; sin
    frase en `NOT_CALCULABLE` ni en `DEGRADED`.
  - **Inmutabilidad:** mutar el contexto o un `Fact` lanza `FrozenInstanceError`; mutar los datos de origen
    después de construir el contexto no lo altera.
  - **Determinismo:** misma fila → mismo contexto → misma narrativa.
  - **Sin IA, sin base y sin recálculo** (AST): `genai` no importa `api`, `db`, `psycopg`, `supply_engine`,
    `forecasting`, `runs` ni bibliotecas de red o de IA; `pyproject.toml` sin dependencias nuevas.
- **API sin base** (`backend/tests/api`): el endpoint 14 en OpenAPI (14 rutas `GET`), con seguridad Bearer;
  matriz de roles de 14 endpoints × 4 roles + sin token; 401, 403 y 422 como en U5.
- **Integración** (`backend/tests/db/test_api_*`, dataset 0.4.0): las 100 evaluaciones dan `VERIFIED` o
  `NOT_APPLICABLE`, ninguna `DEGRADED`; 404 `RECOMMENDATION_NOT_FOUND`; `unit_of_measure` del producto en la
  narrativa; `facts[].value` igual a `calculation_inputs.breakdown`; solo lectura (filas y
  `pg_stat_user_tables` sin cambios) y aislamiento de `demand`.
- **Regresión:** suites de U1–U5 y del generador en verde, en local y en Docker.

*Implementación (2026-10-04).* `backend/tests/genai` (58 pruebas, en la suite por defecto: 295 → 353, sin dependencias
opcionales); `backend/tests/api` sigue en 56 (la matriz y el test de OpenAPI pasan a 14 endpoints, `DT-068`);
`backend/tests/db/test_api_explanation.py` (9: los tres `outcome`, las 100 evaluaciones reales, RS-010 por el
endpoint, roles y errores, solo lectura y `demand`); integración 142 → 151. Todas en verde en local y en Docker.
