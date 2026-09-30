# DT-025 — `manifest.json`: la metadata de generación vive fuera de las entidades

- **Fecha:** 2026-09-18
- **Estado:** `ACEPTADA`
- **Fase del roadmap:** Fase 1 — Datos (Componente 2 en adelante)
- **Afecta a:** `knowledge/dataset-specification.md` §§19, 33, 42; `docs/04-modelo-datos.md` §4;
  el diseño de los Componentes 2 a 8
- **Entrada resumida:** `docs/15-decisiones-tecnicas.md` → `DT-025`
- **Relacionada con:** `DT-024` (formato de salida), `DT-029` (alcance del Componente 2), `DT-030`
  (determinismo)

---

## Decisión

La metadata de generación del dataset se escribe en un **único archivo `manifest.json`**, situado
junto a los CSV de las entidades. **Ninguna entidad de negocio lleva metadata de generación**: ni
`seed`, ni versión del generador, ni escenario asignado.

En particular, **no se añade un campo `scenario` a `Product`, `Supplier`, `Category`,
`ProductSupplier` ni `Location`**.

## Contexto

Dos secciones de la especificación exigen conservar metadata que ninguna entidad del modelo aloja:

- **§19** — «La trazabilidad debe permitir identificar, cuando corresponda: carga; registro; fecha de
  generación; **semilla utilizada; versión del generador; escenario sintético asociado**.»
- **§33** — «Como mínimo se recomienda conservar: `dataset_version`, `generator_version`, `seed`,
  `generated_at`, `time_range`.»

La entidad de soporte `DataLoad` (`docs/04` §4) registra «origen, archivo, fecha, filas
aceptadas/rechazadas, `data_origin`» — no contiene ninguno de esos cinco campos.

La auditoría del Componente 2 (2026-09-17) registró la carencia como bloqueante **B-4**.

La salida aparentemente fácil —añadir un campo `scenario` a `Product`— la cierra la propia §19:
«La información adicional de generación **no debe confundirse con información empresarial**.»

## Alternativas consideradas

| | Alternativa | Ventajas | Inconvenientes |
|---|---|---|---|
| (a) | **Archivo `manifest.json` separado** | La metadata de generación queda físicamente fuera de los datos de negocio, que es lo que §19 exige. Un solo lugar que consultar. Estructura anidada natural (versiones, archivos, rangos) | Un archivo más que mantener coherente con los CSV |
| (b) | Campos de generación en cada entidad (`seed`, `scenario`, `generator_version`) | Todo viaja con el registro | Contamina el modelo de negocio con datos del generador, contra §19. Repite la misma semilla en cada fila. `Product` acabaría con un campo que no existirá cuando los datos sean reales |
| (c) | Ampliar `DataLoad` con los cinco campos | Reutiliza una entidad ya prevista | `DataLoad` es de la **ingesta**, no de la generación: registra qué se cargó, no cómo se produjo. Mezclaría dos responsabilidades. Además obligaría a materializar una entidad de soporte que el Componente 2 no produce |
| (d) | Un CSV de metadata | Coherente con `DT-024` | La metadata es un documento con estructura anidada (rango temporal, lista de archivos, versiones por componente); forzarla a una tabla la deforma |

## Razón

El criterio decisivo es la frase de §19: la metadata de generación **no es información empresarial**.
Un archivo separado la mantiene separada por construcción, sin depender de que nadie recuerde
ignorarla.

La alternativa (b) tiene además un problema de futuro: `ASSUMPTION-001` prevé sustituir los datos
sintéticos por datos reales sin cambiar reglas de negocio (`BR-007`, `DT-004`). Un campo `scenario`
en `Product` no tendría ningún valor posible con datos reales, y quedaría como una columna huérfana
en el esquema definitivo.

Se eligió JSON y no CSV porque el contenido es un documento con estructura anidada. Esto **no
contradice `DT-024`**: aquel decide el formato de **los datos de las entidades**; el manifiesto no es
una entidad.

## Contrato de `manifest.json`

```json
{
  "dataset_version":   "<sin fijar>",
  "generator_version": "<sin fijar>",
  "seed":              20260913,
  "generated_at":      "AAAA-MM-DDTHH:MM:SSZ",
  "time_range":        { "start_date": "AAAA-MM-DD", "end_date": "AAAA-MM-DD" },
  "data_origin":       "SYNTHETIC",
  "config":            { "...": "DatasetConfig.to_dict() íntegro" },
  "components":        [ { "name": "...", "version": "...", "sub_seed": 0 } ],
  "files":             [ { "name": "...", "entity": "...", "rows": 0, "sha256": "..." } ]
}
```

### Campos obligatorios desde el Componente 2

| Campo | Tipo | Contenido | Fuente del requisito |
|---|---|---|---|
| `dataset_version` | texto | Identificador de la versión del dataset producido | §33 |
| `generator_version` | texto | Versión del generador que lo produjo | §19, §33 |
| `seed` | entero | `DatasetConfig.seed`, copiado literalmente | §19, §33, §3.3 |
| `generated_at` | fecha-hora UTC | Instante de la generación, ISO-8601 con `Z` | §19, §33 |
| `time_range` | objeto | `start_date` y `end_date` de `DatasetConfig.period` | §33 |
| `data_origin` | texto | Constante `SYNTHETIC` a nivel de dataset | §19, §34, `DT-026` |
| `config` | objeto | **`DatasetConfig.to_dict()` íntegro**, incluida `scenarios.required` | §19 («escenario sintético asociado»), §33 |
| `components` | lista | Un registro por componente que contribuyó: nombre, versión y sub-semilla derivada | `DT-030` |
| `files` | lista | Un registro por archivo escrito: nombre, entidad, número de filas y `sha256` del contenido | §33, §35 |

`config` es la pieza que cierra el requisito de §19 sobre el «escenario sintético asociado» **a nivel
de dataset**: `DatasetConfig.to_dict()` ya emite la lista normalizada `scenarios.required`, de modo
que el manifiesto registra qué cobertura de escenarios se pidió sin necesidad de etiquetar ninguna
fila. **No requiere ningún cambio en `config.py`**: el método existe y está cubierto por las pruebas.

### Campos que dependen de componentes posteriores

| Campo | Depende de | Por qué no se define ahora |
|---|---|---|
| `scenario_assignment` | **Componente 7** | Qué SKU o qué relación recibió cada eje de Nivel A. La asignación es del Componente 7 (`DT-023`); su forma se definirá al autorizarlo |
| `quality_report` | **Componente 8** | §35 exige un reporte de calidad con **veinte** ítems. Si se enlaza desde aquí o se escribe aparte se decidirá al autorizar el Componente 8 |

Estos dos campos **no se inventan ahora**. Un manifiesto producido por el Componente 2 no los
contiene, y eso no lo hace inválido: el contrato los declara como aportados por componentes
posteriores.

> **Definidos el 2026-09-29.** `scenario_assignment` es un campo del manifiesto con los 16 ejes de
> nivel A y seis campos por eje (`DT-041` §4). `quality_report` es **también** un campo del
> manifiesto —no un archivo aparte— con los veinte ítems de §35 (`DT-042` §5; decisión C7/C8-08).
> Ambos se añaden con `writer.add_manifest_field`, que nunca sobrescribe. Desde `generator_version`
> 0.4.0 los aporta cada ejecución completa y W1 los exige antes de publicar.

### Reglas del manifiesto

1. **Un manifiesto por directorio de salida.** Describe una ejecución completa del generador.
2. **`files` es la lista de lo realmente escrito.** Un manifiesto del Componente 2 lista cinco CSV;
   cuando existan los Componentes 3 a 8, listará más.
3. **El `sha256` de cada archivo** permite detectar un directorio con archivos de ejecuciones
   distintas, que no es un dataset válido (`DT-024`).
4. **Campos no reproducibles.** `generated_at` no lo es nunca, y `files`, `components` y
   `generator_version` dependen del conjunto de componentes ejecutados. El invariante completo está
   enunciado una sola vez, en §44 de la especificación, y `DT-030` remite a él: misma configuración +
   misma semilla + misma versión del generador → archivos de datos idénticos byte a byte. Toda
   comparación de reproducibilidad debe excluir esos cuatro campos del manifiesto.
5. **Esquema de `dataset_version` y `generator_version`.** Cuando se escribió este ADR no se fijaron:
   eran campos del contrato y no existía todavía ninguna versión que registrar. Se decidieron al
   implementar el Componente 2, en **`DT-033`**: `generator_version` es una versión semántica de la
   *salida observable* del generador (`0.1.0` con el Componente 2), y `dataset_version` es
   **derivada** —`ds-` más los 12 primeros hex de `sha256(configuración canónica + versión del
   generador)`—, de modo que regenerar el mismo dataset produce el mismo identificador.

## Consecuencias

**Positivas**

1. §19 y §33 quedan satisfechas sin tocar el modelo de negocio.
2. El modelo de datos sigue siendo válido cuando los datos sean reales: ninguna entidad tiene campos
   que solo tendrían sentido en un dataset sintético.
3. `DatasetConfig.to_dict()` gana un consumidor real, lo que refuerza que la normalización del
   Componente 1 no era decorativa.

**Costos aceptados**

1. Un archivo más cuya coherencia con los CSV hay que mantener. Mitigado con `files[].sha256`.
2. El manifiesto es JSON y los datos CSV: dos formatos en el mismo directorio. Se acepta porque
   describen cosas de naturaleza distinta.
3. `manifest.json` **no está cubierto por `.gitignore`** — ver `DT-024`, *Costos aceptados*, punto 3.

**Qué invalidaría esta decisión**

Que aparezca una necesidad real de consultar la metadata de generación **por fila** —por ejemplo, un
dataset mixto sintético/real dentro del mismo archivo. Hoy no existe: `BR-007` y `DT-004` resuelven
esa distinción con `data_origin` a nivel de registro (`DT-026`), no con metadata de generación.

## Lo que esta decisión NO hace

- **No** genera ningún `manifest.json`. Es un contrato, no un archivo producido.
- **No** fijó valores de `dataset_version` ni `generator_version`; los fija `DT-033` (2026-09-21).
- **No** define el contenido de `scenario_assignment` ni de `quality_report`.
- **No** modifica `DataLoad` ni ninguna otra entidad de `docs/04`.
- **No** modifica `config.py`.
