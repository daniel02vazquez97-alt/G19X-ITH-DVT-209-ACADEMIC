# DT-034 — `Demand`: la demanda latente se persiste, separada del consumo observado

- **Fecha:** 2026-09-23 · **Pendientes cerrados:** 2026-09-24 (mecanismo de recorte de la demanda y
  contrato de `consumption.csv`, ambos en `DT-038`)
- **Estado:** `ACEPTADA`
- **Fase del roadmap:** Fase 1 — Datos (Componente 3: *Demand Generator*)
- **Afecta a:** `docs/04-modelo-datos.md`, `knowledge/dataset-specification.md`, el diseño de los
  Componentes 3 a 8, y la Fase 5 (entrenamiento del modelo)
- **Entrada resumida:** `docs/15-decisiones-tecnicas.md` → `DT-034`
- **Relacionada con:** `DT-011` (demanda censurada), `DT-024` (contrato de salida), `DT-025`
  (manifiesto), `DT-027` (vigencia), `DT-030` / `DT-032` (determinismo), `DT-035` (políticas de
  generación de demanda)

> Vive como archivo propio porque incluye el contrato de columnas de una entidad nueva, que es
> justo el caso que `docs/decisions/ADR-template.md` contempla para separar un ADR del registro.

---

## Decisión

El generador persiste **dos series distintas**, y la distinción entre ellas es la razón de ser de
esta decisión:

| Archivo | Qué contiene | Quién lo produce |
|---|---|---|
| `demand.csv` | **Demanda latente**: la cantidad que se habría demandado si el inventario nunca hubiera limitado la satisfacción de la demanda | **Componente 3** |
| `consumption.csv` | **Demanda satisfecha**: lo que las existencias permitieron entregar, con `is_stockout_affected` cuando hubo desabasto | **Componente 4** |

```text
C2 ──> products.csv, locations.csv
          │
          ▼
C3 ──> demand.csv            demanda latente
          │
          ▼
C4 ──> inventario, stockouts, consumption.csv     demanda satisfecha
```

Con un ejemplo, que es la forma más corta de fijar la semántica:

```text
demanda latente (C3)   = 100
existencias (C4)       =  70
consumo satisfecho (C4)=  70     is_stockout_affected = true
```

**`demand.csv` no es un archivo intermedio desechable.** Es un dataset persistente del generador,
con su contrato de columnas, su entrada en `manifest.json` y su `sha256`, inspeccionable y validable
como cualquier otro.

**El Componente 3 no escribe `consumption.csv`**, no conoce las existencias, no simula desabastos y
no lleva la columna `is_stockout_affected`.

## Contexto

`docs/04` §3.8 enuncia el problema con precisión y lo deja sin resolver en el modelo:

> «Lo registrado es la demanda **satisfecha**. Durante un desabasto, la demanda real fue mayor que la
> registrada. La bandera `is_stockout_affected` permite tratar esos periodos como **censurados** en
> el entrenamiento en lugar de aprender que "la demanda bajó". Ignorar esto sesga el modelo a la baja
> justo en los productos más críticos.»

§9 de la especificación lo repite desde el lado del dataset: «el consumo registrado durante un
stockout no debe interpretarse automáticamente como demanda real completa».

El modelo de datos tenía **una sola** entidad para todo esto, `Consumption`, y ninguna para la
demanda latente. Eso dejaba una circularidad sin dueño —demanda → inventario → desabasto → consumo
censurado → movimientos → inventario— y, sobre todo, dejaba el sesgo por censura **reconocido pero no
medible**: sin la serie latente, la diferencia entre lo que se habría demandado y lo que se entregó
no existe en ninguna parte y no puede cuantificarse.

La auditoría previa al Componente 3 (2026-09-21) registró esa circularidad como el primer bloqueante
del componente, precisamente porque ningún documento decía quién la rompía.

## Alternativas consideradas

| | Alternativa | Ventajas | Inconvenientes |
|---|---|---|---|
| (a) | **C3 persiste la demanda latente; C4 la transforma en consumo** | La censura queda **medible**: ambas series existen y su diferencia es el sesgo. Cada componente tiene un dueño único. C3 no necesita saber nada de inventario | Una entidad más en el modelo, que no existía. Un archivo más que mantener coherente |
| (b) | C3 produce una serie en memoria y solo C4 escribe `consumption.csv` | Ningún archivo nuevo; el modelo de datos no cambia | La demanda latente desaparece en cuanto C4 termina. El sesgo por censura vuelve a ser inauditable, que es el problema que `DT-011` mantiene abierto. Además C3 dejaría de tener salida propia, contra el patrón «un componente, sus archivos» de `DT-024` |
| (c) | C3 escribe `consumption.csv` y C4 lo reescribe anotando la censura | Un solo archivo de consumo | Un componente modificaría el archivo de otro, algo que ningún contrato contempla. Y la serie original se pierde en la reescritura, de modo que (c) tiene el mismo defecto que (b) más un acoplamiento nuevo |
| (d) | C3 y C4 generan desabastos cada uno por su lado | — | Dos componentes dueños de la misma verdad. Se descarta sin más |

## Razón

Se elige (a) por una razón que las otras tres no pueden dar: **hace medible el sesgo por censura en
lugar de limitarse a advertirlo.**

`DT-011` está `PENDIENTE` en su parte de método —ignorar, excluir, imputar o tratar como observación
censurada— y decidirlo «con datos» es exactamente lo que exige. Con ambas series en disco, ese método
puede **evaluarse**: se entrena sobre el consumo, se compara contra la demanda latente y se mide cuál
de las cuatro alternativas recupera mejor la verdad. Con la opción (b) o la (c) no hay contra qué
comparar, y la elección del método volvería a ser una preferencia.

Lo mismo vale para `docs/05` §4, que clasifica la demanda por comportamiento, y para la evaluación de
Nivel 2 de `DT-020`: el dataset sintético es el **único** lugar donde la demanda latente es
conocible. Con datos reales no lo será nunca. Desaprovecharlo sería renunciar al principal beneficio
metodológico de tener un generador.

La separación tiene además una consecuencia de diseño que simplifica dos componentes a la vez: C3 no
necesita ningún concepto de inventario, y C4 recibe una entrada explícita en vez de tener que generar
demanda y consumirla en el mismo paso.

## Contrato de `demand.csv`

Convenciones de formato: las de `DT-024`, **sin cambios ni excepciones** — UTF-8 sin BOM, separador
coma, LF, cabecera obligatoria, nulos como campo vacío, fechas `YYYY-MM-DD`, enteros sin separador.

| # | Columna | Tipo | Notas |
|---|---|---|---|
| 1 | `id` | entero ≥ 1 | Secuencial desde 1 en el orden del archivo |
| 2 | `product_id` | entero ≥ 1 | FK → `products.id` |
| 3 | `location_id` | entero ≥ 1 | FK → `locations.id` |
| 4 | `occurred_on` | fecha | Granularidad **diaria** (§4, §5) |
| 5 | `quantity` | **entero ≥ 0** | Demanda latente del día. Ver *Cantidades enteras* |
| 6 | `data_origin` | texto | Constante `SYNTHETIC` (`DT-026`) |

- **Clave de negocio:** el par-terna (`product_id`, `location_id`, `occurred_on`), única. Es la
  granularidad que §5 fija literalmente: «Producto × Ubicación × Día».
- **Orden de filas:** ascendente por esa clave; el `id` se asigna después siguiendo ese mismo orden,
  como en `DT-024`.
- **Serie densa:** existe una fila por cada día en que el producto está vigente, con `quantity = 0`
  los días sin demanda. §8.5 exige «comprobar que una gran cantidad de ceros **no sea interpretada
  automáticamente como ausencia de producto**»; si los días sin demanda se omitieran, ausencia y cero
  serían indistinguibles en el archivo y esa exigencia sería incomprobable.

### Columnas deliberadamente ausentes

| Columna | Por qué no está |
|---|---|
| `is_stockout_affected` | Pertenece a `Consumption` (`docs/04` §3.8) y la fija el Componente 4. En `demand.csv` sería el Componente 3 afirmando algo sobre unas existencias que no conoce |
| `scenario` | `DT-025` lo prohíbe en **toda** entidad: «no se añade un campo `scenario` a ninguna» |
| `channel` | Existe en `Consumption` y allí es opcional. La demanda latente no tiene canal: el canal es una propiedad de la entrega, no de la necesidad |
| `abc_class`, `rotation_class` | Derivadas del consumo y nulas por `DT-029`. C3 no las lee ni las escribe |

### Periodo: intervalo semiabierto

```text
[start_date, end_date)
```

El inicio se incluye, el fin **no**. Con 2023-01-01 → 2026-01-01 el último día generado es
**2025-12-31** y 2026-01-01 no aparece nunca.

No es una elección nueva: `Period.days` ya devolvía `(end − start).days`, que es el cardinal del
intervalo semiabierto, y con la configuración vigente da 1096 días = 36 meses exactos, coherente con
`ASSUMPTION-003` (24–36 meses). Lo que hace esta decisión es **enunciarlo**, porque `config.py` solo
exige `start < end` y cada componente habría tenido que adivinarlo.

### Vigencia del producto

La serie de un producto vive dentro de `[valid_from, valid_to]`, **ambos extremos incluidos**
(`DT-027`), y abierta por la derecha cuando `valid_to` es nulo. §34 lo exige para todo evento de un
producto.

Un producto inactivo recibe por tanto serie **hasta su `valid_to` y ninguna después**, que es
literalmente lo que pide §18: «un producto inactivo debe conservar su información histórica».

### Cantidades enteras

`quantity` es entero para **toda** unidad de medida en V1.

`DT-024` declara expresamente que su contrato de formato **no cubre** los decimales no monetarios, y
`docs/04` §7 deja las cantidades abiertas: «en `numeric` si el negocio admite fracciones; en entero si
no. **Decidir por unidad de medida**». V1 decide: enteros.

**Esto no afirma que los productos reales se midan en unidades enteras.** Es una propiedad del
dataset sintético, del mismo rango que los valores de `DT-028`: un producto con `unit_of_measure = KG`
tendrá cantidades enteras de kilogramos porque el generador no produce fracciones todavía, no porque
el negocio lo haya dicho. Admitir fracciones exigiría ampliar el contrato de formato de `DT-024` con
un decimal no monetario, y eso es una decisión propia que hoy no hace falta tomar.

## Consecuencias

**Positivas**

1. El sesgo por censura pasa de advertido a **medible**, que es lo que `DT-011` necesita para poder
   cerrarse con datos en lugar de por preferencia.
2. C3 y C4 tienen dueños disjuntos: ninguna situación de desabasto puede generarse dos veces.
3. La Fase 5 puede entrenar sobre la definición correcta de demanda y comparar contra la observada.
4. `demand.csv` es auditable: tiene contrato, `sha256` en el manifiesto y validador futuro.

**Costos aceptados**

1. **Una entidad nueva en el modelo de datos.** `Demand` no existía en `docs/04`; se añade en el
   mismo cambio, conforme a `CLAUDE.md` §8.
2. **Es el archivo más grande del dataset**: con la escala vigente, 108 235 filas y unos 3,5 MB
   frente a los pocos kilobytes de las entidades maestras. Es el precio de la granularidad diaria que
   §5 exige, y no se versiona (`.gitignore`).
3. **`Demand` no tiene equivalente con datos reales.** La demanda latente es conocible solo porque la
   generamos nosotros. Cuando lleguen datos reales, `demand.csv` no tendrá contrapartida — y eso es
   correcto: es un artefacto del entorno sintético, no una entidad de negocio. Conviene que nadie lo
   lea como si fuera un registro histórico de la organización.

**Qué invalidaría esta decisión**

Que se decida que el dataset sintético no debe contener información que los datos reales no podrán
tener. Es un argumento legítimo —el dataset debe poder sustituirse sin rediseñar nada (`BR-007`)— y la
respuesta es que ninguna **regla de negocio** depende de `demand.csv`: lo usan el Componente 4 y la
evaluación metodológica de la Fase 5, no el motor de abastecimiento.

## Lo que esta decisión NO hace

- **No** implementa el Componente 4. ~~Ni define el contrato de `consumption.csv`.~~ **Cerrado el
  2026-09-24:** el contrato de `consumption.csv` está en **`DT-038`** §4.
- ~~**No** decide cómo C4 transforma demanda latente en satisfecha.~~ **Cerrado el 2026-09-24** por
  decisión del responsable, y registrado en `DT-038` §4:

  ```text
  consumption(t) = min( demanda_latente(t), on_hand_antes_del_consumo(t) )
  lost_sales(t)  = demanda_latente(t) − consumption(t)     ← derivable, NO se almacena
  ```

  El recorte es **por día y sin backlog**: la demanda no satisfecha **se pierde**, no se arrastra al
  día siguiente y no se acumula en ninguna cola. De las tres alternativas que este ADR dejó abiertas,
  queda elegida la tercera.
- **No** resuelve `DT-011`: el método de tratamiento de la demanda censurada sigue pendiente. Lo que
  hace es dejar los datos que permitirán decidirlo.
- **No** fija ningún parámetro de generación de demanda: eso es `DT-035`.
- **No** añade `is_stockout_affected` a ninguna entidad nueva ni lo quita de `Consumption`.
- **No** amplía `DatasetConfig` ni modifica el Componente 2.
