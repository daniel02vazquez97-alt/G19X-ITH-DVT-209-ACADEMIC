# DT-027 — Vigencia de `Product`: `valid_from` y `valid_to`

- **Fecha:** 2026-09-18 · **Enmendada:** 2026-09-24 (restricción 3)
- **Estado:** `ACEPTADA` — con una **enmienda aprobada** el 2026-09-24, registrada al final de la
  sección *Restricciones*. La decisión original no se sustituye: se acota.
- **Fase del roadmap:** Fase 1 — Datos (Componente 2), con efecto en las Fases 2 y 5
- **Afecta a:** `docs/04-modelo-datos.md` §3.2, `knowledge/dataset-specification.md` §§7.2, 20 y 34,
  el diseño de los Componentes 2, 3, 4, 5 y 8
- **Entrada resumida:** `docs/15-decisiones-tecnicas.md` → `DT-027`
- **Relacionada con:** `DT-024` (contrato de salida), `DT-028` §7 (cómo las puebla el Componente 2),
  `DT-036` (políticas del Componente 4, origen de la enmienda), `BR-P10` (pendiente)

---

## Decisión

`Product` incorpora dos campos de **vigencia de dominio**:

```text
valid_from    fecha, obligatorio
valid_to      fecha, nulo = vigente sin fecha de fin prevista
```

Son **distintos de `created_at` / `updated_at`**, que siguen siendo auditoría técnica del registro y
**no se reutilizan** como sustituto de la vigencia.

## Contexto

`knowledge/dataset-specification.md` exige la vigencia en dos sitios:

- **§7.2**, contenido mínimo de un producto: «* fechas de creación **o vigencia** según corresponda.»
- **§20**, coherencia temporal:
  - «**Productos.** Las fechas de vigencia deben ser compatibles con los eventos asociados.»
  - «**Consumo.** El consumo debe ocurrir dentro del **periodo de existencia del producto** y
    ubicación correspondiente.»

`docs/04-modelo-datos.md` §3.2, en cambio, solo ofrecía `created_at` y `updated_at`, etiquetados
«Auditoría». No existía ningún campo que representara el periodo de existencia del producto.

La auditoría del Componente 2 (2026-09-17) registró la carencia como bloqueante **B-3**: sin ella, el
Componente 2 no sabe qué fechas emitir, el Componente 3 no tiene contra qué acotar la serie de
demanda y el Componente 8 no puede comprobar §20.

*(Precisión del 2026-09-23: cuando se escribió este ADR se daba por hecho que el Componente 3
produciría el consumo. `DT-034` reparte esa responsabilidad de otro modo — el Componente 3 produce la
demanda **latente** y el Componente 4 el consumo observado — pero la carencia que motivó B-3 y su
solución no cambian: ambos componentes necesitan la ventana de vigencia.)*

## Alternativas consideradas

| | Alternativa | Ventajas | Inconvenientes |
|---|---|---|---|
| (a) | **Añadir `valid_from` / `valid_to`** | Representa exactamente lo que §20 exige comprobar. Coherente con `InventoryPolicy` (§3.12), que ya usa `valid_from` / `valid_to` para su vigencia | Dos columnas más en la entidad más usada del modelo |
| (b) | Reutilizar `created_at` como inicio de vigencia | Cero cambios | Confunde dos conceptos que `docs/04` §5.4 separa deliberadamente. Con una carga histórica, `created_at` es la fecha de la carga y no dice nada sobre cuándo existe el producto. **§20 quedaría sin poder comprobarse** |
| (c) | Derivar la vigencia del histórico (primer y último consumo) | Ningún campo nuevo | Circular: §20 quiere validar el histórico **contra** la vigencia. Derivar una de la otra hace la validación tautológica |
| (d) | Usar solo `is_active` | Ya existe | Un booleano no tiene fecha: no permite responder «¿existía este producto el 2024-06-01?», que es justo lo que §20 pregunta |

## Razón

El argumento decisivo es que **(b), (c) y (d) hacen imposible la validación de §20**, cada una por un
motivo distinto: (b) mide otra cosa, (c) es circular y (d) no tiene resolución temporal.

Pesó además la **coherencia interna del modelo**: `InventoryPolicy` (`docs/04` §3.12) ya resuelve su
vigencia con `valid_from` / `valid_to`, y `BR-P11` establece que las políticas son versionadas en el
tiempo. Usar el mismo par de nombres para el mismo concepto en `Product` no introduce vocabulario
nuevo: lo reutiliza.

La distinción entre vigencia y auditoría no es una sutileza: es la misma que `docs/04` §5.4 impone
entre `occurred_at` y `recorded_at`, y por la misma razón — un registro tardío no debe alterar la
serie temporal de la fecha equivocada.

## Semántica

| Campo | Tipo lógico | Obligatorio | Semántica de `NULL` |
|---|---|---|---|
| `valid_from` | Fecha (`DATE`, sin hora) | **Sí** | No admite `NULL` |
| `valid_to` | Fecha (`DATE`, sin hora) | No | **`NULL` = el producto sigue vigente y no hay fecha de fin prevista.** No significa «desconocido» |

**Intervalo cerrado por la izquierda y por la derecha:** un producto existe en el negocio durante
`[valid_from, valid_to]`, ambos inclusive. Con `valid_to` nulo, el intervalo es
`[valid_from, ∞)`.

**Fechas sin hora.** La granularidad del consumo es diaria (§5 de la especificación:
`Producto × Ubicación × Día`); una vigencia con hora introduciría una precisión que ningún dato del
sistema tiene.

### Restricciones

1. `valid_from` no nulo.
2. Si `valid_to` no es nulo, `valid_from ≤ valid_to`. Como el intervalo es cerrado por ambos
   extremos, un producto vigente un solo día se representa con `valid_to = valid_from`, y esa es una
   vigencia válida, no un caso degenerado. Lo prohibido es `valid_to < valid_from`, que no describe
   ningún intervalo.
3. Todo evento asociado al producto ocurre dentro del intervalo de vigencia (§20). **Enmendada el
   2026-09-24**: ver más abajo.
4. La vigencia es **inmutable hacia atrás** cuando hay histórico: estrecharla dejando eventos fuera
   invalida ese histórico y es un incidente de datos, no una corrección.

Estas cuatro se establecen **sin inventar ninguna regla empresarial**: las tres primeras son
consecuencias lógicas de que un intervalo sea un intervalo, y la cuarta se deriva de `BR-005`
(histórico inmutable) y `DT-006`.

### Enmienda del 2026-09-24 — recepciones de órdenes en vuelo

**Trazabilidad de la enmienda**

```text
DT-027 original (2026-09-18)
    restricción 3: «Todo evento asociado al producto ocurre dentro del intervalo de vigencia (§20).»
        ↓
Enmienda aprobada por el responsable (2026-09-24), a raíz del diseño del Componente 4
        ↓
Nueva restricción 3, con una excepción única y acotada
```

**Nueva restricción 3, texto vigente**

> Todo evento asociado al producto ocurre dentro del intervalo de vigencia (§20), **con una única
> excepción**: una orden de compra emitida **dentro** de `[valid_from, valid_to]` completa su ciclo
> causal aunque sus recepciones, y los movimientos `RECEIPT` derivados de ellas, ocurran **después**
> de `valid_to`. La trazabilidad entre la orden emitida en vigencia y su recepción posterior debe
> conservarse.

**Alcance estricto de la excepción**

```text
Purchase Order emitida dentro de valid_from..valid_to
        ↓
Receipt derivado causalmente de esa PO
        ↓
Receipt (y su InventoryMovement) pueden ocurrir después de valid_to
```

La excepción **no autoriza**, después de `valid_to`: nueva demanda · nuevo consumo · nuevas órdenes ·
nuevas relaciones con proveedores · ningún otro movimiento arbitrario. Y **no autoriza** cancelar la
orden artificialmente, eliminar la recepción, truncar el movimiento ni convertir la recepción en un
ajuste.

**Por qué.** El diseño del Componente 4 (`DT-036`) hizo aflorar la contradicción: un producto dado de
baja el 2025-04-02 con una orden en vuelo emitida días antes recibe mercancía semanas después de su
`valid_to`. La restricción 3 original prohibía ese movimiento, y las tres salidas posibles —prohibir
la orden, truncar la recepción o admitir el movimiento— no son equivalentes: las dos primeras
**borran un hecho** y contradicen la regla aprobada de que las órdenes previas completan su ciclo. La
tercera describe lo que físicamente ocurre: la mercancía pedida llega aunque el SKU se dé de baja.

La enmienda **no debilita** la restricción para ningún otro caso. Sigue siendo cierto que el consumo
y las líneas de orden caen dentro de la vigencia, y que estrechar la vigencia dejando eventos fuera
es un incidente de datos (restricción 4, intacta).

**Sincronizada en:** `knowledge/dataset-specification.md` §34, *Integridad temporal*.

### Relación con `is_active`

**Deliberadamente no se define.** `is_active` es un indicador operativo y la vigencia es un intervalo
temporal; qué relación exacta guardan —si desactivar obliga a cerrar `valid_to`, si un producto
puede estar inactivo y vigente, si la reactivación abre un intervalo nuevo— **depende de cómo el
negocio marque un producto como descontinuado**, que es la regla **propuesta** `BR-P10`, sin
confirmar.

Fijar esa relación ahora sería convertir una hipótesis en requisito, contra `CLAUDE.md` §6.4.

Lo que sí se define, y solo para el dataset sintético, es cómo el Componente 2 los puebla de forma
coherente: `DT-028` §7.1. Eso es una política de generación, no una regla de negocio.

## Consecuencias

**Positivas**

1. B-3 resuelto: el Componente 2 sabe qué emitir y el Componente 8 tiene contra qué validar §20.
2. La validación «el consumo cae dentro de la existencia del producto» pasa a ser comprobable.
3. `created_at` recupera su significado: auditoría del registro, no del negocio.
4. Prepara el segmento «Nuevo / histórico corto» de `docs/05` §4, que necesita saber desde cuándo
   existe un producto. **No se genera en esta versión** (`DT-028` §7.2), pero el modelo ya lo admite.

**Costos aceptados**

1. Dos columnas más en `Product`, y en `products.csv` (`DT-024`).
2. Toda entidad que referencie un producto queda sujeta a la restricción 3, lo que añade una
   validación al Componente 8 y, en la Fase 2, probablemente una comprobación en base de datos.
3. La relación con `is_active` queda abierta, y eso es una ambigüedad consciente hasta que se cierre
   `BR-P10`.

**Qué invalidaría esta decisión**

Que `BR-P10` se confirme con un criterio que haga redundante uno de los dos campos —por ejemplo, si
el negocio gestiona las bajas exclusivamente con un indicador y sin fechas. En ese caso habría que
revisar si `valid_to` sigue teniendo un origen.

## Lo que esta decisión NO hace

- **No** define ninguna política empresarial de altas y bajas de productos: `BR-P10` sigue pendiente.
- **No** fija la relación entre `is_active` y la vigencia.
- **No** añade vigencia a `Supplier`, `Category`, `ProductSupplier` ni `Location`. Ninguna sección de
  la especificación la exige para ellas, y añadirla sería ampliar el modelo sin necesidad.
- **No** decide tipos SQL ni restricciones de base de datos: eso es la Fase 2.
- **No** implementa nada.
