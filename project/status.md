# Estado del proyecto

**Última actualización:** 2026-10-08 (**U12: `-PreflightOnly` corregido** — el script solo aceptaba `-Stage Preflight`, distinto de U10/U11; ahora `-PreflightOnly` (= `-Stage Preflight`) es estrictamente de solo lectura con lista blanca de comandos `az`, 12 secciones y `PREFLIGHT OK`/`PREFLIGHT BLOQUEADO`, `KeyVault deploy/action: ALLOWED/MISSING`; nada desplegado · sin commit) · 2026-10-08 (**U12 AUTORIZADA PARA DESPLIEGUE REAL — opción C del Key Vault aceptada (MVP/`dev`)**; `deploy-u12.ps1` comprueba que tu sesión tenga `Microsoft.KeyVault/vaults/deploy/action` (GitHub no la necesita ni la recibe; rol personalizado mínimo solo si falta), `Verify` con 18 comprobaciones (API tras el proxy, última ejecución del job, contraseñas solo como `secretRef`), evidencias con secretos redactados; despliegue real pendiente del responsable · sin commit) · 2026-10-07 (**U12 IMPLEMENTADA — DESPLIEGUE REAL PENDIENTE DEL RESPONSABLE** — `DT-100` `ACEPTADA`, cierra `DT-P01` para `dev`: Container Apps (Consumption; frontend externo HTTPS, api interna), job único de bootstrap idempotente, ACR Basic, PostgreSQL 16 B1ms con firewall por IP de salida, identidad de ejecución con `AcrPull`, GitHub OIDC con `AcrPush` + Container Apps Contributor (grupo) + Managed Identity Operator (identidad de ejecución), contraseñas generadas en el Key Vault, `deploy-u12.ps1` y `deploy-dev.yml`; **sub-decisión del Key Vault pendiente** (bypass de ARM para plantillas con `publicNetworkAccess` Disabled, frente a A/B); pruebas locales en verde; nada creado en Azure · sin commit) · 2026-10-07 (**U12 AUTORIZADA — BLOQUEADA POR `DT-P01`** — el destino de cómputo sigue abierto; `DT-100` (`PROPUESTA`): Container Apps de Consumo con escala a cero y job de init, ACR Basic, PostgreSQL Flexible 16 B1ms, contraseña generada en Key Vault, sub-decisión de red pendiente, GitHub solo con `AcrPush` + Container Apps Contributor; nada creado en Azure · sin commit) · 2026-10-07 (**U11 COMPLETADA** — `DT-099`: prueba real 5/5 en el entorno aislado `u11-entra-dev`: `VIEWER` (11×200, `history` y `runs` 403), no autenticado (401 `AUTHENTICATION_REQUIRED` / `INVALID_TOKEN`), sin rol (`/me` 200 y 12×403), cambio a `PLANNER` (13×200); identificadores de la API y la SPA en `DT-099`; corregido: `appRoleAssignmentRequired` en la API no filtra usuarios delegados, la barrera es el backend; U12 sin autorizar · sin commit) · 2026-10-07 (**U11: PRUEBA REAL 2/5** — inicio de sesión real con Entra ID como `VIEWER`; `/acceso`: 11 endpoints permitidos → 200, `history` y `runs` → 403 de la API, 13/13 coinciden con la matriz; faltan no autenticado, sin rol y cambio de rol · sin commit) · 2026-10-07 (**U11: INICIO DE SESIÓN CORREGIDO** — `in_mem_redirect_unavailable`: MSAL 5 no admite redirecciones con caché en memoria; la SPA usa ahora el almacenamiento de sesión de la pestaña (desviación de `docs/10` §4 anotada en `DT-099`) y una prueba con el MSAL real cubre la redirección; Entra ID sin cambios; hay que reconstruir la imagen `frontend` · sin commit) · 2026-10-07 (**U11: ENTORNO DOCKER AISLADO `u11-entra-dev`** — el primer arranque real falló en `init` con `MigrationError: applied migration 0001_dataset_tables has changed on disk` porque Compose reutilizaba el proyecto `infra` y su volumen `infra_pgdata`; no era Entra ID. El archivo de U11 fija `name: u11-entra-dev` y la documentación usa `-p u11-entra-dev` (volúmenes propios, base nueva); `smoke.py --entra`; migración, checksum, verificación y volumen local sin tocar. Causa de fondo anotada en `DT-099`: el hash de migraciones depende de CRLF/LF · sin commit) · 2026-10-07 (**U11 IMPLEMENTADA — CONFIGURACIÓN REAL Y PRUEBA REAL PENDIENTES DEL RESPONSABLE** — `DT-099`: `APP_ENV=dev` valida tokens de acceso v2.0 de Microsoft Entra ID (RS256 con el JWKS del tenant, `iss`, `tid`, `aud`, `azp`, `scp`, vigencia) y aplica los cuatro app roles de ASSUMPTION-010 con la matriz de `docs/07` §7.2 sin cambios; SPA con MSAL (código + PKCE, caché en memoria) y página `/acceso`; `infra/azure/deploy-u11.ps1` reejecutable (`ALREADY_CONFIGURED`, sin duplicados, sin secretos, rollback acotado) probado contra un Azure CLI simulado; `APP_ENV=local` sin cambios; API 95, backend 353, integración, infra y frontend 174 en verde; sin commit) · 2026-10-07 (**U10 COMPLETADA — DESPLEGADA Y VERIFICADA** — `DT-098`: el responsable ejecutó `infra/azure/deploy-dev.ps1` con su sesión de Azure CLI: `validate` `Succeeded`, `what-if` con exactamente cinco creaciones en `centralus`, despliegue `u10-base-dev` `Succeeded` y 9/9 comprobaciones; grupo `rg-motor-predictivo-dev` con Key Vault `kv-mpa-dev-dymtafh7zjbba` (RBAC, sin red pública, vacío) e identidad `id-mpa-dev-github` (credencial federada `github-dev`, Reader solo sobre el grupo); sin secretos ni credenciales persistentes; sin costo fijo; U11 no iniciada · sin commit) · 2026-10-07 (**U10: REGIÓN `centralus`** — la directiva de la suscripción solo permite `northcentralus`, `chilecentral`, `norwayeast`, `centralus` y `mexicocentral`; `westus3` descartada; principal `centralus` y respaldo `northcentralus` (`DT-098`); grupo vacío de `eastus` eliminado por el responsable; `validate` pendiente de ejecución en su Azure CLI; cuota de Azure OpenAI pendiente para U13 · sin commit) · 2026-10-06 (**U10 PREPARADA — DESPLIEGUE PENDIENTE DEL RESPONSABLE** — `DT-098`: Bicep en `infra/azure/` (grupo `rg-motor-predictivo-dev`, Key Vault RBAC privado y vacío, identidad administrada con credencial federada OIDC limitada al entorno `dev` y rol Reader, presupuesto opcional); región `westus3` (Mexico Central sin Azure OpenAI), condicionada a la directiva de regiones de la suscripción; Cost Management no admite Azure for Students: control de gasto manual; validado con Bicep CLI y 7 pruebas estáticas; sin recursos creados todavía · commits en `feature/u10-azure-base`) · 2026-10-06 (**U9 IMPLEMENTADA — PENDIENTE DE REVISIÓN** — `DT-097`: migración `0004` con el esquema `analytics` (13 vistas: carga vigente, seis dimensiones y seis hechos de `docs/11` §3 calculables con 0.4.0) y el rol `analytics_reader` sin `LOGIN`, solo `SELECT` sobre esas vistas; KPI con definición única en el glosario; 25 pruebas de integración nuevas y suite de integración completa en verde (177); sin Power BI ni Azure · sin commit) · 2026-10-06 (**U8 IMPLEMENTADA — PENDIENTE DE REVISIÓN** — `DT-096`: `.github/workflows/ci.yml` con ocho jobs (detección de secretos, `ml`, backend, API, integración con PostgreSQL efímero, generador, frontend y Docker con smoke del sistema completo), permisos `contents: read`, acciones fijadas por SHA, Python 3.11.16, Node 24.21.0 y npm 11.19.0, sin linter de Python y sin Azure; detector de secretos propio con solo la biblioteca estándar; digests de las bases de U7 fijados y pendientes de verificación externa; jobs reproducidos fuera de GitHub con todas las suites en verde; falta la primera ejecución real · sin commit) · 2026-10-06 (**U7 INTEGRADA EN `main`** — PR #13, merge commit `7d4fb50`; el cierre documental de F5c quedó en el PR #12, `f07ea79`) · 2026-10-06 (**U7 IMPLEMENTADA — PENDIENTE DE REVISIÓN** — `DT-094` registra el alcance de cierre de la Etapa 2 (stack completo, unidades U7 a U16, Azure for Students con presupuesto de planificación de 50 USD, Bicep, corpus sintético; cada unidad con su autorización) y `DT-095` U7: imágenes `backend`, `frontend` y `dataset`, `docker compose --profile app` del sistema completo en `127.0.0.1`, sin credenciales; verificada con imágenes base sustitutas (smoke 8/8, 3 990 forecasts y 100 evaluaciones como en U3 y U4), falta la construcción con las imágenes oficiales; sin Azure · sin commit) · 2026-10-06 (**F5c INTEGRADA EN `main`** — PR #11, merge commit `6a1d777` (último commit de F5c: `b4d3ad0`); resultados solo `SYNTHETIC` (informe `results_sha256` `1ce5ea29…`); F5c no promueve ningún modelo: SES sigue siendo el candidato fuerte, no promovido; los resultados de `DT-011` son evidencia de estudio y la estrategia (b) sigue pendiente de decisión; F5d, G2 y G3 siguen sin autorizar; nada validado con datos REAL · solo documentación) · 2026-10-06 (**F5c — AJUSTES DE REVISIÓN** — SES en la tabla de criterios: **cumple todos** con (a); tabla por estrategia de `DT-011` con la media móvil bajo la misma estrategia: SES y TSB cumplen con (b) y (c); sensibilidades de cadencia semanal (TSB 3 973, Croston 4 025, Holt 5 658; huella `28ce7c4f…`) y de umbral de segmento (9 y 11: ningún veredicto cambia); `DT-093` puntos 12 a 14 y nota en `DT-081` (conclusión provisional de `DT-011` y PROPUESTA de (b)); rótulo recomendado de la banda para F7d; informe con huella `1ce5ea29…` en Python 3.11 y 3.13; 129 pruebas de `ml/` · sin promoción, sin push) · 2026-10-06 (**F5c IMPLEMENTADA — PENDIENTE DE REVISIÓN** — `ml/candidates.py` (Holt, Holt-Winters, Croston, SBA, TSB) y `ml/f5c/` (Nivel 1, estudio de `DT-011`, US-055, simulación, tabla de criterios sin recomendación), `python -m ml candidates`; informe `docs/reports/fase5-f5c-candidatos-sintetico.md` (`SYNTHETIC`, huella `df9f8753…` igual en Python 3.11 y 3.13; paridad con F5a y F5b comprobada); ninguno de los cinco candidatos nuevos cumple el criterio de unidades faltantes de Nivel 2 frente a la media móvil 13 *(corregido en la revisión: SES cumple todos los criterios)*; las estrategias (b) y (c) reducen las unidades faltantes; 121 pruebas de `ml/`; sin *holdout*, sin promoción, sin tocar `backend/` ni `frontend/` · rama `feature/ml-f5c`, sin push) · 2026-10-06 (**F5c AUTORIZADA — EN IMPLEMENTACIÓN** — `DT-092` autoriza F5c (Holt, Holt-Winters, Croston, SBA y TSB en `ml/`, estudio de `DT-011`, intervalos de US-055; sin *holdout*, sin promoción, sin tocar `backend/` ni `frontend/`); `DT-093` registra antes de evaluar candidatos los criterios complementarios de G1 (MASE en `L + R`, cortes comparables, tolerancias, banda de sesgo, cobertura, segmentación y estacionalidad, estimadores de `DT-081`, ajuste de modelos, Holt-Winters con 104 semanas y sustitución por el baseline oficial en el simulador) · rama `feature/ml-f5c`, sin push) · 2026-10-05 (**FASE 5 — G1 REGISTRADO** — `DT-089` a `DT-091` `ACEPTADA`, provisionales con datos `SYNTHETIC`: baseline oficial, media móvil de 13 semanas; SES, candidato más fuerte, no promovido; métrica primaria MASE (`DT-021` cerrada); valores provisionales de `DT-079`/`DT-P04`; `docs/05` §20.5 con la tabla de los baselines; F5c y F5d siguen sin autorizar · solo documentación, rama `docs/fase5-g1`, sin push) · 2026-10-05 (**F5b — CIERRE DOCUMENTAL ANTES DEL PUSH** — `DT-080`: decisiones del responsable `ACEPTADA` (órdenes abiertas al primer corte en `expected_on`, vencidas al día siguiente, alternativa `ACTUAL_RECEIPTS` configurable; `is_active = True` con la vigencia decidiendo; observaciones de lead time solo de órdenes reales previas al primer corte; valores provisionales del informe aceptados como tales); nota en `DT-078` (MASE, RMSSE y WAPE ordenan igual por serie-corte por construcción); `CLAUDE.md` §17: F5a y F5b autorizadas · solo documentación, rama `feature/ml-f5b`, sin push) · 2026-10-05 (**F5b IMPLEMENTADA — PENDIENTE DE REVISIÓN** — `ml/simulation/` (`DT-080`, `DT-088`): simulador de Nivel 2 en bucle cerrado de los cuatro baselines (naïve, naïve estacional, media móvil 13 y SES provisional) con U1 sin cambios (`engine_version` 0.1.0 en todas las ramas), del 2024-03-27 al 2025-09-24 con la demanda latente (solo `SYNTHETIC`); 95 series simuladas y 5 sin proveedor preferente activo listadas; métricas por rama × producto × ventana de cada corte de F5a y agregados por rama, segmento y periodo (completo y sin 8 semanas de calentamiento); cruce informativo de `DT-078` (acuerdo serie-corte y Spearman) sin elegir métrica; informe `docs/reports/fase5-f5b-nivel2-sintetico.md` y JSON resumido de 29 639 bytes, `results_sha256` `0a83fe3d…` idéntico con Python 3.11 y 3.13; 82 pruebas de `ml/tests` y suites U1–U6, generador y frontend en verde; `backend/` y `frontend/` sin cambios; sin escrituras en la base; *holdout* sin leer · rama `feature/ml-f5b`, sin push) · 2026-10-05 (**F5a INTEGRADA EN `main` (PR #8, `ea72df5`) · F5b AUTORIZADA — NO IMPLEMENTADA** — `DT-088`: simulador de Nivel 2 aplicado a los cuatro baselines; OD-S1 a OD-S4 `ACEPTADA` en `DT-080` (bucle cerrado; órdenes en `suggested_order_date` que llegan tras el `L` usado por el motor; demanda latente y ventas perdidas con desabasto por día; inventario medio relativo al baseline); pendiente del responsable la discrepancia entre `DT-080` punto 7 y OD-S1 para las líneas abiertas al primer corte · rama `feature/ml-f5b`) · 2026-10-05 (**F5a IMPLEMENTADA — PENDIENTE DE REVISIÓN** — `ml/` con solo la biblioteca estándar (`DT-072` a `DT-076`, `DT-086`): 17 cortes de `DT-075` con guarda del *holdout* en el lector y en cada corte (nada posterior al 2025-09-24; `demand.csv` nunca se abre); baselines de U3 invocados sin reimplementar y SES provisional (`DT-076` punto 7) con la frontera `float` → `Decimal` de `DT-074`; Nivel 1 en `h = 1` y en `L + R` (reglas de U1 y `demand_over_horizon`) con MASE, RMSSE, WAPE, MAE, RMSE, sesgo, cobertura y MAPE informativa, sobre todas las semanas y sin las semanas con desabasto; población por corte a la fecha (`DT-087`: vigencia sin la foto de `is_active`; 100 series hasta el corte 2025-03-26 y 95 después), con la regla literal de U3 comparada en cada ejecución; las 5 series sin proveedor preferente activo, fuera de `L + R` y dentro de `h = 1`; segmentación Syntetos-Boylan provisional (85 suaves, 14 intermitentes y 1 irregular mientras los 5 descontinuados están vigentes); informe `docs/reports/fase5-f5a-backtest-sintetico.md` (`SYNTHETIC`, `results_sha256` `67608e95…`, idéntico con Python 3.11 y 3.13; se versionan el Markdown y un JSON resumido de unos 44 KB, `DT-073`) sin elegir baseline oficial, métrica primaria ni umbrales; 57 pruebas de `ml/tests` y suites U1–U6 en verde; notas en `DT-075` y `DT-079` (cortes solapados, no independientes) y `docs/13` §6 corregido; `backend/` y `frontend/` sin cambios; sin escrituras en la base ni en `model_versions` · rama `feature/ml-f5a`, sin push) · 2026-10-05 (**FASE 5 — CIERRE DOCUMENTAL DE DECISIONES; SOLO F5a AUTORIZADA** (`DT-086`) — `DT-071` a `DT-086` (`docs/05` §20): partición F5a–F5d con puertas G1–G3; `ml/` y solo biblioteca estándar; enmienda acotada de D-12 (`float` solo en `ml/` y en el proveedor de modelo, frontera a `Decimal`); 17 cortes y *holdout* 2025-09-24 de uso único, sin zona muerta; Nivel 1 contra el consumo observado; regla de `DT-021` antes de candidatos y del *holdout*; simulador de Nivel 2 con U1 sin cambios; estudios de `DT-011` [(a), (b), (c)] y `DT-010` en simulación; `model_versions` sin migración `0004`; merge commit. OD-S1 a OD-S4 como `PROPUESTA` del responsable (bucle cerrado, lead time realizado, desabasto diario con unidades faltantes, inventario medio relativo al baseline), pendientes de confirmación; criterio serie-corte en `DT-078`; bloqueo de U1 para comparar (c) y (d) de `DT-010` (`DT-083`). Abiertas: umbrales de segmentación, `DT-P04` (5 % propuesto, no aceptado), estimador de imputación y `DT-021` · solo documentación, sin código ni dependencias, rama `docs/fase5-decisiones`) · 2026-10-05 (**FASE 7 COMPLETADA** — F7a–F7d integradas en `main` con los PR #2 a #5 (merge commits `44280ce`, `198df24`, `1ad2916` y `22f1805`, sin *squash* ni *rebase*); validada en Node 24.21.0 y npm 11.19.0 sobre `main`: lint, `tsc`, Prettier, 148 pruebas y build (aviso de paquete de 774 kB por Recharts); `backend/` sin cambios; desviación registrada en `DT-070`: ramas encadenadas · cierre documental en la rama `docs/fase7-cierre`) · 2026-10-05 (**F7d IMPLEMENTADA — FASE 7 COMPLETA, PENDIENTE DE REVISIÓN Y VALIDACIÓN EN NODE 24** — predicciones e historial (US-075 parcial, RF-009): lista de series primarias con procedencia, banda nominal y aviso `INSUFFICIENT_HISTORY`; en el detalle de producto, gráfico de banda con Recharts 3.10.1 y tabla exacta, e historial de consumo con estadísticos poblacionales solo para ANALYST, PLANNER y ADMIN; revisión visual en Chromium con respuestas reales de la API; 148 pruebas, lint, `tsc`, Prettier y build en verde en el entorno de desarrollo (Node 22; lockfile con npm 11.19.0); `backend/` sin cambios · rama `feature/frontend-forecasts`, encadenada sobre `feature/frontend-recommendations`, sin push) · 2026-10-05 (**F7c IMPLEMENTADA — VALIDACIÓN FINAL EN NODE 24 PENDIENTE** — recomendaciones, desglose y explicación (US-073 sin acciones, US-074, US-048): lista con resultado, identificadores y orden de la API, sin urgencia ni prioridad; detalle con `ProvenancePanel` y avisos, explicación de U6 en sus tres estados y `CalculationBreakdown` en dos niveles (`facts[].display` con unidades; detalles técnicos exactos); evaluación en el detalle de producto; detalle de ejecución para PLANNER y ADMIN; 140 pruebas, lint, `tsc`, Prettier y build en verde en el entorno de desarrollo (Node 22); `backend/` sin cambios · rama `feature/frontend-recommendations`, encadenada sobre `feature/frontend-products`, sin push) · 2026-10-05 (**F7b IMPLEMENTADA — VALIDACIÓN FINAL EN NODE 24 PENDIENTE** — productos e inventario (US-072 sin «bajo el punto de reorden»): lista de productos con búsqueda, estado, categoría por identificador y orden; detalle con maestro, inventario al corte y proveedores; inventario con orden y filtros; `/inventario/:id` como vista propia con líneas abiertas; filtros, orden y paginación en la URL con `page`/`total` del backend; 131 pruebas, lint, `tsc`, Prettier y build en verde en el entorno de desarrollo (Node 22); `backend/` sin cambios · rama `feature/frontend-products`, encadenada sobre `feature/frontend-shell` por decisión del responsable, sin push) · 2026-10-05 (**F7a IMPLEMENTADA Y VALIDADA** — `frontend/` con las versiones exactas de `DT-070` (Vite 8.3.2, React 19.3.0, TypeScript 5.9.3, React Router 8.4.0, TanStack Query 5.104.1; `package-lock.json` versionado): `AppShell` con navegación por rol (`RoleGate`, copia de la matriz de `docs/07` §7.2), rutas estables con filtros y paginación en la URL y las vistas de F7b–F7d como «En construcción»; autenticación local con token `dev-…` validado con `GET /api/v1/me` y guardado solo en memoria (401 → login, 403 en el sitio) tras el puerto `Authenticator`; cliente fino con base `/api` (proxy de Vite), tipos generados con `openapi-typescript` y la tabla de errores de `DT-070` punto 9; formato `es-MX` / `America/Mexico_City` con la regla `display` de `DT-069` sin `float`; lint, `tsc`, Prettier, 121 pruebas (Vitest + Testing Library) y build en verde con Node 24.21.0 y npm 11.19.0; `backend/` sin cambios · rama `feature/frontend-shell`, sin push) · 2026-10-05 (**FASE 7 DOCUMENTALMENTE CERRADA — AUTORIZADA PARA IMPLEMENTACIÓN — NO IMPLEMENTADA** — `DT-070` `ACEPTADA`: interfaz React V1 de solo lectura (US-070, US-072 y US-073 reducidas, US-074, US-048, historial y US-075 nominal; sin dashboard priorizado, riesgos ni acciones por `BR-X03` y V1), autenticación simulada con token `dev-…` en memoria, proxy de `/api`, `es-MX` y `America/Mexico_City`, stack con versiones fijadas (React 19.3.0, TypeScript 5.9.3, Vite 8.3.2, Node 24 LTS ≥ 24.15.0, npm 11.19.0…), partición F7a–F7d; PR previo `feat/u1-supply-engine` → `main` con merge commit; solo documentación: sin código ni dependencias · commit `4752e32`, integrado en `main` con el merge `9012a8c`) · 2026-10-04 (**U6 IMPLEMENTADA Y VALIDADA** — `backend/app/genai/` (solo biblioteca estándar: `ExplanationContext` y `Fact` congelados, `display` de `DT-069`, plantillas `template/1.0.0`, verificador y degradación RS-010) y el endpoint 14 `GET /api/v1/recommendations/{recommendation_id}/explanation`; las 100 evaluaciones reales: 50 `RECOMMEND` y 40 `NO_NEED` `VERIFIED`, 10 `NOT_CALCULABLE` `NOT_APPLICABLE`, ninguna `DEGRADED`; 353 pruebas en la suite por defecto (295 + 58 de `tests/genai`), 56 de la API sin base, 151 de integración (142 + 9 de `test_api_explanation.py`), 146 de U1 y 582 del generador en verde, en local y en Docker; U1–U4 sin cambios · commits `55e0c39` y `5861fda`, publicados) · 2026-10-04 (**U6 DOCUMENTALMENTE CERRADA — AUTORIZADA PARA IMPLEMENTACIÓN — NO IMPLEMENTADA** — `DT-068` (endpoint 14 `GET /api/v1/recommendations/{recommendation_id}/explanation`, cuatro roles, `ExplanationContext` inmutable, `facts[]` cerrado, `unit_of_measure` como metadato, plantillas `string.Template` `template/1.0.0`, `NOT_CALCULABLE` estructurado) y `DT-069` (`display` con 6 decimales `ROUND_HALF_EVEN` sin ceros finales, verificación por igualdad de cadena, degradación RS-010 con HTTP 200 `DEGRADED`) `ACEPTADA`; `DT-047` aceptada para U6; solo documentación: sin código, sin dependencias · incluida en el commit `55e0c39`) · 2026-10-03 (**U5 IMPLEMENTADA Y VALIDADA** — `backend/app/api/` (aplicación, `TokenValidator` de desarrollo, roles, errores, `X-Correlation-ID`, paginación, `provenance`, historia, esquemas y siete routers) y `backend/app/db/read/` (consultas de solo lectura), `.env.example` y grupos `api` y `test` de `backend/pyproject.toml`; 13 endpoints de solo lectura (`/health` y doce bajo `/api/v1`), `python -m app.api` en 127.0.0.1:8000 solo con `APP_ENV=local`; selección de ejecución de `DT-066`, historia de `DT-067` con desviación estándar poblacional; ninguna escritura (filas y `pg_stat_user_tables` sin cambios, SQLSTATE 25006); 295 pruebas por defecto, 56 de la API sin base, 142 de integración (29 nuevas de U5) y 582 del generador en verde, en local y en Docker; U1–U4 y el dataset sin cambios · sin commit) · 2026-10-03 (**U5 DOCUMENTALMENTE CERRADA — AUTORIZADA PARA IMPLEMENTACIÓN — NO IMPLEMENTADA** — `DT-064` (FastAPI 0.141.1, Starlette 1.3.1, Pydantic 2.13.5, uvicorn 0.52.4; pruebas con `httpx2` 2.13.1), `DT-065` (validador de desarrollo, solo `APP_ENV=local`), `DT-066` (ejecución por defecto determinista, `provenance`, errores, `X-Correlation-ID`, solo lectura) y `DT-067` (historia de consumo, desviación estándar poblacional) `ACEPTADA`; `DT-047` aceptada para U5; solo documentación: sin código, sin dependencias instaladas · sin commit) · 2026-10-03 (**U4 IMPLEMENTADA Y VALIDADA** — `backend/app/runs/recommendation.py`, `recommendation_inputs.py`, `recommendation_config.py`, migración `0003` y `python -m app.runs recommend --as-of`; ejecución real con `as_of_date = 2025-12-31` sobre `ds-6c8ad65b4999` (carga 1, forecast 1): `COMPLETED`, 100 candidatos y 100 evaluaciones — 50 `RECOMMEND`, 40 `NO_NEED`, 10 `NOT_CALCULABLE` (los 5 inactivos con `PRODUCT_INACTIVE`, `PRODUCT_OUT_OF_VALIDITY`, `FORECAST_MISSING` y `forecast_id` nulo; los 5 sin proveedor preferente activo con `NO_ACTIVE_PREFERRED_SUPPLIER` y su `forecast_id`); la repetición da `ALREADY_COMPUTED` con el mismo id; el *rollback* deja `FAILED` y 0 recomendaciones y el reintento completa; 295 pruebas por defecto y 113 de integración en verde en el PostgreSQL 16 local y en Docker; generador 582 en verde; U1 y el dataset sin cambios · sin commit) · 2026-10-03 (**U4 DOCUMENTALMENTE CERRADA — AUTORIZADA PARA IMPLEMENTACIÓN — NO IMPLEMENTADA** — `DT-P18` cerrada por `DT-059` y `DT-P21` por `DT-058`; `DT-058` a `DT-063` `ACEPTADA`; `DT-047` aceptada para U4; `DT-P16`, `DT-P11`, `DT-P13` y `DT-P23` siguen abiertas; solo documentación: sin código, sin migración `0003`, sin pruebas de U4, `recommend` no ejecutado · sin commit) · 2026-10-02 (**U3 IMPLEMENTADA Y VALIDADA** — `backend/app/forecasting`, `backend/app/runs` y migración `0002`; ejecución real con `as_of_date = 2025-12-31` sobre `ds-6c8ad65b4999`: `COMPLETED`, 95 productos con forecast, 5 excluidos (`INACTIVE_OR_OUT_OF_VALIDITY`), 3 990 filas y 1 330 primarias de la media móvil, sin respaldos; la repetición da `ALREADY_COMPUTED` sin escribir; un fallo controlado deja `FAILED` y ninguna fila; 248 pruebas por defecto y 75 de integración en verde, en el PostgreSQL 16 local y en Docker; generador 582 en verde; dataset sin cambios · sin commit) · 2026-10-02 (**U3 AUTORIZADA — NO IMPLEMENTADA** — cierre documental de U3: `DT-P17` cerrada por `DT-056`, `DT-046` `ACEPTADA`, `DT-057`, `DT-047` aceptada para U3, pendiente `DT-P23`; solo documentación · sin commit) · 2026-10-01 (**U2 IMPLEMENTADA** — `DT-044` `ACEPTADA` (cantidades `numeric`; `quantity_on_hand ≥ 0` compatible con `BR-X09`) y `DT-055` (PostgreSQL 16, `psycopg` opcional, migraciones SQL, Docker); dataset `ds-6c8ad65b4999` cargado en PostgreSQL con validación previa y posterior, idempotencia y *rollback* probados; 181 pruebas por defecto + 43 de integración en verde; generador 582 en verde y dataset sin cambios · sin commit) · 2026-10-01 (**U1 CERRADA** — auditoría post-implementación sin hallazgos BLOCKER/HIGH/MEDIUM; cantidades racionales y `model_version` ratificadas en `docs/06` §16.12 · sin commit) · 2026-10-01 (**U1 IMPLEMENTADA** — `backend/app/supply_engine`, 146 pruebas en verde; `DT-053` y `DT-054` cerradas; generador 582 en verde y dataset sin cambios · sin commit) · 2026-10-01 (**`DT-P22` cerrada** — `PRODUCT_OUT_OF_VALIDITY` cubre también la vigencia que termina dentro del horizonte; **contrato de U1 cerrado, sin pendientes** · **U1: AUTORIZADA — NO IMPLEMENTADA** · sin código) · 2026-10-01 (**contrato de U1 cerrado** — `DT-048` a `DT-052` `ACEPTADA`, `docs/06` §16.11; pendiente `DT-P22`, que bloquea una sola rama · **U1: AUTORIZADA — NO IMPLEMENTADA** · sin código) · 2026-10-01 (**`DT-P14` cerrada** — estimador poblacional, `INSUFFICIENT_HISTORY` para `n = 0` y evaluación exacta B3; `docs/06` §16.6 · **U1: AUTORIZADA — NO IMPLEMENTADA** · sin código) · 2026-09-30 (**U1 autorizada y detenida antes de escribir código** — `DT-P15` y `DT-P20` cerradas; `DT-P14` abierta en tres puntos sin respaldo documental; `DT-043` y `DT-045` `ACEPTADA`; PyYAML declarado en `data/synthetic/requirements.txt`; rama `feat/u1-supply-engine` creada en la copia local) · 2026-09-30 (**Etapa 1 COMPLETADA · Etapa 2 INICIADA** — arquitectura y fundación del sistema principal: `DT-043` a `DT-047` en `PROPUESTA`, contratos en `docs/03` §16, `docs/04` §9, `docs/05` §19, `docs/06` §16, `docs/07` §7 y `docs/09` §14 · sin código de aplicación · primera unidad propuesta: motor V1) · 2026-09-29 (**Generador 0.4.0 terminado: C8 implementado, C7 y C8 integrados en W1, dataset `ds-6c8ad65b4999` validado y publicado** — `quality_report` 51/51, 0 fallos · 582 pruebas en verde) · 2026-09-29 (**Componente 7 implementado y probado, sin integrar en W1** — `DT-041`, `scenario_assignment` con los 16 ejes · `generator_version` sigue en 0.3.0 y el dataset publicado no cambia · 509 pruebas en verde) · 2026-09-29 (**W1 implementado; dataset completo publicado** — `ds-269a698250db`, `generator_version` 0.3.0, C2 → C3 → C6 → C4 → C5 · 463 pruebas en verde) · 2026-09-28 (**pendientes de C5 cerrados**: prueba permanente de la selección exacta de `CANCELLED` y frase de `DT-039` §13 corregida · W1 detenido antes de implementar, pendiente de dos decisiones · 434 pruebas en verde) · 2026-09-28 (**Componente 6 implementado y probado, sin conectar a `__main__`** · lote C6 → C4 → C5 completo, integración bloqueada por W1 · dataset publicado sin cambios · 430 pruebas en verde) · 2026-09-28 (**Componente 5 implementado y probado, sin conectar a `__main__`**) · 2026-09-27 (**D-01 cerrado: elegibilidad de las `CANCELLED` respecto de `valid_to`, opción A**, `DT-039` §5.2 · C5 sigue sin implementar) · 2026-09-26 (**Componente 4 implementado y probado, sin conectar a `__main__`** — decisiones D-C4-1 (O1), D-C4-2 (P1) y D-C4-3 · C5/C6 sin implementar · dataset publicado sin cambios · 323 pruebas en verde)

---

## Estado actual

> ## ETAPA 1 — DATOS · **COMPLETADA**
>
> Cerrada el 2026-09-29 y cierre autorizado por el responsable el 2026-09-30, con:
>
> | | |
> |---|---|
> | `generator_version` | **0.4.0** |
> | Dataset | **`ds-6c8ad65b4999`**, publicado en `data/synthetic/output/` |
> | Validación | **51/51** comprobaciones del Componente 8, 0 fallos (`quality_report` `PASS`) |
> | Pruebas | **582**, todas en verde |
>
> ## ETAPA 2 — SISTEMA PRINCIPAL · **INICIADA** (2026-09-30)
>
> **Bloque actual: arquitectura y fundación.** Se leyó toda la documentación, se auditó el dataset
> 0.4.0 como fuente y se fijaron los contratos del sistema principal **sin escribir código**. Cinco
> decisiones nuevas, todas `PROPUESTA` hasta que el responsable las apruebe: `DT-043` (estructura y
> puertos locales), `DT-044` (ingesta y modelo físico mínimo), `DT-045` (contrato del motor V1),
> `DT-046` (contrato de forecast) y `DT-047` (orden de implementación) *(después: `DT-043` y `DT-045`
> `ACEPTADA` y `DT-047` aceptada en cuanto a U1, el 2026-09-30)*. Nueve decisiones pendientes
> nuevas, `DT-P13` a `DT-P21`; una de ellas es una **contradicción entre documentos** que no se
> resuelve aquí (`DT-P13`). Detalle en *Etapa 2 — arquitectura y fundación*, más abajo.
>
> **Estado del código de aplicación:** `backend/` (U1 a U6), `frontend/` (Fase 7) e `infra/` (U2, solo PostgreSQL local)
> existen; `ml/` sigue sin crearse. *(Hasta el 2026-10-05 decía que `frontend/` no existía.)* *(Hasta el 2026-10-01 esta línea decía que no existía
> código de aplicación.)*
>
> **FASE 7 — Interfaz React V1: DOCUMENTALMENTE CERRADA · AUTORIZADA PARA IMPLEMENTACIÓN · NO IMPLEMENTADA
> (2026-10-05).** `DT-070` (24 decisiones): interfaz de solo lectura sobre las 14 rutas de la API, sin tocar U1–U6;
> autenticación simulada (token `dev-…` en memoria, `/me`); proxy de `/api` sin CORS; `es-MX` y
> `America/Mexico_City`; React 19.3.0 + TypeScript 5.9.3 + Vite 8.3.2 + React Router 8.4.0 + TanStack Query
> 5.104.1 + Recharts 3.10.1, pruebas con Vitest 5.0.3 y Testing Library, Node 24 LTS ≥ 24.15.0 y npm 11.19.0.
> Fuera: dashboard priorizado, riesgos, acciones, proveedores, administración y asistente. Unidades: F7a (base,
> navegación, autenticación y cliente de API) → F7b (productos e inventario) → F7c (recomendaciones, desglose y
> explicación) → F7d (predicciones e historial). Antes de F7a: PR `feat/u1-supply-engine` → `main` con merge
> commit. Concreción en `docs/08` §12.
>
> **U6 — Explicación por plantilla: IMPLEMENTADA Y VALIDADA (2026-10-04).** *(Hasta la implementación este bloque
> decía «documentalmente cerrada, autorizada para implementación, no implementada».)* `DT-068` (entrega por `GET /api/v1/recommendations/{recommendation_id}/explanation`, el endpoint 14
> —U5 = 13—; Bearer y los cuatro roles del detalle; respuesta `VERIFIED` / `DEGRADED` / `NOT_APPLICABLE`;
> `ExplanationContext` inmutable; `facts[]` cerrado; unidad del producto como metadato; plantillas en
> `backend/app/genai/templates.py`; US-048 aclarada) y `DT-069` (presentación de cifras, verificación y
> degradación RS-010). `genai` solo con la biblioteca estándar, sin LLM, RAG ni Azure, sin recalcular y sin
> prioridad, riesgo ni urgencia (`BR-X03`). Concreción en `docs/09` §14.5; criterios de cierre en §14.6, cumplidos.
> **Implementación (2026-10-04).** `backend/app/genai/` (`types`, `errors`, `facts`, `context`, `templates`,
> `verification`, `explanation`), `backend/app/api/routers/explanations.py`, `explanation_source` en
> `backend/app/db/read/recommendations.py` y modelos aditivos en `schemas.py`; `app.py` registra el router y el
> generador. Impacto en U5: solo aditivo (14 endpoints; las respuestas de los otros trece no cambian; en sus
> pruebas, la lista de endpoints y el test de OpenAPI pasan a 14). Las 100 evaluaciones reales se explican sin
> ninguna `DEGRADED`. Pruebas: 353 pruebas en la suite por defecto (295 + 58 de `tests/genai`), 56 de la API sin base, 151 de integración (142 + 9 de `test_api_explanation.py`), 146 de U1 y 582 del generador en verde, en un PostgreSQL 16 local y en el Docker del responsable. Antes de
> implementar se corrigió en `docs/09` §14.5 la frase de `ZERO_FORECAST_DEMAND` («es cero» → «No se prevé
> demanda»), que incumplía la regla de `DT-069` contra los números escritos con letras.
> **Commits:** `55e0c39` (implementación y documentación de U6) y `5861fda` (regresión permanente de
> `ExplanationError` → 500 `INTERNAL_ERROR`), publicados en `origin/feat/u1-supply-engine`.
>
> **U5 — API V1 de solo lectura: IMPLEMENTADA Y VALIDADA (2026-10-03).** *(Hasta la implementación este
> bloque decía «documentalmente cerrada, autorizada para implementación, no implementada».)* `DT-064` (dependencias), `DT-065` (autenticación local y roles), `DT-066` (contrato de
> lectura: ejecución por defecto, `provenance`, errores, `X-Correlation-ID`, paginación, solo lectura) y
> `DT-067` (historia de consumo con desviación estándar poblacional). Trece endpoints (`docs/07` §7.2 y
> §7.4); criterios de cierre en `docs/07` §7.5, cumplidos.
> **Implementación (2026-10-03).** `backend/app/api/` (`settings`, `auth`, `errors`, `correlation`, `pagination`,
> `provenance`, `history`, `schemas`, `app`, `__main__` y `routers/`) y `backend/app/db/read/` (conexión
> `read_only` y consultas por recurso); `.env.example` con identidades ficticias; grupos opcionales `api`
> (FastAPI 0.141.1, Starlette 1.3.1, Pydantic 2.13.5, uvicorn 0.52.4) y `test` (`httpx2` 2.13.1, sin `httpx`).
> U1–U4, sus migraciones y el dataset no cambian. Pruebas: 295 en la suite por defecto (sin dependencias
> opcionales), 56 de la API sin base (`tests/api`), 142 de integración (U2 43, U3 32, U4 38, U5 29) y 582 del
> generador, en un PostgreSQL 16 local y en el Docker del responsable; recorrido manual de los 13 endpoints
> con 401, 403, 404, 405 y 422. Los estadísticos de la historia son exactamente los de `DT-067`.
>
> **U4 — Ejecución de recomendaciones: IMPLEMENTADA Y VALIDADA (2026-10-03).** *(Hasta la implementación
> este bloque decía «documentalmente cerrada, autorizada para implementación, no implementada».)* `DT-058` (un forecast por corte; `recommend --as-of t` consume el forecast
> con el mismo `as_of_date` y no lo lanza; cierra `DT-P21`), `DT-059` (una fila inmutable por evaluación
> para `RECOMMEND`, `NO_NEED` y `NOT_CALCULABLE`; sin `status`, `resolved_*` ni `urgency`; representación
> exacta; `input_sha256` sobre la representación JSON canónica y normalizada de `EvaluationInput`; cierra
> `DT-P18`), `DT-060` (`forecast_id` = fila h=1, ancla de la serie primaria de 14 semanas), `DT-061`
> (ejecución de forecast `COMPLETED` con el mismo corte, la misma carga y la configuración de U3 vigente),
> `DT-062` (`ENGINE_VERSION` de U1, `policy_set = V1_PROVISIONAL`, idempotencia, bloqueo, *rollback*) y
> `DT-063` (solo cargas `SYNTHETIC`; `DT-P16` sigue abierta). Detalle: `docs/04` §9.11 y `docs/06` §16.13;
> criterios de cierre en `docs/06` §16.13.4, cumplidos.
> **Implementación (2026-10-03).** `backend/app/runs/recommendation_inputs.py` (adaptador puro, sin SQL),
> `recommendation_config.py` (representación, `input_sha256`, `config_sha256`), `recommendation.py`
> (orquestación, idempotencia, bloqueo, *rollback*), `backend/db/migrations/0003_recommendation_tables.sql` y el
> subcomando `python -m app.runs recommend --as-of`. U1 no se modificó; U2/U3 solo recibieron ampliaciones
> aditivas (`runs/__main__.py`, `runs/__init__.py` y tres pruebas de esquema y migraciones). Ejecución real con
> `as_of_date = 2025-12-31`: `COMPLETED`, 100 evaluaciones (50 `RECOMMEND`, 40 `NO_NEED`, 10 `NOT_CALCULABLE`, las
> 10 esperadas); marcas: `ORDER_MULTIPLE_ROUNDING` 46, `MOQ_APPLIED` 8, `UNCOUNTED_TRANSIT` 8,
> `OVERDUE_ORDERS_EXCLUDED` 6; ningún `LEAD_TIME_CAPPED` ni `LEAD_TIME_AGREED_FALLBACK`. Validado en un
> PostgreSQL 16 local y en el Docker del responsable (misma `input_sha256` en ambos). Pruebas: 295 en la suite
> por defecto (146 U1, 35 ingesta, 60 forecasting, 54 runs) y 113 de integración (43 U2 + 32 U3 + 38 U4).
>
> **U3 — ForecastProvider + baselines + forecasts persistidos: IMPLEMENTADA Y VALIDADA (2026-10-02).** `DT-P17` queda cerrada por `DT-056`:
> naïve, naïve estacional (52 semanas) y media móvil (`k = 13`), con 14 semanas ancladas en
> `as_of_date + 1`; intervalo por cuantiles empíricos nearest-rank 10/90 del error histórico a cada
> horizonte, con `confidence_level = 0.80` como nivel **nominal** (no calibrado; la cobertura se valida
> en la Fase 5) y un mínimo **operacional** de 11 errores por horizonte; mínimos de 25, 37 y 63 semanas;
> la media móvil es la referencia **provisional** de V1, elección operativa y reversible, no por
> desempeño; respaldo media móvil → naïve → sin forecast; consumo observado bruto como proxy durante el
> desabasto, sin corrección (`DT-011` sigue abierta); catálogo de productos activos y vigentes en
> `as_of_date` (U1 valida después la vigencia sobre su horizonte); `Decimal` de 6 decimales, nunca
> `float`. `DT-046` pasa a `ACEPTADA` (proveedor puro; `runs` lee y persiste) y `DT-057` fija
> `model_versions`, `calculation_runs` y `forecasts`, la idempotencia (`ALREADY_COMPUTED`) y la ejecución
> `python -m app.runs forecast --as-of`. Nueva pendiente `DT-P23`. Detalle: `docs/05` §19.8 y §19.9.
> **Implementación (2026-10-02).** `backend/app/forecasting/` (puro, solo biblioteca estándar),
> `backend/app/runs/` (`python -m app.runs forecast --as-of`) y `backend/db/migrations/0002_forecast_tables.sql`;
> ejecución real con `as_of_date = 2025-12-31` sobre `ds-6c8ad65b4999`: `COMPLETED`, 95 productos con forecast, 5 excluidos (`INACTIVE_OR_OUT_OF_VALIDITY`), 3 990 filas y 1 330 primarias de la media móvil, sin respaldos; la repetición da `ALREADY_COMPUTED` sin escribir; un fallo controlado deja `FAILED` y ninguna fila.
> Validado en el PostgreSQL 16 local y en el Docker del responsable. Pruebas: 248 en la suite por defecto
> (146 U1, 35 ingesta, 60 forecasting, 7 runs) y 75 de integración (43 U2 + 32 U3). Detalle: `docs/05`
> §19.10. *(Hasta la implementación este bloque decía «autorizada, no implementada».)*
>
> **U2 — PostgreSQL + ingesta del 0.4.0: IMPLEMENTADA (2026-10-01).** `DT-044` pasa a `ACEPTADA`
> (cantidades en `numeric` sin precisión fija; `quantity_on_hand ≥ 0` verificado compatible con `BR-X09`,
> cerrada para V1 por `V1-13`) y `DT-055` fija el entorno: PostgreSQL 16, `psycopg[binary]==3.3.6` como
> dependencia **opcional** (`backend[db]`; U1 sigue sin dependencias), migraciones SQL en
> `backend/db/migrations/` con ejecutor propio y `infra/docker-compose.yml`. Esquema: las doce tablas del
> dataset y `data_loads`, nada más. La ingesta (`python -m app.ingestion`) bloquea, detecta, valida sin
> tocar la base, mapea acumulando errores, carga en una transacción, valida dentro de ella y registra
> `data_loads`. **Primera carga real:** `COMPLETED`, 321 043 filas en ~10 s, las seis invariantes en verde;
> la repetición da `ALREADY_LOADED` sin escribir nada. Pruebas: `backend/tests/ingestion` (35, sin base) y
> `backend/tests/db` (43, PostgreSQL real). Detalle: `docs/04` §9.9. **U2 está validada contra PostgreSQL 16
> real y contra el entorno Docker** de `infra/docker-compose.yml` en la máquina del responsable
> (2026-10-01): contenedor `postgres:16-alpine` (16.15) `healthy`, migraciones, primera carga `COMPLETED`,
> repetición `ALREADY_LOADED`, integración 43/43 y suite por defecto 181/181. *(Hasta ese cierre el entorno
> Docker figuraba como verificación pendiente.)*
>
> **U1 — motor V1: IMPLEMENTADA (2026-10-01).** `backend/app/supply_engine` (`contract`, `validation`,
> `exact`, `rules`, `engine`), solo biblioteca estándar, Python ≥ 3.11; 146 pruebas en
> `backend/tests/supply_engine` (`cd backend && python3 -m unittest discover -s tests -t .`). Antes de
> codificar se cerraron `DT-053` (frontera de la salida parcial) y `DT-054` (sin monotonía global de `S`
> frente a `L`). Interpretaciones de implementación ratificadas el 2026-10-01 (`docs/06` §16.12). *(Hasta el
> 2026-10-01 este bloque decía «AUTORIZADA — NO IMPLEMENTADA».)* Sus tres decisiones previas están cerradas:
> `DT-P15` (bordes temporales; la decisión es `as_of_date`, no `as_of_date + 1`, como dice `DT-031`) y
> `DT-P20` (rigen las fórmulas V1 en los tres casos límite), el 2026-09-30; y **`DT-P14`**, el
> 2026-10-01: `σ_H` con estimador poblacional, `n = 0` → `INSUFFICIENT_HISTORY`, `n = 1` → `σ_H = 0`,
> y evaluación exacta **B3** —decisiones por comparación algebraica exacta, sin tolerancias; 28 cifras
> significativas con `ROUND_HALF_EVEN` solo para informar— (`docs/06` §16.6). Ninguna fórmula V1
> cambia. *(Hasta el 2026-10-01 este bloque decía que U1 estaba detenida por `DT-P14`.)*
>
> **Contrato de U1 cerrado el 2026-10-01** (`docs/06` §16.11, `docs/15` v1.21): `DT-048` (cobertura del
> forecast), `DT-049` (vigencia; el horizonte que cruza `valid_to` da `NOT_CALCULABLE`), `DT-050` (orden de
> las observaciones de lead time; aclaración A-1, techo de 90 con cualquier procedencia), `DT-051`
> (tipos, `Fraction`/`Decimal`, `missing_policy_parameters`, orden de razones y marcas, salida parcial,
> `engine_version = "0.1.0"`; aclaración A-2, sin `abc_class`) y `DT-052` (`InvalidInputError`; `on_hand < 0`
> sigue siendo `NEGATIVE_ON_HAND`). **`DT-P22` cerrada el mismo día** (`docs/15` v1.22):
> `PRODUCT_OUT_OF_VALIDITY` significa que el producto no es válido durante todo el periodo requerido
> (de `as_of_date` a `as_of_date + H`), de modo que el horizonte que cruza `valid_to` da `NOT_CALCULABLE`
> con esa razón, sin razón nueva y sin recortar `H`. **El contrato de U1 no tiene decisiones pendientes.**

> ## ETAPA 1 — DATOS · registro de la etapa *(cerrada; el texto que sigue es su historial y no se reescribe)*
>
> La **Etapa 0 está superada** como condición para continuar: documentación base creada (2026-09-03),
> auditada y corregida (revisión 0.1, 2026-09-04, *aprobada con observaciones*).
>
> El responsable del proyecto **autorizó explícitamente el inicio de la Etapa 1 el 2026-09-14**.
>
> **Bloque actual: W1 — publicación del dataset**, **implementado el 2026-09-29** (ver *W1* más
> abajo). Los Componentes 1 a 6 están implementados y conectados: `python3 -m data.synthetic.generator`
> ejecuta C2 → C3 → C6 → C4 → C5 en un workspace temporal y promociona el resultado a `output/`.
> **Generador terminado (2026-09-29).** Los Componentes 1 a 8 y W1 están implementados y
> conectados: `python3 -m data.synthetic.generator` ejecuta C2 → C3 → C6 → C4 → C5 → C7 → C8 →
> verify → promote. **Dataset publicado y validado:** `ds-6c8ad65b4999`, `generator_version`
> **0.4.0**, `quality_report` con 51 de 51 comprobaciones y 0 fallos. **Siguiente:** cierre de la
> Fase 1 y autorización de la siguiente fase, a decidir por el responsable. *(El texto de este párrafo decía «Componente
> actual: 1» y había quedado desfasado; se corrige aquí, no se reescribe el historial que sigue.)*
>
> **Auditoría de escenarios: resuelta** (2026-09-17). Se adopta la separación en tres niveles de
> `DT-023` y el enum `Scenario` pasa de 14 a **16 valores**.
>
> **Auditoría del Componente 1: corregida** (2026-09-17). La auditoría de `DT-023`, `config.py`,
> `dataset_config.yaml`, `test_config.py` y este archivo resultó **NO APROBADA** por tres defectos
> críticos: un recuento incorrecto de la matriz de §25 (se afirmaba 11 + 9 + 5 = 26, que suma 25),
> `_parse_scale` interrumpía la acumulación de problemas en el primer error de tipo, y `validate()`
> no comprobaba duplicados ni orden canónico, de modo que un objeto podía validarse y aun así
> producir un `to_dict()` que `from_mapping()` rechazaba. **Los defectos están corregidos** y las
> pruebas pasan (54). La clasificación conceptual A/B/C **no se modificó**.
>
> **Auditoría del Componente 2: realizada** (2026-09-17). Auditoría documental y técnica, de solo
> lectura, sobre las cinco entidades maestras (`Category`, `Product`, `Supplier`, `ProductSupplier`,
> `Location`). Resultado: la **estructura** estaba definida, pero faltaban siete definiciones —**B-1 a
> B-7**— sin las cuales el componente no podía implementarse sin inventar.
>
> **Bloqueantes B-1 a B-7: resueltos documentalmente** (2026-09-18). Siete decisiones nuevas,
> `DT-024` a `DT-030`, cierran el formato de salida, la marca de origen, la vigencia de `Product`, la
> metadata de generación, las políticas de generación sintética y el determinismo.
> **El Componente 2 sigue SIN implementar**: no existe ningún generador, ningún CSV y ningún dataset.
>
> **Auditoría de consistencia post-decisiones: NO APTA todavía** (2026-09-18). Cuatro revisiones
> independientes sobre `DT-024`–`DT-030` encontraron **seis defectos bloqueantes** en decisiones ya
> marcadas `ACEPTADA` — entre ellos una contradicción interna en `DT-027` sobre la semántica del
> intervalo de vigencia, una garantía falsa de `DT-028` («ningún proveedor queda huérfano»), un
> algoritmo de `DT-028` con dos lecturas de las que una aborta, y una sub-semilla de `DT-030` que
> depende de un identificador que no estaba definido en ninguna parte. **Los seis están corregidos.**
> Quedan **tres cuestiones abiertas que requieren decisión del responsable** y que impiden dar el
> visto bueno: ver *Auditoría de consistencia* más abajo.
>
> **Diseño de los Componentes 4, 5 y 6: cerrado documentalmente** (2026-09-24). El responsable aprobó
> la arquitectura de ejecución **C6 → C4 → C5**, los parámetros sintéticos de inventario
> (`W = 28`, `M = 7`, `C = 21`, factores 750/1000/1500 ‰, mezcla 30/40/30), los perfiles de proveedor
> y siete decisiones de contrato. Quedan registrados en **`DT-036`** y **`DT-037`**. Se **enmienda
> `DT-027`** (restricción 3) para admitir que una orden emitida dentro de la vigencia complete su
> ciclo después de `valid_to`, y se **cierra el pendiente de `data_origin`** que `DT-026` arrastraba
> desde el 2026-09-18. **Los tres componentes siguen SIN implementar**: no existe
> `generator/inventory.py`, ni `supplier_behaviour.py`, ni `orders.py`, ni sus pruebas.
>
> **Auditoría pre-implementación de C4/C5/C6: realizada y resuelta** (2026-09-24). Dos revisiones
> independientes en contexto limpio, con cada hallazgo verificado después contra el repositorio y el
> dataset. Resultado inicial **NO APROBABLE**: ocho bloqueantes, el principal que **los contratos de
> salida de C4 y C5 no existían en el repositorio** —§41.3 de la especificación los declaraba
> pendientes— y que `DT-036` citaba `V1-06` **sin su guarda `raw_need ≤ 0`**, con 9 pares del dataset
> verificados que alcanzan demanda reciente cero. El responsable resolvió las siete decisiones
> abiertas (D-01 a D-07) el mismo día. **Los ocho bloqueantes están cerrados** con `DT-038`, `DT-039`
> y correcciones a `DT-036` y `DT-037`. Los tres componentes siguen **sin implementar**.
>
> **D-01 cerrado documentalmente** (2026-09-24 a 2026-09-26). Tres rondas de análisis sobre las
> órdenes `CANCELLED` sintéticas desembocaron en seis decisiones del responsable: **A2** (el
> Componente 5 forma `order_number` para todas las órdenes; el Componente 4 no conoce la política de
> cancelaciones), **B2** (sin ninguna orden elegible la ejecución falla), `ORDERS_CANCELLED_PERMILLE =
> 20`, `ORDERS_CANCELLED_CLOSE_LAG_DAYS = 1` sin recorte de `closed_at`, `expected_at` copiado de C4,
> y una **regla general de `generator_version`** basada en el artefacto publicado, ya no en una lista
> de parámetros (`DT-033`). El análisis de B2 destapó que **la escritura progresiva del generador
> impedía cumplirla**: C2, C3 y C4 escribían en `output/` antes de que C5 pudiera fallar, dejando un
> dataset parcial o mezclado. Se resuelve con **W1** (`DT-040`): cada ejecución trabaja en su propio
> workspace y `output/` solo cambia por promoción al final. Se corrigieron además seis frases que
> atribuían al Componente 4 **todos** los identificadores, un error introducido en la sesión del
> 2026-09-24. **Pendiente de confirmación:** dos detalles de operación de `DT-040` (qué hacer con el
> dataset sustituido y con el workspace de una ejecución fallida). **C4, C5 y C6 siguen sin
> implementar.**
>
> **D-01 — elegibilidad de las `CANCELLED` cerrada** (2026-09-27). La auditoría previa a C5 encontró
> que una orden gemela cuya plantilla se emitió el propio día `valid_to` se cerraría al día siguiente,
> fuera de la vigencia que exige la restricción 3 de `DT-027`. El responsable eligió la **opción A**:
> una orden causal solo es elegible si su cierre previsto (`issued_on + 1 día`) cumple `< end_date`
> **y** `<= valid_to` (o `valid_to` nulo). El filtrado ocurre antes de calcular `K` y de seleccionar;
> B2 sigue vigente; `closed_at` no se recorta; **`DT-027` no cambia**. Autoridad: `DT-039` §5.2.
> **C5 sigue sin implementar.**
>
> **Componente 4 implementado y probado** (2026-09-26), con tres decisiones del responsable tomadas al
> autorizarlo: **D-C4-1 = O1** (la entrega partida acota `q1` a `Q_final − 1`, `DT-037` §3 enmendado),
> **D-C4-2 = P1** (la ventana de 28 días nunca se acorta: precondiciones P-C4-2 y P-C4-3, `DT-038`
> §16) y **D-C4-3** (lead time acordado, sin `V1-09` ni `R_v1`; `M` solo en la apertura; disparo
> diario). **No está conectado a `__main__`**: consume perfiles del Componente 6 y entrega órdenes al
> Componente 5, y ninguno existe. `output/` y `generator_version` (0.2.0) **no cambian**.
>
> Las observaciones abiertas de la Etapa 0.1 siguen abiertas y son **externas al equipo técnico**:
> doce parámetros del negocio y dos supuestos de alto riesgo sin confirmar. **Ninguna de ellas bloquea
> la Fase 1**, porque el generador de datos sintéticos no depende de parámetros de política.
>
> Detalle de la auditoría en `docs/reports/etapa-0-1-reporte.md`.

## Progreso

| Etapa / Fase | Estado |
|---|---|
| **Fase 0 — Preparación** | ✅ Superada (documentada, auditada y aprobada con observaciones) |
| **Fase 1 — Datos** | ✅ **Completada** (2026-09-29) — generador 0.4.0, `ds-6c8ad65b4999`, 51/51, 582 pruebas. La ingesta pasa a la Etapa 2 (U2) |
| **Etapa 2 — Sistema principal** | 🟡 **En curso** (iniciada el 2026-09-30) — U1–U6 y la Fase 7 integradas en `main`; F5a–F5c integradas; alcance de cierre por unidades U7 a U16 en `DT-094`; U7 implementada, pendiente de revisión |
| Fase 2 — PostgreSQL | 🟡 **En curso** — **U2 implementada y validada** (2026-10-01): esquema, migraciones `0001` a `0003`, carga del dataset 0.4.0 y reconciliación del inventario con los movimientos. Pendientes de la fase: vistas analíticas para Power BI y fotografía diaria de inventario *(hasta el 2026-10-05 decía «No iniciada — diseñada»)* |
| Fase 3 — FastAPI | 🟡 Iniciada — **U5 implementada y validada el 2026-10-03**: API V1 de solo lectura con autenticación local y roles (`docs/07` §7.4 y §7.5, `DT-064` a `DT-067`); Entra ID, CORS, límite de tasa y escrituras quedan fuera de U5 |
| Fase 4 — Motor de abastecimiento | 🟡 **En curso** (pendientes: riesgos, por `BR-X03`, y métricas de proveedor, US-047) — contrato aceptado (`docs/06` §16, `DT-045`); **U1 implementada** (2026-10-01; contrato `DT-048` a `DT-054` y `DT-P22`; 146 pruebas). Persistencia y batch en U4: **implementada y validada el 2026-10-03** (`DT-058` a `DT-063`; ejecución real 2025-12-31 con 100 evaluaciones); endpoints en U5; explicación por plantilla en U6 (**implementada y validada el 2026-10-04**; `DT-068`, `DT-069`) *(hasta el 2026-10-05 decía «No iniciada»)* |
| Fase 5 — Machine Learning | 🟡 **F5c integrada en `main`** (2026-10-06: PR #11, merge commit `6a1d777`; `DT-092`, criterios en `DT-093`, resultados `SYNTHETIC` en `docs/05` §20.7 y `docs/reports/fase5-f5c-candidatos-sintetico.md`; sin promoción; F5d, G2 y G3 sin autorizar) — *antes:* 🟡 **F5c implementada, pendiente de revisión** (rama `feature/ml-f5c`) — *antes:* 🟡 **G1 registrado; F5c pendiente de autorización** (2026-10-05: `DT-089` a `DT-091`, `docs/05` §20.5) — F5a y F5b en `main` (PR #8 y #9); baseline oficial media móvil 13, métrica MASE, valores de aceptación provisionales *(antes: 🟡 **F5a integrada en `main`** (PR #8, `ea72df5`; informe `docs/reports/fase5-f5a-backtest-sintetico.md`); **F5b implementada, pendiente de revisión** (`DT-088`, rama `feature/ml-f5b`; informe `docs/reports/fase5-f5b-nivel2-sintetico.md`) — `DT-071` a `DT-088`, `docs/05` §20; F5c–F5d pendientes de G1 y de las condiciones de `docs/05` §20.4)* |
| Fase 6 — Azure Machine Learning | ⬜ No iniciada |
| Fase 7 — React | ✅ **Completada** (2026-10-05) — F7a–F7d integradas en `main` (PR #2 a #5, `22f1805`) y validadas en Node 24 (148 pruebas); notas de implementación en `DT-070` y `docs/08` §12.1 |
| Fase 8 — Microsoft Entra ID | ⬜ No iniciada |
| Fase 9 — Azure AI Search | ⬜ No iniciada |
| Fase 10 — Azure OpenAI | ⬜ No iniciada |
| Fase 11 — Power BI | 🟡 **U9 (datos analíticos) implementada — pendiente de revisión** (2026-10-06, `DT-097`, `docs/11` §10): esquema `analytics`, 13 vistas y rol `analytics_reader`; Power BI (U16) sin iniciar |
| Fase 12 — Docker | 🟡 **U7 integrada en `main`** (2026-10-06, PR #13; `DT-095`, `docs/12` §3.4): sistema completo con `docker compose -f infra/docker-compose.yml --profile app up --build -d`; verificado con imágenes base sustitutas; bases fijadas por digest (U8), pendientes de verificación externa en el job `docker` de CI |
| Fase 13 — GitHub Actions | 🟡 **U8 (CI) implementada — pendiente de revisión** (2026-10-06, `DT-096`, `docs/12` §4.5): ocho jobs sin Azure; falta la primera ejecución real en GitHub. Despliegue y OIDC, en U12 |
| Fase 14 — QA | ⬜ No iniciada |
| Fase 15 — Documentación y entrega | ⬜ No iniciada |

### Criterios de finalización de la Etapa 0

| Criterio | Estado |
|---|---|
| Estructura documental | ✅ |
| `CLAUDE.md` | ✅ |
| `AGENTS.md` | ✅ |
| Requisitos documentados | ✅ `docs/01` |
| Propuesta técnica | ✅ `docs/02` |
| Arquitectura | ✅ `docs/03` |
| Modelo de datos conceptual | ✅ `docs/04` |
| Estrategia de ML | ✅ `docs/05` |
| Motor de abastecimiento | ✅ `docs/06` |
| API diseñada | ✅ `docs/07` |
| Frontend diseñado | ✅ `docs/08` |
| IA generativa | ✅ `docs/09` |
| Seguridad | ✅ `docs/10` |
| Power BI planificado | ✅ `docs/11` |
| DevOps planificado | ✅ `docs/12` |
| Testing planificado | ✅ `docs/13` |
| Mantenimiento planificado | ✅ `docs/14` |
| Decisiones técnicas registradas | ✅ `docs/15` |
| Glosario | ✅ `knowledge/glossary.md` |
| Supuestos registrados | ✅ `knowledge/assumptions.md` |
| Reglas de negocio documentadas | ✅ `knowledge/business-rules.md` |
| Roadmap | ✅ `project/roadmap.md` |
| Backlog | ✅ `project/backlog.md` |
| Estado del proyecto | ✅ este archivo |
| `README.md` actualizado | ✅ |

**25 criterios verificados.** Reporte de cierre en `docs/reports/etapa-0-reporte.md`.

### Criterios de la revisión 0.1

Los veinte criterios de finalización de la auditoría se cumplen. Detalle en
`docs/reports/etapa-0-1-reporte.md` §7. Resumen de lo corregido: quince problemas encontrados
—cinco de severidad crítica—, treinta y cinco correcciones aplicadas, cuatro decisiones técnicas
nuevas (`DT-019` a `DT-022`), tres historias de usuario nuevas, un requisito nuevo derivado
(`RML-013`) y dos supuestos nuevos.

### Fase 1 — Datos · avance por componente

| # | Componente | Estado |
|---|---|---|
| 1 | **`DatasetConfig`** — contrato de configuración del generador | ✅ Implementado y probado |
| 2 | Catalog Generator | ✅ **Implementado y probado** (2026-09-21) — cinco entidades maestras + `manifest.json` |
| 3 | Demand Generator | ✅ **Implementado y probado** (2026-09-23) — `demand.csv`, demanda **latente** |
| 4 | Inventory Simulator | ✅ **Implementado y probado** (2026-09-26, `DT-036`, `DT-038`) — identificador `inventory`. **Dueño del inventario, los desabastos y `consumption.csv`**; calcula además las órdenes **causales** y sus recepciones y les asigna los identificadores. Conectado a través de W1 (2026-09-29) |
| 5 | Purchase Order Generator | ✅ **Implementado y probado** (2026-09-28, `DT-039`), conectado a través de W1 (2026-09-29) — identificador `orders`. Materializa `purchase_orders.csv`, `purchase_order_items.csv` y `purchase_order_receipts.csv` **sin recalcular nada**; añade las órdenes `CANCELLED` sintéticas, numera solo esas filas y forma el `order_number` de todas |
| 6 | Supplier Behaviour Generator | ✅ **Implementado y probado** (2026-09-28, `DT-037`), conectado a través de W1 (2026-09-29) — identificador `supplier_behaviour`. **No escribe archivos**; entrega perfiles en memoria a C4 |
| 7 | Scenario Assignment | ✅ **Implementado y probado** (2026-09-29, `DT-041`) — identificador `scenarios`. Escribe **solo** `manifest.scenario_assignment` y su entrada en `components`; integrado en W1 con C8 (2026-09-29) |
| 8 | Dataset Validator + informe de calidad | ✅ **Implementado y probado** (2026-09-29, `DT-042`) — identificador `validator`. 51 comprobaciones sobre el workspace; escribe `manifest.quality_report` solo si todas pasan |

**Terminado en el Componente 1:**

- `data/synthetic/config/dataset_config.yaml` — configuración explícita con semilla, ventana
  temporal, escala del catálogo y los **16 valores del enum `Scenario`** requeridos como cobertura
  (13 corresponden a situaciones de §25 y tres a otras secciones, `DT-023`).
- `data/synthetic/config/config.py` — `load_config()` → `DatasetConfig` tipado → `validate()`.
  Objeto congelado y normalizado, que será la entrada de todos los componentes posteriores.
  El enum `Scenario` es un conjunto **cerrado de 16 valores**.
- `data/synthetic/tests/test_config.py` — **54 pruebas**, todas en verde.

**Pendiente en la Fase 1:** los componentes 3 a 8, el histórico del dataset, el proceso de ingesta
con marca de origen, el informe de calidad y los umbrales de aceptación del modelo (`DT-P04`).

**Siguiente componente autorizado:** ninguno todavía. El Componente 2 (*Catalog Generator*) requiere
autorización explícita, como cada componente de esta fase. Lo que ya está preparado para él:

- `DT-023` — la frontera entre los ejes del enum y los Niveles B y C, de modo que el Componente 2 no
  contamine las entidades maestras con información que pertenece al histórico.
- `DT-024` a `DT-030` — el contrato de salida, la marca de origen, la vigencia de `Product`, la
  metadata de generación, las políticas de generación sintética y el determinismo.

**El Componente 2 no está implementado.** No existe generador, ni CSV, ni dataset generado.

**Estado del código de aplicación:** no existe, y es lo correcto. El único código del repositorio es
el generador de datos sintéticos. Backend, frontend, base de datos, ML, Azure, contenedores y CI/CD
pertenecen a fases posteriores.

## Decisiones recientes

Registradas en `docs/15-decisiones-tecnicas.md`. Las de mayor impacto:

| ID | Decisión | Estado |
|---|---|---|
| `DT-001` | Separación estricta entre predicción ML, reglas de negocio e IA generativa | `ACEPTADA` |
| `DT-002` | Monolito modular en el backend, no microservicios | `ACEPTADA` |
| `DT-003` | Dependencias de Azure encapsuladas tras interfaces propias | `ACEPTADA` |
| `DT-006` | Histórico inmutable (append-only) | `ACEPTADA` |
| `DT-007` | Sin generación de SQL libre por el LLM | `ACEPTADA` |
| `DT-009` | Progresión incremental de modelos con criterio de parada | `ACEPTADA` |
| `DT-015` | Sin promoción automática de modelos a producción | `ACEPTADA` |
| `DT-016` | El sistema recomienda; no ejecuta compras | `ACEPTADA` |
| `DT-018` | Explicación por plantilla determinística antes que por LLM | `ACEPTADA` |
| `DT-020` | Evaluación en dos niveles y comparación end-to-end baseline vs. ML | `ACEPTADA` *(0.1)* |
| `DT-008`, `DT-012`, `DT-013`, `DT-014`, `DT-022` | Granularidad, tránsito efectivo, ubicación de carpetas, modo de Power BI, almacén de secretos | `PROPUESTA` |
| `DT-010` | **Metodología del stock de seguridad** | `PENDIENTE DE VALIDACIÓN` *(retrocedió desde `PROPUESTA` en la revisión 0.1)* |
| `DT-019` | Conversión entre pronóstico semanal y lead time en días | `PENDIENTE DE VALIDACIÓN` *(0.1)* |
| `DT-021` | Métrica primaria de pronóstico | `PENDIENTE` *(0.1)*; el descarte de MAPE sí es `ACEPTADA` |
| `DT-011` | Tratamiento de la demanda censurada | `PENDIENTE` (el marcado del dato sí está aceptado) |
| `DT-023` | Clasificación en tres niveles de las 26 situaciones de §25 | `ACEPTADA` |
| `DT-024` | Formato de salida: un CSV por entidad | `ACEPTADA` *(2026-09-18)* |
| `DT-025` | `manifest.json`: la metadata de generación vive fuera de las entidades | `ACEPTADA` *(2026-09-18)* |
| `DT-026` | `data_origin` en las cinco entidades maestras | `ACEPTADA` *(2026-09-18)* |
| `DT-027` | Vigencia de `Product`: `valid_from` y `valid_to` | `ACEPTADA` *(2026-09-18)* |
| `DT-028` | Políticas de generación sintética del Componente 2 | `ACEPTADA` *(2026-09-18)* |
| `DT-029` | Alcance del Componente 2: lo que no genera | `ACEPTADA` *(2026-09-18)* |
| `DT-030` | Determinismo por sub-semillas derivadas de la semilla común | `ACEPTADA` *(2026-09-18)* |
| `DT-023` | **Clasificación en tres niveles de las situaciones de §25**; enum `Scenario` de 14 a 16 | `ACEPTADA` *(2026-09-17)* |

**Decisiones de implementación del Componente 1** (ninguna requiere ADR: son librerías dentro de un
lenguaje ya adoptado, conforme a `CLAUDE.md` §5):

- **PyYAML** como única dependencia externa del generador. La configuración debe ser un `.yaml` y la
  biblioteca estándar no parsea YAML; no hay alternativa más simple.
- **Biblioteca estándar para la validación**, no Pydantic. Pydantic está en el stack por FastAPI, pero
  acoplar el generador de datos a la capa de API no aporta nada aquí y añadiría una dependencia que
  esta tarea no necesita (`CLAUDE.md` §6, regla 2).
- **`unittest` para las pruebas**, no pytest: está en la biblioteca estándar y no añade dependencias.
  Revisable cuando exista más código que probar.

**Decisión de secuenciación destacada:** el motor de abastecimiento (Fase 4) va **antes** que el
Machine Learning (Fase 5). El motor consume un forecast, y ese forecast puede ser un baseline. Así el
sistema entrega valor auditable desde temprano y el modelo, cuando llegue, solo mejora una entrada de
un motor ya probado.

## Problemas conocidos

| # | Problema | Impacto | Acción |
|---|---|---|---|
| 1 | **No hay parámetros de política del negocio** (nivel de servicio, política de revisión, umbrales de riesgo) | **Alto** — bloquea la parametrización de la Fase 4 | Solicitar al negocio; el sistema no los inventa |
| 2 | **No está confirmado que exista corpus documental** | **Alto** — Azure AI Search podría perder su propósito principal | Inventariar la documentación interna (ASSUMPTION-008) |
| 3 | No hay datos reales | Medio — controlado con datos sintéticos y marca de origen | Confirmar fecha de disponibilidad (ASSUMPTION-001) |
| 4 | Volumen real del catálogo y del histórico desconocido | Medio — afecta a decisiones de implementación | Solicitar cifras (ASSUMPTION-012) |
| 5 | Roles no validados con el negocio | Medio — bloquea la Fase 8 | Revisar estructura organizacional (ASSUMPTION-010) |
| 6 | Destino de despliegue en Azure sin decidir | Bajo hoy — mitigado por el uso de contenedores | Decidir en Fases 12–13 (ASSUMPTION-014) |
| 7 | Presupuesto de Azure no definido | Medio — condiciona Fases 6, 9 y 10 | Solicitar antes de provisionar |
| 8 | ~~Desajuste entre los escenarios de `DatasetConfig` y §25~~ | — | ✅ **RESUELTO** el 2026-09-17 por `DT-023`: las 26 situaciones de §25 se reparten en tres niveles (13 A + 9 B + 4 C) y el enum `Scenario` queda en 16 valores |
| 9 | `data/synthetic/generator/config.py`: archivo de 0 bytes que existía solo en el disco del proyecto (2026-09-13 20:58 UTC) y no formaba parte del Componente 1, cuyo `config.py` vive en `data/synthetic/config/` | Bajo, pero confundía: dos rutas con el mismo nombre de archivo y una vacía | **RESUELTO el 2026-09-21.** El responsable autorizó eliminarlo expresamente. Se comprobó antes que ningún import ni referencia de código dependía de él —las únicas menciones estaban en este archivo— y la suite siguió en verde |
| 10 | **Seis documentos del disco del proyecto no tenían las correcciones del 2026-09-18** (detectado el 2026-09-21 comparando `md5sum` árbol contra árbol, y **resuelto el mismo día**): `docs/04-modelo-datos.md`, `knowledge/dataset-specification.md`, `DT-024`, `DT-025`, `DT-027` y `DT-028`. Faltaban, entre otras: el intervalo cerrado `valid_from ≤ valid_to` (`docs/04`, `DT-027`), las precondiciones **P-4** y **P-5** y el testigo de MOQ con `order_multiple = 1` (`DT-028`), el orden de filas por clave de negocio (`DT-024`) y el invariante de reproducibilidad con sus cuatro campos excluidos (`DT-025`). Nota: el primer recuento de esta sesión dijo «cuatro»; la comparación completa del árbol encontró **seis** | Era **alto**: `docs/15` y este archivo declaraban esas correcciones como hechas y el disco decía lo contrario. Un Componente 2 implementado desde el disco habría reintroducido bloqueantes ya corregidos | **RESUELTO.** El responsable autorizó sobrescribir el 2026-09-21 («siempre sobreescribe para que estén actualizadas ambas carpetas»). Los seis archivos se escribieron sobre el disco y **ambas copias coinciden byte a byte**, salvo `data/synthetic/generator/config.py`, que existe solo en el disco y sigue pendiente de decisión (punto 9) |
| 11 | **Contradicción sobre la mutabilidad de las órdenes de compra** (detectada el 2026-09-30): `RNF-013` dice que «los movimientos de inventario y las órdenes de compra son registros históricos inmutables»; `docs/04` §1 clasifica `PurchaseOrder` y `PurchaseOrderItem` como mutables con auditoría, `DT-006` no los incluye entre los *append-only* y `docs/07` §2.7 prevé cambiar su estado | Medio — no afecta a U1–U5, que no escriben órdenes; sí a `US-035` | **Registrada como `DT-P13`. No se resuelve unilateralmente**: decide el responsable |
| 12 | **PyYAML no figura en ningún archivo de dependencias.** `CLAUDE.md` §5 exige registrar las librerías menores en el archivo de dependencias; el repositorio no tiene ninguno | Bajo — el generador funciona, pero su entorno no es reproducible desde el repositorio | **RESUELTO el 2026-09-30** por instrucción del responsable: `data/synthetic/requirements.txt` declara `PyYAML==6.0.3` (la versión de `DT-024`, la instalada en ambos entornos). No había ningún archivo de dependencias oficial; se usa uno por componente. El del sistema llegará con `backend/pyproject.toml` |
| 13 | **La carpeta del proyecto en el equipo del responsable es un repositorio Git en la rama `main`** (un commit, «Estructura del proyecto», con remoto en GitHub; la copia de trabajo del agente no lo es). `CLAUDE.md` §13.2 prohíbe trabajar sobre `main`, y el agente no puede crear ramas: por instrucción del responsable no ejecuta comandos de Git que cambien el estado (`checkout`, `add`, `commit`…) | Bajo — los cambios quedan sin commitear | **RESUELTO el 2026-09-30**: por instrucción expresa del responsable se creó la rama `feat/u1-supply-engine` (`git switch -c`) en la copia local. Los cambios de la Etapa 2 —que el responsable ya había añadido al índice— y los de U1 viajan en ella, sin commit |
| 14 | **Incoherencia de calendario de lint, formato y tipado** (detectada el 2026-10-05 en la revisión de F5a): `docs/12` §8 los automatiza en la Fase 3, mientras que el roadmap sitúa la CI en la Fase 13 (`GitHub Actions`); `CLAUDE.md` §6.10 ya los remite a la DT de la Fase 13 | Bajo — no bloquea nada; en Python no se ejecutan por instrucción del responsable | **Pendiente**: alinear `docs/12` §8 con el roadmap en la DT de la Fase 13 (no se edita `docs/12` ahora) |

**Revisión 0.1 (2026-09-04):** quince problemas encontrados y corregidos. Los cinco críticos:
`DT-010` confundía cuatro conceptos de incertidumbre distintos y daba por buena una fórmula (`√L`)
que solo es válida bajo supuestos no verificados; no existía regla para convertir el pronóstico
semanal a un lead time en días; `quantity_in_transit` mezclaba el tránsito total con el relevante
para una decisión; no existía evaluación del efecto del forecast sobre las decisiones de
abastecimiento; y no existía comparación end-to-end baseline vs. ML. Todos resueltos.

**Contradicciones en las instrucciones recibidas:** ninguna. La única ambigüedad fue el nivel de
`architecture/`, `decisions/` y `reports/`; se resolvió ubicándolas bajo `docs/` con justificación
registrada en `DT-013`, pendiente de confirmación.

**Revisión de consistencia interna (2026-09-03):** se ejecutó una revisión cruzada de los 30
documentos que detectó y corrigió inconsistencias entre ellos — un caso límite de stock de seguridad
mal enunciado, dos definiciones incompatibles de *fill rate*, la frecuencia del proceso batch, el rol
de consulta de políticas, la dependencia circular del baseline entre las Fases 4 y 5, dos ciclos de
dependencia entre requisitos y varios conteos. Todas están resueltas; el detalle está en
`docs/reports/etapa-0-reporte.md` §5.

### Clasificación de escenarios — resuelta (`DT-023`)

La discrepancia entre los 14 valores del enum y las 26 situaciones de §25 **queda resuelta**: no eran
dos versiones de la misma lista, sino **tres niveles distintos** que §25 resume en una sola tabla.

| Nivel | Qué es | Dónde vive | De las 26 |
|---|---|---|---|
| **A — Ejes de generación** | Comportamientos que el generador produce deliberadamente | Enum `Scenario`, `scenarios.required` | 13 |
| **B — Atributos y estados** | Campos del modelo con valores variados (MOQ, múltiplo, proveedor preferente, producto activo, estado de la orden) | Entidades de `docs/04-modelo-datos.md` | 9 |
| **C — Propiedades emergentes** | Situaciones que surgen de combinar entidades y dependen de reglas pendientes | **Validador, Componente 8** | 4 |

13 + 9 + 4 = 26.

**Autorizado e implementado:** el enum pasa de **14 a 16** valores con `LOW_INVENTORY` (§10.2) y
`PARTIAL_DELIVERY` (§12.3). Los catorce originales se conservan sin cambios de nombre ni fusiones.

**No confundir las dos cifras.** «26» cuenta situaciones de §25; «16» cuenta valores del enum. De los
16 valores, 13 corresponden a situaciones de §25 y los otros tres —`HIGH_ROTATION`, `LOW_ROTATION` y
`MULTIPLE_LEAD_TIMES`— están respaldados por otras secciones de la documentación (`DT-023` §7).

**Por qué el escenario crítico de §11 no es un eje:** etiquetar un SKU como «tránsito efectivo
insuficiente» exigiría que el generador supiera qué cuenta como *efectivo*, y ese criterio de corte es
`DT-P11`, todavía pendiente. Lo mismo ocurre con el conflicto MOQ/sobreinventario (`BR-X03`), el
producto inactivo con histórico (`BR-P10`) y la demanda censurada (`DT-011`). El generador produce las
condiciones; el validador comprueba que la propiedad se cumple.

Matriz completa de las 26 situaciones en
[`docs/decisions/DT-023-clasificacion-escenarios.md`](../docs/decisions/DT-023-clasificacion-escenarios.md).

**Abierto, sin decidir:** `HIGH_ROTATION` y `LOW_ROTATION` están en el enum y respaldados por
`docs/02` §8, el roadmap y §10.4 de la propia especificación, pero **no figuran como filas de §25**.
No se modificó §25 (`DT-P12`).

### Componente 2 — auditoría y bloqueantes resueltos

La auditoría del Componente 2 (2026-09-17, solo lectura) concluyó que la **estructura** de las cinco
entidades maestras estaba definida, pero que faltaban siete definiciones sin las cuales el componente
no podía implementarse sin inventar. Las siete quedaron resueltas el 2026-09-18:

| Bloqueante | Qué faltaba | Resuelto por |
|---|---|---|
| **B-1** | Formato y estructura física de salida — §40 lo exigía y ningún documento lo definía | `DT-024` · spec §41 |
| **B-2** | `data_origin` en las maestras: `docs/04` §5.2 lo obligaba, las fichas §§3.1–3.5 lo omitían | `DT-026` · `docs/04` §§3.1–3.5 |
| **B-3** | Vigencia de `Product`: §7.2 y §20 la exigían, el modelo solo tenía `created_at` | `DT-027` · `docs/04` §3.2 |
| **B-4** | Dónde vive la metadata de generación: §19 y §33 la exigían, ninguna entidad la alojaba | `DT-025` · spec §42 |
| **B-5** | Rangos de `moq`, `order_multiple`, `unit_cost`, `agreed_lead_time_days` | `DT-028` §1 · spec §43 |
| **B-6** | Cardinalidad y reparto de `ProductSupplier` | `DT-028` §2 |
| **B-7** | Distribución de productos por categoría | `DT-028` §3 |

**Sobre los valores de `DT-028`.** Son `synthetic generation parameters`: parámetros técnicos del
generador de datos sintéticos, amparados por §3.5 de la especificación. **No son políticas
comerciales, costos, MOQ ni plazos de la organización**, y no deben citarse como información
empresarial. Los parámetros empresariales reales siguen pendientes en `knowledge/business-rules.md` §3.

**Decisiones asociadas que no eran bloqueantes:** `DT-029` (lo que el Componente 2 **no** genera:
`abc_class`, `rotation_class`, `shelf_life_days`, `currency`, `contact_info`, ningún campo `scenario`;
y el rechazo explícito de `location_count > 1`) y `DT-030` (sub-semillas deterministas por componente,
para que implementar el Componente 3 no altere los datos del 2).

**No se modificó código.** `config.py`, `dataset_config.yaml` y las pruebas quedan como estaban; las
54 pruebas siguen en verde. Las tres precondiciones de `DT-028` §8 y el límite de `location_count`
**no se añadieron a `config.py`** deliberadamente: son límites de esta versión del generador, no del
contrato de configuración, y su comprobación corresponde al Componente 2 cuando se implemente.

### Auditoría de consistencia post-decisiones (2026-09-18)

Cuatro revisiones independientes, con contexto limpio, sobre las siete decisiones del bloque
`DT-024`–`DT-030`. **Resultado: NO APTO todavía para autorizar el Componente 2.**

**Seis bloqueantes encontrados y corregidos en esta misma sesión:**

| # | Defecto | Dónde estaba | Corrección |
|---|---|---|---|
| 1 | `DT-027` declaraba el intervalo de vigencia **cerrado por ambos extremos** y once líneas después exigía `valid_from < valid_to` estricto con un ejemplo de intervalo semiabierto. De esa ambigüedad dependía la validación de §20 | `DT-027`, `docs/04` §3.2, spec §34 | Intervalo cerrado, `valid_from ≤ valid_to`; un producto de un día es `valid_to = valid_from` |
| 2 | `DT-028` §2.3 garantizaba que «todo proveedor recibe al menos una relación». **Falso**: con `product_count = 4` y `supplier_count = 50` quedan **43 proveedores huérfanos**, y las tres precondiciones lo permitían | `DT-028` §2.3, §8 | Precondición **P-4**: `supplier_count < R` |
| 3 | La fórmula `valid_to = inicio + ⌊0,75 × period.days⌋` da `valid_to = valid_from` con `period.days = 1`, dejando un producto «inactivo» sin histórico | `DT-028` §7.1, §8 | Precondición **P-5**: `period.days ≥ 2` |
| 4 | El bucle de suelo del reparto por categoría admitía dos lecturas; con donante fijo **aborta** en 718 configuraciones, incluida `category_count = product_count = 10` | `DT-028` §3.2 | Donante recalculado en cada transferencia, con la demostración de por qué nunca se agota; desempate por índice menor |
| 5 | La sub-semilla de `DT-030` es función de «el nombre del componente», que **no estaba definido**, y la extracción de los 64 bits y la codificación quedaban abiertas | `DT-030` | Fórmula completa y explícita; identificador canónico `catalog` para el Componente 2 |
| 6 | El invariante de reproducibilidad estaba enunciado de cuatro formas incompatibles; dos insatisfacibles y dos que serían falsas en cuanto exista el Componente 3 | spec §§42.4 y 44, `DT-025`, `DT-030` | Enunciado **una sola vez** en §44, incluyendo «misma versión del generador»; el resto remite a él |

**Correcciones menores aplicadas:** referencia cruzada de §34 al contrato de columnas; orden canónico
de filas en `DT-024` (era circular: «por `id`», e `id` se definía «por el orden»); retirada de dos
afirmaciones de cobertura universal que eran falsas; `§35` tiene veinte ítems, no dieciocho;
`docs/decisions/` añadido a las dependencias documentales de la especificación; inventario de
exclusiones de `DT-029` completado.

**Tres cuestiones abiertas que requieren decisión del responsable** — el Componente 2 **no debe
autorizarse hasta cerrarlas**:

| # | Cuestión | Por qué no la decide el equipo técnico |
|---|---|---|
| **A** | **¿Ocho o nueve componentes en la Fase 1?** La tabla de este archivo funde validador e informe de calidad en el octavo; `CLAUDE.md` §17 y `data/synthetic/generator/__init__.py` los enumeran por separado, lo que da nueve. Como la sub-semilla de `DT-030` es función del identificador del componente, dos enumeraciones distintas producen datasets distintos | Es una decisión de **alcance** de la Fase 1, no una cuestión de redacción |
| **B** | **¿Debe `moq` ser múltiplo de `order_multiple`?** 31 de las 56 combinaciones posibles no lo son, y en ellas el mínimo pedible real es `⌈moq/M⌉·M`, no `moq`. `docs/06` §8 declara como criterio de aceptación que el motor «recomienda el MOQ»; con un par incoherente recomienda otra cosa | Afecta al criterio de aceptación del motor de abastecimiento, no solo al generador |
| **C** | **¿Quién produce «MOQ superior a la necesidad»?** §16, §17 y §26 lo exigen; `DT-023` lo clasifica como Nivel C, a **comprobar** por el validador. Ningún componente tiene encargado **producirlo** | Es una asignación de responsabilidad entre componentes |

**Pendientes registrados, no bloqueantes:** `PurchaseOrder`, `PurchaseOrderItem`,
`PurchaseOrderReceipt` e `InventoryPolicy` siguen sin `data_origin` en sus fichas —el mismo defecto que
motivó B-2, desplazado a los Componentes 5 y 6—; `project/roadmap.md` sigue declarando la Fase 0 como
etapa actual; `README.md` afirma que el repositorio contiene solo documentación, lo que dejó de ser
cierto el 2026-09-14; y la comprobación de reproducibilidad de §44 no tiene todavía ni prueba ni
dueño. Los cuatro quedan fuera del alcance de esta auditoría.

### V1 — Reglas mínimas funcionales (2026-09-19)

Cambio de enfoque solicitado por el responsable: en lugar de cerrar todas las reglas de negocio antes
de construir, se define una **V1 pequeña, determinista y reemplazable** que permita levantar el flujo
completo `Forecast → Inventory → Supply Engine → Recommendation` sobre el dataset sintético.

`DT-031` define **trece reglas**. Nació `PROPUESTA` el 2026-09-19 y pasó a `ACEPTADA` **como conjunto
de reglas de V1** el 2026-09-21, tras la confirmación del responsable. El matiz importa: lo aceptado
es «estas son las reglas de V1», no «estas son las políticas de la organización».

| ID | Regla | Origen |
|---|---|---|
| `V1-01` | `raw_need = max(0, demanda del horizonte + SS − posición de inventario)` | Ya era `docs/06` §§7-8, rama periódica |
| `V1-02` | `IP = on_hand + effective_in_transit − reserved`, con `reserved = 0` | Ya era `docs/06` §4.2 |
| `V1-03` | `horizonte = lead time acordado + 7 días` | **Nuevo.** `R_v1 = 7` es provisional |
| `V1-04` | Prorrateo uniforme semanal → días, en una sola función | Ya era la recomendación de `DT-019` |
| `V1-05` | `SS = z_v1 × σ_H`, sin escalar por `√L` | **Nuevo.** `z_v1 = 1,65` es provisional |
| `V1-06` | `Q_final = ⌈max(raw_need, MOQ) / M⌉ × M` | Ya era `docs/06` §8 Paso 2 |
| `V1-07` | Quince elementos de demostración, clasificados por nivel y componente | — |
| `V1-08` | Invariantes del validador; **no calcula cifras de abastecimiento** | — |
| `V1-09` | Lead time observado: mediana, mínimo 3 observaciones, fallback al acordado | Implementa `BR-P01` |
| `V1-09.1` | Ventana de 12 observaciones, ordenadas por **fecha de finalización** | Parámetro de `V1-09` |
| `V1-09.2` | Techo de 90 días, con marca `LEAD_TIME_CAPPED` y valor sin topar trazable | Parámetro de `V1-09` |
| `V1-10` | Proveedor **preferente activo**; sin él, no se recomienda | Ya era `BR-P07`; cierra `BR-X05` |
| `V1-11` | **Sin diferenciación ABC**: política única. El campo no se elimina del modelo | `DT-029`; cierra `BR-X07` |
| `V1-12` | **Sin sobre-recepción**: `quantity_received ≤ quantity_ordered` | §21 de la especificación; cierra `BR-X08` |
| `V1-13` | **Sin inventario negativo**: `on_hand ≥ 0` | §26 y `docs/06` §14; cierra `BR-X09` |

*(`V1-03` usa el lead time **observado** desde la decisión D del 2026-09-19; la fila de arriba conserva
la redacción original para que se vea qué cambió.)*

**Diez de las trece ya estaban documentadas** y solo necesitaban nombre y parámetros. Solo `V1-03`,
`V1-05` y `V1-07` introducen algo nuevo.

**Lo que queda provisional, y por qué importa:**

- `R_v1 = 7 días` y `z_v1 = 1,65` son **parámetros técnicos**, no una frecuencia de compra ni un nivel
  de servicio acordados con nadie (`ASSUMPTION-021`, `ASSUMPTION-022`).
- V1 elige implícitamente **revisión periódica**, que es `BR-X02` (`ASSUMPTION-021`).
- V1 mide la incertidumbre sobre la **variabilidad de la demanda**, no sobre el error de pronóstico,
  porque sin modelo entrenado la segunda no existe (`ASSUMPTION-023`).
- **Ninguna salida de V1 puede presentarse como recomendación de negocio.** `BR-009` sigue rigiendo
  sin excepción fuera del entorno sintético. Es la consecuencia que no conviene olvidar.

**Lo que V1 cierra:** la cuestión **C** de la auditoría anterior. «MOQ > necesidad» pasa de no
computable a computable, porque `raw_need` ya tiene definición operativa. También se corrigió una
contradicción de `docs/06` §14 anterior a todo este bloque: el criterio decía «recomienda MOQ» y la
fórmula del mismo documento produce `⌈MOQ/M⌉·M`.

### Decisiones A–F confirmadas por el responsable (2026-09-19)

| | Decisión | Efecto |
|---|---|---|
| **A** | **Ocho componentes**, sin rediseño | La estructura vigente queda confirmada. `DT-023`–`DT-030` se conservan íntegras y «Componente 2» mantiene su significado. **Desbloquea C2** |
| **B** | `review_period = 7 días` | Ya estaba en `V1-03`; queda confirmado como valor **V1/provisional** |
| **C** | `z_v1 = 1,65` | Ya estaba en `V1-05`; confirmado como **parámetro técnico**. No se optimiza el stock de seguridad en V1 |
| **D** | **`observed_lead_time`** en lugar del acordado | **Cambia `V1-03`** y añade `V1-09`. Es la única decisión que modifica lo anterior |
| **E** | MOQ y `order_multiple` independientes | Ya estaba en `V1-06`; confirmado. `(25, 10) → 30` sigue siendo caso válido |
| **F** | Cerrar reglas pendientes de forma básica cuando sea posible | **4 cerradas**, 2 puenteadas, 7 aplazadas |

**`V1-09` — lead time observado.** Mediana de las últimas **12** observaciones válidas del par
producto–proveedor, mínimo **3** para usarla, techo de **90 días**, recalculada **en cada evaluación**
con los datos disponibles hasta la fecha de la decisión. Sin histórico suficiente: **fallback al
acordado**, declarando la procedencia. Una observación es un `PurchaseOrderItem` **completamente
recibido**, fechado por su última recepción — no una por recepción, porque eso subestimaría el lead
time justo en los proveedores con entregas parciales. Parámetros en `ASSUMPTION-024`.
El acordado **no se retira del modelo**: es el fallback y la referencia de desviación del proveedor.

**`V1-10` — elección de proveedor.** El preferente activo; sin él, no se recomienda. Cierra `BR-X05`
para V1 apoyándose en `BR-P07`, que ya lo proponía. Sin scoring ni comparación entre proveedores.

**Reglas pendientes tras la decisión F:**

- **Cerradas con interpretación técnica V1 (4):** `BR-X05` (proveedor preferente) · `BR-X07` (política
  única, sin diferenciación ABC) · `BR-X08` (sin sobre-recepción) · `BR-X09` (sin inventario
  negativo). Las cuatro siguen figurando como pendientes en §3: son provisionales y el negocio puede
  contradecirlas.
- **Pendientes de negocio, puenteadas (2):** `BR-X01` (nivel de servicio: falta el valor **y** la
  definición) · `BR-X02` (política de revisión: continua o periódica, y con qué frecuencia).
- **No necesarias para V1 (7):** `BR-X03`, `BR-X04`, `BR-X06`, `BR-X10`, `BR-X11`, `BR-X12`, `BR-X13`.

**Lo que V1 sigue sin cerrar:** `DT-010`, `DT-019`, `DT-P05`, `DT-P11` y las nueve reglas de arriba.
Ninguna bloquea al Componente 2.

### Cierre de reglas V1 (2026-09-21)

El responsable confirmó `V1-09`, `V1-09.1`, `V1-09.2` y `V1-10`, y añadió tres reglas de alcance:

| ID | Regla | Qué cambia respecto al 19-09 |
|---|---|---|
| `V1-11` | **Sin diferenciación ABC.** Ninguna regla de V1 lee `abc_class` ni `rotation_class`. **El campo no se elimina del modelo**: sigue en `docs/04` §3.2 y en las columnas 8 y 9 de `products.csv`, vacías | La interpretación que cerraba `BR-X07` pasa a ser una regla con nombre propio |
| `V1-12` | **Sin sobre-recepción.** `Σ quantity_received ≤ quantity_ordered` por línea; V1 no genera ningún escenario de sobre-recepción y el validador lo rechaza | Íd. para `BR-X08` |
| `V1-13` | **Sin inventario negativo.** `on_hand(t) ≥ 0` en todo instante; el validador lo rechaza y el motor no calcula. **No aplica a `IP_decisión`**, que sí puede ser negativo legítimamente | Íd. para `BR-X09` |

**Estado del ADR.** `DT-031` pasa de `PROPUESTA` a `ACEPTADA` **como conjunto de reglas de V1**. Yo
mismo había escrito el 19-09 que «debe seguir siendo `PROPUESTA`», y revisé esa postura: `CLAUDE.md`
§8 prohíbe marcar `ACEPTADA` lo que *todavía es una hipótesis*, y estas reglas dejaron de serlo en
cuanto el responsable las decidió. **Provisional no es hipotético.** Lo que no cambia: ninguna de las
trece reglas de `business-rules.md` §3 queda confirmada, y `R_v1`, `z_v1`, `N_v1`, `N_MIN_v1` y
`LT_MAX_v1` siguen siendo parámetros técnicos. El techo de 90 días en particular **no es una política
comercial de PluriOne** y no debe citarse como tal.

**Los trece casos de prueba: ninguno es ejecutable hoy, y no se escribió ninguno.**

Esto es lo único que no se pudo hacer de lo pedido, y conviene que quede claro por qué. Los trece
casos (lead time con 0/1/2/3/>12 observaciones, techo y su trazabilidad, proveedor preferente /
no preferente / ausente, ABC sin influencia, sobre-recepción, inventario negativo) prueban **código
que no existe**:

- Once pertenecen al **motor de abastecimiento**, que es **Fase 4** y no está autorizado.
- Dos pertenecen al **Componente 8 (validador)**, que está en la Fase 1 pero no ha comenzado.
- Los casos 1 a 11 son **pruebas unitarias del motor**: construyen sus entradas a mano, como ya
  prescribe `docs/06` §14 y exige `CLAUDE.md` §12.3. Los casos 12 y 13 son invariantes del validador
  sobre el dataset.
- Dos de ellos —el 9 (proveedores sin preferente) y el 11 (dos productos que difieran en `abc_class`)—
  **no tendrán representación en el dataset**, y es deliberado: `DT-028` §2.4/§2.5 y `DT-024` columna 8
  los hacen imposibles. Su prueba unitaria sigue siendo necesaria.
- Para una comprobación de extremo a extremo, los casos **2 a 7** necesitan órdenes y recepciones
  históricas, que producen los **Componentes 5 y 6**. El caso 1 necesita justo lo contrario —su
  ausencia— y es construible con solo las entidades maestras del Componente 2.

Crear ahora un paquete `supply_engine/` para alojarlos violaría `CLAUDE.md` §6.2 —«si una carpeta o
una capa no tiene un uso hoy, no se crea»— y §17 —«no iniciar una fase posterior sin autorización»—.
En su lugar, `DT-031` registra los trece casos **uno a uno, con su regla y su componente dueño**, de
modo que lleguen con el código que deben probar. La suite sigue en **54 pruebas de `DatasetConfig`,
todas en verde**.

**Sincronización de las dos copias (2026-09-21).** La comparación `md5sum` del árbol completo
encontró **seis** documentos del disco sin las correcciones del 2026-09-18 —`docs/04`,
`dataset-specification.md`, `DT-024`, `DT-025`, `DT-027` y `DT-028`—. Con autorización del
responsable se sobrescribieron con la versión corregida. **Ambas copias coinciden ahora byte a byte**,
con una sola excepción conocida y deliberada: `data/synthetic/generator/config.py` (0 bytes) existe
solo en el disco y **no se ha borrado** (punto 9 de *Problemas conocidos*).

**Limitación conocida registrada en este cierre.** El techo `LT_MAX_v1 = 90` **no garantiza** que el
horizonte de cobertura quepa en el horizonte de pronóstico de `ASSUMPTION-002`: `90 + 7 = 97 días ≈
13,9 semanas`, por encima de las 12 semanas, y ya a partir de un lead time observado de 78 días el
horizonte se sale del rango. El 2026-09-19 escribí que el techo restauraba esa garantía; **era falso**
y queda corregido en `DT-031` (`V1-03` y `V1-09` §6). Restaurarla exigiría bajar `LT_MAX_v1` a 77 días
o ampliar `ASSUMPTION-002`, y **ninguna de las dos se decide aquí**: el responsable confirmó 90 el
2026-09-21. Queda como limitación declarada, señalada por `LEAD_TIME_CAPPED`.

**Cambios de esta etapa:** `DT-031` (trece reglas, sub-reglas `V1-09.1`/`V1-09.2`, tabla de casos de
prueba, estado `ACEPTADA`), `docs/15` (entrada `DT-031`, versión 1.4), `docs/06` (§14 y §15 citan
`V1-10`/`V1-11`/`V1-13`; nota de V1 actualizada), `knowledge/business-rules.md` (la tabla de cierres
cita `V1-10`–`V1-13`), `knowledge/assumptions.md` (`ASSUMPTION-024` confirmada), `knowledge/glossary.md`
(clasificación ABC y lead time observado). **Sin cambios de código.**

### Componente 2 — Catalog Generator (2026-09-21)

**Implementado y probado.** Genera las cinco entidades maestras y su manifiesto; nada más.

| Archivo nuevo | Qué hace | ADR |
|---|---|---|
| `data/synthetic/generator/rng.py` | Sub-semilla y flujo pseudoaleatorio determinista | `DT-030`, `DT-032` |
| `data/synthetic/generator/policies.py` | Constantes sintéticas, Zipf, clases A–D, precondiciones | `DT-028`, `DT-029` |
| `data/synthetic/generator/writer.py` | Contrato de formato CSV y `manifest.json` | `DT-024`, `DT-025`, `DT-033` |
| `data/synthetic/generator/catalog.py` | El generador | — |
| `data/synthetic/generator/__main__.py` | `python3 -m data.synthetic.generator` | — |
| `data/synthetic/tests/test_catalog.py` | 101 pruebas nuevas | — |

**Salida con la configuración vigente** (`seed = 20260913`, 100/10/10/1, 2023-01-01 → 2026-01-01):

| Archivo | Filas | Comprobado |
|---|--:|---|
| `categories.csv` | 10 | Todas activas, jerarquía plana |
| `products.csv` | 100 | 95 activos + 5 inactivos con `valid_to = 2025-04-02`; reparto Zipf `[34,17,11,9,7,6,5,4,4,3]` |
| `suppliers.csv` | 10 | Todos activos, 12 relaciones cada uno, ninguno huérfano |
| `product_suppliers.csv` | 120 | `R = 80·1 + 10·2 + 5·3 + 5·1`; 95 preferentes; 5 productos sin proveedor activo |
| `locations.csv` | 1 | `MAIN_WAREHOUSE` |
| `manifest.json` | — | Nueve campos obligatorios; sin `scenario_assignment` ni `quality_report` |

`dataset_version = ds-a4e50751841e`. Salida en `data/synthetic/output/`, **no versionada**.

**Dos decisiones que los ADR dejaban para este momento**, ambas registradas:

- **`DT-032` — algoritmo pseudoaleatorio.** §44 decía literalmente que fijarlo era trabajo del
  Componente 2, y advertía de un **límite conocido**: el flujo de `random` no garantiza igualdad byte
  a byte entre versiones de Python. Se adoptó un **contador sobre SHA-256**, de modo que cada
  extracción es función pura de `(sub-semilla, etiqueta, contador)`. El límite queda **cerrado**, no
  documentado. El generador no usa `random` en ninguna parte.
- **`DT-033` — versionado.** `generator_version` semántica sobre la salida observable; `dataset_version`
  **derivada** por hash de la configuración y esa versión, de modo que regenerar el mismo dataset da
  el mismo identificador. `components[].version` se mantiene aparte, porque `DT-028` §8 lo usa para
  rastrear qué políticas produjeron el dataset.

**Revisión adversarial independiente.** Dos revisores con contexto limpio auditaron el código y su
conformidad con los ADR (~28 000 configuraciones de barrido). Encontraron **cinco defectos reales**,
todos verificados y corregidos antes de cerrar:

| Defecto | Consecuencia | Corrección |
|---|---|---|
| El ancho fijo de los códigos se desbordaba | Con `category_count > 999` los CSV salían **desordenados en silencio**, rompiendo el orden por clave de negocio de `DT-024` | `policies.code_width()` amplía el ancho con la escala, como `DT-028` §4 ya preveía |
| `below(bound > 2⁶⁴)` no terminaba nunca | Bucle infinito latente en un método público documentado como total | Extrae tantas palabras de 64 bits como haga falta |
| La `Z` de UTC se estampaba sin convertir | Una hora local rotulada como UTC: un instante falso con aspecto autoritativo | `to_utc()` convierte y **rechaza** un `datetime` sin zona |
| La red de seguridad no cubría `DT-028` §2.4 ni §7 | Un fallo futuro en el preferente o en los estados no se habría detectado | Ambas garantías se comprueban ahora, y los problemas se acumulan en vez de cortar al primero |
| Un `10` literal como lead time testigo | Único número del código ausente de `DT-028`, contra su principio de «un solo documento» | Se sustituye por un ajuste de un día, sin constante nueva |

Dos correcciones más, de documentación: §43.4 de la especificación listaba **tres** precondiciones
cuando `DT-028` §8 tiene **cinco** desde el 2026-09-18 (`docs/15` repetía el error), y `DT-028` §1.5
aparecía **dos veces** por un error de numeración.

**Lo que el Componente 2 NO hace**, y es deliberado: no genera demanda, inventario, movimientos,
órdenes, recepciones ni comportamiento de proveedores; no asigna escenarios a SKU; no valida el
dataset; no calcula nada de abastecimiento. `abc_class`, `rotation_class`, `shelf_life_days`,
`currency`, `contact_info`, `description`, `parent_id`, `created_at` y `updated_at` quedan vacíos por
`DT-029`, y las columnas siguen en el archivo porque el esquema es el de la entidad.

**Pendientes reales que deja este componente:**

1. ~~La tabla canónica de identificadores de componente sigue sin existir~~ — **RESUELTO el
   2026-09-21**, ver la sección siguiente.
2. **`generate()` no borra el directorio de salida.** `DT-024` dice que «cada ejecución regenera el
   directorio completo»; hoy sobrescribe los seis archivos pero no elimina huérfanos. Inocuo con un
   solo componente; hay que resolverlo cuando el Componente 3 cambie el conjunto de archivos.
3. **Al añadir el Componente 3 hay que subir `generator_version`** (`DT-033`). Si no, dos datasets con
   contenidos distintos declararían el mismo `dataset_version`.
4. `PurchaseOrder`, `PurchaseOrderItem`, `PurchaseOrderReceipt` e `InventoryPolicy` **siguen sin
   `data_origin`** en sus fichas (`DT-026`). Debe cerrarse antes de autorizar los Componentes 5 y 6.

### Identificadores canónicos de componente (2026-09-21)

Cerrado el último pendiente que bloqueaba al Componente 3. `DT-030` fija la sub-semilla como
`sha256("<seed>:<identificador>")`, de modo que **el identificador tenía que decidirse antes de que un
componente generara datos**: decidirlo después cambiaría esos datos.

| # | Componente | Identificador | Nota |
|---|---|---|---|
| 1 | `DatasetConfig` | **ninguno** | No extrae del flujo pseudoaleatorio; no tiene sub-semilla |
| 2 | Catalog Generator | `catalog` | **Sin cambios**: ya estaba en uso |
| 3 | Demand Generator | `demand` | |
| 4 | Inventory Simulator | `inventory` | |
| 5 | Purchase Order Generator | `orders` | Nombrado por lo que produce, no por el archivo |
| 6 | Supplier Behaviour Generator | `supplier_behaviour` | El único con guion bajo, y es deliberado |
| 7 | Scenario Assignment | `scenarios` | |
| 8 | Dataset Validator + informe de calidad | `validator` | El informe es **parte de este componente** |

`COMPONENT_IDS` en `rng.py`, con una constante por componente. Nueve pruebas nuevas los fijan contra
la fórmula de `DT-030` y comprueban las propiedades que el ADR exige: ASCII en minúsculas, distintos
de su número, únicos, y sub-semillas todas distintas. Una de ellas comprueba la propiedad que
justifica toda la decisión: **renumerar los componentes no cambia ninguna sub-semilla.**

**El Componente 2 no se tocó** y sus cinco CSV salen byte a byte idénticos tras el cambio.

**Quality Report: opción A, dentro del Componente 8.** No fue una preferencia; lo sostienen `DT-023`
(«Validador del dataset (Componente 8)»), `DT-025` (`quality_report` → «Componente 8»), la tabla de
este archivo y `DT-031` (casos de prueba 12 y 13 → «Componente 8»). La ambigüedad que `DT-030`
registraba venía de la prosa de `CLAUDE.md` §17, corregida el 2026-09-21: **ninguna decisión aceptada
propuso nunca un noveno componente.**

**Sigue pendiente, y esta decisión no lo toca:** si `quality_report` se escribe dentro de
`manifest.json` o como archivo aparte. `DT-025` lo aplaza al autorizar el Componente 8.

Corregido de paso un descuido del cierre anterior: la tabla *Fase 1 — avance por componente* seguía
declarando el Componente 2 como «no iniciado, pendiente de autorización» mientras el resto del archivo
lo daba por implementado.

### Componente 3 — Demand Generator (2026-09-23)

**Implementado y probado.** Produce `demand.csv`: la **demanda latente**, producto × ubicación × día.

**La distinción que introduce esta etapa**, y que es su razón de ser:

```text
C2 → products.csv, locations.csv
   → C3 → demand.csv        demanda LATENTE     lo que se habría demandado
   → C4 → consumption.csv   demanda SATISFECHA  lo que las existencias permitieron
                            + is_stockout_affected
```

`docs/04` §3.8 ya advertía que un modelo entrenado sobre el consumo «aprende que la demanda bajó»
justo donde faltó producto. Con las dos series en disco, ese sesgo deja de ser una advertencia y pasa
a ser **una cantidad medible**: la diferencia entre ambas. Es lo que permitirá cerrar `DT-011` —cuyo
método sigue pendiente— comparando los cuatro tratamientos posibles contra la demanda real, que en el
entorno sintético sí se conoce y con datos reales no se conocerá nunca.

**El Componente 3 no escribe `consumption.csv`**, no conoce las existencias y no lleva
`is_stockout_affected`. Todo eso es del Componente 4.

| Archivo nuevo | Qué hace |
|---|---|
| `data/synthetic/generator/demand.py` | El componente |
| `data/synthetic/tests/test_demand.py` | 71 pruebas |
| `docs/decisions/DT-034-demanda-latente-persistente.md` | `Demand` como entidad persistente + contrato de `demand.csv` |
| `docs/decisions/DT-035-politicas-generacion-demanda.md` | Políticas sintéticas de demanda |

**Salida con la configuración vigente** (`seed = 20260913`, 100 productos, 2023-01-01 → 2026-01-01):

| | |
|---|---|
| Filas | **108 235** — 95 productos activos × 1096 días + 5 inactivos × 823 |
| Tamaño | ~3,5 MB, no versionado |
| Columnas | `id`, `product_id`, `location_id`, `occurred_on`, `quantity`, `data_origin` |
| Periodo | **semiabierto** `[2023-01-01, 2026-01-01)` → último día **2025-12-31** |
| Densidad | Una fila por día vigente; `quantity = 0` los días sin demanda |
| `quantity` | **Entero** ≥ 0, para toda unidad de medida en V1 |

**Los ocho comportamientos, medidos sobre la serie generada** —no leídos de una etiqueta—:

| Comportamiento | Evidencia en los datos |
|---|---|
| `STABLE_DEMAND` | CV 0,06 |
| `ERRATIC_DEMAND` | CV 0,36 — seis veces la estable, con nivel medio comparable |
| `GROWING_DEMAND` | Último 10 % del periodo = 1,53× el primero |
| `DECLINING_DEMAND` | 0,46×, sin llegar nunca a cero |
| `SEASONAL_DEMAND` | Autocorrelación a 365 días: 0,46 (estable: −0,00) |
| `INTERMITTENT_DEMAND` | 85 % de días en cero (estable: 0 %) |
| `HIGH_ROTATION` | 41,7 unidades/día de media |
| `LOW_ROTATION` | 3,0 unidades/día |

**Dos ejes ortogonales, no una lista de ocho.** Cada producto recibe una **forma** (seis) y una
**rotación** (dos), cada eje con su mezcla al 100 % y suelo de uno. Fundirlos en una sola lista haría
que «alta rotación» fuera incompatible con «estacional», lo cual no describe ningún producto: la
rotación es magnitud y la forma es reparto temporal. `DT-023` §7.2 ya trata la rotación como eje
aparte.

**Decisiones técnicas que hubo que tomar al implementar:**

- **Onda triangular en lugar de senoidal** para la estacionalidad. `math.sin` lo calcula la `libm` de
  la plataforma y sus últimos bits no están garantizados entre versiones; un solo flotante habría
  deshecho la identidad byte a byte de `DT-032` para cada producto estacional. Todo el mecanismo es
  aritmética entera en por mil, sin un solo flotante.
- **La intermitencia tiene mecanismo propio.** Sus ceros son días sin evento, no un nivel pequeño que
  redondea a cero. Si fuera lo segundo, una serie intermitente sería una estable de bajo volumen con
  otra etiqueta, y §8.5 quedaría incomprobable.
- **C3 lee los CSV de C2**, no un objeto en memoria. La dependencia de la arquitectura es
  `C2 → products.csv/locations.csv → C3`, y leer los archivos la hace real.
- **`generator_version` sube a 0.2.0** (`DT-033`): el generador produce datos distintos, y no subirla
  habría hecho que dos datasets con contenidos distintos declararan el mismo `dataset_version`.

**Pendientes reales antes del Componente 4 — los cuatro cerrados el 2026-09-24:**

1. ✅ **Cómo recorta C4 la demanda latente.** Cerrado: `consumption = min(demanda latente, existencia
   antes del consumo)`, **por día y sin backlog**; la demanda no satisfecha se pierde y `lost_sales`
   es derivable, no almacenada (`DT-038` §4).
2. ✅ **El contrato de columnas de `consumption.csv`.** Cerrado en `DT-038` §4, junto con los de
   `inventory_movements.csv` (§5) e `inventory.csv` (§6), y los tres del Componente 5 en `DT-039`.
3. ✅ **Limpieza del directorio de salida.** Cerrado en `DT-038` §13, con el comportamiento
   aprobado: **no se borra nada indiscriminadamente**; si el directorio contiene archivos ajenos al
   conjunto que la ejecución va a producir, la generación **falla explícitamente** en lugar de
   producir un dataset mezclado en silencio. **Completado el 2026-09-26 por `DT-040`**: además de la
   comprobación previa, cada ejecución trabaja en un workspace propio y `output/` solo cambia por
   promoción al final, de modo que una ejecución fallida nunca lo modifica. La implementación es de
   la fase de código.
4. ✅ **`generator_version`.** Cerrado: **`0.3.0`**, un único incremento para el lote C6 + C4 + C5
   (`DT-036` §8). Se aplicará al implementar, junto con la actualización de la prueba que hoy afirma
   `"0.2.0"`.

### Componente 4 — Inventory Simulator (2026-09-26)

**Implementado y probado. No conectado a `__main__`.** Lee `products.csv`, `locations.csv`,
`product_suppliers.csv` y `demand.csv` del directorio que recibe, más los perfiles de proveedor **en
memoria**, y escribe `consumption.csv`, `inventory_movements.csv` e `inventory.csv` en ese mismo
directorio; entrega en memoria las órdenes causales, sus líneas y sus recepciones, con los
identificadores ya asignados, para el Componente 5.

| Archivo | Qué hace |
|---|---|
| `data/synthetic/generator/inventory.py` | **Nuevo.** El componente: fórmulas de `DT-036`, bucle causal diario de `DT-038` §3, identificadores en seis pasos (§8), precondiciones (§16) |
| `data/synthetic/tests/test_inventory.py` | **Nuevo.** 88 pruebas |
| `data/synthetic/generator/policies.py` | Banner de `DT-036`: `W`, `M`, `C`, factores y mezcla de apertura |
| `data/synthetic/generator/writer.py` | `INVENTORY_VERSION = "0.1.0"`; `GENERATOR_VERSION` **sigue en 0.2.0** |
| `data/synthetic/generator/__init__.py` | Docstring y exportaciones |

**Decisiones tomadas al autorizar la implementación:**

- **D-C4-1 = O1.** `q1 = min(Q_final − 1, max(1, ceil(Q_final × split / 1000)))`, `q2 = Q_final − q1`.
  La fórmula anterior de `DT-037` §3 daba `q2 = 0` para `Q_final` de 2 a 4 con `split = 800`. El
  defecto era latente: con el catálogo vigente ninguna ventana produce `Q_final ≤ 4` (mínimo: 10).
- **D-C4-2 = P1.** P-C4-2 (`period.days ≥ 28`) y P-C4-3 (cada producto vigente al menos 28 días del
  periodo). Si fallan: `GeneratorError`, nada simulado, nada escrito. La ventana no se acorta, no se
  rellena y no se extrapola.
- **D-C4-3.** `L = agreed_lead_time_days` de la relación preferente activa, también para
  `expected_on`; `V1-09` y `R_v1` no intervienen; `M = 7` es solo el margen de la apertura; el disparo
  se evalúa todos los días.

**Cómo se prueba.** Además de las pruebas unitarias de cada fórmula, una **repetición independiente**
(`audit`) recalcula día a día, a partir solo de los archivos escritos y con aritmética propia
(`Fraction`, `W = 28`, `C = 21` literales), el consumo, la marca de desabasto, el disparo, la cantidad,
la fecha comprometida, las recepciones y el snapshot, y la aplica al dataset pequeño, a tres
escenarios hechos a mano y a la escala completa. Se comprobó además que la suite **detecta** trece
defectos inyectados a propósito en una copia desechable del módulo (umbral con `M`, disparo antes del
consumo, fórmula de reparto antigua, guarda de `V1-06` ausente, revisión semanal, backlog, fecha
comprometida desplazada, entre otros).

**Salida a escala completa, con perfiles de prueba** —construidos a mano con los valores de `DT-037`
§2 y un reparto cíclico que **no** es el del Componente 6, de modo que estas cifras no son las del
dataset que se publique—: 108 235 filas de consumo (las mismas que `demand.csv`), 93 010 movimientos
(100 aperturas, 3 951 recepciones, 88 959 salidas), 3 625 órdenes causales (3 536 recibidas, 85
emitidas y 4 parcialmente recibidas al corte), 10 994 días-par con desabasto; ~3 s.

**Lo que no hace, deliberadamente:** no escribe los archivos de órdenes (C5), no crea órdenes
`CANCELLED` ni forma `order_number` (C5, decisión A2), no asigna perfiles de proveedor (C6), no
publica ni conoce `output/` (`DT-040`) y **no calcula `metrics`**: `DT-038` §12 las cita contra una
«`DT-036` §17 del acuerdo» que no existe en el repositorio, y queda registrado como **pendiente
documental**.

**`generator_version` no sube.** Con C4 sin conectar, el artefacto publicado de toda configuración
aceptada es byte a byte el mismo, y la regla de `DT-033` no se activa. El incremento a `0.3.0` de
`DT-036` §8 llega con el lote C6 + C4 + C5 conectado.

### Componente 5 — Purchase Order Generator (2026-09-28)

**Implementado y probado. No conectado a `__main__`.** Recibe en memoria el `SimulationResult` del
Componente 4, lee `products.csv` solo para `valid_to`, y escribe `purchase_orders.csv`,
`purchase_order_items.csv` y `purchase_order_receipts.csv` en el directorio que recibe, extendiendo
el manifiesto con `orders`. **Materializa, no simula**: no recalcula ninguna fecha, cantidad, estado
ni identificador del Componente 4, y no lo importa en tiempo de ejecución (`DT-039` §1).

| Archivo | Qué hace |
|---|---|
| `data/synthetic/generator/orders.py` | **Nuevo.** El componente |
| `data/synthetic/tests/test_orders.py` | **Nuevo.** 55 pruebas |
| `data/synthetic/generator/policies.py` | Banner de `DT-039`: `ORDERS_CANCELLED_PERMILLE = 20`, `ORDERS_CANCELLED_CLOSE_LAG_DAYS = 1` |
| `data/synthetic/generator/writer.py` | `ORDERS_VERSION = "0.1.0"`; `GENERATOR_VERSION` **sigue en 0.2.0** |
| `data/synthetic/generator/__init__.py` | Docstring y exportaciones |

**Política `CANCELLED`, en el orden de `DT-039` §5.2:** universo de plantillas filtrado por la regla
de D-01 (cierre previsto `< end_date` y `<= valid_to` o nulo) → `K = max(1, ceil(N × 20 / 1000))`
con `N` = órdenes causales, acotado por el tamaño del universo → B2 (`GeneratorError` con universo
vacío, incluido `N = 0`) → permutación `cancelled-selection` → gemelas con `closed_at = issued_at + 1
día`, sin recorte, numeradas a continuación de las causales. `order_number = "PO-" + id` con relleno
`max(6, dígitos del id más alto)`.

**Cómo se prueba.** Pruebas unitarias de cada regla —la elegibilidad se compara con la especificación
ejecutable del cierre de D-01—, casos hechos a mano para cada frontera, y una auditoría independiente
de los tres archivos sobre el pipeline C2 → C3 → C4 → C5 a escala pequeña y completa. En una copia
desechable del módulo se inyectaron diecisiete defectos —entre ellos `<=` por `<`, filtrado después de
la selección, `K` sobre el universo, B2 eliminado, `closed_at` recortado a `valid_to`,
`order_number` duplicado, `expected_at` recalculado, selección no determinista y referencias
huérfanas— y la suite detectó los diecisiete.

**Salida a escala completa, con los perfiles de prueba de C4** (no los de C6): 3 625 órdenes causales,
3 620 plantillas elegibles, `K = 73` canceladas; 3 698 órdenes y líneas, 3 951 recepciones.

### Componente 6 — Supplier Behaviour Generator (2026-09-28)

**Implementado y probado. No conectado a `__main__`.** Lee `suppliers.csv` del directorio que recibe
y devuelve, en memoria, una tupla de `SupplierProfile` —uno por proveedor, activos e inactivos,
ordenados por `supplier_id`— para el Componente 4. **No escribe ningún archivo de datos**; su única
traza persistente es su entrada en `manifest.components` (decisión A1).

| Archivo | Qué hace |
|---|---|
| `data/synthetic/generator/supplier_behaviour.py` | **Nuevo.** El componente |
| `data/synthetic/tests/test_supplier_behaviour.py` | **Nuevo.** 40 pruebas |
| `data/synthetic/generator/policies.py` | Banner de `DT-037`: tablas de §2, mezclas 40/40/20 y 70/30, P-C6-1 |
| `data/synthetic/generator/writer.py` | `SUPPLIER_BEHAVIOUR_VERSION = "0.1.0"`; `GENERATOR_VERSION` **sigue en 0.2.0** |
| `data/synthetic/generator/__init__.py` | Docstring y exportaciones |
| `data/synthetic/generator/inventory.py`, `data/synthetic/tests/test_inventory.py` | Solo comentarios que decían que C6 no existía (O2); ninguna línea de lógica |

**Reparto y asignación.** Cupos por mayor resto con suelo de uno —el mismo auxiliar que usan C3 y
C4—, y dos permutaciones independientes, `punctuality-assignment` e `integrity-assignment`, sobre
`sub_seed(seed, "supplier_behaviour")`. Con los 10 proveedores vigentes: **4 / 4 / 2** y **7 / 3**.
`SupplierProfile` se importa de `inventory.py`, solo el tipo (decisión A2).

**Cómo se prueba.** Valores de los cinco perfiles; reparto contra un oráculo independiente para todo
`n` entre 3 y 119; cobertura de inactivos; P-C6-1; determinismo e independencia de los ejes;
entrada del manifiesto sin archivos; y el pipeline en su orden aprobado, `C2 → C3 → C6 → C4 → C5`,
a escala pequeña y completa, con las auditorías independientes de C4 y C5. En una copia desechable se
inyectaron dieciséis defectos —desigualdad del reparto, suelo de uno eliminado, proporción cambiada,
una sola permutación para los dos ejes, etiqueta de sub-semilla o de secuencia cambiada, un eje
dependiente del otro, inactivos omitidos, perfiles desordenados o duplicados, P-C6-1 relajada,
archivo de datos escrito, versión del generador alterada, entre otros— y la suite detectó los
dieciséis.

**Con los perfiles reales de C6 a escala completa**, C4 emite 3 632 órdenes causales; C5 materializa
todas y añade las canceladas. Estas cifras sustituyen, como referencia, a las obtenidas con perfiles
de prueba en las secciones de C4 y C5; el dataset publicado **no cambia** hasta W1.

### W1 — Publicación del dataset (2026-09-29)

**Implementado.** `data/synthetic/generator/pipeline.py`, función `run`, invocada por `__main__.py`.
Decisiones del responsable aplicadas: **`GENERATOR_VERSION` 0.2.0 → 0.3.0** para el lote C6 + C4 +
C5 (`DT-036` §8) y **promoción según `DT-040` §5**, con el directorio anterior solo de forma
transitoria. Los dos detalles pendientes de `DT-040` quedan resueltos: el `.anterior` se elimina
tras una promoción correcta y el workspace de una ejecución fallida también se elimina.

```text
check_output(output/) → tmp/<uuid>/ → C2 → C3 → C6 → C4 → C5 → verify → promote → output/
```

| Archivo | Qué hace |
|---|---|
| `data/synthetic/generator/pipeline.py` | **Nuevo.** Comprobación previa, workspace, los cinco componentes, verificación final, promoción |
| `data/synthetic/generator/__main__.py` | Ejecuta `pipeline.run`; ya no llama a ningún componente directamente |
| `data/synthetic/generator/writer.py` | `GENERATOR_VERSION = "0.3.0"` |
| `data/synthetic/tests/test_pipeline.py` | **Nuevo.** 29 pruebas |
| Pruebas de C3–C6 | Solo las aserciones de versión (`0.2.0` → `0.3.0`) y las de «no conectado», que ahora comprueban que el componente se alcanza **solo** a través de W1 |

**Garantía, sin exagerarla.** Un fallo en la comprobación previa, en cualquier componente o en la
verificación deja `output/` idéntico byte a byte y `tmp/` vacío. La promoción son dos renombrados:
**no** es atómica —`output/` no existe durante un instante— y, si fallan a la vez el segundo
renombrado y la restauración, el dataset anterior queda íntegro en `tmp/<id>.anterior/` y el error
lo dice. Detalle en `DT-040` §9.

**Cómo se prueba.** Fallos reales de C2 (P-1), C3 (P-6) y C4 (P-C4-2) después de que otros
componentes hayan escrito; fallos inyectados de C6 y C5, de la verificación (archivo intruso, bytes
alterados, manifiesto incompleto, existencia negativa) y de cada renombrado de la promoción; éxito,
sustitución completa de un dataset anterior, determinismo byte a byte y ausencia del identificador
del workspace en el artefacto. En una copia desechable se inyectaron **catorce** defectos de W1 —C2
escribiendo en `output/`, promoción omitida, promoción pese al fallo de C5, archivos parciales en
`output/`, promoción por copia, sin verificación, identificador en el manifiesto, contenido no
determinista, workspace no limpiado, archivo temporal en `output/`, sin restauración (c),
`.anterior` borrado en doble fallo, sin comprobación previa, `.anterior` no borrado— y la suite
detectó los catorce.

**Dataset publicado** (`python3 -m data.synthetic.generator`, 2026-09-29): `ds-269a698250db`,
`generator_version` 0.3.0, 12 CSV + `manifest.json`; 108 235 filas de consumo, 93 012 movimientos,
3 705 órdenes (3 543 recibidas, 88 emitidas, 1 parcialmente recibida y 73 canceladas) y 3 810
recepciones. Los seis CSV de C2 y C3 son byte a byte los del dataset anterior; una reproducción
independiente de la ejecución coincide byte a byte con lo publicado, y las auditorías independientes
de C4 y C5 no encuentran ningún problema. No quedó nada en `tmp/`.

### Componente 7 — Scenario Assignment (2026-09-29)

**Implementado y probado, sin integrar en W1.** Contrato en `DT-041`; decisiones C7/C8-01 a 14 de la
auditoría del mismo día.

| Archivo | Qué hace |
|---|---|
| `docs/decisions/DT-041-asignacion-escenarios-c7.md` | **Nuevo.** Contrato: forma de `scenario_assignment`, los 16 ejes, criterios, cláusula `SYNTHETIC_COVERAGE_CRITERION`, nivel C sin etiqueta |
| `data/synthetic/generator/scenarios.py` | **Nuevo.** `build_assignment`, `generate`, `load_facts`, `observed_axes`, `supplier_axes`, `emergent_properties` y la aritmética de §6.6 y §8 |
| `data/synthetic/generator/writer.py` | `SCENARIOS_VERSION = "0.1.0"` y `add_manifest_field` (añade un campo, nunca sobrescribe). Ninguna función existente cambia |
| `data/synthetic/tests/test_scenarios.py` | **Nuevo.** 46 pruebas |
| `DT-031` (`V1-07`, `V1-08`), `DT-030`, `docs/15` | Notas de redacción: C7 registra y mide, no asigna; el validador no clasifica sobreinventario según `BR-X03` |

**Qué registra.** Los 16 ejes en el orden del enum, cada uno con `unit`, `basis`, `criterion`,
`source`, `suppliers` y `products`. Forma y rotación: la decisión de C3, reconstruida con
`build_demand` y aceptada solo si coincide byte a byte con `demand.csv`. Proveedores: unidad
`supplier` y productos como evidencia (`RELIABLE = PUNCTUAL ∧ COMPLETE`, `DELAYED = LATE`,
`PARTIAL = SPLIT`, `IRREGULAR` sin etiqueta). `LOW_INVENTORY` y `OVERSTOCK` con criterios
`SYNTHETIC_COVERAGE_CRITERION`, que **no** son reglas de negocio. El nivel C se detecta en
`emergent_properties` y **no** se escribe: lo reportará C8.

**Sobre el dataset publicado** (solo lectura), los 16 ejes y las cuatro situaciones de nivel C tienen
casos. También en R2, R3 y R1 con tres proveedores, generados en directorios temporales y
contrastados con una reproducción independiente escrita en las pruebas.

**No cambia:** C2–C6, `pipeline.py`, `GENERATOR_VERSION` (0.3.0) ni `output/`. En una copia
desechable se inyectaron **diecinueve** defectos —etiquetas de flujo de C3, orden y contenido del
enum, un escenario omitido, orden invertido, sin comprobación SHA, correspondencias de C6 erróneas,
`IRREGULAR` etiquetado, lead time igual contado como múltiple, umbral y guarda de `OVERSTOCK`,
sobrescritura, CSV escrito, sorteo propio, y los bordes de `LOW_INVENTORY`, retraso, entrega
parcial y propiedades 12 y 18— y la suite detectó los diecinueve.

### Componente 8 — Dataset Validator + informe de calidad; generador 0.4.0 (2026-09-29)

**Implementado, integrado y publicado.** Contrato en `DT-042`.

| Archivo | Qué hace |
|---|---|
| `docs/decisions/DT-042-validador-dataset-quality-report.md` | **Nuevo.** Catálogo de 51 comprobaciones, contrato de `quality_report`, anomalías, fallos, integración y versión |
| `data/synthetic/generator/validator.py` | **Nuevo.** `validate` (no escribe) y `generate` (añade `quality_report` y su componente) |
| `data/synthetic/generator/pipeline.py` | `generate_into` ejecuta C7 y C8 tras C5; `COMPONENT_VERSIONS` con siete componentes; `verify` exige `scenario_assignment` y un `quality_report` sin fallos |
| `data/synthetic/generator/writer.py` | `VALIDATOR_VERSION = "0.1.0"`; **`GENERATOR_VERSION` 0.3.0 → 0.4.0**, un solo incremento |
| `data/synthetic/tests/test_validator.py` | **Nuevo.** 67 pruebas, entre ellas la inyección de fallos por familia |
| Pruebas de C3–C7 y W1 | Versión esperada 0.4.0; fixtures de C7 y C8 que se detienen en C5; pruebas de verificación que alteran el workspace **después** de C8; semilla 4 en lugar de 1 para el segundo dataset de `test_pipeline` (ver abajo); pruebas nuevas de fallo de C7 y C8, manifiesto completo, reproducibilidad salvo `generated_at` y R2/R3 de extremo a extremo |

**Validación.** C8 lee solo el workspace y comprueba manifiesto, formato, origen, identidad,
referencias, reglas comerciales, recepciones, canceladas, `order_number`, inventario, consumo,
temporalidad (con la excepción de `DT-027`), vocabularios, `scenario_assignment`, cobertura de
`scenarios.required` y las cuatro situaciones de nivel C. Acumula todos los fallos antes de lanzar
`GeneratorError`. En una copia desechable se inyectaron **16** defectos en el propio validador y la
suite detectó los 16.

**Hallazgo: a escala muy pequeña la cobertura depende de la semilla.** Con 12 productos y 59 días,
6 de las 14 semillas probadas (1–3, 11, 12 y 14) dejan un escenario requerido o una situación de
nivel C sin caso, y C8 rechaza la ejecución —el comportamiento aprobado en la decisión C7/C8-07—. La
configuración vigente, R2 (semilla por defecto) y R3 pasan. `test_pipeline` usaba la semilla 1 para
su segundo dataset y ahora usa la 4.

**Dataset publicado** (`python3 -m data.synthetic.generator`, 2026-09-29): `ds-6c8ad65b4999`,
`generator_version` 0.4.0, 12 CSV + `manifest.json` con 11 campos y 7 componentes. `quality_report`:
51/51, 0 fallos, 16/16 escenarios cubiertos, nivel C 8/12/18/20 con 100/67/26/5 productos,
`anomalies: []`. Dos generaciones independientes dieron los mismos CSV byte a byte y el mismo
manifiesto salvo `generated_at`; los doce CSV son byte a byte los del dataset 0.3.0. El 0.3.0
permaneció intacto hasta que el 0.4.0 superó todas las comprobaciones y la promoción lo sustituyó
según `DT-040` §5. Informe breve en `docs/reports/dataset-sintetico-0.4.0-calidad.md`.

### Etapa 2 — arquitectura y fundación (2026-09-30)

**Documentado, no implementado.** Ningún archivo de código creado; la suite sigue en 582 pruebas.

| Tema | Dónde | Resumen |
|---|---|---|
| Arquitectura de implementación | `docs/03` §16, `DT-043` | Un proyecto `backend/` con paquetes por responsabilidad; puertos en el paquete que los usa; nuevo `TokenValidator` local; reglas de dependencia verificables; el generador es *upstream* y no se importa |
| Del dataset a PostgreSQL | `docs/04` §9, `DT-044` | Una tabla por archivo; `demand` separada de `consumption` y fuera del cálculo; un linaje por base; carga todo o nada con validación previa y posterior; `data_loads` con el manifiesto |
| Contrato de forecast | `docs/05` §19, `DT-046` | Consumo hasta `as_of_date`, semanas ancladas en `as_of_date + 1`, 14 semanas derivadas de V1; nada de decisiones de compra |
| Contrato del motor V1 | `docs/06` §16, `DT-045` | Evaluación pura; una función por regla de `DT-031`; `RECOMMEND` / `NO_NEED` / `NOT_CALCULABLE`; parámetros V1 en `policy_snapshot` con `policy_set = V1_PROVISIONAL`; sin urgencia |
| API inicial | `docs/07` §7 | Solo lectura; autenticada por defecto salvo `/health`; bloque `provenance` con avisos de dato sintético y política provisional |
| IA generativa | `docs/09` §14 | `ExplanationContext` con cifras almacenadas; plantilla primero; verificación de cifras |
| Seguridad, frontend, Power BI, pruebas | `docs/10` §15, `docs/08` §11, `docs/11` §9, `docs/13` §14 | Dobles locales; vistas frente a contratos; KPIs calculables y bloqueados; capas de prueba por unidad |
| Orden | `DT-047`, `project/roadmap.md` | U1 motor → U2 PostgreSQL + ingesta → U3 forecast → U4 recomendaciones → U5 API → U6 explicación |

**Decisiones que esperan al responsable:** aprobar o cambiar `DT-043` a `DT-047`; cerrar `DT-P14` y
`DT-P15` y `DT-P20` antes de U1; autorizar las dependencias de U2; y resolver la contradicción `DT-P13` antes de
escribir órdenes. `BR-X03` sigue bloqueando cualquier clasificación de riesgo o urgencia.
*(Actualización del 2026-10-01: `DT-P14`, `DT-P15` y `DT-P20` ya están cerradas.)*

## Próximos pasos

0. **U12: ejecutar el despliegue real** (opción C del Key Vault aceptada el 2026-10-08) con
   `infra/azure/u12/README.md` §5 (`-PreflightOnly` → [KeyVaultRole solo si el preflight lo pide] → KeyVault → Secrets → Core → `deploy-u11.ps1` → variables de GitHub →
   Deploy dev → Apps → Bootstrap → Verify → smoke → E2E), y después el redespliegue y las pruebas de fallo de §6.
   Pegar las salidas (sin secretos). U13 no se inicia hasta cerrar U12.
1. **U11: configurar Entra ID y hacer la prueba real** (`infra/azure/entra/README.md`: `deploy-u11.ps1`
   `-SelfTest`, `-PreflightOnly`, ejecución, `-AssignRole VIEWER` y los cinco casos de §4) y pegar la salida y la
   tabla de `/acceso` (sin tokens). Después, **integrar U10 y U11** (commits y PR). *(Antes pedía decidir la
   autorización de U11: autorizada el 2026-10-07, `DT-099`.)* **Integrar U10** (commit y PR de
   `feature/u10-azure-base`, después del PR de U8 y U9). *(Antes pedía desplegar U10: desplegada y verificada el 2026-10-07, identificadores en
   `DT-098`.)* Para U13: comprobar la cuota de Azure OpenAI en `centralus`. **Revisar U9** (`DT-097`: vistas, rol e interpretaciones `PROPUESTA` de cumplimiento en tiempo y en cantidad) y
   decidir la autorización de U10. **Revisar U8 y ver su primera ejecución en GitHub Actions** (PR de la rama de U8): los ocho jobs en verde cierran
   también U7, porque el job `docker` construye con las imágenes oficiales fijadas por digest (`DT-095`, `DT-096`).
   Después, activar la protección de `main` con esos jobs (`docs/12` §2.2) y decidir la autorización de U9. *(Antes
   pedía revisar U7, construirla con las imágenes oficiales y anotar los digests: U7 se integró con el PR #13; los
   digests se fijaron en U8 y los confirma el job `docker`.)* *(Antes pedía revisar y aprobar la
   arquitectura de la Etapa 2, `DT-043` a `DT-047`: aceptada unidad a unidad al autorizar U1–U6.)*
2. **Decidir lo siguiente de la Fase 5** tras la integración de F5c (PR #11, merge commit `6a1d777`). Decisiones pendientes del responsable:
   - adoptar o no la estrategia (b) de `DT-011`, que exigiría una unidad nueva sobre U3 y una DT nueva;
   - autorizar o no F5d (G2 y G3 siguen sin autorizar);
   - la unidad U1b;
   - el ajuste del rótulo de la banda en F7d.

   *(Antes pedía revisar F5c: revisada e integrada en `main` con el PR #11 el 2026-10-06.)* *(Antes pedía implementar F5c, cumplido el 2026-10-06.)* *(Antes pedía revisar G1 y decidir la autorización de F5c: G1 quedó en `main` con el PR #10 y F5c se
   autorizó el 2026-10-06 con `DT-092`; las condiciones abiertas de `docs/05` §20.4 se cerraron para F5c en `DT-093`.)*
   *(Antes pedía revisar F5b y preparar G1: F5b quedó en `main` con el PR #9 y G1 se registró el 2026-10-05 en
   `DT-089` a `DT-091`. Los valores `PROPUESTA` de F5a que G1 no fija siguen sin confirmar (`PROPUESTA`): el SES de
   `DT-076` punto 7, la escala de MASE/RMSSE en `L + R` y el denominador cero.)* *(Este punto pedía implementar F5b, cumplido el 2026-10-05.)* *(Antes pedía revisar F5a, integrada en `main` con el PR #8, y
   confirmar OD-S1 a OD-S4, aceptadas en `DT-088`.)* *(Antes pedía implementar F5a,
   cumplido el 2026-10-05.)* *(Antes pedía elegir la siguiente fase: se eligió la Fase 5 y su cierre documental es del
   2026-10-05.)* *(Antes pedía revisar F7a e integrarla: la Fase 7 completa quedó en
   `main` con los PR #2 a #5 el 2026-10-05.)* *(Antes pedía integrar U1–U6 en `main` e implementar F7a: integración con
   el merge commit `9012a8c` (PR #1) e implementación de F7a el 2026-10-05.)* *(Antes pedía revisar U6, hacer su commit y decidir la siguiente fase: U6
   quedó en `55e0c39` y `5861fda`, publicados, y la Fase 7 se autorizó el 2026-10-05.)* *(Antes pedía implementar U6, cumplido el 2026-10-04.)* *(Antes: revisar U5 y hacer su commit, cumplido en `3eaf696`, y decidir la autorización de U6,
   cumplido el 2026-10-04.)*
   *(Este punto pedía implementar U5, cumplido el 2026-10-03.)* *(Antes: hacer commit de U4, cumplido en `6ddecbd` y `2b764ce`, y decidir la autorización
   de U5, cumplido el 2026-10-03.)* *(Este punto pedía implementar U3, cumplido el 2026-10-02 y con commit en
   `008bd76`, y después cerrar `DT-P18` y `DT-P21`, cumplido el 2026-10-03. El *push* lo hace el
   responsable.)*
3. **Recabar del negocio los parámetros pendientes** (`knowledge/business-rules.md` §3). Es el
   trabajo de mayor valor y no depende de programar nada: sin estos datos, la Fase 4 no puede
   parametrizarse de forma definitiva.
4. **Confirmar o refutar los supuestos de mayor riesgo:** ASSUMPTION-008 (corpus documental),
   ASSUMPTION-004 (el consumo aproxima la demanda), ASSUMPTION-003 (histórico suficiente),
   ASSUMPTION-012 (volumen).
5. **Decidir `DT-P12`:** si la tabla de §25 debe ampliarse con las filas «Alta rotación» y «Baja
   rotación», o si basta con dejar constancia de que §8 y §10.4 la complementan. Es una decisión
   sobre la especificación y **sigue abierta**; `DT-023` no la resuelve.
6. **Mantener sincronizadas ambas copias.** El punto 10 de *Problemas conocidos* quedó resuelto el
   2026-09-21, pero su causa —correcciones aplicadas en la copia de trabajo que no llegaron al
   disco— puede repetirse. Comprobación barata al cierre de cada bloque: `md5sum` del árbol en ambos
   lados.


> **Ningún componente posterior del generador se inicia sin instrucción explícita del responsable.**

## Archivos importantes

| Archivo | Para qué |
|---|---|
| `CLAUDE.md` | **Leer primero.** Reglas permanentes del proyecto |
| `AGENTS.md` | Protocolo de trabajo de los agentes de IA |
| `project/status.md` | Este archivo: dónde está el proyecto ahora |
| `project/roadmap.md` | Fases, dependencias y criterios de finalización |
| `project/backlog.md` | Épicas, historias y prioridades |
| `docs/01-requerimientos.md` | Qué debe hacer el sistema |
| `docs/03-arquitectura.md` | Cómo está organizado |
| `docs/06-motor-abastecimiento.md` | El núcleo de valor del sistema |
| `docs/15-decisiones-tecnicas.md` | Por qué se decidió cada cosa |
| `knowledge/assumptions.md` | Qué se ha dado por cierto sin confirmar |
| `knowledge/business-rules.md` | Qué falta que el negocio defina |
| `knowledge/dataset-specification.md` | **Especificación del dataset.** Lectura obligatoria para cualquier trabajo de la Fase 1 |
| `docs/decisions/DT-023-clasificacion-escenarios.md` | Matriz de las 26 situaciones de §25 y su reparto en Niveles A/B/C |
| `docs/decisions/DT-024-contrato-salida-componente-2.md` | Contrato de salida: CSV por entidad y columnas de las cinco entidades maestras |
| `docs/decisions/DT-025-manifest-metadata-generacion.md` | Contrato de `manifest.json` |
| `docs/decisions/DT-027-vigencia-producto.md` | `valid_from` / `valid_to` frente a `created_at` / `updated_at` |
| `docs/decisions/DT-028-politicas-generacion-sintetica.md` | **Valores sintéticos del Componente 2.** Leer la advertencia de cabecera antes de citar cualquier cifra |
| `data/synthetic/config/config.py` | Componente 1: el contrato de configuración del generador |
| `data/synthetic/config/dataset_config.yaml` | La configuración vigente del dataset sintético |
| `docs/decisions/DT-036-politicas-sinteticas-inventario.md` | **Valores sintéticos del Componente 4** |
| `docs/decisions/DT-038-contrato-salida-c4.md` | Contrato de salida y precondiciones del Componente 4 |
| `data/synthetic/generator/inventory.py` | Componente 4: el simulador de inventario |
| `docs/decisions/DT-041-asignacion-escenarios-c7.md` | Contrato del Componente 7. **Leer la advertencia `SYNTHETIC_COVERAGE_CRITERION`** antes de citar un criterio |
| `data/synthetic/generator/scenarios.py` | Componente 7: `scenario_assignment` |
| `docs/decisions/DT-042-validador-dataset-quality-report.md` | Contrato del Componente 8 y del informe de calidad |
| `data/synthetic/generator/validator.py` | Componente 8: validación y `quality_report` |

## Historial de actualizaciones

| Fecha | Cambio |
|---|---|
| 2026-09-03 | Creación del repositorio y ejecución completa de la Etapa 0 |
| 2026-09-04 | **Etapa 0.1** — auditoría y corrección. 15 problemas, 35 correcciones. `DT-019`–`DT-022`, `RML-013`, `US-034`, `US-035`, `US-058`, `ASSUMPTION-019`, `ASSUMPTION-020`. Resultado: APROBADA CON OBSERVACIONES |
| 2026-09-14 | **Fase 1 — Datos, autorizada.** Componente 1 `DatasetConfig` implementado y probado (37 pruebas en verde). Estructura `data/synthetic/`. El dataset todavía no se genera |
| 2026-09-15 | Corrección: `knowledge/dataset-specification.md` **sí existía**; el informe del 14-09 lo dio por inexistente al inspeccionar una copia de trabajo desactualizada en lugar del repositorio real. Copia resincronizada y verificada contra el disco. Contrastado `DatasetConfig` con la especificación: coherente, salvo el desajuste de escenarios registrado como problema 8 |
| 2026-09-16 | Auditoría de la discrepancia 14 vs. 26 escenarios. Conclusión: tres niveles, no dos listas |
| 2026-09-17 | **`DT-023` aceptada.** Enum `Scenario` ampliado de 14 a 16 (`LOW_INVENTORY`, `PARTIAL_DELIVERY`); matriz de las 26 situaciones en `docs/decisions/DT-023-clasificacion-escenarios.md`; 46 pruebas en verde. Problema 8 cerrado |
| 2026-09-17 | **Auditoría del Componente 1: NO APROBADA y corregida.** Recuento de la matriz de §25 rectificado (13 A + 9 B + 4 C = 26, antes 11 + 9 + 5); `_parse_scale` acumula ya todos los errores de tipo; `validate()` comprueba lista no vacía, ausencia de duplicados y orden canónico; `required_scenarios` pierde su valor por defecto; pruebas ampliadas de 46 a **54, todas en verde**. La clasificación A/B/C no se rediseñó. Componentes 2–8: no iniciados |
| 2026-09-17 | **Auditoría del Componente 2** (solo lectura). Estructura de las cinco entidades maestras definida; siete bloqueantes B-1 a B-7 identificados. No se modificó ningún archivo |
| 2026-09-18 | **Bloqueantes B-1 a B-7 resueltos documentalmente.** `DT-024` (CSV por entidad), `DT-025` (`manifest.json`), `DT-026` (`data_origin` en maestras), `DT-027` (`valid_from` / `valid_to`), `DT-028` (políticas de generación sintética), `DT-029` (alcance del C2), `DT-030` (sub-semillas). Actualizados `docs/04`, `knowledge/dataset-specification.md` (§§41–44) y `docs/15`. **El Componente 2 sigue sin implementar**; sin código nuevo, 54 pruebas en verde |
| 2026-09-18 | **Auditoría de consistencia post-decisiones.** Cuatro revisiones independientes sobre `DT-024`–`DT-030`: **seis bloqueantes encontrados y corregidos** (semántica del intervalo de vigencia, proveedores huérfanos, `valid_to` degenerado, bucle de suelo ambiguo, sub-semilla sin identificador definido, invariante de reproducibilidad en cuatro versiones incompatibles) más ocho correcciones menores. Quedan **tres cuestiones abiertas que requieren decisión del responsable**. Veredicto: **NO APTO para autorizar C2 todavía**. Sin cambios de código; 54 pruebas en verde |
| 2026-09-19 | **`DT-031` — V1: reglas mínimas funcionales** (`PROPUESTA`). Ocho reglas que hacen calculable `Forecast → Inventory → Supply Engine → Recommendation` sin fijar ninguna política: `raw_need`, posición de inventario, horizonte, demanda sobre el horizonte, stock de seguridad, MOQ/múltiplo, escenarios de demostración y alcance del validador. Cinco ya estaban documentadas. `ASSUMPTION-021/022/023`. Corregida la contradicción de `docs/06` §14. Sin cambios de código; 54 pruebas en verde |
| 2026-09-19 | **Decisiones A–F confirmadas.** Ocho componentes sin rediseño · `R_v1 = 7` · `z_v1 = 1,65` · **`observed_lead_time` sustituye al acordado** (`V1-09`, con fallback) · MOQ y múltiplo independientes · **4 reglas pendientes cerradas** con interpretación técnica (`BR-X05`, `BR-X07`, `BR-X08`, `BR-X09`). `DT-031` pasa de ocho a diez reglas. `ASSUMPTION-024`. Sin cambios de código; 54 pruebas en verde. **El Componente 2 queda listo para implementar** |
| 2026-09-21 | **Reglas V1 CERRADAS.** Confirmados `V1-09` (mínimo 3 observaciones), `V1-09.1` (ventana de 12 por fecha de finalización), `V1-09.2` (techo de 90 días con trazabilidad) y `V1-10` (proveedor preferente activo). Añadidas `V1-11` (sin diferenciación ABC, sin eliminar el campo), `V1-12` (sin sobre-recepción) y `V1-13` (sin inventario negativo). `DT-031` pasa a **`ACEPTADA` como conjunto de reglas de V1** con trece reglas; `docs/15` v1.4. Los trece casos de prueba pedidos **no son ejecutables todavía** (motor = Fase 4; validador = Componente 8) y quedan registrados con su dueño en lugar de escribirse. Sin cambios de código; **54 pruebas en verde**. Detectada y **resuelta** en este mismo cierre una divergencia de **seis** documentos entre la copia de trabajo y el disco (punto 10 de *Problemas conocidos*). **C2 LISTO PARA INICIAR** |
| 2026-09-21 | **Componente 2 implementado y probado.** `Catalog Generator`: cinco entidades maestras + `manifest.json`, en `generator/{rng,policies,writer,catalog,__main__}.py`. `DT-032` (flujo contador sobre SHA-256, cierra el límite conocido de §44) y `DT-033` (versionado derivado). Eliminado `generator/config.py` con autorización. Revisión adversarial independiente: **5 defectos reales corregidos** (desbordamiento del ancho de códigos, bucle infinito latente en `below`, `Z` sin convertir a UTC, red de seguridad incompleta, literal fuera de `DT-028`). Pruebas: **54 → 155, todas en verde**. `black` limpio. C3 **no iniciado** |
| 2026-09-21 | **Identificadores canónicos de componente fijados** (`DT-030`, `docs/15` v1.6). Tabla de los ocho componentes; `catalog` sin cambios, siete nuevos. `COMPONENT_IDS` en `rng.py` y nueve pruebas que los fijan contra la fórmula. Resuelta la cuestión **Quality Report vs Validator**: forma parte del Componente 8, según `DT-023`, `DT-025`, `status.md` y `DT-031` — ninguna decisión aceptada propuso un noveno componente. El Componente 2 no se modificó y su salida es byte a byte idéntica. Pruebas: **155 → 164, todas en verde**. C3 **no iniciado** |
| 2026-09-23 | **Componente 3 implementado y probado.** `Demand Generator`: `demand.csv` con 108 235 filas de **demanda latente**, producto × ubicación × día. `DT-034` (la demanda latente se persiste, separada del consumo observado; entidad `Demand` en `docs/04`; periodo semiabierto; serie densa; cantidades enteras) y `DT-035` (políticas sintéticas de demanda: dos ejes ortogonales, onda triangular en vez de senoidal por reproducibilidad, intermitencia con mecanismo propio). `generator_version` 0.1.0 → 0.2.0. Los ocho comportamientos son **verificables midiendo la serie**, no leyendo una etiqueta. Pruebas: **164 → 235, todas en verde**. `black` limpio. C4 **no iniciado** |
| 2026-09-26 | **Componente 4 implementado y probado, sin conectar a `__main__`.** `Inventory Simulator`: `consumption.csv`, `inventory_movements.csv` e `inventory.csv` más las órdenes causales en memoria para C5. Decisiones **D-C4-1 = O1** (`DT-037` §3 enmendado: `q2` nunca es cero), **D-C4-2 = P1** (precondiciones P-C4-2 y P-C4-3 en `DT-038` §16) y **D-C4-3** (lead time acordado, `M` solo en la apertura, disparo diario). `metrics` de `DT-038` §12 **no implementado**: sus definiciones no existen. `generator_version` sigue en 0.2.0; `output/` intacto. Pruebas: **235 → 323, todas en verde**. C5 y C6 **no iniciados** |
| 2026-09-27 | **D-01 cerrado — elegibilidad de las `CANCELLED` sintéticas (opción A).** `DT-039` §5.2 punto 1: cierre previsto `issued_on + ORDERS_CANCELLED_CLOSE_LAG_DAYS` `< end_date` **y** `<= valid_to` (o nulo); filtrado antes de `K` y de la selección; B2 intacta; sin recorte de `closed_at`; `DT-027` **sin cambios**. `docs/15` v1.12. Pruebas de contrato de la regla: **323 → 335, todas en verde**. C5 **no implementado**; `generator_version` 0.2.0 |
| 2026-09-28 | **Componente 5 implementado y probado, sin conectar a `__main__`.** `Purchase Order Generator`: `purchase_orders.csv`, `purchase_order_items.csv` y `purchase_order_receipts.csv` materializados desde el `SimulationResult` de C4 sin recalcular nada; `order_number` para todas las órdenes; órdenes `CANCELLED` sintéticas según `DT-039` §5.2 con la elegibilidad de D-01 (filtrado antes de `K`, B2 y selección; `closed_at` sin recorte). `DT-039` §13 registra dónde vive cada regla; ninguna cambia. `generator_version` 0.2.0; `output/` intacto. Pruebas: **335 → 390, todas en verde**. C6 **no iniciado** |
| 2026-09-28 | **Componente 6 implementado y probado, sin conectar a `__main__`.** `Supplier Behaviour Generator`: un `SupplierProfile` por proveedor, en memoria, con los valores y mezclas de `DT-037` §2 y las dos secuencias de §4; sin archivos de datos, solo su entrada en el manifiesto (A1); tipo importado de C4 (A2). `DT-037` §6 registra la implementación; `DT-040` §3 corregido (O1); comentarios obsoletos de C4 corregidos (O2). `generator_version` 0.2.0; `output/` intacto. Pruebas: **390 → 430, todas en verde**. Siguiente: W1, pendiente de autorización |
| 2026-09-28 | **Pendientes de C5 cerrados.** La auditoría independiente de `test_orders.py` recalcula ahora la **selección exacta** de las plantillas `CANCELLED` (universo, `K` y permutación `cancelled-selection`) sin llamar a C5, y `ExactSelectionTests` la compara orden a orden; `DT-039` §13 ya no dice que el Componente 6 no existe. Sin cambios en C4, C5 ni C6. Pruebas: **430 → 434, todas en verde**. **W1 no iniciado**: se detiene antes de implementar por dos decisiones pendientes (versión 0.3.0 del artefacto y mecanismo de promoción de `DT-040` §5 frente a «sin rollback») |
| 2026-09-29 | **W1 implementado; dataset completo publicado.** `pipeline.run` (comprobación previa, workspace `tmp/<uuid>/`, C2 → C3 → C6 → C4 → C5, verificación final, promoción de `DT-040` §5) y `__main__.py` conectado a él. `GENERATOR_VERSION` **0.2.0 → 0.3.0** (`DT-036` §8). Detalles pendientes de `DT-040` resueltos por el responsable (`.anterior` y workspace fallido se eliminan). Publicado `ds-269a698250db`. Pruebas: **434 → 463, todas en verde** |
| 2026-09-29 | **Componente 7 implementado y probado, sin integrar en W1.** `DT-041` (contrato de `scenario_assignment`: 16 ejes × seis campos; unidad `supplier` para los ejes de proveedor; criterios `SYNTHETIC_COVERAGE_CRITERION` para `LOW_INVENTORY`, `OVERSTOCK` y las situaciones 12 y 18, que no son reglas de negocio). `scenarios.py`; `writer.py` gana `SCENARIOS_VERSION` y `add_manifest_field`. Notas en `DT-030` y `DT-031` (`V1-07`, `V1-08`); `docs/15` v1.16. C2–C6, `pipeline.py`, `generator_version` 0.3.0 y `output/` sin cambios. 19 de 19 mutaciones detectadas. Pruebas: **463 → 509, todas en verde**. Siguiente: C8 |
| 2026-09-29 | **Generador 0.4.0 terminado.** `DT-042` y `validator.py` (51 comprobaciones sobre el workspace, `quality_report` con los veinte ítems de §35, `anomalies: []`); C7 y C8 integrados en W1; `verify` exige `scenario_assignment` y un informe sin fallos; `GENERATOR_VERSION` **0.3.0 → 0.4.0** (un solo incremento). Publicado `ds-6c8ad65b4999`: 51/51, 0 fallos, 16/16 escenarios, nivel C 4/4, reproducible salvo `generated_at`. Documentación: `DT-025`, `DT-033`, `DT-038` §12 (`metrics` cerrado), `DT-040`, `DT-041`, especificación §34/§35/§39/§40/§41.3/§42.3, `docs/15` v1.17, `CLAUDE.md`, informe en `docs/reports/`. Pruebas: **509 → 582, todas en verde** |
| 2026-09-30 | **Etapa 1 COMPLETADA · Etapa 2 INICIADA — arquitectura y fundación.** Lectura completa de la documentación, auditoría del dataset `ds-6c8ad65b4999` como fuente y diseño del sistema principal sin código: `DT-043` a `DT-047` (`PROPUESTA`) y `DT-P13` a `DT-P21`. Actualizados `docs/03` §16, `docs/04` §9, `docs/05` §19, `docs/06` §16, `docs/07` §7, `docs/08` §11, `docs/09` §14, `docs/10` §15, `docs/11` §9, `docs/13` §14, `docs/15` v1.18, `project/roadmap.md`, `CLAUDE.md` (cabecera y §17), `README.md` (estado) y este archivo. Primera unidad propuesta: motor V1 (U1). Sin cambios en el generador ni en el dataset; **582 pruebas en verde** |
| 2026-09-30 | **U1 autorizada; detenida antes de escribir código.** `DT-P15` cerrada (la decisión es `as_of_date`; `as_of_date + 1` es solo el inicio del horizonte; corrige la propuesta de `DT-045`) y `DT-P20` cerrada (rige V1 en demanda cero, lead time cero y `σ = 0`, `docs/06` §16.10). `DT-P14` resuelta en cinco de sus ocho elementos y **abierta** en tres sin respaldo documental. `DT-043` y `DT-045` `ACEPTADA`, `DT-047` aceptada en cuanto a U1 (`docs/15` v1.19). `PyYAML==6.0.3` en `data/synthetic/requirements.txt`. Rama `feat/u1-supply-engine`. Sin código nuevo; **582 pruebas en verde** |
| 2026-10-01 | **`DT-P14` cerrada.** Estimador poblacional; `n = 0` → `NOT_CALCULABLE` (`INSUFFICIENT_HISTORY`), `n = 1` → `σ_H = 0`; evaluación exacta **B3** de `x = P + √B/D` para toda decisión, con `ceil` exacto por `isqrt` y comparación de signo antes del cuadrado; `z_v1 = 33/20`; entradas sin `float`; 28 cifras significativas y `ROUND_HALF_EVEN` solo para informar. Actualizados `docs/06` (v1.3: §16.3, §16.5, §16.6, §16.9, §16.10), `docs/15` (v1.20), `project/roadmap.md` y este archivo. Ninguna fórmula V1 cambia. **U1: AUTORIZADA — NO IMPLEMENTADA**; 582 pruebas en verde |
| 2026-10-01 | **Contrato de U1 cerrado.** Nueve decisiones del responsable registradas como `DT-048` (cobertura del forecast: `K(H) = ⌈H/7⌉`), `DT-049` (vigencia en `as_of_date`; razones independientes; horizonte que cruza `valid_to` → `NOT_CALCULABLE` sin recortar `H`), `DT-050` (orden `completed_on ↓, issued_on ↑`; A-1: techo de 90 sobre cualquier procedencia), `DT-051` (tipos; `Fraction` decide y `Decimal` solo representa; `S` añadido a §16.6 punto 7; `missing_policy_parameters`; orden de razones y marcas; salida parcial con `NOT_CALCULABLE`; `engine_version = "0.1.0"`; A-2: sin `abc_class`) y `DT-052` (`InvalidInputError`, primer error en orden canónico; `on_hand < 0` → `NEGATIVE_ON_HAND`). Nuevo pendiente **`DT-P22`** (razón del cruce de `valid_to`). Actualizados `docs/06` (v1.4: §16 cabecera, §16.3, §16.4, §16.5, §16.6 punto 7, §16.8, §16.11), `docs/15` (v1.21), `docs/13` (v1.3, §3.1), `project/roadmap.md` (v1.3) y este archivo; correcciones de estado de `DT-043`/`DT-045`/`DT-047` en `docs/03` §16, `CLAUDE.md` §17 y `project/backlog.md`. Ninguna fórmula V1 ni regla B3 cambia; `DT-031` intacto. Sin código; **U1: AUTORIZADA — NO IMPLEMENTADA**; 582 pruebas en verde |
| 2026-10-01 | **`DT-P22` cerrada (opción (a)).** `PRODUCT_OUT_OF_VALIDITY` pasa a significar que el producto no es válido durante todo el periodo requerido por U1: caso A (`as_of_date` fuera de vigencia) y caso B (`valid_to` no nulo, `as_of_date ≤ valid_to < as_of_date + H`). En ambos, `NOT_CALCULABLE` con esa razón; sin razón nueva, sin recortar `H` ni el forecast, sin extrapolar. Actualizados `docs/06` (v1.5: §16.5, §16.11, §16.11.2, §16.11.4), `docs/15` (v1.22: `DT-045`, `DT-049`, `DT-051`, tabla de pendientes), `CLAUDE.md` §17, `project/roadmap.md` y este archivo. **Contrato de U1 cerrado, sin pendientes.** Ninguna fórmula V1 ni regla B3 cambia; `DT-031` intacto. Sin código; **U1: AUTORIZADA — NO IMPLEMENTADA**; 582 pruebas en verde |
| 2026-10-01 | **U1 implementada.** Antes de codificar: `DT-053` (frontera de la salida parcial: magnitudes descriptivas conservables, `raw_need`/`Q_moq`/`Q_final` solo sin razones; exclusión con `PRODUCT_INACTIVE` y caso A) y `DT-054` (se retira la monotonía global de `S` frente a `L`; contraejemplo auditado) en `docs/06` §16.8, §16.11.6, §16.11.7, `docs/13` §3.1 y `docs/15` v1.23. Código: `backend/pyproject.toml` (Python ≥ 3.11, sin dependencias) y `backend/app/supply_engine/` (`contract`, `validation`, `exact`, `rules`, `engine`). **146 pruebas** en `backend/tests/supply_engine` (pureza, contrato, B3 contra oráculo, validación, reglas, evaluación, invariantes sembrados). `docs/06` §16.12 (v1.7), `CLAUDE.md` §14 y §17, `project/roadmap.md` (v1.5) y este archivo. Generador: **582 pruebas en verde**; dataset sin cambios. Sin commit ni push |
| 2026-10-01 | **U1 cerrada.** Auditoría contractual post-implementación (solo lectura): contrato, pureza, validación, B3, lead time, horizonte, forecast, `σ_H`/`SS`/`S`, `DT-P22`, `DT-053`, `DT-054`, MOQ y múltiplo, `NO_NEED` e invariantes en PASS; sin hallazgos BLOCKER, HIGH ni MEDIUM. Hallazgo LOW no bloqueante F-1: `as_of_date = date.max` lanza `OverflowError` al calcular `as_of_date + 1`; no se corrige porque exigiría una regla nueva sobre el dominio temporal, sin necesidad en el proyecto. El responsable ratificó las dos interpretaciones de `docs/06` §16.12 (cantidades racionales con `Fraction`; `model_version` como identificador entero opaco); `NO_NEED` ya era normativo. Solo documentación: `docs/06` §16.12 y este archivo. Código, pruebas, generador y dataset sin cambios; U1 146/146 y generador 582/582. Sin commit ni push |
| 2026-10-01 | **U2 implementada.** `DT-044` `ACEPTADA` (cantidades `numeric`; `quantity_on_hand ≥ 0` compatible con `BR-X09`/`V1-13`), `DT-047` aceptada para U2 y `DT-055` (PostgreSQL 16, `psycopg[binary]==3.3.6` opcional en `backend[db]`, migraciones SQL en `backend/db/migrations/`, `infra/docker-compose.yml`, dos suites) en `docs/15` v1.24. Código: `backend/app/db/` (`connection`, `migrations`, `__main__`), `backend/app/ingestion/` (`contract`, `dataset`, `mapping`, `loader`, `__main__`), `0001_dataset_tables.sql` (doce tablas + `data_loads`). **Primera carga real** de `ds-6c8ad65b4999`: `COMPLETED`, 321 043 filas, seis invariantes en verde; repetición `ALREADY_LOADED`. Pruebas: 35 sin base (suite por defecto: 181 con U1) y 43 contra PostgreSQL real (esquema, restricciones, carga, idempotencia, conflictos, *rollback* y reintento). `docs/04` §9.9 (v1.5), `docs/03` §16.6, `CLAUDE.md` §14 y §17, `project/roadmap.md` y este archivo. Validado contra PostgreSQL 16 local: Docker no pudo descargar imágenes en el contenedor de trabajo. Generador 582 en verde; dataset sin cambios. Sin commit ni push |
| 2026-10-01 | **U2 validada en Docker.** Commit de U2: `9d88ff8` (sin push). En la máquina del responsable, `infra/docker-compose.yml` levantó `postgres:16-alpine` (PostgreSQL 16.15) `healthy`; contra esa instancia, migraciones (repetición sin cambios), primera carga `COMPLETED`, segunda `ALREADY_LOADED`, integración 43/43 y suite por defecto 181/181. Se cierra la verificación de infraestructura pendiente. Solo documentación: `docs/04` §9.9 y este archivo |
| 2026-10-02 | **U3: cierre documental y autorización.** `DT-P17` cerrada por `DT-056` (baselines V1: definiciones, intervalo empírico nearest-rank 10/90 con `confidence_level = 0.80` nominal y mínimo operacional de 11 errores, mínimos de 25/37/63 semanas, media móvil como referencia provisional no seleccionada por desempeño, consumo observado bruto como proxy durante el desabasto, catálogo activo y vigente en `as_of_date`, precisión `Decimal` de 6 decimales); `DT-046` `ACEPTADA`; `DT-057` (persistencia, idempotencia y ejecución); `DT-047` aceptada para U3; nueva `DT-P23`. `docs/15` v1.25, `docs/05` v1.3 (§6, §19, §19.8, §19.9), `docs/04` v1.6 (§3.14, §9.6, §9.10), `docs/03` v1.4 (§4, §5.1, §16), `project/roadmap.md` v1.6, `CLAUDE.md` §17 y este archivo. **U3 no implementada**: sin código, sin migración, sin pruebas. `DT-011`, `DT-P21` y `DT-P23` siguen abiertas. Sin commit ni push |
| 2026-10-02 | **U3 implementada y validada.** `backend/app/forecasting/` (contrato, aritmética exacta, semanas ancladas, baselines, intervalo empírico nearest-rank 10/90, cadena primaria; solo biblioteca estándar), `backend/app/runs/` (configuración y `config_sha256`, ejecución `forecast` con bloqueo, idempotencia y *rollback*) y migración `0002_forecast_tables.sql`. Pruebas nuevas: `tests/forecasting` (60), `tests/runs` (7) y `tests/db/test_forecast_*` (32); tres pruebas de U2 ampliadas solo por la migración `0002`. Ejecución real con `as_of_date = 2025-12-31` sobre `ds-6c8ad65b4999`: `COMPLETED`, 95 productos con forecast, 5 excluidos (`INACTIVE_OR_OUT_OF_VALIDITY`), 3 990 filas y 1 330 primarias de la media móvil, sin respaldos; la repetición da `ALREADY_COMPUTED` sin escribir; un fallo controlado deja `FAILED` y ninguna fila. Suite por defecto 248/248, integración 75/75 (local y Docker), U1 146/146, generador 582/582; dataset sin cambios. `status.md`, `roadmap.md`, `CLAUDE.md` §14 y §17, `docs/05` §19 (v1.4, §19.10) y `docs/04` §9.10 (v1.7) registran el hecho; ninguna decisión cambia. Sin commit ni push |
| 2026-10-03 | **U4: cierre documental y autorización — no implementada.** `DT-P18` cerrada por `DT-059` (una fila inmutable por evaluación con los tres `outcome`; sin `status`, `resolved_*` ni `urgency`; `NOT_CALCULABLE ≠ FAILED`) y `DT-P21` por `DT-058` (un forecast por corte; U4 no lanza forecasts). `DT-060` (`forecast_id` = fila h=1), `DT-061` (`forecast_run_id`), `DT-062` (`ENGINE_VERSION` de U1, `policy_set = V1_PROVISIONAL`, idempotencia) y `DT-063` (solo cargas `SYNTHETIC`; `DT-P16` sigue abierta), todas `ACEPTADA`; `DT-047` aceptada para U4. `input_sha256` = SHA-256 de la representación JSON canónica y normalizada de `EvaluationInput` (verifica; la reconstrucción usa la carga inmutable, las reglas de lectura versionadas y `calculation_inputs`). Documentos: `docs/15` v1.26, `docs/04` v1.8, `docs/05` v1.5, `docs/06` v1.8, `docs/07` v1.3, `docs/13` v1.6, `docs/03` v1.5, `roadmap` v1.8, `CLAUDE.md`. Solo documentación: sin código, migración ni pruebas de U4 · sin commit |
| 2026-10-03 | **U4 implementada y validada.** `backend/app/runs/recommendation_inputs.py` (adaptador puro), `recommendation_config.py` (representación exacta, `input_sha256` sobre la representación JSON canónica y normalizada, `config_sha256`), `recommendation.py` (precondiciones `DT-058`/`DT-061`/`DT-063`, bloqueo *advisory*, una transacción, `FAILED` aparte) y migración `0003` (`recommendations` con sus `CHECK` e inmutabilidad; `forecast_run_id` y `engine_version` en `calculation_runs`); subcomando `recommend`. Ejecución real 2025-12-31: `COMPLETED`, 100 evaluaciones (50 `RECOMMEND`, 40 `NO_NEED`, 10 `NOT_CALCULABLE`); repetición `ALREADY_COMPUTED`; otro corte rechazado; *rollback* en copia temporal (`FAILED`, 0 filas) y reintento `COMPLETED`. Pruebas: 295 por defecto y 113 de integración, en local y en Docker; generador 582. U1 y dataset sin cambios · sin commit |
| 2026-10-03 | **U5: cierre documental y autorización — no implementada.** `DT-064` (FastAPI 0.141.1, Starlette 1.3.1, Pydantic 2.13.5, uvicorn 0.52.4; `TestClient` con `httpx2` 2.13.1, porque Starlette 1.3.1 lo importa y deja `httpx` como alternativa obsoleta; resolución verificada en PyPI el 2026-10-03 sin instalar), `DT-065`, `DT-066` y `DT-067` (desviación estándar poblacional) `ACEPTADA`; `DT-047` aceptada para U5. Documentos: `docs/15` v1.28, `docs/07` v1.4, `docs/10` v1.3, `docs/03` v1.6, `docs/13` v1.7, `docs/12` v1.2, `docs/11` v1.3, `roadmap` v1.10, `CLAUDE.md`. Solo documentación · sin commit |
| 2026-10-03 | **U5 implementada y validada.** `backend/app/api/` (aplicación, `TokenValidator` de desarrollo, roles, errores, `X-Correlation-ID`, paginación, `provenance`, historia, esquemas y siete routers) y `backend/app/db/read/` (consultas de solo lectura); `.env.example`; grupos `api` y `test` de `backend/pyproject.toml` instalados con las versiones exactas de `DT-064` (`TestClient` con `httpx2`, sin `httpx`). Trece endpoints; `TokenValidator` de desarrollo con tokens `dev-…`, solo `APP_ENV=local`; matriz de roles explícita; errores uniformes con `correlation_id`; selección de ejecución de `DT-066` probada con ejecuciones construidas (mayor `as_of_date`, empate por mayor `id`, `FAILED` y otras cargas ignoradas, `run_id` inexistente, de otro tipo o no completado → 404); historia de `DT-067` (desviación poblacional); conexión `read_only` (SQLSTATE 25006) y ninguna escritura. 295 pruebas por defecto, 56 de la API sin base, 142 de integración (29 nuevas de U5) y 582 del generador en verde, en local y en Docker. Documentos: `docs/07` v1.5, `docs/13` v1.8, `docs/15` v1.29, `roadmap` v1.11, `CLAUDE.md` · sin commit |
| 2026-10-04 | **U6: cierre documental y autorización — no implementada.** `DT-068` (endpoint 14 `GET /api/v1/recommendations/{recommendation_id}/explanation` —U5 = 13 endpoints—, Bearer y los cuatro roles, respuesta y estados, `ExplanationContext`, `facts[]` cerrado con `on_hand` y `reserved` y sin `z`, `sigma_h` ni la demanda sobre el plazo, `unit_of_measure` como metadato, plantillas `RECOMMEND`/`NO_NEED`, `NOT_CALCULABLE` estructurado, `template/1.0.0`, inmutabilidad, arquitectura `api → genai`, fuera de U6 `DocumentRetriever` y prioridad/riesgo/urgencia) y `DT-069` (`display` con 6 decimales `ROUND_HALF_EVEN` sin ceros finales, cifra narrativa = `-?\d+(?:\.\d+)?` igual a algún `display`, `UnverifiedFigureError` → HTTP 200 `DEGRADED` con `NARRATIVE_UNVERIFIED`, provisionalidad) `ACEPTADA`; `DT-047` aceptada para U6. Documentos: `docs/15` v1.30, `docs/09` v1.3 (§14.5 y §14.6), `docs/07` v1.6, `docs/03` v1.7, `docs/13` v1.9, `backlog` v1.3, `roadmap` v1.12, `CLAUDE.md`. Solo documentación · incluida en el commit `55e0c39` |
| 2026-10-04 | **U6 implementada y validada.** `backend/app/genai/` (solo biblioteca estándar), endpoint 14 `GET /api/v1/recommendations/{recommendation_id}/explanation` y lectura aditiva de `unit_of_measure`; `template/1.0.0`; las 100 evaluaciones reales explicadas (50 + 40 `VERIFIED`, 10 `NOT_APPLICABLE`, ninguna `DEGRADED`). 353 pruebas en la suite por defecto (295 + 58 de `tests/genai`), 56 de la API sin base, 151 de integración (142 + 9 de `test_api_explanation.py`), 146 de U1 y 582 del generador en verde, en local y en Docker. Documentos: `docs/09` v1.4, `docs/07` v1.7, `docs/03` v1.8, `docs/13` v1.10, `docs/15` v1.31, `roadmap` v1.13, `CLAUDE.md` · commits `55e0c39` y `5861fda`, publicados |
| 2026-10-05 | **Fase 7: cierre documental y autorización — no implementada.** `DT-070` `ACEPTADA` (F7-01 a F7-24): alcance V1 (US-070, US-072 sin «bajo el punto de reorden», US-073 sin acciones, US-074, US-048, historial, US-075 nominal; fuera US-071 y US-076 por `BR-X03`), rutas con filtros en la URL, token `dev-…` en memoria validado con `/me`, matriz de roles explícita, `CalculationBreakdown` en dos niveles (`facts[].display` + términos exactos), banda nominal 0.80 separada de la historia, explicación de U6, `notices` permanentes, Vitest + Testing Library, stack con versiones fijadas (verificadas el 2026-10-05), `es-MX` / `America/Mexico_City`, proxy de `/api`, partición F7a–F7d y PR previo a `main` con merge commit. Documentos: `docs/15` v1.32, `docs/08` v1.2 (§12), `docs/03` v1.9, `docs/12` v1.3, `docs/13` v1.11, `roadmap` v1.14, `status.md` (estado de U6 corregido: commits `55e0c39` y `5861fda`), `CLAUDE.md`. Solo documentación · sin commit |
| 2026-10-05 | **F7a implementada y validada.** Integración previa de U1–U6 en `main` con el merge commit `9012a8c` (PR #1, sin *squash* ni *rebase*; incluye el cierre documental `4752e32`). `frontend/` (Fase 7, US-070): Vite + React + TypeScript + React Router + TanStack Query con las versiones exactas de `DT-070`, `AppShell` y navegación por rol, rutas estables (`/productos`, `/inventario`, `/recomendaciones`, `/predicciones`, `/ejecuciones/:runId` y sus detalles) con F7b–F7d «En construcción», `AuthProvider` en memoria con el puerto `Authenticator`, cliente `/api` con proxy de Vite y tipos de `openapi-typescript` (`calculation_inputs` tipado a mano), `ErrorState`, `EmptyState`, `LoadingSkeleton`, `NoticeBanner`, formato `es-MX` / `America/Mexico_City`, tokens de diseño y puntos de corte 48rem y 64rem. 121 pruebas en verde, más lint, `tsc`, Prettier y build, con Node 24.21.0 y npm 11.19.0; recorrido por el proxy contra la API real (401, 403, 422, `X-Correlation-ID`). `backend/` y U1–U6 sin cambios · rama `feature/frontend-shell`, sin push |
| 2026-10-05 | **F7b implementada.** Productos e inventario (US-072): `FilterForm`, `Pagination`, `SortNote` y `QueryView`; lista y detalle de producto (maestro, inventario al corte, proveedores); lista de inventario y vista propia `/inventario/:id` con líneas abiertas y la unidad del producto. Corrección: la regla `display` normaliza enteros como `app.genai` (`-0` → `0`). Decisiones del responsable: ramas encadenadas (desviación puntual de `DT-070` punto 21: F7b sale de `feature/frontend-shell`; un PR por unidad, en orden y con merge commit), detalle de producto por secciones y `/inventario/:id` como vista propia. 131 pruebas en verde; validación final en Node 24 pendiente de la revisión del responsable · sin push |
| 2026-10-05 | **F7c implementada.** Recomendaciones (lista sin acciones ni urgencia), detalle con `ProvenancePanel`, explicación de U6 (`VERIFIED`, `DEGRADED` «Explicación no disponible» con `facts` y desglose, `NOT_APPLICABLE` con `reason_details`) y `CalculationBreakdown` en dos niveles (`DT-070` punto 15); evaluación del producto en su detalle (404 = vacío); detalle de ejecución para PLANNER y ADMIN. Pruebas con respuestas reales de la API sobre el dataset 0.4.0; 140 en verde; validación final en Node 24 pendiente · sin push |
| 2026-10-05 | **F7d implementada; Fase 7 completa a falta de revisión.** Predicciones (series primarias, banda nominal `confidence_level`, aviso `INSUFFICIENT_HISTORY`, historia y forecast separados) y, en el detalle de producto, gráfico de banda con Recharts 3.10.1 (+ `react-is` 19.3.0, `DT-070` punto 20) con la tabla exacta como alternativa textual e historial de consumo para ANALYST, PLANNER y ADMIN. Única conversión de cifras a número: `src/charts/chartValues.ts`, solo para la geometría del gráfico. Revisión visual en Chromium: corregida la banda invisible. 148 pruebas en verde; validación en Node 24 pendiente · sin push |
| 2026-10-05 | **Fase 7 completada.** PR #2 a #5 integrados en orden con merge commit (`44280ce`, `198df24`, `1ad2916`, `22f1805`); `main` = `feature/frontend-forecasts`. Validación del responsable en Node 24.21.0 / npm 11.19.0 sobre `main`: lint, `tsc`, Prettier, 148 pruebas y build. Cierre documental: `DT-070` (estado e *Implementación*), `docs/08` §12.1, `docs/03` §16.2, `docs/13` §14, `CLAUDE.md` §14 y §17, roadmap v1.16 (con la línea de alcance de la Fase 7 restaurada: las actualizaciones de F7c y F7d la habían recortado). Pendientes para fases posteriores: unidad de medida ausente en `/inventory` y `/recommendations`; paquete de 774 kB (carga diferida del gráfico); banda nominal hasta US-055 (Fase 5) |
| 2026-10-05 | **Fase 5: corrección del dossier y cierre documental; F5a autorizada (`DT-086`).** Ajustes del responsable: OD-S1 a OD-S4 como `PROPUESTA` (bucle cerrado; lead time realizado; desabasto diario y unidades faltantes; inventario medio relativo al baseline); criterio serie-corte en `DT-078`; aclaración del Nivel 1 con días imputados (`DT-076`, `DT-081`); verificación de U1 para `DT-010`: solo expone (a), bloqueo previo para (c) y (d) (`DT-083`). `DT-071` a `DT-085` en `docs/15` y protocolo en `docs/05` §20. Correcciones del dossier: «gap» sin zona muerta; regla de `DT-021` fijada antes de candidatos y del *holdout* (`DT-078`); 5 % registrado como propuesta, no aceptada (`DT-079`); simulador con protocolo reproducible y cuatro decisiones `OPEN` (`DT-080`); `DT-011` limitado a (a), (b) y (c), sin (d); `model_versions` ya admite los estados, sin `0004` (`DT-084`); enmienda acotada de D-12 (`DT-074`); merge commit (`DT-085`, `docs/12` §2.2). Tabla de progreso: Fases 2 y 4 pasan de «No iniciada» a «En curso». Sin código, dependencias ni migraciones |
| 2026-10-05 | **F5a implementada (pendiente de revisión).** `ml/` (`config`, `cuts`, `data`, `models`, `protection`, `metrics`, `segmentation`, `backtest`, `report`, `__main__`) y `ml/tests` (57 pruebas: fuga, guarda del *holdout*, reproducibilidad por huella, baselines = U3, sin `float` hacia U1/U3, `app.runs` solo en la prueba de paridad, métricas y SES a mano, `L + R` con la función del motor —22 días— y contraste con `evaluate()`, segmentación, elegibilidad por modelo y población por corte). Ejecución: `PYTHONPATH=backend python -m ml backtest --data data/synthetic/output --out ml/out --report docs/reports/fase5-f5a-backtest-sintetico.md --generated-on AAAA-MM-DD`. Ajustes de la revisión del responsable: población por corte a la fecha (`DT-087`, ACEPTADA; la regla literal de U3 queda comparada), notas en `DT-075` y `DT-079` (cortes solapados, no independientes), `docs/13` §6 corregido, prueba AST de dependencias Markdown y JSON resumido del informe versionados (los datos detallados se regeneran en `ml/out/`), notas en `DT-073` y `DT-077`, `CLAUDE.md` §6.10, frase en `docs/03` §16.2 y `ASSUMPTION-026`. Valores `PROPUESTA` en `ml/config.py`: SES con rejilla 0,05–0,95, nivel inicial = primera semana, mínimo 25 semanas; escala de `L + R` = escala semanal × (L + R)/7; denominador cero excluido y contado; umbrales ADI 1,32 y CV² 0,49. Sin elección de baseline oficial, métrica primaria ni umbrales; `backend/` y `frontend/` sin cambios |
| 2026-10-05 | **F5a integrada y F5b autorizada.** PR #8 integrado en `main` con merge commit (`ea72df5`). `DT-088` autoriza F5b: simulador de Nivel 2 con los cuatro baselines, U1 sin cambios, sin elegir baseline oficial, métrica ni umbrales, sin *holdout*. `DT-080`: OD-S1 a OD-S4 `ACEPTADA` con los refinamientos del responsable (estado inicial reconstruido, órdenes reales posteriores al primer corte descartadas, llegada tras el `L` del motor, demanda latente solo con datos `SYNTHETIC`, inventario medio relativo sin umbral absoluto, cadencia semanal de reentrenamiento, calentamiento de 8 semanas). Pendiente: discrepancia entre el punto 7 (`expected_on`) y OD-S1 («llegadas reales») para las 93 líneas abiertas al primer corte. `docs/15` v1.37, `docs/05` v1.9, backlog v1.5 y roadmap v1.19 |
| 2026-10-05 | **F5b implementada (pendiente de revisión).** `ml/simulation/` (`environment`, `forecasters`, `engine_inputs`, `simulator`, `run`, `level2`, `report`), carga del estado inicial en `ml/data.py` y `python -m ml simulate` (con caché reanudable y presupuesto de tiempo por el límite de las llamadas al equipo). La demanda latente solo la lee `environment` (prueba AST). 82 pruebas de `ml/tests`: trayectoria a mano, tránsito, bucle cerrado, *as-of*, igualdad de condiciones y sensibilidad (`docs/13` §6.1), guardas del *holdout* para demanda, movimientos y órdenes, sin `float` hacia U1, paridad con U4 y U3, reproducibilidad. Corrección de determinismo: `math.fsum` en el cruce (Python 3.12 cambió `sum()`). Huella `0a83fe3d…`, igual en 3.11 y 3.13. `docs/13` v1.16 (segunda excepción de paridad con U4, también en `docs/03` §16.2), `docs/05` v1.10, roadmap v1.20. Pendiente: discrepancia de `DT-080` punto 7 frente a OD-S1 |
| 2026-10-05 | **F5b: cierre documental.** `DT-080` recoge las decisiones del responsable sobre las dudas de F5b (llegada en `expected_on` de las 93 órdenes abiertas al primer corte, vencidas al día siguiente; `is_active = True`; lead time solo de observaciones reales previas al primer corte; valores provisionales aceptados). Nota en `DT-078` y `docs/05` §20.3: el criterio serie-corte no discrimina entre MASE, RMSSE y WAPE por construcción. `CLAUDE.md` §17: Fase 5 autorizada solo en F5a y F5b. `docs/15` v1.38, `docs/05` v1.11. Sin cambios de código |
| 2026-10-05 | **G1 de la Fase 5.** Decisiones del responsable en la revisión de F5b, `ACEPTADA` y provisionales (`SYNTHETIC`): `DT-089` (baseline oficial: media móvil de 13 semanas; SES, candidato más fuerte, no promovido: MASE `L + R` 0,669 frente a 0,800, pero 3 860 frente a 3 882 unidades faltantes e inventario relativo 0,991; `DT-077` y `DT-081` sin cambios, pertenecen a F5c); `DT-090` (MASE como métrica primaria, decisión del responsable; `DT-021` cerrada); `DT-091` (5 % por segmento con mínimo de 10 productos; agregado y 2/3 de los cortes comparables; inventario +5 %; «igual» con unidades faltantes ≤ +2 % y *fill rate* ≤ −0,2 puntos; banda de sesgo y cobertura abiertas). G1 no autoriza F5c ni F5d; *holdout* sin usar. Notas en `DT-010`, `DT-011`, `DT-021`, `DT-077`, `DT-079`, `DT-081`, `DT-P03` y `DT-P04`; `docs/05` §20.5 con la tabla de los cuatro baselines. `docs/15` v1.39, `docs/05` v1.12, backlog v1.6, roadmap v1.21, `CLAUDE.md` §17. Sin cambios de código |
| 2026-10-06 | **F5c autorizada (`DT-092`) y criterios complementarios de G1 (`DT-093`).** Registrados en el primer commit de `feature/ml-f5c`, antes de evaluar ningún candidato: MASE en `L + R` (`h = 1` secundaria); «0,2 puntos» = 0,002; cortes comparables (⌈2/3⌉, mínimo 5, si no, no concluyente); inventario +5 % como criterio y cruce de `DT-078` con 0 y +5 %; banda de sesgo ±0,10 y 0,05 por segmento; cobertura calibrada entre 0,75 y 0,85 (solo rótulo); segmentación Syntetos-Boylan y estacionalidad por autocorrelación en el retardo 52; estimadores (b) y (c) de `DT-081` y series con > 50 % de desabasto aparte; ajuste por rejillas con reoptimización cada 4 decisiones en el simulador (cambio provisional de `DT-080`); Holt-Winters con ≥ 104 semanas; sustitución por el baseline oficial cuando una rama no tiene modelo elegible. `docs/15` v1.40, `docs/05` v1.13, backlog v1.7, roadmap v1.22, `CLAUDE.md` §17 |
| 2026-10-06 | **F5c implementada (pendiente de revisión).** `ml/candidates.py`: Holt, Holt-Winters (104 semanas), Croston, SBA y TSB con ajuste por rejilla y frontera de `DT-074`. `ml/f5c/`: Nivel 1 de los 17 cortes, estudio de `DT-011` (media móvil 13, SES, Holt-Winters y TSB; consumo observado y demanda latente), cobertura y calibración de intervalos, tabla automática de criterios y simulación con 17 ramas (reoptimización cada 4 decisiones; sustitución por el baseline oficial contada). Resultados `SYNTHETIC`: MASE `L + R` relativo a la media móvil de −5,9 % (Holt) a −18,3 % (Holt-Winters, 7 cortes), +12,8 % SBA; unidades faltantes 4 170 a 5 490 frente a 3 882, ninguno de los cinco candidatos nuevos cumple el +2 % *(corregido en la revisión: SES cumple todos los criterios)*; (b) y (c) reducen las unidades faltantes en todos los modelos; intervalo de la media móvil en banda en 14 de 14 horizontes. Paridad con F5a y F5b comprobada. Huella `df9f8753…` en Python 3.11 y 3.13; 121 pruebas. `docs/15` v1.41, `docs/05` v1.14, `docs/13` v1.17, `docs/03` v1.12, roadmap v1.23 |
| 2026-10-06 | **F5c: ajustes de revisión.** SES incluido en la tabla de criterios (cumple todos con (a)); criterios por estrategia de `DT-011` con la media móvil bajo la misma estrategia (SES y TSB cumplen con (b) y (c); Holt-Winters, con posible sesgo de selección por 7 cortes, no); sensibilidades reproducibles de cadencia y de umbral de segmento; `DT-093` puntos 12 a 14 (interpretaciones aceptadas); nota en `DT-081` (reducción de 15 % a 24 % de unidades faltantes con 1,7 % a 2,1 % más inventario; PROPUESTA de (b)); rótulo recomendado de la banda para F7d, a autorizar aparte; corrección de las frases «ningún candidato cumple». Informe `1ce5ea29…` (Python 3.11 desde la caché y 3.13 sin caché). `docs/15` v1.42, `docs/05` v1.15, backlog v1.9, roadmap v1.24 |
| 2026-10-06 | **F5c integrada en `main`.** PR #11, merge commit `6a1d777`; sus padres son `258deef` (G1) y `b4d3ad0` (último commit de `feature/ml-f5c`). Cierre documental: `status.md`, roadmap, `docs/05` §20.1 y §20.7 y `CLAUDE.md` §17 dejan de presentar F5c como pendiente de revisión. Resultados `SYNTHETIC` sin cambios (`1ce5ea29…`); ningún modelo promovido; estrategia (b) de `DT-011`, F5d, G2, G3, U1b y rótulo de F7d siguen pendientes. Sin cambios de código |
| 2026-10-06 | **U7 implementada (pendiente de revisión).** `DT-094` (`ACEPTADA`): alcance de cierre de la Etapa 2 con el stack completo por unidades U7 a U16, cada una con su autorización; Azure for Students con presupuesto de planificación de 50 USD; Bicep; región por verificar en U10; corpus sintético para AI Search; límites de la Fase 5 sin cambios. `DT-095`: imágenes `backend` (API y procesos por lotes), `frontend` (Node 24.21.0 + nginx 1.30.5 sin privilegios, proxy de `/api` en el mismo origen) y `dataset` (generador 0.4.0 sin modificar, en un volumen); `infra/docker-compose.yml` con perfil `app` (`postgres` sigue solo sin perfil), puertos en `127.0.0.1`, `init` idempotente con `RUN_AS_OF=2025-12-31`; `serve_api.py` sin tocar U5; `.dockerignore` como lista de permitidos; 14 pruebas estáticas y `smoke.py`. Verificación con imágenes base sustitutas de la misma versión (el entorno del agente no alcanza ningún registro): `ds-6c8ad65b4999` regenerado igual, 3 990 forecasts y 1 330 primarios, 100 evaluaciones (50/40/10), todo `healthy`, smoke 8/8, interfaz recorrida en Chromium, segundo arranque idempotente; suites por defecto (353) y de la API (56) en verde. Pendiente: construcción con las imágenes oficiales y digests. Sin Azure, sin credenciales, sin commit |
| 2026-10-06 | **U8 implementada (pendiente de revisión).** U7 integrada en `main` (PR #13, `7d4fb50`) y el cierre documental de F5c (PR #12, `f07ea79`). `DT-096`: `.github/workflows/ci.yml` (PR, push a `main` y manual; `contents: read`; `actions/checkout` v7.0.1, `setup-python` v7.0.0 y `setup-node` v7.0.0 fijadas por SHA; Python 3.11.16; Node 24.21.0 y npm 11.19.0) con los jobs `secret-scan`, `ml`, `backend`, `api`, `integration` (PostgreSQL 16 efímero, migraciones y suite), `generator`, `frontend` (ESLint, `tsc`, Prettier, Vitest, build) y `docker` (pruebas de `infra/tests`, construcción, `healthy`, smoke); `infra/ci/secret_scan.py` y `backend_requirements.py`, solo biblioteca estándar; sin Ruff ni Black ni linter de Python; sin Azure ni OIDC. `DT-095`: digests del índice multiplataforma de las cuatro bases tomados de `docker-library/repo-info` y fijados, pendientes de verificación externa. Reproducción fuera de GitHub: `actionlint` limpio; `ml` 129, backend 353, API 56, integración 152, generador 582, frontend 148 + lint, `tsc`, Prettier y build, Docker smoke 8/8, `infra/tests` 22, detector 0 hallazgos. Defecto anotado sin corregir: `pip install -e ".[db]"` de `backend/pyproject.toml` falla con setuptools actual (flat layout). Sin commit |
| 2026-10-06 | **U9 implementada (pendiente de revisión).** `DT-097`: `backend/db/migrations/0004_analytics_views.sql` crea el esquema `analytics` con `data_load`, `dim_date`, `dim_product`, `dim_category`, `dim_supplier`, `dim_location`, `dim_model_version`, `fact_consumption` (con demanda latente, solo `SYNTHETIC`), `fact_inventory_current` (posición contable), `fact_inventory_daily` (existencia al cierre del día desde los movimientos), `fact_purchase_order_line` (pendientes, antigüedad, lead time observado como V1-09, cumplimiento), `fact_forecast` y `fact_recommendation`; rol `analytics_reader` sin `LOGIN`, `USAGE` + `SELECT` solo en `analytics`, privilegios por defecto para vistas futuras. Definiciones de KPI en `knowledge/glossary.md` y catálogo en `docs/11` §10; KPI bloqueados (valoración, `BR-X03`, `DT-P19`, resolución humana, precisión del forecast) fuera. `backend/tests/db/test_analytics.py`: 25 pruebas (migración, esquema, datos de prueba calculados a mano, dataset 0.4.0 frente a tablas, API y U4, seguridad del rol); ajustes mínimos en dos pruebas de U4 (lista de migraciones) y una de U3 (borra antes el esquema `analytics`). Integración completa: 177 en verde (PostgreSQL 16.15). Sin Power BI, sin Azure, sin commit |
| 2026-10-06 | **U10 preparada (pendiente de revisión y de despliegue).** `DT-098`: `infra/azure/main.bicep` (ámbito de suscripción), `modules/base.bicep` (Key Vault Standard con RBAC, sin red pública, retención 7 días y purgable; identidad `id-mpa-dev-github` con credencial federada de GitHub limitada al entorno `dev`; rol Reader sobre `rg-motor-predictivo-dev`), `modules/budget.bicep` (desactivado: Azure for Students no está entre las ofertas que admite Cost Management) y `parameters/dev.bicepparam`; README con despliegue, verificación, control de gasto y desmontaje. Región `westus3`: Mexico Central no tiene Azure OpenAI ni *semantic ranker*; depende de la directiva de regiones permitidas de la suscripción. Nota en `DT-022`: Key Vault elegido para `dev`. Validación: Bicep CLI 0.48.1 sin avisos, `infra/tests` 29, detector de secretos 0. Referencias de Microsoft Learn en `DT-098`. Ningún recurso creado: el despliegue lo hace el responsable. Commits de U8+U9 en `feature/u8-ci-u9-analytics` y de U10 en `feature/u10-azure-base` |
| 2026-10-07 | **U10: región revisada.** Evaluación con las fuentes oficiales vigentes: `westus3` se mantiene: AI Search sin nota de alta demanda y con *semantic ranker*, Azure OpenAI, Azure ML y PostgreSQL. Alternativas: `southcentralus` y `northcentralus`. `westus2` se descarta (no aparece en ninguna tabla de Azure OpenAI), igual que `westus` y `eastus` (AI Search no admite servicios nuevos por alta demanda) y `mexicocentral`. Corregido el orden de respaldo de `DT-098`, que incluía `eastus` y `westus`. El grupo pasa a `rg-motor-predictivo-dev` (parámetro `resourceGroupName`). El responsable lo creó vacío en `eastus`: se borrará y se recreará en la región elegida. El README añade comprobaciones de solo lectura con Azure CLI. Pendiente: directiva de regiones permitidas de la suscripción. |
| 2026-10-07 | **U10: región `centralus`.** La directiva «Allowed resource deployment regions» de la suscripción permite `northcentralus`, `chilecentral`, `norwayeast`, `centralus` y `mexicocentral`: `westus3` queda descartada. Principal `centralus` (AI Search con *semantic ranker* y sin nota de alta demanda; Azure OpenAI solo Global y Data Zone Standard; PostgreSQL flexible) y respaldo `northcentralus`, decisión del responsable (`DT-098`). Cambios: `parameters/dev.bicepparam`, `deploy-dev.ps1` (región esperada en el what-if), README y prueba de región. El grupo vacío de `eastus` ya fue eliminado por el responsable. Pendiente: `validate` en su Azure CLI; cuota de Azure OpenAI en `centralus` para U13 |
| 2026-10-07 | **U10 completada: desplegada y verificada.** El responsable ejecutó `infra/azure/deploy-dev.ps1` con su propia sesión de Azure CLI: suscripción `Azure for Students` comprobada, grupo inexistente, Bicep sin avisos, proveedores `Registered`, `validate` `Succeeded`, `what-if` con exactamente cinco `Create` en `centralus`, confirmación `DESPLEGAR`, despliegue `u10-base-dev` `Succeeded` y las nueve comprobaciones en `OK`. Identificadores anotados en `DT-098` (grupo, Key Vault `kv-mpa-dev-dymtafh7zjbba`, identidad `id-mpa-dev-github` con `principalId` y `clientId`, credencial `github-dev`, asignación `Reader` sobre el grupo). Sin secretos ni credenciales persistentes; ningún workflow usa todavía la identidad. Nota para U13: comprobar la cuota de Azure OpenAI en `centralus`. U11 no iniciada · sin commit |
| 2026-10-07 | **U11 implementada (pendiente de la configuración real y de la prueba real).** `DT-099`: `app/api/entra.py` (validador de Entra ID tras el puerto `TokenValidator`: RS256 con el JWKS del tenant descubierto en su metadata, `iss`, `tid`, `aud` = API, `azp` = SPA, `scp` `access_as_user`, `exp`/`nbf`/`iat` con 60 s, `oid` como `subject_id`, roles limitados a ASSUMPTION-010); `APP_ENV=dev` en `settings.py` con `ENTRA_TENANT_ID`, `ENTRA_API_CLIENT_ID` y `ENTRA_SPA_CLIENT_ID`; grupo `entra` (`PyJWT[crypto]` 2.15.1, `cryptography` 50.0.2). SPA: `@azure/msal-browser` 5.24.0 y `@azure/msal-react` 5.7.2 en un *chunk* que solo cargan las compilaciones `dev`, `VITE_APP_ENV`, `/acceso`. `infra/azure/deploy-u11.ps1`, `infra/azure/entra/` (estado deseado con GUID fijos, README, ejemplo de variables) e `infra/docker-compose.entra-dev.yml`. Pruebas: API 95 (39 nuevas), backend 353, integración de la API 39, infra (18 nuevas, con el flujo del script contra `fake_az.py`), frontend 174 (26 nuevas); `local` sin cambios. Pendiente del responsable: ejecutar el script y la prueba real · sin commit |
| 2026-10-07 | **U12 implementada (despliegue real pendiente).** `DT-100` aceptada por el responsable (cierra `DT-P01` para `dev`). Bicep en `infra/azure/u12/` (ACR Basic sin administrador; PostgreSQL 16 B1ms, TLS, reglas `aca-out-*` por IP de salida; entorno Consumption sin Log Analytics; api interna, frontend externo, job manual `caj-mpa-dev-bootstrap`; identidad `id-mpa-dev-runtime`; roles mínimos de `id-mpa-dev-github`), `deploy-u12.ps1` por etapas con *what-if* comprobado, `bootstrap.py` (dataset con `generated_at` fijo, migrate, ingest, forecast, recommend, usuario `mpa_app` con verificador SCRAM), nginx con `API_UPSTREAM`, workflow `deploy-dev.yml` por OIDC. U10 gana `keyVaultArmSecretAccess` (pendiente de confirmar). Pruebas: infra 80, backend 353, frontend 176, escáner de secretos 0. Falta: ejecución real, E2E, redespliegue y pruebas de fallo. |
| 2026-10-08 | **U12 autorizada para el despliegue real; opción C del Key Vault aceptada (solo MVP/`dev`).** `deploy-u12.ps1`: `Preflight` comprueba `Microsoft.KeyVault/vaults/deploy/action` en la sesión del responsable (comodines y `NotActions` de RBAC) y que `id-mpa-dev-github` no la tenga y solo tenga los roles autorizados dentro del grupo; nueva etapa `KeyVaultRole` (solo si falta: rol personalizado con esa única acción, asignable en el grupo, asignado al responsable sobre el vault, sin duplicados); `Verify` pasa a 18 comprobaciones; las evidencias redactan cualquier valor de secreto; los parámetros con aspecto de secreto detienen el despliegue. Pruebas U12: 27. |
| 2026-10-08 | **U12: `-PreflightOnly` (corrección).** El responsable ejecutó `deploy-u12.ps1 -PreflightOnly` (convención de U10/U11) y el script lo rechazó: solo tenía `-Stage Preflight`. Ahora existe `-PreflightOnly`, idéntico a `-Stage Preflight`, estrictamente de solo lectura: `Invoke-Az` rechaza cualquier comando fuera de `Test-ReadOnlyAz`; el Key Vault se lee con `az resource show`; 12 secciones; código 0/1; dice si hace falta `KeyVaultRole`. Pruebas con el Azure CLI falso (incluida la emulación de PowerShell 5.1) y guardas para que las pruebas de flujo nunca usen el Azure CLI real en Windows. |
| 2026-10-08 | **U12: preflight real OK y etapa `KeyVault` detenida por el guardia (sin cambios en Azure).** Preflight real: `PREFLIGHT OK`, `deploy/action` ALLOWED (Owner), proveedores `Microsoft.App`, `Microsoft.ContainerRegistry` y `Microsoft.DBforPostgreSQL` registrados por el responsable. El *what-if* de U10 mostró el Key Vault con exactamente `enabledForTemplateDeployment` false→true y `networkAcls.bypass` None→AzureServices (`publicNetworkAccess` Disabled) y además un `Modify` en la asignación Reader de `id-mpa-dev-github`: ruido conocido de *what-if* (`principalId` como `reference()` sin evaluar; antes `3db51754-…`, el mismo principal de U10; `principalType` NoEffect). El script aceptaba solo el Key Vault y se detuvo. Corrección: `Test-ReaderReferenceNoise` acepta ese caso únicamente si el rol sigue siendo Reader, la expresión apunta a `id-mpa-dev-github`, el principal anterior coincide con `az identity show` y el resto es NoEffect; 7 casos nuevos en `-SelfTest` y verificado contra el *what-if* real guardado. |
| 2026-10-08 | **U12: `-Stage KeyVault` dijo `ALREADY_CONFIGURED` sin aplicar nada (error del script, sin efecto en Azure).** Causa: `@(As-Array $whatIf.changes \| Where-Object …)` — `As-Array` devuelve `,array` y la tubería recibía la lista entera como un solo elemento, así que el filtro por tipo `Microsoft.KeyVault/vaults` nunca coincidía. Corregido con `(As-Array …)` en las 9 apariciones del patrón (incluidas comprobaciones de `Verify` y del preflight que funcionaban por casualidad con un solo elemento), nueva función pura `Test-KeyVaultPending`, 3 casos en `-SelfTest`, verificado contra el *what-if* real (`True`) y prueba de fuente que prohíbe el patrón. El Key Vault sigue sin la opción C. |
| 2026-10-08 | **U12 en Azure: opción C aplicada, secretos creados; `Core` detenida por el guardia (nada creado).** `-Stage KeyVault`: Key Vault con `publicNetworkAccess=Disabled`, `enabledForTemplateDeployment=true`, `bypass=AzureServices`. `-Stage Secrets`: `pg-owner-password` y `pg-app-password` creados sin mostrarse. `-Stage Core`: `validate` correcto, pero el *what-if* marcó `Unsupported` las dos asignaciones sobre el ACR porque su nombre usaba `guid(…, principalId, …)`, que solo se conoce al desplegar. Corrección: nombres con los ids de recurso de las identidades (`guid(registry.id, <identidad>.id, rol)`); prueba nueva que prohíbe `principalId` dentro de `guid()`. |
| 2026-10-09 | **U12: sujeto OIDC de GitHub corregido en el estado deseado (sin cambios en Azure).** `Deploy dev` falló en `azure/login` con `AADSTS700213`: GitHub presenta `repo:daniel02vazquez97-alt@290574726/G19X-ITH-DVT-209-ACADEMIC@1408075880:environment:dev` (formato inmutable con ids) y `github-dev` tenía el formato antiguo con nombres. `githubOwnerId`/`githubRepositoryId` en el Bicep de U10, sujeto exacto en `deploy-dev.ps1` y `deploy-u12.ps1`, pruebas del formato y de no ampliación. Falta: actualizar la credencial real con Azure CLI (responsable) y repetir `Deploy dev`. |
| 2026-10-09 | **U12: `-Stage Apps` falló por entorno Express (corregido en el repositorio; Azure pendiente).** Imágenes publicadas por OIDC con la etiqueta `267803e…`; ARM rechazó el job (`ExpressEnvironmentResourceNotSupported`) y `allowInsecure` de la api (`ExpressEnvironmentFeatureNotSupported`). `environmentMode: 'WorkloadProfiles'` explícito (API 2026-07-01), api con `allowInsecure: false` y nginx por HTTPS al FQDN interno con certificado verificado; guardia, preflight, `Core` y `Verify` comprueban el modo; la URL de Azure en el estado deseado de Entra se sustituye si el entorno se recrea. Procedimiento en el README de U12 §5.2. |
| 2026-10-09 | **U12: entorno `cae-mpa-dev` convertido a `WorkloadProfiles` sin recrearlo.** Preflight real OK (aviso de modo Express). `-Stage Core` con la plantilla corregida: *what-if* con `Modify` en el entorno (y ruido conocido en ACR, PostgreSQL y asignaciones de rol), `DESPLEGAR`, `create: Succeeded` y comprobación posterior `Entorno cae-mpa-dev: modo WorkloadProfiles`. Mismo dominio (la URL del frontend en Entra no cambia); nada borrado. Siguiente: integrar los cambios (nginx con TLS), `Deploy dev` y `-Stage Apps` con la etiqueta nueva. |
