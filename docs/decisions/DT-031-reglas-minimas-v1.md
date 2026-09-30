# DT-031 — V1: reglas mínimas funcionales del cálculo de abastecimiento

- **Fecha:** 2026-09-19 · **Revisiones:** 2026-09-19 (decisiones A–F) · **2026-09-21 (cierre V1)** · 2026-09-29 (notas de redacción de `V1-07` y `V1-08`, `DT-041`)
- **Estado:** `ACEPTADA` **como conjunto de reglas de V1** — ver la nota sobre el estado más abajo
- **Fase del roadmap:** Fase 1 — Datos (prepara el Componente 2), con efecto en las Fases 4 y 5
- **Afecta a:** `docs/06-motor-abastecimiento.md`, `knowledge/glossary.md`,
  `knowledge/assumptions.md`, `knowledge/business-rules.md`, el diseño de los Componentes 2 a 8
- **Entrada resumida:** `docs/15-decisiones-tecnicas.md` → `DT-031`

---

> # ⚠ QUÉ ES Y QUÉ NO ES ESTE DOCUMENTO
>
> Este ADR define un **conjunto mínimo de reglas técnicas provisionales** que permiten construir y
> probar un flujo completo `Forecast → Inventory → Supply Engine → Recommendation` **antes** de que el
> negocio aporte sus políticas de inventario.
>
> **Ninguna regla de este documento es una política de la organización.** Los parámetros con valor
> numérico —`R_v1`, `z_v1`, `N_v1`, `N_MIN_v1`, `LT_MAX_v1`— son **parámetros técnicos
> provisionales**, no un periodo de revisión acordado ni un nivel de servicio comprometido. Cada regla
> declara explícitamente qué **no** resuelve y por qué decisión pendiente será sustituida.
>
> Tras las decisiones del responsable del 2026-09-19, este ADR **cierra cuatro** reglas pendientes
> (`BR-X05`, `BR-X07`, `BR-X08`, `BR-X09`) con **interpretaciones técnicas**, no con políticas: el
> negocio puede contradecir cualquiera de ellas. Las otras nueve siguen pendientes, dos de ellas
> puenteadas y siete aplazadas por no ser necesarias para V1.
>
> ### Sobre el estado `ACEPTADA`
>
> Desde su creación el 2026-09-19 y hasta este cierre, este ADR estuvo en `PROPUESTA`, y yo mismo
escribí que «debe seguir siéndolo».
> **Revisé esa postura** tras el cierre del 2026-09-21, y conviene explicar por qué, porque la
> distinción importa:
>
> - `CLAUDE.md` §8 prohíbe marcar `ACEPTADA` lo que **todavía es una hipótesis**. Estas reglas ya no
>   lo son: el responsable las ha decidido expresamente y son las que rigen V1.
> - El registro define `ACEPTADA` como «decisión tomada y vigente; cambiarla requiere un nuevo ADR».
>   Es exactamente la situación: cambiar `z_v1` o `R_v1` exigirá un ADR nuevo.
> - **Provisional no es lo mismo que hipotético.** Que una regla esté pensada para ser sustituida no
>   la convierte en una suposición; la convierte en una decisión con fecha de caducidad prevista,
>   que es lo que recoge el apartado «Qué invalidaría estas reglas».
>
> **Lo aceptado es «estas son las reglas de V1», no «estas son las políticas de la organización».**
> Nadie debe leer este `ACEPTADA` como que el negocio ha confirmado un nivel de servicio del 95 %,
> un periodo de revisión semanal ni un lead time máximo de 90 días. No lo ha hecho, y las reglas
> pendientes de `business-rules.md` §3 siguen abiertas.

---

## Decisión

Se adoptan **trece reglas V1** que hacen calculable la cadena de abastecimiento con los datos que el
generador sintético producirá, sin fijar ninguna política empresarial. Las trece quedaron
**confirmadas por el responsable el 2026-09-21** y no vuelven a tratarse como decisiones abiertas.

| ID | Regla | Sustituye provisionalmente a |
|---|---|---|
| `V1-01` | Necesidad bruta (`raw_need`) | — (formaliza `docs/06` §8) |
| `V1-02` | Posición de inventario | — (adopta `docs/06` §4.2 sin cambios) |
| `V1-03` | Horizonte de cobertura | `BR-X02`, `BR-X13`, `DT-P05` |
| `V1-04` | Demanda durante el horizonte | `DT-019` (adopta su recomendación provisional) |
| `V1-05` | Stock de seguridad | `DT-010`, `BR-X01` |
| `V1-06` | MOQ y múltiplo de compra | — (adopta `docs/06` §8 Paso 2) |
| `V1-07` | Escenarios mínimos de demostración | — |
| `V1-08` | Alcance del validador V1 | — |
| `V1-09` | Lead time observado (mediana, mínimo de 3 observaciones) | `BR-P01` (lo implementa de forma provisional) |
| `V1-09.1` | Ventana de 12 observaciones, por fecha de finalización | — (parámetro de `V1-09`) |
| `V1-09.2` | Techo de 90 días, con marca de trazabilidad | — (parámetro de `V1-09`) |
| `V1-10` | Elección de proveedor | **cierra `BR-X05` para V1** |
| `V1-11` | Sin diferenciación ABC | **cierra `BR-X07` para V1** |
| `V1-12` | Sin sobre-recepción | **cierra `BR-X08` para V1** |
| `V1-13` | Sin inventario negativo | **cierra `BR-X09` para V1** |

Hallazgo de estas etapas: **diez de las trece reglas ya estaban documentadas** y solo necesitaban
nombre, parámetros y una comprobación de coherencia — `V1-01` es `docs/06` §§7-8, `V1-02` es §4.2,
`V1-04` es `DT-019`, `V1-06` es §8 Paso 2, `V1-08` recoge invariantes de §§20-21 y §34, `V1-09`
implementa `BR-P01`, `V1-10` adopta `BR-P07`, `V1-11` se apoya en `DT-029`, `V1-12` en §21 y `V1-13`
en §26 junto con `docs/06` §14. Las genuinamente nuevas son solo tres: `V1-03` (elección de la rama de
revisión), `V1-05` (fuente de incertidumbre en ausencia de modelo) y `V1-07` (selección del conjunto
mínimo de escenarios).

---

## V1-01 — Necesidad bruta

```text
ID:        V1-01
Nombre:    Necesidad bruta (raw_need)
Estado:    V1 / provisional (la fórmula NO es provisional; su parametrización sí)
```

**Objetivo.** Dar una definición operativa única de «necesidad», término que la especificación usa con
seis redacciones distintas (§10.4, §11, §16, §17, §26) y que el glosario no define.

**Regla.** `raw_need` es la cantidad que falta para cubrir el horizonte de protección, una vez
descontado lo que ya se tiene o se espera a tiempo. Nunca es negativa.

**Fórmula.**

```text
raw_need = max(0, demand_during_horizon + safety_stock − inventory_position)
```

**Entradas.** `demand_during_horizon` (`V1-04`), `safety_stock` (`V1-05`),
`inventory_position` (`V1-02`).

**Salidas.** Un número ≥ 0, en la unidad de medida del producto.

**Ejemplo** (verificado):

```text
demand_during_horizon = 97,14    safety_stock = 19,80    inventory_position = 30
raw_need = max(0, 97,14 + 19,80 − 30) = 86,94
```

**Motivo de selección.** No es una fórmula nueva: es **exactamente** la rama de revisión periódica de
`docs/06` §§7–8, escrita sin abreviaturas. Comprobación literal:

| `docs/06` | Sustituyendo |
|---|---|
| §7: `S = DDLT_periódica + SS`, con `DDLT_periódica = Σ D̂ₜ sobre (L + R)` | |
| §8: `Q_bruta = max(0, S − IP_decisión)` | `max(0, Σ D̂ sobre (L+R) + SS − IP_decisión)` |

que es la fórmula de arriba con `demand_during_horizon = Σ D̂ sobre (L + R)`. **No hay contradicción
con ningún documento.**

**Nomenclatura.** El mismo concepto aparece con **tres nombres** en el repositorio: `Q_bruta`
(`docs/06` §8), `raw_quantity` (`docs/04` §3.16) y «necesidad bruta». Se adopta `raw_need` como
nombre del cálculo y `raw_quantity` como nombre del campo persistido, y se registran los tres alias
en el glosario. No se renombra ningún campo existente.

**Qué NO resuelve.** No decide qué incertidumbre cubre `safety_stock` (`DT-010`), ni el nivel de
servicio (`BR-X01`), ni el criterio de tránsito efectivo (`DT-P11`), ni la política de revisión
(`BR-X02`). Los cuatro entran por sus parámetros, no por la fórmula.

**Cómo podrá reemplazarse.** La fórmula sobrevive a las cuatro decisiones pendientes: todas cambian
un insumo, ninguna su estructura. Si el negocio confirma **revisión continua**, la fórmula pasa a la
rama de `docs/06` §8 con `H_cobertura` explícito, y `V1-03` es la única regla que cae.

---

## V1-02 — Posición de inventario

```text
ID:        V1-02
Nombre:    Posición de inventario de decisión
Estado:    V1 (adopción sin cambios de una decisión ya aceptada)
```

**Objetivo.** Fijar qué se resta de la necesidad.

**Regla.** Se usa la **posición de decisión**, no la contable.

**Fórmula.**

```text
inventory_position = on_hand + effective_in_transit − reserved
```

**Entradas.** `Inventory.quantity_on_hand`, `effective_in_transit` (derivado, no almacenado),
`Inventory.quantity_reserved`.

**Salidas.** Un número, que puede ser negativo si hay más comprometido que disponible.

**Motivo de selección.** Coincide **literalmente** con `docs/06` §4.2 (`IP_decisión = OH +
effective_in_transit − RSV`) y con `DT-012`. No se introduce nada.

**Dos precisiones de V1, ambas ya documentadas:**

1. **`reserved = 0`.** `docs/04` §3.6 marca `quantity_reserved` como `PENDIENTE DE VALIDACIÓN`: «el
   alcance actual no incluye ningún proceso que genere compromisos… hasta entonces vale 0». §15 de la
   especificación lo confirma. En V1 el término existe en la fórmula y vale cero.
2. **`effective_in_transit` en V1** = cantidad pendiente de las órdenes `ISSUED` o
   `PARTIALLY_RECEIVED` **cuya fecha esperada cae dentro del horizonte de cobertura**. Es la lectura
   más simple compatible con `DT-P11`, que sigue **abierto** en cuanto al tratamiento de las órdenes
   ya vencidas y no recibidas.

**Qué NO resuelve.** `DT-P11` sigue pendiente: V1 **no decide** si una orden atrasada cuenta como
efectiva. La regla de V1 la excluye por construcción —su fecha esperada ya pasó— y eso es una
elección provisional, no la respuesta.

**Cómo podrá reemplazarse.** `effective_in_transit` se calcula en una sola función; cerrar `DT-P11`
cambia esa función y nada más.

---

## V1-03 — Horizonte de cobertura

```text
ID:        V1-03
Nombre:    Horizonte de cobertura V1
Estado:    V1 / PROVISIONAL — contiene un parámetro técnico sin respaldo del negocio
```

**Objetivo.** Determinar cuánto consumo futuro debe cubrir la recomendación.

**Regla.** El horizonte es el **intervalo de protección de la revisión periódica**: lead time más
periodo de revisión.

**Fórmula.**

```text
coverage_horizon_days = lead_time_days + R_v1

donde:
  lead_time_days = observed_lead_time_days  (V1-09)           ← lead time OBSERVADO
                   con fallback a agreed_lead_time_days
                   cuando no hay histórico suficiente
  R_v1           = 7 días                                     ← PARÁMETRO TÉCNICO PROVISIONAL V1
```

**Entradas.** `observed_lead_time_days` calculado por `V1-09`, que a su vez consume
`PurchaseOrder.issued_at`, `PurchaseOrderReceipt.received_at`, `ProductSupplier.agreed_lead_time_days`
(como fallback) y la fecha de la decisión (`as_of_date`). El acordado **ya no es la entrada directa**
desde la decisión D del 2026-09-19; entra solo a través del fallback de `V1-09`.

**Salidas.** Un entero de días.

**Ejemplo.** `lead_time = 10 días`, `R_v1 = 7` → `coverage_horizon = 17 días`.

**Motivo de selección.** Tres apoyos documentales, ninguno inventado:

1. **`ASSUMPTION-002`** ya dice, literalmente: «El horizonte relevante para la decisión de compra es
   del orden de *lead time + periodo de revisión*». La fórmula **no es nueva**: operacionaliza un
   supuesto registrado.
2. **`docs/06` §5** establece que bajo revisión periódica el intervalo de protección es `L + R`.
3. Elegir la rama periódica **elimina** `H_cobertura` (`BR-X13`) del camino crítico: en la
   formulación *order-up-to*, `R` cumple su papel. V1 pasa de depender de **dos** parámetros
   pendientes a depender de **uno**.

**Los dos valores provisionales, declarados:**

| Elemento | Valor V1 | Por qué | Qué lo sustituirá |
|---|---|---|---|
| `R_v1` | **7 días** | El modelado es semanal (`DT-008`); un ciclo de revisión semanal alinea la revisión con la granularidad del pronóstico y evita una conversión extra. **No es la frecuencia de compra de la organización: nadie la ha declarado** | `BR-X02` / `DT-P05` |
| Lead time | **el observado**, con fallback al acordado | Decisión del responsable del 2026-09-19. Adopta la dirección de `BR-P01`: usar el contractual cuando el proveedor entrega sistemáticamente tarde genera desabastos previsibles. El cálculo está en `V1-09` | `BR-P01` pasa a estar **implementada provisionalmente**; su confirmación sigue pendiente |

**Comprobación de coherencia realizada.** Con `agreed_lead_time_days ∈ [1, 45]` (`DT-028` §1.4) y
`R_v1 = 7`, el horizonte V1 va de **8 a 52 días**, es decir hasta **7,4 semanas** — dentro de las
«8–12 semanas» que `ASSUMPTION-002` fija como horizonte de pronóstico. El forecast siempre cubre el
horizonte de cobertura. Verificado aritméticamente.

**Con el lead time observado el margen deja de estar garantizado, y el techo de 90 días NO lo
restaura.** Corrijo aquí una afirmación que escribí el 2026-09-19 y que no resiste la aritmética: con
`LT_MAX_v1 = 90` y `R_v1 = 7`, el horizonte máximo es **97 días ≈ 13,9 semanas**, por encima de las
«8–12 semanas» (84 días) de `ASSUMPTION-002`. El techo **acota** la divergencia; no la elimina. En
concreto, un lead time observado **superior a 77 días** produce ya un horizonte fuera del rango del
pronóstico.

Lo que V1 hace con eso es **señalarlo, no ocultarlo**: `V1-09.2` obliga a marcar `LEAD_TIME_CAPPED`, y
esta limitación queda registrada como tal. Restaurar la garantía exigiría bajar `LT_MAX_v1` a 77 días
o menos, o ampliar el horizonte de `ASSUMPTION-002`; **ninguna de las dos se decide aquí**, porque el
responsable confirmó `LT_MAX_v1 = 90` el 2026-09-21 y cambiarlo es decisión suya. Queda como
**limitación conocida de V1**.

**Qué NO resuelve.** No decide la política de revisión (`BR-X02`, `DT-P05`), no fija la frecuencia de
compra real, no decide si se usa el lead time acordado u observado (`BR-P01`), y no cubre `BR-X06`
(calendario laboral): V1 trabaja en **días naturales**.

**Cómo podrá reemplazarse.** Si el negocio confirma revisión continua, `V1-03` se retira y la fórmula
de `V1-01` recupera el término `D̂ × H_cobertura` de `docs/06` §8. Si confirma periódica con otra
frecuencia, solo cambia `R_v1`.

---

## V1-04 — Demanda durante el horizonte

```text
ID:        V1-04
Nombre:    demand_over_horizon
Estado:    V1 / provisional (adopta la recomendación provisional de DT-019)
```

**Objetivo.** Convertir un pronóstico semanal en demanda esperada sobre un horizonte en días.

**Regla.** **Prorrateo uniforme**, en **una única función** del `supply_engine`.

**Fórmula.**

```text
demand_over_horizon(forecast, start_date, H_days):
    semanas_completas, resto = divmod(H_days, 7)
    return Σ F_i  (i = 1 .. semanas_completas)  +  (resto / 7) × F_(semanas_completas+1)
```

**Entradas.** Serie de pronóstico semanal desde `start_date`, y `H_days` (`V1-03`).

**Salidas.** Un número ≥ 0.

**Ejemplo** (verificado): `H = 17 días` = 2 semanas + 3/7; con `F = [40, 40, 40, 40]` →
`40 + 40 + (3/7)×40 = 97,14`.

**Motivo de selección.** Es la recomendación provisional de **`DT-019`** y de `docs/06` §5.1, palabra
por palabra. V1 no elige una regla nueva: **adopta la que ya estaba propuesta** y la nombra.

**Regla de implementación no negociable, heredada de `docs/06` §5.1:** esta conversión vive en **una
sola función**, que es el único punto del sistema autorizado a traducir entre granularidades. Ningún
otro módulo, consulta SQL, informe ni pantalla la reimplementa. La regla aplicada y el valor obtenido
se registran en `calculation_inputs`.

**Supuesto que introduce.** `ASSUMPTION-019` — demanda uniforme dentro de la semana. Ya registrado,
`VIGENTE`, con su condición de falsedad documentada.

**Qué NO resuelve.** No resuelve `DT-019` —sigue `PENDIENTE DE VALIDACIÓN`— ni `BR-X06`. Si el
negocio no opera todos los días, el prorrateo uniforme sesga sistemáticamente.

**Cómo podrá reemplazarse.** `DT-019` alternativa (b): prorrateo según el perfil intra-semanal
observado. **Sin cambiar la firma de la función**, que es la razón de que `docs/06` §5.1 exija que
viva en un solo sitio.

---

## V1-05 — Stock de seguridad

```text
ID:        V1-05
Nombre:    Stock de seguridad V1
Estado:    V1 / PROVISIONAL — contiene un parámetro técnico sin respaldo del negocio
```

**Objetivo.** Hacer calculable `raw_need` sin decidir la metodología definitiva.

**Regla.** Cuantil normal sobre la **variabilidad de la demanda agregada al horizonte**, calculada
directamente y **sin escalar por √L**.

**Fórmula.**

```text
safety_stock = z_v1 × σ_H

donde:
  σ_H  = desviación estándar de la demanda histórica sumada sobre ventanas
         móviles de coverage_horizon_days
  z_v1 = 1,65                          ← PARÁMETRO TÉCNICO PROVISIONAL V1
```

**Entradas.** Serie histórica de consumo del producto y `coverage_horizon_days`.

**Salidas.** Un número ≥ 0.

**Ejemplo** (verificado): `σ_H = 12`, `z_v1 = 1,65` → `safety_stock = 19,80`.

**Motivo de selección — y por qué NO se usa §6.1 tal cual.** `docs/06` §6.1 propone
`SS = z × σ_D × √L`, pero §6.4 advierte expresamente que **escalar por `√L` no es una identidad
general**: se deriva para el método naïve bajo residuos no correlacionados y varianza constante, y
aplicarla sin verificarla «subestimaría el stock de seguridad precisamente donde más cuesta».

Calcular `σ_H` **directamente** sobre ventanas del horizonte esquiva ese problema por completo: no
escala nada, mide lo que hay que cubrir. Es más simple y **más defendible** que la fórmula de §6.1.

**Sobre la fuente de incertidumbre.** §6.4 distingue cuatro conceptos y señala que el más pertinente
es el **error de pronóstico** (concepto 2), no la variabilidad de la demanda (concepto 1). V1 usa el
concepto 1 por una razón que no es una preferencia: **el concepto 2 exige residuos de backtesting, que
exigen un modelo entrenado, que es la Fase 5**. En V1 no existe modelo, luego el concepto 2 no está
disponible. V1 usa lo único medible y lo declara.

**Sobre `z_v1 = 1,65`:**

> **NO es un nivel de servicio acordado con la organización.** Es un parámetro técnico provisional.
> Bajo normalidad corresponde nominalmente a un ~95 % de probabilidad de no agotar en un ciclo, pero
> `docs/06` §6.3 advierte de dos cosas que V1 **no** resuelve: el supuesto de normalidad **no se
> sostiene** en demanda intermitente ni asimétrica, y existen dos definiciones de «nivel de servicio»
> que no son intercambiables. El negocio no ha indicado cuál usa (`BR-X01`).

**Limitación conocida y aceptada de V1:** la misma fórmula se aplica a todos los segmentos, incluida
la demanda intermitente, donde `docs/06` §6.3 dice que el supuesto falla. V1 no lo corrige; lo
declara.

**Tensión con `BR-009`, declarada.** `BR-009` dice que si falta un parámetro de política el sistema
**no calcula** el valor dependiente. `z_v1` es exactamente un parámetro de política ausente. V1 lo
puentea **solo dentro del entorno sintético** y con la marca `V1/provisional`; **la salida de V1 no
puede presentarse como una recomendación de negocio**. Cuando el sistema opere sobre datos reales,
`BR-009` rige sin excepción: sin `BR-X01`, no hay `SS` y la recomendación se marca no calculable.

**Qué NO resuelve.** `DT-010` (`PENDIENTE DE VALIDACIÓN`), `BR-X01`, `BR-P02` (variabilidad del
proveedor: V1 **ignora** `σ_L`), `BR-P03`.

**Cómo podrá reemplazarse.** `DT-010` se cerrará en la Fase 5 comparando alternativas por su efecto
en las métricas de **Nivel 2** (`DT-020`). `V1-05` es el punto de partida contra el que se comparan:
su valor real es servir de baseline medible, no de respuesta.

---

## V1-06 — MOQ y múltiplo de compra

```text
ID:        V1-06
Nombre:    Ajuste por restricciones del proveedor
Estado:    V1 (adopción sin cambios de docs/06 §8 Paso 2)
```

**Objetivo.** Convertir `raw_need` en una cantidad pedible.

**Regla.** Se aplican **ambas** restricciones, en este orden: primero el mínimo, después el múltiplo.

**Fórmula.**

```text
si raw_need <= 0:  no hay recomendación
Q_moq   = max(raw_need, MOQ)
Q_final = ceil(Q_moq / order_multiple) × order_multiple
```

**Entradas.** `raw_need`, `ProductSupplier.moq`, `ProductSupplier.order_multiple`.

**Salidas.** `Q_final`, múltiplo exacto de `order_multiple` y ≥ `MOQ`.

**Ejemplos** (verificados):

| `raw_need` | MOQ | M | `Q_moq` | `Q_final` | Quién obliga el exceso |
|---:|---:|---:|---:|---:|---|
| 18 | 25 | 10 | 25 | **30** | MOQ **y** múltiplo |
| 86,94 | 25 | 10 | 86,94 | **90** | Solo el múltiplo |
| 10 | 0 | 1 | 10 | **10** | Ninguno |

**Motivo de selección.** Es **literalmente** `docs/06` §8 Paso 2, documentado desde la Etapa 0. V1 no
propone nada: adopta lo que ya estaba.

**`MOQ` NO tiene que ser múltiplo de `order_multiple`.** Verificado por búsqueda en `docs/` y
`knowledge/`: **ninguna fuente lo exige**. `docs/04` §3.4 solo impone `moq ≥ 0` y
`order_multiple ≥ 1`. Imponerlo sería inventar una política comercial (`CLAUDE.md` §7.4) y eliminaría
del dataset el caso que el motor está diseñado para manejar. Pares como `(25, 10)` **se conservan**.

**Contradicción detectada y corregida en esta etapa.** `docs/06` §14 exigía: «MOQ mayor que la
necesidad → **Recomienda MOQ** y señala la sobrecobertura». Con `MOQ = 25` y `M = 10` el Paso 2
produce **30**, no 25: el criterio de aceptación contradecía la fórmula del mismo documento siempre
que `MOQ` no fuera múltiplo de `M`. Es un defecto **anterior a todo este bloque de trabajo**. Se
corrige el criterio de §14, **no la fórmula**, porque la fórmula es correcta y el criterio estaba mal
enunciado.

**Consecuencia para la explicabilidad.** `BR-004` y `docs/06` §13 exigen que la recomendación sea
reconstruible. Con 30 sobre una necesidad de 18, el desglose debe distinguir los 7 que impone el MOQ
de los 5 que impone el redondeo. **V1 registra `raw_need`, `Q_moq` y `Q_final` por separado** en
`calculation_inputs`. `docs/04` §3.16 ya guarda `raw_quantity` y `recommended_quantity`; `Q_moq` es
intermedio y va en el JSON, sin añadir columnas al modelo.

**Qué NO resuelve.** No decide el umbral de sobreinventario del Paso 3 (`BR-X03`), de modo que V1
**calcula** `Q_final` pero **no clasifica** si genera sobrecobertura.

**Cómo podrá reemplazarse.** No necesita reemplazo: la regla es aritmética, no política. Lo que
cambiará es el Paso 3, cuando `BR-X03` se cierre.

---

## V1-07 — Escenarios mínimos de demostración

```text
ID:        V1-07
Nombre:    Conjunto mínimo de demostración de V1
Estado:    V1 (lista de aceptación; NO sustituye la cobertura de §25)
```

**Objetivo.** Fijar qué hay que poder enseñar funcionando, sin generar escenarios de más.

**Aclaración necesaria.** Los quince elementos de esta lista **no son quince escenarios del mismo
tipo**: once corresponden a valores del enum `Scenario` y cuatro son propiedades de Nivel B o C según
`DT-023`. Mezclarlos fue el error que `DT-023` corrigió. La tabla los separa.

| # | Elemento | Nivel (`DT-023`) | Quién lo produce | Quién lo comprueba |
|---|---|---|---|---|
| 1 | Demanda estable | A · `STABLE_DEMAND` | Generador de demanda | Validador |
| 2 | Demanda creciente | A · `GROWING_DEMAND` | Generador de demanda | Validador |
| 3 | Demanda decreciente | A · `DECLINING_DEMAND` | Generador de demanda | Validador |
| 4 | Demanda estacional | A · `SEASONAL_DEMAND` | Generador de demanda | Validador |
| 5 | Demanda intermitente | A · `INTERMITTENT_DEMAND` | Generador de demanda | Validador |
| 6 | **Inventario suficiente** | **C** (§10.1, no es fila de §25) | Simulador de inventario | Validador |
| 7 | Inventario bajo | A · `LOW_INVENTORY` | Simulador de inventario | Validador |
| 8 | Stockout | A · `STOCKOUT` | Simulador de inventario | Validador |
| 9 | Inventario en tránsito | A · `IN_TRANSIT` | Generador de órdenes | Validador |
| 10 | Proveedor confiable | A · `RELIABLE_SUPPLIER` | Comportamiento de proveedores | Validador |
| 11 | Proveedor retrasado | A · `DELAYED_SUPPLIER` | Comportamiento de proveedores | Validador |
| 12 | **MOQ > necesidad** | **C** (§25 fila 18) | **Nadie, hoy** — ver abajo | **Prueba del motor**, no el validador |
| 13 | **El múltiplo modifica la cantidad** | **C** | Ídem | **Prueba del motor** |
| 14 | Entrega parcial | A · `PARTIAL_DELIVERY` | Comportamiento de proveedores | Validador |
| 15 | **Producto sin proveedor activo** | **B/C** (§26) | **Componente 2** (`DT-028` §2.5, clase D) | Validador |

**Reparto por responsabilidad, como se pidió:**

- **Generación de datos:** 6, 7, 8, 9, 15 — surgen de poblar entidades.
- **Registro de escenarios:** 1, 2, 3, 4, 5, 10, 11, 14 — son ejes del enum. La forma de la demanda
  la **decide** el Componente 3 (`DT-035`) y el perfil de proveedor el Componente 6 (`DT-037`); el
  Componente 7 **registra** esas decisiones y **mide** los ejes que emergen (`DT-041` §1). No decide,
  no asigna y no genera datos para forzar cobertura.

> *Corrección de redacción del 2026-09-29 (`DT-041`).* Esta línea decía «asignados a SKU y a
> relaciones concretas por el componente de asignación». El nombre del componente se conserva por
> estabilidad del identificador (`DT-030`), pero la responsabilidad real es registrar y medir. No
> cambia el reparto de los elementos.
- **Validación:** 1–11, 14, 15 — comprobables sobre el dataset sin calcular nada.
- **Pruebas posteriores del motor:** 12 y 13 — **no son propiedades del dataset**, sino del cálculo.

**Los elementos 12 y 13 son el caso especial, y conviene no disimularlo.** Comprobar `MOQ > raw_need`
exige calcular `raw_need`, que exige `V1-03`, `V1-04` y `V1-05` — es decir, el motor. El dataset
**no** puede contener ese escenario; puede contener sus **condiciones**. Con las reglas V1 ya
definidas, esas condiciones son construibles y comprobables: basta una relación con `MOQ` alto sobre
un producto de demanda baja e inventario holgado. **Esta es la única de las tres cuestiones abiertas
de la auditoría anterior que V1 cierra**, y la cierra porque V1 hace calculable `raw_need`.

**El elemento 13 se satisface solo**, por `DT-028` §1.2: basta `order_multiple ≥ 48` con una
necesidad menor. No requiere nada adicional.

**Qué NO resuelve.** V1-07 **no modifica** `dataset_config.yaml` ni el enum: los 16 valores siguen
declarados como cobertura requerida. Esta lista es una **lista de aceptación de V1**, un subconjunto
de demostración. Los cinco ejes del enum que no aparecen —`HIGH_ROTATION`, `LOW_ROTATION`,
`ERRATIC_DEMAND`, `OVERSTOCK`, `MULTIPLE_LEAD_TIMES`— siguen siendo cobertura obligatoria del
dataset, simplemente no forman parte de la demostración mínima.

---

## V1-08 — Alcance del validador V1

```text
ID:        V1-08
Nombre:    Invariantes mínimas del validador
Estado:    V1
```

**Objetivo.** Que el validador compruebe el dataset sin convertirse en un segundo motor de negocio.

**Regla.** El validador comprueba **solo propiedades verificables por inspección de los datos**.
Nunca calcula `raw_need`, `SS`, `ROP` ni `Q_final`.

**Invariantes V1, todas respaldadas:**

| Grupo | Invariante | Fuente |
|---|---|---|
| **Referencial** | `Product.category_id` → `Category` | §34 |
| | `ProductSupplier.product_id` → `Product`; `.supplier_id` → `Supplier` | §34 |
| | `PurchaseOrder.supplier_id` → `Supplier`; `.location_id` → `Location` | §34 |
| | `PurchaseOrderItem.purchase_order_id` → `PurchaseOrder`; `.product_id` → `Product` | §34 |
| | `PurchaseOrderReceipt.purchase_order_item_id` → `PurchaseOrderItem` | §34 |
| **Temporal** | `period.start_date < period.end_date` | `config.py`, ya probado |
| | `valid_from ≤ valid_to` o `valid_to` nulo | `DT-027` |
| | Todo evento del producto dentro de `[valid_from, valid_to]` | §20 |
| | `issued_at ≤ expected_at` | §20 |
| | `issued_at ≤ received_at` — «una recepción no puede ocurrir antes de la emisión» | §20 |
| | Lead time observado ≥ 0 | §20 |
| **Cuantitativa** | `quantity_ordered > 0` | `docs/04` §3.10 |
| | `quantity_received ≥ 0` | §21 |
| | `Σ quantity_received ≤ quantity_ordered` por línea, **sin excepción en V1** (`V1-12`): §21 admite la excepción solo «si existe un escenario explícito», y V1 no crea ninguno | §21, `BR-X08`, `V1-12` |
| | `on_hand(t) ≥ 0` en todo instante del periodo, sobre el saldo reconstruido (`V1-13`) | §26, `docs/06` §14, `V1-13` |
| | `movement.quantity ≠ 0` | `docs/04` §3.7 |
| | `moq ≥ 0`, `order_multiple ≥ 1` | `docs/04` §3.4 |
| **Identidad** | `sku` único; `Category.code`, `Supplier.code`, `Location.code` únicos | `docs/04` §5.8 |
| | Par (`product_id`, `supplier_id`) único | `docs/04` §3.4 |
| | Como máximo un proveedor preferente **activo** por producto | `docs/04` §3.4 |
| **Origen** | `data_origin = SYNTHETIC` en todos los registros | §34, `DT-026` |
| **Formato** | Cabecera, orden de columnas, nulos, fechas, booleanos, decimales | `DT-024` |
| **Reconstrucción** | El inventario se reconstruye desde los movimientos | §22 |
| | El tránsito total se reconstruye desde las órdenes | §23 |
| **Cobertura** | Existe al menos un caso de cada eje declarado en `scenarios.required` | §25, `DT-023` |

**Lo que el validador V1 NO hace, explícitamente:**

- No calcula `raw_need` ni ninguna cifra de abastecimiento.
- No comprueba `MOQ > necesidad` (elemento 12 de `V1-07`): es una prueba del motor.
- No clasifica sobreinventario ni riesgo: depende de `BR-X03`. *Precisión del 2026-09-29
  (`DT-041` §7):* el validador **no** clasifica sobreinventario según `BR-X03`; para demostrar la
  cobertura del eje `OVERSTOCK` y de la situación 18 de §25, los Componentes 7 y 8 usan
  **únicamente** el criterio sintético de cobertura de `DT-041` §6.6 y §8
  (`SYNTHETIC_COVERAGE_CRITERION`). Ese criterio **no** es una regla de negocio ni un umbral de
  riesgo, y `BR-X03` sigue pendiente.
- No crea datos ni escenarios. Solo verifica. Crear invalidaría la reproducibilidad de §3.3 y haría
  que el validador validara su propia salida.

**Cómo podrá reemplazarse.** Las invariantes se añaden; no se sustituyen. Al cerrar `BR-X03` y
`DT-P11` podrán incorporarse comprobaciones hoy imposibles.

---

## V1-09 — Lead time observado

```text
ID:        V1-09
Nombre:    observed_lead_time_days
Estado:    V1 / provisional — implementa la dirección de BR-P01, que sigue sin confirmar
```

**Objetivo.** Que el lead time usado en el cálculo **evolucione con el histórico real** de órdenes y
recepciones, en lugar de quedarse en el valor contractual.

**Regla.** Mediana de las últimas `N_v1` observaciones válidas del par producto–proveedor, calculada
**en el momento de la decisión**. Sin histórico suficiente, se usa el acordado y se declara.

**Fórmula.**

```text
observaciones(product, supplier, as_of_date) =
    para cada PurchaseOrderItem de ese par que esté COMPLETAMENTE RECIBIDO
    y cuya última recepción tenga received_at <= as_of_date:
        lead_time = received_at(última recepción) − purchase_order.issued_at

ventana   = las N_v1 observaciones más recientes por FECHA DE FINALIZACIÓN
            (la de su última recepción)                          (N_v1 = 12)
            si hay entre 3 y 12, se usan todas las disponibles
n         = |ventana|

si n >= N_MIN_v1 (= 3):
    observed_lead_time_days = ceil( mediana(ventana) )
    fuente = OBSERVED
si no:
    observed_lead_time_days = ProductSupplier.agreed_lead_time_days
    fuente = AGREED_FALLBACK

techo: si observed_lead_time_days > LT_MAX_v1 (= 90 días),
       se usa 90 y se marca LEAD_TIME_CAPPED
```

**Entradas.** `PurchaseOrder.issued_at`, `PurchaseOrderReceipt.received_at`,
`PurchaseOrderItem.quantity_ordered` / `quantity_received`, `ProductSupplier.agreed_lead_time_days`,
y la fecha de la decisión (`as_of_date`).

**Salidas.** Un entero de días, **más su procedencia** (`OBSERVED` / `AGREED_FALLBACK`) y el número de
observaciones usadas. Los tres se registran: el valor en `Recommendation.lead_time_used_days` —campo
que **ya existe** en `docs/04` §3.16— y la procedencia y `n` en `calculation_inputs`.

**Ejemplo** (el del responsable, verificado):

```text
Historial: PO1 → 10 d · PO2 → 14 d · PO3 → 12 d · PO4 → 18 d
ordenadas: 10, 12, 14, 18      n = 4 ≥ 3      mediana = 13,0
observed_lead_time_days = 13    fuente = OBSERVED
coverage_horizon = 13 + 7 = 20 días
```

**Sub-reglas identificadas.** El cierre del 2026-09-21 distingue tres piezas dentro de `V1-09`. Se
identifican por separado para poder citarlas y sustituirlas una a una; los tres parámetros
(`N_MIN_v1`, `N_v1`, `LT_MAX_v1`) son igual de provisionales y `ASSUMPTION-024` los valida con el
mismo método empírico, de modo que **no se afirma que unos vayan a caer antes que otros**.

| ID | Contenido | Parámetro |
|---|---|---|
| `V1-09` | Mediana de las observaciones del par producto–proveedor; con menos de `N_MIN_v1` se usa `agreed_lead_time_days` y se declara `AGREED_FALLBACK` | `N_MIN_v1 = 3` |
| `V1-09.1` | Ventana de las `N_v1` observaciones más recientes **por fecha de finalización**; entre 3 y 12, se usan todas las disponibles | `N_v1 = 12` |
| `V1-09.2` | Techo del lead time: por encima de `LT_MAX_v1` se usa `LT_MAX_v1` y se marca `LEAD_TIME_CAPPED`, conservando el valor sin topar en la trazabilidad | `LT_MAX_v1 = 90` |

> **`V1-09.2` no es una afirmación de negocio.** El techo de 90 días es una **regla técnica
> provisional de V1**, adoptada por coherencia con el horizonte de pronóstico de `ASSUMPTION-002`. No
> significa que PluriOne tenga, acepte o comprometa un lead time máximo de 90 días con ningún
> proveedor, y no debe citarse como tal en ninguna salida, informe o conversación con el negocio. Un
> lead time real superior a 90 días no queda «prohibido»: queda **topado para el cálculo** y
> **señalado**, que es justo lo contrario de ocultarlo.

### Las siete preguntas, respondidas

**1. Qué registros participan.** Uno por **`PurchaseOrderItem` completamente recibido**, fechado por
su **última** recepción. No uno por recepción.

La diferencia importa y por eso no la elegí a la ligera. Contar una observación **por recepción**
—que es la granularidad literal de `docs/04` §3.11— haría que un proveedor con entregas parciales
aportara dos o tres observaciones por línea, y la primera parcial siempre llega antes que el
completado. El resultado sería **subestimar** el lead time justo en los proveedores menos fiables,
que es el error exactamente opuesto al que conviene cometer. Una observación por línea completada no
tiene ese sesgo.

Consecuencia aceptada: las líneas parcialmente recibidas **no aportan nada** hasta completarse, de
modo que un proveedor con muchas entregas parciales tarda más en salir del fallback. Es el
comportamiento prudente.

**2. Ventana histórica.** Las **12 observaciones más recientes por fecha de finalización** —la de su
última recepción, no la de emisión de la orden—. Con menos de 12 se usan todas las disponibles; con
menos de 3 se aplica el fallback.

Ventana por **recuento**, no por calendario: siempre produce el mismo conjunto para los mismos datos,
y no puede quedarse vacía porque «no hubo órdenes en los últimos seis meses». Una ventana temporal es
la evolución natural en V2, cuando haya volumen suficiente para que tenga sentido.

*Precisión del 2026-09-21:* el orden es por **finalización**, conforme a la instrucción del
responsable. Es además el criterio correcto: una orden emitida hace mucho y recibida ayer es
información **reciente** sobre el proveedor, y ordenar por emisión la habría descartado antes que a
una orden más antigua pero emitida después.

**3. Valor representativo: la mediana.** No la media. La mediana **es** el tratamiento de valores
anómalos (pregunta 6): una entrega catastrófica de 120 días desplaza la media y no mueve la mediana.
Elegir un estadístico robusto evita tener que inventar un método de detección de atípicos, que es
justo lo que no queremos en V1. Se redondea **hacia arriba** (`ceil`) porque, ante la duda, un día de
más en el lead time es el error seguro.

**4. Frecuencia de recálculo: en cada evaluación**, sin caché ni proceso programado.

Esto **no es** una simplificación por pereza; es un requisito de corrección. §29 prohíbe usar
información posterior al instante de predicción, y `ASSUMPTION-020` y `DT-020` exigen poder simular
retrospectivamente una decisión pasada. Si el lead time observado se guardara y se reutilizara, una
simulación del 2024-06-01 usaría un valor calculado con recepciones de 2025 — **leakage**. Filtrar
por `received_at <= as_of_date` en cada evaluación lo impide por construcción.

**5. Sin histórico suficiente → fallback al acordado.** Analizado, no adoptado por defecto:

| Alternativa | Por qué se descartó o se eligió |
|---|---|
| **Fallback a `agreed_lead_time_days`** | **Elegida.** Siempre existe (dato maestro desde el Componente 2), es la expectativa contractual, y `BR-P01` ya establece que «el acordado se conserva como referencia». No inventa nada |
| No recomendar hasta tener histórico | Descartada: dejaría sin recomendación a todo producto o proveedor nuevo, es decir a todo el catálogo al arrancar. Un sistema que no sirve el primer día no es una V1 |
| Media del proveedor sobre todos sus productos | Descartada: mezcla relaciones con condiciones distintas, y `docs/04` §3.4 es explícito en que el lead time es de la **combinación**, no del proveedor |
| Media global del catálogo | Descartada: inventa un estadístico sin significado |

`N_MIN_v1 = 3` es el mínimo con el que una mediana tiene un valor central propio y no es simplemente
uno de dos extremos. **Parámetro técnico provisional.**

**6. Valores anómalos.** La mediana los absorbe; no se añade recorte ni winsorización. Lo que **no**
es tratamiento estadístico sino validación: un lead time negativo es imposible (§20) y lo rechaza el
validador como incidente de datos, no lo descarta el motor.

El **techo `LT_MAX_v1 = 90 días`** no es detección de atípicos: es una **cota de daño** frente a un
lead time observado desbocado, que de otro modo produciría un horizonte de cobertura arbitrariamente
largo sobre un pronóstico que no llega tan lejos (`ASSUMPTION-002` sitúa el horizonte relevante para
la decisión de compra en 8–12 semanas).

**Precisión del 2026-09-21:** el techo **acota** esa divergencia pero **no la elimina** — `90 + 7 = 97
días ≈ 13,9 semanas` sigue por encima de 12 semanas, y ya a partir de un observado de 78 días el
horizonte se sale del rango. Es una limitación conocida, no una garantía; ver la nota de `V1-03`. Al
aplicarse el techo **se marca** `LEAD_TIME_CAPPED` en la explicación y se conserva el valor sin topar;
no se recorta en silencio.

**7. Almacenamiento.** **No se almacena.** Se calcula en cada evaluación y se registra el valor usado,
su procedencia y `n` en la recomendación, que es donde la trazabilidad lo necesita (`BR-004`).
`SupplierPerformance` (`docs/04` §3.17) ya prevé `avg_lead_time_days` y `stddev_lead_time_days` como
entidad **derivada y recalculable**: es el sitio natural si más adelante conviene materializarlo, y
**no hace falta tocarlo ahora**. Ningún campo nuevo en el modelo.

**Parámetros provisionales de esta regla:** `N_v1 = 12`, `N_MIN_v1 = 3`, `LT_MAX_v1 = 90`.
`ASSUMPTION-024`.

**Motivo de selección.** Cumple la evolución que pedía el responsable —pocos datos → estimación
inicial; más recepciones → recálculo; más historial → estimación más representativa— con **una
mediana y un filtro de fecha**. No hay modelo, ni suavizado, ni detección de anomalías, ni proceso
programado.

**Qué NO resuelve.** No estima `σ_L` (`BR-P02`: V1 ignora la variabilidad del lead time en el stock
de seguridad). No pondera las observaciones por antigüedad. No detecta cambios de comportamiento del
proveedor. No confirma `BR-P01`, que sigue siendo regla **propuesta**.

**Cómo podrá reemplazarse.** La función devuelve un entero y su procedencia; sustituirla por una media
móvil ponderada, un percentil o una estimación bayesiana no cambia nada a su alrededor. La ventana por
recuento pasa a ventana temporal en cuanto haya volumen.

**Efecto sobre el Componente 2: ninguno.** `V1-09` consume órdenes y recepciones, que producen los
componentes 5 y 6. Lo único que exige del Componente 2 es que `agreed_lead_time_days` siga existiendo
y con variación —`DT-028` §1.4 ya lo garantiza—, porque ahora **además** es el fallback de toda
relación sin histórico. El acordado **no se elimina del modelo**: sigue siendo dato contractual y la
referencia contra la que se mide la desviación del proveedor (`docs/04` §3.4, §3.17).

---

## V1-10 — Elección de proveedor

```text
ID:        V1-10
Nombre:    Proveedor usado en el cálculo
Estado:    V1 — cierra BR-X05 para V1 con una regla ya propuesta en el proyecto
```

**Objetivo.** El cálculo necesita **un** proveedor concreto para leer `MOQ`, `order_multiple` y el
lead time. Sin regla, no hay cálculo.

**Regla.**

```text
proveedor = la relación ProductSupplier activa marcada is_preferred del producto
si no existe ninguna  → no se recomienda, y se señala el dato faltante
```

**Motivo de selección.** No es una regla nueva: **`BR-P07` ya la propone** —«Mientras no exista un
criterio de selección definido, se sugiere el proveedor marcado como preferente y se muestran las
alternativas con sus indicadores»— y `DT-028` §2.4 garantiza exactamente un preferente activo por
producto, salvo en la clase D. El caso sin preferente ya está previsto en `docs/06` §14: «Producto
sin proveedor activo → No recomienda; señala el dato faltante».

**Qué NO resuelve.** `BR-X05` sigue **pendiente de negocio**: si prima el costo, el lead time o la
confiabilidad, y si hay acuerdos de volumen. V1 **no introduce ninguna puntuación ni comparación**
entre proveedores, y eso es deliberado.

**Cómo podrá reemplazarse.** Cuando `BR-X05` se cierre, cambia una función de selección. Todo lo
demás —`MOQ`, múltiplo, lead time— se lee de la relación elegida, sea cual sea el criterio.

---

## V1-11 — Sin diferenciación ABC

```text
ID:        V1-11
Nombre:    Política única para todo el catálogo
Estado:    V1 — cierra BR-X07 para V1 con una interpretación técnica
```

**Objetivo.** Que el motor V1 aplique **la misma política a todos los productos**, para que ninguna
recomendación dependa de una segmentación que hoy no existe ni puede calcularse.

**Regla.**

```text
ninguna regla de CÁLCULO de V1 (V1-01 a V1-06, V1-09) lee abc_class, rotation_class
    ni ningún otro atributo de segmento del producto
los parámetros de política (R_v1, z_v1, N_v1, N_MIN_v1, LT_MAX_v1) son
    los mismos para todo el catálogo, sin excepción
```

**Un matiz necesario, para no afirmar de más.** La rotación **sí** existe en V1 como **eje de
generación del dataset**: `HIGH_ROTATION` y `LOW_ROTATION` son dos de los 16 valores del enum
`Scenario` (`DT-023`) y `V1-07` los exige en la cobertura. Lo que `V1-11` prohíbe es distinto y más
estrecho: que el **cálculo** lea un atributo de segmento para aplicar parámetros distintos. Generar un
producto con demanda de alta rotación es legítimo; darle por ello un `z` distinto, no. `DT-029` ya
señaló el riesgo contiguo —que el Componente 2 escriba `rotation_class` a partir del eje asignado— y
lo prohíbe expresamente.

**Lo que esta regla NO hace: no elimina el campo.** `Product.abc_class` y `Product.rotation_class`
**siguen existiendo** en el modelo de datos (`docs/04` §3.2, donde figuran como «Derivada, opcional»)
y **siguen siendo columnas** del contrato de salida: `DT-024` los mantiene en las posiciones 8 y 9 de
`products.csv`, vacías siempre. V1 no los escribe y no los lee; no los suprime.

**Entradas.** Ninguna. La regla es la ausencia de una entrada.

**Salidas.** Ninguna directa. Su efecto es que los parámetros de `V1-03` (`R_v1`), `V1-05` (`z_v1`) y
`V1-09` (`N_v1`, `N_MIN_v1`, `LT_MAX_v1`) no admiten variantes por segmento. `V1-06` no aporta
parámetros de política —`MOQ` y `order_multiple` vienen del proveedor—, pero tampoco se modula por
clase.

**Ejemplo.** Un producto de rotación alta y uno de rotación baja, ambos con el mismo proveedor
preferente, reciben el mismo `R_v1 = 7`, el mismo `z_v1 = 1,65` y la misma ventana `N_v1 = 12`. Si sus
recomendaciones difieren, es por su demanda, su inventario o su lead time observado — nunca por una
clase asignada.

**Motivo de selección.** No es una preferencia: es la única opción coherente con lo ya decidido.

1. `docs/04` §3.2 declara `abc_class` y `rotation_class` «**Derivada, opcional**» en ambos casos. No
   dice de qué se derivan, pero el consumo es el único insumo posible para una clasificación por
   importancia o por rotación, y no existe todavía.
2. `DT-029` excluye ambos del Componente 2 precisamente porque ese consumo todavía no existe: quedan
   **nulos** en todo el dataset.
3. Con el campo nulo en el 100 % de los registros, **no hay segmento sobre el que diferenciar**. Una
   política por clase ABC sobre un catálogo sin clase ABC no es una política: es una rama muerta.
4. Calcular una clase provisional para poder diferenciar sería inventar el insumo del que depende la
   diferenciación, que es lo que `CLAUDE.md` §7.4 prohíbe.

**Qué NO resuelve.** `BR-X07` sigue **pendiente de negocio**: si un producto crítico y uno de bajo
valor deben tratarse igual, y si la política varía por clase, por categoría o por criticidad. V1 no
responde a eso; solo declara que **hoy no puede** responderlo y por qué. `docs/06` §15 (elemento 8 de
los pendientes) sigue listando la diferenciación de política como trabajo futuro.

**Cómo podrá reemplazarse.** El reemplazo tiene dos requisitos independientes y en este orden: (a) que
exista un histórico de consumo del que derivar `abc_class` —Componente 3 en adelante—, y (b) que
`BR-X07` se cierre con una política por ámbito. Cumplidos ambos, el cambio es introducir una
resolución de parámetros por ámbito (`producto → clase → global`) delante de las reglas actuales, que
pasan a ser el ámbito `global`. Ninguna fórmula de `V1-01` a `V1-09` cambia.

---

## V1-12 — Sin sobre-recepción

```text
ID:        V1-12
Nombre:    La cantidad recibida no excede la ordenada
Estado:    V1 — cierra BR-X08 para V1 con una interpretación técnica
```

**Objetivo.** Fijar una invariante verificable sobre las recepciones, para que el generador no
produzca un caso cuya interpretación dependa de una regla empresarial inexistente.

**Regla.**

```text
para todo PurchaseOrderItem:
    sum(quantity_received de sus PurchaseOrderReceipt) <= quantity_ordered

V1 no genera ningún escenario de sobre-recepción
el validador (V1-08) rechaza cualquier violación como incidente de datos
```

**Entradas.** `PurchaseOrderItem.quantity_ordered`; `PurchaseOrderReceipt.quantity_received`.

**Salidas.** Una invariante del validador. No produce ninguna cifra de abastecimiento.

**Ejemplo.** Una orden de 100 unidades con recepciones parciales de 40 y 60 es válida (suma 100).
Con recepciones de 40 y 70 es **inválida** (suma 110) y el validador la rechaza señalando el ítem, no
la «tolera» con un margen: V1 no tiene margen que aplicar.

**Motivo de selección.** La especificación ya lo establece, con una condición que V1 no cumple:

- §21 fija `cantidad recibida <= cantidad ordenada` **«salvo que exista un escenario explícito de
  sobre-recepción»**, y **§3.1 (Coherencia)** advierte que «las cantidades recibidas no deben
  contradecir las cantidades ordenadas, salvo que el escenario esté diseñado explícitamente para
  probar una regla de sobre-recepción **pendiente de definición**».
- V1 **no crea ninguno de esos escenarios**: no están en los escenarios mínimos de `V1-07` ni en el
  enum `Scenario` (`DT-023`, 16 ejes, ninguno de sobre-recepción).
- Sin escenario explícito, la excepción no se activa y la desigualdad rige sin excepciones.
- La alternativa —admitir un margen— exigiría **un número** (¿2 %? ¿5 %? ¿una unidad?) que solo el
  negocio puede dar, y §26 advierte que un caso que dependa de una regla no definida «no debe
  utilizarse para afirmar que dicha regla ya está establecida».

**Qué NO resuelve.** `BR-X08` sigue **pendiente de negocio**: si en la operación real se acepta
recibir de más y con qué tolerancia. Es perfectamente posible que la respuesta sea «sí, hasta un 5 %».
V1 no lo niega; V1 dice que **mientras no haya número, el dataset no contiene el caso**. El apartado
«Fuera de V1» de este ADR y §27 de la especificación lo mantienen en la lista de parámetros
pendientes.

**Cómo podrá reemplazarse.** Cerrado `BR-X08`, cambian cuatro cosas acotadas: la invariante del
validador pasa de `≤ quantity_ordered` a `≤ quantity_ordered × (1 + tolerancia)`; el generador gana un
escenario explícito de sobre-recepción; el enum `Scenario` gana su eje; y —esto **sí** toca dos reglas
de cálculo, contra lo que escribí primero— hay que precisar (a) si «completamente recibido» en
`V1-09` pasa a ser `Σ recibido ≥ ordenado` en vez de `=`, y (b) qué hace `V1-02` con una cantidad
pendiente que la sobre-recepción vuelve negativa. Ambas son precisiones de una línea, pero no son
«ningún cambio».

---

## V1-13 — Sin inventario negativo

```text
ID:        V1-13
Nombre:    Las existencias nunca son negativas
Estado:    V1 — cierra BR-X09 para V1 con una interpretación técnica
```

**Objetivo.** Que la reconstrucción del inventario a partir de los movimientos produzca siempre un
saldo interpretable, y que el motor no tenga que decidir qué significa un `on_hand` negativo.

**Regla.**

```text
para todo producto, ubicación e instante del periodo:
    on_hand(t) = sum(movement.quantity con occurred_at <= t)   >= 0

V1 no genera ningún movimiento que lleve el saldo por debajo de cero
el validador (V1-08) rechaza un saldo negativo como incidente de datos
el motor, ante un on_hand negativo, NO calcula: lo señala (docs/06 §14)
```

La fecha que cuenta es **`occurred_at`, no `recorded_at`**: `docs/04` §3.7 distingue ambas y advierte
que «un registro tardío no debe alterar la serie temporal de la fecha equivocada». Sin esa precisión
la invariante sería ambigua para el validador.

**Entradas.** `InventoryMovement.quantity` y su `occurred_at`; el saldo reconstruido de §22.

**Salidas.** Una invariante del validador y una condición de parada del motor. No produce ninguna
cifra de abastecimiento.

**Ejemplo.** Saldo 30, salida solicitada de 50. V1 **no** registra un movimiento de −50 que deje −20:
el generador limita la salida al saldo disponible. Si aun así un saldo negativo apareciera en un
dataset, el validador lo marca y el motor devuelve «no calculado — inventario inconsistente» en lugar
de una cantidad recomendada.

**Motivo de selección.** Las tres fuentes del repositorio apuntan al mismo sitio:

- §26 incluye el inventario negativo entre los casos límite del dataset **«únicamente si
  posteriormente se confirma que debe permitirse»**. Esa confirmación **no se ha producido**, de modo
  que la condición no se cumple y el caso no se genera.
- `docs/06` §14 ya lo trata así en el motor: «Cantidades negativas de inventario → Rechazado como
  inconsistencia de datos, no calculado».
- El criterio de «no calcular y señalar» es el de `docs/06` §14 para datos inconsistentes. **No es
  `BR-009`**: esa regla cubre los **parámetros de política ausentes** (nivel de servicio, umbral de
  riesgo), no los incidentes de datos, y citarla aquí era estirarla más allá de su enunciado.

Generarlo sin esa confirmación crearía casos cuya lectura correcta nadie conoce —¿venta con saldo
pendiente?, ¿error de conteo?, ¿movimiento fuera de orden?—, y cada una implica una política distinta.

**Qué NO resuelve.** `BR-X09` sigue **pendiente de negocio**: si la operación real admite existencias
negativas (habitual cuando se factura antes de registrar la entrada) y cómo deben interpretarse.

**Qué no alcanza esta regla.** `V1-13` habla del **saldo físico `on_hand`**, no de la posición de
inventario `IP_decisión` de `V1-02` ni del derivado `available = on_hand − reserved` de `docs/04`
§3.6, que son magnitudes distintas. En el modelo general `IP_decisión` puede ser negativo cuando lo
comprometido supera lo disponible —así lo dice `V1-02` en sus «Salidas»—, pero **en V1 no puede
serlo**: `V1-02` fija `reserved = 0` y `effective_in_transit ≥ 0`, de modo que con `on_hand ≥ 0` la
posición de inventario de V1 es estructuralmente no negativa. Es una consecuencia de V1, no una
propiedad general, y conviene no confundirlas.

**Cómo podrá reemplazarse.** Cerrado `BR-X09`, el cambio es retirar del validador la invariante
`on_hand(t) ≥ 0` que `V1-08` incorpora por esta regla, añadir el eje de escenario correspondiente al
generador y definir en `docs/06` §14 qué hace el motor con un saldo negativo en lugar de rechazarlo.
Las fórmulas de `V1-01` a `V1-09` no cambian: lo que cambia es el rango admisible de una de sus
entradas.

---

## Reglas pendientes: qué cierra V1 y qué no

Aplicando el criterio del responsable —¿es necesaria para V1? → ¿se resuelve con la documentación? →
¿es decisión de negocio?— las trece reglas pendientes de `business-rules.md` §3 quedan así:

### Cerradas con una regla técnica V1 (4)

| Regla pendiente | Interpretación técnica de V1 | Regla V1 y fundamento en el repositorio |
|---|---|---|
| `BR-X05` — selección de proveedor | Proveedor **preferente activo**; sin él, no se recomienda | **`V1-10`** — `BR-P07` ya lo propone; `DT-028` §2.4 lo garantiza; `docs/06` §14 prevé el caso sin proveedor |
| `BR-X07` — política por segmento | **Política única** para todo el catálogo en V1. No se diferencia por clase ABC ni categoría, y el campo no se elimina del modelo | **`V1-11`** — `abc_class` queda nulo (`DT-029`), de modo que no hay segmento sobre el que diferenciar |
| `BR-X08` — sobre-recepción | **No se permite en V1**: `Σ quantity_received ≤ quantity_ordered`, y el validador lo rechaza | **`V1-12`** — §21 admite la excepción solo «si existe un escenario explícito», y V1 no crea ninguno: por eso la desigualdad rige sin excepción **dentro de V1**, no en la especificación |
| `BR-X09` — inventario negativo | **No se permite**: `on_hand ≥ 0`; un saldo negativo se rechaza como incidente de datos | **`V1-13`** — §26 condiciona su admisión a «si posteriormente se confirma que debe permitirse»; `docs/06` §14 lo trata como inconsistencia |

Las cuatro son **interpretaciones técnicas provisionales**, no políticas confirmadas: el negocio puede
contradecir cualquiera de ellas y el cambio es acotado.

### Pendientes de negocio, puenteadas en V1 (2)

| Regla | Qué falta exactamente | Qué la puentea |
|---|---|---|
| `BR-X01` — nivel de servicio | El **valor** objetivo y **qué definición** se usa: probabilidad de no agotar en un ciclo, o proporción de demanda satisfecha. Producen stocks distintos y solo el negocio puede elegir | `z_v1 = 1,65` (`V1-05`, `ASSUMPTION-022`) |
| `BR-X02` — política de revisión | Si la revisión es continua o periódica y con qué frecuencia se emiten pedidos hoy | Revisión periódica con `R_v1 = 7 días` (`V1-03`, `ASSUMPTION-021`) |

### No necesarias para V1 (7)

`BR-X03` (umbrales de riesgo: V1 calcula la cantidad pero **no clasifica** el riesgo) · `BR-X04`
(costos: no hay optimización) · `BR-X06` (calendario laboral: V1 usa días naturales) · `BR-X10`
(sustitutos) · `BR-X11` (presupuesto y capacidad) · `BR-X12` (horizonte de aprobación: V1 no emite
órdenes) · `BR-X13` (horizonte de cobertura: `V1-03` lo saca del camino al elegir la rama periódica).

**Balance: 4 cerradas, 2 puenteadas, 7 aplazadas.** Ninguna bloquea el Componente 2.

---

## Casos de prueba de las reglas V1: dónde vivirá cada uno

El cierre del 2026-09-21 enumeró **trece casos de prueba** que estas reglas deben satisfacer. Conviene
decirlo sin rodeos antes de la tabla:

> **Ninguno de los trece es ejecutable hoy, y no se han escrito.** Todos prueban código que no
> existe: el motor de abastecimiento es **Fase 4** y el generador es el **Componente 2 en adelante**.
> `data/synthetic/generator/` no contiene ningún generador. Crear ahora un paquete `supply_engine/`
> para alojar estas pruebas violaría `CLAUDE.md` §6.2 —«si una carpeta o una capa no tiene un uso hoy,
> no se crea»— y §17 —«no iniciar una fase posterior sin autorización»—. La suite actual sigue en
> **54 pruebas de `DatasetConfig`**, todas en verde.

Lo que sí puede hacerse hoy, y es lo que hace esta tabla, es **fijar el caso y su dueño** para que
ninguno se pierda cuando su componente se construya:

| # | Caso | Resultado esperado | Regla | Dueño |
|---|---|---|---|---|
| 1 | Par producto-proveedor con **0** observaciones de lead time | `AGREED_FALLBACK`; se usa `agreed_lead_time_days` | `V1-09` | Motor (Fase 4) |
| 2 | Con **1** observación | `AGREED_FALLBACK` | `V1-09` | Motor (Fase 4) |
| 3 | Con **2** observaciones | `AGREED_FALLBACK` (el mínimo es 3) | `V1-09` | Motor (Fase 4) |
| 4 | Con **3** observaciones | `OBSERVED`; mediana redondeada al alza | `V1-09` | Motor (Fase 4) |
| 5 | Con **más de 12** observaciones | Solo las 12 más recientes por fecha de finalización | `V1-09.1` | Motor (Fase 4) |
| 6 | Mediana observada **> 90 días** | Se usa 90 | `V1-09.2` | Motor (Fase 4) |
| 7 | Trazabilidad del tope | La salida indica `LEAD_TIME_CAPPED` y el valor sin topar | `V1-09.2` | Motor (Fase 4) |
| 8 | Producto **con** proveedor preferente activo | Se calcula con `MOQ`, múltiplo y lead time de esa relación | `V1-10` | Motor (Fase 4) |
| 9 | Producto con proveedores pero **ninguno preferente** | No se recomienda; se señala el dato faltante | `V1-10` | Motor (Fase 4) · **sin caso en el dataset**, ver abajo |
| 10 | Producto **sin proveedor activo** | No se recomienda; se señala el dato faltante | `V1-10` | Motor (Fase 4) |
| 11 | La clase ABC **no influye** en el resultado | Dos entradas idénticas salvo `abc_class` producen la misma recomendación | `V1-11` | Motor (Fase 4) · **sin caso en el dataset**, ver abajo |
| 12 | **Sobre-recepción** en el dataset | El validador la rechaza señalando el ítem | `V1-12` | Componente 8 (validador) |
| 13 | **Inventario negativo** reconstruido | El validador lo rechaza; el motor no calcula | `V1-13` | Componente 8 y motor |

Los casos 1 a 11 pertenecen al **motor de abastecimiento**, que no está autorizado. Los casos 12 y 13
pertenecen al **Componente 8 (validador)**, que sí está en la Fase 1 pero aún no ha comenzado; ambos
están recogidos como invariantes en `V1-08`, de modo que llegarán con él.

**Dos niveles de prueba, que conviene no confundir.**

1. **Pruebas unitarias del motor** (casos 1 a 11). Construyen sus entradas **a mano**, con el
   resultado esperado calculado a mano. Es lo que `docs/06` §14 ya prescribe —«cada uno de estos
   casos tendrá una prueba unitaria con resultado esperado calculado a mano»— y lo que exige
   `CLAUDE.md` §12.3. No dependen del generador.
2. **Comprobaciones del validador sobre el dataset** (casos 12 y 13). Sí dependen de que exista un
   dataset, y son invariantes de `V1-08`.

**Dos casos no tendrán representación en el dataset, y es deliberado.** No invalida su prueba
unitaria, pero conviene dejarlo escrito para que nadie lo busque en los CSV:

- **Caso 11.** `abc_class` está **vacío en el 100 %** de las filas (`V1-11`, `DT-024` columna 8), de
  modo que no existe ni puede existir un par de productos del dataset que difieran en esa columna. La
  prueba construye las dos entradas del motor directamente. Que el caso sea *invraizable* en los datos
  es, de hecho, la forma más fuerte de cumplir `V1-11`.
- **Caso 9.** Con las políticas vigentes tampoco existe: `DT-028` §2.4 da a todo producto de las
  clases A, B y C **exactamente un** proveedor preferente, y §2.5 da a la clase D una única relación
  **inactiva** —que es el caso 10, no el 9—. Ningún producto del dataset tiene proveedores activos sin
  preferente. La prueba unitaria sigue siendo necesaria porque el motor debe comportarse bien ante una
  entrada que el dataset no produce.

**Dependencia de datos para las pruebas de integración.** Cuando se quiera comprobar estos casos de
extremo a extremo y no solo unitariamente, los **casos 2 a 7** requieren órdenes y recepciones
históricas —el caso 1 es justo el contrario: requiere su **ausencia**, y es construible con solo las
entidades maestras del Componente 2—. Ese insumo lo producen los **Componentes 5 (órdenes de compra)
y 6 (comportamiento del proveedor)**, no el 5 en solitario.

---

## Lo que queda explícitamente FUERA de V1

Ninguno de estos elementos bloquea la construcción del generador ni del flujo básico. Se listan para
que una decisión pendiente no paralice el trabajo:

| Fuera de V1 | Dónde vive la decisión |
|---|---|
| EOQ y lote económico | `docs/06` §8, «restricciones no incluidas» |
| Optimización de costos | `BR-X04` |
| Selección avanzada de proveedores y *scoring* | `BR-X05`; `BR-P07` usa el preferente |
| Productos sustitutos | `BR-X10`, `docs/04` §8.6 |
| Restricciones de presupuesto y de capacidad | `BR-X11` |
| Calendario laboral y festivos | `BR-X06`; V1 usa días naturales |
| Múltiples ubicaciones | `ASSUMPTION-006`, `DT-P09`; V1 usa una |
| Lotes y caducidad | `docs/04` §8.4; `shelf_life_days` queda nulo (`DT-029`) |
| Múltiples monedas | `docs/04` §8.5; `currency` queda nulo (`DT-029`) |
| Políticas diferenciadas por clase ABC | `BR-X07`; `V1-11`; `abc_class` queda nulo (`DT-029`) |
| Modelos de ML avanzados | Fase 5; V1 no entrena nada |
| Optimización del nivel de servicio | `BR-X01`; V1 usa `z_v1` fijo |
| Detección avanzada de drift | `docs/05` §11 |
| Optimización conjunta forecast + abastecimiento | `DT-020`, Nivel 2 |
| Variabilidad del lead time en el stock de seguridad (`σ_L`) | `BR-P02`, `docs/06` §6.2 |
| Tratamiento de la demanda censurada | `DT-011` |
| Tolerancia de sobre-recepción | `BR-X08`; `V1-12` fija `≤` sin margen |
| Inventario negativo | `BR-X09`; `V1-13` fija `on_hand ≥ 0` |
| Umbrales de riesgo y de sobreinventario | `BR-X03` |

---

## Consecuencias

**Positivas**

1. La cadena `Forecast → Inventory → Supply Engine → Recommendation` queda **calculable de extremo a
   extremo** sin ninguna decisión de negocio nueva.
2. Se cierra la cuestión **C** de la auditoría anterior: «MOQ > necesidad» pasa de no computable a
   computable, porque `raw_need` ya tiene definición operativa.
3. Se corrige una contradicción interna de `docs/06` anterior a este bloque de trabajo.
4. El glosario gana la definición de «necesidad bruta», término que la especificación usaba con seis
   redacciones distintas.
5. Cada regla declara su sustituto, de modo que cerrar una regla pendiente es un cambio acotado.

**Costos aceptados**

1. **Dos parámetros sin respaldo del negocio** (`R_v1 = 7`, `z_v1 = 1,65`). Mitigado con el etiquetado
   y con `ASSUMPTION-021` y `ASSUMPTION-022`.
2. **V1 elige implícitamente revisión periódica**, que es `BR-X02`. Declarado en `ASSUMPTION-021`.
3. **V1 usa la variabilidad de la demanda, no el error de pronóstico**, que §6.4 señala como la
   fuente más pertinente. Inevitable: no hay modelo todavía.
4. **Ninguna salida de V1 puede presentarse como recomendación de negocio.** Es la consecuencia más
   importante y la que hay que repetir: `BR-009` sigue rigiendo fuera del entorno sintético.

**Qué invalidaría estas reglas**

Que el negocio confirme revisión continua (cae `V1-03`), que `DT-010` se cierre con otra fuente de
incertidumbre (cae `V1-05`), o que `BR-X06` revele un calendario laboral con días no operativos (cae
el prorrateo uniforme de `V1-04`).

## Lo que esta decisión NO hace

- **No** confirma ninguna regla de `knowledge/business-rules.md` §3. Las trece siguen figurando como
  pendientes: cuatro de ellas tienen ahora una **interpretación técnica de V1** (`V1-10` a `V1-13`),
  que es una regla provisional del proyecto, no una política del negocio. «Cerrada para V1» y
  «confirmada» no son lo mismo.
- **No** modifica `config.py`, `dataset_config.yaml` ni las pruebas.
- **No** modifica el enum `Scenario` ni la cobertura declarada en `dataset_config.yaml`.
- **No** modifica `DT-023` a `DT-030`.
- **No** implementa el Componente 2, ni el motor, ni ningún forecast.
- **No** resuelve la parte de negocio de la cuestión **B**: `V1-06` adopta la fórmula vigente y
  corrige el criterio de §14, pero si el responsable decidiera exigir que `MOQ` sea múltiplo de
  `order_multiple`, esa sería una decisión suya. *(La cuestión **A** —descomposición de componentes—
  sí quedó resuelta, pero no por este ADR: la confirmó el responsable el 2026-09-19, ocho componentes
  sin rediseño.)*
