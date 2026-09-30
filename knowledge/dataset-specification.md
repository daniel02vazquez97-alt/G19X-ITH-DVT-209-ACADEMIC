# Especificación del dataset sintético

**Estado:** Versión 1.1 — Etapa 1
**Fecha:** 2026-09-09 · **Revisión 1.1:** 2026-09-18 — se añaden §§41 a 44 (formato de salida, metadata de generación, políticas de generación sintética y determinismo) y se actualiza §40 con el estado de sus prerrequisitos. Decisiones `DT-024` a `DT-030`. · **Revisión 1.2:** 2026-09-24 — excepción de vigencia para las recepciones de órdenes en vuelo (§34, enmienda de `DT-027`), saldo de apertura en §7.6, cierre del pendiente de `data_origin` en §34 y reparto de archivos de los Componentes 4, 5 y 6 en §41.3. Decisiones `DT-036` y `DT-037`. · **Revisión 1.3:** 2026-09-24 — contratos de columnas de los Componentes 4 y 5 (§41.3 y §34, *Integridad de formato*) y texto completo de la excepción de vigencia en §34. Decisiones `DT-038` y `DT-039`. · **Revisión 1.4:** 2026-09-26 — publicación atómica del dataset (§41.3, `DT-040`) y precisión de la autoría de los identificadores en la tabla de §41.3. · **Revisión 1.5:** 2026-09-26 — estado del Componente 4 en la tabla de §41.3 (implementado, sin conectar). · **Revisión 1.6:** 2026-09-28 — estado del Componente 5 en la tabla de §41.3 (implementado, sin conectar). · **Revisión 1.7:** 2026-09-28 — estado del Componente 6 en la tabla de §41.3 (implementado, sin conectar). · **Revisión 1.8:** 2026-09-29 — los Componentes 4, 5 y 6 se ejecutan a través de W1 (`DT-040`) y sus archivos forman parte del dataset publicado. · **Revisión 1.9:** 2026-09-29 — Componentes 7 y 8 (`DT-041`, `DT-042`): `scenario_assignment` y `quality_report` como campos del manifiesto (§42.3), sin CSV propios (§34, §41.3); contenido del informe de §35; estado de §39 y §40; dataset 0.4.0 publicado y validado.
**Propósito:** Especificar el dataset sintético utilizado para desarrollar, probar y validar el Motor Predictivo de Abastecimiento de Inventarios.

---

## 1. Propósito

Este documento define las características, estructura, escenarios y criterios de calidad que debe cumplir el dataset sintético utilizado durante la Etapa 1 del proyecto **Desarrollo de un Motor Predictivo de Abastecimiento de Inventarios**.

El dataset tiene como objetivo proporcionar un entorno controlado y reproducible que permita desarrollar y validar posteriormente:

* el modelo de datos;
* el proceso de ingestión;
* el motor de abastecimiento;
* los modelos predictivos;
* las pruebas de integración;
* la evaluación retrospectiva de decisiones de abastecimiento;
* las visualizaciones y análisis posteriores.

Los datos serán sintéticos y no representan información real de la organización.

El dataset debe representar un escenario empresarial coherente. No se generarán registros independientes mediante valores aleatorios sin relación entre sí.

---

## 2. Alcance

El dataset debe cubrir, como mínimo, los siguientes dominios:

1. Catálogo de productos.
2. Categorías.
3. Proveedores.
4. Relación producto-proveedor.
5. Ubicaciones.
6. Inventario.
7. Movimientos de inventario.
8. Consumo histórico.
9. Órdenes de compra.
10. Partidas de órdenes de compra.
11. Recepciones de órdenes de compra.
12. Políticas de inventario.
13. Información necesaria para evaluar desempeño de proveedores.
14. Información necesaria para generar forecasts.
15. Información necesaria para probar recomendaciones de abastecimiento.
16. Metadatos de origen y carga.

El dataset no implementará todavía la lógica de producción de los motores predictivo y de abastecimiento. Su función es proporcionar los datos necesarios para que estos componentes puedan desarrollarse y probarse posteriormente.

---

## 3. Principios de generación

El dataset debe cumplir los siguientes principios.

### 3.1 Coherencia

Los registros deben representar una misma realidad empresarial.

Por ejemplo:

* una recepción debe corresponder a una orden de compra existente;
* una orden debe corresponder a un proveedor y producto válidos;
* un movimiento de recepción debe poder relacionarse con una recepción;
* el inventario debe poder reconstruirse a partir de los movimientos históricos;
* el lead time observado debe poder calcularse a partir de las fechas de emisión y recepción;
* las cantidades recibidas no deben contradecir las cantidades ordenadas, salvo que el escenario esté diseñado explícitamente para probar una regla de sobre-recepción pendiente de definición.

### 3.2 Temporalidad

Los datos deben respetar el orden temporal de los acontecimientos.

Como regla general:

```text
orden emitida
      ↓
fecha esperada
      ↓
recepción
      ↓
movimiento de inventario
```

Las fechas utilizadas para entrenamiento y evaluación deben permitir distinguir claramente la información disponible en cada momento.

### 3.3 Reproducibilidad

La generación debe utilizar una semilla explícita.

Una misma configuración y una misma semilla deben producir el mismo dataset.

Esto permitirá:

* reproducir errores;
* comparar versiones del generador;
* repetir experimentos de ML;
* validar cambios;
* facilitar auditorías.

### 3.4 Sustituibilidad

Los datos sintéticos deben poder sustituirse posteriormente por datos reales sin modificar las reglas de negocio.

Cada registro o carga debe indicar su origen mediante el mecanismo definido por el modelo de datos.

El origen esperado durante esta etapa será:

```text
SYNTHETIC
```

No debe existir ninguna regla de negocio que dependa de que el dato sea sintético.

### 3.5 No inventar políticas empresariales

Los parámetros de negocio todavía pendientes no deben convertirse en requisitos definitivos del dataset.

Cuando sea necesario utilizar valores para construir escenarios técnicos, estos deben identificarse explícitamente como valores sintéticos de prueba y no como políticas de la organización.

---

# 4. Horizonte temporal

El dataset debe contener suficiente historia para permitir posteriormente el desarrollo y evaluación de modelos de forecasting.

La estrategia predictiva establece como hipótesis inicial que se requieren aproximadamente **24–36 meses de historia** para detectar adecuadamente patrones de estacionalidad anual.

Esta cantidad constituye una hipótesis de trabajo y no una característica confirmada de los datos reales de la organización.

La generación debe mantener una frecuencia diaria para el consumo histórico.

Posteriormente, los modelos podrán trabajar con agregaciones semanales de acuerdo con la estrategia definida en `docs/05-motor-predictivo.md`.

---

# 5. Granularidad

La granularidad principal del dataset histórico será:

```text
Producto × Ubicación × Día
```

para los datos de consumo y los elementos que requieran seguimiento diario.

Los datos de compras deberán conservar sus fechas de emisión, fechas esperadas y fechas reales de recepción.

El dataset debe conservar suficiente detalle para reconstruir situaciones históricas y permitir posteriormente agregaciones semanales o de otras granularidades.

---

# 6. Universo sintético

El universo debe representar una organización que administra múltiples productos y proveedores.

La primera versión debe contemplar:

* múltiples productos;
* múltiples categorías;
* múltiples proveedores;
* relación de varios productos con proveedores;
* una ubicación operativa principal.

Aunque la primera versión puede trabajar con una sola ubicación agregada, el modelo debe conservar la dimensión de ubicación para permitir una futura ampliación sin rediseñar el dominio.

Esto corresponde a `ASSUMPTION-006`.

El volumen inicial debe ser suficiente para probar el sistema, pero no debe pretender representar el volumen real de la organización.

La referencia de volumen existente en `ASSUMPTION-012` es una hipótesis para dimensionamiento y no constituye un requisito para que el dataset sintético replique exactamente dicho volumen.

---

# 7. Entidades del dataset

El dataset debe poder representar las siguientes entidades definidas en `docs/04-modelo-datos.md`.

> **Marca de origen en las entidades maestras** (`DT-026`). `Category`, `Product`, `Supplier`,
> `ProductSupplier` y `Location` llevan, como el resto de entidades cargadas, el campo `data_origin`
> con el valor `SYNTHETIC` durante esta etapa (§19, §34). La marca es **por registro**. La metadata
> de generación del dataset —semilla, versión del generador, escenarios configurados— **no** vive en
> estas entidades: vive en `manifest.json` (§42).

## 7.1 Category

Representa las categorías de productos.

Debe permitir relacionar cada producto con una categoría.

La primera versión utilizará una jerarquía de categorías simple, de acuerdo con `ASSUMPTION-009`.

---

## 7.2 Product

Representa el catálogo de productos.

Cada producto debe tener como mínimo:

* identificador;
* SKU;
* nombre o descripción;
* categoría;
* unidad de medida;
* estado activo/inactivo;
* fechas de creación o vigencia según corresponda.

La vigencia se representa mediante los campos `valid_from` y `valid_to` de `Product`, definidos en
`docs/04-modelo-datos.md` §3.2 (`DT-027`). Son campos de **dominio** y no deben confundirse con
`created_at` / `updated_at`, que son auditoría técnica del registro. `valid_from` es obligatorio;
`valid_to` nulo significa que el producto sigue vigente y no hay fecha de fin prevista.

Es contra este intervalo contra el que se comprueba la coherencia temporal del §20 («el consumo debe
ocurrir dentro del periodo de existencia del producto»).

El SKU debe ser estable y único.

El dataset debe contener productos activos y escenarios que permitan comprobar el tratamiento de productos inactivos.

---

## 7.3 Supplier

Representa a los proveedores.

Cada proveedor debe contar con un identificador estable.

El dataset debe incluir proveedores con diferentes comportamientos de entrega para permitir evaluar posteriormente:

* lead time observado;
* variabilidad del lead time;
* entregas puntuales;
* retrasos;
* entregas parciales.

---

## 7.4 ProductSupplier

Representa la relación entre productos y proveedores.

Debe permitir almacenar:

* producto;
* proveedor;
* lead time acordado;
* MOQ;
* múltiplo de compra;
* costo unitario;
* indicador de proveedor preferente;
* vigencia o estado de la relación.

La información debe permitir representar productos con uno o varios proveedores.

No se implementará todavía una función de puntuación automática entre proveedores.

La regla `BR-P07` propone utilizar el proveedor preferente mientras no exista un criterio empresarial de selección confirmado.

---

## 7.5 Location

Representa la ubicación donde se administra el inventario.

La primera versión puede utilizar una única ubicación.

La entidad debe existir desde el inicio para conservar la capacidad de extender el sistema a múltiples ubicaciones posteriormente.

---

## 7.6 InventoryMovement

Representa hechos históricos de movimiento de inventario.

Los tipos contemplados son:

```text
RECEIPT
ISSUE
ADJUSTMENT
RETURN
TRANSFER_IN
TRANSFER_OUT
SCRAP
```

Los movimientos históricos deben tratarse como hechos inmutables.

Una corrección debe representarse como un nuevo movimiento y no modificando el movimiento original.

Cada registro debe permitir identificar su origen:

```text
SYNTHETIC
```

durante esta etapa.

> **Saldo de apertura del periodo simulado** (`DT-036` §7). El inventario inicial que el Componente 4
> asigna a cada par producto–ubicación se registra como un movimiento `ADJUSTMENT` con
> `reference_type = INITIAL_INVENTORY`, `reference_id` vacío y `reason_code = OPENING_BALANCE`. **No
> es una recepción**, no proviene de una orden de compra, no genera ninguna y no es `SCRAP`:
> representa exclusivamente el estado inicial del periodo. Se registra como movimiento porque, de lo
> contrario, el inventario no sería reconstruible desde este archivo (§34, *Integridad cuantitativa*).

---

## 7.7 Consumption

Representa el consumo histórico registrado.

Debe permitir asociar:

* producto;
* ubicación;
* fecha;
* cantidad;
* canal, cuando corresponda;
* indicador de afectación por stockout;
* origen del dato.

El consumo representa demanda satisfecha registrada.

Cuando exista un periodo de desabasto, la demanda real puede ser mayor que el consumo observado. Dichos periodos deberán poder identificarse mediante el indicador de censura correspondiente.

---

## 7.8 PurchaseOrder

Representa órdenes de compra.

Los estados contemplados son:

```text
DRAFT
ISSUED
PARTIALLY_RECEIVED
RECEIVED
CANCELLED
```

Las órdenes que se encuentren `ISSUED` o `PARTIALLY_RECEIVED` deben poder contribuir al inventario en tránsito.

Las órdenes canceladas o completamente recibidas no deben contribuir al tránsito pendiente.

---

## 7.9 PurchaseOrderItem

Representa los productos contenidos en una orden de compra.

Debe permitir almacenar:

* producto;
* cantidad ordenada;
* cantidad recibida;
* costo unitario;
* fecha esperada;
* proveedor mediante la orden correspondiente.

La cantidad pendiente debe poder obtenerse a partir de:

```text
cantidad pendiente = cantidad ordenada − cantidad recibida
```

---

## 7.10 PurchaseOrderReceipt

Representa las recepciones de las órdenes de compra.

Debe permitir registrar:

* orden de compra;
* fecha real de recepción;
* cantidad recibida;
* información necesaria para relacionarla con el producto correspondiente.

El histórico de recepciones es inmutable.

El lead time observado debe poder calcularse a partir de:

```text
lead time observado =
fecha de recepción − fecha de emisión de la orden
```

La generación debe incluir proveedores con distintos comportamientos para que esta métrica pueda evaluarse posteriormente.

---

## 7.11 InventoryPolicy

Representa las políticas aplicables al inventario.

La entidad debe poder representar políticas con diferentes ámbitos:

```text
PRODUCT
CATEGORY
GLOBAL
```

Sin embargo, los parámetros empresariales todavía pendientes no deben ser presentados como políticas reales de la organización.

Los campos deben quedar preparados para recibir posteriormente parámetros como:

* nivel de servicio;
* periodo de revisión;
* cobertura mínima;
* cobertura máxima;
* cobertura objetivo;
* vigencia.

---

# 8. Escenarios de demanda

El dataset debe incluir diferentes comportamientos de demanda.

Estos escenarios no representan categorías empresariales reales; son escenarios sintéticos diseñados para probar el motor predictivo.

## 8.1 Demanda estable

Productos cuya demanda presenta variación relativamente pequeña alrededor de un nivel.

Objetivo:

* comprobar que los modelos pueden capturar una serie regular;
* proporcionar un escenario adecuado para comparar contra el baseline.

---

## 8.2 Demanda creciente

Productos cuya demanda presenta una tendencia ascendente.

Objetivo:

* evaluar modelos capaces de capturar tendencia;
* comprobar que el baseline y los candidatos pueden distinguir crecimiento.

---

## 8.3 Demanda decreciente

Productos cuya demanda presenta una tendencia descendente.

Objetivo:

* evaluar riesgo de sobreinventario;
* comprobar que el sistema no mantiene indefinidamente una expectativa de demanda histórica alta.

---

## 8.4 Demanda estacional

Productos con patrones repetitivos a lo largo del tiempo.

La estacionalidad anual debe estar representada en algunos productos, considerando que el dataset tendrá suficiente historia para observar ciclos completos.

También pueden existir patrones estacionales de menor periodicidad cuando sean útiles para las pruebas.

---

## 8.5 Demanda intermitente

Productos con numerosos periodos de demanda cero y eventos de consumo separados.

Objetivo:

* probar métodos específicos para demanda intermitente;
* comprobar que una gran cantidad de ceros no sea interpretada automáticamente como ausencia de producto.

---

## 8.6 Demanda errática

Productos con variabilidad elevada y menor regularidad.

Objetivo:

* evaluar robustez de los modelos;
* comprobar la dispersión de los errores;
* evaluar posteriormente los intervalos de predicción.

---

# 9. Escenarios de stockout y demanda censurada

El dataset debe contener periodos donde el inventario disponible sea insuficiente para satisfacer completamente la demanda.

Estos periodos deben poder identificarse mediante los datos disponibles.

El consumo registrado durante un stockout no debe interpretarse automáticamente como demanda real completa.

Debe existir información suficiente para marcar el periodo como afectado:

```text
is_stockout_affected = true
```

cuando corresponda.

Esto permitirá posteriormente probar las alternativas de tratamiento de demanda censurada definidas en `docs/05-motor-predictivo.md`.

El dataset no debe asumir todavía cuál será el tratamiento definitivo de estos registros durante el entrenamiento.

**Quién produce qué (`DT-034`, 2026-09-23).** El dataset sintético conserva las **dos** series, y la
responsabilidad está repartida sin solapamiento:

```text
Componente 3 → demand.csv       demanda LATENTE    (lo que se habría demandado)
Componente 4 → consumption.csv  demanda SATISFECHA (lo que las existencias permitieron)
                                + is_stockout_affected
```

El Componente 3 no conoce las existencias, no simula desabastos y no escribe `consumption.csv`.
Tenerlas separadas es lo que convierte el sesgo por censura en una cantidad **medible** —la diferencia
entre ambas series— en lugar de una advertencia; y es lo que permitirá cerrar `DT-011` comparando los
cuatro tratamientos posibles contra la demanda real, que en este entorno sí se conoce.

---

# 10. Escenarios de inventario

El dataset debe permitir representar diferentes situaciones de inventario.

## 10.1 Inventario saludable

Existencias suficientes para cubrir la demanda esperada sin generar un exceso evidente.

## 10.2 Inventario bajo

Existencias cercanas a los niveles donde una reposición puede ser necesaria.

## 10.3 Riesgo de stockout

Productos donde la posición de inventario y la demanda proyectada permitan posteriormente detectar una posible falta de inventario.

## 10.4 Sobreinventario

Productos con existencias superiores a las necesidades esperadas.

Deben existir casos donde el sobreinventario pueda relacionarse con:

* demanda decreciente;
* baja rotación;
* exceso de cobertura;
* compras superiores a la necesidad.

## 10.5 Inventario en tránsito

Deben existir productos con órdenes de compra pendientes.

El dataset debe distinguir entre:

```text
tránsito total
```

y la parte del tránsito que posteriormente pueda determinarse como:

```text
tránsito efectivo
```

El tránsito efectivo **no se almacena como una propiedad histórica independiente del inventario**. Debe poder derivarse posteriormente según el criterio de decisión utilizado por el motor de abastecimiento.

---

# 11. Escenario crítico: tránsito total frente a tránsito efectivo

El dataset debe incluir explícitamente al menos un escenario donde:

```text
tránsito total > necesidad inmediata
```

pero:

```text
tránsito efectivo < necesidad dentro del intervalo de protección
```

Este escenario es obligatorio porque permite verificar la diferencia entre:

```text
IP_contable =
existencia + tránsito total − comprometido
```

y:

```text
IP_decisión =
existencia + tránsito efectivo − comprometido
```

El objetivo es evitar que el sistema concluya que no necesita reposición únicamente porque existe una orden pendiente que llegará demasiado tarde para cubrir el periodo relevante.

La determinación exacta del tránsito efectivo depende del criterio de corte pendiente `DT-P11`.

Por tanto, el dataset debe proporcionar las fechas necesarias para que dicho cálculo pueda realizarse posteriormente, sin fijar todavía el criterio empresarial definitivo.

---

# 12. Escenarios de proveedores

El dataset debe representar diferentes comportamientos.

## 12.1 Proveedor confiable

Características sintéticas:

* lead times observados cercanos al comportamiento esperado;
* pocas desviaciones;
* entregas completas.

## 12.2 Proveedor con retrasos

Debe presentar recepciones posteriores a las fechas esperadas o al lead time acordado.

Objetivo:

* calcular lead time observado;
* medir desviación;
* evaluar variabilidad.

## 12.3 Proveedor con entregas parciales

Debe existir al menos un caso donde:

```text
cantidad recibida < cantidad ordenada
```

en una recepción o conjunto de recepciones parciales.

Esto permite probar la relación:

```text
cantidad ordenada
cantidad recibida
cantidad pendiente
```

La tolerancia definitiva para sobre-recepción continúa pendiente mediante `BR-X08`.

Por ello, el dataset no debe establecer una política empresarial sobre cuánto exceso puede recibirse.

---

# 13. Lead time

El dataset debe permitir distinguir:

```text
lead time acordado
```

de:

```text
lead time observado
```

El lead time observado debe poder calcularse a partir de las órdenes y recepciones.

Debe existir variación suficiente entre proveedores y entre órdenes para permitir posteriormente calcular:

* promedio;
* desviación;
* desviación respecto al acordado;
* porcentaje de entregas puntuales.

El uso del lead time observado para las decisiones está definido actualmente como `BR-P01`, por lo que permanece como regla propuesta y no confirmada.

---

# 14. Órdenes de compra y tránsito

El dataset debe incluir órdenes:

* completamente recibidas;
* parcialmente recibidas;
* pendientes;
* canceladas;
* con diferentes fechas esperadas;
* con diferentes lead times observados.

Las órdenes pendientes deben permitir reconstruir el inventario total en tránsito.

Debe ser posible determinar qué cantidades todavía no han sido recibidas.

No se debe generar tránsito artificial independiente de las órdenes de compra.

El tránsito debe derivarse de hechos de compras coherentes.

---

# 15. Comprometido / reservado

El modelo conceptual contempla `quantity_reserved`.

Sin embargo, actualmente no existe una fuente confirmada de ventas, reservas o compromisos que permita construir este dato de forma realista.

Por tanto, durante la primera versión del dataset:

* el campo puede mantenerse disponible en el esquema;
* no se debe inventar un proceso de reservas;
* cuando sea necesario para una simulación, su tratamiento deberá quedar explícitamente documentado;
* no debe presentarse como información empresarial real.

La hipótesis vigente establece inicialmente este valor en cero mientras no exista una fuente de reservas validada.

---

# 16. MOQ y múltiplos de compra

El dataset debe contener productos/proveedores con diferentes restricciones comerciales.

Debe poder representar:

* productos sin MOQ significativo;
* productos con MOQ;
* productos con múltiplo de compra;
* productos donde el MOQ sea superior a la necesidad calculada;
* productos donde el múltiplo obligue a redondear la cantidad.

Estos escenarios permiten posteriormente comprobar la separación entre:

```text
cantidad bruta necesaria
```

y:

```text
cantidad final ajustada
```

La aplicación definitiva de las restricciones corresponde al motor de abastecimiento y no al generador de datos.

---

# 17. Conflicto MOQ / sobreinventario

Debe existir al menos un escenario donde el MOQ o múltiplo de compra obligue a adquirir una cantidad superior a la necesidad inmediata.

El dataset debe proporcionar los datos suficientes para que posteriormente el motor pueda identificar:

```text
necesidad real
```

frente a:

```text
cantidad obligatoria por restricción comercial
```

La clasificación del resultado como sobreinventario dependerá de las políticas y umbrales empresariales, que permanecen pendientes.

---

# 18. Productos activos e inactivos

El dataset debe conservar histórico de productos que posteriormente puedan clasificarse como inactivos.

Un producto inactivo debe conservar su información histórica.

El escenario permitirá comprobar que un producto inactivo puede conservar:

* consumo histórico;
* movimientos;
* compras;
* recepciones;

sin generar necesariamente nuevas predicciones o recomendaciones.

El tratamiento definitivo de productos descontinuados permanece como regla propuesta `BR-P10`.

---

# 19. Datos sintéticos y trazabilidad

Todo registro generado durante esta etapa debe poder identificarse como sintético.

El valor esperado de origen será:

```text
SYNTHETIC
```

La trazabilidad debe permitir identificar, cuando corresponda:

* carga;
* registro;
* fecha de generación;
* semilla utilizada;
* versión del generador;
* escenario sintético asociado.

La información adicional de generación no debe confundirse con información empresarial.

Por esa razón, esa información **no se almacena en las entidades de negocio**. Se registra en un
archivo aparte, `manifest.json`, cuyo contrato define la sección §42 (`DT-025`). En particular, **no
existe un campo `scenario` en `Product`, `Supplier`, `Category`, `ProductSupplier` ni `Location`**: la
cobertura de escenarios configurada queda registrada en el manifiesto, y la asignación de escenarios
a registros concretos corresponde al componente de asignación (`DT-023`).

Lo que sí viaja con cada registro es la marca de origen `data_origin` (§7, §34, `DT-026`), que es un
dato del registro y no metadata de generación.

---

# 20. Coherencia temporal

El dataset debe respetar reglas temporales mínimas.

### Productos

Las fechas de vigencia deben ser compatibles con los eventos asociados.

### Órdenes

Una orden debe emitirse antes de su recepción.

### Recepciones

Una recepción no puede ocurrir antes de la emisión de la orden.

### Inventario

Los movimientos deben ocurrir en fechas que permitan reconstruir la existencia histórica.

### Consumo

El consumo debe ocurrir dentro del periodo de existencia del producto y ubicación correspondiente.

### Lead time

El lead time observado no puede ser negativo.

### Predicción

Los datos utilizados como entrada de una predicción deben corresponder únicamente a información disponible hasta su `as_of_date`.

Esta última condición será fundamental para evitar leakage durante la Etapa 5.

---

# 21. Coherencia de cantidades

Las cantidades deben utilizar unidades coherentes.

Debe evitarse mezclar unidades de medida incompatibles sin una conversión explícitamente definida.

Como mínimo deben comprobarse posteriormente:

```text
cantidad != 0
```

para movimientos cuando así lo exige el modelo conceptual.

Para órdenes:

```text
cantidad ordenada >= 0
```

Para recepciones:

```text
cantidad recibida >= 0
```

Y, salvo que exista un escenario explícito de sobre-recepción:

```text
cantidad recibida <= cantidad ordenada
```

La tolerancia empresarial de sobre-recepción permanece pendiente mediante `BR-X08`.

---

# 22. Reconstrucción del inventario

El dataset debe permitir reconstruir el inventario histórico a partir de los movimientos.

La existencia en una fecha determinada debe poder explicarse mediante los movimientos ocurridos hasta ese momento.

El estado calculado de inventario no debe convertirse en la única fuente de verdad.

Esto permitirá posteriormente comprobar la consistencia entre:

```text
histórico de movimientos
```

y:

```text
estado de inventario mantenido
```

El modelo conceptual establece que `Inventory` es un estado calculado/mantenido para rendimiento y que debe ser reconciliable con el histórico.

---

# 23. Reconstrucción del inventario en tránsito

El tránsito total debe poder reconstruirse a partir de las órdenes de compra y sus recepciones.

Conceptualmente:

```text
IT_total =
órdenes emitidas no recibidas completamente
```

considerando únicamente las cantidades pendientes.

No debe existir un campo generado arbitrariamente que contradiga las órdenes.

---

# 24. Reconstrucción del desempeño de proveedores

El dataset debe permitir calcular posteriormente indicadores como:

* número de órdenes;
* lead time promedio observado;
* desviación del lead time;
* variabilidad del lead time;
* porcentaje de entregas puntuales;
* cumplimiento de cantidad.

El cumplimiento de cantidad del proveedor no debe confundirse con el fill rate de demanda.

---

# 25. Escenarios mínimos obligatorios

La primera versión del dataset debe contener como mínimo los siguientes escenarios:

| Escenario                                         | Obligatorio |
| ------------------------------------------------- | ----------: |
| Demanda estable                                   |          Sí |
| Demanda creciente                                 |          Sí |
| Demanda decreciente                               |          Sí |
| Demanda estacional                                |          Sí |
| Demanda intermitente                              |          Sí |
| Demanda errática                                  |          Sí |
| Stockout                                          |          Sí |
| Demanda censurada                                 |          Sí |
| Inventario bajo                                   |          Sí |
| Sobreinventario                                   |          Sí |
| Inventario en tránsito                            |          Sí |
| Tránsito total suficiente / efectivo insuficiente |          Sí |
| Proveedor confiable                               |          Sí |
| Proveedor con retrasos                            |          Sí |
| Entregas parciales                                |          Sí |
| MOQ                                               |          Sí |
| Múltiplo de compra                                |          Sí |
| Conflicto MOQ / sobreinventario                   |          Sí |
| Producto activo                                   |          Sí |
| Producto inactivo con histórico                   |          Sí |
| Múltiples proveedores                             |          Sí |
| Proveedor preferente                              |          Sí |
| Órdenes pendientes                                |          Sí |
| Órdenes recibidas                                 |          Sí |
| Órdenes parcialmente recibidas                    |          Sí |
| Corrección mediante nuevo movimiento              |          Sí |

---

# 26. Casos límite para pruebas posteriores

El dataset debe proporcionar datos suficientes para construir pruebas sobre situaciones como:

* demanda cero;
* inventario cero;
* lead time cero cuando sea necesario para pruebas técnicas;
* variabilidad de demanda cero;
* variabilidad de lead time cero;
* tránsito efectivo superior al punto de reorden;
* tránsito total superior al punto de reorden pero tránsito efectivo insuficiente;
* lead time que no sea múltiplo de siete días;
* MOQ superior a la necesidad;
* múltiplo de compra grande;
* producto sin proveedor activo;
* producto sin forecast disponible;
* producto inactivo;
* inventario negativo, únicamente si posteriormente se confirma que debe permitirse;
* falta de parámetros de política.

Los casos que dependan de una regla empresarial aún no definida no deben utilizarse para afirmar que dicha regla ya está establecida.

---

# 27. Parámetros de política pendientes

El dataset debe permanecer preparado para recibir posteriormente los siguientes parámetros:

* nivel de servicio;
* definición del nivel de servicio;
* política de revisión;
* frecuencia de revisión;
* cobertura objetivo;
* umbrales de riesgo;
* umbrales de sobreinventario;
* costos de faltante;
* costos de mantenimiento;
* criterio de selección de proveedores;
* calendario laboral;
* diferenciación de políticas por segmento;
* tolerancia de sobre-recepción;
* inventario negativo;
* productos sustitutos;
* restricciones presupuestarias;
* restricciones de capacidad;
* horizonte de aprobación;
* horizonte de cobertura.

Estos elementos están registrados en `knowledge/business-rules.md` como reglas pendientes.

El dataset no debe convertir ninguno de ellos en una política empresarial confirmada.

---

# 28. Segmentación para Machine Learning

El dataset debe permitir posteriormente segmentar productos según comportamiento de demanda.

Las categorías conceptuales definidas en `docs/05-motor-predictivo.md` son:

```text
Regular
Seasonal
Intermittent
Erratic
New / short history
Discontinued
```

Los umbrales cuantitativos para asignar automáticamente estas categorías todavía deben calibrarse con datos.

Por ello, la especificación exige la presencia de comportamientos representativos, pero no fija todavía umbrales numéricos definitivos.

---

# 29. Prevención de leakage

El dataset debe conservar suficiente información temporal para permitir posteriormente validaciones de leakage.

Para cualquier fecha `t`, las características utilizadas para predecir una demanda futura deben construirse únicamente con información disponible hasta `t`.

No debe utilizarse información futura accidentalmente mediante:

* ventanas no desplazadas;
* agregaciones calculadas con todo el histórico;
* variables derivadas de recepciones futuras;
* información de inventario posterior al `as_of_date`;
* información de consumo posterior al periodo de predicción.

El generador debe producir datos que permitan verificar esta propiedad posteriormente.

---

# 30. Dataset y baseline

El dataset debe permitir evaluar los modelos predictivos contra baselines.

Como mínimo, debe proporcionar suficiente historia para implementar posteriormente:

* Naïve;
* Seasonal Naïve;
* Moving Average;
* Simple Exponential Smoothing.

El dataset no debe diseñarse para favorecer artificialmente a un modelo concreto.

Los patrones de demanda deben ser suficientemente variados para que diferentes estrategias puedan comportarse de manera distinta.

---

# 31. Dataset y evaluación de Nivel 2

El dataset debe permitir posteriormente realizar simulaciones retrospectivas del impacto de diferentes forecasts sobre decisiones de abastecimiento.

Debe ser posible utilizar el mismo:

* histórico;
* inventario;
* órdenes;
* recepciones;
* proveedores;
* restricciones;
* reglas del motor;

para comparar:

```text
baseline
vs.
modelo ML
```

La comparación deberá utilizar el mismo motor de abastecimiento y las mismas condiciones de evaluación.

Los datos sintéticos no deben utilizarse para afirmar rendimiento real de la organización.

---

# 32. Configuración del generador

El futuro generador deberá utilizar parámetros explícitos.

Como mínimo, deberá permitir controlar:

* semilla;
* horizonte temporal;
* número de productos;
* número de categorías;
* número de proveedores;
* número de ubicaciones;
* proporción de productos por comportamiento de demanda;
* escenarios de proveedores;
* escenarios de stockout;
* escenarios de inventario;
* escenarios de compras;
* intensidad de estacionalidad;
* intensidad de tendencia;
* variabilidad;
* frecuencia de eventos intermitentes.

Los parámetros concretos se definirán al implementar el generador y deberán documentarse cuando constituyan una decisión técnica relevante.

No deben confundirse con parámetros de negocio.

---

# 33. Versionado y reproducibilidad

El dataset generado debe poder identificarse mediante información suficiente para reproducirlo.

Como mínimo se recomienda conservar:

```text
dataset_version
generator_version
seed
generated_at
time_range
```

La información debe permitir determinar con qué configuración fue generado un conjunto de datos utilizado durante una prueba o experimento.

Esta información se materializa en `manifest.json`, un archivo por directorio de salida, cuyo
contrato completo está en §42 (`DT-025`).

---

# 34. Validaciones de calidad

El proceso de ingestión/validación deberá comprobar posteriormente, como mínimo:

### Integridad referencial

* todos los productos referenciados existen;
* todas las categorías referenciadas existen;
* todos los proveedores referenciados existen;
* todas las ubicaciones referenciadas existen;
* todas las relaciones producto-proveedor son válidas;
* todas las órdenes tienen productos/proveedores válidos;
* todas las recepciones pertenecen a órdenes existentes.

### Integridad temporal

* las fechas mantienen un orden lógico;
* no existen recepciones antes de la emisión de una orden;
* los lead times observados son calculables;
* los eventos se encuentran dentro de la vigencia correspondiente;
* todo producto tiene `valid_from`, y `valid_to` es nulo o igual o posterior a `valid_from` (`DT-027`);
* el consumo, los movimientos y las líneas de orden de un producto caen dentro de su intervalo de
  vigencia `[valid_from, valid_to]`, **ambos extremos incluidos** (`DT-027`); con `valid_to` nulo, el
  intervalo es abierto por la derecha. **Única excepción** (enmienda de `DT-027` del 2026-09-24): una
  orden emitida dentro de la vigencia completa su ciclo causal, de modo que sus recepciones y los
  movimientos `RECEIPT` derivados de ellas pueden ocurrir **después** de `valid_to`, conservando la
  trazabilidad con la orden. Esa recepción **no** se cancela, **no** se elimina, **no** se trunca,
  **no** se convierte en `ADJUSTMENT`, y conserva el `reference_type` y el `reference_id`
  correspondientes a su origen. La excepción **no** admite, después de `valid_to`: demanda · consumo ·
  órdenes nuevas · nuevas relaciones con proveedores · ningún otro movimiento arbitrario.

### Integridad cuantitativa

* no existen cantidades inválidas;
* las unidades son coherentes;
* las cantidades recibidas son compatibles con las órdenes;
* el tránsito puede reconstruirse;
* el inventario puede reconstruirse.

### Integridad de origen

Todos los registros sintéticos deben identificarse correctamente como:

```text
SYNTHETIC
```

Esto incluye las cinco entidades maestras (`DT-026`) y, desde el 2026-09-24, `Inventory`,
`PurchaseOrder`, `PurchaseOrderItem` y `PurchaseOrderReceipt`, que hasta entonces no listaban el
campo pese a ser entidades cargadas (pendiente registrado en `DT-026`, cerrado antes de autorizar los
Componentes 4 y 5). El criterio es el de `DT-026`: **lleva `data_origin` la entidad que se carga como
histórico y que RF-023 sustituirá por datos reales**; no lo llevan las salidas calculadas del sistema
—`Forecast`, `RiskAssessment`, `Recommendation`, `SupplierPerformance`, `ModelVersion`— ni
`InventoryPolicy`, que ningún componente del generador escribe. Adicionalmente:

* existe un `manifest.json` en el directorio de salida y su campo `data_origin` es `SYNTHETIC`;
* el `sha256` de cada archivo listado en `manifest.json` coincide con el archivo presente, de modo que
  el directorio no mezcla ejecuciones distintas (§41, §42).

### Integridad de formato

* cada archivo CSV tiene la cabecera y el orden de columnas de su contrato de entidad (`DT-024` para
  las cinco entidades maestras, `DT-034` para `demand.csv`, `DT-038` para los tres archivos del
  Componente 4 y `DT-039` para los tres del Componente 5; los Componentes 7 y 8 **no escriben
  ningún CSV**: aportan `scenario_assignment` y `quality_report` al manifiesto, `DT-041` y `DT-042`);
* los valores nulos se representan como campo vacío, no como la cadena `NULL`;
* las fechas siguen `YYYY-MM-DD` y las fechas con hora, ISO-8601 UTC;
* los booleanos son `true` / `false` en minúscula;
* los importes llevan exactamente dos decimales con punto como separador.

### Integridad predictiva

Debe ser posible construir series temporales sin utilizar información futura.

---

# 35. Reporte de calidad

Al finalizar la generación del dataset debe producirse un reporte de calidad.

El reporte debe incluir, como mínimo:

* versión del dataset;
* versión del generador;
* semilla;
* periodo cubierto;
* número de registros por entidad;
* número de productos;
* número de proveedores;
* número de categorías;
* número de ubicaciones;
* distribución de escenarios;
* cantidad de productos por patrón de demanda;
* cantidad de periodos afectados por stockout;
* cantidad de órdenes;
* cantidad de recepciones;
* distribución de lead times;
* validaciones ejecutadas;
* validaciones aprobadas;
* validaciones fallidas;
* anomalías detectadas;
* limitaciones conocidas.

El reporte no debe presentar los resultados sintéticos como métricas reales del negocio.

**Materialización (`DT-042`, 2026-09-29).** El reporte lo produce el Componente 8 como campo
`quality_report` de `manifest.json`, **solo** cuando todas sus comprobaciones pasan. Contiene los
veinte ítems anteriores, en ese orden, con tipos deterministas y sin números de coma flotante.
«Validaciones ejecutadas, aprobadas y fallidas» son las 51 comprobaciones del catálogo de `DT-042`
§4, incluidas la cobertura de `scenarios.required` y las cuatro situaciones de nivel C.
«Anomalías detectadas» es siempre `[]` en esta versión, con la limitación declarada: no existe un
criterio contractual de anomalía, y una lista vacía no significa que el dataset se haya revisado con
una taxonomía inexistente. La distribución de lead times es una tabla de frecuencias `{días: número}`
del acordado y del observado (`V1-09`), y los periodos afectados por desabasto se cuentan como
días-par con `is_stockout_affected = true` (decisión C7/C8-14).

---

# 36. Criterios de aceptación de la especificación

La especificación se considera completa cuando:

1. Todas las entidades necesarias para Etapa 1 están identificadas.
2. Los escenarios mínimos obligatorios están definidos.
3. Las relaciones entre entidades pueden representarse de manera coherente.
4. El dataset puede soportar reconstrucción histórica.
5. El dataset puede soportar cálculo posterior de inventario en tránsito.
6. El dataset puede soportar cálculo posterior de lead time observado.
7. Existen escenarios de stockout y demanda censurada.
8. Existe un escenario que permita distinguir tránsito total de tránsito efectivo.
9. Existen escenarios con MOQ y múltiplos.
10. Existen proveedores con comportamientos diferenciados.
11. Existe suficiente historia para los experimentos de forecasting definidos.
12. El origen sintético puede identificarse.
13. La generación puede reproducirse mediante semilla.
14. Las validaciones de calidad están definidas.
15. Las políticas empresariales pendientes no se convierten en requisitos inventados.
16. El dataset puede sustituirse posteriormente por datos reales sin cambiar las reglas de negocio.

---

# 37. Elementos explícitamente fuera del alcance

Esta especificación no define:

* políticas empresariales reales;
* niveles de servicio reales;
* costos reales;
* criterios reales de selección de proveedores;
* fórmulas definitivas de stock de seguridad;
* umbrales definitivos de riesgo;
* modelo predictivo definitivo;
* modelo de Machine Learning específico;
* arquitectura de Azure;
* infraestructura de producción;
* API;
* interfaz gráfica;
* automatización de órdenes de compra.

Tampoco define todavía cómo se implementará técnicamente el generador.

---

# 38. Dependencias documentales

Esta especificación debe interpretarse conjuntamente con:

* `docs/04-modelo-datos.md`
* `docs/05-motor-predictivo.md`
* `docs/06-motor-abastecimiento.md`
* `docs/15-decisiones-tecnicas.md`
* `docs/decisions/` — en particular `DT-023`, `DT-024`, `DT-025`, `DT-027`, `DT-028` y `DT-030`, en los
  que §§41 a 44 delegan su contenido normativo
* `knowledge/glossary.md`
* `knowledge/assumptions.md`
* `knowledge/business-rules.md`
* `project/roadmap.md`
* `AGENTS.md`

Cuando exista una contradicción entre documentos, no debe resolverse unilateralmente.

La contradicción debe registrarse y solicitarse validación conforme al protocolo de `AGENTS.md`.

---

# 39. Estado del documento

Este documento define la **especificación del dataset sintético**, no el dataset generado.

Por tanto:

```text
Especificado   = Sí
Implementado   = Sí   (Componentes 1 a 8 y W1, 2026-09-29)
Generado       = Sí   (ds-6c8ad65b4999, generator_version 0.4.0)
Validado       = Sí   (Componente 8: 51 de 51 comprobaciones, quality_report sin fallos)
```

*Actualización del 2026-09-29.* Esta sección decía «Implementado = No, Generado = No, Validado =
No». El generador está completo y el dataset publicado en `data/synthetic/output/` ha superado la
validación del Componente 8 (`DT-042`); su informe de calidad vive en `manifest.quality_report`.
«Validado» se refiere a esta especificación y a los contratos del generador, **no** a ninguna regla
de negocio: los criterios `SYNTHETIC_COVERAGE_CRITERION` no cierran `BR-X03`, `DT-P11`, `BR-P10`
ni `DT-011`.

---

## 40. Próximo paso

El siguiente paso de Etapa 1 es diseñar e implementar el generador de datos sintéticos conforme a esta especificación.

Antes de implementarlo deberán definirse los siguientes elementos. Su estado a 2026-09-18 es:

| # | Elemento | Estado | Dónde |
|---|---|---|---|
| 1 | estructura física de los archivos generados | ✅ **Definido** | §41 (`DT-024`) |
| 2 | formato de intercambio | ✅ **Definido** | §41 (`DT-024`) |
| 3 | configuración del generador | 🟡 **Parcial** | Componente 1 (`DatasetConfig`) cubre semilla, horizonte y escala. Los parámetros de §32 relativos a proporciones e intensidades de demanda **siguen sin definirse** y corresponden a los componentes de demanda y de asignación de escenarios |
| 4 | semilla reproducible | ✅ **Definido** | Componente 1 + §44 (`DT-030`) |
| 5 | estrategia de generación de entidades maestras | ✅ **Definida** | §43 (`DT-028`) |
| 6 | estrategia de generación de series temporales | ⬜ Pendiente | Componente de demanda |
| 7 | estrategia para crear órdenes y recepciones causalmente coherentes | ⬜ Pendiente | Componentes de órdenes y de comportamiento de proveedores |
| 8 | estrategia para introducir los escenarios obligatorios | ✅ **Definida** (2026-09-29) | `DT-023` reparte las 26 situaciones en tres niveles; `DT-041` registra los 16 ejes en `manifest.scenario_assignment` |
| 9 | validaciones automáticas | ✅ **Implementadas** (2026-09-29) | Componente 8, 51 comprobaciones (`DT-042` §4) |
| 10 | reporte de calidad | ✅ **Implementado** (2026-09-29) | `manifest.quality_report` (`DT-042` §5) |

Los elementos 1, 2, 4 y 5 son los que condicionaban la implementación de las **entidades maestras**.
Con ellos definidos, esa parte del generador puede implementarse; los elementos 6, 7 y 10 condicionan
componentes posteriores.

La implementación debe comenzar por el camino más simple que permita satisfacer los criterios de aceptación de Etapa 1.

No deben introducirse dependencias, servicios o infraestructura adicionales sin justificación y autorización cuando corresponda.

---

# 41. Formato de salida del dataset

*Añadido en la revisión 1.1. Cierra el elemento 1 y el elemento 2 de §40. Decisión: `DT-024`.*

## 41.1 Un archivo CSV por entidad

El dataset se materializa como **un archivo CSV independiente por entidad**, más un `manifest.json`
con la metadata de generación (§42).

```text
<directorio de salida>/
├── manifest.json
├── categories.csv
├── products.csv
├── suppliers.csv
├── product_suppliers.csv
└── locations.csv
```

Los nombres de archivo se escriben en plural y en `snake_case`, derivados del nombre de la entidad.
Los componentes posteriores añaden sus propios CSV al mismo directorio, con las mismas convenciones.

**JSON no es el formato de los datos de las entidades.** Se usa exclusivamente para el manifiesto,
que no es una entidad.

El directorio de salida **no se versiona**: `CLAUDE.md` §13.7 establece que los datasets no van al
repositorio.

## 41.2 Convenciones de formato

Sin estas convenciones, «CSV» no es un contrato. Son de obligado cumplimiento para todos los archivos
de datos del dataset.

| Aspecto | Valor |
|---|---|
| Codificación | UTF-8, sin BOM |
| Separador de campo | `,` |
| Entrecomillado | RFC 4180, mínimo; la comilla interna se duplica |
| Fin de línea | `\n` (LF) |
| Cabecera | Obligatoria, primera línea |
| Nombres de columna | Los atributos de `docs/04-modelo-datos.md`, en `snake_case` e inglés (`DT-017`) |
| Orden de columnas | Fijo, el del contrato de cada entidad |
| Nulos | Campo vacío. Nunca `NULL`, `None`, `NaN` ni `-` |
| Fechas | `YYYY-MM-DD` |
| Fechas con hora | ISO-8601 UTC, `YYYY-MM-DDTHH:MM:SSZ` |
| Booleanos | `true` / `false` en minúscula |
| Decimales | Punto decimal; los importes con exactamente dos decimales |
| Orden de filas | Ascendente por clave |

## 41.3 Coherencia del conjunto

Los archivos de un directorio de salida provienen de **una sola ejecución del generador** y son
coherentes entre sí. Un directorio que mezcle archivos de ejecuciones distintas no es un dataset
válido, y `manifest.json` permite detectarlo mediante el `sha256` de cada archivo (§42).

Esto no contradice que los componentes posteriores «añadan» sus archivos: **cada ejecución regenera el
directorio completo**, con los componentes que estén implementados en ese momento. «Añadir» describe
qué archivos produce un componente nuevo, no una acumulación incremental sobre una salida anterior.
Un dataset generado con los Componentes 2 y 3 sustituye por completo a uno generado solo con el 2.

**Generado no es publicado** (`DT-040`, 2026-09-26). Cada ejecución escribe primero en su propio
workspace, `data/synthetic/tmp/<id_de_ejecución>/`, y el directorio de salida solo cambia cuando la
ejecución **completa** ha terminado bien y el workspace se **promociona** en bloque. Una ejecución
fallida —por cualquier componente, incluida la regla B2 del Componente 5— no publica nada y deja
intacto el dataset válido anterior. Así la sustitución completa que describe el párrafo anterior es
también **atómica**: el directorio de salida nunca contiene una ejecución a medias ni archivos de dos
ejecuciones.

El contrato de columnas de las cinco entidades maestras está en `DT-024`; el de `demand.csv` en
`DT-034`; el de `consumption.csv`, `inventory_movements.csv` e `inventory.csv` en **`DT-038`**; y el
de `purchase_orders.csv`, `purchase_order_items.csv` y `purchase_order_receipts.csv` en **`DT-039`**
(ambos del 2026-09-24). Los Componentes 7 y 8 **no escriben ningún CSV**: aportan dos campos al
manifiesto (`DT-041`, `DT-042`).

`DT-038` y `DT-039` **no heredan** de `DT-024` las reglas de identificador y de orden de filas: las
reescriben explícitamente para cada entidad nueva, con su clave de negocio y su desempate, porque la
regla «`id` secuencial tras ordenar por la clave de negocio» no tiene a qué referirse mientras esa
clave no esté declarada.

**Archivos escritos hasta ahora**, por el componente que los produce:

| Componente | Archivos |
|---|---|
| 2 — Catalog Generator | `categories.csv`, `products.csv`, `suppliers.csv`, `product_suppliers.csv`, `locations.csv`, `manifest.json` |
| 3 — Demand Generator | `demand.csv` — **demanda latente** (`DT-034`); extiende el manifiesto |
| 6 — Supplier Behaviour Generator | **Ninguno.** Entrega perfiles en memoria al Componente 4 y figura en `manifest.components` con cero archivos (`DT-037` §1). Implementado (2026-09-28); se ejecuta a través de W1 (2026-09-29) |
| 4 — Inventory Simulator | `consumption.csv` — **demanda satisfecha** —, `inventory.csv` (snapshot final), `inventory_movements.csv` (fuente de verdad histórica). Calcula además las órdenes **causales** y sus recepciones, y les asigna los identificadores, pero no las escribe (`DT-036`, `DT-038`). Implementado (2026-09-26); publicado a través de W1 (2026-09-29) |
| 5 — Purchase Order Generator | `purchase_orders.csv`, `purchase_order_items.csv`, `purchase_order_receipts.csv` — materializa lo que el Componente 4 calculó, sin recalcular nada; añade las órdenes `CANCELLED` sintéticas y numera solo esas filas; forma el `order_number` de todas las órdenes (`DT-039`). Implementado (2026-09-28); publicado a través de W1 (2026-09-29) |
| 7 — Scenario Assignment | **Ninguno.** Añade `scenario_assignment` al manifiesto (`DT-041`). Integrado en W1 (2026-09-29) |
| 8 — Dataset Validator + informe de calidad | **Ninguno.** Valida el workspace y, solo si todo pasa, añade `quality_report` al manifiesto (`DT-042`). Integrado en W1 (2026-09-29) |

> El orden de ejecución aprobado es **C2 → C3 → C6 → C4 → C5 → C7 → C8 → verify → promote**; el
> tramo C6 → C4 → C5 es distinto del orden de numeración. La sub-semilla
> de cada componente deriva de su identificador canónico y no de su posición, de modo que el orden de
> ejecución no altera ningún dato (§44, `DT-030`).

---

# 42. Metadata de generación: `manifest.json`

*Añadido en la revisión 1.1. Complementa §19 y §33. Decisión: `DT-025`.*

## 42.1 Principio

La metadata de generación **no se almacena en las entidades de negocio**, por exigencia de §19: «La
información adicional de generación no debe confundirse con información empresarial».

Se escribe en un **único archivo `manifest.json`** por directorio de salida.

En particular, **ninguna entidad lleva un campo `scenario`**. La cobertura de escenarios configurada
se registra en el manifiesto; la asignación de escenarios a registros concretos corresponde al
componente de asignación de escenarios (`DT-023`).

## 42.2 Campos obligatorios

| Campo | Contenido | Exigido por |
|---|---|---|
| `dataset_version` | Versión del dataset producido | §33 |
| `generator_version` | Versión del generador que lo produjo | §19, §33 |
| `seed` | La semilla, copiada literalmente de la configuración | §3.3, §19, §33 |
| `generated_at` | Instante de generación, ISO-8601 UTC | §19, §33 |
| `time_range` | `start_date` y `end_date` del periodo generado | §33 |
| `data_origin` | `SYNTHETIC` a nivel de dataset | §19, §34 |
| `config` | La configuración completa y normalizada, incluida la lista de escenarios requeridos | §19, §33 |
| `components` | Un registro por componente que contribuyó: nombre, versión y sub-semilla (§44) | §19 |
| `files` | Un registro por archivo escrito: nombre, entidad, número de filas y `sha256` | §33, §35 |

## 42.3 Campos aportados por componentes posteriores

| Campo | Lo aporta | Estado |
|---|---|---|
| `scenario_assignment` | Componente 7 | **Definido** (2026-09-29): campo del manifiesto, 16 ejes × seis campos (`DT-041` §4) |
| `quality_report` | Componente 8 | **Definido** (2026-09-29): campo del manifiesto, no un archivo aparte; los veinte ítems de §35 (`DT-042` §5) |

Un manifiesto que no los contenga no es inválido: el contrato los declara como aportados más tarde.
Desde `generator_version` **0.4.0** (2026-09-29) ambos se aportan en cada ejecución completa, y W1
exige los dos —con `quality_report` sin fallos— antes de publicar (`DT-042` §8).

## 42.4 Reproducibilidad

Dos ejecuciones con la misma configuración, la misma semilla y **la misma versión del generador**
producen archivos de datos idénticos. El manifiesto, en cambio, tiene campos que no son reproducibles
y que toda comprobación debe excluir: `generated_at`, y los que dependen del conjunto de componentes
ejecutados (`files`, `components`, `generator_version`). El invariante completo está en §44.

El contrato completo del manifiesto está en `DT-025`.

---

# 43. Políticas de generación sintética de entidades maestras

*Añadido en la revisión 1.1. Cierra el elemento 5 de §40. Decisión: `DT-028`.*

## 43.1 Naturaleza de estos valores

Generar las entidades maestras exige escribir valores para los que esta especificación no define
rango ni regla: `moq`, `order_multiple`, `unit_cost`, `agreed_lead_time_days`, el número de
proveedores por producto, el reparto de productos entre categorías y la proporción de productos
activos e inactivos.

Estos valores se fijan como **parámetros de generación sintética**, al amparo de §3.5:

> «Cuando sea necesario utilizar valores para construir escenarios técnicos, estos deben
> identificarse explícitamente como valores sintéticos de prueba y no como políticas de la
> organización.»

**Esta sección es esa identificación explícita.** Ninguno de esos valores es una política
empresarial, un costo real, un plazo acordado ni una restricción comercial de la organización. Los
parámetros empresariales reales siguen pendientes en `knowledge/business-rules.md` §3 y **ninguno se
fija aquí**.

## 43.2 Qué cubren

`DT-028` define seis políticas, todas deterministas a partir de la semilla:

| Política | Qué exigencia de esta especificación satisface |
|---|---|
| Valores comerciales de `ProductSupplier` | §16 (con y sin MOQ, con múltiplo), §13 (variación de lead time), §26 (múltiplo grande, lead time no múltiplo de siete) |
| Asignación producto ↔ proveedor | §7.4 (uno o varios proveedores), §25 (múltiples proveedores, proveedor preferente), §26 (producto sin proveedor activo) |
| Distribución ponderada de productos por categoría | §7.1, sin asumir un reparto uniforme que ninguna fuente establece |
| Nomenclatura sintética neutra | §19 (el dato sintético debe reconocerse como tal), §8 («no representan categorías empresariales reales») |
| Vocabulario de unidad de medida | §7.2, §21 (coherencia de unidades) |
| Vocabulario de tipo de ubicación | §6, §7.5 (una ubicación operativa principal) |

## 43.3 «Producto sin proveedor activo» — forma canónica

§26 pide poder construir pruebas sobre un «producto sin proveedor activo». El modelo admite varias
materializaciones; se adopta **una sola**, para que la validación sea comprobable:

> El producto tiene al menos una relación `ProductSupplier`, y **todas** están con
> `is_active = false`.

No se generan productos sin ninguna relación, ni proveedores enteros inactivos. Ver `DT-028` §2.5.

## 43.4 Precondiciones del generador de entidades maestras

Estas políticas imponen **cinco** precondiciones sobre la configuración recibida. No son restricciones
del contrato de configuración, sino límites de esta versión del generador, que debe rechazarlas con un
error explícito y **nunca** producir un dataset degradado en silencio:

```text
P-1  product_count  >= category_count      suelo de un producto por categoría
P-2  product_count  >= 4                   suelo de un producto por clase A/B/C/D
P-3  supplier_count >= 3                   la clase C necesita tres proveedores
P-4  supplier_count <  R                   R = n_A + 2·n_B + 3·n_C + n_D
P-5  period.days    >= 2                   un producto inactivo conserva histórico
```

A ellas se suma el rechazo de `location_count > 1`, que viene de `DT-029`.

*Corrección del 2026-09-21: esta sección listaba solo las tres primeras. **P-4** y **P-5** se
añadieron a `DT-028` §8 en la auditoría de consistencia del 2026-09-18 y no se habían propagado
aquí. El Componente 2 implementa las cinco.*

Los valores concretos de todas las políticas están en `DT-028`.

---

# 44. Determinismo y sub-semillas

*Añadido en la revisión 1.1. Complementa §3.3 y cierra el elemento 4 de §40. Decisión: `DT-030`.*

§3.3 exige que «una misma configuración y una misma semilla produzcan el mismo dataset». Esa
exigencia tiene una consecuencia que conviene enunciar: **si todos los componentes del generador
comparten un único flujo pseudoaleatorio, implementar un componente nuevo altera los datos que
producían los anteriores**, porque cambia el número de extracciones previas.

Para evitarlo, cada componente deriva su propio generador a partir de la semilla común mediante una
**sub-semilla determinista**:

```text
sub_seed(componente) = primeros 64 bits de SHA-256("<seed>:<nombre del componente>")
```

Propiedades:

* solo depende de la semilla y del nombre del componente, no del orden de ejecución;
* es estable entre ejecuciones, versiones de Python y plataformas;
* añadir un componente nuevo no altera la sub-semilla de ninguno de los existentes.

Cada sub-semilla utilizada queda registrada en `manifest.json` (§42.2, campo `components`).

**Enunciado único del invariante.** El resto del documento y las decisiones `DT-025` y `DT-030`
remiten aquí en lugar de reformularlo:

> Misma configuración + misma semilla + **misma versión del generador** → los **archivos de datos**
> son idénticos byte a byte. El manifiesto difiere en `generated_at` y en los campos que dependen del
> conjunto de componentes ejecutados (`files`, `components`, `generator_version`).

La mención a la **versión del generador** no es una salvedad ociosa: §3.3 pide reproducir un dataset,
y un generador con un componente más produce legítimamente otro dataset. Sin ese término, el
invariante sería insatisfacible en cuanto exista el Componente 3.

**Límite conocido, cerrado el 2026-09-21.** La advertencia original decía: la sub-semilla es estable
entre versiones de Python y plataformas porque solo depende de SHA-256, pero el flujo pseudoaleatorio
derivado de ella **no lo está necesariamente**, porque la implementación de las funciones de la
biblioteca estándar puede cambiar entre versiones; y fijar el algoritmo concreto era trabajo del
Componente 2.

Al implementar el Componente 2 se fijó (`DT-032`): el flujo es un **contador sobre SHA-256**, de modo
que cada extracción es una función pura de `(sub-semilla, etiqueta, contador)` y **no depende de
ninguna implementación de la biblioteca estándar**. El generador no usa `random` en ninguna parte.
El límite deja de aplicar; la regla operativa que lo sustituye es que ningún componente del generador
puede usar `random`.

El detalle está en `DT-030`.
