# DT-037 — Comportamiento sintético de proveedores (Componente 6)

- **Fecha:** 2026-09-24 · **Corregida:** 2026-09-24, tras la auditoría pre-implementación: se retiran
  los cinco flujos por proveedor que no extraían nada, se fija el mecanismo de asignación, se tipa la
  estructura y se unifica el nombre `split_range`. **Ningún valor aprobado cambia.** · **Enmendada:**
  2026-09-26, decisión **D-C4-1 (opción O1)**: la fórmula de la entrega parcial de §3 acota `q1` a
  `Q_final − 1` para que `q2` no pueda ser cero. **Ningún valor aprobado cambia.** · **Implementada:**
  2026-09-28 en `data/synthetic/generator/supplier_behaviour.py` (§6); ninguna regla cambia
- **Estado:** `ACEPTADA`
- **Fase del roadmap:** Fase 1 — Datos (Componente 6: *Supplier Behaviour Generator*), con efecto en
  los Componentes 4, 5 y 8
- **Afecta a:** `knowledge/dataset-specification.md` §§12, 13 y 14, el diseño de los Componentes 4 y
  6 y el contrato de validación del Componente 8
- **Entrada resumida:** `docs/15-decisiones-tecnicas.md` → `DT-037`
- **Relacionada con:** `DT-028` (políticas del Componente 2, cuyo patrón este documento reproduce),
  `DT-030` (sub-semillas e identificadores canónicos), `DT-031` (`V1-09`, `V1-09.2`, `V1-12`),
  `DT-032` (algoritmo pseudoaleatorio), `DT-035` (dos ejes ortogonales, patrón reutilizado aquí),
  `DT-036` (políticas de inventario, que consume estos perfiles)

---

> # ⚠ ADVERTENCIA DE LECTURA
>
> **Todos los valores numéricos, proporciones, rangos y probabilidades de este documento son
> `synthetic generation parameters`: parámetros técnicos del generador de datos sintéticos.**
>
> **NO son niveles de servicio, ni acuerdos comerciales, ni tasas de cumplimiento, ni
> características de ningún proveedor real. NO son requisitos de PluriOne, ni reglas de negocio, ni
> políticas de inventario, ni parámetros del motor real, ni supuestos sobre proveedores reales. NO
> deben citarse como información empresarial ni usarse para evaluar, calificar ni negociar con
> ningún proveedor.**
>
> Su respaldo es §3.5 de la especificación, el mismo que ampara `DT-028`, `DT-035` y `DT-036`.

---

## Decisión

El Componente 6 genera **perfiles de comportamiento por proveedor**: parámetros deterministas que
describen con qué puntualidad y con qué integridad entrega. Viven en
`data/synthetic/generator/policies.py` bajo su propio banner, y el componente los materializa en
`data/synthetic/generator/supplier_behaviour.py`.

### 1. Qué es y qué no es el Componente 6

**C6 no escribe ningún archivo.** Un `supplier_behaviour.csv` sería metadata de generación alojada
en una entidad de negocio, que §42.1 prohíbe expresamente: «La información adicional de generación
no debe confundirse con información empresarial». Además, el efecto observable del perfil —las
fechas y las cantidades de cada recepción— ya queda registrado en las órdenes y las recepciones que
escribe el Componente 5, de modo que persistir la etiqueta sería duplicar la causa del hecho junto
al hecho.

C6 **sí** figura en `manifest.json`, en el campo `components`, con su nombre, su versión y su
sub-semilla, como exige §44 y `DT-025`. Es un componente que contribuye con cero archivos.

**C6 no conoce ninguna orden.** No sabe cuántas hay, ni de qué producto, ni de qué fecha. Entrega
parámetros por proveedor y termina. **C4 es quien aplica esos parámetros a órdenes concretas**,
porque la decisión de si *esta* entrega llega tarde depende de *esta* orden, que solo C4 conoce.

Esa frontera es lo que impide que C6 acabe simulando. C6 **no** genera órdenes, recepciones,
movimientos, tránsito ni inventario.

### 2. Dos ejes ortogonales

Mismo patrón que `DT-035`: no una lista de comportamientos, sino dos ejes independientes que se
combinan. Un proveedor puede ser puntual y partir envíos.

**Eje 1 — Puntualidad**

| Perfil | `on_time_permille` | `delay_days` | Mezcla |
|---|--:|---|--:|
| `PUNCTUAL` | 900 | 1 a 3 | 40 % |
| `IRREGULAR` | 650 | 1 a 7 | 40 % |
| `LATE` | 250 | 3 a 14 | 20 % |

`on_time_permille` es la probabilidad, en por mil, de que la recepción ocurra en la fecha esperada.
En caso contrario se sortea un retraso en el rango indicado, en días naturales.

**Eje 2 — Integridad**

| Perfil | `partial_permille` | `split_range` | `completion_lag_days` | Mezcla |
|---|--:|---|---|--:|
| `COMPLETE` | 0 | — | — | 70 % |
| `SPLIT` | 250 | 400 a 800 | 1 a 10 | 30 % |

`partial_permille` es la probabilidad, por orden, de que la entrega se parta en dos recepciones.
`split_range` es el rango, **en por mil**, de la cuota que se lleva la **primera** recepción; el
resto va en la segunda. `completion_lag_days` es la demora de la segunda respecto de la primera,
siempre ≥ 1 día.

**Nombres canónicos, para que no haya dos.** El campo del rango de la partición se llama
`split_range` en todos los documentos *(una versión anterior de este ADR lo llamaba
`split_permille`, nombre que sugería un escalar cuando es un rango; queda retirado)*. Los valores no
cambian.

Las dos mezclas suman 100 % y se reparten con el mecanismo de mayor resto y suelo de uno de
`DT-028` §3.2. Con los 10 proveedores del catálogo vigente el reparto es exacto: 4 / 4 / 2 y 7 / 3.
**La cobertura de `RELIABLE_SUPPLIER`, `DELAYED_SUPPLIER` y `PARTIAL_DELIVERY` es por tanto una
construcción del reparto, no una probabilidad.**

**Precondición P-C6-1:** `supplier_count ≥ 3`. Con menos proveedores el suelo de uno del eje de
puntualidad no puede cumplirse, y la generación falla explícitamente en lugar de producir un dataset
que incumple §12 sin avisar. Es el mismo criterio que la precondición P-6 de `DT-035`.

### 3. Cómo se materializa el comportamiento

C6 entrega a C4 una estructura congelada por proveedor, **con tipos explícitos**:

| Campo | Tipo | Valores | Semántica |
|---|---|---|---|
| `supplier_id` | entero | → `suppliers.id` | **Clave, única**: un perfil por proveedor |
| `punctuality` | texto | `PUNCTUAL` \| `IRREGULAR` \| `LATE` | Perfil del eje 1 |
| `integrity` | texto | `COMPLETE` \| `SPLIT` | Perfil del eje 2 |
| `on_time_permille` | entero | 0 … 1000 | Probabilidad, por mil, de llegar en la fecha esperada |
| `delay_days` | `(entero, entero)` | mínimo ≥ 1 | Rango del retraso cuando no llega a tiempo |
| `partial_permille` | entero | 0 … 1000 | Probabilidad, por orden, de partir la entrega |
| `split_range` | `(entero, entero)` \| **nulo** | 0 … 1000 | Cuota por mil de la primera recepción. **Nulo** en `COMPLETE` |
| `completion_lag_days` | `(entero, entero)` \| **nulo** | mínimo ≥ 1 | Demora de la segunda recepción. **Nulo** en `COMPLETE` |

Los dos campos que la tabla del eje 2 marca con «—» son **nulos** en `COMPLETE`, no cero ni campo
omitido: con `partial_permille = 0` la rama nunca se ejecuta, y un valor nulo lo hace evidente en
lugar de dejar un número que nadie usa.

La colección se entrega ordenada por `supplier_id` ascendente. C6 **no escribe ningún archivo**: la
estructura vive en memoria y solo el Componente 4 la consume.

C4, al emitir una orden, calcula `expected_at = issued_at + agreed_lead_time_days` y aplica el
perfil del proveedor:

```text
puntualidad   below(1000) < on_time_permille  →  llega en expected_at
              en caso contrario               →  expected_at + between(delay_days[0], delay_days[1])

integridad    below(1000) < partial_permille  y  Q_final ≥ 2
              →  split = between(split_range[0], split_range[1])
                 q1 = min( Q_final − 1, max(1, ceil(Q_final × split / 1000)) )
                 q2 = Q_final − q1
                 segunda recepción en la fecha de la primera
                     + between(completion_lag_days[0], completion_lag_days[1])
              en caso contrario → una sola recepción de Q_final
```

`q1 + q2 = Q_final` **exactamente**, por construcción: la segunda cantidad es el resto, no un segundo
sorteo. Con ello `Σ recibido ≤ ordenado` se cumple siempre y `V1-12` (sin sobre-recepción) no puede
violarse por redondeo. Y, para todo `Q_final ≥ 2`, **`1 ≤ q1 ≤ Q_final − 1` y `1 ≤ q2 ≤ Q_final − 1`**:
las dos recepciones de una entrega partida tienen al menos una unidad. El faltante de una entrega
parcial **siempre** tiene su segunda recepción programada; si esa fecha cae después del corte del
periodo, la orden queda `PARTIALLY_RECEIVED` con su saldo pendiente visible, nunca desaparecido.

> **Enmienda del 2026-09-26 — decisión D-C4-1, opción O1.** La versión anterior de esta sección decía
> `q1 = max(1, ceil(Q_final × split / 1000))`, sin cota superior. Con `split_range` de hasta 800 ‰ esa
> fórmula da `q2 = 0` para órdenes pequeñas —`Q_final = 2, 3, 4` con `split = 800` dan `q1 = 2, 3, 4`
> y `q2 = 0`—, es decir una «segunda recepción» de cero unidades, que el contrato de recepción excluye
> (`quantity > 0` en `DT-038` §12 y en `DT-039`) y que contradice la propia definición de entrega
> partida. El término `min(Q_final − 1, …)` es la corrección mínima: **no cambia ningún valor
> aprobado** (`partial_permille`, `split_range`, `completion_lag_days`) y no altera el resultado cuando
> la cota no se activa —en particular, para todo `Q_final ≥ 5` dentro de `split_range = 400 … 800`—.
> Con el catálogo vigente ninguna ventana producía todavía `Q_final` de 2, 3 o 4: el defecto era
> latente. La notación `delay_min`, `delay_max`, `lag_min`, `lag_max` de la versión anterior se
> sustituye por los nombres de campo de la tabla de arriba; el significado no cambia.

### 4. Determinismo

Sub-semilla propia, derivada del **identificador canónico** del componente y no de su posición en el
pipeline, como exige `DT-030`:

```text
sub_seed(seed, "supplier_behaviour")
```

**Dos flujos, y solo dos**, ambos de asignación:

| Flujo | Qué hace |
|---|---|
| `punctuality-assignment` | Permutación determinista de los proveedores para repartir los cupos del eje 1 |
| `integrity-assignment` | Permutación determinista independiente para el eje 2 |

**Mecanismo de asignación.** Los cupos se calculan con el reparto de mayor resto y suelo de uno de
`DT-028` §3.2; **a qué proveedor concreto le toca cada perfil lo decide una permutación sembrada**
sobre `suppliers.csv` ordenado por `id` ascendente, exactamente como el Componente 3 asigna formas de
demanda a productos. Sin esa frase, el reparto 4/4/2 sería el mismo pero la identidad de cada
proveedor no, y el dataset dejaría de ser reproducible.

Se genera **un perfil por fila de `suppliers.csv`**, con independencia de `is_active`: un proveedor
inactivo no recibirá órdenes, pero tener su perfil calculado mantiene la asignación estable si su
estado cambia en otra configuración.

**Los parámetros de cada perfil son constantes, no sorteos** *(decisión del 2026-09-24)*. Una versión
anterior de este ADR declaraba además cinco flujos por proveedor —`on-time-rate:{supplier_id}`,
`delay-range:{supplier_id}`, `partial-rate:{supplier_id}`, `split-range:{supplier_id}`,
`completion-lag:{supplier_id}`— que **no extraían nada**, porque las tablas de la sección 2 dan esos
valores como constantes del perfil. **Los cinco flujos quedan retirados.** No se crean rangos nuevos
y no se reabre ninguno de los valores aprobados.

> **De dónde viene la heterogeneidad en V1: de la pertenencia a un perfil, no de sortear tasas
> individuales dentro de un mismo perfil.** Dos proveedores del mismo perfil se comportan con los
> mismos parámetros; lo que los distingue es qué órdenes concretas les tocan, y eso lo decide el
> Componente 4.

Los sorteos por orden que aplica C4 usan flujos **de C4**, etiquetados por par producto–ubicación,
no por orden: así un cambio en un producto no desplaza la secuencia de los demás.

Todo en **aritmética entera**: probabilidades por mil y rangos con extracciones uniformes. `DT-032`
prohíbe los flotantes, y ninguno aparece aquí.

### 5. Limitaciones conocidas de V1

Las dos siguientes son **`LIMITACIÓN CONOCIDA DE V1`**, declaradas y aprobadas el 2026-09-24. **No
son defectos** y no deben reportarse como tales en ninguna auditoría del dataset.

**O-1 — No se generan entregas anticipadas.** Con estos parámetros, el lead time observado es
siempre mayor o igual que el acordado: un proveedor puntual entrega en la fecha esperada, nunca
antes. §13 de la especificación pide poder calcular «desviación respecto al acordado», y esa
desviación existe, pero es unilateralmente positiva. Introducir entregas anticipadas cambiaría el
comportamiento de cuatro de los diez proveedores y con él todo el inventario del dataset; **no se
hace**.

**O-2 — `LEAD_TIME_CAPPED` no se ejercita.** El máximo alcanzable del lead time observado es
`44 + 14 = 58` días con el catálogo vigente: 44 es el mayor `agreed_lead_time_days` **entre las
relaciones preferentes y activas**, que son las únicas que emiten órdenes, y 14 el retraso máximo de
`LATE`. Con el tope de la política de `DT-028` §1.4 —`[1, 45]`— la cota superior teórica sería 59.
Queda
por debajo del techo `LT_MAX_v1 = 90` de `V1-09.2`, de modo que el dataset **no contendrá ningún
caso** que active esa marca de trazabilidad. Ejercitarla exigiría un proveedor con retrasos de más de
46 días —un proveedor patológico que nadie ha pedido—, y **no se introduce**.

De O-2 se sigue una comprobación útil que sí se hizo: con un observado máximo de 58 días y
`R_v1 = 7`, el horizonte de cobertura de `V1-03` llega a 65 días ≈ 9,3 semanas, **dentro** de las
8–12 semanas de `ASSUMPTION-002`. Estos parámetros no introducen ninguna incoherencia nueva con el
horizonte de pronóstico.

**O-3 — La cobertura se mide sobre productos, no sobre proveedores.** El reparto garantiza que
existan proveedores de los cinco perfiles, pero no cuántos SKU sirve cada uno. Si el proveedor `LATE`
resulta servir pocos productos, `DELAYED_SUPPLIER` quedará representado por pocos casos. Las métricas
del Componente 4 deben contar **productos afectados**, no proveedores etiquetados. Es una exigencia
sobre la medición, no sobre los parámetros.

### 6. Implementación *(2026-09-28)*

Implementada en `data/synthetic/generator/supplier_behaviour.py`, con sus pruebas en
`data/synthetic/tests/test_supplier_behaviour.py`. **No cambia ninguna regla de este documento**;
esta sección solo dice dónde vive cada una y registra las dos decisiones de implementación aprobadas
por el responsable el 2026-09-28:

| Regla | Dónde |
|---|---|
| Valores de §2 y precondición P-C6-1 | `policies.py`, banner de `DT-037` |
| Reparto de §2 (mayor resto, suelo de uno) | El mismo auxiliar de `policies.py` que usan los Componentes 3 y 4 |
| Asignación de §4 | `build_supplier_profiles`: dos permutaciones, `punctuality-assignment` e `integrity-assignment`, sobre `sub_seed(seed, "supplier_behaviour")`, aplicadas a los proveedores ordenados por `id`, igual que el Componente 3 |
| Estructura de §3 | Tupla de `SupplierProfile`, ordenada por `supplier_id` |

- **Decisión A1 — manifiesto.** El componente **no escribe ningún archivo de datos**; su única traza
  persistente es su propia entrada en `manifest.components` (nombre, `SUPPLIER_BEHAVIOUR_VERSION =
  "0.1.0"` y sub-semilla), que añade él mismo con `extend_manifest` y sin tocar `files`.
- **Decisión A2 — tipo.** `SupplierProfile` sigue declarado en `generator/inventory.py`, donde lo
  declaró el Componente 4 como contrato que consume. El Componente 6 importa **solo ese tipo**; no
  llama a ninguna función del Componente 4.

**No está conectado a `__main__`**: la ejecución `C2 → C3 → C6 → C4 → C5` se conecta con la
publicación atómica de `DT-040` (W1), que no está implementada. *(Actualización del 2026-09-29: W1
está implementado y el componente se ejecuta dentro de él, `DT-040` §9.)*

## Contexto

§12 de la especificación describe tres comportamientos de proveedor —confiable, con retrasos, con
entregas parciales— de forma **puramente cualitativa**: «lead times observados cercanos al
comportamiento esperado», «pocas desviaciones», «recepciones posteriores a las fechas esperadas»,
«cantidad recibida < cantidad ordenada». No contiene un solo número. §13 exige variación suficiente
entre proveedores y entre órdenes para poder calcular promedio, desviación y porcentaje de entregas
puntuales, sin decir cuánta.

`DT-028` §1.4 pobló `agreed_lead_time_days` en el rango [1, 45], que es el lead time **acordado**.
El observado no existe todavía: nace de las recepciones, que nacen de estos perfiles.

Sin estos parámetros, el Componente 6 no es implementable y el Componente 4 no puede fechar ninguna
recepción.

## Alternativas consideradas

| | Alternativa | Ventajas | Inconvenientes |
|---|---|---|---|
| (a) | **Perfiles sintéticos documentados, dos ejes ortogonales** | Precedente de `DT-035`; cobertura por construcción; C6 queda disjunto de C4 | Los valores son constantes del código |
| (b) | Un único eje con cinco perfiles combinados | Una sola tabla | Multiplica los perfiles y hace imposible un proveedor puntual que parte envíos. `DT-035` ya descartó esta forma por el mismo motivo |
| (c) | Que C6 escriba `supplier_behaviour.csv` | El perfil quedaría inspeccionable | §42.1 lo prohíbe: es metadata de generación en una entidad de negocio. Y duplicaría la causa junto al hecho |
| (d) | Que C6 genere directamente las recepciones | Menos componentes | C6 tendría que conocer las órdenes, que son de C4. Sería una segunda simulación, prohibida por la arquitectura aprobada |
| (e) | Derivar el comportamiento de un atributo real del proveedor | Sin parámetros nuevos | `suppliers.csv` no tiene ningún atributo de comportamiento, y añadirlo sería inventar una calificación de proveedor que el negocio no ha definido |

## Razón

**(a)**, por §3.5 y por el precedente inmediato de `DT-035`, que resolvió el mismo problema —ocho
comportamientos cualitativos sin números— con dos ejes y mezclas con suelo de uno.

La elección de los valores persigue que el comportamiento sea **falsable midiendo el dataset**: la
tasa de puntualidad separa los tres perfiles por más de 250 ‰ en cada salto, los rangos de retraso no
se solapan en su extremo superior, y la parcialidad afecta a una minoría clara de órdenes. Un
generador que produjera retrasos indistinguibles bajo tres nombres pasaría una comprobación de
etiquetas y fallaría cualquier prueba de comportamiento.

**(c)** y **(d)** se descartan por razones documentales y arquitectónicas, no de conveniencia.

## Consecuencias

**Positivas**

1. El Componente 6 es implementable, y es pequeño: entrega una tupla de perfiles y nada más.
2. C4 y C6 quedan disjuntos: C6 no conoce órdenes y C4 no decide comportamientos.
3. Los escenarios `RELIABLE_SUPPLIER`, `DELAYED_SUPPLIER` y `PARTIAL_DELIVERY` quedan cubiertos por
   construcción del reparto.
4. El lead time **observado** pasa a existir y a ser distinto del acordado, que es lo que §13 y
   `V1-09` necesitan para tener sentido.

**Costos aceptados**

1. Los perfiles no se persisten: para saber por qué una orden llegó tarde hay que mirar las fechas,
   no una etiqueta.
2. Cambiar cualquiera de estos valores regenera todas las fechas de recepción y con ellas el
   inventario entero. No es un ajuste marginal, y obliga a subir `GENERATOR_VERSION` (`DT-036` §8).
3. Las tres limitaciones de la sección 5.

**Qué invalidaría esta decisión**

Que lleguen datos reales de recepciones, en cuyo caso estos perfiles dejan de usarse. O que el
negocio defina una calificación de proveedores (`SupplierPerformance`, `docs/04` §3.17), que no
cambiaría el generador pero sí daría un referente contra el que contrastar estos rangos.

## Lo que esta decisión NO hace

- **No** establece ningún nivel de servicio, acuerdo comercial ni calificación de proveedor.
- **No** describe a ningún proveedor real, ni de PluriOne ni de nadie.
- **No** escribe archivos, ni entidades, ni columnas.
- **No** genera órdenes, recepciones, movimientos, tránsito ni inventario: todo eso es del
  Componente 4.
- **No** decide el contrato de `purchase_order_receipts.csv`, que escribe el Componente 5.
- **No** modifica `V1-09` ni su techo `LT_MAX_v1 = 90`: lo deja sin ejercitar, y lo declara.
- **No** implementa nada por sí mismo. *(Nota del 2026-09-28: el contrato está implementado en
  `generator/supplier_behaviour.py`, §6.)*
