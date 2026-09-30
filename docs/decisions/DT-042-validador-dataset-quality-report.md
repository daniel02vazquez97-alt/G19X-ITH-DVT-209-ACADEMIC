# DT-042 — Dataset Validator e informe de calidad: contrato del Componente 8

- **Fecha:** 2026-09-29
- **Estado:** `ACEPTADA` (decisiones C7/C8-01 a 14, cerradas por el responsable el 2026-09-29)
- **Fase del roadmap:** Fase 1 — Datos (Componente 8: *Dataset Validator + informe de calidad*)
- **Afecta a:** `data/synthetic/generator/validator.py`, `data/synthetic/generator/pipeline.py`
  (integración de C7 y C8, `verify`), `data/synthetic/generator/writer.py`
  (`VALIDATOR_VERSION`, `GENERATOR_VERSION`), `manifest.json` (campo `quality_report`)
- **Entrada resumida:** `docs/15-decisiones-tecnicas.md` → `DT-042`
- **Relacionada con:** `DT-023`, `DT-024`, `DT-025`, `DT-026`, `DT-027`, `DT-028`, `DT-030`, `DT-031`
  (`V1-08`, `V1-12`, `V1-13`), `DT-033`, `DT-034`, `DT-036`, `DT-037`, `DT-038`, `DT-039`, `DT-040`,
  `DT-041`; especificación §19, §20–§23, §34, §35

---

> # ⚠ ADVERTENCIA DE LECTURA
>
> **El Componente 8 valida un dataset sintético.** Las comprobaciones marcadas con criterio
> `SYNTHETIC_COVERAGE_CRITERION` (`DT-041`) existen **solo** para demostrar que el dataset contiene
> las situaciones que exige §25; **no son reglas de negocio**, no pueden usarse en el motor, la API,
> la UI, ML ni RAG, y **no cierran `BR-X03`, `DT-P11`, `BR-P10` ni `DT-011`**. El informe de
> calidad describe datos sintéticos y, como exige §35, **no presenta ningún resultado como métrica
> real del negocio**.

---

## Decisión

### 1. Propósito

El Componente 8 valida el **dataset materializado en el workspace** —los doce CSV y
`manifest.json` que C2–C7 escribieron— y, solo si todo es válido, escribe
`manifest.quality_report`.

| C8 **sí** | C8 **no** |
|---|---|
| Lee los archivos del workspace y comprueba su integridad estructural y semántica | Usa como fuente de verdad objetos internos de C2–C7 |
| Comprueba la coherencia **entre** archivos: la frontera estado interno → serialización → archivos | Genera demanda, inventario, órdenes ni recepciones; asigna perfiles |
| Comprueba la cobertura de `scenarios.required` y las cuatro situaciones de nivel C | Vuelve a seleccionar ni a sortear las canceladas; sortea nada |
| Escribe `quality_report` cuando **todas** las comprobaciones pasan | Modifica, corrige ni reescribe ningún registro ni ningún CSV |
| Falla con `GeneratorError` y **todos** los fallos cuando alguna no pasa | Aplica reglas de negocio futuras; clasifica sobreinventario según `BR-X03` |
| — | Calcula recomendaciones, pronósticos, ROP, stock de seguridad ni optimiza nada |

C8 **puede** usar funciones **públicas y puras** del generador para reproducir un criterio
contractual —`orders.cancelled_target`, `orders.is_eligible_for_cancel`,
`orders.order_number_width`, `orders.format_order_number`, `writer.dataset_version`,
`supplier_behaviour.build_supplier_profiles` y las funciones públicas de `scenarios` (`DT-041`)—,
pero **los hechos que valida salen siempre de los archivos del workspace**.

### 2. Identificador, versión y sub-semilla

| Campo | Valor |
|---|---|
| Identificador canónico | `validator` (`DT-030`) |
| `components[].version` | `VALIDATOR_VERSION = "0.1.0"` (`writer.py`) |
| `components[].sub_seed` | `sub_seed(seed, "validator")`, registrada por uniformidad; **no se usa** (decisión C7/C8-13) |

C8 no instancia ningún flujo pseudoaleatorio propio. Las únicas extracciones que ocurren durante C8
son las de **C3** y **C6** al reconstruir sus decisiones —la demanda dentro de
`scenarios.build_assignment` (`DT-041` §6.1) y los perfiles con
`supplier_behaviour.build_supplier_profiles`—, con las sub-semillas de C3 y C6: repiten decisiones
ya tomadas, no sortean nada nuevo.

### 3. Entradas y salida

```text
validator.validate(config, input_dir)  -> quality_report   (no escribe nada)
validator.generate(config, output_dir) -> manifest          (añade quality_report y su componente)
```

- **Entradas:** `config`, y exactamente los archivos del workspace: `manifest.json` y los doce CSV de
  `pipeline.FILE_COLUMNS`. C8 no lee ningún otro archivo.
- **Salida:** el manifiesto, extendido con `components[validator]` (sin archivos) y con el campo
  `quality_report`, añadido con `writer.add_manifest_field`, que **nunca sobrescribe**. C8 **no
  crea ningún CSV** ni ningún `quality_report.json` (decisión C7/C8-08).

### 4. Catálogo de comprobaciones

51 comprobaciones en 16 familias. Cada una tiene un identificador estable, que aparece en el informe
y en los mensajes de error.

| Familia | Identificadores | Qué comprueba | Fuente |
|---|---|---|---|
| **MAN** manifiesto | MAN-01 … MAN-04 | Campos presentes (los nueve obligatorios más `scenario_assignment`, sin `quality_report` previo); identidad (`seed`, `time_range`, `config`, `data_origin`, `generator_version` y `dataset_version` derivado); los seis componentes previos con versión y sub-semilla, ordenados; los doce archivos del contrato, ordenados, con `sha256` y filas exactos, y el directorio sin nada más | `DT-025`, `DT-030`, `DT-033`, `DT-040` §4, §34 *Origen* |
| **FMT** formato | FMT-01 … FMT-04 | UTF-8 sin BOM, fin de línea LF, salto final; cabecera y orden de columnas; número de campos por fila; tipo, nulabilidad y columnas siempre vacías de cada columna; ningún nulo escrito como `NULL`, `null`, `None` o `NaN` | `DT-024`, `DT-034`, `DT-038`, `DT-039`, §34 *Formato* |
| **ORG** origen | ORG-01 | `data_origin = SYNTHETIC` en todas las filas de los doce archivos | `DT-026`, §34 *Origen* |
| **IDN** identidad | IDN-01 … IDN-03 | Identificadores únicos según la regla de cada contrato (secuenciales en el orden del archivo; líneas con el `id` de su orden; recepciones numeradas por `(received_at, purchase_order_item_id)`); claves de negocio únicas y orden de filas; como máximo una relación preferente activa por producto | `DT-024`, `DT-034`, `DT-038` §§4-8, `DT-039` §§2-4, §7 |
| **REF** referencias | REF-01 … REF-07 | Todas las claves foráneas; orden ↔ línea 1 : 1 y como máximo dos recepciones por línea; la orden usa la relación preferente activa de su producto; `RECEIPT` ↔ recepción y `ISSUE` ↔ consumo, uno a uno, con par, día y cantidad; saldo de apertura; una fila de inventario por par | `DT-038` §§5.2, 6, 8; `DT-039` §8 |
| **COM** comerciales | COM-01 … COM-04 | `moq ≥ 0`, `order_multiple ≥ 1`, lead time ≥ 1; `quantity_ordered > 0`, `≥ moq` y múltiplo de `order_multiple`; `unit_cost` de la relación; `expected_at = issued_at + agreed_lead_time_days` | `DT-028` §1, `DT-036` §4, `DT-037` §3, `DT-038` §§7, 12 |
| **RCP** recepciones | RCP-01 … RCP-03 | Recepción > 0 y en `[issued_at, end_date)`; Σ recepciones = `quantity_received` ≤ `quantity_ordered`; estado y `closed_at` de cada orden causal coherentes con sus recepciones | `V1-12`, `DT-038` §§9-10, `DT-039` §§3-4, 8 |
| **CAN** canceladas | CAN-01 … CAN-04 | `closed_at = issued_at + 1 día`, recibido 0, sin recepciones; gemela de una plantilla causal **elegible** y distinta; número = `min(cancelled_target(N), elegibles)` y ≥ 1; las causales numeradas desde 1 por `(issued, supplier, product, location)` y las canceladas en el tramo final con la misma clave | `DT-039` §§5.1-5.2, 7 |
| **ONB** `order_number` | ONB-01 | `"PO-" + zfill(id, w)`, `w = max(6, dígitos del id más alto)`, único y de ancho uniforme. **No** se exige orden cronológico: las canceladas ocupan el tramo final | `DT-039` §§5.2, 6 |
| **INV** inventario | INV-01 … INV-04 | Tipo, signo, `reference_type`, `reference_id`, `reason_code`, hora por tipo, `recorded_at = occurred_at` y día en el periodo de cada movimiento; saldo nunca negativo; snapshot = Σ movimientos, `quantity_reserved = 0`, `last_movement_at`; `quantity_in_transit` = pendiente de las órdenes `ISSUED` y `PARTIALLY_RECEIVED` | `DT-036` §9, `DT-038` §§5-6, `V1-13` |
| **CON** consumo | CON-01 … CON-03 | Misma rejilla que `demand.csv`; `consumo = min(latente, existencia antes del consumo)`, sin backlog; `is_stockout_affected = (latente > consumo)` | `DT-034`, `DT-038` §4 |
| **TMP** temporal | TMP-01 … TMP-05 | `valid_from` presente y `valid_to` nulo o ≥; demanda densa solo en días vigentes; órdenes emitidas en periodo y vigencia, `issued ≤ expected`, `closed ≥ issued`; apertura y consumo dentro de la vigencia, y `RECEIPT` después de la vigencia **solo** de órdenes emitidas en vigencia (excepción de `DT-027`, comprobada, no eliminada); toda orden `RECEIVED` con recepción y lead time observado ≥ 0 | `DT-027`, `DT-038` §9, §20, §34 *Temporal* |
| **MST** maestros | MST-01 | `unit_of_measure` y `locations.type` en su vocabulario cerrado | `DT-028` §§5-6, §21 (decisión C7/C8-14) |
| **SCN** escenarios | SCN-01, SCN-02 | Estructura de `scenario_assignment` (16 claves en orden canónico, seis campos, tipos, identificadores ascendentes y existentes); coherencia con los datos: igual al objeto que `scenarios.build_assignment` obtiene del workspace con los perfiles de `supplier_behaviour.build_supplier_profiles` | `DT-041` |
| **COV** cobertura | COV-01 | Cada escenario de `scenarios.required` tiene productos; en los ejes de proveedor, además, proveedores | `V1-08` *Cobertura*, `DT-041` §10 (decisión C7/C8-07) |
| **LVC** nivel C | LVC-08, LVC-12, LVC-18, LVC-20 | Cada situación de nivel C tiene al menos un producto según `scenarios.emergent_properties` | `DT-023`, `DT-041` §8 |

Las comprobaciones de nivel C y de cobertura son **obligatorias**: §25 marca las 26 situaciones
como obligatorias, y `COV-01` usa `scenarios.required` porque así lo fija `V1-08`.

### 5. `quality_report`

Un objeto JSON dentro del manifiesto, con los **20 ítems de §35**, en este orden:

| # §35 | Clave | Contenido |
|--:|---|---|
| — | `result` | `"PASS"`. Un informe solo existe si todas las comprobaciones pasaron |
| 1 | `dataset_version` | Copia del manifiesto |
| 2 | `generator_version` | Copia del manifiesto |
| 3 | `seed` | Copia del manifiesto |
| 4 | `time_range` | Copia del manifiesto |
| 5 | `records_by_entity` | `{archivo: filas}`, de `files[]` |
| 6–9 | `counts` | `products`, `suppliers`, `categories`, `locations` |
| 10 | `scenario_distribution` | Por cada uno de los 16 escenarios: `unit`, `criterion`, `required`, `covered`, `suppliers` (número o `null`) y `products` (número) |
| 11 | `products_by_demand_pattern` | Productos por cada una de las seis formas |
| 12 | `stockout` | `pair_days` (filas con `is_stockout_affected = true`) y `products` |
| 13 | `orders` | `total` y `by_status` |
| 14 | `receipts` | Número de recepciones |
| 15 | `lead_time_distribution` | `agreed` (relaciones de `product_suppliers.csv`) y `observed` (órdenes `RECEIVED`: última recepción − emisión, la definición de `V1-09`), cada una como lista `[{"days", "count"}]` ascendente |
| 16–18 | `validations` | `executed`, `passed`, `failed`, `checks` (lista de `{id, family, source, status}` en el orden del catálogo) y `level_c` (las cuatro situaciones con `criterion`, `source` y número de productos) |
| 19 | `anomalies` | **`[]`** — ver §6 |
| 20 | `known_limitations` | Lista de `{id, text, source}`, fija, tomada de los documentos |

**Resultado global contractual:** `validations.failed == 0` y `validations.executed ==
validations.passed`. `verify` (W1) lo exige antes de promocionar (`DT-040` §4).

**Determinismo y tipos.** El informe es función pura del workspace y la configuración: mismo
workspace, mismos bytes. Usa **solo** cadenas, enteros, booleanos, `null`, listas y objetos, y
**ningún número de coma flotante** (`DT-032`: el generador no contiene flotantes, y la representación
textual de un flotante rompería la identidad byte a byte de §44). No contiene `generated_at`, marcas
de tiempo de ejecución, duraciones, rutas, identificadores de ejecución ni valores aleatorios.

### 6. Anomalías

`"anomalies": []`, siempre, en esta versión (decisión C7/C8-09). §35 pide «anomalías detectadas»,
pero **ningún documento define un criterio de anomalía** para el generador, y convertir estados
válidos del dataset en anomalías sería inventarlo. El informe declara la limitación correspondiente:

> *No existe actualmente un criterio contractual de anomalía para este generador; una lista vacía no
> implica que el dataset haya sido revisado bajo una taxonomía de anomalías inexistente.*

### 7. Fallos

- C8 ejecuta **todas** las comprobaciones y **acumula todos los fallos** antes de lanzar
  `GeneratorError`; nunca se detiene en el primero.
- Cada mensaje empieza por el identificador de la comprobación y nombra el archivo, la fila o clave
  cuando aplica, la causa, el valor observado y el esperado cuando puede determinarse. Para que un
  dataset muy dañado no produzca un mensaje ilegible, cada comprobación detalla sus primeros 20
  hallazgos y resume el resto con su número total.
- Una comprobación que no puede evaluarse —un archivo ausente, una columna que falta, un valor que no
  se puede interpretar— **falla**, con el motivo; no se omite.
- Con cualquier fallo, C8 **no escribe nada** y la ejecución no se promociona. La publicación sigue
  `DT-040`.
- C8 **no repara**: nunca lee un CSV, lo corrige y lo vuelve a escribir.

### 8. Integración en W1

```text
C2 → C3 → C6 → C4 → C5 → C7 → C8 → verify → promote
```

C7 recibe los perfiles de C6 en memoria (`DT-041` §3); C8 recibe solo la configuración y el
workspace. `pipeline.COMPONENT_VERSIONS` pasa a **siete** componentes (C2–C8; W1 no es un
componente). `verify` conserva todas sus comprobaciones y exige además que existan
`scenario_assignment` y `quality_report`, con `validations.failed == 0`, `executed == passed` y
`result = "PASS"`.

### 9. `GENERATOR_VERSION`

La integración de C7 y C8 cambia el artefacto publicado —el manifiesto gana dos campos y dos
componentes— y, por la regla de `DT-033`, **`GENERATOR_VERSION` sube una sola vez, de `0.3.0` a
`0.4.0`** (decisión C7/C8-11). Los doce CSV no cambian: su contenido es byte a byte el del dataset
0.3.0 de la misma configuración, porque ni C7 ni C8 escriben datos.

### 10. Implementación *(2026-09-29)*

`data/synthetic/generator/validator.py` (`validate`, `generate`, `CHECKS`, `KNOWN_LIMITATIONS`) y
`data/synthetic/tests/test_validator.py` (67 pruebas: catálogo, informe, determinismo y una inyección
de fallos por familia). `writer.py` gana `VALIDATOR_VERSION = "0.1.0"` y `GENERATOR_VERSION` pasa a
`0.4.0`; `pipeline.py` integra C7 y C8 y amplía `verify`. En una copia desechable se inyectaron 16
defectos en el propio validador —cada uno desactiva una comprobación o el acumulado de hallazgos— y
las pruebas detectaron los 16.

**Dataset publicado con esta versión:** `ds-6c8ad65b4999`, 51/51 comprobaciones, 0 fallos. Con escalas
muy pequeñas (12 productos, 59 días) la cobertura depende de la semilla: 6 de las 14 semillas probadas
dejan un escenario requerido o una situación de nivel C sin caso, y C8 rechaza la ejecución, como fija
la decisión C7/C8-07.

## Contexto

`DT-023` encargó al Componente 8 las cuatro situaciones de nivel C y las validaciones de §34;
`DT-030` le asignó el informe de calidad; `DT-025` aplazó a su autorización si el informe vive en el
manifiesto; `DT-031` `V1-08` fijó sus invariantes mínimas; `DT-038` y `DT-039` fueron escritos para
que tuviera «contra qué validar». La auditoría C7/C8 del 2026-09-29 cerró las decisiones restantes.

## Alternativas consideradas

| | Alternativa | Por qué no |
|---|---|---|
| (a) | `quality_report.json` como archivo aparte | Exige una entidad, un número de filas y cambios en `FILE_COLUMNS` y `check_output`; `DT-025` ya lo prevé como campo (decisión C7/C8-08) |
| (b) | Validar los objetos en memoria de C4 y C5 | No comprueba la serialización ni la coherencia entre archivos, que es donde un dataset puede romperse con un generador correcto |
| (c) | Publicar con avisos cuando algo falla | Contradice `V1-08` («el validador lo rechaza») y la regla de no publicar datasets incompletos (`DT-040`) |
| (d) | Catálogo de anomalías propio | Inventaría una taxonomía que ningún documento define (decisión C7/C8-09) |

## Consecuencias

**Positivas**

1. Ningún dataset que incumpla un contrato llega a `output/`.
2. Cada fallo se identifica por comprobación, archivo y clave.
3. El informe de §35 viaja con el dataset y es reproducible byte a byte.

**Costos aceptados**

1. C8 repite comprobaciones que C4, C5 y `verify` ya hacen en memoria o en parte: es deliberado, la
   frontera que valida es otra.
2. Un dataset publicado siempre muestra `failed = 0`: los fallos se ven en el error, no en el
   informe, porque un informe con fallos nunca se publica.
3. El workspace de una ejecución fallida se elimina (`DT-040` §9): el diagnóstico es el mensaje de
   `GeneratorError`.

## Lo que esta decisión NO hace

- **No** modifica C2–C7, ni sus políticas, ni `DT-027`, ni las cancelaciones.
- **No** añade métricas a C4: `DT-038` §12 queda cerrado sin `metrics`.
- **No** define anomalías, ni reglas de negocio, ni umbrales de riesgo.
- **No** cierra `BR-X03`, `DT-P11`, `BR-P10`, `DT-011` ni `DT-P12`.
