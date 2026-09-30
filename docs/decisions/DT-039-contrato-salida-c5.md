# DT-039 — Contrato de salida del Componente 5 (Purchase Order Generator)

- **Fecha:** 2026-09-24 · **Actualizada:** 2026-09-26 — decisiones de D-01: A2 (C5 forma
  `order_number`), B2 (fallo con cero elegibles, sin publicación), `expected_at` copiado de C4,
  valores aprobados de §5.2, publicación por promoción (`DT-040`) y corrección de la autoría de los
  identificadores · **Actualizada:** 2026-09-27 — cierre de D-01, **opción A**: condición de
  elegibilidad de las canceladas respecto de `valid_to` (§5.2, punto 1) · **Implementada:**
  2026-09-28 en `data/synthetic/generator/orders.py` (§13); ninguna regla de este documento cambia
- **Estado:** `ACEPTADA`
- **Fase del roadmap:** Fase 1 — Datos (Componente 5), con efecto en el Componente 8
- **Afecta a:** `knowledge/dataset-specification.md` §§14, 20, 21, 34 y 41.3,
  `docs/04-modelo-datos.md` §§3.9, 3.10, 3.11, el diseño de los Componentes 5 y 8
- **Entrada resumida:** `docs/15-decisiones-tecnicas.md` → `DT-039`
- **Relacionada con:** `DT-024` (patrón de contrato), `DT-025` (manifiesto), `DT-028` §4 (ensanchado
  de códigos), `DT-031` (`V1-12`), `DT-036` (políticas sintéticas), `DT-037` (comportamiento de
  proveedores), `DT-038` (contrato de salida del Componente 4, del que este depende), `DT-040`
  (publicación atómica del dataset)

---

> **El Componente 5 es un materializador, no un simulador.** Recibe de `DT-038` §12 los hechos ya
> decididos por el Componente 4 —con sus identificadores ya asignados— y los escribe. La única
> excepción, acotada y declarada, son las órdenes `CANCELLED` sintéticas de §5, que existen para
> cubrir §14 de la especificación y que **no** son cancelaciones causales.

---

## 1. Lo que el Componente 5 NO hace

No recalcula, bajo ninguna circunstancia:

```text
s          ·  Q          ·  demanda       ·  consumo        ·  inventario
lead time  ·  retrasos   ·  particiones   ·  cantidades recibidas  ·  fechas causales
```

Tampoco decide estados, ni reordena recepciones, ni reasigna identificadores, ni inventa condiciones
de cancelación para las órdenes causales. Si el Componente 5 necesitara alguno de esos valores y no
lo tuviera, la respuesta correcta es ampliar la estructura de `DT-038` §12, **no** recomputarlo.

Consecuencia comprobable: el módulo del Componente 5 **no importa** el módulo del Componente 4 para
recalcular nada, no consume ninguna política de `DT-036` y no usa el flujo aleatorio `inventory`. Su
único uso de aleatoriedad es el de §5.

**Lo que el Componente 5 SÍ forma, y por qué no es recalcular** *(decisión A2 del 2026-09-26)*: el
`order_number` de **todas** las órdenes, causales y canceladas (§6). No es una decisión causal sino
una **representación derivada del `id`**: una función pura del identificador y del número total de
órdenes de la ejecución, que solo el Componente 5 conoce, porque es quien crea las canceladas. El
Componente 5 **no renumera** ningún `id` al formarlo.

**Las fechas causales se copian, no se recalculan.** `issued_at` y `expected_at` proceden de
`SimulatedOrder.issued_on` y `SimulatedOrder.expected_on`, que calcula el Componente 4. El Componente
5 no los recalcula, no los modifica y no los reinterpreta.

## 2. `purchase_orders.csv` — entidad `PurchaseOrder`

| # | Columna | Tipo | Nulo | Clave | Valores y semántica |
|--:|---|---|---|---|---|
| 1 | `id` | entero ≥ 1 | No | PK | Órdenes causales: asignado por C4 (`DT-038` §8), y C5 lo escribe tal cual. Órdenes `CANCELLED` sintéticas: asignado por C5, continuando la secuencia (§5.2) |
| 2 | `order_number` | texto | No | BN | **Formado por C5** para todas las órdenes, según §6 |
| 3 | `supplier_id` | entero | No | FK | → `suppliers.id` |
| 4 | `location_id` | entero | No | FK | → `locations.id` |
| 5 | `status` | texto | No | | `ISSUED` \| `PARTIALLY_RECEIVED` \| `RECEIVED` \| `CANCELLED`. **`DRAFT` no se emite** |
| 6 | `issued_at` | fecha-hora ISO UTC | No | | Copiado de `SimulatedOrder.issued_on`, a `T00:00:00Z`. En una cancelada, el de su plantilla |
| 7 | `expected_at` | fecha-hora ISO UTC | No | | **Copiado de `SimulatedOrder.expected_on`, calculado por C4** (`DT-038` §12), a `T00:00:00Z`. C5 no lo recalcula, no lo modifica ni lo reinterpreta. En una cancelada, el de su plantilla |
| 8 | `closed_at` | fecha-hora ISO UTC | Sí | | Solo en `RECEIVED` y `CANCELLED`; vacío en los demás |
| 9 | `currency` | texto | **Sí — siempre vacío** | | `suppliers.csv` no lleva moneda (`DT-028`); un importe sin divisa sería peor que omitirlo |
| 10 | `total_amount` | — | **Sí — siempre vacío** | | Opcional en `docs/04` §3.9, y sin `currency` no tiene lectura única. Derivable de la línea |
| 11 | `created_by` | — | **Sí — siempre vacío** | | No existe proceso usuario (`D-05`) |
| 12 | `created_at` | — | **Sí — siempre vacío** | | Auditoría técnica: la fija la ingesta (`DT-024`, `D-05`) |
| 13 | `updated_at` | — | **Sí — siempre vacío** | | Ídem |
| 14 | `data_origin` | texto | No | | Constante `SYNTHETIC` |

- **Clave de negocio:** `order_number`, única.
- **Orden de filas:** ascendente por `order_number`, que por §6 coincide con el orden numérico de
  `id`: primero las causales en el orden canónico de `DT-038` §8, y después las `CANCELLED`
  sintéticas, numeradas a continuación (§5.2).
- **Una línea por orden** (`DT-038` §7): no hay consolidación de compras.

## 3. `purchase_order_items.csv` — entidad `PurchaseOrderItem`

| # | Columna | Tipo | Nulo | Clave | Valores y semántica |
|--:|---|---|---|---|---|
| 1 | `id` | entero ≥ 1 | No | PK | Líneas de órdenes causales: asignado por C4. Líneas de órdenes `CANCELLED` sintéticas: asignado por C5, continuando la secuencia (§5.2) |
| 2 | `purchase_order_id` | entero | No | FK + BN | → `purchase_orders.id` |
| 3 | `product_id` | entero | No | FK + BN | → `products.id` |
| 4 | `quantity_ordered` | entero > 0 | No | | `Q_final` (`DT-038` §7). **Nunca 0**, por la guarda de `V1-06` |
| 5 | `quantity_received` | entero ≥ 0 | No | | Acumulado **dentro del periodo**; `≤ quantity_ordered` sin excepción (`V1-12`) |
| 6 | `unit_cost` | decimal, 2 decimales | No | | De la relación `ProductSupplier` preferente y activa |
| 7 | `expected_at` | — | **Sí — siempre vacío** | | `docs/04` §3.10: «si difiere de la cabecera». Con una línea por orden nunca difiere |
| 8 | `data_origin` | texto | No | | Constante `SYNTHETIC` |

- **Clave de negocio:** `(purchase_order_id, product_id)`, única.
- **Orden de filas:** ascendente por `(purchase_order_id, product_id)`.
- **Derivado, no almacenado:** `quantity_pending = quantity_ordered − quantity_received`.
- En una orden `CANCELLED` sintética, `quantity_received = 0` siempre.

## 4. `purchase_order_receipts.csv` — entidad `PurchaseOrderReceipt`

| # | Columna | Tipo | Nulo | Clave | Valores y semántica |
|--:|---|---|---|---|---|
| 1 | `id` | entero ≥ 1 | No | PK | Asignado por C4; es el que referencia el movimiento `RECEIPT` (`DT-038` §5.2) |
| 2 | `purchase_order_item_id` | entero | No | FK + BN | → `purchase_order_items.id` |
| 3 | `received_at` | fecha-hora ISO UTC | No | BN | Día de recepción a `T00:00:00Z` |
| 4 | `quantity_received` | entero > 0 | No | | Cantidad **de esta** recepción |
| 5 | `quality_rejected` | — | **Sí — siempre vacío** | | Nada genera rechazos de calidad; la parcialidad se modela como envío partido (`DT-037`) |
| 6 | `data_origin` | texto | No | | Constante `SYNTHETIC` |

- **Clave de negocio:** `(purchase_order_item_id, received_at)`, única. Es total porque la segunda
  recepción de una entrega partida lleva una demora mínima de un día (`DT-037` §2).
- **Orden de filas:** ascendente por `(purchase_order_item_id, received_at)`.
- Solo existen recepciones con `received_at < end_date` (`DT-038` §9).
- Una orden `CANCELLED` sintética **no tiene ninguna fila aquí**.

## 5. Órdenes `CANCELLED` sintéticas — el único dato no causal

### 5.1 Separación explícita

| | A — Órdenes causales | B — Órdenes `CANCELLED` sintéticas |
|---|---|---|
| Quién las decide | Componente 4, por el disparo de `DT-038` §7 | Componente 5, por la política de §5.2 |
| Por qué existen | Reponen inventario en la simulación | Cubrir §14 de la especificación, que exige órdenes canceladas |
| Efecto en inventario | Recepciones y movimientos | **Ninguno** |
| Tránsito | Sí, mientras están `ISSUED` o `PARTIALLY_RECEIVED` | **Ninguno**: `docs/04` §3.9 limita el tránsito a esos dos estados |
| Recepciones | Sí | **Ninguna** |
| Movimientos | Sí | **Ninguno** |
| Estados posibles | `ISSUED`, `PARTIALLY_RECEIVED`, `RECEIVED` | `CANCELLED` |

**El Componente 5 no cancela ninguna orden causal.** No evalúa condiciones sobre ellas, no cambia su
estado y no las convierte en canceladas. El conjunto B es disjunto del A.

**Neutralidad por construcción, no por cuidado.** Una orden `CANCELLED` no aporta tránsito porque
`docs/04` §3.9 lo dice, y no altera el inventario porque no genera ninguna fila en
`inventory_movements.csv`, que es la fuente de verdad (`DT-038` §5). No hace falta ninguna
comprobación adicional para que el inventario quede intacto.

### 5.2 La política

Vive en `generator/policies.py`, bajo el banner de `DT-039`, con el mismo estatuto que las de
`DT-028`, `DT-035`, `DT-036` y `DT-037`: **parámetro sintético de generación**.

```text
ORDERS_CANCELLED_PERMILLE   = 20     ‰ de las órdenes causales, con suelo de 1
ORDERS_CANCELLED_CLOSE_LAG_DAYS = 1  días entre la emisión y la cancelación
```

**Ambos valores aprobados por el responsable el 2026-09-26** como parámetros sintéticos de cobertura,
apropiados para el entorno de pruebas actual. `20 ‰` es el 2 % de las órdenes causales, **no** una tasa
real de cancelación, ni un requisito empresarial, ni una medición histórica, ni una estimación del
comportamiento de ningún proveedor. `1 día` es el mínimo que evita una orden cancelada en el mismo
instante en que se emite.

**Mecanismo, sin recalcular nada:**

1. **Elegibles.** Una orden causal es elegible si y solo si su **cierre previsto** como cancelada,
   `issued_on + ORDERS_CANCELLED_CLOSE_LAG_DAYS` —hoy `issued_on + 1 día`—, cumple **las dos**
   condiciones siguientes:

   ```text
   cierre_previsto = issued_on + ORDERS_CANCELLED_CLOSE_LAG_DAYS

   elegible =  es orden causal (DT-038 §12)
               AND  cierre_previsto <  end_date
               AND  ( valid_to del producto de su línea IS NULL
                      OR  cierre_previsto <= valid_to )
   ```

   - **`< end_date`** es la condición que ya existía: el cierre ocurre dentro del periodo
     semiabierto `[start_date, end_date)`. La desigualdad es **estricta** y no cambia.
   - **`<= valid_to`** se añade el 2026-09-27 *(cierre de D-01, opción A)*: el cierre ocurre dentro
     de la vigencia del producto, que es un intervalo **cerrado** `[valid_from, valid_to]`
     (`DT-027`). Un cierre **el mismo día** `valid_to` es elegible; uno **posterior** no lo es. En
     particular, una orden emitida **el propio día** `valid_to` nunca es elegible, porque su cierre
     caería en `valid_to + 1 día`. Con `valid_to` nulo la condición se cumple siempre.
   - **Por qué.** Sin esta condición, una gemela cuya plantilla se emitió en `valid_to` se cerraría
     después de la vigencia, y ese cierre sería un evento del producto fuera de su intervalo,
     que la restricción 3 de `DT-027` no admite: su única excepción son las **recepciones** de
     órdenes emitidas en vigencia y sus movimientos `RECEIPT`, es decir, el ciclo logístico de una
     orden en vuelo. **Una cancelación sintética no es ese ciclo y no usa esa excepción**, y
     `DT-027` **no se modifica**.
   - **Es una restricción sintética de elegibilidad**, no una regla de negocio: solo decide qué
     órdenes pueden servir de plantilla. No afecta a las órdenes causales, ni a sus recepciones, ni
     a su cierre por recepción, ni a ningún otro resultado del Componente 4.
   - **Las órdenes que no cumplen no forman parte del universo de selección.** No se seleccionan
     para después rechazarse ni sustituirse: el conjunto de elegibles se calcula **completo y
     antes** de los puntos 2 y 3, y todo lo que sigue opera solo sobre él.
2. **Cuántas.** `K = max(1, ceil(nº de causales × ORDERS_CANCELLED_PERMILLE / 1000))`, acotado por el
   número de elegibles —las que cumplen el punto 1 completo—. **Regla B2** *(decisión del
   2026-09-26)*:

   | Caso | Resultado |
   |---|---|
   | `K > 0` y **cero elegibles** —incluido `N = 0`, donde el suelo da `K = 1`— | **`GeneratorError`**: la ejecución **falla**, **no hay promoción** (`DT-040`) y `output/` queda **intacto** |
   | `K > 0` y `0 < elegibles < K` | Se emiten tantas canceladas como elegibles haya. §14 queda cubierta con una sola |
   | `K > 0` y `elegibles ≥ K` | Se emiten `K` |
   | `K = 0` | **Inalcanzable** con la fórmula vigente: el suelo de uno lo impide. Si la fórmula cambiara, esta regla debería revisarse |

   El Componente 5 calcula `K` y cuenta las elegibles **después** de recibir el resultado del
   Componente 4 y **antes** de crear ninguna fila sintética. A diferencia de la precondición P-6 de
   `DT-035`, que se comprueba sobre la configuración antes de generar nada, esta condición **depende
   del resultado de la simulación** y solo puede evaluarse aquí; por eso su cumplimiento exige la
   publicación por promoción de `DT-040`, y no una simple comprobación previa.
3. **Cuáles.** Una permutación determinista de las elegibles en su orden canónico, tomando las `K`
   primeras. Flujo `cancelled-selection` sobre `sub_seed(seed, "orders")`.
4. **Qué se emite.** Por cada elegida, una orden **gemela** que copia `supplier_id`, `location_id`,
   `product_id`, `quantity_ordered`, `unit_cost`, `issued_at` y **`expected_at`** de su plantilla,
   con `status = CANCELLED`, `closed_at = issued_at + ORDERS_CANCELLED_CLOSE_LAG_DAYS`, su línea con
   `quantity_received = 0` y **ninguna recepción**.

**`closed_at` no se recorta nunca.** No se aplica `min(issued_at + lag, end_date − 1 día)`, ni
`min(issued_at + lag, valid_to)`, ni ninguna otra variante, y `closed_at` no se mueve a `valid_to`:
es siempre `issued_at + ORDERS_CANCELLED_CLOSE_LAG_DAYS`. Las condiciones del punto 1 **no ajustan**
esa fecha; solo deciden qué órdenes pueden ser plantilla. Si ninguna orden es elegible —por
cualquiera de las dos condiciones—, la ejecución falla por B2. Una orden cancelada con
`issued_at == closed_at` **no puede existir**.

**Por qué se copia en lugar de calcular.** La cantidad de una orden cancelada tiene que ser
verosímil, y la única cantidad verosímil disponible es una que el Componente 4 ya calculó. Copiarla
evita que el Componente 5 tenga que recomputar `d̄_recent`, `s` o `Q` —lo que lo convertiría en un
segundo simulador— y evita inventar una cifra. La plantilla no se modifica en absoluto: sigue su
ciclo causal intacto.

**La proporción es sintética, no empresarial.** `ORDERS_CANCELLED_PERMILLE` **no es una tasa de
cancelación de ninguna organización**, no se ha obtenido de ningún dato real y no debe citarse como
información de negocio. Existe para que el dataset contenga al menos un caso de cada situación de
§14, que es lo que la especificación exige.

**Identificadores.** Las órdenes sintéticas **no** pueden entrar en la numeración del Componente 4,
porque se crean después de que esa numeración esté cerrada. El Componente 5 **continúa** la
secuencia:

```text
id de la primera orden sintética   = último id de purchase_orders emitido por C4 + 1
orden de asignación entre ellas    = (issued_on, supplier_id, product_id, location_id)
id de sus líneas                   = último id de purchase_order_items emitido por C4 + 1, en el mismo orden
recepciones                        = ninguna
```

El Componente 5 **no renumera ni reordena nada de lo que recibe**: solo numera las filas que él mismo
crea. Así cada `id` conserva una autoridad única —C4 para lo causal, C5 para lo sintético— y no hay
dependencia circular entre los dos componentes.

Consecuencia visible y deliberada: en `purchase_orders.csv` las órdenes `CANCELLED` ocupan el tramo
final de la numeración, de modo que el orden por `order_number` **no** es cronológico en ese tramo.
Es compatible con `DT-024`, cuya regla es ordenar por la clave de negocio —aquí `order_number`— y
cuyo motivo es que el orden lexicográfico coincida con el numérico, cosa que se sigue cumpliendo.

### 5.3 `DRAFT` no se emite

§14 de la especificación exige órdenes «completamente recibidas; parcialmente recibidas; pendientes;
canceladas». **No exige `DRAFT`**, y ninguna otra sección lo hace. El estado existe en el enum de
`docs/04` §3.9 y el dataset de V1 simplemente no lo ejercita, igual que no ejercita `RETURN` ni
`TRANSFER_IN` en los movimientos. Queda como **limitación declarada de V1**, no como defecto.

## 6. `order_number` — formato determinista

```text
order_number = "PO-" + str(id).zfill(w)

w = max( 6, número de dígitos del id más alto de la ejecución )
```

- **Lo forma el Componente 5, para todas las órdenes** *(decisión A2 del 2026-09-26)*. El ancho `w`
  depende del `id` más alto de la ejecución, que incluye las canceladas; solo el Componente 5 lo
  conoce. Así el Componente 4 no necesita saber nada de la política de cancelaciones.
- El `id` del que se deriva es el asignado según §7 —por el Componente 4 en las causales, por el
  Componente 5 en las canceladas—, de modo que el número **no depende** del orden de iteración de
  ningún diccionario, ni del sistema de archivos, ni de ningún UUID. Formar `order_number` **no
  renumera** ningún `id`.
- El ancho se **ensancha** si la escala lo desborda, con la misma regla y el mismo motivo que
  `DT-028` §4: con relleno fijo de 6 y un millón de órdenes, `PO-1000000` ordenaría antes que
  `PO-999999` y el archivo saldría desordenado sin que nada lo delatara. El ancho es uniforme dentro
  de un dataset.
- Ejemplo: con 1 240 órdenes, `PO-000001` … `PO-001240`.
- Los `order_number` **no son comparables entre datasets** de configuraciones distintas.

## 7. Identificadores

El **Componente 4** asigna los `id` de todo lo causal —órdenes, líneas, recepciones— y de sus tres
entidades de inventario y consumo, en la secuencia y con las claves de ordenamiento de `DT-038` §8.
El **Componente 5** asigna solo los `id` de las filas sintéticas que él mismo crea: las órdenes
`CANCELLED` y sus líneas. Cada `id` tiene una sola autoridad. Se reproduce aquí la parte que afecta al
Componente 5, porque es el punto donde una segunda autoridad rompería el dataset:

| Entidad | Quién asigna | Clave de ordenamiento previa | Primero | Incremento | Desempate final |
|---|---|---|--:|--:|---|
| `purchase_orders` **causales** | **C4** | `(issued_on, supplier_id, product_id, location_id)` | 1 | 1 | La clave es única: una orden por par y día |
| `purchase_orders` **`CANCELLED`** | **C5** | `(issued_on, supplier_id, product_id, location_id)` | último id de C4 + 1 | 1 | Ídem |
| `purchase_order_items` de órdenes causales | **C4** | `(purchase_order_id)` | 1 | 1 | No hace falta: una línea por orden |
| `purchase_order_items` de órdenes `CANCELLED` | **C5** | `(purchase_order_id)` | último id de C4 + 1 | 1 | Ídem |
| `purchase_order_receipts` | **C4** | `(received_on, purchase_order_item_id)` | 1 | 1 | `purchase_order_item_id` |
| `inventory_movements` | **C4** | `(product_id, location_id, occurred_at, rango_de_tipo, reference_id)` | 1 | 1 | `reference_id` |
| `consumption` | **C4** | `(product_id, location_id, occurred_on)` | 1 | 1 | No hace falta: la clave es única |
| `inventory` | **C4** | `(product_id, location_id)` | 1 | 1 | No hace falta: la clave es única |

**El Componente 5 conserva literalmente el identificador que recibe.** No lo recalcula, no lo
renumera y no lo reordena. Solo numera las filas sintéticas que él mismo crea (§5.2), continuando la
secuencia. La misma ejecución con la misma semilla produce exactamente los mismos identificadores.

**Sin dependencia circular.** El grafo de asignación es una cadena: C4 numera órdenes causales →
líneas → recepciones → consumos → movimientos → inventario; C5 numera después, y solo hacia adelante.
Ningún identificador de C4 depende de nada que C5 produzca.

## 8. Relación orden → línea → recepción

```text
purchase_orders.id
      ↑ purchase_order_items.purchase_order_id          (1 : 1 en V1)
purchase_order_items.id
      ↑ purchase_order_receipts.purchase_order_item_id  (1 : 0..2 en V1)
purchase_order_receipts.id
      ↑ inventory_movements.reference_id                (1 : 1, con reference_type = PURCHASE_ORDER_RECEIPT)
```

- **1 : 1** entre orden y línea, porque el disparo es por par producto–ubicación (`DT-038` §7).
- **0, 1 o 2 recepciones** por línea: cero si la orden sigue pendiente al corte o está cancelada,
  una si la entrega fue completa, dos si el proveedor partió el envío (`DT-037` §3). Nunca más de
  dos en V1.
- Invariante: `Σ quantity_received de las recepciones de una línea = purchase_order_items.quantity_received`,
  y ambos `≤ quantity_ordered` (`V1-12`).

## 9. Manifiesto

```text
components[] += { name: "orders", version: ORDERS_VERSION, sub_seed: sub_seed(seed, "orders") }
files[]      += purchase_orders.csv · purchase_order_items.csv · purchase_order_receipts.csv
```

`ORDERS_VERSION` vale `"0.1.0"` y vive en `writer.py`, con el mismo estatuto que las versiones de los
componentes anteriores.

## 10. Convenciones heredadas

Rigen sin cambios las de `DT-024` §Convenciones de archivo y la convención de reloj de `DT-036` §9.
Todas las cantidades son **enteras**; `unit_cost` lleva exactamente **dos decimales**; los campos de
auditoría van **vacíos** (`D-05`).

## 11. Materialización y publicación

El Componente 5 **materializa** sus tres archivos en el directorio que recibe, que es el **workspace
de la ejecución** (`DT-040`), no `output/`. Materializar no es publicar: los archivos que escribe el
Componente 5 solo pasan a formar parte del dataset publicado cuando el orquestador promociona el
workspace entero, después de que la ejecución completa haya terminado bien y pasado la verificación
final.

En particular, si el Componente 5 falla por la regla B2 (§5.2), sus archivos no llegan a escribirse,
no hay promoción, y `output/` conserva intacto el dataset válido anterior, si lo había.

## 12. `GENERATOR_VERSION`

Los dos parámetros de §5.2, igual que cualquier otra constante o literal del generador, están
sujetos a la regla de incremento de `DT-033` (entrada en `docs/15-decisiones-tecnicas.md`): cambiarlos
altera `purchase_orders.csv` y `purchase_order_items.csv` —es decir, el artefacto publicado—, y por
tanto obliga a subir `GENERATOR_VERSION`.

## 13. Implementación *(2026-09-28)*

Implementada en `data/synthetic/generator/orders.py`, con sus pruebas en
`data/synthetic/tests/test_orders.py`. **No cambia ninguna regla de este documento**; esta sección
solo dice dónde vive cada una:

| Regla | Dónde |
|---|---|
| Elegibilidad, §5.2 punto 1 | `is_eligible_for_cancel` y `planned_close`; el universo completo se construye en `_eligible_universe` **antes** de todo lo demás |
| `K`, §5.2 punto 2 | `cancelled_target(N)`, con `N` = número de órdenes **causales**; el tope por elegibles se aplica en `_select_templates` |
| B2 | `_select_templates`: `GeneratorError` si `K > 0` y el universo está vacío, incluido `N = 0` |
| Selección, §5.2 punto 3 | Permutación `cancelled-selection` sobre `sub_seed(seed, "orders")`, aplicada al universo ya filtrado |
| Gemelas, §5.2 punto 4 | `_twins`: copian la plantilla; `closed_on = planned_close(issued_on)`, sin recorte |
| `order_number`, §6 | `order_number_width` y `format_order_number` |
| Constantes | `ORDERS_CANCELLED_PERMILLE = 20` y `ORDERS_CANCELLED_CLOSE_LAG_DAYS = 1`, en `policies.py` bajo el banner de este ADR |

El componente valida la estructura que recibe del Componente 4 —identificadores, orden canónico,
estados, recepciones, cantidades— y **rechaza** con `GeneratorError` una entrada incoherente en
lugar de corregirla: una orden en un estado que el Componente 4 no emite no es una orden causal
(§5.1). Lee `products.csv` solo para obtener `valid_to`. **No está conectado a `__main__`**: los
Componentes 5 y 6 ya están implementados, y la integración y publicación del pipeline completo quedan
pendientes de W1 (`DT-040`). *(Frase corregida el 2026-09-28: decía que el Componente 6 no existía.
Actualización del 2026-09-29: W1 está implementado y el componente se ejecuta dentro de él,
`DT-040` §9.)*

## Alternativas consideradas

| | Alternativa | Ventajas | Inconvenientes |
|---|---|---|---|
| (a) | **C5 materializa; las canceladas se copian de una plantilla causal** | C5 no recalcula nada; la cantidad no se inventa; neutralidad por construcción | Una gemela comparte datos con su plantilla y exige un desempate en la numeración |
| (b) | C4 cancela causalmente algunas órdenes | Todo sería causal | Exigiría una condición de cancelación, es decir una regla de negocio que nadie ha declarado |
| (c) | C5 calcula la cantidad de la cancelada con `V1-06` | No copia nada | C5 necesitaría `d̄_recent`: sería un segundo simulador, lo que la arquitectura prohíbe |
| (d) | No emitir ninguna cancelada | Cero trabajo | Incumple §14 de la especificación, y el Componente 8 lo marcará |
| (e) | Emitir también `DRAFT` | Cubre el enum completo | Ninguna sección lo exige: ampliar el dataset sin necesidad (`CLAUDE.md` §6.2) |

## Razón

**(a).** (b) y (c) rompen, cada una por su lado, la frontera que la arquitectura aprobada fija entre
calcular y materializar. (d) deja el dataset incompleto frente a una exigencia explícita. (e) amplía
sin necesidad. La copia de plantilla es lo único que permite que una orden cancelada tenga una
cantidad verosímil sin que ningún componente recompute nada ni nadie invente una cifra.

## Consecuencias

**Positivas**

1. Los tres archivos del Componente 5 tienen contrato completo, y el Componente 8 tiene contra qué
   validar.
2. `order_number` es determinista y su orden lexicográfico coincide con el numérico.
3. El dataset cubre las cuatro situaciones de órdenes que exige §14.
4. La frontera «C4 calcula, C5 materializa» queda comprobable: basta verificar que las cantidades,
   fechas y estados escritos son idénticos a los recibidos.

**Costos aceptados**

1. Las órdenes `CANCELLED` son el único dato del dataset que no procede del bucle causal. Están
   acotadas, parametrizadas y separadas, pero son la grieta por la que en el futuro podría colarse
   lógica de negocio en el Componente 5. La prueba que lo impide es la que comprueba que el
   Componente 5 no recalcula.
2. `currency` y `total_amount` vacíos: un consumidor que quiera el importe debe multiplicar
   `quantity_ordered × unit_cost` él mismo.
3. `PurchaseOrder.status` es un estado **terminal**, no una serie: una orden cancelada no deja
   rastro del tránsito que tuvo mientras estuvo viva. Es lo que `docs/04` modela.

**Qué invalidaría esta decisión**

Que lleguen órdenes de compra reales, en cuyo caso estos contratos se sustituyen por el esquema de la
Fase 2 y las canceladas sintéticas desaparecen.

## Lo que esta decisión NO hace

- **No** introduce ninguna regla de negocio: `ORDERS_CANCELLED_PERMILLE` es un parámetro sintético de
  generación, no una tasa de cancelación de ninguna organización.
- **No** permite que el Componente 5 recalcule nada, ni que cancele órdenes causales.
- **No** introduce estados que `docs/04` §3.9 no tenga, ni emite `DRAFT`.
- **No** modifica `DT-024`, ni el contrato del Componente 4 (`DT-038`), ni las políticas de `DT-036`
  y `DT-037`.
- **No** modifica `DT-027` ni amplía su excepción de recepciones en vuelo: la condición `<= valid_to`
  del §5.2 (2026-09-27) existe precisamente para que las canceladas sintéticas no la necesiten.
- **No** implementa nada por sí mismo. *(Nota del 2026-09-28: el contrato está implementado en
  `generator/orders.py`, §13.)*
