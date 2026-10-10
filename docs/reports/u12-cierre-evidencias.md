# U12: matriz de cierre y evidencias (`DT-100`)

**Fecha:** 2026-10-10. Revisión 2, que incorpora la evidencia real de Azure aportada por el responsable.

**Base revisada:** `main` en `62f25ca` (PR #3).

**Estado de U12:** desplegada y verificada en Azure (Apps, Bootstrap, Verify y smoke de Entra ID). **No está cerrada:**
faltan la reconciliación completa del firewall, el E2E en el navegador, el redespliegue, las pruebas de fallo y el
cierre documental.

## 0. Origen de la evidencia

Cada afirmación de este informe indica de cuál de estas tres fuentes procede:

| Marca | Origen | Qué incluye |
|---|---|---|
| **[AZ-U]** | **Evidencia real de Azure aportada por el responsable** | Salidas de PowerShell que ejecutó en su equipo con su sesión de Azure y que compartió fuera de esta sesión. El agente **no** las ejecutó, ni ve la salida completa, ni la tiene versionada. Se recogen tal como el responsable las resumió el 2026-10-10. |
| **[CC]** | **Pruebas ejecutadas en Claude Code Cloud** | Pruebas locales ejecutadas por el agente en el contenedor de esta sesión, sin acceso a Azure (§3), y estado de GitHub Actions consultado desde la sesión. |
| **[PEND]** | **Sin ejecutar o sin evidencia suficiente** | Lo que todavía no tiene una salida real que lo demuestre. |

El agente no ejecutó ninguna operación contra Azure ni en el navegador.

## 1. Criterios de cierre: lista `PROPUESTA` C01–C15

`DT-100` dice que «U12 no se cierra hasta cumplir los 15 criterios de cierre», pero solo nombra sus áreas: despliegue,
OIDC, ACR, PostgreSQL, *bootstrap*, frontend, API, Entra con la URL real, redespliegue y fallos. **Ningún documento del
repositorio los enumera como lista formal.** La tabla siguiente es una **propuesta del agente**, no una lista que ya
existiera. Sale de esas áreas, del procedimiento de `infra/azure/u12/README.md` §5 y de sus pruebas de aceptación de §6,
y no añade requisitos. Queda en estado **`PROPUESTA`** hasta que el responsable la valide (`CLAUDE.md` §7).

| # | Criterio propuesto | Fuente |
|---|---|---|
| C01 | Infraestructura desplegada (`Core` y `Apps`; despliegue `u12-dev` `Succeeded`); entorno `WorkloadProfiles` | DT-100 §1, README §5 pasos 4 y 8 |
| C02 | GitHub entra en Azure por OIDC sin secretos; identidades con permisos mínimos | DT-100 §7, README §2 |
| C03 | ACR Basic sin usuario administrador; *push* con `AcrPush` y *pull* con `id-mpa-dev-runtime` (`AcrPull`) | DT-100 §3 |
| C04 | PostgreSQL Flexible 16 `Standard_B1ms`, sin HA, TLS obligatorio, `Ready` | DT-100 §4 |
| C05 | Firewall solo con reglas `aca-out-<ip>` (nunca `0.0.0.0`), reconciliado por `-Stage Firewall` | DT-100 §5, README §4 |
| C06 | Key Vault en opción C; contraseñas solo como `secretRef`; `DATABASE_URL` sin contraseña | DT-100 §6, README §3 |
| C07 | El job de *bootstrap* termina en `Succeeded` y `BOOTSTRAP OK` en una sola ejecución | DT-100 §2, README §5 paso 9 |
| C08 | El frontend responde 200 por HTTPS | README §5 pasos 10 y 11 |
| C09 | API con ingress interno y solo HTTPS; detrás del proxy, sin token → 401 | DT-100 §1 y §8, README §5 paso 10 |
| C10 | *Redirect URI* real aplicado al registro de la SPA e inicio de sesión real con MSAL | DT-100 §8, README §5 paso 5 |
| C11 | Matriz de roles en el navegador: VIEWER, 11 rutas → 200 y `history`/`runs` → 403; PLANNER, 13 → 200; sin sesión → 401; sin rol → 403 salvo `/me` | README §6 E2E |
| C12 | Datos reales de la API en el navegador: catálogo, detalle, pronóstico y recomendación con explicación | README §6 E2E |
| C13 | Redespliegue idempotente: etiqueta nueva en api, frontend y job; `ALREADY_LOADED`/`ALREADY_COMPUTED`; recuentos estables; `/ejecuciones/<n+1>` → 404 | DT-100 §2, README §6 |
| C14 | Pruebas de fallo de README §6, recuperables y sin pérdida de datos | README §6 |
| C15 | Cierre documental con todas las salidas (sin secretos) | CLAUDE.md §8, README §5 |

## 2. Evidencia por criterio

Estado:

- ✅ **demostrado** con evidencia real;
- 🟡 **parcial** (evidencia real de una parte; otra parte [PEND]);
- ⬜ **pendiente**.

| # | Evidencia real de Azure [AZ-U] | Pruebas en Claude Code Cloud [CC] | Estado | Pendiente [PEND] |
|---|---|---|---|---|
| C01 | Despliegue `u12-dev` `Succeeded`, sin error; `ca-mpa-dev-api` y `ca-mpa-dev-frontend` `Succeeded`/`Running`; `caj-mpa-dev-bootstrap` existe con su recurso `Succeeded`; Verify: Workload Profiles OK | Bicep 0.48.1 `build`/`lint` y guardias del *what-if* (`infra/tests`) | ✅ | — |
| C02 | Verify: identidades con permisos mínimos OK | Deploy dev #2 y #3 en verde con `azure/login` por OIDC (GitHub Actions); `test_u12_config.Workflow` | ✅ | — |
| C03 | Las apps arrancan (`Running`) con imágenes del ACR; Verify OK (ACR e identidades) | Deploy dev #3 publicó `backend`, `frontend` y `bootstrap` (`2742539…`) con `AcrPush` | ✅ | — |
| C04 | Verify: PostgreSQL 16/B1ms, TLS obligatorio y `Ready` OK | Bicep (`postgres.bicep`) | ✅ | — |
| C05 | Las reglas `aca-out-*` se consultaron y existen; Verify: firewall limitado a `aca-out-*`, sin `0.0.0.0` | `test_firewall_rule_commands_name_the_server_with_server_name` (corrección `dd2d45f`, PR #3, en `main`) | 🟡 | **Ejecución completa de `-Stage Firewall` después de la corrección:** no se ha compartido una salida satisfactoria. Ni fallida ni completada. |
| C06 | Verify: Key Vault opción C OK y el resto de las 19 comprobaciones, entre ellas las contraseñas solo como `secretRef` | Detector de secretos y pruebas de redacción (`infra/tests`) | ✅ | — |
| C07 | Ejecución `caj-mpa-dev-bootstrap-tbazfuc`: `BOOTSTRAP OK`, `Succeeded`. `data_loads` 1, `products` 100, `inventory` 100, `consumption` 108 235, `calculation_runs` 2, `forecasts` 3 990, `recommendations` 100. Evaluaciones: 100 productos, 50 `RECOMMEND`, 40 `NO_NEED`, 10 `NOT_CALCULABLE`; motor `0.1.0`, política `V1_PROVISIONAL`. Verify: *bootstrap* `Succeeded` | `bootstrap.py` contra PostgreSQL 16 local con los mismos recuentos (§3) | ✅ | — |
| C08 | Verify: frontend HTTPS 200 OK. Smoke `--entra`: `/` y ruta profunda de la SPA → 200 | Smoke de Compose en el job `docker` de CI | ✅ | — |
| C09 | Verify: API interna solo HTTPS y API detrás del proxy → 401 sin token. Smoke: peticiones sin token → 401; `/api/v1/runs/1` sin token → 401 | `tests/api` (95) | ✅ | — |
| C10 | Smoke `SMOKE OK (entra-dev)`: la SPA contiene los identificadores esperados de `entra-dev.env`; en `APP_ENV=dev` se rechazan el token de desarrollo (401) y un token RS256 falsificado (401) | `tests/api` (`test_entra`); `u11-entra.dev.json` incluye la URL real del frontend | 🟡 | **Inicio de sesión real con MSAL en el navegador**, que demuestra también que el *redirect URI* está aplicado |
| C11 | — | `test_entra.test_role_matrix`, `test_401_without_token_and_with_invalid_tokens` y `test_me_with_and_without_roles` | ⬜ | **E2E en el navegador** con la URL real: VIEWER (rutas autorizadas y no autorizadas en `/acceso`), después PLANNER, sin sesión y sin rol |
| C12 | — | Contrato de la API (`tests/api`) y suite por defecto (353) | ⬜ | **E2E en el navegador:** catálogo, detalle, pronóstico y recomendación con su explicación |
| C13 | — | 2.ª ejecución local de `bootstrap.py`: `applied: none`, `ALREADY_LOADED`, `ALREADY_COMPUTED` ×2 y recuentos idénticos | ⬜ | **Redespliegue en Azure** con `run_bootstrap=true`: etiqueta nueva en los 3 recursos, `ALREADY_LOADED`, `ALREADY_COMPUTED`, recuentos estables y `/ejecuciones/<n+1>` → 404 |
| C14 | El smoke ya mostró rechazos de tokens en Azure (desarrollo y RS256 falsificado → 401). No es la prueba de README §6 (`Authorization: Bearer x`) | Job con la base detenida: para en el paso 2 y se recupera (§3); token inválido → 401 en `tests/api` | ⬜ | **Pruebas de fallo en Azure** (§5) |
| C15 | — | — | ⬜ | **Cierre documental** después de C05, C10–C14 |

**Resumen:**

- **Demostrados (8):** C01, C02, C03, C04, C06, C07, C08 y C09.
- **Parciales (2):** C05 (falta la reconciliación con `-Stage Firewall`) y C10 (falta el inicio de sesión real).
- **Pendientes (5):** C11, C12, C13, C14 y C15.

## 3. Pruebas ejecutadas en Claude Code Cloud [CC]

Entorno del contenedor de la sesión:

- Linux, Python 3.13.16 (CI usa 3.11.16), sin *daemon* de Docker ni Azure CLI.
- Bicep CLI 0.48.1, con el mismo SHA-256 que fija CI (`b09ec25a…7f6e`).
- PowerShell 7.4.6, comprobado con su `hashes.sha256`.
- Los dos binarios están solo en el directorio temporal de la sesión.
- Las dependencias de Python son las fijadas en `backend/pyproject.toml`, instaladas en un *venv* temporal.

Primera revisión (2026-10-10):

| Comando | Resultado |
|---|---|
| `python infra/ci/secret_scan.py` | 426 archivos, **0 hallazgos** |
| `python -m unittest discover -s infra/tests -t infra/tests` sin pwsh ni Bicep | 95 OK, **26 omitidas** |
| la misma suite con Bicep 0.48.1 y pwsh 7.4.6 en el `PATH` | **95 OK, 0 omitidas** (incluye `-SelfTest`, `-PreflightOnly` y los flujos con el Azure CLI falso) |
| `python -m data.synthetic.generator` | `ds-6c8ad65b4999` |
| `cd backend && python -m unittest discover -s tests -t .` | **353 OK** |
| `cd backend && python -m unittest discover -s tests/api -t tests/api` (grupos `db api test entra`) | **95 OK** |
| `infra/docker/bootstrap.py` ×2 contra PostgreSQL 16.15 local (`mpa_owner` era superusuario local, a diferencia de Azure) | 1.ª: `COMPLETED` ×3 y `BOOTSTRAP OK`. 2.ª: `applied: none`, `ALREADY_LOADED`, `ALREADY_COMPUTED` ×2 y `BOOTSTRAP OK`, con recuentos idénticos (los mismos que dio Azure en C07) |
| `mpa_app` tras el *bootstrap* | `SELECT` → 100; `DELETE` → `permission denied for table`; `CREATE TABLE` → `permission denied for schema public` |
| `bootstrap.py` con la base detenida | código 1, `BOOTSTRAP FAILED at step 2 (migraciones)`, sin paso 3 |
| `bootstrap.py` después de arrancar la base | `ALREADY_LOADED`, `ALREADY_COMPUTED` ×2 y `BOOTSTRAP OK` |

Consultado en GitHub Actions desde la sesión:

- CI en verde en `62f25ca` (run 38035570538).
- Deploy dev #3 en verde (run 38016512995): publicó las imágenes con la etiqueta `2742539…`. En ese momento las apps
  todavía no existían.

Validaciones de esta revisión 2 (solo documentación): se repiten el detector de secretos y `infra/tests`. Los
resultados están en el informe de entrega de esta revisión.

**No ejecutado en la sesión:**

- **Frontend (Vitest, ESLint, `tsc`):** U12 no modificó `frontend/` y el contenedor tiene Node 22, mientras que
  `engines` exige Node 24.
- **Suite de integración `tests/db`.**
- **Smoke de Compose:** no hay *daemon* de Docker.

## 4. Hallazgos documentales

1. **No existía una lista formal de los 15 criterios** (§1). La propuesta C01–C15 espera la validación del responsable.
2. **`project/status.md` iba por detrás de `main`:** `ci.yml` figuraba como pendiente y faltaban el primer `-Stage Apps`
   del 2026-10-10 (falló en `firewall-rule list`) y su corrección `dd2d45f`. Ya está recogido, junto con la evidencia
   real de esta revisión.
3. ~~El estado real de las apps no estaba registrado~~. **Resuelto** con la evidencia [AZ-U]: api y frontend
   `Succeeded`/`Running`, job `Succeeded`, `u12-dev` `Succeeded`.
4. **Número de comprobaciones de `Verify`:** el script tiene 19, igual que el README y la evidencia [AZ-U]. La fila de
   `status.md` del 2026-10-08 dice 18; es historial anterior a la comprobación `WorkloadProfiles` y se deja como está.
5. **README §6, «Job con fallo»:** ya corregido en esta rama. El job se detiene en el primer paso que usa la base
   (2, migraciones); el paso 1 genera el dataset sin base.
6. **Evidencia [AZ-U] sin versionar:** no hay en el repositorio una copia de `tmp/u12-evidence/u12-evidence.json` ni de
   las salidas. `tmp/` está excluido de Git a propósito. Para el cierre (C15) conviene decidir si se adjunta un extracto
   redactado (solo identificadores) o basta con este resumen.

## 5. Plan mínimo para lo pendiente

No repite Apps, Bootstrap, Verify ni el smoke de Entra ID, que ya están demostrados. Lo ejecuta el responsable con su
sesión.

| # | Acción | Cierra | Evidencia que hay que aportar (sin secretos) |
|---|---|---|---|
| 1 | `deploy-u12.ps1 -Stage Firewall`, ejecución completa con el script corregido (`dd2d45f`) | C05 | Termina sin error; «Las reglas ya coinciden…» o reglas actualizadas; ninguna regla obsoleta ni ajena |
| 2 | E2E en el navegador con la URL real: `deploy-u11.ps1 -AssignRole VIEWER`, inicio de sesión, `/acceso` (11 → 200; `history` y `runs` → 403), catálogo, detalle, un pronóstico y una recomendación con explicación. Después PLANNER (13 → 200), sin sesión (401) y sin rol (403 salvo `/me`) | C10, C11, C12 | Tabla de `/acceso` por rol y lista de vistas comprobadas, sin tokens |
| 3 | Redespliegue: PR con un cambio inocuo → merge → Deploy dev con `run_bootstrap=true` | C13 | Etiqueta nueva en api, frontend y job (`az containerapp show … --query properties.template.containers[0].image`); salida del job con `ALREADY_LOADED` y `ALREADY_COMPUTED`; mismos recuentos que en C07; ejecuciones visibles sin cambios y `/ejecuciones/<n+1>` → 404 |
| 4 | Pruebas de fallo de README §6 (abajo) | C14 | Resultado y recuperación de cada una |
| 5 | Cierre documental: completar §6, `status.md` y `DT-100`; validar C01–C15 | C15 | — |

**Pruebas de fallo exigidas** (README §6), con su alcance:

| Prueba | Cómo | Esperado | Recuperación | Alcance |
|---|---|---|---|---|
| PostgreSQL detenido | `-Stage Stop` | El frontend carga; las vistas con datos reciben 5xx sin traza ni secreto | `-Stage Start` (y `-Stage Firewall` si la API no conecta); comprobar que los datos siguen ahí (mismos recuentos) | Solo `dev`; detener la base deja la API sin datos mientras dure la prueba |
| Token inválido | `curl` a `/api/...` a través del frontend con `Authorization: Bearer x` | 401 | — | Solo lectura. El smoke ya cubrió tokens de desarrollo y RS256 falsificados; falta el caso literal de §6 |
| Etiqueta de imagen inexistente | `-Stage Apps -ImageTag noexiste` | La revisión nueva no arranca y la anterior sigue sirviendo | `-Stage Apps -ImageTag <sha bueno>` | Modifica las apps de `dev`; restaurar la etiqueta buena antes de seguir |

README §6 incluye además «Firewall desactualizado», «Job con fallo» (ya comprobado en local [CC], §3) y «Key Vault
inaccesible». El responsable decide si entran en el cierre. Si entran, cada uno necesita su evidencia [AZ-U].

## 6. Registro de evidencias reales

| Paso | Origen | Resultado | Estado |
|---|---|---|---|
| Despliegue `u12-dev` | [AZ-U] | `Succeeded`, sin error | ✅ |
| Apps | [AZ-U] | `ca-mpa-dev-api` y `ca-mpa-dev-frontend` `Succeeded`/`Running`; `caj-mpa-dev-bootstrap` `Succeeded` | ✅ |
| Bootstrap | [AZ-U] | `caj-mpa-dev-bootstrap-tbazfuc`: `BOOTSTRAP OK`, `Succeeded`; recuentos de C07 | ✅ |
| Verify | [AZ-U] | 19/19 `OK`, «U12: dev verificado» | ✅ |
| Smoke | [AZ-U] | `python infra/docker/smoke.py --entra` → `SMOKE OK (entra-dev)` | ✅ |
| Firewall | [AZ-U] | Reglas `aca-out-*` existentes, sin `0.0.0.0`; ejecución completa de `-Stage Firewall` posterior a la corrección **sin salida aportada** | [PEND] |
| E2E en el navegador | — | | [PEND] |
| Redespliegue | — | | [PEND] |
| Fallos: PostgreSQL detenido y recuperación | — | | [PEND] |
| Fallos: token inválido | — | | [PEND] |
| Fallos: imagen inexistente | — | | [PEND] |
| Cierre documental | — | | [PEND] |
