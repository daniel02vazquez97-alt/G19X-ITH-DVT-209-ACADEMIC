# DT-041 — Scenario Assignment: contrato del Componente 7

- **Fecha:** 2026-09-29
- **Estado:** `ACEPTADA` (decisiones C7/C8-01 a 14, cerradas por el responsable el 2026-09-29)
- **Fase del roadmap:** Fase 1 — Datos (Componente 7: *Scenario Assignment*)
- **Afecta a:** `data/synthetic/generator/scenarios.py`, `data/synthetic/generator/writer.py`
  (`SCENARIOS_VERSION`, `add_manifest_field`), `manifest.json` (campo `scenario_assignment`), el
  diseño del Componente 8
- **Entrada resumida:** `docs/15-decisiones-tecnicas.md` → `DT-041`
- **Relacionada con:** `DT-023` (tres niveles), `DT-025` (campo `scenario_assignment` del
  manifiesto), `DT-028` §1.6.3, `DT-030` (identificador `scenarios`), `DT-031` `V1-07` y `V1-08`,
  `DT-035`, `DT-036`, `DT-037`, `DT-038`, `DT-039`

---

> # ⚠ ADVERTENCIA DE LECTURA — `SYNTHETIC_COVERAGE_CRITERION`
>
> **Los criterios marcados `SYNTHETIC_COVERAGE_CRITERION` en este documento existen únicamente para
> demostrar que el dataset sintético contiene las situaciones que exige §25 de la especificación.**
> Detectan casos que el generador produjo.
>
> **No son reglas de negocio.** No definen qué es, para el negocio, inventario bajo,
> sobreinventario, tránsito suficiente o efectivo, conflicto MOQ/sobreinventario ni producto
> descontinuado. **No cierran, no sustituyen y no anticipan `BR-X03`, `DT-P11`, `BR-P10` ni
> `DT-011`**, que siguen pendientes.
>
> **Ningún componente del sistema principal —motor de abastecimiento, API, UI, ML, RAG— puede
> usarlos como regla.** Un criterio sintético que coincida numéricamente con una regla futura es una
> coincidencia, no una adopción.
>
> El estatuto es el mismo que el de `s` y `Q` en `DT-036` §7: `s` no es un punto de reorden, y
> `LOW_INVENTORY` no es la definición empresarial de «inventario bajo».

---

## Decisión

### 1. Propósito y responsabilidad

El Componente 7 **registra** en el manifiesto qué productos y qué proveedores representan cada uno
de los 16 ejes de nivel A de `DT-023`, y **mide** los ejes que no se asignan sino que emergen de la
simulación.

| C7 **sí** | C7 **no** |
|---|---|
| Registra la forma y la rotación que **C3 ya decidió** (`DT-035`) | Decide cómo C3 genera la demanda |
| Registra el perfil que **C6 ya asignó** a cada proveedor (`DT-037`) y comprueba si se manifiesta | Decide qué perfil tiene un proveedor |
| Mide, sobre los archivos ya escritos, los ejes que emergen de C4 y C2 | Genera, corrige ni modifica ningún dato |
| Escribe `manifest.scenario_assignment` y su entrada en `manifest.components` | Escribe ningún CSV, ni `scenario_assignment.csv` ni `.json` |
| — | Sortea: no crea ningún flujo pseudoaleatorio |
| — | Etiqueta ninguna situación de nivel C (`DT-023`) |

C7 **no asigna**: la palabra «asignación» del nombre del componente viene de la tabla de `DT-030` y
se conserva por estabilidad del identificador. Lo que C7 hace es **registrar** decisiones ajenas y
**medir** situaciones emergentes (corrección de redacción de `DT-031` `V1-07`).

### 2. Identificador, versión y sub-semilla

| Campo | Valor |
|---|---|
| Identificador canónico | `scenarios` (`DT-030`) |
| `components[].version` | `SCENARIOS_VERSION = "0.1.0"` (`writer.py`) |
| `components[].sub_seed` | `sub_seed(seed, "scenarios")`, registrada por uniformidad (decisión C7/C8-13) |

**C7 no usa su sub-semilla para nada.** Se registra porque todas las entradas de `components`
tienen la misma forma (`DT-025`) y porque el identificador está reservado desde `DT-030`; el
precedente de `DatasetConfig` —sin sub-semilla por no sortear— se refiere a un componente que no
figura en `components`. C7 no instancia `DeterministicRandom` con ella ni con ninguna otra etiqueta
propia. La única extracción pseudoaleatoria que ocurre durante C7 es la **reconstrucción de C3** de
§6.1, que repite los flujos de C3 con la sub-semilla de C3.

### 3. Entradas y salida

```text
scenarios.generate(config, output_dir, profiles) -> manifest
```

| Entrada | Origen |
|---|---|
| `config` | `DatasetConfig` validado |
| `output_dir` | El directorio donde C2–C5 ya escribieron (en W1, el workspace) |
| `profiles` | Los `SupplierProfile` de C6, **en memoria**, igual que los recibe C4 (`DT-037` §3) |
| Archivos | `manifest.json`, `products.csv`, `suppliers.csv`, `product_suppliers.csv`, `demand.csv`, `consumption.csv`, `inventory.csv`, `inventory_movements.csv`, `purchase_orders.csv`, `purchase_order_items.csv`, `purchase_order_receipts.csv` |

**Salida:** el manifiesto, extendido con `components[scenarios]` (sin archivos) y con el campo
`scenario_assignment`. **Ningún otro byte del directorio cambia.**

La construcción está separada de la escritura: `build_assignment(config, input_dir, profiles)`
devuelve el objeto sin escribir nada.

### 4. Forma de `scenario_assignment`

Un objeto JSON con **exactamente 16 claves**, los valores de `Scenario` en su **orden canónico**
(el de declaración del enum, el mismo con el que `DatasetConfig` normaliza `scenarios.required`).
Cada valor tiene **exactamente seis campos**, en este orden:

| Campo | Tipo | Valores |
|---|---|---|
| `unit` | texto | `product` \| `supplier` — la unidad primaria de cobertura |
| `basis` | texto | `ASSIGNED` (lo decidió C3 o C6) \| `STRUCTURAL` (propiedad del catálogo de C2) \| `OBSERVED` (emerge de la simulación) |
| `criterion` | texto | `COMPONENT_DECISION` \| `DOCUMENTED_DEFINITION` \| `SYNTHETIC_COVERAGE_CRITERION` |
| `source` | texto | Componente de origen y documento que respalda el criterio |
| `suppliers` | lista de enteros ascendentes \| `null` | Proveedores con el perfil; `null` cuando la unidad es `product` |
| `products` | lista de enteros ascendentes | Productos que representan el eje (para ejes de proveedor: los que lo **manifiestan**) |

**`null` y `[]` no significan lo mismo.** `null` es «no aplicable» (un eje de demanda no tiene
proveedores); `[]` es «aplicable y vacío» (ningún producto cumple). Esa distinción es la que
permitirá al Componente 8 comprobar la cobertura sin ambigüedad.

La estructura está **orientada a escenario**: no es un índice producto → escenarios ni un recuento.

### 5. Los 16 escenarios

| Escenario | `unit` | `basis` | `criterion` | `source` | Criterio |
|---|---|---|---|---|---|
| `HIGH_ROTATION`, `LOW_ROTATION` | product | ASSIGNED | COMPONENT_DECISION | `demand: DT-035 §1-§2` | Rotación que C3 dio al producto (§6.1) |
| `STABLE_DEMAND` … `ERRATIC_DEMAND` (6) | product | ASSIGNED | COMPONENT_DECISION | `demand: DT-035 §1-§2` | Forma que C3 dio al producto (§6.1) |
| `STOCKOUT` | product | OBSERVED | DOCUMENTED_DEFINITION | `inventory: DT-038 §4` | Al menos un día con `is_stockout_affected = true` |
| `OVERSTOCK` | product | OBSERVED | **SYNTHETIC_COVERAGE_CRITERION** | `scenarios: DT-041 §6.6` | §6.6 |
| `LOW_INVENTORY` | product | OBSERVED | **SYNTHETIC_COVERAGE_CRITERION** | `scenarios: DT-041 §6.5` | §6.5 |
| `RELIABLE_SUPPLIER` | supplier | ASSIGNED | COMPONENT_DECISION | `supplier_behaviour: DT-037 §2; spec §12.1` | §6.2 |
| `DELAYED_SUPPLIER` | supplier | ASSIGNED | COMPONENT_DECISION | `supplier_behaviour: DT-037 §2; spec §12.2` | §6.2 |
| `PARTIAL_DELIVERY` | supplier | ASSIGNED | COMPONENT_DECISION | `supplier_behaviour: DT-037 §2; spec §12.3` | §6.2 |
| `MULTIPLE_LEAD_TIMES` | product | STRUCTURAL | DOCUMENTED_DEFINITION | `catalog: DT-028 §1.6.3` | §6.3 |
| `IN_TRANSIT` | product | OBSERVED | DOCUMENTED_DEFINITION | `inventory: DT-038 §6.1` | `inventory.quantity_in_transit > 0` al corte |

Con una sola ubicación (`DT-029`), cada criterio que se evalúa por par producto–ubicación se
registra por producto: un producto representa el eje si **alguno** de sus pares lo cumple.

### 6. Criterios

#### 6.1 Formas y rotación — reconstrucción de C3 verificada por SHA-256

Los perfiles de C3 no se escriben en ningún archivo y `demand.generate` no los devuelve. C7 **no
modifica C3**: los reconstruye con la función pública y pura `demand.build_demand(config,
output_dir)`, que lee el catálogo ya publicado y repite exactamente los flujos de C3.

Antes de usarlos, C7 comprueba que la reconstrucción es **la misma demanda publicada**: renderiza
las filas reconstruidas con `writer.render_csv` y exige que su `sha256` coincida **a la vez** con el
de `demand.csv` en disco y con el de `demand.csv` en `manifest.files`. Si no coincide, `GeneratorError`
y **no se escribe nada**. C7 no regenera la demanda para «arreglar» el archivo.

La forma y la rotación registradas son, así, **la misma decisión que tomó C3**, no una inferencia
estadística sobre el CSV.

#### 6.2 Perfiles de C6 — unidad primaria `supplier`, manifestación en `products`

Correspondencia, por el texto literal de §12 de la especificación:

| Escenario | Perfil de C6 | Manifestación exigida en los datos (órdenes causales de esos proveedores) |
|---|---|---|
| `RELIABLE_SUPPLIER` | `PUNCTUAL` **y** `COMPLETE` (§12.1: «entregas completas») | Una orden `RECEIVED`: sin recepción no hay lead time observado (§12.1, §13) |
| `DELAYED_SUPPLIER` | `LATE` | Una orden cuya primera recepción es posterior a `expected_at` (§12.2) |
| `PARTIAL_DELIVERY` | `SPLIT` | Una recepción con `quantity_received < quantity_ordered` de su línea (§12.3) |

`IRREGULAR` **no recibe etiqueta**: ningún documento lo asocia a un escenario.

- `suppliers` = los proveedores con el perfil. Es la **cobertura primaria**, que C6 garantiza por
  construcción del reparto (`DT-037` §2).
- `products` = los productos de las órdenes causales de esos proveedores que **manifiestan** el
  comportamiento. Es la medición que pide `DT-037` O-3. Un proveedor con el perfil y sin evidencia
  observable **no** aporta productos.

C7 **no convierte** un proveedor en productos por la mera existencia de una relación: un producto
entra en la lista solo si una orden concreta muestra el comportamiento.

*Órdenes causales* son las que no están `CANCELLED`: las canceladas son copias sintéticas de C5
(`DT-039` §5) y no tienen recepciones.

#### 6.3 `MULTIPLE_LEAD_TIMES`

Definición existente, `DT-028` §1.6.3: un producto con **al menos dos relaciones en
`product_suppliers.csv` con `agreed_lead_time_days` distintos**. Se cuentan todas las relaciones del
producto, activas o no, como en `DT-028`.

#### 6.4 `STOCKOUT` e `IN_TRANSIT`

Datos almacenados, sin recalcular nada: `consumption.is_stockout_affected` (`DT-038` §4) e
`inventory.quantity_in_transit` al corte (`DT-038` §6.1, el tránsito **total**; no el efectivo,
que sigue siendo `DT-P11`).

#### 6.5 `LOW_INVENTORY` — `SYNTHETIC_COVERAGE_CRITERION`

> Un producto representa `LOW_INVENTORY` si existe **un día en que se emitió una orden causal suya y
> su existencia al cierre de ese día era mayor que cero**.

La existencia al cierre de un día es la suma de los movimientos de `inventory_movements.csv` del par
hasta ese día, inclusive (`DT-038` §3: todos los movimientos de un día preceden al disparo). Es
exactamente el disparo de `DT-036` §3 con existencias positivas: con `on_hand > 0`, el disparo exige
`s ≥ 1`, luego `d̄ > 0`, y la guarda de `V1-06` no bloquea la orden. Distingue el estado previo al
desabasto del desabasto consumado (`DT-023` §5). **No** es un punto de reorden.

#### 6.6 `OVERSTOCK` — `SYNTHETIC_COVERAGE_CRITERION`

> Un producto con relación preferente y activa representa `OVERSTOCK` si existe un día `t` de su
> vigencia con
>
> ```text
> d̄_recent(t) > 0   y   on_hand_cierre(t) > ⌈ d̄_recent(t) × (L + C) ⌉
> ```

- `d̄_recent(t)` es la de `DT-036` §5: suma de la demanda latente de la ventana de `W = 28` días que
  empieza en `a(t) = max(primer_día, t − W)`, dividida entre `W`, como racional exacto.
- `L` es el `agreed_lead_time_days` de la relación preferente y activa (la que usa C4, `DT-036` §3).
- `C = 21` (`DT-036` §4).

`⌈d̄·(L + C)⌉` es la cantidad que la propia política sintética de C4 considera necesaria —umbral
más pedido— **sin** MOQ ni múltiplo, de modo que el criterio capta el exceso causado por el MOQ, la
apertura holgada y la demanda decreciente (§10.4). **No introduce ningún número nuevo** y **no** es
un umbral de cobertura del negocio: `BR-X03` sigue pendiente. Un producto sin relación preferente y
activa no tiene `L` y no se evalúa. En el umbral exacto **no** hay sobreinventario.

### 7. Cláusula: criterio sintético ≠ regla de negocio

Rige la advertencia de lectura de la cabecera. En particular:

| Criterio | Regla de negocio que **no** cierra |
|---|---|
| `LOW_INVENTORY` (§6.5) | Punto de reorden y niveles de riesgo (`BR-X01`, `BR-P06`, `BR-X03`) |
| `OVERSTOCK` (§6.6) | Umbral de sobreinventario (`BR-X03`) |
| Propiedad 12 (§8) | Criterio de corte del tránsito efectivo (`DT-P11`, `V1-02`) |
| Propiedad 18 (§8) | Umbral de sobreinventario y conflicto MOQ (`BR-X03`, `BR-P05`) |
| Propiedad 20 (§8) | Tratamiento de descontinuados (`BR-P10`) |
| Propiedad 8 (§8) | Tratamiento de la demanda censurada (`DT-011`) |

`DT-031` `V1-08` queda precisado en el mismo sentido: el validador no clasifica sobreinventario
según `BR-X03`; solo aplica el criterio sintético de §6.6.

### 8. Propiedades de nivel C — criterios de detección, sin etiqueta

Las cuatro situaciones de nivel C (`DT-023`) **no se escriben en `scenario_assignment`**: etiquetarlas
obligaría a fijar las reglas pendientes que `DT-023` protege. Sus criterios de detección se definen
aquí porque comparten el cálculo de §6.5 y §6.6, y viven en `scenarios.emergent_properties`, una
función pura que **C7 no publica**: la consumirá el Componente 8 para el informe de calidad.

| # §25 | Situación | Criterio | Tipo |
|---|---|---|---|
| 8 | Demanda censurada | Un día con `is_stockout_affected = true` **y** demanda latente > consumo (`DT-038` §4) | Definición existente |
| 12 | Tránsito total suficiente / existencias insuficientes | Una orden causal cuya `quantity_ordered` supera la demanda latente acumulada en el intervalo abierto (emisión, primera recepción) —hasta el fin del periodo si no tiene recepciones—, con al menos un día `is_stockout_affected` en ese intervalo | **SYNTHETIC_COVERAGE_CRITERION** |
| 18 | Conflicto MOQ / sobreinventario | Una orden causal con `quantity_ordered > Q_sint`, `Q_sint = ⌈d̄_recent(emisión) × C⌉`, y el producto cumple §6.6 en algún día igual o posterior a su primera recepción | **SYNTHETIC_COVERAGE_CRITERION** |
| 20 | Producto inactivo con histórico | `is_active = false` con consumo > 0, al menos un movimiento, una orden causal y una recepción (§18 de la especificación) | Definición existente |

Notas:

- **12** es el «fallo silencioso» de `DT-012` observado a posteriori. **No** calcula el tránsito
  efectivo del motor (`V1-02`) ni redefine `DT-P11`.
- **18** llama `Q_sint` a la cantidad sintética previa a MOQ y múltiplo, **deliberadamente distinta**
  de `raw_need`, que es un nombre del motor (`V1-01`).

### 9. Determinismo

Misma configuración, mismos archivos y mismos perfiles → mismo `scenario_assignment` y mismos bytes
de `manifest.json`, salvo `generated_at`, que C7 no toca. Todas las listas se ordenan por su
identificador; el orden de las claves es el del enum; C7 no depende del orden del sistema de
archivos, ni de UUID, ni de marcas de tiempo, ni de `hash()`, ni de estado global.

### 10. Escenario vacío y `scenarios.required`

- C7 registra **los 16 escenarios siempre**, estén o no en `scenarios.required`. No lee esa lista.
- Un escenario sin productos se registra con `products: []` (y, si aplica, `suppliers: []`). **C7 no
  falla por eso.**
- Decidir si un vacío incumple `scenarios.required` es del **Componente 8** (decisión C7/C8-07,
  respaldada por `V1-08` «Cobertura»). Para un eje de proveedor, «vacío» significará sin proveedor
  **o** sin manifestación.

### 11. Errores

C7 falla con `GeneratorError`, sin escribir nada, si:

1. falta `manifest.json`, o ya contiene `scenario_assignment` o una entrada `scenarios` en
   `components` (no se sobrescribe nunca);
2. falta un archivo de entrada o su cabecera no es la de su contrato;
3. la demanda reconstruida no coincide con `demand.csv` (§6.1);
4. los perfiles no se corresponden con `suppliers.csv`: perfil duplicado, perfil de un proveedor
   inexistente, u orden causal de un proveedor sin perfil;
5. los archivos no permiten evaluar un criterio: un par con menos de `W` días de demanda, un consumo
   que no cubre la rejilla de la demanda, un par sin fila de `inventory.csv`, una orden sin línea
   única o emitida fuera de la serie de su producto, un producto con más de una relación preferente
   y activa, o un valor mal formado.

Validar la integridad del dataset **no** es de C7: estas comprobaciones solo garantizan que C7 puede
calcular lo que registra.

### 12. Integración

El orden aprobado es `C2 → C3 → C6 → C4 → C5 → C7 → C8 → verify → promote` (decisión C7/C8-01).
**Con este documento C7 no se integra todavía en W1**: `pipeline.generate_into` no lo ejecuta,
`GENERATOR_VERSION` sigue en `0.3.0` y el dataset publicado no cambia. La integración, el ajuste de
`verify` y la subida única a `0.4.0` se harán con el Componente 8 (decisión C7/C8-11).

> **Integrado el 2026-09-29 (`DT-042` §8).** C7 se ejecuta en W1 después de C5, con los perfiles de
> C6 en memoria, y antes de C8. `GENERATOR_VERSION` pasó a `0.4.0` una sola vez, junto con C8.

### 13. Implementación *(2026-09-29)*

`data/synthetic/generator/scenarios.py`:

| Función | Qué hace |
|---|---|
| `build_assignment(config, input_dir, profiles)` | Construye el objeto de §4; no escribe |
| `generate(config, output_dir, profiles)` | Comprueba §11.1, construye y escribe el manifiesto |
| `load_facts(config, input_dir)` | Lee los archivos en la estructura inmutable `Facts` |
| `observed_axes(facts)` | Productos de `STOCKOUT`, `OVERSTOCK`, `LOW_INVENTORY`, `MULTIPLE_LEAD_TIMES` e `IN_TRANSIT` (§6.3–§6.6) |
| `supplier_axes(facts, profiles)` | `(suppliers, products)` de los tres ejes de proveedor (§6.2) |
| `emergent_properties(facts)` | Criterios de §8; no publica nada |
| `window_sum`, `overstock_threshold`, `is_overstocked`, `synthetic_quantity` | Aritmética de §6.6 y §8, entera y exacta |

`writer.py` gana `SCENARIOS_VERSION = "0.1.0"` y `add_manifest_field`, que añade un campo aportado
por un componente posterior (`DT-025`) y se niega a sobrescribir uno existente. Ninguna función
existente cambia. Pruebas en `data/synthetic/tests/test_scenarios.py`.

## Contexto

`DT-025` declaró `scenario_assignment` como campo del manifiesto aportado por el Componente 7 y
aplazó su forma a la autorización de ese componente. `DT-035` y `DT-037` dejaron escrito que la
forma de la demanda y el perfil de proveedor los deciden C3 y C6, y que registrarlos es de C7.
`DT-036` dejó que los escenarios de inventario emergieran de la simulación en lugar de fabricarse.
La auditoría C7/C8 (2026-09-29) cerró las catorce decisiones que faltaban.

## Alternativas consideradas

| | Alternativa | Por qué no |
|---|---|---|
| (a) | `scenario_assignment.json` o CSV aparte | Contradice `DT-025` y §42.1: la metadata de generación vive en el manifiesto y ninguna entidad lleva escenario |
| (b) | Índice producto → escenarios, o solo recuentos | Pierde la unidad de cada eje y el `source`; un recuento no es comprobable |
| (c) | Devolver los perfiles desde `demand.generate` | Modifica C3 |
| (d) | Inferir forma y rotación estadísticamente desde `demand.csv` | No es contractual y exigiría inventar umbrales |
| (e) | Umbrales de N días de cobertura para bajo y sobreinventario | Introducen números nuevos que parecerían reglas de negocio |
| (f) | Cobertura de proveedores por producto servido | Mezcla la unidad de C6 con la medición; convierte proveedor en producto sin evidencia |

## Consecuencias

**Positivas**

1. El manifiesto dice qué productos y proveedores representan cada eje, con la procedencia de cada
   dato, sin tocar ninguna entidad (§19, `DT-025`).
2. C3–C6 no cambian; el dataset publicado no cambia.
3. El Componente 8 recibe un contrato de cobertura sin ambigüedad (`null` frente a `[]`).

**Costos aceptados**

1. C7 reconstruye la demanda de C3 (medio segundo con la configuración vigente).
2. Los criterios sintéticos se verán en el manifiesto; se mitiga con la etiqueta en cada entrada y
   con la advertencia de cabecera.

**Qué invalidaría esta decisión**

Que se cierren `BR-X03` o `DT-P11`. Entonces los criterios de §6.6 y §8 podrían sustituirse por las
reglas reales, y `DT-023` prevé reconsiderar la promoción del nivel C a ejes.

## Lo que esta decisión NO hace

- **No** integra C7 en W1, **no** sube `GENERATOR_VERSION` y **no** regenera el dataset publicado.
- **No** implementa el Componente 8 ni el informe de calidad.
- **No** modifica C2, C3, C4, C5, C6, `pipeline.py` ni ninguna regla de negocio.
- **No** añade escenarios al enum ni etiqueta el nivel C.
- **No** cierra `BR-X03`, `DT-P11`, `BR-P10`, `DT-011` ni `DT-P12`.
