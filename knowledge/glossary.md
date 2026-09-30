# Glosario del dominio

**Estado:** Versión 1.0 — Etapa 0 · **Fecha:** 2026-09-04 · **Versión 1.1** — revisada en la auditoría de Etapa 0.1

Definiciones únicas y compartidas. Si un término significa una cosa en la aplicación y otra en un
informe de Power BI, el proyecto ha fallado. **Este documento es la referencia.**

Cada término incluye su equivalente en inglés, que es el usado en el código y en el esquema de datos
(`DT-017`).

---

## Producto e identificación

**SKU** *(Stock Keeping Unit)* — Unidad de mantenimiento de existencias. Identificador único de un
producto a efectos de inventario y de predicción. Es la **unidad de análisis y de decisión** del
sistema: se predice por SKU y se recomienda por SKU.

**Producto** *(Product)* — Artículo gestionado por el sistema, identificado por su SKU.

**Categoría** *(Category)* — Agrupación de productos para clasificación, agregación y análisis.

**Unidad de medida** *(Unit of measure)* — Unidad en la que se cuenta el producto (pieza, caja, kg…).
Debe ser coherente entre consumo, inventario y órdenes de compra.

**Clasificación ABC** *(ABC classification)* — Segmentación de productos por importancia, típicamente
según el valor de consumo: A (pocos artículos, gran parte del valor), B (intermedios), C (muchos
artículos, poco valor). Sirve para diferenciar el nivel de atención y la política aplicada.
**En V1 no se usa:** `abc_class` es un campo **derivado del consumo**, que todavía no existe, y el
Componente 2 lo deja nulo (`DT-029`). `DT-031` §V1-11 fija en consecuencia una **política única** para
todo el catálogo. El campo **no se elimina** del modelo: queda fuera del cálculo hasta que `BR-X07`
se cierre y exista histórico del que derivarlo.

**Rotación** *(Turnover / rotation)* — Velocidad a la que el inventario se consume y se repone. Alta
rotación: se consume con frecuencia. Baja rotación: permanece mucho tiempo almacenado.

---

## Inventario

**Inventario** *(Inventory)* — Cantidad de producto almacenada y disponible para su consumo o venta.

**Existencia física** *(On hand)* — Cantidad físicamente presente en la ubicación.

**Inventario comprometido / reservado** *(Reserved)* — Cantidad asignada a un pedido o consumo
pendiente. Está físicamente presente pero **no disponible** para otras necesidades.

**Inventario disponible** *(Available)* — `Existencia física − Comprometido`. Lo que realmente se
puede usar hoy.

**Saldo de apertura** *(Opening balance)* — Existencia con la que un producto empieza el periodo
**simulado**. En el dataset sintético se registra como un movimiento `ADJUSTMENT` con
`reference_type = INITIAL_INVENTORY` y `reason_code = OPENING_BALANCE`, para que el inventario sea
reconstruible desde los movimientos (`DT-036`). **No es una recepción** y no proviene de ninguna orden
de compra. Solo existe en datos sintéticos.

**Perfil de apertura** *(Opening profile)* — Etiqueta sintética —`AJUSTADO`, `NORMAL` o `HOLGADO`—
que multiplica el saldo de apertura de un producto por un factor, para que el dataset contenga
productos holgados y productos justos desde el primer día (`DT-036`). **Parámetro del generador, no
política de inventario.**

**Inventario en tránsito** *(In transit)* — Cantidad pedida a un proveedor y aún no recibida. Ya está
comprometida como compra pero todavía no está en el almacén.

**Posición de inventario** *(Inventory position)* — `Existencia física + En tránsito − Comprometido`.
Comparar contra la existencia física en lugar de contra la posición produce compras duplicadas: es el
error más común en reabastecimiento.

Tiene **dos lecturas**, y decir cuál se usa es obligatorio (`DT-012`, `docs/06` §4.2):
- **Posición contable** — con el **tránsito total**. Responde a "¿qué hay comprometido?". Se usa en
  informes de inventario y valoración.
- **Posición de decisión** — con el **tránsito efectivo**. Responde a "¿qué habrá disponible a
  tiempo?". **Es la que se compara con el punto de reorden.**

**Tránsito total** *(Total in transit)* — Todo lo pedido y no recibido. Hecho sobre el mundo.

**Tránsito efectivo** *(Effective in transit)* — La parte del tránsito que se espera recibir dentro
del intervalo de protección de la decisión que se evalúa. Es **relativo a una decisión**: la misma
orden es efectiva para un producto y no para otro. No se almacena; se deriva en cada cálculo.

**Movimiento de inventario** *(Inventory movement)* — Todo hecho que altera el inventario: recepción,
salida, ajuste, devolución, traspaso, merma. En este sistema los movimientos son **inmutables**.

**Ajuste** *(Adjustment)* — Movimiento que corrige una discrepancia entre el inventario registrado y
el real. No modifica registros previos: se añade como hecho nuevo.

---

## Demanda y consumo

**Demanda** *(Demand)* — Cantidad de producto que los clientes o la operación **necesitan** en un
periodo. No es directamente observable cuando hay desabasto.

**Consumo / Venta** *(Consumption / Sales)* — Cantidad efectivamente entregada o utilizada. Es lo que
el histórico registra: **demanda satisfecha**.

**Demanda censurada** *(Censored demand)* — Demanda no observable porque no había producto. En un
periodo de desabasto, el consumo registrado es una **cota inferior** de la demanda real. Ignorar esta
distinción sesga el modelo a la baja justo en los productos más críticos.

**Demanda intermitente** *(Intermittent demand)* — Patrón con muchos periodos de demanda cero
intercalados con demanda ocasional. Los métodos de pronóstico habituales rinden mal y requieren
técnicas específicas.

**Estacionalidad** *(Seasonality)* — Patrón que se repite con periodicidad conocida (semanal, mensual, anual).

**Tendencia** *(Trend)* — Dirección sostenida de la demanda a lo largo del tiempo: creciente,
estable o decreciente.

**Variabilidad** *(Variability)* — Grado de dispersión de la demanda respecto a su valor medio. Se
mide con la desviación estándar o el coeficiente de variación. **Es lo que el stock de seguridad cubre.**

**Coeficiente de variación** *(Coefficient of variation, CV)* — Desviación estándar dividida entre la
media. Permite comparar la variabilidad entre productos de escalas distintas.

**Demanda latente** *(Latent demand)* — Lo que se habría demandado si el inventario nunca hubiera
limitado nada. Solo es conocible en datos sintéticos, donde el generador la produce antes de saber si
habrá existencias (`demand.csv`, `DT-034`). Su contrapartida observable es el consumo.

**Demanda perdida** *(Lost sales)* — `demanda latente − consumo` de un día. **No se almacena como
columna**: se deriva comparando las dos series, que están ambas en disco (`DT-036`).

**Demanda reciente** *(d̄_recent)* — Media de la demanda de los últimos `W` días que el **generador
sintético** usa para decidir cuándo y cuánto pedir. **No es un pronóstico**, no incorpora
incertidumbre y no tiene ninguna relación con el motor predictivo (`DT-036`).

**Warm-up sintético** *(Synthetic warm-up)* — Los primeros `W` días de la serie de un producto, en los
que `d̄_recent` usa una ventana congelada porque todavía no hay `W` días de histórico. Durante esa
ventana el generador depende de demanda posterior al día simulado: es una característica declarada del
generador, no una fuga de información de un modelo. La demanda y el consumo generados **no** están
afectados; la precaución de uso está en `docs/05-motor-predictivo.md` §5.5 (`DT-036`).

---

## Abastecimiento

**Abastecimiento** *(Replenishment / Supply)* — Proceso de reponer inventario para cubrir la demanda futura.

**Lead time** *(Lead time)* — Tiempo transcurrido entre la emisión de una orden de compra y la
recepción del producto. Se distinguen dos:
- **Lead time acordado** *(Agreed lead time)* — El comprometido contractualmente por el proveedor.
- **Lead time observado** *(Observed lead time)* — El que realmente ocurre, calculado desde el
  histórico de recepciones: `received_at − purchase_order.issued_at` (`docs/04` §3.11). **Atención a
  la granularidad:** V1 no cuenta una observación por recepción —que es la lectura literal de §3.11—
  sino **una por línea de orden completamente recibida**, fechada por su última recepción, porque
  contar las entregas parciales subestimaría el lead time justo en los proveedores menos fiables
  (`DT-031` §V1-09). Es el que el
  sistema **usa** en sus cálculos, porque usar el acordado cuando el proveedor entrega
  sistemáticamente tarde genera desabastos previsibles (regla propuesta `BR-P01`, pendiente de
  confirmación, **implementada de forma provisional en V1**).
  En V1 el valor representativo es la **mediana de las últimas observaciones válidas** del par
  producto–proveedor, recalculada en cada evaluación con los datos disponibles hasta la fecha de la
  decisión, y con **fallback al acordado** mientras no haya histórico suficiente (`DT-031` §V1-09).
  La ventana es de **12 observaciones**, ordenadas por la fecha de **finalización** (la de su última
  recepción); con menos de **3** se aplica el fallback; por encima de **90 días** el valor se topa y
  se marca `LEAD_TIME_CAPPED`, conservando el valor sin topar (`DT-031` §`V1-09.1`, §`V1-09.2`). Esos
  tres números son **parámetros técnicos provisionales de V1**, no un compromiso comercial.
  Ambos conceptos conviven: el acordado es el compromiso contractual, el observado es la realidad, y
  su diferencia es el indicador de desempeño del proveedor (`docs/04` §3.17).

**Demanda durante el lead time** *(Demand during lead time, DDLT)* — Cantidad que se espera consumir
mientras se espera la llegada de un pedido. Es lo que el inventario debe cubrir como mínimo.

**Stock de seguridad** *(Safety stock)* — Inventario adicional que protege frente a la **variabilidad**
—de la demanda y del lead time— durante el periodo de reposición. No cubre la demanda esperada, sino
la incertidumbre sobre ella.

**Punto de reorden** *(Reorder point, ROP)* — Nivel de posición de inventario que, al alcanzarse,
dispara la recomendación de reponer. Conceptualmente: `demanda durante el lead time + stock de seguridad`.

**Umbral sintético de reposición** *(`s`, synthetic replenishment threshold)* — Umbral que el
**generador de datos sintéticos** usa para decidir cuándo emitir una orden: `ceil(d̄_recent × L)`
(`DT-036`). **No es un punto de reorden**: no lleva stock de seguridad, no usa pronóstico, no depende
de ningún nivel de servicio y no produce ninguna recomendación. Existe solo para que el histórico
sintético contenga órdenes en momentos plausibles, y desaparece en cuanto haya datos reales.

**Nivel objetivo** *(Order-up-to level, S)* — En políticas de revisión periódica, el nivel hasta el
que se repone en cada revisión.

**Periodo de revisión** *(Review period, R)* — Intervalo entre dos evaluaciones de la necesidad de
reposición. En revisión continua es cero; en revisión periódica, el periodo definido.

**Revisión continua** *(Continuous review)* — La posición de inventario se evalúa permanentemente y se
pide al alcanzar el punto de reorden.

**Revisión periódica** *(Periodic review)* — La posición se evalúa cada `R` periodos y se repone hasta
el nivel objetivo. Requiere más stock de seguridad, porque entre revisiones no hay oportunidad de reaccionar.

**Cobertura** *(Coverage / Days of supply)* — Número de días o periodos que el inventario actual puede
satisfacer al ritmo de demanda previsto. `Posición de inventario ÷ demanda diaria estimada`.

**Necesidad bruta** *(Raw need)* — Cantidad que falta para cubrir el horizonte de protección, una vez
descontado lo que ya se tiene o se espera a tiempo: `max(0, demanda del horizonte + stock de
seguridad − posición de inventario)`. Es **anterior** a las restricciones del proveedor. Aparece en el
proyecto con **tres nombres que designan lo mismo**: `Q_bruta` (`docs/06` §8), `raw_quantity` (campo
persistido, `docs/04` §3.16) y `raw_need` (nombre del cálculo, `DT-031`). La especificación del
dataset usa además «necesidad calculada» (§16), «necesidad inmediata» (§17) y «necesidad real» (§17)
sin definirlas; **todas se refieren a este concepto**.

**Horizonte de cobertura** *(Coverage horizon)* — Periodo futuro que la recomendación debe cubrir.
Bajo revisión periódica es el **intervalo de protección** `lead time + periodo de revisión`
(`ASSUMPTION-002`, `docs/06` §5). No confundir con el **horizonte de predicción**, que es la extensión
del pronóstico y debe ser al menos igual de largo.

**MOQ** *(Minimum Order Quantity)* — Cantidad mínima que el proveedor acepta por pedido. Puede forzar
a comprar más de lo necesario, generando sobrecobertura. **No tiene por qué ser múltiplo del múltiplo
de compra**; cuando no lo es, el mínimo pedible real es `⌈MOQ/M⌉·M`, no el MOQ.

**Múltiplo de compra** *(Order multiple / Lot size)* — Incremento en que debe expresarse la cantidad
pedida (caja, pallet, contenedor).

**Orden de compra** *(Purchase order, PO)* — Documento que formaliza un pedido a un proveedor.

**Recepción** *(Receipt)* — Registro de la llegada efectiva de la mercancía de una orden.

**Nivel de servicio** *(Service level)* — Objetivo de disponibilidad. **Existen dos definiciones y no
son intercambiables**:
- **Nivel de servicio por ciclo** *(Cycle service level)* — Probabilidad de no agotar existencias
  durante un ciclo de reposición.
- **Tasa de satisfacción** *(Fill rate)* — Proporción de la demanda satisfecha directamente desde inventario.

El negocio debe indicar cuál usa: producen stocks de seguridad distintos.

---

## Riesgos

**Desabasto** *(Stockout)* — Situación en que no hay inventario para satisfacer la demanda. Genera
pérdida de venta, paro operativo o compra urgente.

**Riesgo de desabasto** *(Stockout risk)* — Probabilidad o indicio de que un producto se agote dentro
del horizonte considerado.

**Sobreinventario** *(Overstock / Excess inventory)* — Inventario significativamente superior a la
demanda previsible. Inmoviliza capital, ocupa espacio y expone a obsolescencia.

**Obsolescencia** *(Obsolescence)* — Pérdida de valor o utilidad del inventario por caducidad,
sustitución o cambio de demanda.

**Capital inmovilizado** *(Tied-up capital)* — Valor monetario del inventario que no está generando
retorno mientras permanece almacenado.

**Confiabilidad del proveedor** *(Supplier reliability)* — Grado en que un proveedor cumple lo
comprometido en tiempo y cantidad. Su variabilidad se traduce directamente en más stock de seguridad,
y por tanto en más capital inmovilizado.

---

## Predicción

**Forecast / Pronóstico** *(Forecast)* — Estimación de la demanda futura para un producto y periodo.
Incluye siempre una medida de incertidumbre.

**Horizonte de predicción** *(Forecast horizon)* — Extensión temporal que abarca la predicción. Debe
cubrir al menos el lead time más el periodo de revisión.

**Granularidad** *(Granularity)* — Unidad temporal del pronóstico: diaria, semanal o mensual.

**`as_of_date`** — Fecha de corte de la información utilizada para generar una predicción. Fundamental
para demostrar que no se usó información futura y para evaluar después la calidad del pronóstico.

**Intervalo de predicción** *(Prediction interval)* — Rango dentro del cual se espera que caiga la
demanda real, con un nivel de confianza declarado. Es **una de las fuentes candidatas** de la
incertidumbre que alimenta el stock de seguridad; cuál se usa está `PENDIENTE DE VALIDACIÓN`
(`DT-010`), y usar el intervalo del modelo exige antes verificar su calibración.

**Baseline** *(Baseline)* — Método de referencia simple contra el que se compara todo modelo. Si un
modelo no lo supera, no aporta valor. También actúa como mecanismo de respaldo.

**Backtesting / Validación temporal** *(Backtesting, rolling origin)* — Evaluación que simula el paso
del tiempo: se entrena con datos hasta una fecha y se evalúa sobre lo posterior, repitiendo el proceso
en varios cortes.

**Fuga de información** *(Data leakage)* — Uso, durante el entrenamiento, de información que no
estaría disponible en el momento real de la predicción. Produce métricas excelentes en evaluación y
un fracaso en producción.

**Sesgo** *(Bias)* — Tendencia sistemática a sobreestimar o subestimar. Un sesgo negativo persistente
produce desabastos crónicos aunque el error absoluto parezca aceptable.

**Deriva** *(Drift)* — Cambio en la distribución de los datos o en la relación entre variables que
degrada la calidad del modelo con el tiempo, sin producir ningún error visible.

**Versión de modelo** *(Model version)* — Identificación de un modelo entrenado concreto, con sus
métricas, datos y fecha. Cada predicción referencia la versión que la generó.

**MASE, MAE, RMSE, WAPE** — Métricas de error de pronóstico. MASE es comparable entre series de
escalas distintas y robusta ante demanda cero; MAPE no lo es y no se usa como métrica de decisión.

---

## Sistema

**Motor predictivo** *(Predictive engine)* — Componente que estima la demanda futura. **No decide compras.**

**Motor de abastecimiento** *(Supply engine)* — Componente que aplica reglas determinísticas para
calcular stock de seguridad, punto de reorden, cantidad recomendada y riesgos. **No predice.**

**Recomendación** *(Recommendation)* — Propuesta de compra generada por el sistema: producto, cantidad,
proveedor, fecha y urgencia, con el desglose completo de su cálculo. **Nunca se ejecuta automáticamente.**

**RAG** *(Retrieval-Augmented Generation)* — Técnica que recupera fragmentos de documentos relevantes
y los entrega como contexto a un modelo de lenguaje, para que responda con base en fuentes citables
en lugar de en su memoria.

**Datos sintéticos** *(Synthetic data)* — Datos generados artificialmente que simulan un escenario
empresarial verosímil, usados mientras no se dispone de datos reales.

**Determinístico** *(Deterministic)* — Que produce siempre el mismo resultado con las mismas entradas.
Propiedad exigida a todo el motor de abastecimiento.

**Trazabilidad** *(Traceability)* — Capacidad de reconstruir por qué el sistema produjo un resultado
concreto en una fecha pasada, con los insumos y versiones vigentes en aquel momento.
