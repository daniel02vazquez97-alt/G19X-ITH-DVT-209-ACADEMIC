# DT-040 — Publicación atómica del dataset: workspace de ejecución y promoción final (W1)

- **Fecha:** 2026-09-26
- **Estado:** `ACEPTADA` — decisión W1 del responsable del proyecto. Dos detalles de operación,
  señalados en la sección *Pendiente de confirmación*, quedaron propuestos y no aprobados; **el
  responsable los resolvió el 2026-09-29** (ver esa sección).
- **Implementada:** 2026-09-29 en `data/synthetic/generator/pipeline.py`, invocada desde
  `__main__.py` (§9)
- **Fase del roadmap:** Fase 1 — Datos. Afecta a la **ejecución completa del generador**, no a un
  componente concreto
- **Afecta a:** `data/synthetic/generator/__main__.py` (orquestación, en la fase de implementación),
  `DT-038` §13, `DT-039` §5.2, `knowledge/dataset-specification.md` §41.3
- **Entrada resumida:** `docs/15-decisiones-tecnicas.md` → `DT-040`
- **Relacionada con:** `DT-024` (el directorio de salida contiene una sola ejecución), `DT-025`
  (un manifiesto describe una ejecución completa), `DT-038` §13 (contrato del directorio de salida),
  `DT-039` §5.2 (regla B2 de cero elegibles)

---

## Problema que resuelve

La regla B2 (`DT-039` §5.2) exige que, si el Componente 5 no encuentra ninguna orden causal elegible
para generar las canceladas, la ejecución **falle y no publique ningún dataset**. Con la escritura
vigente eso **no es posible**, y no por un defecto de C5, sino por cómo escribe el generador:

- El Componente 2 escribe sus cinco CSV y `manifest.json` en el directorio de salida en cuanto
  termina.
- El Componente 3 **lee de disco** lo que escribió C2, escribe `demand.csv` y reescribe el manifiesto.
- El Componente 4 lee de disco los archivos de C2 y C3 (`DT-038` §1).
- El Componente 5 se ejecuta el último.

Cuando C5 falla, C2, C3 y C4 ya han escrito. Cada componente cumple por separado su promesa de no
escribir nada si falla; **la ejecución en conjunto no la cumple**. El resultado es uno de dos:

1. **Directorio vacío de partida:** queda publicado un dataset parcial, con un `manifest.json`
   internamente coherente que no dice que la ejecución falló.
2. **Directorio con un dataset anterior completo:** los archivos de C2, C3 y C4 se sobrescriben, los
   de C5 anteriores se quedan, y el directorio pasa a contener **un dataset mezclado**, justo lo que
   prohíbe la regla 5 de `DT-038` §13. Además, el dataset válido anterior se pierde.

El problema no nace con B2 —un fallo de la precondición P-6 en C3 ya dejaba publicado un dataset solo
con el catálogo—, pero B2 lo hace inevitable, porque su condición depende del **resultado de la
simulación** y no puede comprobarse antes de que los componentes anteriores hayan escrito.

## Decisión

**Cada ejecución completa del generador trabaja en un workspace propio, y el directorio de salida
solo cambia por promoción del workspace entero, después de que todo haya terminado bien.**

### 1. Vocabulario

| Término | Significado |
|---|---|
| **Generado** | Existe en el **workspace** de una ejecución. No es un dataset: es trabajo en curso, o el resto de una ejecución fallida |
| **Publicado** | Existe en `data/synthetic/output/`. Es, siempre, **el resultado completo de una única ejecución que terminó bien** |
| **Dataset válido anterior** | Lo que había publicado en `output/` antes de empezar una ejecución nueva |
| **Workspace de una ejecución nueva** | El directorio de trabajo de la ejecución en curso. Nada en él se considera publicado |

> **Un dataset solo se considera publicado cuando la ejecución completa ha terminado
> satisfactoriamente y su workspace ha sido promocionado a `output/`.**

### 2. Ubicación del workspace

```text
data/synthetic/
├── output/                    ← dataset PUBLICADO
└── tmp/
    └── <id_de_ejecución>/     ← workspace de una ejecución
```

**Por qué `tmp/` y no otro nombre.** El `.gitignore` del repositorio ya tiene, en su sección
*«Logs y temporales»*, la regla `tmp/`, que excluye del control de versiones cualquier directorio con
ese nombre. Es la convención existente del proyecto para directorios temporales: usarla evita añadir
una regla nueva y deja el workspace excluido de Git desde el primer momento. `CLAUDE.md` §13.7 exige
que los datasets no entren en el repositorio, y un workspace contiene un dataset en construcción.

**Por qué hermano de `output/`.** El workspace y `output/` tienen que estar en el **mismo sistema de
archivos**, porque la promoción es un renombrado de directorio (§5), y un renombrado entre sistemas de
archivos distintos no es atómico: se convierte en una copia.

**`<id_de_ejecución>`** debe ser único por ejecución, no reutilizarse nunca y **no formar parte del
artefacto**: ningún byte del dataset ni del manifiesto depende de él, de modo que no afecta a la
reproducibilidad de §44. Su formato concreto se fija al implementar.

### 3. Quién hace qué

| Actor | Responsabilidad |
|---|---|
| **Orquestador** (`__main__.py`, o la función de ejecución que invoque) | Comprobar `output/` antes de empezar (`DT-038` §13); crear el workspace; ejecutar C2 → C3 → C6 → C4 → C5 → C7 → C8 **dentro** de él; hacer la verificación final; promocionar. **Es el único actor que toca `output/`** |
| **Componentes C2, C3, C6, C4, C5, C7 y C8** | Leer y escribir en el directorio que reciben —C6 solo añade su entrada al manifiesto (`DT-037` §1); C7 y C8 solo añaden su entrada y un campo (`scenario_assignment`, `quality_report`; `DT-041`, `DT-042`)—. **No saben** que es un workspace, no conocen `output/` y no promocionan nada |

**Esto no cambia la interfaz de ningún componente.** C2 y C3 ya reciben el directorio como parámetro
—`generate(config, output_dir)`—; C6, C4 y C5 lo reciben igual. El orquestador les pasa la ruta del
workspace en lugar de la de `output/`, y el modelo de archivos intermedios **no cambia**: C3 sigue
leyendo de disco lo que escribió C2, y C4 lo que escribieron C2 y C3. *W1 no es W2: no se convierte
el pipeline a memoria.*

Las pruebas de los componentes, que ya llaman a `generate()` con directorios temporales propios, no
se ven afectadas.

### 4. Flujo de una ejecución

```text
1. Comprobación previa de output/   (DT-038 §13, reglas 1 a 3)
       ↓ si falla: error, nada se crea, output/ intacto
2. Crear el workspace tmp/<id_de_ejecución>/
3. C2 → C3 → C6 → C4 → C5 → C7 → C8, todos dentro del workspace
       ↓ si cualquiera falla —incluido C8 al rechazar el dataset—: error, NO se promociona,
         output/ intacto
4. Verificación final, sobre el workspace:
     · el conjunto de archivos del workspace es exactamente
       manifest.files[].name + manifest.json
     · el sha256 de cada archivo coincide con el que registra el manifiesto
       ↓ si falla: error, NO se promociona, output/ intacto
5. Promoción del workspace a output/   (§5)
       ↓ solo ahora el dataset queda publicado
```

La verificación del paso 4 no inventa ninguna regla nueva: comprueba las propiedades que `DT-025`
(el manifiesto describe una ejecución completa, con el `sha256` de cada archivo) y §34 de la
especificación (*Integridad de origen*) ya exigen al dataset. Cuando exista el Componente 8, sus
validaciones se ejecutarán también **antes** de este paso.

> **Actualización del 2026-09-29 (`DT-042` §8).** El Componente 8 existe y se ejecuta en el paso 3,
> después de C7 y antes de este paso. La verificación final conserva todas sus comprobaciones y exige
> además `scenario_assignment` y un `quality_report` con `result = PASS`, `validations.failed = 0` y
> `executed = passed`. `COMPONENT_VERSIONS` lista los siete componentes C2–C8.

### 5. Promoción

**La promoción reemplaza `output/` en bloque. Nunca copia ni sustituye archivo a archivo dentro de un
`output/` existente.** Tres mecanismos posibles, y dos quedan descartados por el propio contrato, no
por preferencia:

| Mecanismo | ¿Cumple el contrato? |
|---|---|
| Copiar o sustituir los archivos uno a uno dentro de `output/` | **No.** Cada archivo sería atómico, el **conjunto no**: un corte a mitad de la promoción deja un dataset mezclado |
| Enlace simbólico `output → tmp/<id>` que se cambia de destino | **No es portable.** La copia de trabajo del proyecto vive en Windows, donde crear enlaces simbólicos exige privilegios que no pueden suponerse |
| **Renombrado de directorios en el mismo sistema de archivos** | **Sí.** Es el mecanismo que se adopta |

**Secuencia de la promoción:**

```text
a. Renombrar output/          → tmp/<id_de_ejecución>.anterior/     (si output/ existe)
b. Renombrar tmp/<id_de_ejecución>/ → output/
c. Si (b) falla: renombrar tmp/<id_de_ejecución>.anterior/ → output/, y la ejecución falla
```

**Garantía:** en ningún instante `output/` contiene archivos de dos ejecuciones. Entre (a) y (b),
`output/` **no existe** durante un instante; si el proceso se interrumpe justo ahí, el dataset
anterior sigue íntegro en `tmp/<id_de_ejecución>.anterior/`, recuperable renombrándolo. Un
directorio ausente puede detectarse; un directorio mezclado, no.

**Lo que la promoción no hace:** no borra ningún archivo de `output/` que el generador no vaya a
escribir. La regla 3 de `DT-038` §13 garantiza, en el paso 1, que `output/` no contiene ningún
archivo ajeno al conjunto del dataset; si lo contuviera, la ejecución falla **antes** de crear el
workspace.

**Consideración de Windows.** Si algún archivo de `output/` está abierto por otro programa —por
ejemplo, un CSV abierto en una hoja de cálculo—, el renombrado (a) falla. En ese caso no se ha
tocado nada: la ejecución se declara fallida y `output/` queda intacto.

### 6. Comportamiento ante fallo

| Fallo en | `output/` | Workspace |
|---|---|---|
| Comprobación previa (paso 1) | Intacto | No se crea |
| C2, C3, C6, C4 o **C5 por B2** (paso 3) | **Intacto**, incluido cualquier dataset válido anterior | Se conserva; ver *Pendiente de confirmación* |
| Verificación final (paso 4) | Intacto | Se conserva |
| Renombrado (a) (paso 5) | Intacto | Se conserva |
| Renombrado (b) (paso 5) | Restaurado por (c) | Se conserva |

**Prohibido** —estrategia W3, no aprobada—: escribir en `output/`, fallar y después borrar lo
escrito. Además de no ser atómica, esa estrategia no puede recuperar un dataset anterior que ya se
sobrescribió.

### 7. Workspaces abandonados

Un workspace que queda en `tmp/` —por un fallo controlado, o porque el proceso se interrumpió— es
**inerte**:

- **nunca se promociona** después: la promoción solo la hace la ejecución que lo creó, al final;
- **ninguna otra ejecución lo lee**: cada ejecución trabaja en su propio `<id_de_ejecución>`;
- **no bloquea** una ejecución nueva;
- **no es un dataset publicado**, aunque contenga archivos completos y un manifiesto;
- está **excluido de Git** por la convención `tmp/`.

### 8. Ejecuciones concurrentes

**V1 no admite dos ejecuciones simultáneas sobre el mismo `output/`.** Cada una tendría su propio
workspace, pero sus promociones podrían intercalarse. Es una limitación declarada, no un defecto: el
generador se ejecuta manualmente y de una en una.

## Pendiente de confirmación

> **Resuelto el 2026-09-29** por el responsable, al autorizar la implementación. El texto de abajo
> se conserva como estaba:
>
> 1. **Dataset anterior sustituido:** se **elimina** tras una promoción correcta —coincide con la
>    propuesta—. `tmp/<id_de_ejecución>.anterior/` es transitorio: no es un historial, ni un
>    respaldo, ni un mecanismo de versionado.
> 2. **Workspace de una ejecución fallida:** se **elimina** —**no** la propuesta de conservarlo—. La
>    tabla de §6, que decía «se conserva», queda sustituida en ese punto por §9.
>
> Única excepción, derivada de §5 y no de una preferencia: si fallan a la vez (b) y (c),
> `tmp/<id_de_ejecución>.anterior/` **no** se elimina, porque es la única copia del dataset
> anterior.

Dos detalles de operación que la decisión W1 no fija. **No están aprobados**; se proponen para la
revisión:

1. **El dataset anterior sustituido.** Propuesta: tras una promoción correcta, se **elimina**
   `tmp/<id_de_ejecución>.anterior/`. Es un dataset que el propio generador escribió, y la regla 3 de
   `DT-038` §13 garantiza que no contiene archivos ajenos. La alternativa es conservarlo, a costa de
   que se acumulen datasets antiguos en `tmp/`.
2. **El workspace de una ejecución fallida.** Propuesta: se **conserva** para diagnóstico. Es inerte
   (§7) y está excluido de Git. La alternativa es eliminarlo al fallar, a costa de perder el material
   para entender el fallo.

## 9. Implementación *(2026-09-29)*

`data/synthetic/generator/pipeline.py`, función `run(config, output_dir)`, a la que llama
`__main__.py`. No cambia ningún componente: C2, C3, C6, C4 y C5 se invocan con sus `generate`
existentes, recibiendo el workspace como directorio.

| Paso de §4 | Implementación |
|---|---|
| 1. Comprobación previa | `check_output`: `output/` ausente o vacío, o solo con archivos del conjunto del dataset; cualquier otra entrada —archivo ajeno, subdirectorio, o una ruta que no es directorio— hace fallar la ejecución nombrándola, sin crear ni borrar nada |
| 2. Workspace | `<padre de output>/tmp/<id>/`, con `<id>` = UUID4 en hexadecimal. **No aparece en ningún byte del dataset** |
| 3. Componentes | `generate_into`: C2 → C3 → C6 → C4 → C5, con un único `generated_at` para toda la ejecución |
| 4. Verificación final | `verify`: versión del generador y de cada componente, sub-semillas, archivos en disco = `manifest.files` + `manifest.json` y conjunto completo, `sha256` y número de filas, cabeceras de cada contrato, y existencia sin negativos reconstruible desde los movimientos (`V1-13`, `DT-038` §6). **No añade ninguna regla**: repite propiedades que los contratos ya exigen |
| 5. Promoción | `promote`: (a), (b) y (c) de §5 con `os.rename`; `.anterior` se elimina tras (b) |
| Fallo en cualquier paso | El workspace se **elimina** siempre (resolución del punto 2 pendiente); `output/` queda como estaba |

**Garantía real, sin exagerarla.** La promoción **no** es un reemplazo atómico: Python no ofrece
ninguna primitiva que sustituya un directorio no vacío de una sola vez, ni en Linux (`os.replace`
devuelve `ENOTEMPTY`) ni en Windows. Lo que sí garantiza, y está probado:

- un fallo en la comprobación previa, en cualquier componente o en la verificación deja `output/`
  **idéntico byte a byte** y no deja nada en `tmp/`;
- un fallo de (a) no mueve nada; un fallo de (b) se deshace con (c);
- `output/` nunca contiene archivos de dos ejecuciones;
- si fallan (b) **y** (c), o si el proceso muere entre (a) y (b), `output/` no existe y el dataset
  anterior está **íntegro** en `tmp/<id>.anterior/`; en el primer caso el error lo nombra.

Tras una ejecución correcta no queda nada en `tmp/`: ni workspace, ni `.anterior`, ni el propio
directorio `tmp/` si quedó vacío. Un workspace o un `.anterior` que sobreviva a un proceso
interrumpido **no se borra automáticamente** en la ejecución siguiente: puede ser la única copia del
dataset anterior (§7).

**`GENERATOR_VERSION` pasa a `0.3.0`** con esta implementación, el incremento único que `DT-036` §8
fijó para el lote C6 + C4 + C5 (regla de `DT-033`): el artefacto publicado cambia —seis archivos
nuevos y tres componentes más en el manifiesto— y, con la versión anterior, compartiría
`dataset_version` con el dataset C2 + C3 al que sustituye.

## Alternativas consideradas

| | Alternativa | Por qué no |
|---|---|---|
| **W1** | **Workspace y promoción al final** | *Adoptada* |
| W2 | Todo en memoria, escribir al final | Refactoriza la entrada de C3 y la de C4, que leen de disco: cambia componentes cerrados |
| W3 | Escribir en `output/` y borrar lo escrito si algo falla | No es atómica; no recupera el dataset anterior sobrescrito; roza la regla 4 de `DT-038` §13 |

## Consecuencias

**Positivas**

1. B2 se cumple por completo: **fallar implica no publicar**.
2. Un dataset válido anterior **sobrevive** a cualquier ejecución fallida.
3. La regla 5 de `DT-038` §13 —nunca un dataset mezclado— pasa a ser una garantía estructural.
4. Ningún componente cambia de interfaz.

**Costos aceptados**

1. Durante una ejecución, el disco aloja dos datasets: el publicado y el del workspace.
2. Durante un instante de la promoción, `output/` no existe.
3. No se admiten ejecuciones concurrentes sobre el mismo `output/`.
4. El orquestador, hasta ahora trivial, pasa a tener responsabilidades propias.

## Lo que esta decisión NO hace

- **No** cambia `DT-024` ni `DT-025`: el dataset publicado sigue siendo un único directorio con una
  sola ejecución completa. Cambia **cómo** se llega a él, no **qué** contiene.
- **No** convierte el pipeline a memoria (W2).
- **No** autoriza borrar nunca archivos de `output/` tras un fallo (W3).
- **No** implementa nada: a la fecha de este ADR, el orquestador sigue escribiendo directamente en
  `output/`, y `data/synthetic/tmp/` no existe.
