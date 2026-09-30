# DT-024 — Contrato de salida del dataset sintético: un CSV por entidad

- **Fecha:** 2026-09-18
- **Estado:** `ACEPTADA`
- **Fase del roadmap:** Fase 1 — Datos (Componente 2: *Catalog Generator*)
- **Afecta a:** `knowledge/dataset-specification.md` §41, `docs/04-modelo-datos.md`, el diseño de los
  Componentes 2 a 8, y el proceso de ingesta de la Fase 1
- **Entrada resumida:** `docs/15-decisiones-tecnicas.md` → `DT-024`
- **Relacionada con:** `DT-025` (metadata de generación), `DT-026` (`data_origin`), `DT-027`
  (vigencia de `Product`), `DT-028` (políticas de generación sintética), `DT-029` (alcance del
  Componente 2)

> Este ADR vive como archivo propio porque incluye el contrato de columnas de las cinco entidades
> maestras, que no cabe en el registro sin inflarlo. `docs/decisions/ADR-template.md` contempla ese caso.

---

## Decisión

El dataset sintético se materializa como **un archivo CSV independiente por entidad**. Junto a ellos
se escribe un único `manifest.json` con la metadata de generación (`DT-025`).

**No se adopta JSON como formato de los datos de las entidades.** JSON se usa exclusivamente para el
manifiesto, que no es una entidad.

## Contexto

§40 de `knowledge/dataset-specification.md` condiciona la implementación del generador a que se
definan antes, entre otras cosas, la «estructura física de los archivos generados» y el «formato de
intercambio». La auditoría del Componente 2 (2026-09-17) verificó que **ningún documento del
repositorio los definía**, y registró la carencia como bloqueante **B-1**.

Sin esta decisión el Componente 2 no tiene salida que producir.

## Alternativas consideradas

| | Alternativa | Ventajas | Inconvenientes |
|---|---|---|---|
| (a) | **Un CSV por entidad** | Una tabla por archivo, que es exactamente la forma del modelo relacional de destino (Fase 2). Legible sin herramientas. `COPY` de PostgreSQL lo carga directamente. Diff línea a línea | No lleva tipos: todo es texto y hay que declarar las convenciones (esta decisión lo hace) |
| (b) | Un único JSON con las cinco colecciones | Tipos nativos; un solo archivo | Un documento anidado que hay que aplanar para cargarlo en tablas; ilegible a partir de cierto tamaño; no se puede inspeccionar por partes |
| (c) | Parquet | Tipado, comprimido, eficiente | Añade una dependencia (`pyarrow`/`pandas`) que hoy no existe — la única dependencia externa del proyecto es PyYAML. Ilegible sin herramientas. Sobredimensionado para 100 productos |
| (d) | No decidir y dejarlo al implementar | Aplaza el trabajo | Es justo lo que §40 prohíbe, y lo que bloqueó al Componente 2 |

## Razón

El destino declarado de estos datos es **PostgreSQL** (Fase 2) y el modelo de `docs/04` es
relacional: una entidad, una tabla. El CSV por entidad es la representación más directa de esa forma
y la que menos transformación exige en la ingesta.

Pesó además el **coste de dependencias**: `CLAUDE.md` §17 prohíbe instalar dependencias innecesarias
y hoy el proyecto tiene una sola dependencia externa (PyYAML 6.0.3). CSV se escribe y se lee con el
módulo `csv` de la biblioteca estándar; Parquet no.

La alternativa (b) se descartó por una razón concreta: obligaría a aplanar el documento en la
ingesta, y ese aplanamiento sería un paso más donde puede perderse la correspondencia con el modelo.

## Contrato de formato

Estas convenciones son **parte de la decisión**, no detalles de implementación: sin ellas, «CSV» no
es un contrato.

| Aspecto | Valor |
|---|---|
| Codificación | UTF-8, **sin BOM** |
| Separador de campo | `,` (coma) |
| Entrecomillado | RFC 4180 — mínimo; solo cuando el valor contiene `,`, `"` o salto de línea. La comilla interna se duplica (`""`) |
| Fin de línea | `\n` (LF), también en Windows |
| Cabecera | **Obligatoria**, primera línea, con los nombres de columna del contrato de abajo |
| Nombres de columna | Idénticos a los atributos de `docs/04-modelo-datos.md`, en `snake_case` e inglés (`DT-017`) |
| Orden de columnas | El del contrato de abajo, fijo |
| `NULL` | Campo **vacío** (dos separadores consecutivos), nunca la cadena `NULL`, `None`, `NaN` ni `-` |
| Fechas | ISO-8601 `YYYY-MM-DD` |
| Fechas con hora | ISO-8601 UTC `YYYY-MM-DDTHH:MM:SSZ` |
| Booleanos | `true` / `false` en minúscula |
| Enteros | Sin separador de millares ni signo `+` |
| Decimales | Punto como separador decimal. Los importes, con **exactamente 2 decimales** (`docs/04` §7: «Tipos monetarios en `numeric`, nunca en coma flotante») |
| Orden de filas | **Ascendente por la clave de negocio**, no por `id`: `code` en `categories`, `suppliers` y `locations`; `sku` en `products`; y el par (`product_id`, `supplier_id`) en `product_suppliers`. El `id` se asigna después, siguiendo ese mismo orden, de modo que también resulta ascendente. Enunciarlo al revés sería circular y no restringiría nada |

## Estructura física

```text
<directorio de salida>/
├── manifest.json          ← DT-025
├── categories.csv
├── products.csv
├── suppliers.csv
├── product_suppliers.csv
└── locations.csv
```

- Nombres de archivo en **plural y `snake_case`**, derivados del nombre de la entidad.
- Directorio de salida por defecto: `data/synthetic/output/`. **No se versiona**: `CLAUDE.md` §13.7
  establece que los datasets no van al repositorio.
- Los seis archivos se escriben en **una sola ejecución del generador** y son coherentes entre sí. Un
  directorio de salida con archivos de ejecuciones distintas no es un dataset válido; `manifest.json`
  permite detectarlo (`DT-025`).
- Los Componentes 3 a 8 producirán sus propios CSV en este mismo directorio, con las mismas
  convenciones. Cada ejecución regenera el directorio completo con los componentes implementados en
  ese momento; «añadir» describe qué archivos aporta un componente nuevo, no una acumulación
  incremental sobre una salida anterior.
- **Alcance del contrato de formato.** La tabla de arriba cubre los tipos que aparecen en las cinco
  entidades maestras: entero, texto, booleano, decimal monetario, fecha y fecha-hora. **No cubre**
  tres tipos que sí aparecen en entidades posteriores y que habrá que añadir al autorizarlas:
  campos JSON (`policy_snapshot`, `calculation_inputs`, `metrics`…), decimales **no** monetarios
  (cantidades, que `docs/04` §7 deja abiertos a fracción según la unidad de medida) y la distinción
  entre cadena vacía y `NULL` en campos de texto opcionales. El contrato de columnas se fija aquí
  solo para las cinco entidades del Componente 2.

## Contrato de columnas — Componente 2

Se incluyen **todas** las columnas del modelo conceptual, también las que el Componente 2 deja
vacías. El esquema del archivo es el de la entidad; que una columna venga vacía significa que el
generador no produjo ese dato, que es información honesta y verificable.

### `categories.csv`

| # | Columna | Tipo | ¿La escribe C2? | Notas |
|---|---|---|---|---|
| 1 | `id` | entero ≥ 1 | Sí | Secuencial desde 1 en el orden del archivo |
| 2 | `code` | texto | Sí | Clave de negocio, única (`DT-028` §4) |
| 3 | `name` | texto | Sí | Etiqueta neutra (`DT-028` §4) |
| 4 | `parent_id` | entero \| vacío | **Vacío siempre** | Jerarquía plana (`ASSUMPTION-009`) |
| 5 | `is_active` | booleano | Sí | Ver `DT-028` §7 |
| 6 | `data_origin` | texto | Sí | Constante `SYNTHETIC` (`DT-026`) |

### `products.csv`

| # | Columna | Tipo | ¿La escribe C2? | Notas |
|---|---|---|---|---|
| 1 | `id` | entero ≥ 1 | Sí | |
| 2 | `sku` | texto | Sí | Clave de negocio, única e inmutable |
| 3 | `name` | texto | Sí | Etiqueta neutra |
| 4 | `description` | texto \| vacío | **Vacío** | §7.2 pide «nombre **o** descripción»; basta `name` |
| 5 | `category_id` | entero ≥ 1 | Sí | FK → `categories.id` |
| 6 | `unit_of_measure` | texto | Sí | Vocabulario cerrado (`DT-028` §5) |
| 7 | `is_active` | booleano | Sí | Ambos valores presentes (§25 filas 19 y 20) |
| 8 | `abc_class` | texto \| vacío | **Vacío siempre** | Derivado del consumo (`DT-029`) |
| 9 | `rotation_class` | texto \| vacío | **Vacío siempre** | Derivado del consumo (`DT-029`) |
| 10 | `shelf_life_days` | entero \| vacío | **Vacío siempre** | `docs/04` §8.4 sin responder (`DT-029`) |
| 11 | `valid_from` | fecha | Sí | Vigencia (`DT-027`) |
| 12 | `valid_to` | fecha \| vacío | Sí | Vacío = vigente sin fecha de fin (`DT-027`) |
| 13 | `created_at` | fecha-hora \| vacío | **Vacío** | Auditoría técnica: la fija la ingesta, no el generador |
| 14 | `updated_at` | fecha-hora \| vacío | **Vacío** | Ídem |
| 15 | `data_origin` | texto | Sí | `SYNTHETIC` |

### `suppliers.csv`

| # | Columna | Tipo | ¿La escribe C2? | Notas |
|---|---|---|---|---|
| 1 | `id` | entero ≥ 1 | Sí | |
| 2 | `code` | texto | Sí | Clave de negocio, única |
| 3 | `name` | texto | Sí | Etiqueta neutra |
| 4 | `contact_info` | texto \| vacío | **Vacío siempre** | `CLAUDE.md` §9.7 y `DT-029` |
| 5 | `is_active` | booleano | Sí | |
| 6 | `currency` | texto \| vacío | **Vacío siempre** | Multi-moneda sin decidir (`docs/04` §8.5, `DT-029`) |
| 7 | `created_at` | fecha-hora \| vacío | **Vacío** | Auditoría técnica |
| 8 | `updated_at` | fecha-hora \| vacío | **Vacío** | Ídem |
| 9 | `data_origin` | texto | Sí | `SYNTHETIC` |

### `product_suppliers.csv`

| # | Columna | Tipo | ¿La escribe C2? | Notas |
|---|---|---|---|---|
| 1 | `id` | entero ≥ 1 | Sí | |
| 2 | `product_id` | entero ≥ 1 | Sí | FK → `products.id` |
| 3 | `supplier_id` | entero ≥ 1 | Sí | FK → `suppliers.id` |
| 4 | `agreed_lead_time_days` | entero | Sí | Valor sintético (`DT-028` §1) |
| 5 | `moq` | entero ≥ 0 | Sí | Valor sintético (`DT-028` §1) |
| 6 | `order_multiple` | entero ≥ 1 | Sí | Valor sintético (`DT-028` §1) |
| 7 | `unit_cost` | decimal, 2 dec. | Sí | Valor sintético (`DT-028` §1) |
| 8 | `is_preferred` | booleano | Sí | Como máximo uno activo por producto |
| 9 | `is_active` | booleano | Sí | |
| 10 | `data_origin` | texto | Sí | `SYNTHETIC` |

El par (`product_id`, `supplier_id`) es la clave de negocio de esta entidad y es único. **No se añade
un código propio**: `docs/04` §3.4 no lo define y `docs/04` §5.8 solo exige clave de negocio única,
que el par ya proporciona.

### `locations.csv`

| # | Columna | Tipo | ¿La escribe C2? | Notas |
|---|---|---|---|---|
| 1 | `id` | entero ≥ 1 | Sí | |
| 2 | `code` | texto | Sí | Clave de negocio, única |
| 3 | `name` | texto | Sí | Etiqueta neutra |
| 4 | `type` | texto | Sí | Vocabulario cerrado (`DT-028` §6) |
| 5 | `is_active` | booleano | Sí | |
| 6 | `data_origin` | texto | Sí | `SYNTHETIC` |

### Sobre `id`

`id` es la **clave técnica** del modelo (`docs/04` §§3.1–3.5). En los CSV es un entero positivo
asignado secuencialmente desde 1 **siguiendo el orden de la clave de negocio** definido arriba, y las
claves foráneas lo referencian. Es estable para una misma configuración, semilla y versión del
generador (`DT-030`).

Como los códigos llevan relleno de ceros a ancho fijo (`DT-028` §4), el orden lexicográfico de la
clave de negocio coincide con el numérico, de modo que `CAT-002` precede a `CAT-010` y no al revés.

El **tipo SQL definitivo** (`integer`, `bigint`, `uuid`) es una decisión de la Fase 2 y **no se toma
aquí**: `docs/04` §7 anota las consideraciones de PostgreSQL como orientación y declara
explícitamente que «no se decide nada todavía».

## Consecuencias

**Positivas**

1. El Componente 2 deja de estar bloqueado por B-1.
2. El contrato es verificable sin ejecutar nada: el validador (Componente 8) puede comprobar
   cabeceras, orden de columnas, tipos y valores nulos contra estas tablas.
3. La carga en PostgreSQL (Fase 2) es directa con `COPY`.
4. Cero dependencias nuevas.

**Costos aceptados**

1. El CSV no lleva tipos: la corrección del dato depende de que se respeten las convenciones de
   arriba. Es el precio de la simplicidad, y se mitiga con la validación del Componente 8.
2. Columnas permanentemente vacías en `products.csv` y `suppliers.csv`. Se aceptan porque el esquema
   del archivo debe ser el de la entidad, no el de lo que un componente concreto sabe rellenar.
3. **Tarea pendiente para la implementación:** `.gitignore` ignora `*.csv` pero **no**
   `manifest.json`. Antes de que el generador escriba por primera vez hay que excluir el directorio
   de salida, o `manifest.json` acabaría versionado contra `CLAUDE.md` §13.7. **No se modifica
   `.gitignore` en esta tarea** porque todavía no existe ningún archivo generado.
4. **Segunda tarea pendiente:** `CLAUDE.md` §14 describe el árbol de `data/synthetic/` con tres
   carpetas —`config/`, `generator/`, `tests/`— y **no contempla el directorio de salida**. Hoy no
   hay contradicción, porque el directorio no existe y `CLAUDE.md` §6.2 prohíbe crear carpetas sin
   uso. Cuando el Componente 2 genere por primera vez, §14 debe recoger `output/` en el mismo cambio,
   conforme a `CLAUDE.md` §8 («si una decisión técnica cambia, se actualiza la documentación en el
   mismo cambio»). **`CLAUDE.md` no se modifica en esta tarea.**

**Qué invalidaría esta decisión**

Que el volumen del dataset crezca hasta hacer el CSV impracticable, o que la Fase 2 adopte un
mecanismo de carga que exija otro formato. Ninguna de las dos es el caso con la escala actual
(100 productos, 10 proveedores, 10 categorías, 1 ubicación).

## Lo que esta decisión NO hace

- **No** decide los tipos SQL ni el esquema físico de PostgreSQL (Fase 2).
- **No** define el formato de salida de los Componentes 3 a 8 más allá de las convenciones generales;
  sus columnas se definirán al autorizar cada componente.
- **No** genera ningún archivo. El Componente 2 **no está implementado**.
- **No** introduce ninguna dependencia.
