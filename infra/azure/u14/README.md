# U14 — Azure Machine Learning mínimo (`DT-102`)

Reproduce en Azure Machine Learning el *backtesting* F5a del baseline oficial (media móvil de 13 semanas) y lo registra
con MLflow. **Criterio de aceptación:** el `results_sha256` del job es idéntico al del informe versionado
[`docs/reports/fase5-f5a-backtest-sintetico.json`](../../../docs/reports/fase5-f5a-backtest-sintetico.json)
(`67608e95…`). `ml/` no cambia y sigue sin dependencias; MLflow vive en `job/run_backtest.py`.

## 1. Qué se crea

| Recurso | Configuración | Coste |
|---|---|---|
| Workspace `mlw-mpa-dev` | `kind: Default`, identidad del sistema, **sin** registro de contenedores | 0 USD |
| Almacenamiento `stmpaml<sufijo>` | `Standard_LRS`, sin blobs públicos, solo HTTPS, TLS 1.2 | Céntimos al mes |
| Key Vault `kv-mpaml-<sufijo>` | Standard, directivas de acceso vacías (el servicio añade la del workspace), borrado temporal de 7 días | Céntimos |
| Application Insights `appi-mpa-ml-dev` sobre Log Analytics `log-mpa-ml-dev` | El servicio lo exige (el primer despliegue falló sin él). Retención de 30 días y límite de ingesta de 0,1 GB/día | Céntimos como máximo |
| Cómputo | **Serverless** `Standard_DS2_v2` (2 vCPU, familia DSv2, cuota de 4): solo existe mientras dura el job | Céntimos por ejecución |
| Modelo `baseline-ma13` | `custom_model`: configuración del baseline, comparación e informe. **Sin endpoint** | 0 USD |

El job usa la misma imagen base que la API (`python:3.11.17-slim-trixie`, fijada por digest) e instala sus tres
dependencias fijadas (`job/requirements.txt`). No se construye ninguna imagen, así que no hace falta registro de
contenedores.

## 2. Procedimiento

Desde la raíz del repositorio, con tu sesión de Azure CLI y la extensión `ml` (`az extension add --name ml`):

| # | Comando | Qué hace | Confirmación |
|---|---|---|---|
| 1 | `powershell -ExecutionPolicy Bypass -File infra\azure\deploy-u14.ps1 -PreflightOnly` | Solo lectura: sesión, grupo, proveedores, extensión `ml`, workspaces existentes y huella versionada | — |
| 2 | `… -Stage Deploy` | `validate` → *what-if* comprobado (workspace sin ACR, almacenamiento, Key Vault, Application Insights y Log Analytics con límite diario; nada más ni ningún `Delete`) → creación | `AZUREML` |
| 3 | `… -Stage Submit` | Monta la instantánea mínima del código en `tmp/u14-job`, envía el job, espera, descarga la salida `model` a `tmp/u14-evidence/` y, **solo si la huella coincide**, registra `baseline-ma13` | — |
| 4 | `… -Stage Verify` | Workspace, job `Completed`, huella igual a la versionada, modelo registrado, sin cómputo ni *endpoints*; `tmp/u14-evidence/u14-evidence.json` | — |

En el portal (Azure ML Studio → Jobs → `u14-baseline-ma13`) se ven las métricas de MLflow (MASE, WAPE, MAE, RMSE,
sesgo y cobertura de cada baseline) y los artefactos del informe.

## 3. Desmontaje

`deploy-u14.ps1 -Stage Remove`, confirmando con `BORRAR`: borra de forma permanente el workspace con todos sus recursos
dependientes, purga el Key Vault y borra Log Analytics. No toca nada de U10–U13.

## 4. Pruebas sin Azure

- `infra/tests/test_u14_config.py`: Bicep, job (imagen igual a la de la API, *serverless*, dependencias fijadas),
  `ml/` sin MLflow ni Azure, funciones del envoltorio y `deploy-u14.ps1 -SelfTest` (9 casos del *what-if*).
- El envoltorio se ejecutó en local desde la instantánea mínima: `reproduces_versioned_report: true`.
