# DT-038 — Contrato de salida del Componente 4 (Inventory Simulator)

- **Fecha:** 2026-09-24 · **Actualizada:** 2026-09-26 — decisiones A2 (`order_number` sale de
  `SimulatedOrder`), W1 (§13, publicación por promoción, `DT-040`) y corrección de la autoría de los
  identificadores en §8 · **Actualizada:** 2026-09-26, fase C4 — decisiones D-C4-2 (precondiciones
  de ventana, §16) y D-C4-3 (lead time, margen y disparo diario, §§3 y 7), flujos pseudoaleatorios
  (§17), `metrics` pendiente (§12) e implementación en `generator/inventory.py`
- **Estado:** `ACEPTADA`
- **Fase del roadmap:** Fase 1 — Datos (Componente 4), con efecto en los Componentes 5 y 8
- **Afecta a:** `knowledge/dataset-specification.md` §§20, 21, 34 y 41.3, `docs/04-modelo-datos.md`
  §§3.6, 3.7, 3.8, el diseño de los Componentes 4, 5 y 8
- **Entrada resumida:** `docs/15-decisiones-tecnicas.md` → `DT-038`
- **Relacionada con:** `DT-024` (contrato de salida del Componente 2, cuyo patrón este documento
  reproduce), `DT-025` (manifiesto), `DT-027` (vigencia, enmendada), `DT-031` (`V1-06`, `V1-12`,
  `V1-13`), `DT-032` (determinismo), `DT-033` (versionado), `DT-034` (contrato de `demand.csv`),
  `DT-036` (políticas sintéticas de inventario), `DT-037` (comportamiento de proveedores),
  `DT-039` (contrato de salida del Componente 5), `DT-040` (publicación atómica del dataset)

---

> **Qué es este documento.** `DT-036` fija **qué valores** usa el Componente 4; este fija **qué
> forma** tienen sus salidas. Sin él, `DT-024` solo cubre las cinco entidades maestras y `DT-034`
> solo `demand.csv`, y los tres archivos del Componente 4 quedarían sin contrato — que es la carencia
> que `knowledge/dataset-specification.md` §41.3 declaraba pendiente.
>
> **Las reglas de identificador y de orden de filas de `DT-024` NO se heredan automáticamente.** Se
> reescriben aquí de forma explícita para cada entidad nueva.

---

## 1. Entradas del Componente 4

| Entrada | De dónde | Qué toma |
|---|---|---|
| `products.csv` | C2 | `id`, `is_active`, `valid_from`, `valid_to` |
| `locations.csv` | C2 | `id` |
| `product_suppliers.csv` | C2 | `product_id`, `supplier_id`, `agreed_lead_time_days`, `moq`, `order_multiple`, `unit_cost`, `is_preferred`, `is_active` |
| `demand.csv` | C3 | La serie de demanda **latente** completa (`DT-034`) |
| Perfiles de proveedor | C6, **en memoria** | `SupplierProfile` por `supplier_id` (`DT-037` §3) |
| Políticas | `DT-036` | `W`, `M`, `C`, factores y mezcla de perfiles de apertura |

**No lee** `categories.csv` ni `suppliers.csv`: nada en el bucle causal depende de la categoría de un
producto ni de los atributos del proveedor más allá de su perfil. **`products.is_active` no decide los
días vigentes**: la vigencia es el intervalo `[valid_from, valid_to]` de `DT-027`, que deja abierta a
propósito su relación con `is_active`; el Componente 4 usa la misma rejilla de días que `demand.csv`
(`DT-034`) y comprueba que coincidan (§16). *(No existe ningún archivo
`catalog.csv`; el catálogo son las cinco entidades maestras de `DT-024`.)*

**`demand.csv` es de solo lectura.** El Componente 4 no lo reescribe, no lo reordena y no lo amplía.
Su `sha256` antes y después de una ejecución debe ser idéntico.

## 2. Unidad de cálculo

Todas las recurrencias de inventario, consumo y reposición se calculan por el par

```text
(product_id, location_id)
```

**nunca por `product_id` aislado.** Queda explícito aunque la configuración vigente tenga
`location_count: 1`: la fórmula debe ser correcta para varias ubicaciones sin reescribirse.

## 3. Orden causal del día

Para cada día `t` del periodo `[start_date, end_date)` y cada par `(product_id, location_id)`, en
este orden y sin alternativa:

```text
1. Apertura del día: estado disponible al comenzar t
2. Aplicar las recepciones programadas para t     → movimiento RECEIPT, occurred_at = t T06:00:00Z
3. Leer la demanda latente del día                → demand.csv
4. Aplicar el consumo                             → movimiento ISSUE,  occurred_at = t T18:00:00Z
5. Evaluar el disparo de reposición               → DESPUÉS del consumo del día
6. Si corresponde, emitir la orden                → issued_at = t T00:00:00Z
7. Cerrar el estado del día
```

**El disparo usa el inventario disponible después del consumo del día** (paso 5 después del 4). Esto
cierra la ambigüedad que `DT-036` §3 no resolvía.

**El paso 5 se ejecuta todos los días** del intervalo vigente *(decisión D-C4-3 del 2026-09-26)*. No hay
periodo de revisión: ni `M` —que es el margen del saldo de apertura de `DT-036` §1— ni el `R_v1` del
motor intervienen en el disparo. Si una orden no basta para superar `s(t)`, al día siguiente se evalúa
de nuevo y puede emitirse otra.

El bucle recorre **todo** el periodo también para los productos cuya vigencia ya terminó, porque sus
órdenes en vuelo siguen recibiendo (§9). Después de `valid_to` no hay demanda, ni consumo, ni disparo.

## 4. `consumption.csv` — entidad `Consumption`

**Fórmula, sin backlog:**

```text
consumption(t) = min( demanda_latente(t), on_hand_antes_del_consumo(t) )
lost_sales(t)  = demanda_latente(t) − consumption(t)        ← derivable, NO se almacena
```

La demanda no satisfecha **se pierde**: no se arrastra al día siguiente, no se acumula en ninguna
cola y no reaparece. Invariantes que se siguen de la fórmula y que el Componente 8 debe comprobar:

```text
0 ≤ consumption(t) ≤ demanda_latente(t)
consumption(t) ≤ on_hand_antes_del_consumo(t)
is_stockout_affected(t) = ( demanda_latente(t) > consumption(t) )
demanda_latente(t) = 0  ⟹  consumption(t) = 0  y  is_stockout_affected(t) = false
```

**Densidad: serie densa, una fila por día vigente**, exactamente la misma rejilla que `demand.csv`
(`DT-034`). Una fila con `quantity = 0` no es una fila ausente: distingue «ese día no se consumió
nada» de «ese día el producto no existía».

**Columnas, en este orden:**

| # | Columna | Tipo | Nulo | Clave | Valores y semántica |
|--:|---|---|---|---|---|
| 1 | `id` | entero ≥ 1 | No | PK | Asignado según §8 |
| 2 | `product_id` | entero | No | FK + BN | → `products.id` |
| 3 | `location_id` | entero | No | FK + BN | → `locations.id` |
| 4 | `occurred_on` | fecha `YYYY-MM-DD` | No | BN | Día del consumo |
| 5 | `quantity` | **entero** ≥ 0 | No | | Demanda satisfecha del día |
| 6 | `channel` | texto | **Sí — siempre vacío** | | Ninguna política define canales en V1 |
| 7 | `is_stockout_affected` | `true` / `false` | No | | Según la fórmula de arriba |
| 8 | `data_origin` | texto | No | | Constante `SYNTHETIC` |

- **Clave de negocio (BN):** `(product_id, location_id, occurred_on)`, única.
- **Orden de filas:** ascendente por `(product_id, location_id, occurred_on)`.
- **Precisión:** `quantity` es **entero** para toda unidad de medida en V1, igual que `DT-034` fijó
  para `demand.csv`. No se emiten decimales.
- **Número de filas:** idéntico al de `demand.csv` en la misma ejecución.

## 5. `inventory_movements.csv` — entidad `InventoryMovement`

Es la **fuente de verdad histórica** del inventario. Append-only, inmutable.

**Columnas, en este orden:**

| # | Columna | Tipo | Nulo | Clave | Valores y semántica |
|--:|---|---|---|---|---|
| 1 | `id` | entero ≥ 1 | No | PK | Asignado según §8 |
| 2 | `product_id` | entero | No | FK + BN | → `products.id` |
| 3 | `location_id` | entero | No | FK + BN | → `locations.id` |
| 4 | `movement_type` | texto | No | BN | **Solo** `ADJUSTMENT`, `RECEIPT`, `ISSUE` en V1 |
| 5 | `quantity` | entero ≠ 0 | No | | **Con signo, según §5.1** |
| 6 | `occurred_at` | fecha-hora ISO UTC | No | BN | Según la convención de reloj de `DT-036` §9 |
| 7 | `recorded_at` | fecha-hora ISO UTC | No | | `= occurred_at`. V1 no simula registro tardío |
| 8 | `reference_type` | texto | No | | `INITIAL_INVENTORY` \| `PURCHASE_ORDER_RECEIPT` \| `CONSUMPTION` |
| 9 | `reference_id` | entero | Sí | BN | Según §5.2. Vacío **solo** en el saldo de apertura |
| 10 | `reason_code` | texto | Sí | | `OPENING_BALANCE` en la apertura; vacío en los demás |
| 11 | `data_origin` | texto | No | | Constante `SYNTHETIC` |
| 12 | `created_by` | texto | **Sí — siempre vacío** | | No existe proceso usuario (`D-05`) |

### 5.1 Signo de `quantity` — explícito, no «según el tipo»

| `movement_type` | Signo | Efecto sobre la existencia |
|---|---|---|
| `ADJUSTMENT` con `reason_code = OPENING_BALANCE` | **Positivo** | Aumenta |
| `RECEIPT` | **Positivo** | Aumenta |
| `ISSUE` | **Negativo** | Disminuye |

Con ello la reconstrucción es una suma sin excepciones:

```text
on_hand(p, l, t) = Σ quantity  sobre los movimientos de (p, l) con occurred_at ≤ t
```

V1 no emite `RETURN`, `TRANSFER_IN`, `TRANSFER_OUT` ni `SCRAP`: ningún proceso los genera y `DT-036`
§7 prohíbe expresamente usar `SCRAP` para las bajas de producto.

### 5.2 Referencias por tipo

| `movement_type` | `reference_type` | `reference_id` | `reason_code` |
|---|---|---|---|
| `ADJUSTMENT` (apertura) | `INITIAL_INVENTORY` | **vacío** — no hay documento origen | `OPENING_BALANCE` |
| `RECEIPT` | `PURCHASE_ORDER_RECEIPT` | `purchase_order_receipts.id` | vacío |
| `ISSUE` | `CONSUMPTION` | `consumption.id` | vacío |

Un `RECEIPT` enlaza con **la recepción concreta**, no con la orden ni con la línea: desde la
recepción se llega a la línea (`purchase_order_item_id`) y desde ella a la orden, de modo que la
cadena `movimiento → recepción → línea → orden` es navegable en un solo sentido y sin ambigüedad.
Ese `id` lo asigna el Componente 4 (§8), **no** el Componente 5, precisamente para que el movimiento
pueda referenciarlo antes de que el archivo exista.

### 5.3 Cuándo NO se emite un movimiento

- **Consumo cero**: no se emite `ISSUE`, porque `docs/04` §3.7 exige `quantity ≠ 0`. La fila de
  `consumption.csv` **sí** se emite (la serie es densa); el movimiento no.
- **Saldo de apertura cero**: no se emite `ADJUSTMENT`, por la misma razón. Con la configuración
  vigente el caso no se alcanza —la suma mínima de los primeros 28 días es 12 unidades—, pero la
  regla queda escrita para que el generador no dependa de esa circunstancia.

### 5.4 Desempate determinista

Dos movimientos del mismo par pueden compartir `occurred_at` (dos recepciones el mismo día). El
orden total es:

```text
(product_id, location_id, occurred_at, rango_de_tipo, reference_id)

rango_de_tipo:  ADJUSTMENT = 0   RECEIPT = 1   ISSUE = 2
reference_id vacío ordena como 0
```

El desempate por `reference_id` es total porque dos recepciones distintas tienen `id` distintos, y
esos `id` ya están asignados cuando se ordenan los movimientos (§8). **No depende del orden de
iteración** de ninguna estructura. El saldo matemático es indiferente al desempate —la suma es
conmutativa—, pero el orden de filas y, con él, la asignación de `id` y la identidad byte a byte de
§44 dependen de que exista.

## 6. `inventory.csv` — entidad `Inventory`

**Snapshot final. No es una serie temporal.** Una fila por `(product_id, location_id)`, con el estado
en el instante del corte. Incluye **todos** los pares, también los de productos descatalogados, que
conservan su saldo.

| # | Columna | Tipo | Nulo | Clave | Valores y semántica |
|--:|---|---|---|---|---|
| 1 | `id` | entero ≥ 1 | No | PK | Asignado según §8 |
| 2 | `product_id` | entero | No | FK + BN | → `products.id` |
| 3 | `location_id` | entero | No | FK + BN | → `locations.id` |
| 4 | `quantity_on_hand` | entero ≥ 0 | No | | Σ de los movimientos del par (`V1-13`) |
| 5 | `quantity_reserved` | entero | No | | Constante `0` (`V1-02`; `docs/04` §3.6) |
| 6 | `quantity_in_transit` | entero ≥ 0 | No | | Tránsito **total** al corte, según §6.1 |
| 7 | `last_movement_at` | fecha-hora ISO UTC | Sí | | `occurred_at` del último movimiento del par; vacío si no tuvo ninguno |
| 8 | `updated_at` | — | **Sí — siempre vacío** | | Auditoría técnica: la fija la ingesta, no el generador (`DT-024`, `D-05`) |
| 9 | `data_origin` | texto | No | | Constante `SYNTHETIC` |

- **Clave de negocio:** `(product_id, location_id)`, **única** — es lo que `docs/04` §3.6 exige.
- **Orden de filas:** ascendente por `(product_id, location_id)`.
- **Número de filas:** `product_count × location_count`.
- **Reconstruible:** `quantity_on_hand` debe coincidir exactamente con la suma firmada de los
  movimientos del par. `inventory.csv` **no es una segunda fuente de verdad**: es un estado
  calculado, y cualquier discrepancia es un incidente de datos.

### 6.1 `quantity_in_transit`

```text
quantity_in_transit(p, l) = Σ ( quantity_ordered − quantity_received )
                            sobre las líneas de órdenes de (p, l)
                            cuyo estado al corte es ISSUED o PARTIALLY_RECEIVED
```

Es la definición de `docs/04` §3.9 («solo las órdenes en estado `ISSUED` o `PARTIALLY_RECEIVED`
aportan inventario en tránsito») aplicada al corte. Las órdenes `RECEIVED` y `CANCELLED` no aportan.

**Terminología:** el concepto que `DT-036` §3 llamaba `inventory_on_order` **es** este
`quantity_in_transit`. No se crea ninguna entidad ni ningún campo nuevo; se usa el nombre canónico
del modelo. `DT-036` queda corregido en ese punto.

## 7. Reposición — forma exacta

```text
d̄_recent(t) = media de la demanda latente en la ventana de W = 28 días de DT-036 §5
              calculada como RACIONAL EXACTO: suma_demanda / número_de_días
              sin redondeo intermedio, y sin flotantes (DT-032)

s(t)      = ceil( d̄_recent(t) × L )                L = agreed_lead_time_days del preferente activo
raw_need  = Q                                      Q = ceil( d̄_recent(t) × C )   C = 21

si raw_need ≤ 0:  NO HAY ORDEN                     ← guarda obligatoria de V1-06
Q_moq     = max( raw_need, MOQ )
Q_final   = ceil( Q_moq / order_multiple ) × order_multiple
```

**La guarda `raw_need ≤ 0` es obligatoria y precede a todo cálculo de `Q_final`.** Es la primera
línea de `V1-06` (`DT-031`), que `DT-036` §4 citaba amputada. Consecuencias, todas exigidas:

- `d̄_recent = 0` **no** produce ninguna orden. Con la configuración vigente hay 9 pares que alcanzan
  ese estado (productos 18, 22, 24, 30, 66, 68, 69, 75, 100).
- No se emite una orden repetida cada día cuando `s = 0`.
- **Nunca** se genera `quantity_ordered = 0`, que violaría `docs/04` §3.10.
- **No** se introduce un mínimo artificial de una unidad.
- **No** se cambia el operador `≤` del disparo: la guarda actúa sobre la cantidad, no sobre el
  disparo.

**Disparo:**

```text
on_hand_después_del_consumo(t) + quantity_in_transit(t)  ≤  s(t)
```

evaluado en el paso 5 del día (§3), **solo** si el producto está vigente en `t` y tiene una relación
`ProductSupplier` activa y preferente. Los cinco productos sin proveedor activo no lo evalúan nunca
(`DT-036` §6).

**`L` es siempre el lead time acordado** *(decisión D-C4-3 del 2026-09-26)*: el
`agreed_lead_time_days` de la relación preferente activa, tanto en `s(t)` como en
`expected_on = issued_on + L`. **No** se usa el lead time observado ni la regla `V1-09` (mínimo de
3 observaciones, ventana de 12 observaciones, techo de 90 días), que es del motor de abastecimiento y
no del generador: un proveedor que llega tarde no altera ni el umbral ni la fecha comprometida de las
órdenes siguientes. `M = 7` **no** aparece en esta sección: es exclusivamente el margen del saldo de
apertura (`DT-036` §1).

**Una orden por par producto–ubicación.** El disparo es por par, de modo que cada orden lleva
**exactamente una línea**. Agrupar varios productos del mismo proveedor en una orden sería una
política de consolidación de compras que ningún documento declara, y `docs/02` §247 la sitúa
explícitamente fuera del alcance. No se consolida.

## 8. Identificadores — asignación explícita

El Componente 4 asigna los identificadores de **todo lo causal**: las órdenes que su simulación emite,
sus líneas y sus recepciones —que el Componente 5 materializará sin renumerar—, y las tres entidades
que él mismo escribe. **No asigna** los de las órdenes `CANCELLED` sintéticas ni los de sus líneas:
esas filas las crea el Componente 5, y es él quien las numera (`DT-039` §5.2). Los identificadores del
Componente 4 se asignan **después** de completar la simulación, en esta secuencia, que es acíclica por
construcción:

| Orden | Entidad | Clave de ordenamiento previa | Primer valor | Incremento |
|--:|---|---|--:|--:|
| 1 | `purchase_orders` **causales** | `(issued_on, supplier_id, product_id, location_id)` | 1 | 1 |
| 2 | `purchase_order_items` de esas órdenes | `(purchase_order_id)` | 1 | 1 |
| 3 | `purchase_order_receipts` | `(received_on, purchase_order_item_id)` | 1 | 1 |
| 4 | `consumption` | `(product_id, location_id, occurred_on)` | 1 | 1 |
| 5 | `inventory_movements` | `(product_id, location_id, occurred_at, rango_de_tipo, reference_id)` | 1 | 1 |
| 6 | `inventory` | `(product_id, location_id)` | 1 | 1 |

- **El Componente 4 numera las órdenes causales, y solo esas.** Las órdenes `CANCELLED` sintéticas
  las crea el Componente 5 **después**, de modo que no pueden formar parte de esta numeración: el
  Componente 5 **continúa** la secuencia a partir del último `id` que el Componente 4 emitió, sin
  renumerar nada de lo recibido (`DT-039` §5.2 y §7). Cada `id` tiene, por tanto, **una sola
  autoridad**: el Componente 4 para todo lo causal y para las seis entidades de inventario y consumo;
  el Componente 5 solo para las filas sintéticas que él mismo crea.
- El paso 3 precede al 5 para que el movimiento `RECEIPT` pueda referenciar la recepción (§5.2).
- El paso 4 precede al 5 por la misma razón, para `ISSUE`.
- Cada clave de ordenamiento es **total**: no hay empates residuales, y ninguna depende del orden de
  iteración de un diccionario, de un conjunto ni del sistema de archivos.
- `id` es único dentro de su entidad y **no se reutiliza entre ejecuciones con configuraciones
  distintas**, igual que en `DT-028` §4.

**Reproducibilidad exigida:** la misma semilla y la misma configuración producen exactamente los
mismos identificadores.

## 9. Vigencia y corte del periodo

**Órdenes en vuelo (enmienda de `DT-027` del 2026-09-24).** Una orden emitida **antes** de `valid_to`
conserva su ciclo causal aunque una recepción ocurra después de `valid_to`. Esa recepción:

- **no** se cancela;
- **no** se elimina;
- **no** se trunca;
- **no** se convierte en `ADJUSTMENT`;
- conserva el `reference_type` y el `reference_id` correspondientes a su origen.

Después de `valid_to` no hay demanda, ni consumo, ni órdenes nuevas, ni ningún otro movimiento.

**Corte del dataset.** El periodo es semiabierto `[start_date, end_date)`:

| Hecho | Dentro del dataset |
|---|---|
| Recepción con `received_on < end_date` | **Sí** — se materializa, genera su movimiento `RECEIPT` y actualiza `quantity_received` |
| Recepción con `received_on ≥ end_date` | **No** — no se escribe ninguna fila ni ningún movimiento |
| Orden cuya recepción cae fuera | Queda **pendiente al corte**: `ISSUED` o `PARTIALLY_RECEIVED`, y aporta `quantity_in_transit` |

`closed_at` y `quantity_received` reflejan **únicamente hechos materializados hasta el corte**. Una
orden cuyo faltante llegaría después de `end_date` no se cierra: no se inventa ninguna regla de
cierre posterior.

## 10. Máquina de estados de la orden

Estados de `docs/04` §3.9. V1 usa cuatro de los cinco; **`DRAFT` no se emite** (§11).

| Desde | Hacia | Guarda | Quién |
|---|---|---|---|
| — | `ISSUED` | Disparo de §7 satisfecho | C4 (causal) |
| `ISSUED` | `PARTIALLY_RECEIVED` | `0 < Σ recibido < ordenado` antes del corte | C4 |
| `ISSUED` | `RECEIVED` | `Σ recibido = ordenado` antes del corte | C4 |
| `PARTIALLY_RECEIVED` | `RECEIVED` | Llega el faltante antes del corte | C4 |
| — | `CANCELLED` | Orden sintética de cobertura | C5 (`DT-039`, **no causal**) |

- `closed_at` se rellena **solo** en `RECEIVED` y en `CANCELLED`; vacío en los demás.
- `Σ recibido ≤ ordenado` **siempre**, sin excepción (`V1-12`).
- Estados terminales al corte: `ISSUED` y `PARTIALLY_RECEIVED` son los que aportan tránsito.

## 11. Órdenes `CANCELLED` — dónde vive la regla

El Componente 4 **no cancela ninguna orden**. Las órdenes `CANCELLED` que el dataset necesita para
cumplir §14 de la especificación son sintéticas, no causales, y su regla vive en `DT-039` §5. Son
neutras para el inventario **por construcción**, no por cuidado: `docs/04` §3.9 limita el tránsito a
`ISSUED` y `PARTIALLY_RECEIVED`, y no generan recepciones ni movimientos.

**`DRAFT` no se emite.** §14 de la especificación enumera «completamente recibidas, parcialmente
recibidas, pendientes, canceladas» y **no** exige `DRAFT`; ninguna otra sección lo exige. Emitirlo
sería ampliar el dataset sin necesidad.

## 12. Estructura que el Componente 4 entrega al Componente 5

En memoria, congelada, con los identificadores **ya asignados** según §8:

```text
SimulationResult
├── orders:  tupla de SimulatedOrder, en el orden canónico de §8
└── metrics: métricas de simulación (DT-036 §17 del acuerdo; no se persisten en V1)  ← PENDIENTE

SimulatedOrder
├── id, supplier_id, location_id
├── issued_on, expected_on, closed_on | None, status
├── line: SimulatedOrderLine
└── receipts: tupla de SimulatedReceipt, ordenada por (received_on, id)

SimulatedOrderLine
├── id, purchase_order_id, product_id
├── quantity_ordered, quantity_received      ← acumulado DENTRO del periodo
└── unit_cost_cents                          ← de la relación preferente activa

SimulatedReceipt
├── id, purchase_order_item_id
├── received_on
└── quantity                                 ← > 0
```

El Componente 5 recibe esto y **lo escribe**. No recalcula nada: `DT-039` lo desarrolla.

> **Cerrado el 2026-09-29 (decisión C7/C8-09, `DT-042`).** `SimulationResult` **no** tendrá
> `metrics`: el Componente 4 no cambia, y las magnitudes que el informe de calidad necesita las
> deriva el Componente 8 de los archivos del dataset. El pendiente documental de abajo queda cerrado
> sin ninguna definición nueva.

**`metrics` no está implementado** *(fase C4, 2026-09-26)*. La referencia «`DT-036` §17 del acuerdo» no
apunta a ningún texto del repositorio: `DT-036` no tiene sección 17 y ningún documento define qué
métricas son ni cómo se calculan. Inventar sus fórmulas está prohibido, de modo que
`SimulationResult` entrega solo `orders`. **Pendiente documental**: si se quieren métricas de
simulación, su definición debe aprobarse antes de implementarlas. Todas las magnitudes que podrían
necesitar —desabastos, ventas perdidas, retrasos, entregas partidas, tránsito— son derivables de los
archivos que el Componente 4 escribe y de las órdenes que entrega.

**`SimulatedOrder` no lleva `order_number`** *(decisión A2 del 2026-09-26)*. El ancho de relleno de
`order_number` depende del total de órdenes de la ejecución —las causales **más** las `CANCELLED`
que crea el Componente 5—, y el Componente 4 no puede conocer ese total sin conocer la política de
cancelaciones de `DT-039`. Por eso `order_number` lo forma **el Componente 5**, para todas las
órdenes, a partir del `id` que recibe (`DT-039` §6). **El Componente 4 no conoce
`ORDERS_CANCELLED_PERMILLE` ni ninguna otra política de C5.** *Una versión anterior de esta sección
incluía `order_number` en `SimulatedOrder`; queda retirado.*

**`expected_on` es la única fuente de la fecha comprometida.** Lo calcula el Componente 4 al emitir
la orden (`issued_on + agreed_lead_time_days`, `DT-037` §3). El Componente 5 lo **copia** a
`purchase_orders.expected_at` sin recalcularlo, modificarlo ni reinterpretarlo (`DT-039` §2).

## 13. Contrato del directorio de salida

`DT-024` establece que «cada ejecución regenera el directorio completo» y que un directorio que
mezcle archivos de ejecuciones distintas **no es un dataset válido**. Hasta ahora el generador no lo
comprobaba. Con seis archivos nuevos, comprobarlo deja de ser opcional.

**Comportamiento exigido, antes de escribir nada** —comprobación previa sobre `output/`, paso 1 del
flujo de `DT-040`:

1. Si el directorio no existe o está vacío, la ejecución continúa con normalidad.
2. Si contiene únicamente archivos del conjunto que esta ejecución va a producir, la ejecución
   continúa, y esos archivos **se reemplazan en bloque en la promoción final** (`DT-040` §5). *Antes
   de `DT-040` esta regla decía «se sobrescriben»; con la escritura progresiva eso era, precisamente,
   lo que podía mezclar dos ejecuciones.*
3. Si contiene **cualquier otro archivo** —de una ejecución anterior con otro conjunto de
   componentes, o ajeno al dataset—, la generación **falla explícitamente**, nombrando los archivos
   encontrados.
4. **Nunca se borra un archivo que el generador no vaya a escribir.** No hay limpieza indiscriminada
   del directorio ni eliminación de archivos del usuario.
5. Nunca se produce en silencio un dataset mezclado.

**Publicación (`DT-040`, decisión W1 del 2026-09-26).** Ningún componente escribe en `output/`. Cada
ejecución completa trabaja en su propio workspace, `data/synthetic/tmp/<id_de_ejecución>/`, y
`output/` solo cambia cuando el orquestador **promociona el workspace entero**, después de que todos
los componentes hayan terminado y la verificación final haya pasado. En particular:

- **Si cualquier componente falla** —incluido el Componente 5 por la regla B2 de cero elegibles
  (`DT-039` §5.2)—, **no hay promoción** y `output/` queda **intacto**, con el dataset válido anterior
  si lo había.
- **Una ejecución fallida nunca deja `output/` parcialmente actualizado.** La regla 5 deja de depender
  de la disciplina de cada componente y pasa a ser una garantía estructural.
- **Prohibido** escribir en `output/` y borrar lo escrito si algo falla (estrategia W3, no aprobada).

Para el Componente 4 esto no cambia nada de su contrato: escribe sus tres archivos en el directorio
que recibe, que es el workspace, y lee de ese mismo directorio los archivos de C2 y C3 (§1). No sabe
que es un workspace ni conoce `output/`.

La implementación concreta corresponde a la fase de código; el comportamiento esperado queda fijado
aquí y en `DT-040`. Esto cierra el pendiente que `project/status.md` arrastraba desde el Componente 3.

## 14. Convenciones heredadas y precisión numérica

Rigen sin cambios: `DT-024` §Convenciones de archivo —UTF-8 sin BOM, coma, RFC 4180 mínimo, LF,
cabecera obligatoria, nulos como campo vacío, fechas `YYYY-MM-DD`, fechas-hora ISO-8601 UTC,
booleanos en minúscula, filas ascendentes por clave de negocio— y la convención de reloj de `DT-036`
§9.

**Precisión numérica.** Todas las cantidades de los tres archivos son **enteras**: `quantity`,
`quantity_on_hand`, `quantity_reserved`, `quantity_in_transit`. Es la misma decisión que `DT-034`
tomó para `demand.csv` y responde al hueco que `DT-024` dejaba abierto para los decimales no
monetarios. Los importes —que aparecen en los archivos del Componente 5, no en estos— llevan
exactamente dos decimales.

**Campos de auditoría vacíos** (`D-05`): `created_by` en los movimientos y `updated_at` en el
inventario se emiten como campo vacío. No se generan marcas de tiempo artificiales de auditoría: la
temporalidad de la simulación se expresa con los campos temporales propios de cada entidad y con
`manifest.time_range`.

## 15. Manifiesto

El Componente 4 extiende el manifiesto con su componente y sus tres archivos, mediante
`writer.extend_manifest`:

```text
components[] += { name: "inventory", version: INVENTORY_VERSION, sub_seed: sub_seed(seed, "inventory") }
files[]      += consumption.csv · inventory.csv · inventory_movements.csv   (nombre, entidad, filas, sha256)
```

`dataset_version` no se recalcula al extender: deriva de la configuración y de `generator_version`
(`DT-033`).

## 16. Precondiciones *(decisión D-C4-2 del 2026-09-26)*

La ventana `W` de `DT-036` §§1 y 5 mide **siempre** exactamente `W = 28` días. Cuando los datos no
permiten una ventana completa, la ventana **no se acorta, no se rellena y no se extrapola**: la
generación **falla** con `GeneratorError`, antes de simular nada y sin escribir ningún archivo.

| Precondición | Condición | Por qué |
|---|---|---|
| **P-C4-2** | `period.days ≥ W` | Sin un periodo de `W` días no existe ninguna ventana completa |
| **P-C4-3** | Para cada producto, los días vigentes dentro del periodo son `≥ W` | El saldo de apertura usa los primeros `W` días vigentes del par, y la ventana congelada del warm-up también (`DT-036` §5) |

Ambas se comprueban juntas con el resto de problemas, que se informan **todos a la vez**. Con la
configuración vigente no se activan: el periodo tiene 1 096 días y el producto de menor vigencia
está en vigor 823 de ellos. Son alcanzables con configuraciones que el Componente 2 acepta —periodos
de 20 o 30 días, o productos cuya vigencia termina o empieza cerca del borde del periodo—, y esa es
la razón de declararlas.

El Componente 4 hace además estas **comprobaciones de coherencia de entradas**, cada una derivada de
una regla ya escrita en otro documento; ninguna introduce una regla nueva:

| Comprobación | Regla de la que se deriva |
|---|---|
| Todo producto tiene al menos una relación en `product_suppliers.csv` | `DT-036` §6: sin relación no se inventa un lead time por defecto |
| Como máximo una relación activa y preferente por producto | `DT-028` §2.4 y `docs/04` §3.4; §7 ordena a esa única relación |
| Todo proveedor que emite órdenes tiene un `SupplierProfile`, y un solo perfil | `DT-037` §3: `supplier_id` es clave única del perfil |
| Los perfiles respetan los rangos de la tabla de `DT-037` §3 | `DT-037` §3 |
| `demand.csv` tiene exactamente una fila por par y día vigente | `DT-034` (serie densa) y §4 de este documento |
| Al menos una ubicación y al menos tres pares producto–ubicación | `DT-036` §2: suelo de uno por perfil de apertura |

Un proveedor que no emite órdenes —el de una relación inactiva o no preferente— **no** necesita
perfil.

## 17. Flujos pseudoaleatorios del Componente 4

Todos derivan de `sub_seed(seed, "inventory")` (`DT-030`) con el generador de `DT-032`, y **ninguno**
depende del orden de iteración de una estructura:

| Flujo | Qué extrae | Orden de extracción |
|---|---|---|
| `opening-profile-assignment` | Una permutación de los pares ordenados por `(product_id, location_id)`, que reparte los cupos de `DT-036` §2 | Una sola vez |
| `receipt-timing:{product_id}:{location_id}` | Puntualidad de cada orden del par (`DT-037` §3) | Por orden, en orden de emisión: `below(1000)`; si no llega a tiempo, `between` sobre `delay_days` |
| `receipt-split:{product_id}:{location_id}` | Integridad de cada orden del par (`DT-037` §3) | Por orden, en orden de emisión: `below(1000)`; si se parte, `between` sobre `split_range` y después sobre `completion_lag_days` |

Los flujos de recepción van **por par**, como pide `DT-037` §4: un cambio en la demanda de un producto
no desplaza la secuencia de ningún otro. Los parámetros del perfil son constantes (`DT-037` §4); lo
único que se sortea es qué ocurre con cada orden concreta.

## Alternativas consideradas

| | Alternativa | Ventajas | Inconvenientes |
|---|---|---|---|
| (a) | **Un ADR de contrato por componente, con el patrón de `DT-024`** | Es el precedente del repositorio; el Componente 8 tiene contra qué validar | Dos documentos más |
| (b) | Ampliar `DT-024` con las entidades nuevas | Un solo contrato | `DT-024` es el contrato **del Componente 2**; ampliarlo mezclaría tres componentes en una decisión ya aceptada |
| (c) | Dejar los contratos en el código y documentarlos después | Más rápido | `CLAUDE.md` §8: la documentación no se dispersa en el código. Y es justo lo que la auditoría encontró como bloqueante |
| (d) | Heredar implícitamente las reglas de `DT-024` | Cero trabajo | `DT-024` fija el orden de filas por claves de negocio **que estas entidades no tienen declaradas**. La herencia no tiene a qué referirse |

## Razón

**(a).** (d) es la que la auditoría del 2026-09-24 descartó con evidencia: la regla «`id` secuencial
tras ordenar por la clave de negocio» de `DT-024` **no tiene orden al que referirse** mientras la
clave de negocio de cada entidad nueva no esté declarada, y eso convierte la reproducibilidad del
`id` en una consecuencia del orden accidental del bucle. (b) alteraría una decisión aceptada cuyo
alcance es otro componente. (c) contradice la regla de documentación del proyecto.

## Consecuencias

**Positivas**

1. Los tres archivos del Componente 4 tienen contrato completo: columnas, tipos, claves, orden,
   identificadores y precisión. El Componente 8 tiene contra qué validar.
2. La reconstrucción del inventario desde los movimientos es una suma sin excepciones, porque el
   signo está fijado por tipo.
3. La cadena `movimiento → recepción → línea → orden` es navegable y acíclica.
4. Los casos degenerados —consumo cero, apertura cero, `d̄_recent` cero— tienen regla escrita.

**Costos aceptados**

1. Dos documentos más que mantener sincronizados con `docs/04`.
2. `consumption.csv` densa significa un archivo tan grande como `demand.csv` (≈108 000 filas con la
   escala vigente). Es el precio de distinguir «no se consumió» de «no existía».
3. La asignación de identificadores en seis pasos obliga a completar la simulación antes de escribir
   nada. El generador deja de poder escribir en streaming.

**Qué invalidaría esta decisión**

Que lleguen datos reales de inventario, consumo y órdenes, en cuyo caso estos contratos se
sustituyen por el esquema de la base de datos de la Fase 2. O que el negocio confirme que el
histórico real no tiene granularidad diaria, lo que obligaría a revisar la densidad de
`consumption.csv`.

## Lo que esta decisión NO hace

- **No** fija ninguna política de negocio, ni umbral, ni parámetro de compra: los valores están en
  `DT-036` y son sintéticos.
- **No** decide el contrato de los archivos del Componente 5: eso es `DT-039`.
- **No** modifica `DT-024`, ni el Componente 2, ni el Componente 3, ni `demand.csv`.
- **No** introduce estados de orden que `docs/04` §3.9 no tenga.
- **No** implementa nada por sí mismo. *(Nota del 2026-09-26: el contrato está implementado en
  `data/synthetic/generator/inventory.py` y probado en `data/synthetic/tests/test_inventory.py`; el
  Componente 4 **no** está conectado a `__main__` hasta que existan los Componentes 5 y 6.
  Actualización del 2026-09-29: conectado a través de W1, `DT-040` §9.)*
