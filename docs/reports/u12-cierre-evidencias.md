# U12: matriz de cierre y evidencias (`DT-100`)

**Revisión 3 (2026-10-10).** Formaliza la matriz e incorpora las pruebas y bloqueos de la sesión de Claude Code Cloud
del mismo día.

- **Base revisada:** `main` en `5460fd9` (PR #4).
- **Estado de U12:** **desplegada y verificada en `dev`; no cerrada.**
- **Fuente única del estado de U12:** este informe. `DT-100`, `project/status.md`, `project/roadmap.md`, `CLAUDE.md`
  y [`docs/00-guia-maestra.md`](../00-guia-maestra.md) §G **enlazan aquí** y no mantienen copias de la matriz.

## 0. Origen de la evidencia

| Marca | Origen |
|---|---|
| **[AZ-U]** | Ejecutado en Azure **por el responsable** con su sesión de PowerShell y compartido el 2026-10-10. **No lo ejecutó ningún agente**, no hay copia versionada (`tmp/` está excluido de Git) y se recoge tal como el responsable lo resumió. |
| **[AZ-A]** | Ejecutado en Azure por un agente con acceso autorizado. **Hasta hoy, ninguno** (§3.2). |
| **[CC]** | Ejecutado por el agente en Claude Code Cloud: local o en un entorno sustituto. **No aprueba un criterio de Azure.** |
| **[CI]** | GitHub Actions, con su número de *run*. |
| **[PEND]** | Sin ejecutar o sin evidencia suficiente. |

## 1. Matriz C01–C15: matriz de seguimiento derivada

`DT-100` exige «los 15 criterios de cierre» y solo nombra sus áreas: despliegue, OIDC, ACR, PostgreSQL, *bootstrap*,
frontend, API, Entra con la URL real, redespliegue y fallos. **Ningún documento los enumera.**

C01–C15 es una **matriz de seguimiento derivada** de `DT-100` y de `infra/azure/u12/README.md` §5–§6:

- **no** es una lista original aprobada;
- **no** añade requisitos funcionales;
- queda en estado **`PROPUESTA`** hasta que el responsable la valide (`CLAUDE.md` §7).

Si la lista validada difiere, prevalece la del responsable y esta matriz se ajusta.

**Estados:**

- `APROBADO`: hay salida real que cumple la aceptación;
- `PARCIAL`: parte demostrada, parte pendiente;
- `PENDIENTE`: sin ejecutar;
- `BLOQUEADO`: no puede ejecutarse por una causa externa identificada;
- `NO APLICA`.

Responsable de toda ejecución en Azure y en el navegador: **el responsable del proyecto**, con su sesión (`DT-100`,
`CLAUDE.md` §17).

### C01 — Infraestructura desplegada

| Campo | Contenido |
|---|---|
| Requisito y referencia | «despliegue» (`DT-100`, *Estado*); `DT-100` §1; README §5 pasos 4 y 8 |
| Aceptación | `u12-dev` `Succeeded`; api, frontend y job creados; entorno `WorkloadProfiles` |
| Procedimiento | `-Stage Core` y `-Stage Apps -ImageTag <sha>`; comprobación con `-Stage Verify` |
| Entorno | Azure `dev` (`rg-motor-predictivo-dev`, `centralus`) |
| Evidencia requerida | Estado del despliegue y de los recursos |
| Resultado | **[AZ-U]** `u12-dev` `Succeeded`, sin error. `ca-mpa-dev-api` y `ca-mpa-dev-frontend` `Succeeded`/`Running`. `caj-mpa-dev-bootstrap` creado. `cae-mpa-dev` convertido a `WorkloadProfiles` en el mismo recurso, sin recrearlo. Verify: «entorno en modo WorkloadProfiles» OK. **[CC]** `build`/`lint` de Bicep y guardias del *what-if* (`infra/tests`) |
| Estado | **APROBADO** |

### C02 — OIDC de GitHub con permisos mínimos

| Campo | Contenido |
|---|---|
| Requisito y referencia | «OIDC»; `DT-100` §7; README §2 |
| Aceptación | `azure/login` por OIDC sin secretos; `id-mpa-dev-github` con 4 roles dentro del grupo y sin `deploy/action` |
| Procedimiento | *Deploy dev* y `-Stage Verify` |
| Entorno | GitHub Actions y Azure |
| Evidencia requerida | *Run* en verde y comprobaciones de roles |
| Resultado | **[CI]** *Deploy dev* #2 y #3 en verde (runs 37902049561 y 38016512995). **[AZ-U]** Verify: «GitHub: 4 roles mínimos», «GitHub sin deploy/action» y la identidad de ejecución solo con `AcrPull`, todo OK |
| Estado | **APROBADO** |

### C03 — ACR y descarga por identidad

| Campo | Contenido |
|---|---|
| Requisito y referencia | «ACR»; `DT-100` §3 |
| Aceptación | ACR Basic sin usuario administrador; *push* con `AcrPush`; las apps y el job descargan con `id-mpa-dev-runtime` |
| Procedimiento | *Deploy dev*; `-Stage Apps`; `-Stage Verify` |
| Entorno | Azure y GitHub |
| Evidencia requerida | Push en verde; apps en ejecución; Verify |
| Resultado | **[CI]** run 38016512995 publicó `backend`, `frontend` y `bootstrap` con la etiqueta `2742539…`. **[AZ-U]** apps `Running`; Verify: «ACR Basic sin usuario administrador» e «imágenes con identidad administrada» OK |
| Estado | **APROBADO** |

### C04 — PostgreSQL

| Campo | Contenido |
|---|---|
| Requisito y referencia | «PostgreSQL»; `DT-100` §4 |
| Aceptación | Flexible 16, `Standard_B1ms`, sin HA, `require_secure_transport=ON`, `Ready` |
| Procedimiento | `-Stage Verify` |
| Entorno | Azure |
| Evidencia requerida | Comprobaciones de Verify |
| Resultado | **[AZ-U]** «PostgreSQL 16, B1ms, sin alta disponibilidad», «TLS obligatorio» y «arrancado (Ready)», OK |
| Estado | **APROBADO** |

### C05 — Firewall reconciliado

| Campo | Contenido |
|---|---|
| Requisito y referencia | `DT-100` §5; README §4; README §6, fila «Firewall desactualizado» |
| Aceptación | Solo reglas `aca-out-<ip>` (una por IP de salida actual, nunca `0.0.0.0`) **y** `-Stage Firewall` termina sin error con el script corregido |
| Procedimiento | `-Stage Firewall`. Si las IP cambiaron, hay un *what-if* y se pide `FIREWALL`; si no, «Las reglas ya coinciden…». Después lista las reglas, borra las obsoletas y `-Stage Verify` |
| Entorno | Azure |
| Evidencia requerida | Salida completa de `-Stage Firewall` y Verify posterior |
| Resultado | **[AZ-U]** Las reglas `aca-out-*` existen; Verify: «firewall: solo IP de salida (aca-out-*), sin 0.0.0.0» OK. Corrección de la CLI (`--server-name`; `--name` = regla en `delete`; nunca `--rule-name`) en `dd2d45f`, en `main`, con prueba de regresión. **[PEND]** Ninguna salida completa de `-Stage Firewall` posterior a la corrección. **[CC]** Sin acceso a Azure (§3.2) |
| Estado | **PARCIAL**: la configuración es correcta; falta la reconciliación con el script corregido. No es un fallo ni un aprobado |
| Motivo y responsable | Requiere la sesión de Azure del responsable |

### C06 — Key Vault y secretos

| Campo | Contenido |
|---|---|
| Requisito y referencia | `DT-100` §6; README §3 |
| Aceptación | Opción C (`publicNetworkAccess=Disabled`, plantillas habilitadas, `bypass=AzureServices`); contraseñas solo como `secretRef`; `DATABASE_URL` sin contraseña; la sesión que despliega tiene `deploy/action` |
| Procedimiento | `-Stage Verify` |
| Entorno | Azure |
| Evidencia requerida | Comprobaciones de Verify |
| Resultado | **[AZ-U]** «Key Vault opción C», «contraseñas solo como secretRef, DATABASE_URL sin contraseña» y «tu sesión puede usar getSecret», OK (parte de 19/19) |
| Estado | **APROBADO** |

### C07 — Bootstrap en Azure

| Campo | Contenido |
|---|---|
| Requisito y referencia | «bootstrap»; `DT-100` §2; README §5 paso 9 |
| Aceptación | Una ejecución del job en `Succeeded` y `BOOTSTRAP OK`: dataset, migrate, ingest, forecast, recommend y rol `mpa_app` |
| Procedimiento | `-Stage Bootstrap` |
| Entorno | Azure |
| Evidencia requerida | Nombre de la ejecución, estado y resumen de filas |
| Resultado | **[AZ-U]** `caj-mpa-dev-bootstrap-tbazfuc`: `BOOTSTRAP OK` y `BOOTSTRAP Succeeded`. Filas: `data_loads` 1, `products` 100, `inventory` 100, `consumption` 108 235, `calculation_runs` 2, `forecasts` 3 990, `recommendations` 100. 100 candidatos: 50 `RECOMMEND`, 40 `NO_NEED` y 10 `NOT_CALCULABLE`. Motor `0.1.0`, política `V1_PROVISIONAL`. Verify: «bootstrap: última ejecución Succeeded» OK. **[CC]** mismos recuentos en local (§3.1) |
| Estado | **APROBADO** |

### C08 — Frontend HTTPS

| Campo | Contenido |
|---|---|
| Requisito y referencia | «frontend»; README §5 pasos 10 y 11 |
| Aceptación | Ingress externo solo HTTPS y 200 en `/` y en una ruta profunda de la SPA |
| Procedimiento | `-Stage Verify`; `python infra/docker/smoke.py --entra` |
| Entorno | Azure (URL pública) |
| Evidencia requerida | Verify y smoke |
| Resultado | **[AZ-U]** Verify: «frontend solo HTTPS» y «responde 200 por HTTPS» OK. Smoke: `/` y la ruta profunda → 200 |
| Estado | **APROBADO** |

### C09 — API interna detrás del proxy

| Campo | Contenido |
|---|---|
| Requisito y referencia | «API»; `DT-100` §1 y §8 |
| Aceptación | Ingress interno, solo HTTPS; a través del proxy, sin token → 401 |
| Procedimiento | `-Stage Verify`; smoke `--entra` |
| Entorno | Azure |
| Evidencia requerida | Verify y smoke |
| Resultado | **[AZ-U]** Verify: «api sin ingress público y solo HTTPS» y «API viva tras el proxy (/api/v1/me sin token → 401)» OK. Smoke: peticiones sin token → 401; `/api/v1/runs/1` sin token → 401 |
| Estado | **APROBADO** |

### C10 — Entra ID con la URL real

| Campo | Contenido |
|---|---|
| Requisito y referencia | «Entra con la URL real»; `DT-100` §8; README §5 paso 5 |
| Aceptación | *Redirect URI* `https://<FQDN del frontend>` aplicado a la SPA e **inicio de sesión real** con MSAL en esa URL |
| Procedimiento | `deploy-u11.ps1` (aplica o confirma); iniciar sesión en el navegador |
| Entorno | Azure, Entra ID y navegador |
| Evidencia requerida | Salida de `deploy-u11.ps1` (o `ALREADY_CONFIGURED`) y sesión iniciada (`/me` con el rol) |
| Resultado | **[AZ-U]** Smoke `SMOKE OK (entra-dev)`: la SPA contiene los identificadores esperados de `entra-dev.env`; con `APP_ENV=dev` se rechazan el token de desarrollo y un RS256 falsificado (401). La URL real está en el estado deseado `infra/azure/entra/u11-entra.dev.json`. **[PEND]** Inicio de sesión real; no consta salida de `deploy-u11.ps1` con esa URL. El smoke **no sustituye** al E2E |
| Estado | **PARCIAL** |
| Motivo y responsable | Necesita navegador y una cuenta del tenant: el responsable |

### C11 — Matriz de roles en el navegador

| Campo | Contenido |
|---|---|
| Requisito y referencia | README §6 E2E; matriz de [`docs/07-api.md`](../07-api.md) §7.2; método de `/acceso` en `infra/azure/entra/README.md` §4 |
| Aceptación | VIEWER en `/acceso`: `runs` e `history` → 403 y el resto no 403, con «Coincide» = sí en las 13 filas. PLANNER: 13 sin 403. Sin sesión → 401. Sin rol → 403 en todo salvo `/me` |
| Procedimiento | `deploy-u11.ps1 -AssignRole VIEWER` → iniciar sesión en la URL de Azure → `/acceso` → «Comprobar la matriz». Después PLANNER y `-RemoveRole`, cerrando sesión entre cambios |
| Entorno | Navegador con la URL real |
| Evidencia requerida | Tabla de `/acceso` por rol, que no contiene tokens |
| Resultado | **[PEND]** **[CC]** cubierto por pruebas automatizadas (`test_entra.test_role_matrix`, `tests/api`), que no sustituyen a la prueba real |
| Estado | **PENDIENTE** |
| Motivo y responsable | Navegador y cuenta real: el responsable. Bloqueado para el agente (§3.2) |
| Ambigüedad | README §6 dice «11 permitidos → 200»; un 404 legítimo (id inexistente) no es un 403. Se acepta «no 403 y Coincide = sí», que es el criterio de `/acceso` en U11. **A confirmar por el responsable** |

### C12 — Datos reales en el navegador

| Campo | Contenido |
|---|---|
| Requisito y referencia | README §6 E2E |
| Aceptación | Con VIEWER: catálogo, detalle de producto, un pronóstico y una recomendación con su explicación, servidos por la API real |
| Procedimiento | Recorrido en la interfaz tras C11 |
| Entorno | Navegador |
| Evidencia requerida | Lista de vistas comprobadas con su identificador (sin tokens) |
| Resultado | **[PEND]** |
| Estado | **PENDIENTE** |
| Motivo y responsable | El responsable |

### C13 — Redespliegue idempotente

| Campo | Contenido |
|---|---|
| Requisito y referencia | «redespliegue»; `DT-100` §2; README §6 *Redespliegue* |
| Aceptación | api, frontend y job con la etiqueta nueva. La ejecución del job en `Succeeded`, con migración ya aplicada sin reaplicar, ingesta `ALREADY_LOADED` y forecast/recommend `ALREADY_COMPUTED`. Los mismos recuentos que C07. Ejecuciones visibles sin cambio y `/ejecuciones/<n+1>` → 404 |
| Procedimiento | Cambio inocuo integrado en `main` → *Deploy dev* con `run_bootstrap=true` → `az containerapp show … --query properties.template.containers[0].image` (×3) → registros del job (portal, *Console logs*: sin Log Analytics no hay registros por CLI) → interfaz |
| Entorno | GitHub Actions, Azure y navegador |
| Evidencia requerida | Run de *Deploy dev*, las tres etiquetas, líneas `ALREADY_*`, recuentos y 404 |
| Resultado | **[PEND]**. **[CC]** dos ejecuciones locales de `bootstrap.py` idempotentes (§3.1): **no** aprueban el criterio |
| Estado | **PENDIENTE** |
| Motivo y responsable | El responsable dispara *Deploy dev* o autoriza expresamente al agente a dispararlo (§3.2). La verificación de registros y del 404 requiere portal y navegador |

### C14 — Pruebas de fallo

| Campo | Contenido |
|---|---|
| Requisito y referencia | README §6 *Fallos* (seis filas) |
| Aceptación | Por cada prueba: el efecto esperado de la tabla y su recuperación, sin pérdida de datos |
| Procedimiento | [`docs/00-guia-maestra.md`](../00-guia-maestra.md) §F.4 |
| Entorno | Azure |
| Evidencia requerida | Resultado y recuperación de cada prueba, con Verify 19/19 al final |
| Resultado | **[PEND]** en Azure. **[AZ-U]** relacionado: el smoke mostró rechazo (401) de tokens de desarrollo y RS256 falsificados, pero no es el caso literal `Bearer x`. **[CC]** con la base detenida, `bootstrap.py` se para en el paso 2 y se recupera; `Bearer x` → 401 en `tests/api` |
| Estado | **PENDIENTE** |
| Alcance | Exigidas por el responsable (2026-10-10): **PostgreSQL detenido y recuperación**, **token inválido** e **imagen inexistente**. Las otras tres filas de README §6 (firewall desactualizado, job con fallo y Key Vault inaccesible) quedan **pendientes de decisión de alcance**; no se marcan `NO APLICA` sin esa decisión |
| Motivo y responsable | El responsable. El token inválido es de solo lectura y podría ejecutarlo un agente si tuviera red hacia la URL (§3.2) |

### C15 — Cierre documental

| Campo | Contenido |
|---|---|
| Requisito y referencia | `CLAUDE.md` §8 y §12; README §5 |
| Aceptación | C01–C14 en `APROBADO` (o `NO APLICA` justificado); matriz validada por el responsable; `status.md`, `roadmap.md` y `DT-100` actualizados; evidencias sin secretos |
| Procedimiento | `docs/00-guia-maestra.md` §G.2 |
| Entorno | Repositorio |
| Evidencia requerida | PR con los cambios |
| Resultado | **[PEND]** |
| Estado | **PENDIENTE**, hasta completar C05, C10–C14 |

### Resumen

| Estado | Criterios |
|---|---|
| APROBADO (8) | C01, C02, C03, C04, C06, C07, C08, C09 |
| PARCIAL (2) | C05, C10 |
| PENDIENTE (5) | C11, C12, C13, C14, C15 |
| BLOQUEADO / NO APLICA | — (los bloqueos de §3.2 afectan al agente, no al criterio) |

## 2. Fuentes de la evidencia [AZ-U]

Resumen literal aportado por el responsable el 2026-10-10. No se vuelve a pedir:

- **Apps:** api y frontend `Succeeded`/`Running`; `caj-mpa-dev-bootstrap` creado y `Succeeded`; `u12-dev`
  `Succeeded`; `cae-mpa-dev` convertido a `WorkloadProfiles` en el mismo recurso.
- **Bootstrap:** C07.
- **Verify:** «U12: dev verificado», con las 19 comprobaciones del script en `OK`:
  - ACR;
  - PostgreSQL 16/B1ms/sin HA;
  - TLS;
  - firewall;
  - api interna HTTPS;
  - entorno `WorkloadProfiles`;
  - frontend HTTPS;
  - imágenes por identidad;
  - job manual;
  - roles de GitHub;
  - identidad de ejecución;
  - Key Vault opción C;
  - `deploy/action` propia;
  - GitHub sin `deploy/action`;
  - `secretRef`;
  - PostgreSQL `Ready`;
  - *bootstrap* `Succeeded`;
  - frontend 200;
  - API → 401 sin token.
- **Smoke:** `python infra/docker/smoke.py --entra` → `SMOKE OK (entra-dev)`.

## 3. Pruebas y bloqueos de la sesión de Claude Code Cloud (2026-10-10)

### 3.1 Ejecutado [CC]

Herramientas descargadas al directorio temporal de la sesión y verificadas, no instaladas en el repositorio:

- Bicep 0.48.1 (SHA-256 de `ci.yml`);
- PowerShell 7.4.6 (`hashes.sha256` de la publicación);
- Node 24.21.0 con npm 11.19.0 (`SHASUMS256.txt` de nodejs.org).

Python 3.13.16; dependencias fijadas en un *venv* temporal.

| Prueba | Resultado |
|---|---|
| `python infra/ci/secret_scan.py` | 0 hallazgos |
| `infra/tests` con Bicep 0.48.1 y `pwsh` 7.4.6 | 95 OK, 0 omitidas (incluye `-SelfTest`, `-PreflightOnly` y los flujos con el Azure CLI falso) |
| Backend, suite por defecto | 353 OK |
| `tests/api` (grupos `db`, `api`, `test`, `entra`) | 95 OK |
| `tests/db`, integración contra PostgreSQL 16.15 efímero (`U2_TEST_ADMIN_DSN`) | 177 OK |
| Frontend con Node 24.21.0: `npm ci`, ESLint, `tsc`, Prettier, Vitest y build | todo con código 0; Vitest 23 archivos, 176 pruebas; build con un aviso de tamaño de *chunk* |
| `bootstrap.py` ×2 contra PostgreSQL 16.15 local, sobre `5460fd9` | 1.ª `applied: 0001…0004`, `COMPLETED` ×3, `BOOTSTRAP OK`; 2.ª `applied: none`, `ALREADY_LOADED`, `ALREADY_COMPUTED` ×2, recuentos idénticos a C07 |
| `mpa_app` tras el *bootstrap* | `SELECT` OK; `DELETE` y `CREATE TABLE` denegados |
| `bootstrap.py` con la base detenida | código 1 en el paso 2 (migraciones); recuperación con `BOOTSTRAP OK` al arrancar la base |

**No ejecutado:** smoke de Docker Compose, porque no hay *daemon* de Docker. Lo cubre el job `docker` de CI, en verde
en `main` `62f25ca` (run 38035570538) **[CI]**.

### 3.2 Bloqueos exactos para las pruebas en Azure

| Prueba | Bloqueo | Qué lo levantaría |
|---|---|---|
| `-Stage Firewall` (C05), fallos con `Stop`/`Start` e imagen inexistente (C14) | El contenedor no tiene Azure CLI ni credenciales de Azure (`~/.azure` no existe, ninguna variable `AZURE_*`). `CLAUDE.md` §17: el agente nunca recibe credenciales | Ejecución por el responsable |
| Token inválido (C14) y smoke contra la URL real | El proxy de salida de la sesión **rechaza** `ca-mpa-dev-frontend.greensmoke-cfd723ad.centralus.azurecontainerapps.io:443` (`connect_rejected`, política de red del entorno) | Ejecución por el responsable, o añadir ese dominio a los permitidos del entorno de Claude Code Cloud |
| E2E (C10–C12) | Sin navegador interactivo ni cuenta del tenant | El responsable |
| Redespliegue (C13) | El agente podría disparar *Deploy dev* (`workflow_dispatch`) desde las herramientas de GitHub, pero eso **crea revisiones nuevas en Azure** y **no lo ha autorizado expresamente** el responsable. Además, verificar `ALREADY_*`, los recuentos y el 404 requiere el portal y el navegador | Autorización explícita para disparar el workflow, más la verificación por el responsable |

## 4. Plan mínimo para lo pendiente

Lo ejecuta el responsable. No repite Apps, Bootstrap, Verify ni el smoke.

| # | Acción | Cierra |
|---|---|---|
| 1 | `deploy-u12.ps1 -Stage Firewall`, y después `-Stage Verify` | C05 |
| 2 | `deploy-u11.ps1` (confirmar *redirect URI*); E2E con VIEWER, PLANNER, sin sesión y sin rol (C11) y vistas de datos (C12) | C10, C11, C12 |
| 3 | *Deploy dev* con `run_bootstrap=true` sobre `main` actual. El último commit de `main` es solo documental, así que sirve como cambio inocuo. Después las comprobaciones de C13 | C13 |
| 4 | Fallos de `docs/00-guia-maestra.md` §F.4, en este orden: token inválido, imagen inexistente con su restauración, PostgreSQL detenido con su recuperación, y Verify al final | C14 |
| 5 | Validar C01–C15, actualizar este informe y cerrar U12 en `DT-100`, `status.md` y `roadmap.md` | C15 |

## 5. Registro de evidencias reales

| Paso | Origen | Resultado | Estado |
|---|---|---|---|
| Despliegue `u12-dev` y apps | [AZ-U] | `Succeeded`; api y frontend `Running`; job creado | APROBADO |
| Bootstrap | [AZ-U] | `caj-mpa-dev-bootstrap-tbazfuc`, `BOOTSTRAP OK` | APROBADO |
| Verify | [AZ-U] | 19/19, «U12: dev verificado» | APROBADO |
| Smoke Entra | [AZ-U] | `SMOKE OK (entra-dev)` | APROBADO (C08, C09); parcial para C10 |
| Firewall completo | — | | PENDIENTE |
| E2E | — | | PENDIENTE |
| Redespliegue | — | | PENDIENTE |
| Fallos ×3 (+3 por decidir) | — | | PENDIENTE |
| Cierre documental | — | | PENDIENTE |

## Historial del informe

| Revisión | Cambio |
|---|---|
| 1 (2026-10-10, `fe032c5`) | Primera matriz `PROPUESTA` y plan, antes de la evidencia real |
| 2 (2026-10-10, `527c3f7`) | Evidencia real de Azure aportada por el responsable |
| 3 (2026-10-10) | Matriz formal por criterio (requisito, aceptación, procedimiento, entorno, evidencia, resultado, estado y responsable); pruebas y bloqueos de Claude Code Cloud; fuente única del estado de U12 |
