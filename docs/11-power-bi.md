# 11 — Diseño analítico en Power BI

**Estado:** Versión 1.0 — Etapa 0 (diseño, **no implementado**) · **Fecha:** 2026-09-04 · **Versión 1.1** — revisada en la auditoría de Etapa 0.1 · **Versión 1.2** (2026-09-30) — §9, fuentes de la Etapa 2; §§1–8 no cambian · **Versión 1.3** (2026-10-03) — §9: corrección de la fila de recomendaciones (`DT-P18` cerrada por `DT-059`) · **Versión 1.4** (2026-10-06) — §10: capa analítica de U9 implementada, pendiente de revisión (`DT-097`); ningún informe ni conexión de Power BI

> **No se crea ningún dashboard en esta etapa.** Se define qué se va a medir y con qué estructura,
> para que el modelo de datos de la Fase 2 ya contemple lo que la analítica necesitará.

---

## 1. Alcance y frontera con la aplicación

| | Aplicación web | Power BI |
|---|---|---|
| **Público** | Planificador, comprador, analista | Dirección, finanzas, compras, gestión |
| **Pregunta** | "¿Qué hago hoy con este SKU?" | "¿Cómo va el abastecimiento en conjunto?" |
| **Horizonte** | Operativo, inmediato | Táctico y estratégico, con tendencia |
| **Interacción** | Acciones sobre el sistema | Solo lectura y exploración |
| **Detalle** | SKU individual | Agregados por categoría, proveedor, periodo |

**Regla de oro:** **ninguna lógica de negocio se reimplementa en Power BI.** Los puntos de reorden,
el stock de seguridad, la cobertura y los niveles de riesgo se calculan **una vez**, en el motor de
abastecimiento, y Power BI los consume ya calculados. Reimplementar una fórmula en DAX produciría dos
verdades distintas para el mismo indicador, que es precisamente lo que el proyecto trata de eliminar.

En Power BI solo se calculan **agregaciones** (sumas, promedios, conteos, evolución) sobre valores
que el sistema ya produjo.

## 2. Conexión

- **Origen:** PostgreSQL, mediante el conector nativo de Power BI, sobre **vistas analíticas
  dedicadas** — nunca directamente sobre las tablas operativas.
- **Usuario:** de solo lectura, con acceso limitado a esas vistas (`docs/10-seguridad.md` §7).
- **Modo de conexión:** *Import* como opción por defecto, con actualización programada. El volumen de
  referencia (ASSUMPTION-012) lo permite y ofrece mejor rendimiento y flexibilidad de modelado.
  DirectQuery se reservará para el caso en que se requiera latencia baja sobre datos operativos, y se
  decidirá con evidencia en la Fase 11 (`DT-014`, estado `PROPUESTA`).
- **Frecuencia de actualización:** alineada con el proceso batch de recálculo (propuesta: diaria,
  posterior a la generación de forecast y recomendaciones).

## 3. Modelo dimensional

Esquema en estrella, construido sobre vistas.

```mermaid
erDiagram
    DIM_DATE ||--o{ FACT_CONSUMPTION : fecha
    DIM_DATE ||--o{ FACT_INVENTORY_SNAPSHOT : fecha
    DIM_DATE ||--o{ FACT_FORECAST : fecha
    DIM_DATE ||--o{ FACT_PURCHASE_ORDER : fecha
    DIM_PRODUCT ||--o{ FACT_CONSUMPTION : producto
    DIM_PRODUCT ||--o{ FACT_INVENTORY_SNAPSHOT : producto
    DIM_PRODUCT ||--o{ FACT_FORECAST : producto
    DIM_PRODUCT ||--o{ FACT_RECOMMENDATION : producto
    DIM_SUPPLIER ||--o{ FACT_PURCHASE_ORDER : proveedor
    DIM_SUPPLIER ||--o{ FACT_RECOMMENDATION : proveedor
    DIM_CATEGORY ||--o{ DIM_PRODUCT : clasifica
    DIM_LOCATION ||--o{ FACT_INVENTORY_SNAPSHOT : ubicación
```

### 3.1 Dimensiones

| Dimensión | Atributos principales |
|---|---|
| `DIM_DATE` | Fecha, día, semana, mes, trimestre, año, día hábil, festivo (**pendiente**: calendario del negocio) |
| `DIM_PRODUCT` | SKU, nombre, categoría, unidad, clase ABC, clase de rotación, segmento de serie, estado |
| `DIM_CATEGORY` | Código, nombre, jerarquía |
| `DIM_SUPPLIER` | Código, nombre, estado, segmento de confiabilidad |
| `DIM_LOCATION` | Código, nombre, tipo |
| `DIM_MODEL_VERSION` | Versión, algoritmo, fecha de entrenamiento, estado |

### 3.2 Tablas de hechos

| Hecho | Grano | Medidas |
|---|---|---|
| `FACT_CONSUMPTION` | Producto × ubicación × día | Cantidad consumida, indicador de desabasto |
| `FACT_INVENTORY_SNAPSHOT` | Producto × ubicación × día | On hand, comprometido, en tránsito, posición, valor, cobertura en días |
| `FACT_FORECAST` | Producto × ubicación × periodo × `as_of_date` | Cantidad prevista, límites del intervalo, método, versión de modelo |
| `FACT_RECOMMENDATION` | Producto × fecha de generación | Cantidad recomendada, urgencia, punto de reorden, stock de seguridad, estado, resolución |
| `FACT_PURCHASE_ORDER` | Línea de orden × evento | Cantidad pedida, recibida, pendiente, importe, días de retraso |
| `FACT_FORECAST_ACCURACY` | Producto × periodo | Previsto, real, error, error absoluto, sesgo |

**Nota sobre `FACT_INVENTORY_SNAPSHOT`:** la fotografía diaria del inventario es necesaria para poder
analizar la evolución y calcular rotación y cobertura históricas. Reconstruirla cada vez a partir de
los movimientos sería costoso y frágil. Su generación se define en la Fase 2.

**Nota sobre `as_of_date` en `FACT_FORECAST`:** conservarla permite responder la pregunta más útil
sobre la calidad del pronóstico — "¿qué predecíamos hace ocho semanas y qué ocurrió realmente?" —,
que es la base de `FACT_FORECAST_ACCURACY`.

## 4. KPIs

### 4.1 Indicadores de inventario

| KPI | Definición | Interpretación |
|---|---|---|
| **Stock actual** | Existencia física total, en unidades y en valor | Volumen y capital |
| **Posición de inventario (contable)** | On hand + tránsito **total** − comprometido | Situación de aprovisionamiento comprometida. La posición **de decisión**, con el tránsito efectivo, vive en la aplicación y no se recalcula aquí (`DT-012`) |
| **Cobertura media (días)** | Posición ÷ demanda diaria prevista | Cuánto tiempo aguanta el inventario |
| **Rotación de inventario** | Consumo del periodo ÷ inventario medio | Eficiencia del capital |
| **Valor de inventario** | Σ (cantidad × costo unitario) | Capital inmovilizado |
| **Inventario sin movimiento** | SKU con existencia y sin consumo en N periodos | Candidatos a liquidación |
| **Exactitud de inventario** | Desviación de los ajustes sobre el total | Calidad del dato |

### 4.2 Indicadores de abastecimiento

| KPI | Definición |
|---|---|
| **Productos críticos** | SKU con riesgo de desabasto `CRITICAL` o `HIGH` |
| **Productos en sobreinventario** | SKU con cobertura por encima del umbral de política |
| **Recomendaciones abiertas** | Número y valor de las recomendaciones sin resolver, por urgencia |
| **Órdenes pendientes** | Órdenes emitidas no recibidas, en número, valor y unidades |
| **Antigüedad de órdenes pendientes** | Días desde la emisión de órdenes aún abiertas |
| **Tasa de conversión de recomendaciones** | Recomendaciones convertidas en orden ÷ recomendaciones emitidas |
| **Tasa de descarte y motivos** | Proporción de recomendaciones descartadas, agrupadas por motivo |

Los dos últimos son los indicadores de **adopción del sistema**. Una tasa de descarte alta con un
motivo recurrente no significa que los planificadores se equivoquen: significa que al motor le falta
una restricción que ellos sí conocen. Es la señal más valiosa para mejorar las reglas.

### 4.3 Indicadores de proveedores

| KPI | Definición |
|---|---|
| **Cumplimiento en tiempo** | % de recepciones dentro de la fecha comprometida |
| **Cumplimiento en cantidad** | Cantidad recibida ÷ cantidad pedida |
| **Lead time medio observado** | Media de días entre emisión y recepción |
| **Variabilidad del lead time** | Desviación estándar del lead time observado |
| **Desviación acordado vs. observado** | Lead time observado − lead time acordado |
| **Concentración de proveedor** | % de compra concentrada en un proveedor (riesgo de dependencia) |
| **Impacto en stock de seguridad** | Parte del stock de seguridad atribuible a la variabilidad del proveedor |

El último KPI traduce el desempeño del proveedor a dinero inmovilizado. Es el argumento cuantitativo
para una negociación.

### 4.4 Indicadores predictivos

| KPI | Definición |
|---|---|
| **Demanda proyectada** | Demanda prevista agregada por categoría y periodo |
| **Error de pronóstico (WAPE / MASE)** | Error agregado ponderado por volumen |
| **Sesgo del pronóstico** | Error con signo acumulado: detecta sobre o subestimación sistemática |
| **Cobertura del intervalo** | % de observaciones dentro del intervalo declarado |
| **Uso de baseline** | % de SKU predichos con baseline en lugar de modelo |
| **SKU sin predicción** | Productos que no obtuvieron estimación y por qué |
| **Evolución del error por versión de modelo** | Comparación entre versiones a lo largo del tiempo |

El **sesgo** merece atención especial: un sesgo negativo persistente produce desabastos crónicos
aunque el error absoluto parezca aceptable, y es invisible en las métricas habituales de error.

### 4.5 Indicadores de impacto (a construir cuando haya histórico)

| KPI | Definición |
|---|---|
| **Incidencias de desabasto** | Número de SKU-día con existencia cero y demanda |
| **Evolución del capital inmovilizado** | Valor de inventario a lo largo del tiempo |
| **Compras urgentes** | Órdenes emitidas con lead time inferior al normal (proxy del costo logístico extra) |
| **Nivel de servicio alcanzado** | Demanda satisfecha ÷ demanda total |

Estos son los indicadores que miden si el proyecto **cumple su objetivo**. Los demás miden si el
sistema funciona; estos, si sirve.

**Coinciden deliberadamente con las métricas de Nivel 2** de `docs/05-motor-predictivo.md` §9.4, que
son las que deciden si un modelo se promueve (`DT-020`). Es la misma pregunta formulada en dos
horizontes: en Power BI, cómo va el abastecimiento en producción; en la evaluación del modelo, si un
forecast concreto lo mejoraría. **La definición de cada métrica debe ser una sola**, y vive en
`knowledge/glossary.md`.

## 5. Informes previstos

| Informe | Público | Contenido |
|---|---|---|
| **Panorama de inventario** | Dirección, finanzas | Valor, cobertura, rotación, evolución, distribución por categoría |
| **Situación de abastecimiento** | Compras | Productos críticos, recomendaciones abiertas, órdenes pendientes |
| **Desempeño de proveedores** | Compras, gestión | Cumplimiento, lead times, variabilidad, concentración |
| **Calidad del pronóstico** | Analistas, TI | Error, sesgo, cobertura del intervalo, uso de baseline, evolución por versión |
| **Impacto del sistema** | Dirección | Desabastos, sobreinventario, nivel de servicio, capital, adopción |

## 6. Reglas de construcción

1. **Sin lógica de negocio en DAX.** Solo agregaciones.
2. **Sin conexión a tablas operativas.** Solo vistas analíticas dedicadas y documentadas.
3. **Definición única de cada métrica**, documentada en `knowledge/glossary.md`. Si "cobertura"
   significa una cosa en la aplicación y otra en el informe, el proyecto ha fallado.
4. **Fecha de actualización visible** en cada informe: un dato de ayer presentado como de hoy induce
   a error operativo.
5. **Seguridad:** el acceso a los informes se gestiona en Power BI; si se requiere restricción por
   categoría o ubicación, se implementará con seguridad a nivel de fila (**pendiente**, §8).
6. **Coherencia de nombres** con el glosario y con la interfaz de la aplicación.

## 7. Dependencias con otras fases

| Necesita | De |
|---|---|
| Vistas analíticas en PostgreSQL | Fase 2 |
| Fotografía diaria de inventario | Fase 2 |
| Forecast persistido con `as_of_date` | Fase 5 |
| Recomendaciones con estado y motivo de resolución | Fase 4 |
| Métricas de desempeño de proveedor | Fase 4 |
| Métricas de exactitud del pronóstico | Fase 5–6 |

## 8. Pendiente de definición

1. ¿Existe una licencia y una capacidad de Power BI disponibles? ¿Qué tipo?
2. ¿Quién consumirá los informes y con qué frecuencia?
3. ¿Se requiere seguridad a nivel de fila por categoría, ubicación o unidad de negocio?
4. Calendario laboral y festivos del negocio (necesario para `DIM_DATE`).
5. ¿Hay informes existentes cuyas definiciones deban respetarse para mantener continuidad?
6. ¿Se requiere distribución automática (suscripciones, alertas)?
7. Periodo de histórico a conservar en el modelo analítico.

## 9. Etapa 2 — fuentes y KPIs calculables con el dataset 0.4.0

*Añadido el 2026-09-30. **No se construye ningún informe ni vista** hasta la Fase 11. Esta tabla
evita dos errores: prometer KPIs que dependen de parámetros inexistentes, y recalcular en DAX lo que
calcula el motor (§1).*

| KPI (§4) | Fuente (`docs/04` §9) | Granularidad | ¿Calculable con 0.4.0? |
|---|---|---|---|
| Stock actual (unidades) | `inventory` | Producto × ubicación, al corte | Sí |
| Posición de inventario contable | `inventory` | Ídem | Sí |
| Rotación, inventario sin movimiento | `consumption` + fotografía diaria reconstruida desde `inventory_movements` | Producto × día | Sí, cuando exista la vista de fotografía diaria (§3.2) |
| Órdenes pendientes y su antigüedad | `purchase_orders`, `purchase_order_items` | Línea | Sí |
| Lead time observado, variabilidad, cumplimiento en tiempo y en cantidad | Órdenes y recepciones | Línea / proveedor | Sí (indicadores de gestión; RF-016 sigue siendo clase D) |
| Incidencias de desabasto | `consumption.is_stockout_affected` | Producto × día | Sí |
| Nivel de servicio alcanzado (satisfecha ÷ total) | `consumption` ÷ `demand` | Producto × periodo | **Solo con datos sintéticos**: con datos reales no existe la demanda total |
| Valor de inventario, capital inmovilizado | `inventory` × costo | — | **Pendiente**: falta la regla de valoración (qué costo si hay varios proveedores) y, para el capital, el umbral de exceso (`BR-X03`) |
| Productos críticos, sobreinventario | Motor | — | **Bloqueado** por `BR-X03` |
| Recomendaciones abiertas, conversión, descarte | `recommendations` | — | Tras U4 (implementada) y un flujo de resolución humana que no existe en V1: `DT-059` (cerró `DT-P18`) no crea `status` ni `resolved_*` |
| Error de pronóstico, sesgo, cobertura del intervalo, uso de baseline | `forecasts` frente a `consumption` | Producto × semana | Tras U3 (baseline) y Fase 5 |

Quién consume cada informe sigue pendiente del negocio (§8.2). Ningún KPI de esta tabla se presenta
como métrica real de la organización mientras la fuente sea `SYNTHETIC` (`DT-004`).

## 10. Capa analítica implementada (U9, `DT-097`, 2026-10-06, pendiente de revisión)

Migración `0004`, esquema `analytics`, rol `analytics_reader` (solo `SELECT` sobre estas vistas; `docs/10` §7). Es
el origen previsto en §2 para U16. Las fórmulas de los indicadores están en `knowledge/glossary.md`
(«Indicadores analíticos»), su definición única (§6.3). Aquí se dice qué vista los sostiene.

| Vista | Grano | Para qué | Fuente |
|---|---|---|---|
| `data_load` | Una fila (carga `COMPLETED`) | Fecha de los datos y corte, visibles en cada informe (§6.4) | `data_loads` |
| `dim_date` | Día | Calendario natural (sin día hábil ni festivos: calendario del negocio pendiente) | Periodo cargado y horizonte de forecast |
| `dim_product`, `dim_category`, `dim_supplier`, `dim_location`, `dim_model_version` | Una fila por entidad | Dimensiones de §3.1 que existen en la base (sin segmento de serie ni de confiabilidad; sin datos de contacto) | Tablas maestras y `model_versions` |
| `fact_consumption` | Producto × ubicación × día | Consumo, desabasto y demanda latente (solo `SYNTHETIC`) | `consumption`, `demand` |
| `fact_inventory_current` | Producto × ubicación al corte | Stock actual y posición contable | `inventory` |
| `fact_inventory_daily` | Producto × ubicación × día | Existencia al cierre del día (suma de movimientos), base de rotación e inventario medio | `inventory_movements` |
| `fact_purchase_order_line` | Línea de orden | Pendientes y antigüedad, lead time observado, cumplimiento en tiempo y cantidad | Órdenes, líneas, recepciones, `product_suppliers` |
| `fact_forecast` | Producto × ubicación × semana × corte × versión | Demanda proyectada y uso de baseline | `forecasts` de ejecuciones `COMPLETED` |
| `fact_recommendation` | Ejecución × producto × ubicación | Evaluaciones del motor por resultado, con sus magnitudes ya calculadas | `recommendations` de ejecuciones `COMPLETED` |

Los KPI de §9 que siguen pendientes o bloqueados no tienen vista; la lista está en `DT-097`. **Pendiente para U16:**

- Import o DirectQuery (`DT-014`);
- RLS (`DT-P10`);
- la cuenta de conexión y su secreto;
- licencia y publicación;
- los informes;
- los indicadores fuera de U9.
