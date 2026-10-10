# U12: matriz de cierre y evidencias (`DT-100`)

**Fecha:** 2026-10-10 · **Base revisada:** `main` en `62f25ca` (PR #3) · **Estado de U12:** desplegada en parte;
**no cerrada**.

Este informe compara los criterios de cierre de U12 con la evidencia que hay en el repositorio, en GitHub Actions y en
las pruebas locales de esta revisión. Separa tres tipos de evidencia:

- lo demostrado por pruebas automatizadas, en local o en CI;
- lo demostrado en Azure, cuando la ejecución real quedó registrada en `project/status.md` o en GitHub Actions;
- lo que todavía necesita una sesión real de Azure o de navegador.

Las pruebas de Azure y de navegador **no se ejecutaron en esta revisión**. Nada de este informe afirma que hayan pasado.

## 1. Los 15 criterios: enumeración `PROPUESTA`

`DT-100` dice que «U12 no se cierra hasta cumplir los 15 criterios de cierre», pero solo nombra sus áreas: despliegue,
OIDC, ACR, PostgreSQL, *bootstrap*, frontend, API, Entra con la URL real, redespliegue y fallos. **Ningún documento los
enumera**, a diferencia de U3 a U6, que tienen su sección «Criterios de cierre». La lista siguiente sale de esas áreas,
del procedimiento de `infra/azure/u12/README.md` §5 y de las pruebas de aceptación de §6. No añade requisitos nuevos.
**Está en estado `PROPUESTA` hasta que el responsable la valide** (`CLAUDE.md` §7: las contradicciones o los huecos se
documentan, no se resuelven por cuenta propia).

| # | Criterio | Fuente |
|---|---|---|
| C01 | Infraestructura desplegada con `Core` y `Apps`: *validate* y *what-if* sin borrados ni tipos fuera de la lista; entorno `WorkloadProfiles` | DT-100 §1, README §5 pasos 4 y 8 |
| C02 | GitHub entra en Azure por OIDC (`environment:dev`) sin secretos de larga vida; `id-mpa-dev-github` solo tiene los 4 roles mínimos y no tiene `deploy/action` | DT-100 §7, README §2 |
| C03 | ACR Basic sin usuario administrador; GitHub sube imágenes con `AcrPush`; las apps y el job descargan con `id-mpa-dev-runtime` (`AcrPull`) | DT-100 §3 |
| C04 | PostgreSQL Flexible 16 `Standard_B1ms`, sin HA, `require_secure_transport=ON`, en `Ready` | DT-100 §4 |
| C05 | El firewall solo tiene reglas `aca-out-<ip>` (una por IP de salida, nunca `0.0.0.0`), y `-Stage Firewall` las reconcilia | DT-100 §5, README §4 |
| C06 | Key Vault en opción C (`publicNetworkAccess=Disabled`, plantillas habilitadas, `bypass=AzureServices`); las contraseñas solo llegan como `secretRef` y `DATABASE_URL` no lleva contraseña | DT-100 §6, README §3 |
| C07 | El job `caj-mpa-dev-bootstrap` termina en `Succeeded`/`BOOTSTRAP OK` en una ejecución: dataset, migrate, ingest, forecast, recommend y rol `mpa_app` de solo lectura | DT-100 §2, README §5 paso 9 |
| C08 | El frontend responde 200 por HTTPS en su FQDN externo | README §5 pasos 10 y 11 |
| C09 | La API tiene ingress interno, solo HTTPS, y responde detrás del proxy de nginx (`/api/v1/me` sin token → 401) | DT-100 §1 y §8, README §5 paso 10 |
| C10 | El *redirect URI* real del frontend está aplicado al registro de la SPA (U11) y el inicio de sesión con MSAL funciona | DT-100 §8, README §5 paso 5 |
| C11 | La matriz de roles se cumple en el navegador: VIEWER con 11 rutas en 200 y `history`/`runs` en 403; PLANNER con 13 en 200; sin sesión → 401; sin rol → 403 salvo `/me` | README §6 E2E |
| C12 | Los datos vienen de la API real: catálogo, detalle, un pronóstico y una recomendación con su explicación | README §6 E2E |
| C13 | Redespliegue idempotente: api, frontend y job con la etiqueta nueva; *bootstrap* con `ALREADY_LOADED`/`ALREADY_COMPUTED`; sin duplicados | DT-100 §2, README §6 |
| C14 | Las seis pruebas de fallo de README §6 se recuperan sin pérdida de datos | README §6 |
| C15 | Cierre documental: `Verify` con 19/19, smoke `--entra` correcto, evidencias sin secretos, CI verde en `main`, `status.md` y `DT-100` actualizados | CLAUDE.md §8 y §12, README §5 |

## 2. Evidencia por criterio

Estados:

- ✅ **demostrado**;
- 🟡 **parcial**;
- ⬜ **pendiente**;
- 🔒 **requiere Azure o navegador** (el agente no puede ejecutarlo).

| # | Automatizado (local o CI) | Real en Azure (registrado) | Estado | Qué falta |
|---|---|---|---|---|
| C01 | Bicep 0.48.1 `build`/`lint` sin avisos y guardias del *what-if* (`infra/tests`, esta revisión y CI `main`) | `Core` `Succeeded` y entorno convertido a `WorkloadProfiles` (status, 2026-10-09). `Apps` del 2026-10-10 con `267803e` → falló por Express; con `2742539` → falló en `firewall-rule list` («unrecognized arguments»), corregido en `dd2d45f` | 🟡 🔒 | Repetir `-Stage Apps -ImageTag 27425390899bb032106cb42f0102bc5cb48433bc` y registrar el resultado |
| C02 | `test_u12_config.Workflow` (OIDC sin secretos, solo `dev`) | **Deploy dev #2 y #3 en verde**: `azure/login` por OIDC y `az acr login` (runs 37902049561 y 38016512995) | 🟡 | Comprobación de roles (4 roles, sin `deploy/action`) en `Verify` |
| C03 | Bicep y pruebas de registro (`infra/tests`) | Push de `backend`, `frontend` y `bootstrap:2742539…` a `acrmpadeva73qz3afqj7no` (Deploy dev #3). En ese momento las apps no existían («Las apps aún no existen») | 🟡 🔒 | Descarga por `AcrPull` (lo demuestra que las apps arranquen) y `Verify` |
| C04 | Bicep (`postgres.bicep`) | Servidor creado con `Core` | 🟡 🔒 | `Verify`: versión, SKU, TLS y `Ready` |
| C05 | `test_firewall_rule_commands_name_the_server_with_server_name` y la regla sin `0.0.0.0` (`infra/tests`) | **No reconciliado todavía**: el primer `Firewall` real falló por argumentos de la CLI | ⬜ 🔒 | `-Stage Firewall` (o `Apps`) con `dd2d45f` y `Verify` |
| C06 | Redacción de secretos y `secretRef` (`test_u12_config`), detector de secretos | Opción C aplicada y los dos secretos creados (status, 2026-10-08) | 🟡 🔒 | `Verify`: `secretRef` y `DATABASE_URL` sin contraseña en las apps reales |
| C07 | **Esta revisión:** `bootstrap.py` contra un PostgreSQL 16.15 efímero: `BOOTSTRAP OK`, 100 recomendaciones; `mpa_app` puede leer, pero no escribir ni crear tablas | Ninguna ejecución del job en Azure | 🟡 🔒 | `-Stage Bootstrap` → `Succeeded` |
| C08 | `smoke.py` en el job `docker` de CI (Compose local) | — | ⬜ 🔒 | `Verify` y smoke `--entra` |
| C09 | `tests/api` (95, esta revisión): 401 sin token y con tokens inválidos; HTTPS al FQDN interno en `nginx.conf` | — | ⬜ 🔒 | `Verify`: `/api/v1/me` → 401 detrás del proxy |
| C10 | Configuración de Entra (`test_entra_config`, flujo con Azure CLI falso) | La URL `https://ca-mpa-dev-frontend.greensmoke-cfd723ad.centralus.azurecontainerapps.io` está en el estado deseado `u11-entra.dev.json`; **no consta que se aplicara** con `deploy-u11.ps1` | ⬜ 🔒 | `deploy-u11.ps1` (aplicar o verificar `ALREADY_CONFIGURED`) e inicio de sesión real |
| C11 | `test_entra.test_role_matrix`, `test_401_without_token_and_with_invalid_tokens` y `test_me_with_and_without_roles` (`tests/api`) | — | ⬜ 🔒 | E2E en el navegador con VIEWER y después PLANNER (sin guardar tokens) |
| C12 | Contrato de la API (`tests/api`) y suite por defecto (353) | — | ⬜ 🔒 | E2E en el navegador |
| C13 | **Esta revisión:** segunda ejecución de `bootstrap.py`: migraciones `applied: none`, `ALREADY_LOADED`, `ALREADY_COMPUTED` ×2 y los mismos recuentos que en la primera | — | 🟡 🔒 | Deploy dev con `run_bootstrap=true` sobre un cambio inocuo; etiqueta de los 3 recursos; mismas filas; `/ejecuciones/<n+1>` → 404 |
| C14 | **Esta revisión:** job con la base detenida → `BOOTSTRAP FAILED at step 2 (migraciones)`, código 1, sin pasos siguientes; al arrancar la base, la repetición termina en `BOOTSTRAP OK`. Token inválido → 401 (`tests/api`) | — | 🟡 🔒 | Las seis pruebas de README §6 en Azure |
| C15 | CI de `main` en verde en `62f25ca` (run 38035570538) | — | ⬜ | `Verify` 19/19, smoke y actualización de `status.md` y `DT-100` con las salidas |

**Resumen:** ningún criterio está cerrado del todo.

- **Con evidencia real parcial (5):** C01, C02, C03, C04 y C06.
- **Solo con evidencia local, pendientes de Azure (3):** C07, C13 y C14.
- **Sin evidencia real (7):** C05, C08, C09, C10, C11, C12 y C15.

## 3. Pruebas locales ejecutadas en esta revisión (2026-10-10)

Entorno: Linux, Python 3.13.16 (CI usa 3.11.16), sin Docker *daemon* ni Azure CLI. Bicep CLI 0.48.1, descargado de
Azure/bicep con el mismo SHA-256 que fija CI (`b09ec25a…7f6e`), y PowerShell 7.4.6, descargado de PowerShell/PowerShell
y comprobado con su `hashes.sha256`. Los dos binarios se instalaron solo en el directorio temporal de la sesión, nunca
en el repositorio. Las dependencias de Python son las fijadas en `backend/pyproject.toml`, instaladas en un *venv*
temporal.

| Comando | Resultado |
|---|---|
| `python infra/ci/secret_scan.py` | 426 archivos, **0 hallazgos** |
| `python -m unittest discover -s infra/tests -t infra/tests` (sin pwsh ni Bicep) | 95 pruebas OK, **26 omitidas** |
| la misma suite con Bicep 0.48.1 y pwsh 7.4.6 en el `PATH` | **95 OK, 0 omitidas** (84 s); incluye `-SelfTest`, `-PreflightOnly` y los flujos con el Azure CLI falso |
| `python -m data.synthetic.generator` | `ds-6c8ad65b4999` |
| `cd backend && python -m unittest discover -s tests -t .` | **353 OK** |
| `cd backend && python -m unittest discover -s tests/api -t tests/api` (grupos `db api test entra`) | **95 OK** |
| `infra/docker/bootstrap.py` ×2 contra PostgreSQL 16.15 local (`mpa_owner` era superusuario local, a diferencia de Azure) | 1.ª: `COMPLETED` ×3 y `BOOTSTRAP OK`; 2.ª: `applied: none`, `ALREADY_LOADED`, `ALREADY_COMPUTED` ×2 y `BOOTSTRAP OK`, con recuentos idénticos (`data_loads` 1, `products` 100, `inventory` 100, `consumption` 108 235, `calculation_runs` 2, `forecasts` 3 990, `recommendations` 100) |
| `mpa_app` tras el *bootstrap* | `SELECT` → 100 filas; `DELETE` → `permission denied for table`; `CREATE TABLE` → `permission denied for schema public` |
| `bootstrap.py` con la base detenida | código 1, `BOOTSTRAP FAILED at step 2 (migraciones)`; no hay paso 3 |
| `bootstrap.py` después de arrancar la base | `ALREADY_LOADED`, `ALREADY_COMPUTED` ×2 y `BOOTSTRAP OK` |
| Contraseñas locales en los registros del *bootstrap* | 0 apariciones |

**No ejecutado:**

- **Frontend (Vitest, ESLint, `tsc`):** U12 no tocó `frontend/` y el entorno tiene Node 22, mientras que `engines`
  exige Node 24.
- **Integración `tests/db`:** cubre U2–U5; las pruebas de idempotencia anteriores ya usan las mismas entradas.
- **Smoke de Compose:** no hay Docker *daemon*. Lo cubre el job `docker` de CI, en verde en `62f25ca`.

## 4. Hallazgos documentales

1. **No existe la lista de los 15 criterios** (§1). Se propone la de este informe, a la espera de validación.
2. **`project/status.md` va por detrás de `main`:**
   - la última fila (2026-10-10) dice «Pendiente: commit de `ci.yml` y push», pero `ci.yml` está en `91f1b8a` y en
     `main` (PR #2) y CI está en verde;
   - no constan ni el `-Stage Apps` real del 2026-10-10, que falló en `firewall-rule list`, ni su corrección
     `dd2d45f` (PR #3);
   - no consta Deploy dev #3 (`2742539`, imágenes publicadas, apps inexistentes).
3. **Estado real de las apps sin registrar:** `Apps` falló en el paso `Firewall`, después del despliegue ARM. No consta
   si `ca-mpa-dev-api`, `ca-mpa-dev-frontend` y `caj-mpa-dev-bootstrap` existen ni con qué etiqueta. Hay que comprobarlo
   en solo lectura antes de seguir (§5, paso 1).
4. **Número de comprobaciones de `Verify`:** el script tiene 19 (el README dice 19); la fila de `status.md` del
   2026-10-08 dice 18. Es una fila histórica: es anterior a la comprobación `WorkloadProfiles`.
5. **README §6, «Job con fallo»:** dice «se detiene en el primer paso». El comportamiento comprobado es que el paso 1
   (generar el dataset) no usa la base, y el job se detiene en el primer paso que la usa (2, migraciones).

## 5. Plan mínimo para cerrar U12

Lo ejecuta el responsable con su sesión. Cada paso parte del anterior y no repite lo que ya funciona: preflight, opción
C, secretos, `Core`, OIDC y publicación de imágenes.

| # | Acción | Cierra | Tipo |
|---|---|---|---|
| 1 | **Diagnóstico de solo lectura:** `deploy-u12.ps1 -PreflightOnly`, `az containerapp list -g rg-motor-predictivo-dev -o table` y `az containerapp job list -g rg-motor-predictivo-dev -o table` | Hallazgo 3 | 🔒 Azure, lectura |
| 2 | `-Stage Apps -ImageTag 27425390899bb032106cb42f0102bc5cb48433bc`; las imágenes ya están en el ACR y no hace falta reconstruirlas. Incluye `Firewall`, con la corrección `dd2d45f` | C01, C03, C05 | 🔒 Azure (`DESPLEGAR`) |
| 3 | `deploy-u11.ps1`, para aplicar o confirmar el *redirect URI* real | C10 (configuración) | 🔒 Entra |
| 4 | `-Stage Bootstrap` → `Succeeded` y `BOOTSTRAP OK`; guardar el resumen de filas | C07 | 🔒 Azure |
| 5 | `-Stage Verify` → 19/19 y `tmp/u12-evidence/u12-evidence.json` | C02–C09, C15 | 🔒 Azure, lectura |
| 6 | Smoke `python infra/docker/smoke.py --entra` con `SMOKE_API_URL=none` | C08, C09 | 🔒 red pública |
| 7 | E2E en el navegador: `-AssignRole VIEWER`, `/acceso`, catálogo, detalle, pronóstico y recomendación con explicación; después PLANNER; sin sesión y sin rol | C10–C12 | 🔒 navegador |
| 8 | Redespliegue: PR con un cambio inocuo → merge → Deploy dev con `run_bootstrap=true`; etiqueta de los 3 recursos; mismos recuentos; `/ejecuciones/<n+1>` → 404 | C13 | 🔒 Azure y GitHub |
| 9 | Pruebas de fallo de README §6, en este orden: token inválido, imagen inexistente, firewall desactualizado, base detenida (`Stop`/`Start`), job con la base detenida y, por último, Key Vault (validación rechazada, sin cambios) | C14 | 🔒 Azure |
| 10 | Cierre documental: pegar las salidas sin secretos en este informe (§6), `status.md` y `DT-100`; validar la lista de §1 | C15 | documentación |

Notas:

- El paso 8 puede servir de PR del cierre documental si el cambio inocuo es la propia actualización de este informe.
- En el paso 9, «base detenida» y «job con la base detenida» comparten un mismo `Stop`/`Start`, para ahorrar un ciclo
  de PostgreSQL.

## 6. Plantilla de evidencias reales (a rellenar por el responsable, sin secretos)

| Paso | Fecha (UTC) | Comando | Resultado literal (resumido) | Etiqueta o commit |
|---|---|---|---|---|
| 1 Diagnóstico | | | | |
| 2 Apps + Firewall | | | | |
| 3 U11 *redirect URI* | | | | |
| 4 Bootstrap | | | | |
| 5 Verify | | | `__/19` | |
| 6 Smoke | | | | |
| 7 E2E VIEWER / PLANNER / sin sesión / sin rol | | | | |
| 8 Redespliegue | | | | |
| 9 Fallos (×6) | | | | |
