# Reglas de negocio

**Estado:** Versión 1.0 — Etapa 0 · **Fecha:** 2026-09-04 · **Versión 1.1** — revisada en la auditoría de Etapa 0.1

Reglas que rigen el comportamiento del sistema, clasificadas por su grado de confirmación.

**Advertencia central:** este proyecto no ha recibido todavía las políticas de inventario de la
organización. Por tanto, la mayoría de las reglas cuantitativas están **pendientes de validación** y
**ninguna hipótesis se presenta aquí como requisito**.

## Clasificación

| Estado | Significado |
|---|---|
| ✅ **CONFIRMADA** | Deriva directamente del alcance dado por el responsable. Es vinculante |
| 🟡 **PROPUESTA** | Razonada y coherente, pero **no confirmada** por el negocio. No es vinculante |
| ⏳ **PENDIENTE** | Se sabe que hace falta una regla, y **no se inventa** su contenido |

---

## 1. Reglas confirmadas ✅

Derivadas del alcance declarado del proyecto.

### BR-001 — El sistema recomienda; no compra
El sistema **nunca** emite una orden de compra de forma automática. Toda conversión de una
recomendación en orden es una acción humana explícita.
*Fuente:* alcance del proyecto · `RF-015`, `DT-016`

### BR-002 — La predicción no decide
El modelo de Machine Learning estima demanda futura e incertidumbre. **No** determina cantidades a
comprar, puntos de reorden ni stock de seguridad.
*Fuente:* principio arquitectónico fundamental del alcance · `RML-012`, `DT-001`

### BR-003 — La IA generativa no calcula
Azure OpenAI explica resultados ya calculados. **No** genera, altera ni recalcula ninguna cifra de
inventario o abastecimiento.
*Fuente:* principio arquitectónico fundamental del alcance · `RS-010`, `DT-001`

### BR-004 — Toda recomendación es explicable
Cada recomendación expone todos sus insumos y valores intermedios: forecast usado y su versión de
modelo, inventario considerado, lead time aplicado, stock de seguridad, punto de reorden y
restricciones del proveedor.
*Fuente:* alcance ("proporcionar explicaciones") + requisito de auditabilidad · `RF-015`, `RF-024`

### BR-005 — El histórico es inmutable
Los movimientos de inventario, el consumo y las recepciones no se modifican ni se eliminan. Toda
corrección se registra como un hecho nuevo.
*Fuente:* requisito de trazabilidad y auditabilidad · `RNF-013`, `DT-006`

### BR-006 — La posición de inventario incluye el tránsito
La comparación con el punto de reorden se hace contra la **posición de inventario de decisión** —
`existencia + tránsito efectivo − comprometido` — y no contra la existencia física ni contra la
posición contable (que usa el tránsito total). Ver `DT-012`.
*Fuente:* definición estándar del dominio · `docs/06-motor-abastecimiento.md` §4.2
*Nota:* lo **confirmado** es que el tránsito cuenta. Qué parte del tránsito es efectiva depende de un
criterio de corte todavía pendiente (`DT-P11`).

### BR-007 — Los datos sintéticos deben poder sustituirse sin rediseño
El origen de los datos se marca a nivel de registro o carga, y ninguna regla de negocio depende de
que los datos sean sintéticos o reales.
*Fuente:* alcance del proyecto · `RF-023`, `DT-004`

### BR-008 — El acceso está restringido por identidad y rol
Ningún dato se expone sin autenticación con Microsoft Entra ID y sin la autorización correspondiente
al rol, verificada en el servidor.
*Fuente:* alcance del proyecto · `RS-001`, `RS-002`, `RS-003`

### BR-009 — Los parámetros de política no se inventan
Si un parámetro necesario (nivel de servicio, umbral de riesgo) no está definido por el negocio, el
sistema **no calcula** el valor dependiente y señala explícitamente qué falta. No sustituye por un
valor por defecto silencioso.
*Fuente:* regla del proyecto "no inventar información empresarial" · `docs/06-motor-abastecimiento.md` §14

---

## 2. Reglas propuestas 🟡

Coherentes con el dominio y con el alcance, **pendientes de confirmación**. No deben tratarse como
requisitos ni implementarse como definitivas.

### BR-P01 — Se usa el lead time observado, no el acordado
Los cálculos emplean el lead time realmente observado en el histórico de recepciones. El acordado se
conserva como referencia y para medir la desviación del proveedor.
*Razón:* usar el contractual cuando el proveedor entrega sistemáticamente tarde genera desabastos previsibles.
*Requiere:* confirmación de que hay suficientes recepciones registradas para estimarlo.

### BR-P02 — El stock de seguridad incorpora la variabilidad del proveedor
El cálculo considera tanto la variabilidad de la demanda como la del lead time.
*Razón:* con proveedores poco confiables, la variabilidad del lead time domina el riesgo.
*Requiere:* confirmación del negocio sobre si se acepta este mayor nivel de inventario.

### BR-P03 — El error de pronóstico como fuente de incertidumbre del stock de seguridad
El error de pronóstico observado es la fuente de información **más pertinente** sobre la incertidumbre
que el stock de seguridad debe cubrir, por delante de la desviación histórica de la demanda.
*Razón:* lo que causa desabasto es el error de predicción, no la variabilidad en sí.
**La metodología exacta está `PENDIENTE DE VALIDACIÓN`** (`DT-010`): error acumulado sobre el intervalo
de protección, cuantiles empíricos, o intervalo del modelo previa verificación de calibración. Ninguna
de las tres es todavía la fórmula del proyecto.
*Requiere:* backtesting al horizonte del intervalo de protección y comparación por su efecto en las
métricas de Nivel 2 (`DT-020`).

### BR-P04 — Las restricciones del proveedor se aplican al final
La cantidad se calcula primero según la necesidad y después se ajusta a MOQ y múltiplo de compra,
conservando y mostrando ambos valores.
*Razón:* permite distinguir la necesidad real del ajuste comercial impuesto.

### BR-P05 — Se señala el conflicto entre MOQ y sobreinventario
Cuando el MOQ obliga a una cantidad que genera sobrecobertura, el sistema lo indica en lugar de
ocultarlo.
*Razón:* puede haber razones comerciales que el sistema desconoce; la decisión es del comprador.

### BR-P06 — Cuatro niveles de riesgo
Clasificación en `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`. `CRITICAL` identifica el caso en que ya no se
llega a tiempo aunque se pida hoy.
*Razón:* `CRITICAL` requiere una acción distinta (proveedor alternativo, envío urgente, sustitución),
no simplemente "comprar antes".
*Requiere:* validación de los umbrales por el negocio.

### BR-P07 — Proveedor sugerido por preferencia declarada
Mientras no exista un criterio de selección definido, se sugiere el proveedor marcado como preferente
y se muestran las alternativas con sus indicadores.
*Razón:* no se inventa una función de puntuación entre costo, lead time y confiabilidad.
*Requiere:* definición del criterio de selección por el negocio.

### BR-P08 — El descarte de una recomendación exige motivo
Descartar una recomendación requiere indicar el motivo.
*Razón:* es la retroalimentación que permitirá detectar qué restricción le falta al motor. Una tasa
alta de descarte con un motivo recurrente es información valiosa, no ruido.

### BR-P09 — Sin modelo disponible se usa el baseline, declarándolo
Si el modelo no está disponible o su calidad cae bajo el umbral, se usa el baseline y la salida lo
indica explícitamente.
*Razón:* el sistema nunca se queda sin predicción, y nunca presenta una predicción degradada como normal.

### BR-P10 — Los productos inactivos se excluyen del cálculo
Los productos desactivados o descontinuados no generan predicciones ni recomendaciones, pero
conservan su histórico.
*Requiere:* confirmación de cómo se marca un producto como descontinuado en el negocio.

### BR-P11 — Las políticas de inventario son versionadas
Un cambio de política crea una nueva versión con vigencia; no sobrescribe la anterior.
*Razón:* una recomendación pasada debe explicarse con la política vigente en su momento.

### BR-P12 — Los periodos de desabasto se marcan como censurados
El consumo registrado durante un desabasto se marca para recibir un tratamiento explícito en el
entrenamiento.
*Razón:* evita que el modelo aprenda que la demanda cayó (`DT-011`).
*Requiere:* verificar que el histórico permite identificar esos periodos (ASSUMPTION-005).

---

## 3. Reglas pendientes de definición ⏳

Se sabe que el sistema las necesita. **Su contenido no se inventa**: debe aportarlo el negocio.

### BR-X01 — Nivel de servicio objetivo
**Falta:** el valor objetivo y **qué definición** se usa (probabilidad de no agotar en un ciclo, o
proporción de demanda satisfecha). Ambas producen stocks de seguridad distintos.
**Bloquea:** el cálculo del stock de seguridad (`RF-011`).
**Pregunta al negocio:** ¿qué nivel de servicio se compromete? ¿Es el mismo para todo el catálogo o
varía por categoría o clase ABC?

### BR-X02 — Política de revisión
**Falta:** si la revisión es continua o periódica, y con qué frecuencia.
**Bloquea:** la fórmula del punto de reorden y el intervalo de protección (`RF-012`).
**Pregunta al negocio:** ¿con qué frecuencia se revisan y emiten pedidos hoy?

### BR-X03 — Umbrales de clasificación de riesgo
**Falta:** los valores que separan `CRITICAL`, `HIGH`, `MEDIUM` y `LOW`, y los de sobreinventario.
**Bloquea:** `RF-013`, `RF-014`.
**Pregunta al negocio:** ¿a partir de cuántos días de cobertura se considera un producto en riesgo?
¿Y en exceso?

### BR-X04 — Costos de faltante y de mantener inventario
**Falta:** el costo de un desabasto y el costo de mantener inventario.
**Bloquea:** cualquier optimización económica y la priorización por impacto monetario.
**Pregunta al negocio:** ¿existe una estimación del costo de un desabasto (venta perdida, paro, urgencia)?

### BR-X05 — Criterio de selección entre proveedores
**Falta:** cómo elegir cuando hay varios proveedores para un producto.
**Bloquea:** la sugerencia automática de proveedor (`RF-015`).
**Pregunta al negocio:** ¿prima el costo, el lead time o la confiabilidad? ¿Hay acuerdos de volumen?

### BR-X06 — Calendario laboral y estacionalidades conocidas
**Falta:** días hábiles, festivos, cierres, periodos de alta y baja actividad conocidos.
**Bloquea:** conversión entre días naturales y hábiles; features de calendario.
**Pregunta al negocio:** ¿qué días no hay operación? ¿Hay temporadas conocidas de alta demanda?

### BR-X07 — Diferenciación de política por segmento
**Falta:** si la política varía por clase ABC, categoría o criticidad.
**Bloquea:** el diseño de `InventoryPolicy` por ámbito.
**Pregunta al negocio:** ¿se trata igual a un producto crítico que a uno de bajo valor?

### BR-X08 — Tolerancia de sobre-recepción
**Falta:** si se acepta recibir más de lo pedido y con qué margen.
**Bloquea:** validación de recepciones.

### BR-X09 — Tratamiento del inventario negativo
**Falta:** si el sistema debe permitir existencias negativas.
**Bloquea:** restricciones del modelo de datos.

### BR-X10 — Productos sustitutos o equivalentes
**Falta:** si existen productos intercambiables cuya demanda deba analizarse conjuntamente.
**Bloquea:** interpretación correcta de la demanda; un sustituto puede explicar una caída aparente.

### BR-X11 — Restricciones de presupuesto y de capacidad
**Falta:** si hay límites de presupuesto de compra por periodo o de capacidad de almacén.
**Bloquea:** cualquier optimización conjunta (hoy fuera de alcance, pero condicionaría el diseño futuro).

### BR-X12 — Horizonte de aprobación de compras
**Falta:** si existen umbrales de importe que requieran aprobaciones adicionales.
**Bloquea:** el flujo de conversión de recomendación en orden.

### BR-X13 — Horizonte de cobertura deseado
**Falta:** cuánta cobertura adicional se desea más allá del punto de reorden (`H_cobertura` en
`docs/06-motor-abastecimiento.md` §8; campo `target_coverage_days` de `InventoryPolicy`).
**Bloquea:** el cálculo de la cantidad recomendada (`RF-015`).
**Pregunta al negocio:** cuando se repone, ¿para cuántos días o semanas se compra habitualmente?

---

## Reglas puenteadas provisionalmente por V1

`DT-031` define un conjunto de **reglas técnicas provisionales de V1** que permiten calcular la
cadena de abastecimiento sobre el dataset sintético sin esperar a que el negocio aporte sus
políticas. **No confirma ninguna regla de este documento.** Lo que hace es sustituirlas de forma
declarada y reemplazable, y solo dentro del entorno sintético:

| Regla pendiente | Qué la puentea en V1 | Con qué valor provisional |
|---|---|---|
| `BR-X01` — nivel de servicio | `DT-031` §V1-05 | `z_v1 = 1,65`, **parámetro técnico**, no un nivel de servicio acordado |
| `BR-X02` — política de revisión | `DT-031` §V1-03 | Revisión periódica con `R_v1 = 7 días`, **no la frecuencia de compra real** |
| `BR-X13` — horizonte de cobertura | `DT-031` §V1-03 | Queda fuera del camino: en la formulación *order-up-to*, `R` cumple su papel |
| `BR-P01` — lead time observado | `DT-031` §V1-09 | **V1 la implementa**: mediana de las últimas observaciones, con fallback al acordado sin histórico suficiente. Sigue siendo regla **propuesta**: su confirmación es del negocio |
| `BR-P02` — variabilidad del proveedor | `DT-031` §V1-05 | V1 **ignora** `σ_L` |
| `DT-010` — fuente de la incertidumbre | `DT-031` §V1-05 | V1 usa variabilidad de la demanda, porque sin modelo no hay error de pronóstico medible |
| `DT-019` — conversión semanal → días | `DT-031` §V1-04 | Prorrateo uniforme, la alternativa (a) ya recomendada |
| `DT-P11` — corte del tránsito efectivo | `DT-031` §V1-02 | V1 cuenta como efectivo lo que llega dentro del horizonte; **no decide** el caso de las órdenes vencidas |

### Reglas cerradas con una interpretación técnica V1 (2026-09-19, confirmadas el 2026-09-21)

Cuatro reglas de §3 **no requerían una política empresarial**, sino una interpretación técnica que la
documentación ya sostenía. `DT-031` la fija para V1. **Siguen figurando como pendientes en §3**: lo
que existe es una regla provisional que el negocio puede contradecir, no una confirmación.

| Regla | Interpretación V1 | Regla V1 | En qué se apoya |
|---|---|---|---|
| `BR-X05` | Se usa el **proveedor preferente activo**; sin él, no se recomienda | `V1-10` | `BR-P07` ya lo propone; `DT-028` §2.4 garantiza exactamente uno por producto **en las clases A, B y C** — la clase D es justamente el caso sin proveedor activo |
| `BR-X07` | **Política única** para todo el catálogo; sin diferenciación por ABC. El campo **no se elimina** del modelo: queda fuera del cálculo | `V1-11` | `abc_class` queda nulo (`DT-029`): no hay segmento sobre el que diferenciar |
| `BR-X08` | **No se permite** sobre-recepción (`quantity_received ≤ quantity_ordered`); el validador la rechaza | `V1-12` | §21 de la especificación lo establece salvo escenario explícito, y V1 no crea ninguno |
| `BR-X09` | **No se permite** inventario negativo (`on_hand ≥ 0`); es incidente de datos | `V1-13` | §26 condiciona su admisión a una confirmación que no existe; `docs/06` §14 ya lo trata como inconsistencia |

Las otras nueve siguen abiertas: `BR-X01` y `BR-X02` **puenteadas** (tabla de arriba), y `BR-X03`,
`BR-X04`, `BR-X06`, `BR-X10`, `BR-X11`, `BR-X12` y `BR-X13` **no son necesarias para V1** y se
aplazan sin puentear.

**Confirmación del 2026-09-21.** El responsable confirmó las cuatro interpretaciones y pidió
nombrarlas como reglas propias de V1 (`V1-10` a `V1-13`) para que queden trazables. La confirmación
es **de la regla técnica de V1**, no de la política empresarial: las trece reglas de §3 siguen
figurando como pendientes y ninguna de ellas puede citarse como decidida por el negocio. En
particular, `V1-11` **no elimina** `abc_class` ni `rotation_class` del modelo de datos: los mantiene
como campos derivados, nulos y fuera del cálculo.

**`BR-009` no queda puenteada.** Sigue rigiendo sin excepción fuera del entorno sintético: si falta
un parámetro de política, el sistema no calcula el valor dependiente y señala qué falta. La salida
de V1 **no puede presentarse como una recomendación de negocio**.

---

## Cómo usar este documento

1. **Nunca** implementar una regla marcada 🟡 o ⏳ como si fuera definitiva.
2. Al obtener una definición del negocio: mover la regla a ✅, registrar la fuente y la fecha, y
   actualizar los documentos afectados en el mismo cambio.
3. Al descubrir una regla nueva durante el desarrollo: registrarla aquí con su estado correcto **antes**
   de construir sobre ella.
4. Si una regla propuesta se refuta: documentar la realidad y actualizar los cálculos afectados.
5. Ante una contradicción entre reglas: documentarla y solicitar validación. No resolverla unilateralmente.
