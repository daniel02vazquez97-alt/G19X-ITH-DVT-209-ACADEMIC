# Informe de calidad del dataset sintético — `ds-6c8ad65b4999` (generador 0.4.0)

- **Fecha:** 2026-09-29
- **Alcance:** dataset sintético de la Fase 1 publicado en `data/synthetic/output/` con la
  configuración `data/synthetic/config/dataset_config.yaml`.
- **Versiones:** `dataset_version` `ds-6c8ad65b4999` · `generator_version` `0.4.0` · componentes
  C2–C8 en `0.1.0` · semilla 20260913 · periodo 2023-01-01 → 2026-01-01.
- **Fuente única del informe:** el campo **`quality_report` de `data/synthetic/output/manifest.json`**
  (`DT-042` §5). Este documento **no lo duplica**: solo registra que existe, contra qué se emitió y su
  resultado.

## Resultado

| | |
|---|---|
| Resultado | `PASS` |
| Comprobaciones ejecutadas / aprobadas / fallidas | 51 / 51 / 0 (`DT-042` §4) |
| Escenarios de `scenarios.required` cubiertos | 16 de 16 (`scenario_assignment`, `DT-041`) |
| Situaciones de nivel C detectadas | 4 de 4 (8, 12, 18 y 20 de §25) |
| Anomalías | `[]` — no existe criterio contractual de anomalía (`DT-042` §6) |
| Reproducibilidad | Dos generaciones independientes: CSV idénticos byte a byte y manifiesto idéntico salvo `generated_at` |

Los doce CSV son byte a byte los del dataset 0.3.0 (`ds-269a698250db`) de la misma configuración: la
versión 0.4.0 cambia el manifiesto —`scenario_assignment`, `quality_report` y dos componentes—, no
los datos.

## Advertencia

Los datos son **sintéticos**: ninguna cifra del informe es una métrica real del negocio (§35). Los
criterios `SYNTHETIC_COVERAGE_CRITERION` demuestran cobertura del dataset y **no** son reglas de
negocio; `BR-X03`, `DT-P11`, `BR-P10` y `DT-011` siguen pendientes. Las limitaciones conocidas están
en `quality_report.known_limitations`.
