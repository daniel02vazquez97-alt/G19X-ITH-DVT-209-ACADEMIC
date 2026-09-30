# 14 — Plan preliminar de mantenimiento

**Estado:** Versión 1.0 — Etapa 0 (plan preliminar) · **Fecha:** 2026-09-03

> Plan **preliminar**. Los objetivos de servicio, los responsables y las ventanas de mantenimiento
> están pendientes de definición por la organización.

---

## 1. Particularidad de este sistema

Un sistema con un componente de Machine Learning se degrada **aunque nadie toque el código**. El
mundo cambia —nuevos productos, nuevos proveedores, cambios de demanda— y un modelo entrenado hace
seis meses sigue respondiendo con normalidad mientras acumula error.

Esto obliga a un mantenimiento en dos planos:

| Plano | Naturaleza del deterioro | Cómo se detecta |
|---|---|---|
| **Software** | Fallos, vulnerabilidades, dependencias obsoletas | Errores, alertas, análisis automatizado |
| **Modelo** | Deriva silenciosa: sigue funcionando, pero acierta menos | **Solo con monitoreo activo de la calidad predictiva** |

El segundo es el peligroso: no produce errores, produce recomendaciones peores.

## 2. Mantenimiento de la aplicación

| Actividad | Frecuencia propuesta | Contenido |
|---|---|---|
| Revisión de errores y logs | Diaria (laborable) | Errores recurrentes, latencias anómalas |
| Revisión de alertas | Continua | Disponibilidad, tasa de error, procesos batch fallidos |
| Verificación del proceso batch | Diaria | Que el recálculo se ejecutó y cubrió todo el catálogo |
| Actualización de dependencias menores | Mensual | Parches de seguridad y correcciones |
| Actualización de dependencias mayores | Trimestral | Con pruebas de regresión completas |
| Revisión de configuración | Trimestral | Variables, límites de tasa, políticas |
| Revisión de documentación | Por cada decisión técnica | Documentación al día (`CLAUDE.md` §8) |

**Indicadores de salud:** disponibilidad de la API, tasa de error por endpoint, latencia p95, éxito
y duración del proceso batch, número de SKU sin predicción, proporción de uso del baseline.

## 3. Mantenimiento de la base de datos

| Actividad | Frecuencia propuesta | Contenido |
|---|---|---|
| Verificación de respaldos | Semanal | Que existen y son restaurables |
| **Prueba de restauración** | Trimestral | Restauración real en entorno aislado. Un respaldo no probado no es un respaldo |
| Revisión de rendimiento | Mensual | Consultas lentas, índices no usados o faltantes |
| Mantenimiento rutinario | Automático | Estadísticas y limpieza (`VACUUM`/`ANALYZE` en PostgreSQL) |
| Crecimiento y espacio | Mensual | Proyección de crecimiento de tablas históricas |
| Conciliación de inventario | Semanal | Posición almacenada vs. reconstruida desde movimientos |
| Revisión de calidad de datos | Semanal | Huecos en el histórico, valores atípicos, duplicados |
| Archivado de datos antiguos | Anual | Según la política de retención (**pendiente**) |

La **conciliación de inventario** es específica de este sistema: si la posición almacenada se separa
del histórico de movimientos, todas las recomendaciones posteriores parten de una base falsa.

## 4. Monitoreo del modelo

| Señal | Qué indica | Frecuencia |
|---|---|---|
| Error de pronóstico observado (WAPE/MASE) | Calidad real contra la demanda ocurrida | Semanal |
| **Sesgo acumulado** | Sobre o subestimación sistemática | Semanal |
| Cobertura del intervalo | Si la incertidumbre declarada es realista | Mensual |
| Error por segmento | Si falla en los SKU críticos aunque el promedio esté bien | Mensual |
| Deriva de datos de entrada | Cambio en la distribución respecto al entrenamiento | Semanal |
| Deriva de predicción | Cambio en la distribución de salidas | Semanal |
| Proporción de uso del baseline | Salud operativa del modelo | Diaria |
| SKU sin predicción | Cobertura del catálogo | Diaria |

Azure Machine Learning proporciona monitoreo de modelos en producción con señales de deriva de datos
y de degradación del desempeño; se usará esa capacidad. La configuración concreta se verificará
contra la documentación oficial vigente en la Fase 6.

**El sesgo merece vigilancia separada.** Un modelo con error absoluto aceptable pero sesgo negativo
persistente subestima la demanda de forma sistemática y produce desabastos crónicos. No aparece en
las métricas habituales de error, y es el fallo más costoso de este sistema.

## 5. Detección de deriva

| Tipo | Qué cambia | Respuesta |
|---|---|---|
| **Deriva de datos (covariate shift)** | La distribución de las entradas | Investigar la causa; evaluar reentrenamiento |
| **Deriva de concepto** | La relación entre entradas y demanda | Reentrenamiento; posible revisión de features |
| **Deriva de desempeño** | El error aumenta | Prioritario: investigar y reentrenar |
| **Cambio estructural** | Nuevo catálogo, nuevo proveedor, nueva política | Reentrenamiento y revisión del diseño |

**Procedimiento ante una alerta de deriva:**

1. Confirmar que no se trata de un problema de datos (carga incompleta, cambio de unidad, duplicados).
   La causa más frecuente de una "deriva" es un fallo de datos, no un cambio del mundo.
2. Determinar el alcance: ¿todo el catálogo o un segmento?
3. Evaluar si el baseline se comporta mejor que el modelo en ese periodo.
4. Decidir: reentrenar, revisar features, o aceptar y vigilar.
5. Documentar el episodio y su resolución.

**Ninguna alerta dispara por sí sola un cambio de modelo en producción.**

## 6. Reentrenamiento

| Disparador | Detalle |
|---|---|
| **Programado** | Mensual (propuesta inicial, ajustable con evidencia) |
| **Por deriva** | Al superarse un umbral de deriva o de degradación |
| **Por cambio estructural** | Decisión humana ante cambios del negocio |

Procedimiento: entrenar → evaluar con el mismo protocolo (`docs/05-motor-predictivo.md` §12) →
comparar contra el baseline **y** contra el modelo en producción → aprobación humana → promoción →
registro de la nueva versión.

**Un modelo reentrenado no sustituye automáticamente al vigente.** Un reentrenamiento sobre un
periodo anómalo puede empeorar el sistema; la evaluación existe precisamente para detectarlo.

## 7. Versionado

| Elemento | Estrategia |
|---|---|
| Aplicación | Versionado semántico; imagen etiquetada con versión y commit |
| Esquema de base de datos | Migraciones versionadas y ordenadas |
| Modelos | `ModelVersion` + registro de modelos de Azure ML |
| Motor de reglas | `engine_version` almacenada en cada recomendación |
| Políticas de inventario | Versionadas con vigencia temporal |
| API | Versión en la ruta (`/api/v1`) |

**Regla de trazabilidad:** una recomendación generada hace seis meses debe poder explicarse con la
versión de modelo, la versión de motor y la política **vigentes en aquel momento**, no con las actuales.

## 8. Gestión de incidentes

### Clasificación propuesta (pendiente de validación)

| Severidad | Definición | Ejemplo |
|---|---|---|
| **S1 — Crítica** | Sistema inaccesible o datos corrompidos | API caída; inventario inconsistente |
| **S2 — Alta** | Función principal degradada | El batch no genera recomendaciones |
| **S3 — Media** | Función secundaria afectada | El asistente de IA no responde |
| **S4 — Baja** | Molestia sin impacto operativo | Error de formato en una vista |

### Procedimiento

1. Detectar y registrar (identificador de correlación, alcance, hora).
2. Clasificar y comunicar a los afectados.
3. **Contener**: si el motor produce resultados dudosos, suspender la generación de recomendaciones
   antes que emitir recomendaciones erróneas. Es preferible no recomendar a recomendar mal.
4. Diagnosticar y resolver.
5. Verificar con pruebas.
6. Documentar: causa raíz, resolución y prevención.
7. Añadir la prueba que habría detectado el incidente.

**Caso especial — resultados dudosos:** si se sospecha que las recomendaciones son incorrectas, se
marcan como no fiables en la interfaz. Ocultarlo destruiría la confianza del planificador, que es el
activo más difícil de recuperar en este tipo de sistema.

## 9. Respaldos

| Elemento | Propuesta | Estado |
|---|---|---|
| Base de datos | Respaldo diario completo + registros de transacciones | **Pendiente** de política formal |
| Retención | 30 días en línea; archivado de largo plazo por definir | **Pendiente** |
| Modelos | Conservados en el registro de Azure ML | Propuesta |
| Configuración e infraestructura | Versionada en el repositorio | Propuesta |
| Documentos indexados | Respaldo del origen documental | **Pendiente** |

**Verificación:** un respaldo que nunca se ha restaurado no es un respaldo. Prueba de restauración
trimestral, obligatoria.

## 10. Recuperación

| Escenario | Acción |
|---|---|
| Pérdida de la base de datos | Restaurar desde respaldo; recalcular los datos derivados |
| Corrupción de datos operativos | Restaurar al punto anterior; reprocesar la ingesta desde el origen |
| Modelo defectuoso en producción | Revertir a la versión anterior o al baseline |
| Despliegue fallido | Revertir a la imagen anterior; revertir migraciones si procede |
| Servicio de Azure no disponible | Degradación controlada (RNF-010): el núcleo sigue operando |
| Pérdida de datos derivados | Regenerar por recálculo; **la trazabilidad histórica no se recupera** |

Los objetivos de RTO y RPO están **pendientes de definición**. Sin ellos, el plan de recuperación es
una intención, no un compromiso.

## 11. Actualización de dependencias

| Tipo | Criterio |
|---|---|
| Parches de seguridad | Aplicar con prontitud; los críticos, de forma prioritaria |
| Versiones menores | Mensual, con la suite de pruebas completa |
| Versiones mayores | Trimestral, evaluando cambios incompatibles |
| Dependencias abandonadas | Sustituir; registrar la decisión como ADR |

Todas las versiones fijadas; análisis de vulnerabilidades automatizado en CI (RS-013).
Ninguna actualización se integra sin que las pruebas pasen.

## 12. Soporte

**Pendiente de definición** por la organización: canal de atención, horario, responsables, tiempos de
respuesta comprometidos por severidad y procedimiento de escalado.

Propuesta mínima de partida: un canal único de registro de incidencias, un responsable técnico
identificado y un responsable de negocio para las decisiones sobre parámetros de política.

## 13. Documentación operativa a producir

| Documento | Fase |
|---|---|
| Manual de operación del proceso batch | 4–5 |
| Guía de resolución de incidencias frecuentes | 14 |
| Procedimiento de reentrenamiento y promoción | 6 |
| Procedimiento de respaldo y restauración | 13 |
| Guía de usuario para el planificador | 15 |
| Registro de cambios de política de inventario | Desde la Fase 4 |

## 14. Pendiente de definición

1. Objetivos de disponibilidad, RTO y RPO.
2. Ventanas de mantenimiento permitidas.
3. Responsables de operación, soporte y decisiones de negocio.
4. Política de retención de datos, logs y auditoría.
5. Presupuesto operativo (afecta a la frecuencia de reentrenamiento y al uso de servicios de Azure).
6. Umbrales concretos de alerta para deriva y degradación.
7. ¿Existe un procedimiento corporativo de gestión de incidentes al que deba alinearse este plan?
