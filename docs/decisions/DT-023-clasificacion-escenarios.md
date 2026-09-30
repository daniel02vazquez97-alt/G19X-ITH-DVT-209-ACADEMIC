# DT-023 — Clasificación en tres niveles de las situaciones de `dataset-specification.md` §25

- **Fecha:** 2026-09-17
- **Estado:** `ACEPTADA`
- **Fase del roadmap:** Fase 1 — Datos (Componente 1: `DatasetConfig`)
- **Afecta a:** `data/synthetic/config/config.py`, `data/synthetic/config/dataset_config.yaml`,
  y el diseño de los Componentes 2, 7 (asignación de escenarios) y 8 (validador del dataset)
- **Entrada resumida:** `docs/15-decisiones-tecnicas.md` → `DT-023`

> Este ADR vive como archivo propio, y no como entrada en el registro, porque incluye la matriz
> completa de las 26 situaciones de §25. `docs/decisions/ADR-template.md` contempla justamente ese
> caso: *«o añadir la entrada directamente en `docs/15-decisiones-tecnicas.md` si es una decisión
> breve»*. Esta no lo es.

---

## Decisión

Las **26 situaciones mínimas obligatorias** de `knowledge/dataset-specification.md` §25 **no son
26 valores del enum `Scenario`**. Se reparten en tres niveles, cada uno con un responsable distinto:

| Nivel | Qué es | Dónde vive | Quién lo produce o lo comprueba |
|---|---|---|---|
| **A — Ejes de generación** | Comportamientos que el generador produce deliberadamente y que se asignan a un SKU o a una relación producto–proveedor | Enum `Scenario` + `scenarios.required` | Generador (Componentes 2–7) |
| **B — Atributos y estados** | Campos del modelo de datos que deben tomar valores variados | Entidades de `docs/04-modelo-datos.md` | Generador, al poblar las entidades |
| **C — Propiedades emergentes** | Situaciones que surgen de combinar varias entidades, y que dependen de reglas todavía pendientes | Ninguna etiqueta: se verifican sobre el dataset ya generado | **Validador del dataset (Componente 8)** |

Como consecuencia de esta clasificación se autorizó ampliar el enum de **14 a 16 valores**, añadiendo
`LOW_INVENTORY` y `PARTIAL_DELIVERY` (§§5 y 6 de este documento).

**Dos cifras que no deben confundirse.** El enum `Scenario` contiene **16 valores**. De ellos, **13
corresponden directamente a situaciones enumeradas en §25**; los otros **tres** —`HIGH_ROTATION`,
`LOW_ROTATION` y `MULTIPLE_LEAD_TIMES`— permanecen como ejes del generador respaldados por otras
secciones de la especificación y de la documentación (§7 de este documento). Las **26 situaciones de
§25**, por su parte, se reparten en **13 de Nivel A, 9 de Nivel B y 4 de Nivel C**. «26» cuenta
situaciones de la especificación; «16» cuenta valores del enum. No son la misma magnitud: no deben
sumarse entre sí ni usarse una para verificar la otra.

## Contexto

La instrucción de inicio de la Fase 1 enumeró catorce escenarios. Una auditoría posterior detectó que
§25 de la especificación exige veintiséis situaciones mínimas obligatorias, de las cuales quince no
tenían representación en el enum. La pregunta a resolver era si el enum estaba incompleto o si ambas
listas describían cosas distintas.

## Alternativas consideradas

| | Alternativa | Ventajas | Inconvenientes |
|---|---|---|---|
| (a) | Ampliar `Scenario` a 26 valores, uno por fila de §25 | Correspondencia literal con la especificación; un solo lugar que consultar | **Obliga al generador a etiquetar situaciones cuya definición es una regla de negocio pendiente.** Mezcla comportamientos, atributos, estados y propiedades derivadas en una sola dimensión. Hace imposible validar cobertura: un SKU etiquetado `MOQ` no dice nada comprobable |
| (b) | Dejar el enum en 14 y verificar §25 en otro lugar | Cambio nulo | Deja fuera dos ejes que §25 sí exige y que el generador **sí** puede producir deliberadamente (§10.2 y §12.3) |
| (c) | **Tres niveles: A en el enum, B en el modelo, C en el validador** | Cada situación vive donde puede producirse o comprobarse; no se fija ninguna regla pendiente; el validador tiene un contrato claro | Exige mantener la correspondencia documentada — esta matriz |
| (d) | No hacer nada y decidirlo al implementar el Componente 7 | Aplaza el trabajo | La ambigüedad se propagaría a los Componentes 2 y 8, que se diseñan antes |

## Razón

La especificación **ya usa tres niveles**; §25 es una tabla-resumen heterogénea que los mezcla. Cuatro
pruebas tomadas del propio documento:

1. **§32** enumera lo que el generador debe controlar y lo agrupa en familias — «proporción de
   productos por comportamiento de demanda», «escenarios de proveedores», «escenarios de stockout»,
   «escenarios de inventario», «escenarios de compras» — no como una lista plana de veintiséis.
2. **§35** pide en el reporte de calidad, como ítems **separados**, «distribución de escenarios» **y**
   «cantidad de productos por patrón de demanda». En el vocabulario del documento, escenario y patrón
   de demanda no son lo mismo.
3. **§26 y §25 describen las mismas situaciones con distinta intención.** No hay coincidencia
   textual, pero sí correspondencia conceptual:

   | §25 (situación obligatoria) | §26 (caso límite para pruebas) |
   |---|---|
   | «MOQ» | «MOQ superior a la necesidad» |
   | «Producto inactivo con histórico» | «producto inactivo» |
   | «Tránsito total suficiente / efectivo insuficiente» | «tránsito total superior al punto de reorden pero tránsito efectivo insuficiente» |

   Las expresiones de la columna derecha **solo figuran en §26**. §26 las llama *casos límite para
   pruebas*: propiedades a verificar sobre los datos, no etiquetas de configuración. Que la misma
   situación aparezca en una sección como «obligatoria» y en otra como «caso de prueba» es
   precisamente el indicio de que no es un valor de configuración.
4. **Cuatro situaciones dependen de reglas pendientes.** §11 remite a `DT-P11` para el corte del
   tránsito efectivo; §17 dice que «la clasificación del resultado como sobreinventario dependerá de
   las políticas y umbrales empresariales, que permanecen pendientes» (`BR-X03`); §18 remite a
   `BR-P10`; §9 dice que «el dataset no debe asumir todavía cuál será el tratamiento definitivo»
   (`DT-011`). Convertirlas en valores de `Scenario` obligaría al generador a fijar esas reglas —
   exactamente lo que §3.5, §27 y §37 prohíben.

El argumento decisivo es el cuarto. **Una etiqueta obliga a decidir.** Si el generador tuviera que
marcar un SKU como `TRANSIT_EFFECTIVE_INSUFFICIENT`, tendría que saber qué cuenta como «efectivo», y
eso es precisamente la decisión que `DT-P11` mantiene abierta.

---

## Matriz de cobertura de §25

Las 26 situaciones, transcritas literalmente de la tabla de §25, con su nivel y su representación.

### Nivel A — Ejes de generación (13 de las 26)

Se declaran en `scenarios.required` y son valores del enum `Scenario`.

| # | Situación §25 | Sección | Valor de `Scenario` |
|---|---|---|---|
| 1 | Demanda estable | §8.1 | `STABLE_DEMAND` |
| 2 | Demanda creciente | §8.2 | `GROWING_DEMAND` |
| 3 | Demanda decreciente | §8.3 | `DECLINING_DEMAND` |
| 4 | Demanda estacional | §8.4 | `SEASONAL_DEMAND` |
| 5 | Demanda intermitente | §8.5 | `INTERMITTENT_DEMAND` |
| 6 | Demanda errática | §8.6 | `ERRATIC_DEMAND` |
| 7 | Stockout | §9, §10.3 | `STOCKOUT` |
| 9 | Inventario bajo | §10.2 | **`LOW_INVENTORY`** *(añadido)* |
| 10 | Sobreinventario | §10.4 | `OVERSTOCK` |
| 11 | Inventario en tránsito | §10.5, §14 | `IN_TRANSIT` |
| 13 | Proveedor confiable | §12.1 | `RELIABLE_SUPPLIER` |
| 14 | Proveedor con retrasos | §12.2 | `DELAYED_SUPPLIER` |
| 15 | Entregas parciales | §12.3 | **`PARTIAL_DELIVERY`** *(añadido)* |

*(Trece filas: las situaciones 1–7, 9–11 y 13–15 de §25. La numeración no es consecutiva porque
los huecos —8 y 12— son situaciones de Nivel C, y las situaciones 16–26 se reparten entre los
Niveles B y C.)*

De estas trece, once ya estaban en el enum de catorce valores; las dos restantes —`LOW_INVENTORY`
(situación 9) y `PARTIAL_DELIVERY` (situación 15)— son las que esta decisión añadió.

Además de estos trece valores, el enum contiene **tres** que no corresponden a ninguna fila de §25:
`HIGH_ROTATION`, `LOW_ROTATION` y `MULTIPLE_LEAD_TIMES`. Están respaldados por otras secciones de la
documentación y se justifican en **§7 de este documento**; 13 + 3 = 16, el tamaño del enum.

### Nivel B — Atributos y estados (9 de las 26)

Se representan mediante campos de las entidades de `docs/04-modelo-datos.md`. El generador los
produce dándoles valores variados; **no llevan etiqueta**.

| # | Situación §25 | Sección | Representación en el modelo de datos |
|---|---|---|---|
| 16 | MOQ | §16, §7.4 | `ProductSupplier.moq` |
| 17 | Múltiplo de compra | §16, §7.4 | `ProductSupplier.order_multiple` |
| 19 | Producto activo | §18, §7.2 | `Product.is_active = true` |
| 21 | Múltiples proveedores | §7.4 | Cardinalidad de `ProductSupplier` para un mismo producto |
| 22 | Proveedor preferente | §7.4 | `ProductSupplier.is_preferred` |
| 23 | Órdenes pendientes | §14 | `PurchaseOrder.status ∈ {ISSUED, PARTIALLY_RECEIVED}` |
| 24 | Órdenes recibidas | §14 | `PurchaseOrder.status = RECEIVED` |
| 25 | Órdenes parcialmente recibidas | §14 | `PurchaseOrder.status = PARTIALLY_RECEIVED` |
| 26 | Corrección mediante nuevo movimiento | §7.6, §22 | `InventoryMovement.movement_type = ADJUSTMENT`, nunca editando el movimiento original (`DT-006`) |

§16 lo dice sin ambigüedad: «La aplicación definitiva de las restricciones corresponde al motor de
abastecimiento y **no al generador de datos**». §7.4 lista MOQ, múltiplo de compra y el indicador de
proveedor preferente como **campos** de la entidad.

> **Las situaciones de §25 no son mutuamente excluyentes.** La tabla enumera situaciones que el
> dataset debe contener, no una partición de los datos. Un mismo registro puede satisfacer varias a
> la vez, y hay al menos un caso de **inclusión estricta**: la situación 25 («órdenes parcialmente
> recibidas», `status = PARTIALLY_RECEIVED`) está contenida en la situación 23 («órdenes
> pendientes», `status ∈ {ISSUED, PARTIALLY_RECEIVED}`). Toda orden que cubra la 25 cubre también la
> 23. Esto no altera el recuento —cada fila de §25 se clasifica una sola vez— pero sí significa que
> el validador (Componente 8) no puede comprobar la cobertura contando registros disjuntos.

### Nivel C — Propiedades emergentes (4 de las 26)

Surgen de combinar varias entidades. **No se etiquetan.** El **validador del dataset (Componente 8)**
es responsable de comprobar que existen.

| # | Situación §25 | Sección | Entidades a combinar | Regla pendiente que impide etiquetarla |
|---|---|---|---|---|
| 8 | Demanda censurada | §9 | `Consumption.is_stockout_affected` + `Inventory` | `DT-011` — tratamiento de la demanda censurada |
| 12 | **Tránsito total suficiente / efectivo insuficiente** | **§11** | `PurchaseOrder` + `PurchaseOrderItem` + `PurchaseOrderReceipt` + fechas + `Inventory` + lead time + ROP | **`DT-P11`** — criterio de corte del tránsito efectivo |
| 18 | Conflicto MOQ / sobreinventario | §17 | `ProductSupplier` + `Consumption` + `Inventory` | `BR-X03` — umbrales de clasificación de riesgo |
| 20 | Producto inactivo con histórico | §18 | `Product.is_active = false` + `Consumption` + `InventoryMovement` + `PurchaseOrder` | `BR-P10` — tratamiento de productos descontinuados |
| — | *(Inventario saludable, §10.1)* | §10.1 | `Inventory` + demanda prevista | No figura en §25; se anota por completitud |

*(Cuatro situaciones de §25: 8, 12, 18 y 20. La última fila de la tabla —inventario saludable,
§10.1— **no es** una situación de §25: se anota por completitud y no entra en el recuento.)*

**Recuento de las 26 situaciones de §25:**

| Nivel | Situaciones de §25 | Cuáles |
|---|---|---|
| A — Ejes de generación | **13** | 1–7, 9, 10, 11, 13, 14, 15 |
| B — Atributos y estados | **9** | 16, 17, 19, 21, 22, 23, 24, 25, 26 |
| C — Propiedades emergentes | **4** | 8, 12, 18, 20 |
| **Total** | **26** | ✓ |

13 + 9 + 4 = 26. La situación 15 («entregas parciales») se clasificó como Nivel A; ver §6.

**El tamaño del enum es otra cifra.** El enum `Scenario` tiene **16** valores: los 13 de Nivel A más
los tres ejes de §7 que no son filas de §25. 26 y 16 cuentan cosas distintas y no deben compararse.

---

## 5. Por qué `LOW_INVENTORY` pertenece al Nivel A

§10.2 define «inventario bajo» como *«Existencias cercanas a los niveles donde una reposición puede ser
necesaria»*. Es una **condición del inventario que el generador puede producir deliberadamente**:
basta simular un nivel de existencias bajo respecto del consumo del SKU.

No requiere ninguna regla pendiente. En particular, **no exige conocer el punto de reorden**: la
definición citada no dice «por debajo del ROP», y «cercanas» es una relación con el consumo del SKU
que el generador puede construir sin la política de inventario.

Distinguirlo de `STOCKOUT` importa: el stockout es el fallo consumado; el inventario bajo es el
estado **previo**, y es justamente el que permitirá probar que el motor recomienda **antes** de que
falte producto.

## 6. Por qué `PARTIAL_DELIVERY` se trata como Nivel A

Es el único de los seis casos auditados donde ambas lecturas eran defendibles, y la elección se apoya
en el título de la sección de origen.

§12.3 se titula **«Proveedor con entregas parciales»** y la sitúa entre los *escenarios de
proveedores*, junto a «proveedor confiable» y «proveedor con retrasos» — que ya son ejes de Nivel A.
Describe, por tanto, un **comportamiento del proveedor**, no solo un estado de una orden.

Es además un comportamiento **distinto** de `DELAYED_SUPPLIER`: el retraso es un déficit en **tiempo**
(la recepción llega tarde) y la entrega parcial es un déficit en **cantidad** (`cantidad recibida <
cantidad ordenada`). Un proveedor puede incurrir en uno, en otro o en ambos.

La consecuencia en los datos —`PurchaseOrder.status = PARTIALLY_RECEIVED`— es de Nivel B, y ambas
cosas conviven sin contradicción: el **eje** dice qué comportamiento simular para ese proveedor; el
**estado** es la huella que ese comportamiento deja en la orden.

§12.3 cierra recordando que «la tolerancia definitiva para sobre-recepción continúa pendiente mediante
`BR-X08`» y que «el dataset no debe establecer una política empresarial sobre cuánto exceso puede
recibirse». El eje simula el déficit; **no** fija tolerancia alguna.

## 7. Los tres valores del enum que no son filas de §25

De los 16 valores del enum, 13 corresponden a situaciones de §25 (Nivel A, arriba). Los otros tres
—`HIGH_ROTATION`, `LOW_ROTATION` y `MULTIPLE_LEAD_TIMES`— son ejes del generador respaldados por
otras secciones. Ninguno es una invención, pero su situación no es la misma en los tres casos.

### 7.1 `MULTIPLE_LEAD_TIMES` — exigido por la especificación, aunque no como fila de §25

No aparece en la tabla de §25, pero **§13 lo exige de forma explícita**: «Debe existir variación
suficiente entre proveedores y entre órdenes para permitir posteriormente calcular: promedio;
desviación; desviación respecto al acordado; porcentaje de entregas puntuales». **§14** lo confirma
al pedir que las órdenes se registren «con diferentes lead times observados».

Es, por tanto, un eje que el generador debe producir deliberadamente. Cubre una **relación
estructural** (producto–proveedor, y orden a orden) más que un comportamiento de un SKU aislado, y no
depende de ninguna regla de negocio pendiente. **No hay aquí discrepancia que resolver**: §25 no lo
lista porque §25 enumera situaciones, y la variación de lead time es un requisito de distribución de
los datos, enunciado en su propia sección.

### 7.2 `HIGH_ROTATION` y `LOW_ROTATION` — discrepancia documentada, no resuelta

Estos dos sí constituyen una discrepancia. Están en el enum, **no** figuran como filas de la tabla
§25 y tampoco se exigen en una sección propia como el caso anterior. No son una invención: el resto
de la documentación los respalda.

| Dónde aparecen | Cómo |
|---|---|
| `docs/02-propuesta-tecnica.md` §8 | «alta y baja rotación» encabeza la lista de escenarios del dataset sintético |
| `project/roadmap.md`, Fase 1 | «productos de alta y baja rotación» es la primera actividad de diseño del dataset |
| `knowledge/dataset-specification.md` **§10.4** | cita «baja rotación» como una de las causas con las que el sobreinventario debe poder relacionarse |
| `knowledge/glossary.md` | define «rotación» como término de dominio |

La discrepancia es, por tanto, que **§25 no recoge un eje que la propia especificación usa en §10.4**.

**No se ha modificado §25.** Determinar si la tabla debe ampliarse es una decisión sobre la
especificación, no sobre el Componente 1. Queda registrada como **`DT-P12`** y sigue abierta:

- **Opción 1** — añadir dos filas a §25 («Alta rotación», «Baja rotación») por completitud.
- **Opción 2** — dejar constancia en §25 de que la tabla no pretende ser exhaustiva respecto de los
  ejes de demanda, y que §8 y §10.4 la complementan.

## 8. Consecuencias

**Positivas**

1. Ninguna regla de negocio pendiente queda fijada por la vía indirecta de una etiqueta.
2. El **Componente 8 (validador)** tiene un contrato claro: comprobar las **cuatro** propiedades de
   Nivel C (situaciones 8, 12, 18 y 20) sobre el dataset generado, además de las validaciones de §34.
3. El **Componente 7 (asignación de escenarios)** sabe exactamente qué puede asignar: los 16 valores
   del enum `Scenario` —los 13 de Nivel A más los tres de §7—, y nada más.
4. El enum sigue siendo un conjunto cerrado y pequeño, verificable con pruebas exactas.

**Costos aceptados**

1. La correspondencia entre §25 y los tres niveles hay que mantenerla: **es esta matriz**. Si §25
   cambia, este documento cambia con ella.
2. Alguien que lea solo `dataset_config.yaml` podría creer que los 16 valores del enum son todo lo que el dataset
   debe contener. Mitigado con una nota explícita en el YAML y en el docstring de `Scenario`.

**Qué invalidaría esta decisión**

Que se cierren `DT-P11`, `BR-X03`, `BR-P10` y `DT-011`. Con esas cuatro reglas definidas, las
situaciones de Nivel C **pasarían a ser etiquetables** y cabría reconsiderar si conviene promoverlas a
ejes de Nivel A. No antes.

## 9. Lo que esta decisión NO hace

- **No** modifica `knowledge/dataset-specification.md`. §25 queda tal cual.
- **No** introduce ningún parámetro de negocio: ni nivel de servicio, ni stock de seguridad, ni punto
  de reorden, ni periodo de revisión, ni cobertura objetivo, ni `z`, ni costos, ni umbrales de riesgo,
  ni criterios de selección de proveedor, ni criterio de tránsito efectivo.
- **No** resuelve `DT-P11`, `BR-X03`, `BR-P10`, `DT-011` ni `BR-X08`. Las cuatro primeras son
  justamente la razón de que el Nivel C exista.
- **No** decide si §25 debe ampliarse con las dos filas de rotación (§7).
- **No** implementa ningún componente del generador.
