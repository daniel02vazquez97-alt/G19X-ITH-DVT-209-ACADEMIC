-- 0005 — Enlace del baseline de referencia con el registro de modelos de Azure ML (U14, DT-102, DT-104).
--
-- U14 registró en Azure ML el modelo baseline-ma13, versión 1, después de reproducir el backtesting con la misma
-- huella results_sha256 que el informe versionado. Esta migración anota esa referencia en external_ref (docs/04
-- §9.10) de la fila del baseline de referencia: baseline.moving_average 1.0.0, ventana de 13 semanas. Solo rellena
-- un valor NULL; no cambia ninguna definición, cálculo ni ejecución. En una base vacía no hace nada: la fila se crea
-- después con la referencia (backend/app/forecasting/baselines.py).

UPDATE model_versions
SET external_ref = 'azureml:baseline-ma13:1'
WHERE name = 'baseline.moving_average' AND version = '1.0.0' AND is_baseline AND external_ref IS NULL;
