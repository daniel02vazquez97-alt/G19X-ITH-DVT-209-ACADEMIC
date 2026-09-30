# Estado del proyecto

**Última actualización:** 2026-09-29 (**Generador 0.4.0 terminado: C8 implementado, C7 y C8 integrados en W1, dataset `ds-6c8ad65b4999` validado y publicado** — `quality_report` 51/51, 0 fallos · 582 pruebas en verde) · 2026-09-29 (**Componente 7 implementado y probado, sin integrar en W1** — `DT-041`, `scenario_assignment` con los 16 ejes · `generator_version` sigue en 0.3.0 y el dataset publicado no cambia · 509 pruebas en verde) · 2026-09-29 (**W1 implementado; dataset completo publicado** — `ds-269a698250db`, `generator_version` 0.3.0, C2 → C3 → C6 → C4 → C5 · 463 pruebas en verde) · 2026-09-28 (**pendientes de C5 cerrados**: prueba permanente de la selección exacta de `CANCELLED` y frase de `DT-039` §13 corregida · W1 detenido antes de implementar, pendiente de dos decisiones · 434 pruebas en verde) · 2026-09-28 (**Componente 6 implementado y probado, sin conectar a `__main__`** · lote C6 → C4 → C5 completo, integración bloqueada por W1 · dataset publicado sin cambios · 430 pruebas en verde) · 2026-09-28 (**Componente 5 implementado y probado, sin conectar a `__main__`**) · 2026-09-27 (**D-01 cerrado: elegibilidad de las `CANCELLED` respecto de `valid_to`, opción A**, `DT-039` §5.2 · C5 sigue sin implementar) · 2026-09-26 (**Componente 4 implementado y probado, sin conectar a `__main__`** — decisiones D-C4-1 (O1), D-C4-2 (P1) y D-C4-3 · C5/C6 sin implementar · dataset publicado sin cambios · 323 pruebas en verde)

---

## Estado actual

> ## ETAPA 1 — DATOS · **EN PROGRESO**
>
> La **Etapa 0 está superada** como condición para continuar: documentación base creada (2026-09-03),
> auditada y corregida (revisión 0.1, 2026-09-04, *aprobada con observaciones*).
>
> El responsable del proyecto **autorizó explícitamente el inicio de la Etapa 1 el 2026-09-14**.
>
> **Bloque actual: W1 — publicación del dataset**, **implementado el 2026-09-29** (ver *W1* más
> abajo). Los Componentes 1 a 6 están implementados y conectados: `python3 -m data.synthetic.generator`
> ejecuta C2 → C3 → C6 → C4 → C5 en un workspace temporal y promociona el resultado a `output/`.
> **Generador terminado (2026-09-29).** Los Componentes 1 a 8 y W1 están implementados y
> conectados: `python3 -m data.synthetic.generator` ejecuta C2 → C3 → C6 → C4 → C5 → C7 → C8 →
> verify → promote. **Dataset publicado y validado:** `ds-6c8ad65b4999`, `generator_version`
> **0.4.0**, `quality_report` con 51 de 51 comprobaciones y 0 fallos. **Siguiente:** cierre de la
> Fase 1 y autorización de la siguiente fase, a decidir por el responsable. *(El texto de este párrafo decía «Componente
> actual: 1» y había quedado desfasado; se corrige aquí, no se reescribe el historial que sigue.)*
>
> **Auditoría de escenarios: resuelta** (2026-09-17). Se adopta la separación en tres niveles de
> `DT-023` y el enum `Scenario` pasa de 14 a **16 valores**.
>
> **Auditoría del Componente 1: corregida** (2026-09-17). La auditoría de `DT-023`, `config.py`,
> `dataset_config.yaml`, `test_config.py` y este archivo resultó **NO APROBADA** por tres defectos
> críticos: un recuento incorrecto de la matriz de §25 (se afirmaba 11 + 9 + 5 = 26, que suma 25),
> `_parse_scale` interrumpía la acumulación de problemas en el primer error de tipo, y `validate()`
> no comprobaba duplicados ni orden canónico, de modo que un objeto podía validarse y aun así
> producir un `to_dict()` que `from_mapping()` rechazaba. **Los defectos están corregidos** y las
> pruebas pasan (54). La clasificación conceptual A/B/C **no se modificó**.
>
> **Auditoría del Componente 2: realizada** (2026-09-17). Auditoría documental y técnica, de solo
> lectura, sobre las cinco entidades maestras (`Category`, `Product`, `Supplier`, `ProductSupplier`,
> `Location`). Resultado: la **estructura** estaba definida, pero faltaban siete definiciones —**B-1 a
> B-7**— sin las cuales el componente no podía implementarse sin inventar.
>
> **Bloqueantes B-1 a B-7: resueltos documentalmente** (2026-09-18). Siete decisiones nuevas,
> `DT-024` a `DT-030`, cierran el formato de salida, la marca de origen, la vigencia de `Product`, la
> metadata de generación, las políticas de generación sintética y el determinismo.
> **El Componente 2 sigue SIN implementar**: no existe ningún generador, ningún CSV y ningún dataset.
>
> **Auditoría de consistencia post-decisiones: NO APTA todavía** (2026-09-18). Cuatro revisiones
> independientes sobre `DT-024`–`DT-030` encontraron **seis defectos bloqueantes** en decisiones ya
> marcadas `ACEPTADA` — entre ellos una contradicción interna en `DT-027` sobre la semántica del
> intervalo de vigencia, una garantía falsa de `DT-028` («ningún proveedor queda huérfano»), un
> algoritmo de `DT-028` con dos lecturas de las que una aborta, y una sub-semilla de `DT-030` que
> depende de un identificador que no estaba definido en ninguna parte. **Los seis están corregidos.**
> Quedan **tres cuestiones abiertas que requieren decisión del responsable** y que impiden dar el
> visto bueno: ver *Auditoría de consistencia* más abajo.
>
> **Diseño de los Componentes 4, 5 y 6: cerrado documentalmente** (2026-09-24). El responsable aprobó
> la arquitectura de ejecución **C6 → C4 → C5**, los parámetros sintéticos de inventario
> (`W = 28`, `M = 7`, `C = 21`, factores 750/1000/1500 ‰, mezcla 30/40/30), los perfiles de proveedor
> y siete decisiones de contrato. Quedan registrados en **`DT-036`** y **`DT-037`**. Se **enmienda
> `DT-027`** (restricción 3) para admitir que una orden emitida dentro de la vigencia complete su
> ciclo después de `valid_to`, y se **cierra el pendiente de `data_origin`** que `DT-026` arrastraba
> desde el 2026-09-18. **Los tres componentes siguen SIN implementar**: no existe
> `generator/inventory.py`, ni `supplier_behaviour.py`, ni `orders.py`, ni sus pruebas.
>
> **Auditoría pre-implementación de C4/C5/C6: realizada y resuelta** (2026-09-24). Dos revisiones
> independientes en contexto limpio, con cada hallazgo verificado después contra el repositorio y el
> dataset. Resultado inicial **NO APROBABLE**: ocho bloqueantes, el principal que **los contratos de
> salida de C4 y C5 no existían en el repositorio** —§41.3 de la especificación los declaraba
> pendientes— y que `DT-036` citaba `V1-06` **sin su guarda `raw_need ≤ 0`**, con 9 pares del dataset
> verificados que alcanzan demanda reciente cero. El responsable resolvió las siete decisiones
> abiertas (D-01 a D-07) el mismo día. **Los ocho bloqueantes están cerrados** con `DT-038`, `DT-039`
> y correcciones a `DT-036` y `DT-037`. Los tres componentes siguen **sin implementar**.
>
> **D-01 cerrado documentalmente** (2026-09-24 a 2026-09-26). Tres rondas de análisis sobre las
> órdenes `CANCELLED` sintéticas desembocaron en seis decisiones del responsable: **A2** (el
> Componente 5 forma `order_number` para todas las órdenes; el Componente 4 no conoce la política de
> cancelaciones), **B2** (sin ninguna orden elegible la ejecución falla), `ORDERS_CANCELLED_PERMILLE =
> 20`, `ORDERS_CANCELLED_CLOSE_LAG_DAYS = 1` sin recorte de `closed_at`, `expected_at` copiado de C4,
> y una **regla general de `generator_version`** basada en el artefacto publicado, ya no en una lista
> de parámetros (`DT-033`). El análisis de B2 destapó que **la escritura progresiva del generador
> impedía cumplirla**: C2, C3 y C4 escribían en `output/` antes de que C5 pudiera fallar, dejando un
> dataset parcial o mezclado. Se resuelve con **W1** (`DT-040`): cada ejecución trabaja en su propio
> workspace y `output/` solo cambia por promoción al final. Se corrigieron además seis frases que
> atribuían al Componente 4 **todos** los identificadores, un error introducido en la sesión del
> 2026-09-24. **Pendiente de confirmación:** dos detalles de operación de `DT-040` (qué hacer con el
> dataset sustituido y con el workspace de una ejecución fallida). **C4, C5 y C6 siguen sin
> implementar.**
>
> **D-01 — elegibilidad de las `CANCELLED` cerrada** (2026-09-27). La auditoría previa a C5 encontró
> que una orden gemela cuya plantilla se emitió el propio día `valid_to` se cerraría al día siguiente,
> fuera de la vigencia que exige la restricción 3 de `DT-027`. El responsable eligió la **opción A**:
> una orden causal solo es elegible si su cierre previsto (`issued_on + 1 día`) cumple `< end_date`
> **y** `<= valid_to` (o `valid_to` nulo). El filtrado ocurre antes de calcular `K` y de seleccionar;
> B2 sigue vigente; `closed_at` no se recorta; **`DT-027` no cambia**. Autoridad: `DT-039` §5.2.
> **C5 sigue sin implementar.**
>
> **Componente 4 implementado y probado** (2026-09-26), con tres decisiones del responsable tomadas al
> autorizarlo: **D-C4-1 = O1** (la entrega partida acota `q1` a `Q_final − 1`, `DT-037` §3 enmendado),
> **D-C4-2 = P1** (la ventana de 28 días nunca se acorta: precondiciones P-C4-2 y P-C4-3, `DT-038`
> §16) y **D-C4-3** (lead time acordado, sin `V1-09` ni `R_v1`; `M` solo en la apertura; disparo
> diario). **No está conectado a `__main__`**: consume perfiles del Componente 6 y entrega órdenes al
> Componente 5, y ninguno existe. `output/` y `generator_version` (0.2.0) **no cambian**.
>
> Las observaciones abiertas de la Etapa 0.1 siguen abiertas y son **externas al equipo técnico**:
> doce parámetros del negocio y dos supuestos de alto riesgo sin confirmar. **Ninguna de ellas bloquea
> la Fase 1**, porque el generador de datos sintéticos no depende de parámetros de política.
>
> Detalle de la auditoría en `docs/reports/etapa-0-1-reporte.md`.

## Progreso

| Etapa / Fase | Estado |
|---|---|
| **Fase 0 — Preparación** | ✅ Superada (documentada, auditada y aprobada con observaciones) |
| **Fase 1 — Datos** | 🟡 **En progreso** — Componentes 1 a 6 de 8 implementados y conectados; W1 implementado; dataset completo publicado |
| Fase 2 — PostgreSQL | ⬜ No iniciada |
| Fase 3 — FastAPI | ⬜ No iniciada |
| Fase 4 — Motor de abastecimiento | ⬜ No iniciada |
| Fase 5 — Machine Learning | ⬜ No iniciada |
| Fase 6 — Azure Machine Learning | ⬜ No iniciada |
| Fase 7 — React | ⬜ No iniciada |
| Fase 8 — Microsoft Entra ID | ⬜ No iniciada |
| Fase 9 — Azure AI Search | ⬜ No iniciada |
| Fase 10 — Azure OpenAI | ⬜ No iniciada |
| Fase 11 — Power BI | ⬜ No iniciada |
| Fase 12 — Docker | ⬜ No iniciada |
| Fase 13 — GitHub Actions | ⬜ No iniciada |
| Fase 14 — QA | ⬜ No iniciada |
| Fase 15 — Documentación y entrega | ⬜ No iniciada |

### Criterios de finalización de la Etapa 0

| Criterio | Estado |
|---|---|
| Estructura documental | ✅ |
| `CLAUDE.md` | ✅ |
| `AGENTS.md` | ✅ |
| Requisitos documentados | ✅ `docs/01` |
| Propuesta técnica | ✅ `docs/02` |
| Arquitectura | ✅ `docs/03` |
| Modelo de datos conceptual | ✅ `docs/04` |
| Estrategia de ML | ✅ `docs/05` |
| Motor de abastecimiento | ✅ `docs/06` |
| API diseñada | ✅ `docs/07` |
| Frontend diseñado | ✅ `docs/08` |
| IA generativa | ✅ `docs/09` |
| Seguridad | ✅ `docs/10` |
| Power BI planificado | ✅ `docs/11` |
| DevOps planificado | ✅ `docs/12` |
| Testing planificado | ✅ `docs/13` |
| Mantenimiento planificado | ✅ `docs/14` |
| Decisiones técnicas registradas | ✅ `docs/15` |
| Glosario | ✅ `knowledge/glossary.md` |
| Supuestos registrados | ✅ `knowledge/assumptions.md` |
| Reglas de negocio documentadas | ✅ `knowledge/business-rules.md` |
| Roadmap | ✅ `project/roadmap.md` |
| Backlog | ✅ `project/backlog.md` |
| Estado del proyecto | ✅ este archivo |
| `README.md` actualizado | ✅ |

**25 criterios verificados.** Reporte de cierre en `docs/reports/etapa-0-reporte.md`.

### Criterios de la revisión 0.1

Los veinte criterios de finalización de la auditoría se cumplen. Detalle en
`docs/reports/etapa-0-1-reporte.md` §7. Resumen de lo corregido: quince problemas encontrados
—cinco de severidad crítica—, treinta y cinco correcciones aplicadas, cuatro decisiones técnicas
nuevas (`DT-019` a `DT-022`), tres historias de usuario nuevas, un requisito nuevo derivado
(`RML-013`) y dos supuestos nuevos.

### Fase 1 — Datos · avance por componente

| # | Componente | Estado |
|---|---|---|
| 1 | **`DatasetConfig`** — contrato de configuración del generador | ✅ Implementado y probado |
| 2 | Catalog Generator | ✅ **Implementado y probado** (2026-09-21) — cinco entidades maestras + `manifest.json` |
| 3 | Demand Generator | ✅ **Implementado y probado** (2026-09-23) — `demand.csv`, demanda **latente** |
| 4 | Inventory Simulator | ✅ **Implementado y probado** (2026-09-26, `DT-036`, `DT-038`) — identificador `inventory`. **Dueño del inventario, los desabastos y `consumption.csv`**; calcula además las órdenes **causales** y sus recepciones y les asigna los identificadores. Conectado a través de W1 (2026-09-29) |
| 5 | Purchase Order Generator | ✅ **Implementado y probado** (2026-09-28, `DT-039`), conectado a través de W1 (2026-09-29) — identificador `orders`. Materializa `purchase_orders.csv`, `purchase_order_items.csv` y `purchase_order_receipts.csv` **sin recalcular nada**; añade las órdenes `CANCELLED` sintéticas, numera solo esas filas y forma el `order_number` de todas |
| 6 | Supplier Behaviour Generator | ✅ **Implementado y probado** (2026-09-28, `DT-037`), conectado a través de W1 (2026-09-29) — identificador `supplier_behaviour`. **No escribe archivos**; entrega perfiles en memoria a C4 |
| 7 | Scenario Assignment | ✅ **Implementado y probado** (2026-09-29, `DT-041`) — identificador `scenarios`. Escribe **solo** `manifest.scenario_assignment` y su entrada en `components`; integrado en W1 con C8 (2026-09-29) |
| 8 | Dataset Validator + informe de calidad | ✅ **Implementado y probado** (2026-09-29, `DT-042`) — identificador `validator`. 51 comprobaciones sobre el workspace; escribe `manifest.quality_report` solo si todas pasan |

**Terminado en el Componente 1:**

- `data/synthetic/config/dataset_config.yaml` — configuración explícita con semilla, ventana
  temporal, escala del catálogo y los **16 valores del enum `Scenario`** requeridos como cobertura
  (13 corresponden a situaciones de §25 y tres a otras secciones, `DT-023`).
- `data/synthetic/config/config.py` — `load_config()` → `DatasetConfig` tipado → `validate()`.
  Objeto congelado y normalizado, que será la entrada de todos los componentes posteriores.
  El enum `Scenario` es un conjunto **cerrado de 16 valores**.
- `data/synthetic/tests/test_config.py` — **54 pruebas**, todas en verde.

**Pendiente en la Fase 1:** los componentes 3 a 8, el histórico del dataset, el proceso de ingesta
con marca de origen, el informe de calidad y los umbrales de aceptación del modelo (`DT-P04`).

**Siguiente componente autorizado:** ninguno todavía. El Componente 2 (*Catalog Generator*) requiere
autorización explícita, como cada componente de esta fase. Lo que ya está preparado para él:

- `DT-023` — la frontera entre los ejes del enum y los Niveles B y C, de modo que el Componente 2 no
  contamine las entidades maestras con información que pertenece al histórico.
- `DT-024` a `DT-030` — el contrato de salida, la marca de origen, la vigencia de `Product`, la
  metadata de generación, las políticas de generación sintética y el determinismo.

**El Componente 2 no está implementado.** No existe generador, ni CSV, ni dataset generado.

**Estado del código de aplicación:** no existe, y es lo correcto. El único código del repositorio es
el generador de datos sintéticos. Backend, frontend, base de datos, ML, Azure, contenedores y CI/CD
pertenecen a fases posteriores.

## Decisiones recientes

Registradas en `docs/15-decisiones-tecnicas.md`. Las de mayor impacto:

| ID | Decisión | Estado |
|---|---|---|
| `DT-001` | Separación estricta entre predicción ML, reglas de negocio e IA generativa | `ACEPTADA` |
| `DT-002` | Monolito modular en el backend, no microservicios | `ACEPTADA` |
| `DT-003` | Dependencias de Azure encapsuladas tras interfaces propias | `ACEPTADA` |
| `DT-006` | Histórico inmutable (append-only) | `ACEPTADA` |
| `DT-007` | Sin generación de SQL libre por el LLM | `ACEPTADA` |
| `DT-009` | Progresión incremental de modelos con criterio de parada | `ACEPTADA` |
| `DT-015` | Sin promoción automática de modelos a producción | `ACEPTADA` |
| `DT-016` | El sistema recomienda; no ejecuta compras | `ACEPTADA` |
| `DT-018` | Explicación por plantilla determinística antes que por LLM | `ACEPTADA` |
| `DT-020` | Evaluación en dos niveles y comparación end-to-end baseline vs. ML | `ACEPTADA` *(0.1)* |
| `DT-008`, `DT-012`, `DT-013`, `DT-014`, `DT-022` | Granularidad, tránsito efectivo, ubicación de carpetas, modo de Power BI, almacén de secretos | `PROPUESTA` |
| `DT-010` | **Metodología del stock de seguridad** | `PENDIENTE DE VALIDACIÓN` *(retrocedió desde `PROPUESTA` en la revisión 0.1)* |
| `DT-019` | Conversión entre pronóstico semanal y lead time en días | `PENDIENTE DE VALIDACIÓN` *(0.1)* |
| `DT-021` | Métrica primaria de pronóstico | `PENDIENTE` *(0.1)*; el descarte de MAPE sí es `ACEPTADA` |
| `DT-011` | Tratamiento de la demanda censurada | `PENDIENTE` (el marcado del dato sí está aceptado) |
| `DT-023` | Clasificación en tres niveles de las 26 situaciones de §25 | `ACEPTADA` |
| `DT-024` | Formato de salida: un CSV por entidad | `ACEPTADA` *(2026-09-18)* |
| `DT-025` | `manifest.json`: la metadata de generación vive fuera de las entidades | `ACEPTADA` *(2026-09-18)* |
| `DT-026` | `data_origin` en las cinco entidades maestras | `ACEPTADA` *(2026-09-18)* |
| `DT-027` | Vigencia de `Product`: `valid_from` y `valid_to` | `ACEPTADA` *(2026-09-18)* |
| `DT-028` | Políticas de generación sintética del Componente 2 | `ACEPTADA` *(2026-09-18)* |
| `DT-029` | Alcance del Componente 2: lo que no genera | `ACEPTADA` *(2026-09-18)* |
| `DT-030` | Determinismo por sub-semillas derivadas de la semilla común | `ACEPTADA` *(2026-09-18)* |
| `DT-023` | **Clasificación en tres niveles de las situaciones de §25**; enum `Scenario` de 14 a 16 | `ACEPTADA` *(2026-09-17)* |

**Decisiones de implementación del Componente 1** (ninguna requiere ADR: son librerías dentro de un
lenguaje ya adoptado, conforme a `CLAUDE.md` §5):

- **PyYAML** como única dependencia externa del generador. La configuración debe ser un `.yaml` y la
  biblioteca estándar no parsea YAML; no hay alternativa más simple.
- **Biblioteca estándar para la validación**, no Pydantic. Pydantic está en el stack por FastAPI, pero
  acoplar el generador de datos a la capa de API no aporta nada aquí y añadiría una dependencia que
  esta tarea no necesita (`CLAUDE.md` §6, regla 2).
- **`unittest` para las pruebas**, no pytest: está en la biblioteca estándar y no añade dependencias.
  Revisable cuando exista más código que probar.

**Decisión de secuenciación destacada:** el motor de abastecimiento (Fase 4) va **antes** que el
Machine Learning (Fase 5). El motor consume un forecast, y ese forecast puede ser un baseline. Así el
sistema entrega valor auditable desde temprano y el modelo, cuando llegue, solo mejora una entrada de
un motor ya probado.

## Problemas conocidos

| # | Problema | Impacto | Acción |
|---|---|---|---|
| 1 | **No hay parámetros de política del negocio** (nivel de servicio, política de revisión, umbrales de riesgo) | **Alto** — bloquea la parametrización de la Fase 4 | Solicitar al negocio; el sistema no los inventa |
| 2 | **No está confirmado que exista corpus documental** | **Alto** — Azure AI Search podría perder su propósito principal | Inventariar la documentación interna (ASSUMPTION-008) |
| 3 | No hay datos reales | Medio — controlado con datos sintéticos y marca de origen | Confirmar fecha de disponibilidad (ASSUMPTION-001) |
| 4 | Volumen real del catálogo y del histórico desconocido | Medio — afecta a decisiones de implementación | Solicitar cifras (ASSUMPTION-012) |
| 5 | Roles no validados con el negocio | Medio — bloquea la Fase 8 | Revisar estructura organizacional (ASSUMPTION-010) |
| 6 | Destino de despliegue en Azure sin decidir | Bajo hoy — mitigado por el uso de contenedores | Decidir en Fases 12–13 (ASSUMPTION-014) |
| 7 | Presupuesto de Azure no definido | Medio — condiciona Fases 6, 9 y 10 | Solicitar antes de provisionar |
| 8 | ~~Desajuste entre los escenarios de `DatasetConfig` y §25~~ | — | ✅ **RESUELTO** el 2026-09-17 por `DT-023`: las 26 situaciones de §25 se reparten en tres niveles (13 A + 9 B + 4 C) y el enum `Scenario` queda en 16 valores |
| 9 | `data/synthetic/generator/config.py`: archivo de 0 bytes que existía solo en el disco del proyecto (2026-09-13 20:58 UTC) y no formaba parte del Componente 1, cuyo `config.py` vive en `data/synthetic/config/` | Bajo, pero confundía: dos rutas con el mismo nombre de archivo y una vacía | **RESUELTO el 2026-09-21.** El responsable autorizó eliminarlo expresamente. Se comprobó antes que ningún import ni referencia de código dependía de él —las únicas menciones estaban en este archivo— y la suite siguió en verde |
| 10 | **Seis documentos del disco del proyecto no tenían las correcciones del 2026-09-18** (detectado el 2026-09-21 comparando `md5sum` árbol contra árbol, y **resuelto el mismo día**): `docs/04-modelo-datos.md`, `knowledge/dataset-specification.md`, `DT-024`, `DT-025`, `DT-027` y `DT-028`. Faltaban, entre otras: el intervalo cerrado `valid_from ≤ valid_to` (`docs/04`, `DT-027`), las precondiciones **P-4** y **P-5** y el testigo de MOQ con `order_multiple = 1` (`DT-028`), el orden de filas por clave de negocio (`DT-024`) y el invariante de reproducibilidad con sus cuatro campos excluidos (`DT-025`). Nota: el primer recuento de esta sesión dijo «cuatro»; la comparación completa del árbol encontró **seis** | Era **alto**: `docs/15` y este archivo declaraban esas correcciones como hechas y el disco decía lo contrario. Un Componente 2 implementado desde el disco habría reintroducido bloqueantes ya corregidos | **RESUELTO.** El responsable autorizó sobrescribir el 2026-09-21 («siempre sobreescribe para que estén actualizadas ambas carpetas»). Los seis archivos se escribieron sobre el disco y **ambas copias coinciden byte a byte**, salvo `data/synthetic/generator/config.py`, que existe solo en el disco y sigue pendiente de decisión (punto 9) |

**Revisión 0.1 (2026-09-04):** quince problemas encontrados y corregidos. Los cinco críticos:
`DT-010` confundía cuatro conceptos de incertidumbre distintos y daba por buena una fórmula (`√L`)
que solo es válida bajo supuestos no verificados; no existía regla para convertir el pronóstico
semanal a un lead time en días; `quantity_in_transit` mezclaba el tránsito total con el relevante
para una decisión; no existía evaluación del efecto del forecast sobre las decisiones de
abastecimiento; y no existía comparación end-to-end baseline vs. ML. Todos resueltos.

**Contradicciones en las instrucciones recibidas:** ninguna. La única ambigüedad fue el nivel de
`architecture/`, `decisions/` y `reports/`; se resolvió ubicándolas bajo `docs/` con justificación
registrada en `DT-013`, pendiente de confirmación.

**Revisión de consistencia interna (2026-09-03):** se ejecutó una revisión cruzada de los 30
documentos que detectó y corrigió inconsistencias entre ellos — un caso límite de stock de seguridad
mal enunciado, dos definiciones incompatibles de *fill rate*, la frecuencia del proceso batch, el rol
de consulta de políticas, la dependencia circular del baseline entre las Fases 4 y 5, dos ciclos de
dependencia entre requisitos y varios conteos. Todas están resueltas; el detalle está en
`docs/reports/etapa-0-reporte.md` §5.

### Clasificación de escenarios — resuelta (`DT-023`)

La discrepancia entre los 14 valores del enum y las 26 situaciones de §25 **queda resuelta**: no eran
dos versiones de la misma lista, sino **tres niveles distintos** que §25 resume en una sola tabla.

| Nivel | Qué es | Dónde vive | De las 26 |
|---|---|---|---|
| **A — Ejes de generación** | Comportamientos que el generador produce deliberadamente | Enum `Scenario`, `scenarios.required` | 13 |
| **B — Atributos y estados** | Campos del modelo con valores variados (MOQ, múltiplo, proveedor preferente, producto activo, estado de la orden) | Entidades de `docs/04-modelo-datos.md` | 9 |
| **C — Propiedades emergentes** | Situaciones que surgen de combinar entidades y dependen de reglas pendientes | **Validador, Componente 8** | 4 |

13 + 9 + 4 = 26.

**Autorizado e implementado:** el enum pasa de **14 a 16** valores con `LOW_INVENTORY` (§10.2) y
`PARTIAL_DELIVERY` (§12.3). Los catorce originales se conservan sin cambios de nombre ni fusiones.

**No confundir las dos cifras.** «26» cuenta situaciones de §25; «16» cuenta valores del enum. De los
16 valores, 13 corresponden a situaciones de §25 y los otros tres —`HIGH_ROTATION`, `LOW_ROTATION` y
`MULTIPLE_LEAD_TIMES`— están respaldados por otras secciones de la documentación (`DT-023` §7).

**Por qué el escenario crítico de §11 no es un eje:** etiquetar un SKU como «tránsito efectivo
insuficiente» exigiría que el generador supiera qué cuenta como *efectivo*, y ese criterio de corte es
`DT-P11`, todavía pendiente. Lo mismo ocurre con el conflicto MOQ/sobreinventario (`BR-X03`), el
producto inactivo con histórico (`BR-P10`) y la demanda censurada (`DT-011`). El generador produce las
condiciones; el validador comprueba que la propiedad se cumple.

Matriz completa de las 26 situaciones en
[`docs/decisions/DT-023-clasificacion-escenarios.md`](../docs/decisions/DT-023-clasificacion-escenarios.md).

**Abierto, sin decidir:** `HIGH_ROTATION` y `LOW_ROTATION` están en el enum y respaldados por
`docs/02` §8, el roadmap y §10.4 de la propia especificación, pero **no figuran como filas de §25**.
No se modificó §25 (`DT-P12`).

### Componente 2 — auditoría y bloqueantes resueltos

La auditoría del Componente 2 (2026-09-17, solo lectura) concluyó que la **estructura** de las cinco
entidades maestras estaba definida, pero que faltaban siete definiciones sin las cuales el componente
no podía implementarse sin inventar. Las siete quedaron resueltas el 2026-09-18:

| Bloqueante | Qué faltaba | Resuelto por |
|---|---|---|
| **B-1** | Formato y estructura física de salida — §40 lo exigía y ningún documento lo definía | `DT-024` · spec §41 |
| **B-2** | `data_origin` en las maestras: `docs/04` §5.2 lo obligaba, las fichas §§3.1–3.5 lo omitían | `DT-026` · `docs/04` §§3.1–3.5 |
| **B-3** | Vigencia de `Product`: §7.2 y §20 la exigían, el modelo solo tenía `created_at` | `DT-027` · `docs/04` §3.2 |
| **B-4** | Dónde vive la metadata de generación: §19 y §33 la exigían, ninguna entidad la alojaba | `DT-025` · spec §42 |
| **B-5** | Rangos de `moq`, `order_multiple`, `unit_cost`, `agreed_lead_time_days` | `DT-028` §1 · spec §43 |
| **B-6** | Cardinalidad y reparto de `ProductSupplier` | `DT-028` §2 |
| **B-7** | Distribución de productos por categoría | `DT-028` §3 |

**Sobre los valores de `DT-028`.** Son `synthetic generation parameters`: parámetros técnicos del
generador de datos sintéticos, amparados por §3.5 de la especificación. **No son políticas
comerciales, costos, MOQ ni plazos de la organización**, y no deben citarse como información
empresarial. Los parámetros empresariales reales siguen pendientes en `knowledge/business-rules.md` §3.

**Decisiones asociadas que no eran bloqueantes:** `DT-029` (lo que el Componente 2 **no** genera:
`abc_class`, `rotation_class`, `shelf_life_days`, `currency`, `contact_info`, ningún campo `scenario`;
y el rechazo explícito de `location_count > 1`) y `DT-030` (sub-semillas deterministas por componente,
para que implementar el Componente 3 no altere los datos del 2).

**No se modificó código.** `config.py`, `dataset_config.yaml` y las pruebas quedan como estaban; las
54 pruebas siguen en verde. Las tres precondiciones de `DT-028` §8 y el límite de `location_count`
**no se añadieron a `config.py`** deliberadamente: son límites de esta versión del generador, no del
contrato de configuración, y su comprobación corresponde al Componente 2 cuando se implemente.

### Auditoría de consistencia post-decisiones (2026-09-18)

Cuatro revisiones independientes, con contexto limpio, sobre las siete decisiones del bloque
`DT-024`–`DT-030`. **Resultado: NO APTO todavía para autorizar el Componente 2.**

**Seis bloqueantes encontrados y corregidos en esta misma sesión:**

| # | Defecto | Dónde estaba | Corrección |
|---|---|---|---|
| 1 | `DT-027` declaraba el intervalo de vigencia **cerrado por ambos extremos** y once líneas después exigía `valid_from < valid_to` estricto con un ejemplo de intervalo semiabierto. De esa ambigüedad dependía la validación de §20 | `DT-027`, `docs/04` §3.2, spec §34 | Intervalo cerrado, `valid_from ≤ valid_to`; un producto de un día es `valid_to = valid_from` |
| 2 | `DT-028` §2.3 garantizaba que «todo proveedor recibe al menos una relación». **Falso**: con `product_count = 4` y `supplier_count = 50` quedan **43 proveedores huérfanos**, y las tres precondiciones lo permitían | `DT-028` §2.3, §8 | Precondición **P-4**: `supplier_count < R` |
| 3 | La fórmula `valid_to = inicio + ⌊0,75 × period.days⌋` da `valid_to = valid_from` con `period.days = 1`, dejando un producto «inactivo» sin histórico | `DT-028` §7.1, §8 | Precondición **P-5**: `period.days ≥ 2` |
| 4 | El bucle de suelo del reparto por categoría admitía dos lecturas; con donante fijo **aborta** en 718 configuraciones, incluida `category_count = product_count = 10` | `DT-028` §3.2 | Donante recalculado en cada transferencia, con la demostración de por qué nunca se agota; desempate por índice menor |
| 5 | La sub-semilla de `DT-030` es función de «el nombre del componente», que **no estaba definido**, y la extracción de los 64 bits y la codificación quedaban abiertas | `DT-030` | Fórmula completa y explícita; identificador canónico `catalog` para el Componente 2 |
| 6 | El invariante de reproducibilidad estaba enunciado de cuatro formas incompatibles; dos insatisfacibles y dos que serían falsas en cuanto exista el Componente 3 | spec §§42.4 y 44, `DT-025`, `DT-030` | Enunciado **una sola vez** en §44, incluyendo «misma versión del generador»; el resto remite a él |

**Correcciones menores aplicadas:** referencia cruzada de §34 al contrato de columnas; orden canónico
de filas en `DT-024` (era circular: «por `id`», e `id` se definía «por el orden»); retirada de dos
afirmaciones de cobertura universal que eran falsas; `§35` tiene veinte ítems, no dieciocho;
`docs/decisions/` añadido a las dependencias documentales de la especificación; inventario de
exclusiones de `DT-029` completado.

**Tres cuestiones abiertas que requieren decisión del responsable** — el Componente 2 **no debe
autorizarse hasta cerrarlas**:

| # | Cuestión | Por qué no la decide el equipo técnico |
|---|---|---|
| **A** | **¿Ocho o nueve componentes en la Fase 1?** La tabla de este archivo funde validador e informe de calidad en el octavo; `CLAUDE.md` §17 y `data/synthetic/generator/__init__.py` los enumeran por separado, lo que da nueve. Como la sub-semilla de `DT-030` es función del identificador del componente, dos enumeraciones distintas producen datasets distintos | Es una decisión de **alcance** de la Fase 1, no una cuestión de redacción |
| **B** | **¿Debe `moq` ser múltiplo de `order_multiple`?** 31 de las 56 combinaciones posibles no lo son, y en ellas el mínimo pedible real es `⌈moq/M⌉·M`, no `moq`. `docs/06` §8 declara como criterio de aceptación que el motor «recomienda el MOQ»; con un par incoherente recomienda otra cosa | Afecta al criterio de aceptación del motor de abastecimiento, no solo al generador |
| **C** | **¿Quién produce «MOQ superior a la necesidad»?** §16, §17 y §26 lo exigen; `DT-023` lo clasifica como Nivel C, a **comprobar** por el validador. Ningún componente tiene encargado **producirlo** | Es una asignación de responsabilidad entre componentes |

**Pendientes registrados, no bloqueantes:** `PurchaseOrder`, `PurchaseOrderItem`,
`PurchaseOrderReceipt` e `InventoryPolicy` siguen sin `data_origin` en sus fichas —el mismo defecto que
motivó B-2, desplazado a los Componentes 5 y 6—; `project/roadmap.md` sigue declarando la Fase 0 como
etapa actual; `README.md` afirma que el repositorio contiene solo documentación, lo que dejó de ser
cierto el 2026-09-14; y la comprobación de reproducibilidad de §44 no tiene todavía ni prueba ni
dueño. Los cuatro quedan fuera del alcance de esta auditoría.

### V1 — Reglas mínimas funcionales (2026-09-19)

Cambio de enfoque solicitado por el responsable: en lugar de cerrar todas las reglas de negocio antes
de construir, se define una **V1 pequeña, determinista y reemplazable** que permita levantar el flujo
completo `Forecast → Inventory → Supply Engine → Recommendation` sobre el dataset sintético.

`DT-031` define **trece reglas**. Nació `PROPUESTA` el 2026-09-19 y pasó a `ACEPTADA` **como conjunto
de reglas de V1** el 2026-09-21, tras la confirmación del responsable. El matiz importa: lo aceptado
es «estas son las reglas de V1», no «estas son las políticas de la organización».

| ID | Regla | Origen |
|---|---|---|
| `V1-01` | `raw_need = max(0, demanda del horizonte + SS − posición de inventario)` | Ya era `docs/06` §§7-8, rama periódica |
| `V1-02` | `IP = on_hand + effective_in_transit − reserved`, con `reserved = 0` | Ya era `docs/06` §4.2 |
| `V1-03` | `horizonte = lead time acordado + 7 días` | **Nuevo.** `R_v1 = 7` es provisional |
| `V1-04` | Prorrateo uniforme semanal → días, en una sola función | Ya era la recomendación de `DT-019` |
| `V1-05` | `SS = z_v1 × σ_H`, sin escalar por `√L` | **Nuevo.** `z_v1 = 1,65` es provisional |
| `V1-06` | `Q_final = ⌈max(raw_need, MOQ) / M⌉ × M` | Ya era `docs/06` §8 Paso 2 |
| `V1-07` | Quince elementos de demostración, clasificados por nivel y componente | — |
| `V1-08` | Invariantes del validador; **no calcula cifras de abastecimiento** | — |
| `V1-09` | Lead time observado: mediana, mínimo 3 observaciones, fallback al acordado | Implementa `BR-P01` |
| `V1-09.1` | Ventana de 12 observaciones, ordenadas por **fecha de finalización** | Parámetro de `V1-09` |
| `V1-09.2` | Techo de 90 días, con marca `LEAD_TIME_CAPPED` y valor sin topar trazable | Parámetro de `V1-09` |
| `V1-10` | Proveedor **preferente activo**; sin él, no se recomienda | Ya era `BR-P07`; cierra `BR-X05` |
| `V1-11` | **Sin diferenciación ABC**: política única. El campo no se elimina del modelo | `DT-029`; cierra `BR-X07` |
| `V1-12` | **Sin sobre-recepción**: `quantity_received ≤ quantity_ordered` | §21 de la especificación; cierra `BR-X08` |
| `V1-13` | **Sin inventario negativo**: `on_hand ≥ 0` | §26 y `docs/06` §14; cierra `BR-X09` |

*(`V1-03` usa el lead time **observado** desde la decisión D del 2026-09-19; la fila de arriba conserva
la redacción original para que se vea qué cambió.)*

**Diez de las trece ya estaban documentadas** y solo necesitaban nombre y parámetros. Solo `V1-03`,
`V1-05` y `V1-07` introducen algo nuevo.

**Lo que queda provisional, y por qué importa:**

- `R_v1 = 7 días` y `z_v1 = 1,65` son **parámetros técnicos**, no una frecuencia de compra ni un nivel
  de servicio acordados con nadie (`ASSUMPTION-021`, `ASSUMPTION-022`).
- V1 elige implícitamente **revisión periódica**, que es `BR-X02` (`ASSUMPTION-021`).
- V1 mide la incertidumbre sobre la **variabilidad de la demanda**, no sobre el error de pronóstico,
  porque sin modelo entrenado la segunda no existe (`ASSUMPTION-023`).
- **Ninguna salida de V1 puede presentarse como recomendación de negocio.** `BR-009` sigue rigiendo
  sin excepción fuera del entorno sintético. Es la consecuencia que no conviene olvidar.

**Lo que V1 cierra:** la cuestión **C** de la auditoría anterior. «MOQ > necesidad» pasa de no
computable a computable, porque `raw_need` ya tiene definición operativa. También se corrigió una
contradicción de `docs/06` §14 anterior a todo este bloque: el criterio decía «recomienda MOQ» y la
fórmula del mismo documento produce `⌈MOQ/M⌉·M`.

### Decisiones A–F confirmadas por el responsable (2026-09-19)

| | Decisión | Efecto |
|---|---|---|
| **A** | **Ocho componentes**, sin rediseño | La estructura vigente queda confirmada. `DT-023`–`DT-030` se conservan íntegras y «Componente 2» mantiene su significado. **Desbloquea C2** |
| **B** | `review_period = 7 días` | Ya estaba en `V1-03`; queda confirmado como valor **V1/provisional** |
| **C** | `z_v1 = 1,65` | Ya estaba en `V1-05`; confirmado como **parámetro técnico**. No se optimiza el stock de seguridad en V1 |
| **D** | **`observed_lead_time`** en lugar del acordado | **Cambia `V1-03`** y añade `V1-09`. Es la única decisión que modifica lo anterior |
| **E** | MOQ y `order_multiple` independientes | Ya estaba en `V1-06`; confirmado. `(25, 10) → 30` sigue siendo caso válido |
| **F** | Cerrar reglas pendientes de forma básica cuando sea posible | **4 cerradas**, 2 puenteadas, 7 aplazadas |

**`V1-09` — lead time observado.** Mediana de las últimas **12** observaciones válidas del par
producto–proveedor, mínimo **3** para usarla, techo de **90 días**, recalculada **en cada evaluación**
con los datos disponibles hasta la fecha de la decisión. Sin histórico suficiente: **fallback al
acordado**, declarando la procedencia. Una observación es un `PurchaseOrderItem` **completamente
recibido**, fechado por su última recepción — no una por recepción, porque eso subestimaría el lead
time justo en los proveedores con entregas parciales. Parámetros en `ASSUMPTION-024`.
El acordado **no se retira del modelo**: es el fallback y la referencia de desviación del proveedor.

**`V1-10` — elección de proveedor.** El preferente activo; sin él, no se recomienda. Cierra `BR-X05`
para V1 apoyándose en `BR-P07`, que ya lo proponía. Sin scoring ni comparación entre proveedores.

**Reglas pendientes tras la decisión F:**

- **Cerradas con interpretación técnica V1 (4):** `BR-X05` (proveedor preferente) · `BR-X07` (política
  única, sin diferenciación ABC) · `BR-X08` (sin sobre-recepción) · `BR-X09` (sin inventario
  negativo). Las cuatro siguen figurando como pendientes en §3: son provisionales y el negocio puede
  contradecirlas.
- **Pendientes de negocio, puenteadas (2):** `BR-X01` (nivel de servicio: falta el valor **y** la
  definición) · `BR-X02` (política de revisión: continua o periódica, y con qué frecuencia).
- **No necesarias para V1 (7):** `BR-X03`, `BR-X04`, `BR-X06`, `BR-X10`, `BR-X11`, `BR-X12`, `BR-X13`.

**Lo que V1 sigue sin cerrar:** `DT-010`, `DT-019`, `DT-P05`, `DT-P11` y las nueve reglas de arriba.
Ninguna bloquea al Componente 2.

### Cierre de reglas V1 (2026-09-21)

El responsable confirmó `V1-09`, `V1-09.1`, `V1-09.2` y `V1-10`, y añadió tres reglas de alcance:

| ID | Regla | Qué cambia respecto al 19-09 |
|---|---|---|
| `V1-11` | **Sin diferenciación ABC.** Ninguna regla de V1 lee `abc_class` ni `rotation_class`. **El campo no se elimina del modelo**: sigue en `docs/04` §3.2 y en las columnas 8 y 9 de `products.csv`, vacías | La interpretación que cerraba `BR-X07` pasa a ser una regla con nombre propio |
| `V1-12` | **Sin sobre-recepción.** `Σ quantity_received ≤ quantity_ordered` por línea; V1 no genera ningún escenario de sobre-recepción y el validador lo rechaza | Íd. para `BR-X08` |
| `V1-13` | **Sin inventario negativo.** `on_hand(t) ≥ 0` en todo instante; el validador lo rechaza y el motor no calcula. **No aplica a `IP_decisión`**, que sí puede ser negativo legítimamente | Íd. para `BR-X09` |

**Estado del ADR.** `DT-031` pasa de `PROPUESTA` a `ACEPTADA` **como conjunto de reglas de V1**. Yo
mismo había escrito el 19-09 que «debe seguir siendo `PROPUESTA`», y revisé esa postura: `CLAUDE.md`
§8 prohíbe marcar `ACEPTADA` lo que *todavía es una hipótesis*, y estas reglas dejaron de serlo en
cuanto el responsable las decidió. **Provisional no es hipotético.** Lo que no cambia: ninguna de las
trece reglas de `business-rules.md` §3 queda confirmada, y `R_v1`, `z_v1`, `N_v1`, `N_MIN_v1` y
`LT_MAX_v1` siguen siendo parámetros técnicos. El techo de 90 días en particular **no es una política
comercial de PluriOne** y no debe citarse como tal.

**Los trece casos de prueba: ninguno es ejecutable hoy, y no se escribió ninguno.**

Esto es lo único que no se pudo hacer de lo pedido, y conviene que quede claro por qué. Los trece
casos (lead time con 0/1/2/3/>12 observaciones, techo y su trazabilidad, proveedor preferente /
no preferente / ausente, ABC sin influencia, sobre-recepción, inventario negativo) prueban **código
que no existe**:

- Once pertenecen al **motor de abastecimiento**, que es **Fase 4** y no está autorizado.
- Dos pertenecen al **Componente 8 (validador)**, que está en la Fase 1 pero no ha comenzado.
- Los casos 1 a 11 son **pruebas unitarias del motor**: construyen sus entradas a mano, como ya
  prescribe `docs/06` §14 y exige `CLAUDE.md` §12.3. Los casos 12 y 13 son invariantes del validador
  sobre el dataset.
- Dos de ellos —el 9 (proveedores sin preferente) y el 11 (dos productos que difieran en `abc_class`)—
  **no tendrán representación en el dataset**, y es deliberado: `DT-028` §2.4/§2.5 y `DT-024` columna 8
  los hacen imposibles. Su prueba unitaria sigue siendo necesaria.
- Para una comprobación de extremo a extremo, los casos **2 a 7** necesitan órdenes y recepciones
  históricas, que producen los **Componentes 5 y 6**. El caso 1 necesita justo lo contrario —su
  ausencia— y es construible con solo las entidades maestras del Componente 2.

Crear ahora un paquete `supply_engine/` para alojarlos violaría `CLAUDE.md` §6.2 —«si una carpeta o
una capa no tiene un uso hoy, no se crea»— y §17 —«no iniciar una fase posterior sin autorización»—.
En su lugar, `DT-031` registra los trece casos **uno a uno, con su regla y su componente dueño**, de
modo que lleguen con el código que deben probar. La suite sigue en **54 pruebas de `DatasetConfig`,
todas en verde**.

**Sincronización de las dos copias (2026-09-21).** La comparación `md5sum` del árbol completo
encontró **seis** documentos del disco sin las correcciones del 2026-09-18 —`docs/04`,
`dataset-specification.md`, `DT-024`, `DT-025`, `DT-027` y `DT-028`—. Con autorización del
responsable se sobrescribieron con la versión corregida. **Ambas copias coinciden ahora byte a byte**,
con una sola excepción conocida y deliberada: `data/synthetic/generator/config.py` (0 bytes) existe
solo en el disco y **no se ha borrado** (punto 9 de *Problemas conocidos*).

**Limitación conocida registrada en este cierre.** El techo `LT_MAX_v1 = 90` **no garantiza** que el
horizonte de cobertura quepa en el horizonte de pronóstico de `ASSUMPTION-002`: `90 + 7 = 97 días ≈
13,9 semanas`, por encima de las 12 semanas, y ya a partir de un lead time observado de 78 días el
horizonte se sale del rango. El 2026-09-19 escribí que el techo restauraba esa garantía; **era falso**
y queda corregido en `DT-031` (`V1-03` y `V1-09` §6). Restaurarla exigiría bajar `LT_MAX_v1` a 77 días
o ampliar `ASSUMPTION-002`, y **ninguna de las dos se decide aquí**: el responsable confirmó 90 el
2026-09-21. Queda como limitación declarada, señalada por `LEAD_TIME_CAPPED`.

**Cambios de esta etapa:** `DT-031` (trece reglas, sub-reglas `V1-09.1`/`V1-09.2`, tabla de casos de
prueba, estado `ACEPTADA`), `docs/15` (entrada `DT-031`, versión 1.4), `docs/06` (§14 y §15 citan
`V1-10`/`V1-11`/`V1-13`; nota de V1 actualizada), `knowledge/business-rules.md` (la tabla de cierres
cita `V1-10`–`V1-13`), `knowledge/assumptions.md` (`ASSUMPTION-024` confirmada), `knowledge/glossary.md`
(clasificación ABC y lead time observado). **Sin cambios de código.**

### Componente 2 — Catalog Generator (2026-09-21)

**Implementado y probado.** Genera las cinco entidades maestras y su manifiesto; nada más.

| Archivo nuevo | Qué hace | ADR |
|---|---|---|
| `data/synthetic/generator/rng.py` | Sub-semilla y flujo pseudoaleatorio determinista | `DT-030`, `DT-032` |
| `data/synthetic/generator/policies.py` | Constantes sintéticas, Zipf, clases A–D, precondiciones | `DT-028`, `DT-029` |
| `data/synthetic/generator/writer.py` | Contrato de formato CSV y `manifest.json` | `DT-024`, `DT-025`, `DT-033` |
| `data/synthetic/generator/catalog.py` | El generador | — |
| `data/synthetic/generator/__main__.py` | `python3 -m data.synthetic.generator` | — |
| `data/synthetic/tests/test_catalog.py` | 101 pruebas nuevas | — |

**Salida con la configuración vigente** (`seed = 20260913`, 100/10/10/1, 2023-01-01 → 2026-01-01):

| Archivo | Filas | Comprobado |
|---|--:|---|
| `categories.csv` | 10 | Todas activas, jerarquía plana |
| `products.csv` | 100 | 95 activos + 5 inactivos con `valid_to = 2025-04-02`; reparto Zipf `[34,17,11,9,7,6,5,4,4,3]` |
| `suppliers.csv` | 10 | Todos activos, 12 relaciones cada uno, ninguno huérfano |
| `product_suppliers.csv` | 120 | `R = 80·1 + 10·2 + 5·3 + 5·1`; 95 preferentes; 5 productos sin proveedor activo |
| `locations.csv` | 1 | `MAIN_WAREHOUSE` |
| `manifest.json` | — | Nueve campos obligatorios; sin `scenario_assignment` ni `quality_report` |

`dataset_version = ds-a4e50751841e`. Salida en `data/synthetic/output/`, **no versionada**.

**Dos decisiones que los ADR dejaban para este momento**, ambas registradas:

- **`DT-032` — algoritmo pseudoaleatorio.** §44 decía literalmente que fijarlo era trabajo del
  Componente 2, y advertía de un **límite conocido**: el flujo de `random` no garantiza igualdad byte
  a byte entre versiones de Python. Se adoptó un **contador sobre SHA-256**, de modo que cada
  extracción es función pura de `(sub-semilla, etiqueta, contador)`. El límite queda **cerrado**, no
  documentado. El generador no usa `random` en ninguna parte.
- **`DT-033` — versionado.** `generator_version` semántica sobre la salida observable; `dataset_version`
  **derivada** por hash de la configuración y esa versión, de modo que regenerar el mismo dataset da
  el mismo identificador. `components[].version` se mantiene aparte, porque `DT-028` §8 lo usa para
  rastrear qué políticas produjeron el dataset.

**Revisión adversarial independiente.** Dos revisores con contexto limpio auditaron el código y su
conformidad con los ADR (~28 000 configuraciones de barrido). Encontraron **cinco defectos reales**,
todos verificados y corregidos antes de cerrar:

| Defecto | Consecuencia | Corrección |
|---|---|---|
| El ancho fijo de los códigos se desbordaba | Con `category_count > 999` los CSV salían **desordenados en silencio**, rompiendo el orden por clave de negocio de `DT-024` | `policies.code_width()` amplía el ancho con la escala, como `DT-028` §4 ya preveía |
| `below(bound > 2⁶⁴)` no terminaba nunca | Bucle infinito latente en un método público documentado como total | Extrae tantas palabras de 64 bits como haga falta |
| La `Z` de UTC se estampaba sin convertir | Una hora local rotulada como UTC: un instante falso con aspecto autoritativo | `to_utc()` convierte y **rechaza** un `datetime` sin zona |
| La red de seguridad no cubría `DT-028` §2.4 ni §7 | Un fallo futuro en el preferente o en los estados no se habría detectado | Ambas garantías se comprueban ahora, y los problemas se acumulan en vez de cortar al primero |
| Un `10` literal como lead time testigo | Único número del código ausente de `DT-028`, contra su principio de «un solo documento» | Se sustituye por un ajuste de un día, sin constante nueva |

Dos correcciones más, de documentación: §43.4 de la especificación listaba **tres** precondiciones
cuando `DT-028` §8 tiene **cinco** desde el 2026-09-18 (`docs/15` repetía el error), y `DT-028` §1.5
aparecía **dos veces** por un error de numeración.

**Lo que el Componente 2 NO hace**, y es deliberado: no genera demanda, inventario, movimientos,
órdenes, recepciones ni comportamiento de proveedores; no asigna escenarios a SKU; no valida el
dataset; no calcula nada de abastecimiento. `abc_class`, `rotation_class`, `shelf_life_days`,
`currency`, `contact_info`, `description`, `parent_id`, `created_at` y `updated_at` quedan vacíos por
`DT-029`, y las columnas siguen en el archivo porque el esquema es el de la entidad.

**Pendientes reales que deja este componente:**

1. ~~La tabla canónica de identificadores de componente sigue sin existir~~ — **RESUELTO el
   2026-09-21**, ver la sección siguiente.
2. **`generate()` no borra el directorio de salida.** `DT-024` dice que «cada ejecución regenera el
   directorio completo»; hoy sobrescribe los seis archivos pero no elimina huérfanos. Inocuo con un
   solo componente; hay que resolverlo cuando el Componente 3 cambie el conjunto de archivos.
3. **Al añadir el Componente 3 hay que subir `generator_version`** (`DT-033`). Si no, dos datasets con
   contenidos distintos declararían el mismo `dataset_version`.
4. `PurchaseOrder`, `PurchaseOrderItem`, `PurchaseOrderReceipt` e `InventoryPolicy` **siguen sin
   `data_origin`** en sus fichas (`DT-026`). Debe cerrarse antes de autorizar los Componentes 5 y 6.

### Identificadores canónicos de componente (2026-09-21)

Cerrado el último pendiente que bloqueaba al Componente 3. `DT-030` fija la sub-semilla como
`sha256("<seed>:<identificador>")`, de modo que **el identificador tenía que decidirse antes de que un
componente generara datos**: decidirlo después cambiaría esos datos.

| # | Componente | Identificador | Nota |
|---|---|---|---|
| 1 | `DatasetConfig` | **ninguno** | No extrae del flujo pseudoaleatorio; no tiene sub-semilla |
| 2 | Catalog Generator | `catalog` | **Sin cambios**: ya estaba en uso |
| 3 | Demand Generator | `demand` | |
| 4 | Inventory Simulator | `inventory` | |
| 5 | Purchase Order Generator | `orders` | Nombrado por lo que produce, no por el archivo |
| 6 | Supplier Behaviour Generator | `supplier_behaviour` | El único con guion bajo, y es deliberado |
| 7 | Scenario Assignment | `scenarios` | |
| 8 | Dataset Validator + informe de calidad | `validator` | El informe es **parte de este componente** |

`COMPONENT_IDS` en `rng.py`, con una constante por componente. Nueve pruebas nuevas los fijan contra
la fórmula de `DT-030` y comprueban las propiedades que el ADR exige: ASCII en minúsculas, distintos
de su número, únicos, y sub-semillas todas distintas. Una de ellas comprueba la propiedad que
justifica toda la decisión: **renumerar los componentes no cambia ninguna sub-semilla.**

**El Componente 2 no se tocó** y sus cinco CSV salen byte a byte idénticos tras el cambio.

**Quality Report: opción A, dentro del Componente 8.** No fue una preferencia; lo sostienen `DT-023`
(«Validador del dataset (Componente 8)»), `DT-025` (`quality_report` → «Componente 8»), la tabla de
este archivo y `DT-031` (casos de prueba 12 y 13 → «Componente 8»). La ambigüedad que `DT-030`
registraba venía de la prosa de `CLAUDE.md` §17, corregida el 2026-09-21: **ninguna decisión aceptada
propuso nunca un noveno componente.**

**Sigue pendiente, y esta decisión no lo toca:** si `quality_report` se escribe dentro de
`manifest.json` o como archivo aparte. `DT-025` lo aplaza al autorizar el Componente 8.

Corregido de paso un descuido del cierre anterior: la tabla *Fase 1 — avance por componente* seguía
declarando el Componente 2 como «no iniciado, pendiente de autorización» mientras el resto del archivo
lo daba por implementado.

### Componente 3 — Demand Generator (2026-09-23)

**Implementado y probado.** Produce `demand.csv`: la **demanda latente**, producto × ubicación × día.

**La distinción que introduce esta etapa**, y que es su razón de ser:

```text
C2 → products.csv, locations.csv
   → C3 → demand.csv        demanda LATENTE     lo que se habría demandado
   → C4 → consumption.csv   demanda SATISFECHA  lo que las existencias permitieron
                            + is_stockout_affected
```

`docs/04` §3.8 ya advertía que un modelo entrenado sobre el consumo «aprende que la demanda bajó»
justo donde faltó producto. Con las dos series en disco, ese sesgo deja de ser una advertencia y pasa
a ser **una cantidad medible**: la diferencia entre ambas. Es lo que permitirá cerrar `DT-011` —cuyo
método sigue pendiente— comparando los cuatro tratamientos posibles contra la demanda real, que en el
entorno sintético sí se conoce y con datos reales no se conocerá nunca.

**El Componente 3 no escribe `consumption.csv`**, no conoce las existencias y no lleva
`is_stockout_affected`. Todo eso es del Componente 4.

| Archivo nuevo | Qué hace |
|---|---|
| `data/synthetic/generator/demand.py` | El componente |
| `data/synthetic/tests/test_demand.py` | 71 pruebas |
| `docs/decisions/DT-034-demanda-latente-persistente.md` | `Demand` como entidad persistente + contrato de `demand.csv` |
| `docs/decisions/DT-035-politicas-generacion-demanda.md` | Políticas sintéticas de demanda |

**Salida con la configuración vigente** (`seed = 20260913`, 100 productos, 2023-01-01 → 2026-01-01):

| | |
|---|---|
| Filas | **108 235** — 95 productos activos × 1096 días + 5 inactivos × 823 |
| Tamaño | ~3,5 MB, no versionado |
| Columnas | `id`, `product_id`, `location_id`, `occurred_on`, `quantity`, `data_origin` |
| Periodo | **semiabierto** `[2023-01-01, 2026-01-01)` → último día **2025-12-31** |
| Densidad | Una fila por día vigente; `quantity = 0` los días sin demanda |
| `quantity` | **Entero** ≥ 0, para toda unidad de medida en V1 |

**Los ocho comportamientos, medidos sobre la serie generada** —no leídos de una etiqueta—:

| Comportamiento | Evidencia en los datos |
|---|---|
| `STABLE_DEMAND` | CV 0,06 |
| `ERRATIC_DEMAND` | CV 0,36 — seis veces la estable, con nivel medio comparable |
| `GROWING_DEMAND` | Último 10 % del periodo = 1,53× el primero |
| `DECLINING_DEMAND` | 0,46×, sin llegar nunca a cero |
| `SEASONAL_DEMAND` | Autocorrelación a 365 días: 0,46 (estable: −0,00) |
| `INTERMITTENT_DEMAND` | 85 % de días en cero (estable: 0 %) |
| `HIGH_ROTATION` | 41,7 unidades/día de media |
| `LOW_ROTATION` | 3,0 unidades/día |

**Dos ejes ortogonales, no una lista de ocho.** Cada producto recibe una **forma** (seis) y una
**rotación** (dos), cada eje con su mezcla al 100 % y suelo de uno. Fundirlos en una sola lista haría
que «alta rotación» fuera incompatible con «estacional», lo cual no describe ningún producto: la
rotación es magnitud y la forma es reparto temporal. `DT-023` §7.2 ya trata la rotación como eje
aparte.

**Decisiones técnicas que hubo que tomar al implementar:**

- **Onda triangular en lugar de senoidal** para la estacionalidad. `math.sin` lo calcula la `libm` de
  la plataforma y sus últimos bits no están garantizados entre versiones; un solo flotante habría
  deshecho la identidad byte a byte de `DT-032` para cada producto estacional. Todo el mecanismo es
  aritmética entera en por mil, sin un solo flotante.
- **La intermitencia tiene mecanismo propio.** Sus ceros son días sin evento, no un nivel pequeño que
  redondea a cero. Si fuera lo segundo, una serie intermitente sería una estable de bajo volumen con
  otra etiqueta, y §8.5 quedaría incomprobable.
- **C3 lee los CSV de C2**, no un objeto en memoria. La dependencia de la arquitectura es
  `C2 → products.csv/locations.csv → C3`, y leer los archivos la hace real.
- **`generator_version` sube a 0.2.0** (`DT-033`): el generador produce datos distintos, y no subirla
  habría hecho que dos datasets con contenidos distintos declararan el mismo `dataset_version`.

**Pendientes reales antes del Componente 4 — los cuatro cerrados el 2026-09-24:**

1. ✅ **Cómo recorta C4 la demanda latente.** Cerrado: `consumption = min(demanda latente, existencia
   antes del consumo)`, **por día y sin backlog**; la demanda no satisfecha se pierde y `lost_sales`
   es derivable, no almacenada (`DT-038` §4).
2. ✅ **El contrato de columnas de `consumption.csv`.** Cerrado en `DT-038` §4, junto con los de
   `inventory_movements.csv` (§5) e `inventory.csv` (§6), y los tres del Componente 5 en `DT-039`.
3. ✅ **Limpieza del directorio de salida.** Cerrado en `DT-038` §13, con el comportamiento
   aprobado: **no se borra nada indiscriminadamente**; si el directorio contiene archivos ajenos al
   conjunto que la ejecución va a producir, la generación **falla explícitamente** en lugar de
   producir un dataset mezclado en silencio. **Completado el 2026-09-26 por `DT-040`**: además de la
   comprobación previa, cada ejecución trabaja en un workspace propio y `output/` solo cambia por
   promoción al final, de modo que una ejecución fallida nunca lo modifica. La implementación es de
   la fase de código.
4. ✅ **`generator_version`.** Cerrado: **`0.3.0`**, un único incremento para el lote C6 + C4 + C5
   (`DT-036` §8). Se aplicará al implementar, junto con la actualización de la prueba que hoy afirma
   `"0.2.0"`.

### Componente 4 — Inventory Simulator (2026-09-26)

**Implementado y probado. No conectado a `__main__`.** Lee `products.csv`, `locations.csv`,
`product_suppliers.csv` y `demand.csv` del directorio que recibe, más los perfiles de proveedor **en
memoria**, y escribe `consumption.csv`, `inventory_movements.csv` e `inventory.csv` en ese mismo
directorio; entrega en memoria las órdenes causales, sus líneas y sus recepciones, con los
identificadores ya asignados, para el Componente 5.

| Archivo | Qué hace |
|---|---|
| `data/synthetic/generator/inventory.py` | **Nuevo.** El componente: fórmulas de `DT-036`, bucle causal diario de `DT-038` §3, identificadores en seis pasos (§8), precondiciones (§16) |
| `data/synthetic/tests/test_inventory.py` | **Nuevo.** 88 pruebas |
| `data/synthetic/generator/policies.py` | Banner de `DT-036`: `W`, `M`, `C`, factores y mezcla de apertura |
| `data/synthetic/generator/writer.py` | `INVENTORY_VERSION = "0.1.0"`; `GENERATOR_VERSION` **sigue en 0.2.0** |
| `data/synthetic/generator/__init__.py` | Docstring y exportaciones |

**Decisiones tomadas al autorizar la implementación:**

- **D-C4-1 = O1.** `q1 = min(Q_final − 1, max(1, ceil(Q_final × split / 1000)))`, `q2 = Q_final − q1`.
  La fórmula anterior de `DT-037` §3 daba `q2 = 0` para `Q_final` de 2 a 4 con `split = 800`. El
  defecto era latente: con el catálogo vigente ninguna ventana produce `Q_final ≤ 4` (mínimo: 10).
- **D-C4-2 = P1.** P-C4-2 (`period.days ≥ 28`) y P-C4-3 (cada producto vigente al menos 28 días del
  periodo). Si fallan: `GeneratorError`, nada simulado, nada escrito. La ventana no se acorta, no se
  rellena y no se extrapola.
- **D-C4-3.** `L = agreed_lead_time_days` de la relación preferente activa, también para
  `expected_on`; `V1-09` y `R_v1` no intervienen; `M = 7` es solo el margen de la apertura; el disparo
  se evalúa todos los días.

**Cómo se prueba.** Además de las pruebas unitarias de cada fórmula, una **repetición independiente**
(`audit`) recalcula día a día, a partir solo de los archivos escritos y con aritmética propia
(`Fraction`, `W = 28`, `C = 21` literales), el consumo, la marca de desabasto, el disparo, la cantidad,
la fecha comprometida, las recepciones y el snapshot, y la aplica al dataset pequeño, a tres
escenarios hechos a mano y a la escala completa. Se comprobó además que la suite **detecta** trece
defectos inyectados a propósito en una copia desechable del módulo (umbral con `M`, disparo antes del
consumo, fórmula de reparto antigua, guarda de `V1-06` ausente, revisión semanal, backlog, fecha
comprometida desplazada, entre otros).

**Salida a escala completa, con perfiles de prueba** —construidos a mano con los valores de `DT-037`
§2 y un reparto cíclico que **no** es el del Componente 6, de modo que estas cifras no son las del
dataset que se publique—: 108 235 filas de consumo (las mismas que `demand.csv`), 93 010 movimientos
(100 aperturas, 3 951 recepciones, 88 959 salidas), 3 625 órdenes causales (3 536 recibidas, 85
emitidas y 4 parcialmente recibidas al corte), 10 994 días-par con desabasto; ~3 s.

**Lo que no hace, deliberadamente:** no escribe los archivos de órdenes (C5), no crea órdenes
`CANCELLED` ni forma `order_number` (C5, decisión A2), no asigna perfiles de proveedor (C6), no
publica ni conoce `output/` (`DT-040`) y **no calcula `metrics`**: `DT-038` §12 las cita contra una
«`DT-036` §17 del acuerdo» que no existe en el repositorio, y queda registrado como **pendiente
documental**.

**`generator_version` no sube.** Con C4 sin conectar, el artefacto publicado de toda configuración
aceptada es byte a byte el mismo, y la regla de `DT-033` no se activa. El incremento a `0.3.0` de
`DT-036` §8 llega con el lote C6 + C4 + C5 conectado.

### Componente 5 — Purchase Order Generator (2026-09-28)

**Implementado y probado. No conectado a `__main__`.** Recibe en memoria el `SimulationResult` del
Componente 4, lee `products.csv` solo para `valid_to`, y escribe `purchase_orders.csv`,
`purchase_order_items.csv` y `purchase_order_receipts.csv` en el directorio que recibe, extendiendo
el manifiesto con `orders`. **Materializa, no simula**: no recalcula ninguna fecha, cantidad, estado
ni identificador del Componente 4, y no lo importa en tiempo de ejecución (`DT-039` §1).

| Archivo | Qué hace |
|---|---|
| `data/synthetic/generator/orders.py` | **Nuevo.** El componente |
| `data/synthetic/tests/test_orders.py` | **Nuevo.** 55 pruebas |
| `data/synthetic/generator/policies.py` | Banner de `DT-039`: `ORDERS_CANCELLED_PERMILLE = 20`, `ORDERS_CANCELLED_CLOSE_LAG_DAYS = 1` |
| `data/synthetic/generator/writer.py` | `ORDERS_VERSION = "0.1.0"`; `GENERATOR_VERSION` **sigue en 0.2.0** |
| `data/synthetic/generator/__init__.py` | Docstring y exportaciones |

**Política `CANCELLED`, en el orden de `DT-039` §5.2:** universo de plantillas filtrado por la regla
de D-01 (cierre previsto `< end_date` y `<= valid_to` o nulo) → `K = max(1, ceil(N × 20 / 1000))`
con `N` = órdenes causales, acotado por el tamaño del universo → B2 (`GeneratorError` con universo
vacío, incluido `N = 0`) → permutación `cancelled-selection` → gemelas con `closed_at = issued_at + 1
día`, sin recorte, numeradas a continuación de las causales. `order_number = "PO-" + id` con relleno
`max(6, dígitos del id más alto)`.

**Cómo se prueba.** Pruebas unitarias de cada regla —la elegibilidad se compara con la especificación
ejecutable del cierre de D-01—, casos hechos a mano para cada frontera, y una auditoría independiente
de los tres archivos sobre el pipeline C2 → C3 → C4 → C5 a escala pequeña y completa. En una copia
desechable del módulo se inyectaron diecisiete defectos —entre ellos `<=` por `<`, filtrado después de
la selección, `K` sobre el universo, B2 eliminado, `closed_at` recortado a `valid_to`,
`order_number` duplicado, `expected_at` recalculado, selección no determinista y referencias
huérfanas— y la suite detectó los diecisiete.

**Salida a escala completa, con los perfiles de prueba de C4** (no los de C6): 3 625 órdenes causales,
3 620 plantillas elegibles, `K = 73` canceladas; 3 698 órdenes y líneas, 3 951 recepciones.

### Componente 6 — Supplier Behaviour Generator (2026-09-28)

**Implementado y probado. No conectado a `__main__`.** Lee `suppliers.csv` del directorio que recibe
y devuelve, en memoria, una tupla de `SupplierProfile` —uno por proveedor, activos e inactivos,
ordenados por `supplier_id`— para el Componente 4. **No escribe ningún archivo de datos**; su única
traza persistente es su entrada en `manifest.components` (decisión A1).

| Archivo | Qué hace |
|---|---|
| `data/synthetic/generator/supplier_behaviour.py` | **Nuevo.** El componente |
| `data/synthetic/tests/test_supplier_behaviour.py` | **Nuevo.** 40 pruebas |
| `data/synthetic/generator/policies.py` | Banner de `DT-037`: tablas de §2, mezclas 40/40/20 y 70/30, P-C6-1 |
| `data/synthetic/generator/writer.py` | `SUPPLIER_BEHAVIOUR_VERSION = "0.1.0"`; `GENERATOR_VERSION` **sigue en 0.2.0** |
| `data/synthetic/generator/__init__.py` | Docstring y exportaciones |
| `data/synthetic/generator/inventory.py`, `data/synthetic/tests/test_inventory.py` | Solo comentarios que decían que C6 no existía (O2); ninguna línea de lógica |

**Reparto y asignación.** Cupos por mayor resto con suelo de uno —el mismo auxiliar que usan C3 y
C4—, y dos permutaciones independientes, `punctuality-assignment` e `integrity-assignment`, sobre
`sub_seed(seed, "supplier_behaviour")`. Con los 10 proveedores vigentes: **4 / 4 / 2** y **7 / 3**.
`SupplierProfile` se importa de `inventory.py`, solo el tipo (decisión A2).

**Cómo se prueba.** Valores de los cinco perfiles; reparto contra un oráculo independiente para todo
`n` entre 3 y 119; cobertura de inactivos; P-C6-1; determinismo e independencia de los ejes;
entrada del manifiesto sin archivos; y el pipeline en su orden aprobado, `C2 → C3 → C6 → C4 → C5`,
a escala pequeña y completa, con las auditorías independientes de C4 y C5. En una copia desechable se
inyectaron dieciséis defectos —desigualdad del reparto, suelo de uno eliminado, proporción cambiada,
una sola permutación para los dos ejes, etiqueta de sub-semilla o de secuencia cambiada, un eje
dependiente del otro, inactivos omitidos, perfiles desordenados o duplicados, P-C6-1 relajada,
archivo de datos escrito, versión del generador alterada, entre otros— y la suite detectó los
dieciséis.

**Con los perfiles reales de C6 a escala completa**, C4 emite 3 632 órdenes causales; C5 materializa
todas y añade las canceladas. Estas cifras sustituyen, como referencia, a las obtenidas con perfiles
de prueba en las secciones de C4 y C5; el dataset publicado **no cambia** hasta W1.

### W1 — Publicación del dataset (2026-09-29)

**Implementado.** `data/synthetic/generator/pipeline.py`, función `run`, invocada por `__main__.py`.
Decisiones del responsable aplicadas: **`GENERATOR_VERSION` 0.2.0 → 0.3.0** para el lote C6 + C4 +
C5 (`DT-036` §8) y **promoción según `DT-040` §5**, con el directorio anterior solo de forma
transitoria. Los dos detalles pendientes de `DT-040` quedan resueltos: el `.anterior` se elimina
tras una promoción correcta y el workspace de una ejecución fallida también se elimina.

```text
check_output(output/) → tmp/<uuid>/ → C2 → C3 → C6 → C4 → C5 → verify → promote → output/
```

| Archivo | Qué hace |
|---|---|
| `data/synthetic/generator/pipeline.py` | **Nuevo.** Comprobación previa, workspace, los cinco componentes, verificación final, promoción |
| `data/synthetic/generator/__main__.py` | Ejecuta `pipeline.run`; ya no llama a ningún componente directamente |
| `data/synthetic/generator/writer.py` | `GENERATOR_VERSION = "0.3.0"` |
| `data/synthetic/tests/test_pipeline.py` | **Nuevo.** 29 pruebas |
| Pruebas de C3–C6 | Solo las aserciones de versión (`0.2.0` → `0.3.0`) y las de «no conectado», que ahora comprueban que el componente se alcanza **solo** a través de W1 |

**Garantía, sin exagerarla.** Un fallo en la comprobación previa, en cualquier componente o en la
verificación deja `output/` idéntico byte a byte y `tmp/` vacío. La promoción son dos renombrados:
**no** es atómica —`output/` no existe durante un instante— y, si fallan a la vez el segundo
renombrado y la restauración, el dataset anterior queda íntegro en `tmp/<id>.anterior/` y el error
lo dice. Detalle en `DT-040` §9.

**Cómo se prueba.** Fallos reales de C2 (P-1), C3 (P-6) y C4 (P-C4-2) después de que otros
componentes hayan escrito; fallos inyectados de C6 y C5, de la verificación (archivo intruso, bytes
alterados, manifiesto incompleto, existencia negativa) y de cada renombrado de la promoción; éxito,
sustitución completa de un dataset anterior, determinismo byte a byte y ausencia del identificador
del workspace en el artefacto. En una copia desechable se inyectaron **catorce** defectos de W1 —C2
escribiendo en `output/`, promoción omitida, promoción pese al fallo de C5, archivos parciales en
`output/`, promoción por copia, sin verificación, identificador en el manifiesto, contenido no
determinista, workspace no limpiado, archivo temporal en `output/`, sin restauración (c),
`.anterior` borrado en doble fallo, sin comprobación previa, `.anterior` no borrado— y la suite
detectó los catorce.

**Dataset publicado** (`python3 -m data.synthetic.generator`, 2026-09-29): `ds-269a698250db`,
`generator_version` 0.3.0, 12 CSV + `manifest.json`; 108 235 filas de consumo, 93 012 movimientos,
3 705 órdenes (3 543 recibidas, 88 emitidas, 1 parcialmente recibida y 73 canceladas) y 3 810
recepciones. Los seis CSV de C2 y C3 son byte a byte los del dataset anterior; una reproducción
independiente de la ejecución coincide byte a byte con lo publicado, y las auditorías independientes
de C4 y C5 no encuentran ningún problema. No quedó nada en `tmp/`.

### Componente 7 — Scenario Assignment (2026-09-29)

**Implementado y probado, sin integrar en W1.** Contrato en `DT-041`; decisiones C7/C8-01 a 14 de la
auditoría del mismo día.

| Archivo | Qué hace |
|---|---|
| `docs/decisions/DT-041-asignacion-escenarios-c7.md` | **Nuevo.** Contrato: forma de `scenario_assignment`, los 16 ejes, criterios, cláusula `SYNTHETIC_COVERAGE_CRITERION`, nivel C sin etiqueta |
| `data/synthetic/generator/scenarios.py` | **Nuevo.** `build_assignment`, `generate`, `load_facts`, `observed_axes`, `supplier_axes`, `emergent_properties` y la aritmética de §6.6 y §8 |
| `data/synthetic/generator/writer.py` | `SCENARIOS_VERSION = "0.1.0"` y `add_manifest_field` (añade un campo, nunca sobrescribe). Ninguna función existente cambia |
| `data/synthetic/tests/test_scenarios.py` | **Nuevo.** 46 pruebas |
| `DT-031` (`V1-07`, `V1-08`), `DT-030`, `docs/15` | Notas de redacción: C7 registra y mide, no asigna; el validador no clasifica sobreinventario según `BR-X03` |

**Qué registra.** Los 16 ejes en el orden del enum, cada uno con `unit`, `basis`, `criterion`,
`source`, `suppliers` y `products`. Forma y rotación: la decisión de C3, reconstruida con
`build_demand` y aceptada solo si coincide byte a byte con `demand.csv`. Proveedores: unidad
`supplier` y productos como evidencia (`RELIABLE = PUNCTUAL ∧ COMPLETE`, `DELAYED = LATE`,
`PARTIAL = SPLIT`, `IRREGULAR` sin etiqueta). `LOW_INVENTORY` y `OVERSTOCK` con criterios
`SYNTHETIC_COVERAGE_CRITERION`, que **no** son reglas de negocio. El nivel C se detecta en
`emergent_properties` y **no** se escribe: lo reportará C8.

**Sobre el dataset publicado** (solo lectura), los 16 ejes y las cuatro situaciones de nivel C tienen
casos. También en R2, R3 y R1 con tres proveedores, generados en directorios temporales y
contrastados con una reproducción independiente escrita en las pruebas.

**No cambia:** C2–C6, `pipeline.py`, `GENERATOR_VERSION` (0.3.0) ni `output/`. En una copia
desechable se inyectaron **diecinueve** defectos —etiquetas de flujo de C3, orden y contenido del
enum, un escenario omitido, orden invertido, sin comprobación SHA, correspondencias de C6 erróneas,
`IRREGULAR` etiquetado, lead time igual contado como múltiple, umbral y guarda de `OVERSTOCK`,
sobrescritura, CSV escrito, sorteo propio, y los bordes de `LOW_INVENTORY`, retraso, entrega
parcial y propiedades 12 y 18— y la suite detectó los diecinueve.

### Componente 8 — Dataset Validator + informe de calidad; generador 0.4.0 (2026-09-29)

**Implementado, integrado y publicado.** Contrato en `DT-042`.

| Archivo | Qué hace |
|---|---|
| `docs/decisions/DT-042-validador-dataset-quality-report.md` | **Nuevo.** Catálogo de 51 comprobaciones, contrato de `quality_report`, anomalías, fallos, integración y versión |
| `data/synthetic/generator/validator.py` | **Nuevo.** `validate` (no escribe) y `generate` (añade `quality_report` y su componente) |
| `data/synthetic/generator/pipeline.py` | `generate_into` ejecuta C7 y C8 tras C5; `COMPONENT_VERSIONS` con siete componentes; `verify` exige `scenario_assignment` y un `quality_report` sin fallos |
| `data/synthetic/generator/writer.py` | `VALIDATOR_VERSION = "0.1.0"`; **`GENERATOR_VERSION` 0.3.0 → 0.4.0**, un solo incremento |
| `data/synthetic/tests/test_validator.py` | **Nuevo.** 67 pruebas, entre ellas la inyección de fallos por familia |
| Pruebas de C3–C7 y W1 | Versión esperada 0.4.0; fixtures de C7 y C8 que se detienen en C5; pruebas de verificación que alteran el workspace **después** de C8; semilla 4 en lugar de 1 para el segundo dataset de `test_pipeline` (ver abajo); pruebas nuevas de fallo de C7 y C8, manifiesto completo, reproducibilidad salvo `generated_at` y R2/R3 de extremo a extremo |

**Validación.** C8 lee solo el workspace y comprueba manifiesto, formato, origen, identidad,
referencias, reglas comerciales, recepciones, canceladas, `order_number`, inventario, consumo,
temporalidad (con la excepción de `DT-027`), vocabularios, `scenario_assignment`, cobertura de
`scenarios.required` y las cuatro situaciones de nivel C. Acumula todos los fallos antes de lanzar
`GeneratorError`. En una copia desechable se inyectaron **16** defectos en el propio validador y la
suite detectó los 16.

**Hallazgo: a escala muy pequeña la cobertura depende de la semilla.** Con 12 productos y 59 días,
6 de las 14 semillas probadas (1–3, 11, 12 y 14) dejan un escenario requerido o una situación de
nivel C sin caso, y C8 rechaza la ejecución —el comportamiento aprobado en la decisión C7/C8-07—. La
configuración vigente, R2 (semilla por defecto) y R3 pasan. `test_pipeline` usaba la semilla 1 para
su segundo dataset y ahora usa la 4.

**Dataset publicado** (`python3 -m data.synthetic.generator`, 2026-09-29): `ds-6c8ad65b4999`,
`generator_version` 0.4.0, 12 CSV + `manifest.json` con 11 campos y 7 componentes. `quality_report`:
51/51, 0 fallos, 16/16 escenarios cubiertos, nivel C 8/12/18/20 con 100/67/26/5 productos,
`anomalies: []`. Dos generaciones independientes dieron los mismos CSV byte a byte y el mismo
manifiesto salvo `generated_at`; los doce CSV son byte a byte los del dataset 0.3.0. El 0.3.0
permaneció intacto hasta que el 0.4.0 superó todas las comprobaciones y la promoción lo sustituyó
según `DT-040` §5. Informe breve en `docs/reports/dataset-sintetico-0.4.0-calidad.md`.

## Próximos pasos

1. **Cierre de la Fase 1 y autorización de la siguiente.** El generador está terminado (0.4.0). Lo
   que la hoja de ruta de la Fase 1 lista fuera del generador —proceso de ingesta con marca de
   origen (US-011) y umbrales de aceptación del modelo (`DT-P04`)— sigue pendiente y es decisión del
   responsable cuándo abordarlo.
3. **Recabar del negocio los parámetros pendientes** (`knowledge/business-rules.md` §3). Es el
   trabajo de mayor valor y no depende de programar nada: sin estos datos, la Fase 4 no puede
   parametrizarse de forma definitiva.
4. **Confirmar o refutar los supuestos de mayor riesgo:** ASSUMPTION-008 (corpus documental),
   ASSUMPTION-004 (el consumo aproxima la demanda), ASSUMPTION-003 (histórico suficiente),
   ASSUMPTION-012 (volumen).
5. **Decidir `DT-P12`:** si la tabla de §25 debe ampliarse con las filas «Alta rotación» y «Baja
   rotación», o si basta con dejar constancia de que §8 y §10.4 la complementan. Es una decisión
   sobre la especificación y **sigue abierta**; `DT-023` no la resuelve.
6. **Mantener sincronizadas ambas copias.** El punto 10 de *Problemas conocidos* quedó resuelto el
   2026-09-21, pero su causa —correcciones aplicadas en la copia de trabajo que no llegaron al
   disco— puede repetirse. Comprobación barata al cierre de cada bloque: `md5sum` del árbol en ambos
   lados.


> **Ningún componente posterior del generador se inicia sin instrucción explícita del responsable.**

## Archivos importantes

| Archivo | Para qué |
|---|---|
| `CLAUDE.md` | **Leer primero.** Reglas permanentes del proyecto |
| `AGENTS.md` | Protocolo de trabajo de los agentes de IA |
| `project/status.md` | Este archivo: dónde está el proyecto ahora |
| `project/roadmap.md` | Fases, dependencias y criterios de finalización |
| `project/backlog.md` | Épicas, historias y prioridades |
| `docs/01-requerimientos.md` | Qué debe hacer el sistema |
| `docs/03-arquitectura.md` | Cómo está organizado |
| `docs/06-motor-abastecimiento.md` | El núcleo de valor del sistema |
| `docs/15-decisiones-tecnicas.md` | Por qué se decidió cada cosa |
| `knowledge/assumptions.md` | Qué se ha dado por cierto sin confirmar |
| `knowledge/business-rules.md` | Qué falta que el negocio defina |
| `knowledge/dataset-specification.md` | **Especificación del dataset.** Lectura obligatoria para cualquier trabajo de la Fase 1 |
| `docs/decisions/DT-023-clasificacion-escenarios.md` | Matriz de las 26 situaciones de §25 y su reparto en Niveles A/B/C |
| `docs/decisions/DT-024-contrato-salida-componente-2.md` | Contrato de salida: CSV por entidad y columnas de las cinco entidades maestras |
| `docs/decisions/DT-025-manifest-metadata-generacion.md` | Contrato de `manifest.json` |
| `docs/decisions/DT-027-vigencia-producto.md` | `valid_from` / `valid_to` frente a `created_at` / `updated_at` |
| `docs/decisions/DT-028-politicas-generacion-sintetica.md` | **Valores sintéticos del Componente 2.** Leer la advertencia de cabecera antes de citar cualquier cifra |
| `data/synthetic/config/config.py` | Componente 1: el contrato de configuración del generador |
| `data/synthetic/config/dataset_config.yaml` | La configuración vigente del dataset sintético |
| `docs/decisions/DT-036-politicas-sinteticas-inventario.md` | **Valores sintéticos del Componente 4** |
| `docs/decisions/DT-038-contrato-salida-c4.md` | Contrato de salida y precondiciones del Componente 4 |
| `data/synthetic/generator/inventory.py` | Componente 4: el simulador de inventario |
| `docs/decisions/DT-041-asignacion-escenarios-c7.md` | Contrato del Componente 7. **Leer la advertencia `SYNTHETIC_COVERAGE_CRITERION`** antes de citar un criterio |
| `data/synthetic/generator/scenarios.py` | Componente 7: `scenario_assignment` |
| `docs/decisions/DT-042-validador-dataset-quality-report.md` | Contrato del Componente 8 y del informe de calidad |
| `data/synthetic/generator/validator.py` | Componente 8: validación y `quality_report` |

## Historial de actualizaciones

| Fecha | Cambio |
|---|---|
| 2026-09-03 | Creación del repositorio y ejecución completa de la Etapa 0 |
| 2026-09-04 | **Etapa 0.1** — auditoría y corrección. 15 problemas, 35 correcciones. `DT-019`–`DT-022`, `RML-013`, `US-034`, `US-035`, `US-058`, `ASSUMPTION-019`, `ASSUMPTION-020`. Resultado: APROBADA CON OBSERVACIONES |
| 2026-09-14 | **Fase 1 — Datos, autorizada.** Componente 1 `DatasetConfig` implementado y probado (37 pruebas en verde). Estructura `data/synthetic/`. El dataset todavía no se genera |
| 2026-09-15 | Corrección: `knowledge/dataset-specification.md` **sí existía**; el informe del 14-09 lo dio por inexistente al inspeccionar una copia de trabajo desactualizada en lugar del repositorio real. Copia resincronizada y verificada contra el disco. Contrastado `DatasetConfig` con la especificación: coherente, salvo el desajuste de escenarios registrado como problema 8 |
| 2026-09-16 | Auditoría de la discrepancia 14 vs. 26 escenarios. Conclusión: tres niveles, no dos listas |
| 2026-09-17 | **`DT-023` aceptada.** Enum `Scenario` ampliado de 14 a 16 (`LOW_INVENTORY`, `PARTIAL_DELIVERY`); matriz de las 26 situaciones en `docs/decisions/DT-023-clasificacion-escenarios.md`; 46 pruebas en verde. Problema 8 cerrado |
| 2026-09-17 | **Auditoría del Componente 1: NO APROBADA y corregida.** Recuento de la matriz de §25 rectificado (13 A + 9 B + 4 C = 26, antes 11 + 9 + 5); `_parse_scale` acumula ya todos los errores de tipo; `validate()` comprueba lista no vacía, ausencia de duplicados y orden canónico; `required_scenarios` pierde su valor por defecto; pruebas ampliadas de 46 a **54, todas en verde**. La clasificación A/B/C no se rediseñó. Componentes 2–8: no iniciados |
| 2026-09-17 | **Auditoría del Componente 2** (solo lectura). Estructura de las cinco entidades maestras definida; siete bloqueantes B-1 a B-7 identificados. No se modificó ningún archivo |
| 2026-09-18 | **Bloqueantes B-1 a B-7 resueltos documentalmente.** `DT-024` (CSV por entidad), `DT-025` (`manifest.json`), `DT-026` (`data_origin` en maestras), `DT-027` (`valid_from` / `valid_to`), `DT-028` (políticas de generación sintética), `DT-029` (alcance del C2), `DT-030` (sub-semillas). Actualizados `docs/04`, `knowledge/dataset-specification.md` (§§41–44) y `docs/15`. **El Componente 2 sigue sin implementar**; sin código nuevo, 54 pruebas en verde |
| 2026-09-18 | **Auditoría de consistencia post-decisiones.** Cuatro revisiones independientes sobre `DT-024`–`DT-030`: **seis bloqueantes encontrados y corregidos** (semántica del intervalo de vigencia, proveedores huérfanos, `valid_to` degenerado, bucle de suelo ambiguo, sub-semilla sin identificador definido, invariante de reproducibilidad en cuatro versiones incompatibles) más ocho correcciones menores. Quedan **tres cuestiones abiertas que requieren decisión del responsable**. Veredicto: **NO APTO para autorizar C2 todavía**. Sin cambios de código; 54 pruebas en verde |
| 2026-09-19 | **`DT-031` — V1: reglas mínimas funcionales** (`PROPUESTA`). Ocho reglas que hacen calculable `Forecast → Inventory → Supply Engine → Recommendation` sin fijar ninguna política: `raw_need`, posición de inventario, horizonte, demanda sobre el horizonte, stock de seguridad, MOQ/múltiplo, escenarios de demostración y alcance del validador. Cinco ya estaban documentadas. `ASSUMPTION-021/022/023`. Corregida la contradicción de `docs/06` §14. Sin cambios de código; 54 pruebas en verde |
| 2026-09-19 | **Decisiones A–F confirmadas.** Ocho componentes sin rediseño · `R_v1 = 7` · `z_v1 = 1,65` · **`observed_lead_time` sustituye al acordado** (`V1-09`, con fallback) · MOQ y múltiplo independientes · **4 reglas pendientes cerradas** con interpretación técnica (`BR-X05`, `BR-X07`, `BR-X08`, `BR-X09`). `DT-031` pasa de ocho a diez reglas. `ASSUMPTION-024`. Sin cambios de código; 54 pruebas en verde. **El Componente 2 queda listo para implementar** |
| 2026-09-21 | **Reglas V1 CERRADAS.** Confirmados `V1-09` (mínimo 3 observaciones), `V1-09.1` (ventana de 12 por fecha de finalización), `V1-09.2` (techo de 90 días con trazabilidad) y `V1-10` (proveedor preferente activo). Añadidas `V1-11` (sin diferenciación ABC, sin eliminar el campo), `V1-12` (sin sobre-recepción) y `V1-13` (sin inventario negativo). `DT-031` pasa a **`ACEPTADA` como conjunto de reglas de V1** con trece reglas; `docs/15` v1.4. Los trece casos de prueba pedidos **no son ejecutables todavía** (motor = Fase 4; validador = Componente 8) y quedan registrados con su dueño en lugar de escribirse. Sin cambios de código; **54 pruebas en verde**. Detectada y **resuelta** en este mismo cierre una divergencia de **seis** documentos entre la copia de trabajo y el disco (punto 10 de *Problemas conocidos*). **C2 LISTO PARA INICIAR** |
| 2026-09-21 | **Componente 2 implementado y probado.** `Catalog Generator`: cinco entidades maestras + `manifest.json`, en `generator/{rng,policies,writer,catalog,__main__}.py`. `DT-032` (flujo contador sobre SHA-256, cierra el límite conocido de §44) y `DT-033` (versionado derivado). Eliminado `generator/config.py` con autorización. Revisión adversarial independiente: **5 defectos reales corregidos** (desbordamiento del ancho de códigos, bucle infinito latente en `below`, `Z` sin convertir a UTC, red de seguridad incompleta, literal fuera de `DT-028`). Pruebas: **54 → 155, todas en verde**. `black` limpio. C3 **no iniciado** |
| 2026-09-21 | **Identificadores canónicos de componente fijados** (`DT-030`, `docs/15` v1.6). Tabla de los ocho componentes; `catalog` sin cambios, siete nuevos. `COMPONENT_IDS` en `rng.py` y nueve pruebas que los fijan contra la fórmula. Resuelta la cuestión **Quality Report vs Validator**: forma parte del Componente 8, según `DT-023`, `DT-025`, `status.md` y `DT-031` — ninguna decisión aceptada propuso un noveno componente. El Componente 2 no se modificó y su salida es byte a byte idéntica. Pruebas: **155 → 164, todas en verde**. C3 **no iniciado** |
| 2026-09-23 | **Componente 3 implementado y probado.** `Demand Generator`: `demand.csv` con 108 235 filas de **demanda latente**, producto × ubicación × día. `DT-034` (la demanda latente se persiste, separada del consumo observado; entidad `Demand` en `docs/04`; periodo semiabierto; serie densa; cantidades enteras) y `DT-035` (políticas sintéticas de demanda: dos ejes ortogonales, onda triangular en vez de senoidal por reproducibilidad, intermitencia con mecanismo propio). `generator_version` 0.1.0 → 0.2.0. Los ocho comportamientos son **verificables midiendo la serie**, no leyendo una etiqueta. Pruebas: **164 → 235, todas en verde**. `black` limpio. C4 **no iniciado** |
| 2026-09-26 | **Componente 4 implementado y probado, sin conectar a `__main__`.** `Inventory Simulator`: `consumption.csv`, `inventory_movements.csv` e `inventory.csv` más las órdenes causales en memoria para C5. Decisiones **D-C4-1 = O1** (`DT-037` §3 enmendado: `q2` nunca es cero), **D-C4-2 = P1** (precondiciones P-C4-2 y P-C4-3 en `DT-038` §16) y **D-C4-3** (lead time acordado, `M` solo en la apertura, disparo diario). `metrics` de `DT-038` §12 **no implementado**: sus definiciones no existen. `generator_version` sigue en 0.2.0; `output/` intacto. Pruebas: **235 → 323, todas en verde**. C5 y C6 **no iniciados** |
| 2026-09-27 | **D-01 cerrado — elegibilidad de las `CANCELLED` sintéticas (opción A).** `DT-039` §5.2 punto 1: cierre previsto `issued_on + ORDERS_CANCELLED_CLOSE_LAG_DAYS` `< end_date` **y** `<= valid_to` (o nulo); filtrado antes de `K` y de la selección; B2 intacta; sin recorte de `closed_at`; `DT-027` **sin cambios**. `docs/15` v1.12. Pruebas de contrato de la regla: **323 → 335, todas en verde**. C5 **no implementado**; `generator_version` 0.2.0 |
| 2026-09-28 | **Componente 5 implementado y probado, sin conectar a `__main__`.** `Purchase Order Generator`: `purchase_orders.csv`, `purchase_order_items.csv` y `purchase_order_receipts.csv` materializados desde el `SimulationResult` de C4 sin recalcular nada; `order_number` para todas las órdenes; órdenes `CANCELLED` sintéticas según `DT-039` §5.2 con la elegibilidad de D-01 (filtrado antes de `K`, B2 y selección; `closed_at` sin recorte). `DT-039` §13 registra dónde vive cada regla; ninguna cambia. `generator_version` 0.2.0; `output/` intacto. Pruebas: **335 → 390, todas en verde**. C6 **no iniciado** |
| 2026-09-28 | **Componente 6 implementado y probado, sin conectar a `__main__`.** `Supplier Behaviour Generator`: un `SupplierProfile` por proveedor, en memoria, con los valores y mezclas de `DT-037` §2 y las dos secuencias de §4; sin archivos de datos, solo su entrada en el manifiesto (A1); tipo importado de C4 (A2). `DT-037` §6 registra la implementación; `DT-040` §3 corregido (O1); comentarios obsoletos de C4 corregidos (O2). `generator_version` 0.2.0; `output/` intacto. Pruebas: **390 → 430, todas en verde**. Siguiente: W1, pendiente de autorización |
| 2026-09-28 | **Pendientes de C5 cerrados.** La auditoría independiente de `test_orders.py` recalcula ahora la **selección exacta** de las plantillas `CANCELLED` (universo, `K` y permutación `cancelled-selection`) sin llamar a C5, y `ExactSelectionTests` la compara orden a orden; `DT-039` §13 ya no dice que el Componente 6 no existe. Sin cambios en C4, C5 ni C6. Pruebas: **430 → 434, todas en verde**. **W1 no iniciado**: se detiene antes de implementar por dos decisiones pendientes (versión 0.3.0 del artefacto y mecanismo de promoción de `DT-040` §5 frente a «sin rollback») |
| 2026-09-29 | **W1 implementado; dataset completo publicado.** `pipeline.run` (comprobación previa, workspace `tmp/<uuid>/`, C2 → C3 → C6 → C4 → C5, verificación final, promoción de `DT-040` §5) y `__main__.py` conectado a él. `GENERATOR_VERSION` **0.2.0 → 0.3.0** (`DT-036` §8). Detalles pendientes de `DT-040` resueltos por el responsable (`.anterior` y workspace fallido se eliminan). Publicado `ds-269a698250db`. Pruebas: **434 → 463, todas en verde** |
| 2026-09-29 | **Componente 7 implementado y probado, sin integrar en W1.** `DT-041` (contrato de `scenario_assignment`: 16 ejes × seis campos; unidad `supplier` para los ejes de proveedor; criterios `SYNTHETIC_COVERAGE_CRITERION` para `LOW_INVENTORY`, `OVERSTOCK` y las situaciones 12 y 18, que no son reglas de negocio). `scenarios.py`; `writer.py` gana `SCENARIOS_VERSION` y `add_manifest_field`. Notas en `DT-030` y `DT-031` (`V1-07`, `V1-08`); `docs/15` v1.16. C2–C6, `pipeline.py`, `generator_version` 0.3.0 y `output/` sin cambios. 19 de 19 mutaciones detectadas. Pruebas: **463 → 509, todas en verde**. Siguiente: C8 |
| 2026-09-29 | **Generador 0.4.0 terminado.** `DT-042` y `validator.py` (51 comprobaciones sobre el workspace, `quality_report` con los veinte ítems de §35, `anomalies: []`); C7 y C8 integrados en W1; `verify` exige `scenario_assignment` y un informe sin fallos; `GENERATOR_VERSION` **0.3.0 → 0.4.0** (un solo incremento). Publicado `ds-6c8ad65b4999`: 51/51, 0 fallos, 16/16 escenarios, nivel C 4/4, reproducible salvo `generated_at`. Documentación: `DT-025`, `DT-033`, `DT-038` §12 (`metrics` cerrado), `DT-040`, `DT-041`, especificación §34/§35/§39/§40/§41.3/§42.3, `docs/15` v1.17, `CLAUDE.md`, informe en `docs/reports/`. Pruebas: **509 → 582, todas en verde** |
