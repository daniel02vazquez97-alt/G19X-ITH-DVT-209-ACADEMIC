# 13 — Estrategia de testing

**Estado:** Versión 1.0 — Etapa 0 (estrategia, **no implementada**) · **Fecha:** 2026-09-04 · **Versión 1.1** — revisada en la auditoría de Etapa 0.1 · **Versión 1.2** (2026-09-30) — §14, capas de prueba de la Etapa 2; §§1–13 no cambian · **Versión 1.3** (2026-10-01) — §3.1: aclaración de `InvalidInputError` y excepción de `on_hand < 0` para U1 (`DT-052`) · **Versión 1.4** (2026-10-01) — §3.1: sin monotonía global del punto de reorden frente al lead time en U1 (`DT-054`) · **Versión 1.5** (2026-10-01) — §14: dónde viven las suites de U2 (`DT-055`)

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
| API | Esquema OpenAPI, formato de error, paginación, **matriz rol × endpoint**, ninguna ruta sin autenticación salvo `/health` | PostgreSQL local + `TokenValidator` de desarrollo | U5 |
| IA generativa | La verificación detecta una cifra ajena al contexto | Python | U6 |

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
