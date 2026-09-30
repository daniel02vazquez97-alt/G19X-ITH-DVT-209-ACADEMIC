# DT-036 — Políticas sintéticas de inventario y reabastecimiento (Componente 4)

- **Fecha:** 2026-09-24 · **Corregida:** 2026-09-24, tras la auditoría pre-implementación (§§1, 3, 4,
  9, 10 y la versión destino de §8). Las correcciones están señaladas en el punto donde aplican.
- **Estado:** `ACEPTADA`
- **Fase del roadmap:** Fase 1 — Datos (Componente 4: *Inventory Simulator*), con efecto en los
  Componentes 5 y 8
- **Afecta a:** `docs/04-modelo-datos.md` §§3.6–3.11, `knowledge/dataset-specification.md` §§10, 11,
  14, 20, 34 y 41.3, el diseño de los Componentes 4 y 5 y el contrato de validación del Componente 8
- **Entrada resumida:** `docs/15-decisiones-tecnicas.md` → `DT-036`
- **Relacionada con:** `DT-024` (contrato de salida), `DT-025` (manifiesto), `DT-027` (vigencia de
  `Product`, enmendada por esta decisión), `DT-028` (políticas del Componente 2, cuyo patrón este
  documento reproduce), `DT-030` (sub-semillas), `DT-031` (`V1-06`, `V1-12`, `V1-13`), `DT-032`
  (algoritmo pseudoaleatorio), `DT-033` (versionado), `DT-034` (demanda latente frente a consumo),
  `DT-037` (comportamiento sintético de proveedores), **`DT-038`** (contrato de salida del
  Componente 4: columnas, identificadores, orden diario y corte), **`DT-039`** (contrato de salida
  del Componente 5)

---

> # ⚠ ADVERTENCIA DE LECTURA
>
> **Todos los valores numéricos, fórmulas, umbrales, ventanas y factores de este documento son
> `synthetic generation parameters`: parámetros técnicos del generador de datos sintéticos.**
>
> **NO son políticas de inventario, ni puntos de reorden, ni stock de seguridad, ni niveles de
> servicio, ni cantidades recomendadas de ninguna organización. NO deben citarse como información
> empresarial ni usarse para dimensionar, presupuestar, comprar ni negociar nada.**
>
> En particular, y de forma inequívoca:
>
> ```text
> s ≠ ROP                     (punto de reorden del motor real)
> Q ≠ recommendation          (cantidad recomendada del motor real)
> C ≠ target_coverage_days    (horizonte de cobertura, InventoryPolicy)
> d̄_recent ≠ forecast         (no hay pronóstico en el generador)
> ```
>
> Su respaldo es §3.5 de la especificación:
>
> > «Cuando sea necesario utilizar valores para construir escenarios técnicos, estos deben
> > identificarse explícitamente como valores sintéticos de prueba y no como políticas de la
> > organización.»
>
> Es exactamente el mismo estatuto que tienen los MOQ y los costos de `DT-028` y los niveles de
> demanda de `DT-035`.

---

## Decisión

El Componente 4 simula el ciclo causal completo del inventario —existencia, disparo, orden, lead
time, recepción, movimiento, existencia— aplicando las políticas de este documento. Viven en
`data/synthetic/generator/policies.py`, junto a las de los Componentes 2 y 3 y bajo su propio banner.

**No entran en `dataset_config.yaml` ni en `manifest.config`.** Ese archivo declara en su cabecera
que no contiene parámetros de negocio, y el Componente 1 está cerrado. La consecuencia de esa
elección se cierra en la sección 8 de este documento.

### 1. Inventario inicial

Cada par producto–ubicación empieza el periodo con una existencia dimensionada a partir de su propia
demanda y del lead time acordado de su proveedor:

```text
on_hand_base(i) = ceil( d̄_i × (L_i + M) )
on_hand(i)      = ceil( on_hand_base(i) × factor_perfil(i) )
```

donde:

| Símbolo | Significado | Valor |
|---|---|---|
| `d̄_i` | Demanda media diaria del **par producto–ubicación** en la ventana inicial | Calculada sobre `demand.csv` |
| `W` | Ancho de la ventana de demanda, en días | **28** |
| `L_i` | `agreed_lead_time_days` de la relación proveedor aplicable | Del catálogo; entre las relaciones preferentes y activas de hoy, de 1 a 44 |
| `M` | Margen sintético añadido al lead time, en días | **7** |
| `factor_perfil(i)` | Factor del perfil de apertura | 750 / 1000 / 1500 **por mil** |

`d̄_i` es la media de la demanda de los **primeros `W` días vigentes del par**, no de toda la serie.

**Unidad de cálculo: el par `(product_id, location_id)`, nunca el producto aislado.** Queda explícito
aunque la configuración vigente tenga `location_count: 1`; la fórmula debe ser correcta para varias
ubicaciones sin reescribirse.

**`d̄_i` es un racional exacto:** `suma_demanda / número_de_días`. **No se redondea la media antes de
aplicar el `ceil`.** La fracción se conserva hasta el único punto de redondeo que la fórmula
especifica, y ningún flotante interviene en decidir una cantidad entera (`DT-032`). El precedente
está en `policies.py`, que ya usa `Fraction` por este mismo motivo en `DT-028`.

Con la escala vigente, la media de los primeros 28 días va de **0,43 a 73,89** unidades/día —la media
del periodo completo, que es otra magnitud, va de 0,66 a 70,39—, de modo que las existencias
iniciales varían en casi dos órdenes de magnitud entre productos: eso es deliberado y es lo que
produce heterogeneidad sin asignar escenarios a mano.

### 2. Perfiles de apertura

Tres perfiles, repartidos por una mezcla que suma 100 % con suelo de un producto por clase, con el
mismo mecanismo de mayor resto que `DT-028` §3.2 y `DT-035`:

| Perfil | Factor | Mezcla |
|---|--:|--:|
| `AJUSTADO` | 750 ‰ | 30 % |
| `NORMAL` | 1000 ‰ | 40 % |
| `HOLGADO` | 1500 ‰ | 30 % |

La asignación es **determinista**, por permutación sembrada, y **no** se apoya en `abc_class` ni en
`rotation_class`: ambas columnas están vacías en los 100 productos del catálogo vigente, porque
`DT-029` las deja derivadas del consumo, que no existía cuando se generó el catálogo. `V1-11`
mantiene además que V1 no diferencia por clase ABC.

**Los factores se almacenan como enteros por mil —750, 1000, 1500— y se aplican con
`ceil(base × permille / 1000)`.** `DT-032` prohíbe los flotantes en el generador: escribir `0.75`
introduciría el redondeo binario que `DT-028` ya evita con `Fraction`. La representación es exacta
para los tres valores; los valores aprobados no cambian.

### 3. Umbral sintético de reposición

```text
disparo:  on_hand_después_del_consumo(t) + quantity_in_transit(t)  ≤  s(t)
s(t)    = ceil( d̄_recent(t) × L_i )
```

**El disparo se evalúa después del consumo del día**, en el paso 5 del orden causal que fija
`DT-038` §3. El `on_hand` de la desigualdad es el de cierre del día, no el de apertura.

**`quantity_in_transit` es el nombre canónico** del modelo (`docs/04` §3.6, `docs/06` §4.2): el
tránsito total, es decir `Σ (quantity_ordered − quantity_received)` sobre las líneas de órdenes en
estado `ISSUED` o `PARTIALLY_RECEIVED`. *Una versión anterior de este ADR lo llamaba
`inventory_on_order`; ese nombre queda retirado y no crea ninguna entidad ni ningún campo nuevo.*

`s` es un **umbral sintético de simulación**. Existe para que el generador emita órdenes en momentos
plausibles y el histórico contenga tránsito, recepciones, desabastos y sobreinventario. **No es un
punto de reorden**: no lleva stock de seguridad, no incorpora incertidumbre, no usa pronóstico, no
depende de ningún nivel de servicio y no produce ninguna recomendación. La sección 7 desarrolla la
separación.

### 4. Cantidad sintética del pedido

```text
raw_need = Q = ceil( d̄_recent(t) × C )          C = 21 días

si raw_need ≤ 0:  NO HAY ORDEN                  ← guarda obligatoria de V1-06
Q_moq    = max( raw_need, MOQ )
Q_final  = ceil( Q_moq / order_multiple ) × order_multiple
```

Estas tres últimas líneas son **`V1-06` completa**, incluida su primera línea. *(Corrección del
2026-09-24: la primera versión de este ADR reproducía solo las dos últimas y afirmaba que eran
«exactamente `V1-06`». La guarda faltaba, y sin ella el caso degenerado quedaba sin regla.)*

**La guarda es obligatoria y precede a todo cálculo de `Q_final`.** Consecuencias exigidas:

- `d̄_recent = 0` **no** produce ninguna orden. Con la configuración vigente hay **9 pares** que
  alcanzan ese estado —productos 18, 22, 24, 30, 66, 68, 69, 75 y 100—, verificado sobre `demand.csv`.
- No se emite una orden repetida cada día cuando `s = 0`.
- **Nunca** se genera `quantity_ordered = 0`, que violaría `docs/04` §3.10.
- **No** se introduce un mínimo artificial de una unidad.
- **No** se cambia el operador `≤` del disparo por esta causa: la guarda actúa sobre la cantidad, no
  sobre el disparo.

Se cita `V1-06` por **coherencia de datos, no por adopción de una regla del motor**: `moq` y
`order_multiple` son atributos de la relación `ProductSupplier`, es decir hechos del catálogo, y §21
de la especificación exige que las cantidades del dataset sean coherentes con ellos. Un generador que
los incumpliera produciría órdenes imposibles.

Consecuencia conocida y **deliberadamente no corregida**: seis productos del catálogo vigente
—ids 21, 17, 34, 52, 55 y 75— tienen una cantidad mínima pedible que cubre entre 99 y 248 días de su
demanda. Eso genera sobreinventario permanente en ellos. Es el conflicto MOQ/sobreinventario que §17
de la especificación pide **representar**, apareciendo por sí solo; corregirlo destruiría el
escenario.

### 5. Ventana de demanda reciente y warm-up

```text
a(t)          = max( primer_día_vigente, t − W )
d̄_recent(t)   = media de la demanda en [ a(t), a(t) + W )
```

La ventana mide **siempre** exactamente `W = 28` días. Durante los primeros 28 días de vida del
producto queda congelada en sus primeros 28 días; a partir de ahí se desplaza. Las dos ramas
**coinciden exactamente** en `t = primer_día + W`, de modo que la función es continua y no hay caso
especial.

**Declaración explícita de dependencia de información posterior.** Durante esos primeros `W` días,
`d̄_recent` depende de demanda posterior a `t`. Es deliberado y coherente con la sección 1, que ya
dimensiona la existencia de apertura del día 1 con los días 1 a 28: **el warm-up no abre un canal
nuevo, prolonga de forma continua el que la sección 1 ya abre.**

Alcance exacto del efecto sobre el dataset:

| Afectado | No afectado |
|---|---|
| Primeros `W` días de la serie de cada producto | El resto del periodo |
| Eventos de orden, tránsito y existencia de esa ventana | `demand.csv`, que C4 no toca |
| | `consumption.csv`, que se deriva de la demanda y de la existencia del día |

**Esto es una característica del generador sintético, no una fuga de información de un modelo.** La
demanda y el consumo generados **no deben interpretarse como afectados por leakage**. Lo que sí
procede es una precaución de uso, registrada en `docs/05-motor-predictivo.md` §5.5: excluir los
primeros `W` días del entrenamiento cuando se utilicen features derivadas de órdenes, inventario,
tránsito o abastecimiento. Esa nota es una precaución sobre el dataset sintético; **no es una regla
de negocio ni un requisito de ML nuevo**.

### 6. Productos sin proveedor activo

Cinco productos del catálogo vigente —ids **3, 20, 57, 71 y 74**— no tienen ninguna relación
`ProductSupplier` activa y preferente. Cada uno tiene exactamente una relación con
`is_preferred = false` e `is_active = false`.

**Regla del generador sintético:**

> Para dimensionar **exclusivamente** el saldo de apertura de un producto sin relación proveedor
> activa y preferente, `L_i` se obtiene del `agreed_lead_time_days` de una relación existente, aunque
> esté inactiva y no sea preferente. Si hay varias y ninguna es activa+preferente, se usa la de
> `supplier_id` menor. Si no existe ninguna relación, la generación **falla explícitamente** por
> precondición; no se inventa un lead time por defecto.

Queda **prohibido** usar esa relación para generar órdenes, seleccionar proveedor, activar
abastecimiento, crear o reactivar una relación, simular compras o calcular lead time observado.
`V1-10` (elección de proveedor) queda intacta porque para estos productos nunca se emite una orden.

Comportamiento resultante, que es el caso límite de §26 de la especificación: reciben saldo de
apertura, generan demanda, consumen, entran en desabasto cuando se agotan, **no** generan órdenes,
**no** generan recepciones y permanecen en cero. Sin proveedor ficticio, sin orden ficticia y sin
evitar artificialmente el desabasto.

Esta regla es del **generador sintético** y **no** del motor real de abastecimiento. Queda además
registrada como `ASSUMPTION-025`.

### 7. Saldo de apertura: `INITIAL_INVENTORY` / `OPENING_BALANCE`

El inventario inicial se materializa como un movimiento, porque `inventory.csv` debe ser
reconstruible desde `inventory_movements.csv` y esa reconstrucción no puede partir de un saldo que no
esté registrado en ninguna parte.

```text
movement_type   = ADJUSTMENT
reference_type  = INITIAL_INVENTORY
reference_id    = (vacío)
reason_code     = OPENING_BALANCE
quantity        = saldo inicial, positivo
occurred_at     = primer día vigente del producto, 00:00:00Z
```

El saldo de apertura **no es una recepción**, **no proviene de una orden de compra**, **no genera
una orden de compra**, **no es `SCRAP`** y **no debe confundirse con una operación real de
abastecimiento**. Representa exclusivamente el estado inicial del periodo simulado.

`ADJUSTMENT` y `reason_code` son valores que `docs/04` §3.7 y la especificación §7.6 ya definen: no
se introduce ningún tipo nuevo. **La etiqueta va en `reason_code` y no en `reference_id`** porque
`reference_id` conserva la semántica de identificador de documento origen —numérico— y ponerle una
etiqueta de texto rompería la comprobación de integridad referencial de §34.

### 8. `GENERATOR_VERSION`

> **La regla de incremento es la de `DT-033`** (entrada en `docs/15-decisiones-tecnicas.md`, regla
> operativa del 2026-09-26): se incrementa `GENERATOR_VERSION` cuando un cambio en el generador
> —en cualquier módulo, parámetro o literal— altera el **artefacto publicado** de al menos una
> configuración aceptada antes y después del cambio. **La versión depende del artefacto, no del
> archivo donde vive el parámetro.**

*Versión anterior de esta sección:* enumeraba los parámetros afectados —`W`, `M`, `C`, los factores
y la mezcla de perfiles, y los parámetros del Componente 6—. **La enumeración queda retirada**: dejaba
fuera los parámetros de los Componentes 2, 3 y 5, y todo lo que no vive en `policies.py`. Los
parámetros de este ADR están cubiertos por la regla general igual que antes: cambiarlos altera el
artefacto.

No es una recomendación de higiene. `DT-033` define

```text
dataset_version = "ds-" + sha256( config canónica + "|" + generator_version )[:12]
```

Como estos parámetros **no** viven en la configuración, son el único término del dataset que no entra
en ese hash por la vía de `config`. Si cambiaran sin mover `generator_version`, dos datasets distintos
compartirían `dataset_version` y el identificador dejaría de identificar. `DT-033` ya define
`generator_version` como la versión de la **salida observable**, y estos parámetros la determinan:
la regla es la consecuencia, no una excepción.

**Versión destino de la incorporación de C6, C4 y C5: `0.3.0`.** Los tres componentes son **un único
lote funcional** —C6 no escribe nada por sí solo y C4 sin C5 deja las órdenes sin archivo—, de modo
que se incrementa una sola vez para el lote, y **no** `0.3.0 → 0.4.0 → 0.5.0`. El incremento se
aplica en la fase de implementación, junto con la actualización de la prueba que hoy afirma
`generator_version == "0.2.0"`; este ADR solo fija el valor.

### 9. Convención temporal

| Campo | Valor |
|---|---|
| `issued_at`, `expected_at`, `closed_at`, `received_at` | El día a `T00:00:00Z` |
| `inventory_movements.occurred_at` — `ADJUSTMENT` | `00:00:00Z` |
| `inventory_movements.occurred_at` — `RECEIPT` | `06:00:00Z` |
| `inventory_movements.occurred_at` — `ISSUE` | `18:00:00Z` |
| `inventory_movements.recorded_at` | `= occurred_at` |
| `created_at`, `updated_at`, `created_by` | **Vacíos, siempre** |

Las horas fijas por tipo existen **solo** en `inventory_movements.csv`, porque es el único archivo
donde el orden intradía es semántico: la recepción del día debe preceder al consumo del día para que
el saldo reconstruya ordenando por `occurred_at`. Cuando dos movimientos comparten `occurred_at` —dos
recepciones el mismo día—, el desempate determinista está en `DT-038` §5.4. En el resto de archivos
el hecho es el día.

**Los campos de auditoría van vacíos** *(corrección del 2026-09-24)*. La primera versión de este ADR
incluía `updated_at` entre los campos fijados a `T00:00:00Z`, lo que contradecía `DT-024`, que para
los mismos campos establece «**Vacío**. Auditoría técnica: la fija la ingesta, no el generador». Rige
`DT-024`: el generador **no** produce marcas de tiempo de auditoría. La temporalidad de la simulación
se expresa con los campos temporales propios de cada entidad —`occurred_at`, `occurred_on`,
`issued_at`, `expected_at`, `received_at`, `closed_at`, `last_movement_at`— y con
`manifest.time_range`. `DT-024` **no** se enmienda.

`recorded_at = occurred_at` significa que **V1 no simula registro tardío**. `docs/04` §3.7 distingue
los dos campos precisamente para que un registro tardío no ensucie la serie de la fecha equivocada;
el dataset de V1 no ejercita esa distinción. Es una limitación declarada.

### 10. Vigencia y órdenes en vuelo

Una orden emitida **dentro** del intervalo de vigencia de un producto completa su ciclo causal aunque
sus recepciones —**y los movimientos `RECEIPT` derivados de ellas**— caigan después de `valid_to`.
Esta excepción está acotada y enmendada formalmente en `DT-027` (restricción 3, enmienda del
2026-09-24), en §34 de la especificación y en `docs/04` §3.2.

Una recepción derivada de una orden emitida en vigencia **no** se cancela, **no** se elimina, **no**
se trunca, **no** se convierte en `ADJUSTMENT`, y conserva el `reference_type` y el `reference_id`
correspondientes a su origen.

La excepción **no autoriza**, después de `valid_to`: nueva demanda · nuevo consumo · nuevas órdenes ·
nuevas relaciones con proveedores · ningún otro movimiento arbitrario.

El corte del periodo y qué hechos quedan dentro de él están en `DT-038` §9.

## Contexto

§10 de la especificación describe cinco situaciones de inventario —saludable, bajo, riesgo de
stockout, sobreinventario, tránsito—, §11 exige un escenario donde el tránsito total supere la
necesidad inmediata mientras el efectivo no cubre el intervalo de protección, y §14 pide órdenes
completas, parciales, pendientes y canceladas. Ninguna de esas secciones fija una sola fórmula, un
solo umbral ni un solo número: describen **qué debe poder observarse**, no cómo generarlo.

`docs/06-motor-abastecimiento.md` sí tiene fórmulas, pero son las del **motor real**, y dependen de
un pronóstico que en la Fase 1 no existe y de parámetros de negocio que siguen pendientes
(`BR-X01`, `BR-X02`, `BR-X13`, `DT-010`, `DT-P05`). Usarlas dentro del generador exigiría inventar
esos parámetros, que es justo lo que `CLAUDE.md` §7.4 prohíbe.

Sin estas políticas, el Componente 4 no es implementable.

## Alternativas consideradas

| | Alternativa | Ventajas | Inconvenientes |
|---|---|---|---|
| (a) | **Políticas sintéticas documentadas, constantes del componente** | Precedente directo de `DT-028` y `DT-035`; amparada por §3.5; no inventa ningún parámetro de negocio | Son constantes del código: cambiarlas exige tocar el componente y regenerar |
| (b) | Reutilizar las fórmulas de `docs/06` dentro del generador | Una sola definición en el repositorio | Exigiría fijar stock de seguridad, nivel de servicio y horizonte de cobertura, todos pendientes del negocio. Y convertiría el generador en el motor, que es la confusión que este ADR existe para impedir |
| (c) | Añadir `W`, `M`, `C` y los factores a `DatasetConfig` | Visibles en el manifiesto | Reabre el Componente 1, cerrado, y contradice la cabecera de `dataset_config.yaml`, que declara no contener parámetros de este tipo |
| (d) | Generar inventario sin bucle causal (series independientes) | Mucho más simple | §14 lo prohíbe literalmente: «No se debe generar tránsito artificial independiente de las órdenes de compra» |

## Razón

**(a)**, por §3.5 y por el precedente de los dos componentes ya implementados.

**(b)** se descarta por dos motivos independientes, y cualquiera bastaría: exigiría inventar
parámetros de negocio, y borraría la frontera entre el generador y el motor. Esa frontera es la razón
de ser de la advertencia de lectura de este documento.

**(c)** se descartó por decisión del responsable del 2026-09-23: el Componente 1 no se reabre. La
consecuencia —que el manifiesto ya no determina por sí solo el dataset— se cierra con la regla de
`GENERATOR_VERSION` de la sección 8.

**(d)** está prohibida por la especificación.

Los valores concretos se eligieron para que el comportamiento sea **falsable midiendo el dataset**,
no para obtener un resultado predeterminado. En particular, `AJUSTADO` con lead time alto arranca por
debajo de su propio umbral y dispara el primer día, mientras `HOLGADO` con lead time bajo tarda
semanas: la dispersión de comportamientos es una consecuencia aritmética de la mezcla, no una
asignación manual de escenarios.

## Consecuencias

**Positivas**

1. El Componente 4 es implementable sin inventar un solo parámetro de negocio.
2. `inventory.csv` es reconstruible desde `inventory_movements.csv`, porque el saldo de apertura es
   un movimiento y no un valor externo.
3. Los escenarios de §10, §11 y §14 pueden **emerger y medirse** en lugar de fabricarse producto a
   producto.
4. La frontera con `docs/06` queda escrita y es verificable: ninguna columna del dataset lleva un
   nombre reservado del motor, y el Componente 4 **no escribe `InventoryPolicy`**.

**Costos aceptados**

1. Los parámetros son constantes del código: cambiarlos exige tocar el componente, subir
   `GENERATOR_VERSION` y regenerar.
2. El manifiesto no los registra. La trazabilidad pasa por `generator_version` y por este ADR.
3. Seis productos quedarán con sobreinventario permanente por MOQ, y cinco sin proveedor terminarán
   en cero. Ambas cosas son correctas y se verán como defectos si no se leen aquí primero.
4. Los primeros `W` días del dataset llevan la dependencia declarada en la sección 5.

**Qué invalidaría esta decisión**

Que lleguen datos reales de inventario y consumo, en cuyo caso estas políticas dejan de usarse y
`ASSUMPTION-001` se cierra. O que el negocio confirme una política de revisión y un horizonte de
cobertura (`BR-X02`, `BR-X13`, `DT-P05`), lo que no cambiaría el generador pero sí haría que la
distancia entre `s` y el `ROP` real pudiera medirse en lugar de solo afirmarse.

## Lo que esta decisión NO hace

- **No** fija ninguna política empresarial de inventario, ni punto de reorden, ni stock de seguridad,
  ni nivel de servicio, ni horizonte de cobertura.
- **No** implementa ni modifica el motor de abastecimiento de `docs/06`, ni altera `DT-031`.
- **No** escribe la entidad `InventoryPolicy`: `C = 21` **no** es `target_coverage_days`.
- **No** decide el contrato de columnas de los archivos del Componente 5: eso es del Componente 5,
  aunque los identificadores los asigne el Componente 4.
- **No** asigna escenarios a SKU concretos: eso es el Componente 7.
- **No** fija un porcentaje obligatorio de desabasto. Las métricas se implementan primero, se mide
  después, y cualquier ajuste posterior exige un análisis de sensibilidad documentado.
- **No** modifica `config.py`, `dataset_config.yaml`, el Componente 2 ni el Componente 3.
- **No** implementa nada: a la fecha de este ADR, `generator/inventory.py` no existe.
