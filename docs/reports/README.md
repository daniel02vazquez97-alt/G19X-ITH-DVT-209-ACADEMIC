# Reportes

Reportes de cierre de etapa y de fase, informes de evaluación y resultados de verificación.

## Contenido actual

| Reporte | Fecha |
|---|---|
| [`etapa-0-reporte.md`](etapa-0-reporte.md) | 2026-09-03 |
| [`etapa-0-1-reporte.md`](etapa-0-1-reporte.md) | 2026-09-04 |
| [`dataset-sintetico-0.4.0-calidad.md`](dataset-sintetico-0.4.0-calidad.md) — remite a `manifest.quality_report` | 2026-09-29 |
| [`fase5-f5a-backtest-sintetico.md`](fase5-f5a-backtest-sintetico.md) — F5a: backtesting de baselines, Nivel 1 y segmentación provisional (`SYNTHETIC`; sin elección de baseline ni de métrica; incluye la huella, el comando exacto y la fecha de generación) | 2026-10-05 |

## Reportes previstos

| Reporte | Fase |
|---|---|
| Informe de evaluación de modelos (métricas, baseline, decisión) | 5 |
| Informe de simulación retrospectiva del motor de abastecimiento | 14 |
| Informe de pruebas de rendimiento | 14 |
| Informe de pruebas de seguridad | 14 |
| Informe de cierre del proyecto | 15 |

## Convenciones

- Los informes de la Fase 5 versionan solo el Markdown. Los datos detallados (CSV por serie y corte y el resumen
  JSON con las métricas por corte) no se versionan: se regeneran de forma determinista con el comando que figura en
  cada informe, en `ml/out/`, que Git ignora. La huella `results_sha256` del informe permite comprobar que la
  regeneración coincide.
- Un reporte describe **lo que ocurrió**, no lo que se pretendía. Incluye lo que no funcionó.
- Los informes de evaluación de modelos incluyen **siempre** el resultado del baseline y la
  dispersión entre cortes, no solo la métrica promedio del modelo elegido.
- Todo reporte lleva fecha, alcance y las versiones de datos, modelo y código sobre las que se hizo.
- Los reportes no se editan después de emitidos: se emite uno nuevo.
