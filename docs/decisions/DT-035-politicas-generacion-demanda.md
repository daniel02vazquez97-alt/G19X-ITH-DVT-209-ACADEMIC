# DT-035 — Políticas sintéticas de generación de demanda (Componente 3)

- **Fecha:** 2026-09-23
- **Estado:** `ACEPTADA`
- **Fase del roadmap:** Fase 1 — Datos (Componente 3: *Demand Generator*)
- **Afecta a:** `knowledge/dataset-specification.md` §8 y §32, el diseño del Componente 3 y el
  contrato de validación del Componente 8
- **Entrada resumida:** `docs/15-decisiones-tecnicas.md` → `DT-035`
- **Relacionada con:** `DT-023` (clasificación de escenarios), `DT-028` (políticas del Componente 2,
  cuyo patrón este documento reproduce), `DT-032` (algoritmo pseudoaleatorio), `DT-034` (contrato de
  `demand.csv`)

---

> # ⚠ ADVERTENCIA DE LECTURA
>
> **Todos los valores numéricos, conjuntos, rangos, proporciones e intensidades de este documento son
> `synthetic generation parameters`: parámetros técnicos del generador de datos sintéticos.**
>
> **NO son volúmenes de demanda, ni niveles de rotación, ni estacionalidades, ni tasas de crecimiento
> de ninguna organización. NO deben citarse como información empresarial ni usarse para dimensionar,
> presupuestar, pronosticar ni negociar nada.**
>
> Su respaldo es §3.5 de la especificación:
>
> > «Cuando sea necesario utilizar valores para construir escenarios técnicos, estos deben
> > identificarse explícitamente como valores sintéticos de prueba y no como políticas de la
> > organización.»
>
> Es exactamente el mismo estatuto que tienen los MOQ y los costos de `DT-028`.

---

## Decisión

El Componente 3 genera la demanda latente aplicando las políticas de este documento. Viven en
`data/synthetic/generator/policies.py`, junto a las del Componente 2 y bajo su propio banner.

### 1. Dos ejes ortogonales, no una lista de ocho

Cada producto recibe **una forma** y **una clase de rotación**:

| Eje | Valores | Qué describe |
|---|---|---|
| **Forma** | `STABLE_DEMAND`, `GROWING_DEMAND`, `DECLINING_DEMAND`, `SEASONAL_DEMAND`, `INTERMITTENT_DEMAND`, `ERRATIC_DEMAND` | **Cómo** se distribuye la demanda en el tiempo (§8) |
| **Rotación** | `HIGH_ROTATION`, `LOW_ROTATION` | **Cuánto** se mueve el producto (`DT-023` §7.2) |

**Por qué no una sola distribución de ocho.** Fundirlas haría que «alta rotación» fuera mutuamente
excluyente con «estacional», lo cual no describe nada: la rotación es magnitud, la forma es reparto
temporal, y todo producto tiene ambas cosas a la vez. `DT-023` §7.2 ya trata la rotación como un eje
aparte, respaldado por `docs/02` §8, `roadmap` Fase 1 y §10.4 de la especificación — no como un
séptimo patrón de demanda. Una única lista de ocho dejaría además a los productos de rotación sin
ninguna forma temporal, que es un producto imposible.

**Regla explícita para el producto con más de un comportamiento:** todo producto tiene exactamente
dos, uno de cada eje. Ninguno tiene dos formas ni dos rotaciones.

### 2. Proporciones

Cada eje tiene su propia mezcla, **cada una suma 100 %**, con **suelo de un producto por clase**:

| Forma | % | | Rotación | % |
|---|--:|---|---|--:|
| `STABLE_DEMAND` | 30 | | `HIGH_ROTATION` | 30 |
| `GROWING_DEMAND` | 15 | | `LOW_ROTATION` | 70 |
| `DECLINING_DEMAND` | 15 | | | |
| `SEASONAL_DEMAND` | 20 | | | |
| `INTERMITTENT_DEMAND` | 10 | | | |
| `ERRATIC_DEMAND` | 10 | | | |
| **Σ** | **100** | | **Σ** | **100** |

Estable es la porción mayor porque es el baseline contra el que §8.1 quiere comparar; intermitente y
errática son las menores porque son los casos difíciles, no los frecuentes. **No se afirma que un
catálogo real tenga esta forma**: la mezcla existe para que el dataset contenga las seis formas en
cantidades utilizables.

El reparto usa **mayor resto con fracciones exactas y empates al índice menor**, el mismo método que
`DT-028` §3.2 fija para la distribución de categorías y por la misma razón: el resultado debe ser
función total de sus argumentos, no del orden de iteración. El suelo de uno hace que la cobertura sea
una **construcción**, no una probabilidad — la lección que `DT-028` §1.5 ya aprendió a escala pequeña.

### 3. Parámetros

```text
DEMAND_BASE_LEVEL          HIGH_ROTATION = [20, 60]   unidades/día
                           LOW_ROTATION  = [1, 5]

DEMAND_NOISE_PERMILLE      ERRATIC_DEMAND = 600       ‰ del nivel
                           todas las demás = 150

DEMAND_TREND_PERMILLE            = 600   cambio total a lo largo del periodo
DEMAND_SEASON_AMPLITUDE_PERMILLE = 400   amplitud relativa
DEMAND_SEASON_PERIOD_DAYS        = 365   anual
DEMAND_INTERMITTENT_EVENT_PERMILLE      = 150   ‰ de días con evento
DEMAND_INTERMITTENT_EVENT_MULTIPLIER    = [2, 6]  múltiplo del nivel en un evento
```

**El nivel base es el parámetro que la especificación nunca nombra** —§32 lista intensidades y
frecuencias, pero no cuánto se mueve un producto en un día corriente— y sin él no hay serie. Los dos
rangos son disjuntos y de un orden de magnitud de distancia: es eso lo que hace que `HIGH_ROTATION` y
`LOW_ROTATION` se distingan **por inspección de los datos** y no por la etiqueta.

`DEMAND_TREND_PERMILLE = 600` tiene un límite que importa: una serie decreciente termina en 0,4 veces
su nivel inicial. Debe quedar **cómodamente por encima de cero**, porque un nivel que llegara a cero
convertiría un producto decreciente en uno intermitente y las dos formas dejarían de distinguirse.

### 4. Mecanismo

Para un producto de nivel `L`, forma `S` y día `t` medido desde el inicio del periodo:

```text
cantidad(t) = max(0, redondeo( L · tendencia(t) · estación(t) · ruido(t) ))
```

- **tendencia(t)** — lineal en `t`: `1 ± TREND · t/(N−1)` para las formas creciente y decreciente,
  y exactamente 1 para las demás. Lineal porque es el mecanismo más simple que produce una tendencia
  global monótona y el más fácil de falsar en una prueba.
- **estación(t)** — solo en `SEASONAL_DEMAND`: `1 + A · triángulo(t + fase)`, con periodo 365 y fase
  propia de cada producto. Exactamente 1 para las demás.
- **ruido(t)** — multiplicador uniforme en `1 ± CV`, con `CV` según la forma.

**`INTERMITTENT_DEMAND` sigue otra ruta, y es deliberado.** Sus ceros no son un nivel pequeño que
redondea a cero: son días **sin evento de demanda**. Y sus días positivos son bultos, no el nivel
ordinario. §8.5 pide «numerosos periodos de demanda cero y eventos de consumo separados»; una serie
que solo redondeara a cero sería una serie estable de bajo volumen con una etiqueta distinta, y las
dos serían indistinguibles por inspección — que es precisamente lo que §8.5 quiere evitar.

### 5. Onda triangular, no senoidal

La estacionalidad usa un **triángulo**, no un seno, y la razón es la reproducibilidad, no el gusto.

`math.sin` lo calcula la `libm` de la plataforma, cuyos últimos bits **no están garantizados** entre
versiones ni entre arquitecturas. `DT-032` existe para que el dataset sea idéntico byte a byte en
todas partes, y un solo flotante de `libm` lo desharía para cada producto estacional. Un triángulo es
aritmética entera exacta y satisface §8.4 igual de bien: lo que esa sección pide es «una periodicidad
claramente definida y reproducible», no una sinusoide.

Por la misma razón, **todo el mecanismo es aritmética entera en por mil**. No hay un solo flotante en
la ruta de generación.

### 6. Configurabilidad

**Ninguno de estos parámetros es configurable en esta versión.** Son constantes del Componente 3, y
el contrato para hacer configurable cualquiera de ellos es el de `DT-028` §8, que este ADR adopta sin
cambios: sección propia y separada en el YAML, tipo propio validado en `config.py`, decisión técnica
registrada, y una prueba por invariante nueva.

Justificación: §32 lista estos parámetros entre los que el generador «deberá permitir controlar»,
pero no fija ninguno, y `DatasetConfig` no los tiene. Ampliar el contrato de configuración del
Componente 1 antes de saber si necesitan variar entre ejecuciones sería especular.

### 7. Precondición

| # | Precondición | Origen |
|---|---|---|
| **P-6** | `product_count ≥ 6` | §1, para que ninguna de las seis formas se quede sin producto |

Se comprueba al arrancar y **falla con un error explícito**; el Componente 3 nunca genera un dataset
que omita en silencio una forma que la especificación exige. Es el mismo espíritu que P-2 para las
cuatro clases del Componente 2.

## Contexto

§8 de la especificación describe las seis formas **cualitativamente** —«tendencia ascendente»,
«variabilidad elevada», «numerosos periodos de demanda cero»— y no fija ni una fórmula, ni una
distribución, ni un rango, ni un parámetro. §32 lista cinco parámetros que el generador «deberá
permitir controlar» y les asigna cero valores. Nada en el repositorio dice qué es «elevada» ni cuántos
ceros son «numerosos».

Sin estos valores, el Componente 3 no es implementable. La auditoría previa (2026-09-21) lo registró
como el tercero de sus tres bloqueantes.

## Alternativas consideradas

| | Alternativa | Ventajas | Inconvenientes |
|---|---|---|---|
| (a) | **Políticas sintéticas documentadas, constantes del Componente 3** | Desbloquea C3 sin esperar a nadie. Los valores quedan en un solo lugar, etiquetados y auditables. §3.5 lo autoriza, y `DT-028` ya sentó el precedente | Hay que mantener este documento si cambian |
| (b) | Preguntar al negocio por niveles de demanda y estacionalidades | No se inventa nada | Pediría al negocio datos que **no tiene que dar**: son volúmenes de un catálogo que no existe. Y §37 excluye del alcance los datos reales |
| (c) | Añadirlos a `DatasetConfig` ahora | Configurables sin tocar código | Amplía el contrato del Componente 1 por un componente recién nacido, sin saber si necesitan variar. `CLAUDE.md` §6.2 |
| (d) | Valores aleatorios sin rango declarado | Cero trabajo | Produce series incoherentes y hace incomprobable cualquier garantía de §8 |

## Razón

Se elige (a) por el argumento de §3.5 y por el precedente de `DT-028`, que resolvió el mismo problema
para el Componente 2 y no ha dado ningún inconveniente.

Se descarta (b) con el mismo razonamiento que allí: **nadie debe acordar el volumen de demanda de un
producto que no existe.** La demanda de este dataset no aproxima la de PluriOne y no pretende hacerlo;
§6 de la especificación ya dice que el volumen «no debe pretender representar el volumen real de la
organización».

La elección concreta de cada número persigue una sola propiedad: que cada comportamiento sea
**falsable midiendo la serie**, no leyendo una etiqueta. De ahí que el ruido errático sea cuatro veces
el estable y no un 20 % mayor, que los niveles de rotación estén separados por un orden de magnitud, y
que la intermitencia tenga su propio mecanismo. Un generador que produjera ruido plano bajo los ocho
nombres pasaría cualquier comprobación de etiquetas y fallaría todas las pruebas de comportamiento.

## Consecuencias

**Positivas**

1. El Componente 3 es implementable sin inventar nada sobre la marcha.
2. Todos los valores están en **un solo lugar**, etiquetados. Si mañana hay datos reales, se sabe
   exactamente qué sustituir.
3. Las seis formas y las dos rotaciones son **verificables sobre los datos**: con la escala vigente,
   la serie estable tiene un coeficiente de variación de 0,06 frente a 0,36 de la errática; la
   creciente termina en 1,53× su inicio y la decreciente en 0,46×; la intermitente tiene un 85 % de
   ceros frente al 0 % de la estable; la estacional tiene autocorrelación anual de 0,46 frente a
   −0,00 de la estable; y la rotación alta mueve 41,7 unidades/día de media frente a 3,0 de la baja.
4. Cero dependencias nuevas y cero flotantes.

**Costos aceptados**

1. Estos valores **se verán** en el dataset y alguien podría citarlos fuera de contexto. Mitigado con
   la advertencia de cabecera, con el banner del módulo y con `data_origin = SYNTHETIC` en cada fila.
2. Son constantes del código: cambiarlas exige tocar el Componente 3 y regenerar.
3. La precondición P-6 hace que algunas configuraciones válidas no sean atendibles. Es preferible a
   generar un dataset que incumple §8 sin avisar.

**Qué invalidaría esta decisión**

Que lleguen datos reales de consumo, en cuyo caso estas políticas dejan de usarse y `ASSUMPTION-001`
se cierra. O que se confirme que la granularidad real del histórico no es diaria (`docs/04` §8,
punto 7), lo que obligaría a revisar el mecanismo entero, no solo los parámetros.

## Lo que esta decisión NO hace

- **No** fija ninguna política empresarial, ni nivel de servicio, ni umbral, ni parámetro de compra.
- **No** decide el contrato de `demand.csv`: eso es `DT-034`.
- **No** asigna escenarios a SKU concretos en el sentido del Componente 7. C3 decide internamente el
  comportamiento que necesita para generar; `DT-025` prohíbe escribir esa asignación en ninguna
  entidad, y registrarla es del Componente 7.
- **No** genera desabastos, inventario ni consumo satisfecho. Es del Componente 4.
- **No** resuelve `DT-P12` (si §25 debe incorporar las filas de rotación), que sigue abierta.
- **No** modifica `config.py`, `dataset_config.yaml` ni el Componente 2.
