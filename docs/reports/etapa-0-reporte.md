# Reporte de cierre — ETAPA 0

**Fecha:** 2026-09-03 · **Alcance:** Preparación, análisis y documentación base del proyecto
**Estado del repositorio al iniciar:** vacío (sin archivos, sin carpetas, sin Git, sin configuración previa)

---

## 1. Archivos creados

**Raíz (4)**

| Archivo | Contenido |
|---|---|
| `CLAUDE.md` | Guía permanente: descripción, objetivo, alcance, arquitectura conceptual, tecnologías, reglas de desarrollo, documentación, seguridad, ML, Azure, testing y Git; estructura del proyecto; flujo de trabajo del agente; criterios para modificar archivos; comportamiento ante información desconocida |
| `AGENTS.md` | Protocolo de sesión: cómo comenzar, qué leer, cómo investigar código y documentación externa, cómo planificar, implementar, probar, documentar, reportar y cuándo pedir confirmación |
| `README.md` | Qué es el proyecto, objetivo, arquitectura, tecnologías, estructura, estado actual y cómo continuará el desarrollo |
| `.gitignore` | Exclusión de secretos, datos, modelos y artefactos desde el primer commit |

**`docs/` (19)**

`01-requerimientos.md` · `02-propuesta-tecnica.md` · `03-arquitectura.md` · `04-modelo-datos.md` ·
`05-motor-predictivo.md` · `06-motor-abastecimiento.md` · `07-api.md` · `08-frontend.md` ·
`09-ia-generativa.md` · `10-seguridad.md` · `11-power-bi.md` · `12-devops.md` · `13-testing.md` ·
`14-mantenimiento.md` · `15-decisiones-tecnicas.md` · `architecture/README.md` ·
`decisions/ADR-template.md` · `reports/README.md` · `reports/etapa-0-reporte.md` (este archivo)

**`knowledge/` (4)** — `glossary.md` · `assumptions.md` · `business-rules.md` · `sources.md`

**`project/` (3)** — `roadmap.md` · `backlog.md` · `status.md`

**`tests/` (1)** — `README.md`

**Total: 31 archivos** (30 documentos markdown y `.gitignore`).

## 2. Archivos modificados

Ninguno. El directorio estaba vacío; no se sobrescribió ni eliminó nada.

## 3. Decisiones importantes

Dieciocho decisiones registradas en `docs/15-decisiones-tecnicas.md`, más diez explícitamente
diferidas. Las de mayor consecuencia:

| ID | Decisión | Estado | Por qué importa |
|---|---|---|---|
| `DT-001` | Separación estricta entre predicción ML, reglas de negocio e IA generativa | `ACEPTADA` | Es el principio que hace el sistema auditable. El LLM queda fuera de la ruta de cálculo |
| `DT-002` | Monolito modular, no microservicios | `ACEPTADA` | Evita complejidad operativa que el alcance no justifica |
| `DT-003` | Dependencias de Azure encapsuladas tras interfaces propias | `ACEPTADA` | Permite desarrollar y probar sin credenciales ni costos, y degradar sin ellas |
| `DT-006` | Histórico inmutable | `ACEPTADA` | Sin esto no hay reproducibilidad del entrenamiento ni trazabilidad de recomendaciones pasadas |
| `DT-007` | Sin SQL generado por el LLM | `ACEPTADA` | Evita respuestas plausibles pero incorrectas que nadie revisa |
| `DT-009` | Progresión de modelos por niveles con criterio de parada | `ACEPTADA` | Contrapesa la presión hacia sofisticación innecesaria |
| `DT-015` | Sin promoción automática de modelos | `ACEPTADA` | El costo de un modelo malo en producción son desabastos reales |
| `DT-016` | El sistema recomienda, no compra | `ACEPTADA` | Requisito del alcance y condición de adopción |
| `DT-018` | Explicación por plantilla determinística antes que por LLM | `ACEPTADA` | Obliga a que el desglose del cálculo esté completo antes de añadir lenguaje natural |

**Decisión de secuenciación:** el motor de abastecimiento (Fase 4) se sitúa **antes** del Machine
Learning (Fase 5). El motor consume un forecast, y ese forecast puede ser un baseline; así el sistema
entrega valor auditable temprano y el modelo, cuando llegue, solo mejora una entrada de un motor ya
probado.

**Marcadas como `PROPUESTA`** (no vinculantes): `DT-008` granularidad semanal · `DT-010` stock de
seguridad basado en el error de pronóstico · `DT-012` tránsito acotado al horizonte ·
`DT-013` ubicación de carpetas · `DT-014` modo Import en Power BI.

## 4. Supuestos realizados

Dieciocho supuestos en `knowledge/assumptions.md`, cada uno con su método de validación y su impacto
si resulta falso. Los de mayor riesgo:

| ID | Supuesto | Qué se rompe si es falso |
|---|---|---|
| `ASSUMPTION-008` | Existe corpus documental interno indexable | **Azure AI Search pierde su propósito principal** en el proyecto |
| `ASSUMPTION-004` | El consumo registrado aproxima la demanda | Todo el histórico estaría sesgado de forma no corregible |
| `ASSUMPTION-003` | Hay 24–36 meses de histórico | Se reduce drásticamente la ambición del modelado |
| `ASSUMPTION-012` | ~5.000 SKU, ~50 proveedores, 1–3 ubicaciones | Cambian varias decisiones de implementación |
| `ASSUMPTION-006` | Ubicación única en la primera versión | Aparece un dominio entero de decisiones de asignación |
| `ASSUMPTION-001` | Se trabajará con datos sintéticos | (Declarado en el alcance; condiciona la interpretación de toda métrica) |

Los demás cubren horizonte de predicción, identificación de desabastos, órdenes mono-proveedor,
jerarquía de categorías, roles, rendimiento, disponibilidad, destino de despliegue, estabilidad de
maestros y de unidades de medida, disponibilidad de costos y perfil de uso.

## 5. Problemas encontrados

| # | Problema | Cómo se trató |
|---|---|---|
| 1 | **Ausencia total de parámetros de política del negocio** (nivel de servicio, política de revisión, umbrales de riesgo, costos) | No se inventaron. Registrados como pendientes en `knowledge/business-rules.md` §3. El motor está diseñado para **no calcular** y declarar el parámetro faltante en lugar de usar un valor por defecto silencioso |
| 2 | Ambigüedad en la estructura documental solicitada: no quedaba claro si `architecture/`, `decisions/` y `reports/` iban en la raíz o dentro de `docs/` | Se ubicaron bajo `docs/` con justificación técnica registrada en `DT-013`, marcada como `PROPUESTA` pendiente de confirmación |
| 3 | Riesgo de que Azure AI Search quede sin propósito si no existe documentación interna | Documentado como el supuesto de mayor riesgo (ASSUMPTION-008) y como bloqueo explícito de la Fase 9 |
| 4 | La superficie de Azure OpenAI ha cambiado: hoy se expone como *Azure OpenAI in Microsoft Foundry Models*, con API `v1` en disponibilidad general que ya no exige `api-version` | Verificado en la documentación oficial y registrado en `knowledge/sources.md`. Reforzada la regla de verificar antes de implementar (`CLAUDE.md` §11) |
| 5 | Tensión entre completitud documental y sobreingeniería | Resuelta documentando también lo que **no** se hace y lo que se decide **no decidir** todavía (diez decisiones diferidas) |
| 6 | El entorno de trabajo en el equipo del usuario no estuvo disponible durante la sesión | La documentación se construyó en el entorno de la sesión y se entrega para su colocación en la carpeta del proyecto |
| 7 | Una revisión cruzada de los 30 documentos detectó inconsistencias internas | **Todas corregidas.** Las de fondo: (a) el caso límite "lead time cero" enunciaba que el stock de seguridad quedaba en manos de la variabilidad de la demanda, cuando la fórmula de §6.2 deja exactamente lo contrario; (b) *fill rate* estaba definido de dos formas incompatibles entre el glosario y el modelo de datos —el campo se renombró a `quantity_fulfillment_rate`—; (c) el forecast es semanal y el recálculo de recomendaciones diario, lo que no estaba dicho; (d) el rol de consulta de políticas contradecía la matriz de autorización; (e) la Fase 4 dependía de un baseline que solo producía la Fase 5, que a su vez dependía de la Fase 4 — el baseline se traslada a la Fase 4; (f) dos ciclos de dependencia entre requisitos; (g) tres conteos incorrectos de archivos, criterios y casos límite |

**Contradicciones en las instrucciones:** ninguna. La única ambigüedad relevante fue la del punto 2.

## 6. Elementos pendientes de validación

### Del negocio (bloquean fases posteriores)

1. Nivel de servicio objetivo y **qué definición** se usa (probabilidad por ciclo o tasa de satisfacción).
2. Política de revisión: continua o periódica, y con qué frecuencia.
3. Umbrales de clasificación de riesgo de desabasto y de sobreinventario.
4. Costos de faltante y de mantener inventario.
5. Criterio de selección entre proveedores alternativos.
6. Calendario laboral, festivos y estacionalidades conocidas.
7. Diferenciación de política por clase ABC o categoría.
8. Volúmenes reales de catálogo, histórico y usuarios.
9. Existencia, formato y volumen del corpus documental.
10. Mapeo de roles con los grupos de Entra ID.
11. Presupuesto disponible para servicios de Azure.
12. Licencia y capacidad de Power BI.

### Del responsable técnico

13. Confirmación de `DT-013` (ubicación de `architecture/`, `decisions/`, `reports/` bajo `docs/`).
14. Confirmación de las decisiones marcadas como `PROPUESTA` (`DT-008`, `DT-010`, `DT-012`, `DT-014`).
15. Aprobación general de la Etapa 0.

## 7. Próximo paso recomendado

**En orden de valor:**

1. **Revisar y aprobar la Etapa 0.** En particular, los cuatro documentos que fijan el rumbo:
   `01-requerimientos`, `03-arquitectura`, `06-motor-abastecimiento` y `15-decisiones-tecnicas`.

2. **Recabar del negocio los parámetros pendientes** (§6, puntos 1–8). Es el trabajo de mayor valor
   inmediato y no requiere programar nada. Sin estos datos, la Fase 4 —el núcleo del sistema— no puede
   parametrizarse de forma definitiva, por muy bien construida que esté.

3. **Confirmar o refutar ASSUMPTION-008** (existencia de corpus documental). Es la validación más
   urgente: si no hay documentación interna indexable, hay que replantear el papel de Azure AI Search
   en el proyecto, y es mejor saberlo ahora que en la Fase 9.

4. **Autorizar el inicio de la Etapa 1** (Fase 1 — Datos). Su sprint propuesto —`US-010` diseño del
   dataset → `US-011` ingesta → `US-012` marcado de desabasto— es autocontenido y **no depende de
   ninguna decisión pendiente del negocio**, por lo que puede avanzar en paralelo al punto 2.

> **La Etapa 1 no se inicia sin instrucción explícita del responsable del proyecto.**

---

## Verificación de los criterios de finalización

Los veinticinco criterios establecidos para la Etapa 0 se cumplen. Detalle en `project/status.md`.

**Restricciones respetadas:** no se desarrolló la aplicación · no se generó el dataset · no se
configuró ningún servicio de Azure · no se crearon credenciales · no se hicieron commits · no se
instalaron dependencias · no se inventó información empresarial · ninguna hipótesis se presentó como
requisito · la Etapa 1 no se inició.
