# DT-028 — Políticas de generación sintética del Componente 2

- **Fecha:** 2026-09-18
- **Estado:** `ACEPTADA`
- **Fase del roadmap:** Fase 1 — Datos (Componente 2: *Catalog Generator*)
- **Afecta a:** `knowledge/dataset-specification.md` §43, el diseño del Componente 2 y el contrato de
  validación del Componente 8
- **Entrada resumida:** `docs/15-decisiones-tecnicas.md` → `DT-028`
- **Relacionada con:** `DT-024` (contrato de salida), `DT-027` (vigencia de `Product`), `DT-029`
  (alcance), `DT-030` (determinismo)

---

> # ⚠ ADVERTENCIA DE LECTURA
>
> **Todos los valores numéricos, conjuntos, rangos, pesos y proporciones de este documento son
> `synthetic generation parameters`: parámetros técnicos del generador de datos sintéticos.**
>
> **NO son políticas comerciales de la organización. NO son costos, MOQ, múltiplos de compra ni
> lead times acordados con ningún proveedor real. NO deben citarse como información empresarial,
> ni usarse para dimensionar, presupuestar o negociar nada.**
>
> Existen con un único fin: permitir que el dataset sintético contenga los escenarios técnicos que
> `knowledge/dataset-specification.md` exige. Su respaldo es §3.5 de esa especificación:
>
> > «Cuando sea necesario utilizar valores para construir escenarios técnicos, estos deben
> > identificarse explícitamente como valores sintéticos de prueba y no como políticas de la
> > organización.»
>
> Los parámetros **empresariales** reales siguen pendientes y están registrados en
> `knowledge/business-rules.md` §3. Ninguno de ellos se fija aquí.

---

## Decisión

El Componente 2 genera las cinco entidades maestras aplicando seis políticas sintéticas
deterministas, definidas en este documento:

| § | Política | Bloqueante que resuelve |
|---|---|---|
| 1 | Valores comerciales de `ProductSupplier` | **B-5** |
| 2 | Asignación producto ↔ proveedor | **B-6** |
| 3 | Distribución ponderada de productos por categoría | **B-7** |
| 4 | Nomenclatura sintética neutra | — |
| 5 | Vocabulario de `unit_of_measure` | — |
| 6 | Vocabulario de `Location.type` | — |

Y una séptima regla transversal sobre estados (§7).

Todas son **deterministas a partir de `DatasetConfig.seed`** (`DT-030`) y **no dependen de ningún
dato real**.

## Contexto

La auditoría del Componente 2 (2026-09-17) verificó que el modelo exige escribir `moq`,
`order_multiple`, `unit_cost` y `agreed_lead_time_days`, y que **ninguna fuente del repositorio
define un valor, un rango ni una regla de generación** para ellos. Lo mismo ocurre con el número de
proveedores por producto, el reparto de productos entre categorías y la proporción de productos
activos e inactivos.

§16 exige además «productos sin MOQ significativo; productos con MOQ; productos con múltiplo de
compra»; §13 exige «variación suficiente entre proveedores y entre órdenes»; y §25 exige que existan
«Múltiples proveedores», «Proveedor preferente», «Producto activo» y «Producto inactivo con
histórico». Sin valores concretos, ninguna de esas exigencias es satisfacible.

**La vía elegida es §3.5**, no la consulta al negocio: estos valores no son políticas empresariales
sino insumos técnicos para construir escenarios de prueba, y la especificación los autoriza
explícitamente siempre que se identifiquen como tales. Este documento es esa identificación.

## Alternativas consideradas

| | Alternativa | Ventajas | Inconvenientes |
|---|---|---|---|
| (a) | **Políticas sintéticas documentadas, fijas en el Componente 2** | Desbloquea el Componente 2 sin esperar al negocio. Los valores quedan en un solo lugar, etiquetados y auditables. §3.5 lo autoriza | Hay que mantener este documento si cambian |
| (b) | Esperar a que el negocio defina MOQ, costos y lead times | No se inventa nada | Bloquea la Fase 1 por tiempo indefinido, y pediría al negocio datos que **no necesita definir**: el dataset es sintético y §37 excluye «costos reales» del alcance |
| (c) | Añadirlos a `DatasetConfig` | Configurables sin tocar código | §32 no los lista entre los parámetros mínimos del generador. Ampliar el contrato de configuración del Componente 1 por un componente que aún no existe es especulación, contra `CLAUDE.md` §6.2 |
| (d) | Valores aleatorios sin rango declarado | Cero trabajo | Produce datos incoherentes (costos negativos, MOQ absurdos) y rompe §3.3 si no van sembrados |

## Razón

Se elige (a) por el argumento de §3.5, y se descarta (b) porque **pediría al negocio una decisión que
el negocio no tiene que tomar**: nadie debe acordar el MOQ de un producto que no existe.

Se descarta (c) por prudencia de alcance, pero con matiz: si al implementar el Componente 2 se
comprueba que estos valores necesitan variar entre ejecuciones, la vía correcta es ampliar
`DatasetConfig` con una sección claramente separada de la configuración de negocio, y registrarlo
como decisión propia. **Hoy no se hace.** Ver §8, *Contrato mínimo de configurabilidad*.

---

## 1. Valores comerciales de `ProductSupplier` (B-5)

`synthetic generation parameters`

Las restricciones estructurales que estos valores deben respetar están en `docs/04` §3.4 y **no se
tocan**: `moq ≥ 0`, `order_multiple ≥ 1`, par (`product_id`, `supplier_id`) único, como máximo un
proveedor preferente activo por producto.

### 1.1 `moq`

Conjunto cerrado de valores admisibles:

```text
MOQ_VALUES = {0, 1, 5, 10, 25, 50, 100, 250}
```

- `0` y `1` representan **«sin MOQ significativo»** (§16, primer caso): el proveedor no impone
  cantidad mínima.
- Los seis restantes representan **«productos con MOQ»** (§16, segundo caso).
- El Componente 2 debe garantizar que **al menos una relación** cae en cada uno de los dos grupos.
- **El testigo del primer grupo debe llevar además `order_multiple = 1`.** Sin esa condición la
  garantía es vacía: una relación con `moq = 1` y `order_multiple = 100` tiene un mínimo pedible
  **real** de 100 unidades —el motor calcula `⌈Q/M⌉·M` (`docs/06` §8)— y por tanto no representa el
  primer caso de §16, por mucho que su columna `moq` valga 1. Corrección de la auditoría de
  consistencia del 2026-09-18.

### 1.2 `order_multiple`

```text
ORDER_MULTIPLE_VALUES = {1, 5, 10, 12, 24, 48, 100}
```

- `1` significa **sin múltiplo efectivo**: cualquier cantidad es pedible.
- `100` cubre el caso límite «múltiplo de compra grande» de §26.
- El Componente 2 debe garantizar al menos una relación con `order_multiple = 1` y al menos una con
  `order_multiple ≥ 48`.

### 1.3 `unit_cost`

```text
UNIT_COST_RANGE = [0.50, 2500.00]   decimal con exactamente 2 decimales
```

Rango amplio deliberadamente, para que el dataset permita después distinguir productos de alto y bajo
valor unitario —insumo de la clasificación ABC derivada (`glossary.md`: ABC «según el valor de
consumo»)— sin que ningún valor concreto signifique nada.

**Sin moneda.** `Supplier.currency` queda vacío (`DT-029`): el costo es un número, no un importe en
una divisa concreta, mientras `docs/04` §8.5 («¿Se requiere multi-moneda?») siga sin responder.

### 1.4 `agreed_lead_time_days`

```text
AGREED_LEAD_TIME_RANGE = [1, 45]   días naturales, entero
```

### 1.5 Cómo se elige un valor concreto

Dentro de cada conjunto o rango, el valor de una relación se obtiene de forma **determinista a partir
de la sub-semilla del Componente 2** (`DT-030`).

Pero las garantías de cobertura de §§1.1, 1.2 y 1.4 **no pueden dejarse a la extracción**: con pocas
relaciones, una extracción uniforme sembrada incumple alguna de ellas con probabilidad apreciable
—con `product_count = 4` hay 7 relaciones y la probabilidad de incumplir al menos una garantía ronda
el 50 %—. El Componente 2 debe por tanto **sembrar primero las relaciones testigo** que cubren cada
caso obligatorio y extraer el resto. La cobertura es una construcción, no un resultado esperado.
Corrección de la auditoría de consistencia del 2026-09-18.

**Mecanismos concretos, registrados al implementar el Componente 2 (2026-09-21).** El ADR exigía la
garantía sin fijar cómo obtenerla. La implementación usa dos, ambos deterministas y ambos dentro de
los conjuntos y rangos ya declarados aquí:

1. **Fijación de testigos.** Tras el sorteo, las tres primeras relaciones **activas** en orden de
   archivo reciben, respectivamente: `moq = 0` con `order_multiple = 1` (§1.1, primer grupo, con la
   condición del múltiplo); el mayor valor de `MOQ_WITH_MINIMUM_VALUES` (§1.1, segundo grupo); y el
   mayor valor de `ORDER_MULTIPLE_VALUES` (§1.2, múltiplo grande). Ningún valor nuevo: los tres salen
   de los conjuntos de §§1.1 y 1.2.
2. **Ajuste de un día.** Para las dos garantías de §1.6 que no se pueden fijar sin introducir un
   número que este documento no contiene —«al menos un lead time que no sea múltiplo de 7» y «dos
   lead times distintos en un producto multi-proveedor»— la implementación **ajusta** en lugar de
   fijar: si la condición no se cumple tras el sorteo, suma un día al valor infractor (resta uno si ya
   está en el máximo). Se mantiene dentro de `[1, 45]` y no incorpora ninguna constante nueva.

Después de ambos, el Componente 2 **reverifica todas las garantías** y falla con error explícito si
alguna no se cumple (§8). La construcción no se da por buena: se comprueba.

### 1.6 Condiciones que el lead time debe cumplir

Tres condiciones que el Componente 2 debe garantizar, todas con respaldo documental:

1. **Variación entre proveedores.** §13: «Debe existir variación suficiente entre proveedores y entre
   órdenes». La parte «entre proveedores» es maestra y se cumple aquí; la parte «entre órdenes» es
   histórica y corresponde a los Componentes 5 y 6.
2. **Al menos un valor que NO sea múltiplo de 7.** §26 lista «lead time que no sea múltiplo de siete
   días» como caso límite obligatorio para pruebas. Es el caso que ejercita la conversión de
   granularidad semanal a días de `DT-019`.
3. **Al menos dos relaciones del mismo producto con lead times distintos**, cuando el producto tenga
   más de un proveedor. Es lo que da contenido al eje `MULTIPLE_LEAD_TIMES` (`DT-023` §7.1).

**El límite inferior es 1, no 0.** El «lead time cero» que §26 pide como caso límite es un lead time
**observado** —una orden recibida el mismo día en que se emite— y se construye con las fechas de
`PurchaseOrder` y `PurchaseOrderReceipt` en los Componentes 5 y 6. Un lead time **acordado** de cero
días no representa nada: nadie contrata una entrega instantánea. Generarlo sería introducir un dato
sin sentido de negocio en una entidad maestra.

### 1.7 Lo que estos valores NO significan

| No significa | Dónde está el dato real |
|---|---|
| Que la organización compre con estos MOQ | `BR-X05`, pendiente |
| Que estos sean costos de compra | `BR-X04` y `ASSUMPTION-017`, pendientes |
| Que los proveedores comprometan estos plazos | Dato real, no disponible |
| Que exista una política de múltiplos de compra | No documentada |
| Que estos rangos acoten los datos reales futuros | §6: el dataset «no debe pretender representar el volumen real» |

---

## 2. Política sintética de asignación producto ↔ proveedor (B-6)

`synthetic generation parameters`

### 2.1 Qué debe quedar representado

| Situación exigida | Fuente | Cómo se cubre |
|---|---|---|
| Productos con un proveedor | §7.4 «uno o varios» | Clase A |
| Productos con múltiples proveedores | **§25 fila 21**, obligatoria | Clases B y C |
| Proveedores con múltiples productos | §7.4 | Rotación de §2.3 |
| Proveedor preferente | **§25 fila 22**, obligatoria | §2.4 |
| Producto sin proveedor **activo** | §26, caso límite | Clase D |
| Variación de lead time entre relaciones | §13 | §1.4 |

### 2.2 Reparto en cuatro clases

Sobre `scale.product_count` productos, con suelo de **un producto por clase**:

| Clase | Descripción | Proporción | Con `product_count = 100` |
|---|---|---|---|
| **A** | 1 proveedor, relación activa | resto | 80 productos |
| **B** | 2 proveedores, ambas relaciones activas | 10 % | 10 productos |
| **C** | 3 proveedores, las tres relaciones activas | 5 % | 5 productos |
| **D** | 1 proveedor, relación **inactiva** (`is_active = false`) | 5 % | 5 productos |

Total de relaciones con la escala vigente: `80·1 + 10·2 + 5·3 + 5·1 = 120`.

**Precondición:** `product_count ≥ 4`. Con menos productos el suelo de una clase por tipo no cabe, y
el Componente 2 debe rechazar la configuración con un error explícito (§8).

### 2.3 Qué proveedor concreto recibe cada relación

**Rotación determinista** sobre la lista de proveedores, comenzando en un desplazamiento derivado de
la sub-semilla del Componente 2 (`DT-030`), avanzando una posición por relación y **saltando al
siguiente si el par (`product_id`, `supplier_id`) ya existe**.

Esta regla, que es de tres líneas, garantiza tres cosas a la vez:

1. el par es único, sin necesidad de reintentos ni de comprobaciones globales;
2. **todo proveedor recibe al menos una relación, siempre que haya al menos tantas relaciones como
   proveedores**; con la escala vigente —120 relaciones sobre 10 proveedores— la rotación los recorre
   doce veces y no queda ningún `Supplier` huérfano;
3. el reparto no depende del orden en que se generen los productos más allá de la semilla.

> **Corrección de la auditoría de consistencia (2026-09-18).** La versión inicial de este ADR afirmaba
> el punto 2 sin condición. Era **falso**: la rotación produce exactamente `R` relaciones, y cada
> relación toca un proveedor, de modo que con `supplier_count > R` quedan `supplier_count − R`
> proveedores sin ninguna fila. Ejemplo que pasaba las tres precondiciones originales:
> `product_count = 4`, `supplier_count = 50` → 7 relaciones y **43 proveedores huérfanos**. Un
> proveedor huérfano no puede aparecer en ninguna orden, y por tanto no tiene lead time observado ni
> puntualidad, que es justo lo que §7.3 y §24 de la especificación exigen poder calcular. De ahí la
> precondición **P-4**.

**Precondiciones:** `supplier_count ≥ 3`, porque la clase C necesita tres proveedores distintos para
un mismo producto; y `supplier_count < R`, siendo `R = n_A + 2·n_B + 3·n_C + n_D` el número total de
relaciones. La desigualdad es **estricta**: con `supplier_count = R` cada proveedor recibiría
exactamente una relación y ninguno tendría varios productos, incumpliendo §7.4. Con la escala vigente
`R = 120`, de modo que `supplier_count` admisible está en `[3, 119]`. Fuera de ese rango, el
Componente 2 debe rechazar la configuración (§8).

### 2.4 Proveedor preferente

- Todo producto de las clases **A, B y C** tiene **exactamente un** `is_preferred = true`.
- Los productos de la clase **D** no tienen ninguno: su única relación está inactiva, y
  `docs/04` §3.4 restringe «como máximo un proveedor preferente **activo** por producto».
- El preferente es **el primer proveedor asignado** al producto por la rotación de §2.3. No hay
  criterio de elección, y eso es deliberado: `BR-X05` (criterio de selección entre proveedores) está
  pendiente y `BR-P07` es solo propuesta. **Este ADR no introduce ninguna lógica de selección ni
  scoring de proveedores**; solo marca una relación para que el campo tenga contenido.

### 2.5 «Producto sin proveedor activo» — forma canónica

La auditoría registró que §26 admite tres materializaciones distintas. Se adopta **una sola**:

> Un producto de la clase **D** tiene exactamente una fila en `product_suppliers.csv`, con
> `is_active = false`.

**Por qué esta y no las otras dos:**

- *Producto con cero filas de `ProductSupplier`*: el ERD lo permite (`PRODUCT ||--o{`), pero pierde
  información. La clase D conserva la evidencia de que la relación existió y se desactivó, que es una
  situación más rica para probar el motor y más parecida a lo que ocurre con datos reales.
- *Proveedor entero inactivo* (`Supplier.is_active = false`): afectaría a **todos** sus productos a
  la vez, mezclando el caso con otros y haciendo el dataset menos controlable.

**Consecuencia para el Componente 8:** la comprobación de §26 es «existe al menos un producto cuyas
relaciones están todas inactivas», no «existe un producto sin relaciones».

**Consecuencia para el Componente 2:** en esta versión **no se generan productos sin ninguna relación
`ProductSupplier`**. El modelo lo permitiría; la política no lo usa.

---

## 3. Distribución ponderada de productos por categoría (B-7)

`synthetic generation parameters`

### 3.1 Por qué no uniforme

Que `scale` fije 100 productos y 10 categorías **no implica 10 productos por categoría**. El YAML
declara totales, no reparto, y ninguna fuente del repositorio establece uno. Un reparto uniforme
sería una regla inventada, y además produciría un catálogo poco representativo: en un catálogo real
unas pocas categorías concentran la mayor parte de los SKU.

**Esto no pretende reproducir la distribución real de la organización**, que se desconoce. Es
variedad sintética.

### 3.2 Algoritmo

Pesos con forma de **Zipf de exponente 1**, repartidos por **mayor resto** y con **suelo de un
producto por categoría**:

```text
w_i = 1 / i                     para i = 1 .. category_count
p_i = w_i / Σ w                 pesos normalizados, Σ p_i = 1   ← validar
n_i = reparto por mayor resto de product_count según p_i
mientras min(n_i) < 1:
    d = índice del máximo n_i         ← se RECALCULA en cada iteración
    n_d -= 1 ;  n_(argmin) += 1
```

**El donante se recalcula en cada transferencia.** No es un detalle: fijar el donante una sola vez al
principio produce un algoritmo distinto que, además, **aborta**. Con `category_count = 10` y
`product_count = 10` el reparto base es `[3,2,1,1,1,1,1,0,0,0]` y hay tres categorías que rellenar;
un donante fijo llega a cero antes de terminar. Recalculándolo, el resultado es `[1]×10`.

Recalcular es además **demostrablemente seguro**: si alguna categoría tiene `n_i = 0` y todas las
demás tuvieran `n_i ≤ 1`, entonces `Σ n_i < category_count ≤ product_count`, lo que contradice que el
reparto sume `product_count`. Luego siempre que hay un cero, el máximo vale al menos 2 y el donante
nunca baja de 1. El bucle termina en a lo sumo `category_count` transferencias.

En caso de empate —dos categorías con el mismo resto, o dos con el mismo `n_i`— **gana el índice
menor**. Con pesos `1/i` no se produce ningún empate que cruce el corte de asignación en el rango
práctico, pero la regla se declara para que el reparto sea función total de `(category_count,
product_count)` y no dependa del orden de iteración de la implementación.

La normalización **debe validarse**: `Σ p_i = 1` exacta. Se calcula con aritmética racional o entera,
nunca comparando flotantes por igualdad.

### 3.3 Resultado con la escala vigente

`category_count = 10`, `product_count = 100`:

| Categoría | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | **Σ** |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Productos | 34 | 17 | 11 | 9 | 7 | 6 | 5 | 4 | 4 | 3 | **100** |

Verificado: la suma es exactamente 100 y el mínimo es 3.

### 3.4 Propiedades

- **Determinista sin aleatoriedad**: el reparto es una función de `category_count` y `product_count`.
  La semilla interviene solo en **qué producto concreto** va a cada categoría, no en cuántos.
- **Ninguna categoría queda vacía**, lo que evita `Category` huérfanas y hace verificable §34.
- **Precondición:** `product_count ≥ category_count`. En caso contrario el suelo es imposible y el
  Componente 2 debe rechazar la configuración (§8).

---

## 4. Nomenclatura sintética (`synthetic generation parameters`)

Patrones neutros, con relleno de ceros a la izquierda y ancho fijo:

| Entidad | Patrón de `code` / `sku` | Ancho | Ejemplos |
|---|---|---|---|
| `Category` | `CAT-NNN` | 3 | `CAT-001` … `CAT-010` |
| `Product` | `SKU-NNNNN` | 5 | `SKU-00001` … `SKU-00100` |
| `Supplier` | `SUP-NNN` | 3 | `SUP-001` … `SUP-010` |
| `Location` | `LOC-NNN` | 3 | `LOC-001` |

`ProductSupplier` **no recibe código propio**: su clave de negocio es el par
(`product_id`, `supplier_id`), y `docs/04` §3.4 no define ningún código adicional.

**`name`** es una etiqueta neutra derivada del código —`Category CAT-001`, `Product SKU-00001`,
`Supplier SUP-001`, `Location LOC-001`— en inglés, por coherencia con `DT-017`.

**Prohibido**, y esta es la razón de ser de la política: nombres que aparenten corresponder a
categorías, productos o proveedores reales. Nada de «Ferretería», «Consumibles», «Distribuidora del
Norte» ni equivalentes. `CLAUDE.md` §7.4 prohíbe rellenar vacíos con datos de negocio inventados, y
un nombre verosímil es exactamente eso: un dato inventado que alguien acabará citando como real.

Si el ancho fijo se queda corto para una escala mayor, se amplía; los identificadores **no** se
reutilizan entre ejecuciones con configuraciones distintas.

**Cómo se amplía, registrado al implementar el Componente 2 (2026-09-21).** El ancho efectivo es
`max(ancho tabulado, dígitos del mayor número)`, calculado por entidad a partir de la escala. No es
un detalle cosmético: `DT-024` ordena las filas por clave de negocio y lo justifica precisamente con
que el relleno a ancho fijo hace coincidir el orden lexicográfico con el numérico. Si el ancho se
desborda, esa equivalencia se rompe —`CAT-1000` ordenaría **antes** que `CAT-999`— y el archivo
saldría desordenado **en silencio**, porque todas las filas seguirían presentes y siendo únicas. Con
`category_count ≤ 999` y `product_count ≤ 99 999` el ancho efectivo es el tabulado, de modo que la
escala vigente no cambia.

---

## 5. Vocabulario de `unit_of_measure` (`synthetic generation parameters`)

Conjunto **cerrado** de tres valores, uno por cada ejemplo de `docs/04` §3.2 —«(pieza, caja, kg…)»—,
expresados en inglés (`DT-017`):

```text
UNIT_OF_MEASURE_VALUES = {EACH, BOX, KG}
```

| Valor | Corresponde a |
|---|---|
| `EACH` | pieza |
| `BOX` | caja |
| `KG` | kilogramo |

- La asignación por producto es **determinista** a partir de la sub-semilla del Componente 2.
- La unidad es **estable por producto** a lo largo de todo el dataset (`ASSUMPTION-016`,
  `docs/04` §5.3), y no cambia nunca una vez asignada.
- **No se crean unidades específicas del negocio.** Tres valores bastan para ejercitar la coherencia
  de unidades; añadir más sería inventar un catálogo de unidades que nadie ha definido.
- Consecuencia para los componentes posteriores: las cantidades de consumo, inventario y órdenes de
  un producto con `KG` podrían ser fraccionarias. `docs/04` §7 lo deja abierto («Cantidades en
  `numeric` si el negocio admite fracciones; en entero si no. Decidir por unidad de medida») y esta
  decisión **no lo resuelve**.

---

## 6. Vocabulario de `Location.type` (`synthetic generation parameters`)

Conjunto **cerrado de un solo valor** en esta versión:

```text
LOCATION_TYPE_VALUES = {MAIN_WAREHOUSE}
```

El alcance vigente es **una ubicación operativa principal** (§6 de la especificación,
`ASSUMPTION-006`, `scale.location_count = 1`). Un vocabulario con un solo valor es la representación
exacta de ese alcance.

**No se define `BRANCH`, `STORE` ni ningún otro tipo.** `docs/04` §3.5 los menciona como ejemplos
(«Almacén central, sucursal, etc.»), pero introducirlos ahora sería diseñar soporte multi-almacén,
que es `DT-P09` y está deliberadamente aplazado. Ampliar este vocabulario es parte de esa decisión
futura, no de esta.

---

## 7. Estados y vigencia — regla transversal

`synthetic generation parameters`

| Entidad | `is_active` | Regla |
|---|---|---|
| `Category` | Todas `true` | Ningún escenario de §25 ni de §26 exige categorías inactivas |
| `Location` | `true` | Una sola ubicación, operativa |
| `Supplier` | Todos `true` | El caso «sin proveedor activo» se materializa en la relación, no en el proveedor (§2.5) |
| `ProductSupplier` | `true`, salvo la clase D | §2.2 |
| `Product` | **5 % `false`**, con suelo de 1 | §25 exige ambos estados (filas 19 y 20) |

### 7.1 Coherencia entre `is_active` y la vigencia de `Product`

Aplicando `DT-027`:

| Producto | `is_active` | `valid_from` | `valid_to` |
|---|---|---|---|
| Activo (95 %) | `true` | `period.start_date` | vacío |
| Inactivo (5 %) | `false` | `period.start_date` | `period.start_date + ⌊0,75 × period.days⌋` |

> **Corrección de la auditoría de consistencia (2026-09-18).** Con `period.days = 1` —una ventana de
> dos fechas consecutivas, que `config.py` acepta sin error— la fórmula da `⌊0,75 × 1⌋ = 0` y por
> tanto `valid_to = valid_from`. Bajo la semántica **corregida** de `DT-027` eso ya es una vigencia
> válida de un día, pero deja al producto «inactivo» sin ningún histórico, incumpliendo §18 («Un
> producto inactivo debe conservar su información histórica»). De ahí la precondición **P-5**.

Con el periodo vigente (2023-01-01 → 2026-01-01, 1096 días), `valid_to` de los inactivos es
**2025-04-02**. Esto deja ~75 % de la ventana con histórico y ~25 % sin él, que es exactamente lo que
§18 pide: «El dataset debe conservar histórico de productos que posteriormente puedan clasificarse
como inactivos».

**Los productos inactivos y los productos de la clase D (sin proveedor activo) son conjuntos
independientes**, elegidos por separado. Solaparlos confundiría dos casos de prueba distintos.

> **Esto no es una política empresarial de altas y bajas de productos.** Cómo se marca un producto
> como descontinuado en el negocio es `BR-P10`, regla **propuesta y no confirmada**. Aquí solo se
> construye el escenario técnico que §25 exige.

### 7.2 Lo que NO se genera en esta versión

- **Productos de histórico corto** (`valid_from` posterior al inicio del periodo). El segmento
  «Nuevo / histórico corto» de `docs/05` §4 existe, pero **no figura en los escenarios mínimos
  obligatorios de §25**. Añadirlo sería ampliar el alcance. Queda registrado como posible ampliación.
- **Productos sin ninguna relación `ProductSupplier`** (§2.5).
- **Categorías, ubicaciones o proveedores inactivos** (§7).

---

## 8. Contrato mínimo de configurabilidad

**En esta versión, ninguno de los parámetros de este documento es configurable**: son constantes del
Componente 2. `DatasetConfig` **no se amplía**.

Justificación: §32 de la especificación lista los parámetros mínimos que el generador debe permitir
controlar, y **ninguno de los de este documento está en esa lista**. Ampliar el contrato de
configuración del Componente 1 por un componente que todavía no existe sería especular.

Si al implementar el Componente 2 se comprueba que alguno necesita variar entre ejecuciones, el
contrato mínimo para hacerlo configurable es:

1. Una sección **propia y claramente separada** en `dataset_config.yaml`, rotulada como parámetros de
   generación sintética y **nunca mezclada** con la sección de negocio que el YAML declara vacía.
2. Un tipo propio en `config.py`, validado como los existentes y con acumulación de errores.
3. Una decisión técnica registrada que la justifique.
4. Pruebas por cada invariante nueva.

Mientras tanto, **el valor efectivo de estos parámetros queda registrado en `manifest.json`** a
través de `components[].version` (`DT-025`): dos datasets generados con versiones distintas del
Componente 2 pueden haber usado políticas distintas, y el manifiesto lo dice.

### Precondiciones que el Componente 2 debe verificar

Las **cinco** surgen de este documento y **no de `DatasetConfig`**. El Componente 2 las comprueba al
arrancar y **falla con un error explícito** si no se cumplen; nunca genera un dataset degradado en
silencio. A ellas se suma, desde `DT-029`, el rechazo de `location_count > 1`.

| # | Precondición | Origen |
|---|---|---|
| P-1 | `product_count ≥ category_count` | §3.2, suelo de un producto por categoría |
| P-2 | `product_count ≥ 4` | §2.2, suelo de un producto por clase |
| P-3 | `supplier_count ≥ 3` | §2.3, la clase C necesita tres proveedores distintos |
| **P-4** | `supplier_count < R`, con `R = n_A + 2·n_B + 3·n_C + n_D` | §2.3, evitar proveedores huérfanos y garantizar que alguno tenga varios productos |
| **P-5** | `period.days ≥ 2` | §7.1, que un producto inactivo conserve histórico |

Las tres primeras se declararon al aprobar este ADR; **P-4 y P-5 las añadió la auditoría de
consistencia del 2026-09-18**, que encontró configuraciones que pasaban las tres originales y aun así
producían un dataset inválido. Con la configuración vigente (`product_count = 100`,
`supplier_count = 10`, `category_count = 10`, `period.days = 1096`) las cinco se cumplen.

**No se añaden a `config.py`.** Son restricciones de esta versión del Componente 2, no del contrato
de configuración: una configuración con 2 productos es válida como configuración y simplemente no la
puede atender este generador. Registrar la restricción donde vive la limitación es lo correcto.

---

## Consecuencias

**Positivas**

1. B-5, B-6 y B-7 quedan resueltos, y el Componente 2 puede implementarse sin inventar nada sobre la
   marcha.
2. Todos los valores están en **un solo documento**, etiquetados. Si mañana el negocio aporta datos
   reales, se sabe exactamente qué sustituir.
3. Las políticas hacen verificables ocho escenarios obligatorios de §25 y tres casos límite de §26.
4. Cero cambios de código en esta tarea.

**Costos aceptados**

1. Estos valores **se verán** en el dataset y alguien podría citarlos fuera de contexto. Mitigado con
   la advertencia de cabecera y con `data_origin = SYNTHETIC` en cada fila (`DT-026`).
2. Las políticas son constantes del código: cambiarlas exige tocar el Componente 2 y volver a generar.
   Es aceptable mientras el dataset sea uno solo.
3. Las tres precondiciones hacen que algunas configuraciones válidas no sean atendibles. Es preferible
   a generar un dataset que incumple §25 sin avisar.

**Qué invalidaría esta decisión**

- Que el negocio aporte datos reales de MOQ, costos o lead times: entonces estas políticas dejan de
  usarse para esos campos, y `ASSUMPTION-001` se cierra.
- Que `DT-P12` decida ampliar §25, lo que podría exigir escenarios maestros nuevos.
- Que se confirme `DT-P09` (multi-ubicación): el vocabulario de §6 tendría que ampliarse.

## Lo que esta decisión NO hace

- **No** fija ninguna política empresarial. Ni nivel de servicio, ni umbrales, ni criterio de
  selección de proveedor, ni política de compra, ni tolerancia de sobre-recepción.
- **No** introduce lógica de selección de proveedor ni scoring: `BR-X05` sigue pendiente y `BR-P07`
  sigue siendo propuesta.
- **No** asigna escenarios a SKU concretos: eso es el Componente 7 (`DT-023`).
- **No** implementa nada. El Componente 2 **no está implementado**.
- **No** modifica `config.py`, `dataset_config.yaml` ni las pruebas.
- **No** resuelve `DT-P09`, `DT-P11`, `DT-P12`, `BR-P10`, `BR-X03`, `BR-X04`, `BR-X05` ni `BR-X08`.
