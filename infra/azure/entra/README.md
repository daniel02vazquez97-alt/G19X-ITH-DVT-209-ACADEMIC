# Microsoft Entra ID del entorno `dev` (U11, `DT-099`)

Autenticación y autorización reales para `dev`: la SPA inicia sesión con MSAL (código de autorización + PKCE),
obtiene un **token de acceso para la API** y la API lo valida (firma, emisor, audiencia, vigencia, tenant,
scope) y aplica los **app roles** de ASSUMPTION-010 con la matriz de `docs/07` §7.2.

**`APP_ENV=local` no cambia:** sin Azure, sin Entra ID y con los tokens `dev-…` de siempre. Nada de este
directorio es necesario para trabajar en local ni para las pruebas.

## Qué se configura

| Objeto | Nombre | Configuración |
|---|---|---|
| Registro de la API | `app-mpa-dev-api` | Un solo tenant; Application ID URI `api://<appId>`; scope delegado `access_as_user`; tokens v2.0 (`aud` = appId de la API); cuatro app roles `VIEWER`, `ANALYST`, `PLANNER`, `ADMIN` (miembros: usuarios); la SPA preautorizada para el scope; sin flujo implícito; sin secretos |
| Service principal de la API | — | `appRoleAssignmentRequired = true` (defensa para clientes solo de aplicación). **No** impide el token a un usuario sin rol: quien bloquea es la API (403) |
| Registro de la SPA | `app-mpa-dev-spa` | Un solo tenant; plataforma **SPA** con `http://localhost:5173` (Vite) y `http://localhost:8080` (Docker); único permiso: `access_as_user` de la API; sin secretos ni certificados; sin flujo implícito |
| Service principal de la SPA | — | Creado explícitamente |

No se pide **ningún permiso de Microsoft Graph** para la aplicación (ni `User.Read`). MSAL solicita además
`openid`, `profile` y `offline_access` al iniciar sesión, que son los de OpenID Connect.

Estado deseado: `u11-entra.dev.json` (GUID fijos de roles y scope; nunca se regeneran). La identidad
`id-mpa-dev-github` de U10 es otra cosa (GitHub Actions → Azure) y no se toca.

## 1. Configurar (en la máquina del responsable, desde la raíz del repositorio)

```
az login
az account show --query "{tenant:tenantId, suscripcion:name}" --output table
powershell -ExecutionPolicy Bypass -File infra\azure\deploy-u11.ps1 -SelfTest
powershell -ExecutionPolicy Bypass -File infra\azure\deploy-u11.ps1 -PreflightOnly
powershell -ExecutionPolicy Bypass -File infra\azure\deploy-u11.ps1
```

- `-SelfTest` no llama a Azure: comprueba el tratamiento de JSON y las comparaciones en tu PowerShell.
- `-PreflightOnly` solo lee: tenant, permiso para registrar aplicaciones, registros existentes y plan.
- La ejecución normal pide escribir `CONFIGURAR`, crea o corrige lo que falte y verifica. Si todo ya estaba
  bien, dice `ALREADY_CONFIGURED` y no cambia nada. Se puede repetir sin duplicar nada.
- Si la cuenta no puede registrar aplicaciones (`Authorization_RequestDenied` o la política del tenant), se
  **detiene** y dice qué hace falta: que *Users can register applications* esté en **Yes** o el rol
  **Application Developer** asignado por un administrador del tenant. No intenta elevar privilegios.

Deja en `tmp/u11-evidence/` (ignorado por Git), solo con identificadores:
`u11-evidence.json`, `entra-dev.env` (API y Docker) y `frontend.env.development.local` (Vite).

## 2. Asignar roles (explícito; nadie tiene roles por defecto)

Solo al **usuario que ejecuta el script** (el responsable), para la prueba de `dev`:

```
powershell -ExecutionPolicy Bypass -File infra\azure\deploy-u11.ps1 -AssignRole VIEWER
powershell -ExecutionPolicy Bypass -File infra\azure\deploy-u11.ps1 -RemoveRole VIEWER
```

La asignación es directa a usuarios: asignar **grupos** a una aplicación exige Microsoft Entra ID P1 o P2
(Microsoft Learn). Quién aprueba asignaciones a otras personas sigue pendiente (`docs/10` §3.3). Un cambio de
roles llega en el **siguiente** token: cerrar sesión en la SPA y volver a entrar.

## 3. Levantar el sistema en modo `dev`

Con Docker (recomendado), desde la raíz, en un **proyecto Compose aislado `u11-entra-dev`**: contenedores, red y
volúmenes propios (`u11-entra-dev_pgdata`, `u11-entra-dev_dataset`), distintos de los del entorno local (proyecto
`infra`: `infra_pgdata`, `infra_dataset`). Su PostgreSQL empieza vacía y aplica las migraciones desde cero; nunca
reutiliza la base local. El archivo de U11 fija `name: u11-entra-dev` y los comandos lo repiten con `-p`.

```powershell
# 1. Liberar los puertos 5432/8000/8080 del entorno local. `stop` no borra contenedores ni volúmenes.
docker compose -f infra/docker-compose.yml --profile app stop

# 2. Levantar U11 aislado.
docker compose -p u11-entra-dev -f infra/docker-compose.yml -f infra/docker-compose.entra-dev.yml --env-file tmp/u11-evidence/entra-dev.env --profile app up --build -d

# 3. Comprobar: init terminado (exit 0), api y frontend healthy, migraciones de una base nueva, smoke.
docker compose -p u11-entra-dev -f infra/docker-compose.yml -f infra/docker-compose.entra-dev.yml --env-file tmp/u11-evidence/entra-dev.env --profile app ps -a
docker compose -p u11-entra-dev -f infra/docker-compose.yml -f infra/docker-compose.entra-dev.yml --env-file tmp/u11-evidence/entra-dev.env --profile app logs --no-color init
docker compose -p u11-entra-dev -f infra/docker-compose.yml -f infra/docker-compose.entra-dev.yml --env-file tmp/u11-evidence/entra-dev.env --profile app exec postgres psql -U postgres -d inventory -c "SELECT version, left(sha256, 16) AS sha256, applied_at FROM schema_migrations ORDER BY version"
docker volume ls --filter name=u11-entra-dev
python infra/docker/smoke.py --entra
```

`smoke.py --entra` recorre lo mismo que la smoke de U7 hasta la autenticación (API, SPA, proxy) y comprueba que
la API está en `dev`: rechaza el token de desarrollo y un token falsificado (401) y la SPA está compilada con los
identificadores de `entra-dev.env`. Los datos detrás de la autenticación los comprueba la prueba real (`/acceso`).

Abrir **http://localhost:8080** (con `localhost`, no `127.0.0.1`: es el redirect URI registrado).

Sin Docker: API con `APP_ENV=dev` y las tres variables de `entra-dev.env` (más `DATABASE_URL`), y la SPA con
`npm run dev` tras copiar `tmp/u11-evidence/frontend.env.development.local` a
`frontend/.env.development.local`; abrir **http://localhost:5173**.

Volver a local: parar U11 (`docker compose -p u11-entra-dev … stop`) y el comando de siempre, sin el segundo
`-f` ni `-p` (`docs/12` §3.4).

**Por qué el proyecto aislado (2026-10-07).** Sin `-p`, Compose llama al proyecto como la carpeta del primer
archivo (`infra`) y U11 reutilizaba `infra_pgdata`, migrada antes con otros bytes de `0001_dataset_tables.sql`:
`MigrationError: applied migration 0001_dataset_tables has changed on disk`. La migración no cambió de contenido;
`app.db.migrations` guarda el SHA-256 de los **bytes** del archivo y el árbol de trabajo de Windows tiene CRLF
(`core.autocrlf=true`) mientras que Git y Linux tienen LF: 0001 da `e6dfdfb9…` con CRLF y `82574549…` con LF. La
protección se mantiene tal cual; ver `DT-099` (pendiente: decidir cómo normalizar los finales de línea).

## 4. Prueba real (criterio 14 de U11)

No guardes ni pegues tokens; basta con lo que muestra la interfaz y el registro de acceso de la API
(`docker compose ... logs api`), que solo contiene `subject_id` (el `oid`), ruta y estado.

| # | Situación | Cómo | Resultado esperado |
|---|---|---|---|
| 1 | Usuario autorizado | `-AssignRole VIEWER`, iniciar sesión, abrir Productos | 200: la lista se ve; el registro muestra `/api/v1/products` 200 con tu `oid` |
| 2 | Autenticado sin el rol | Con solo `VIEWER`, abrir **`/acceso`** y pulsar «Comprobar la matriz rol × endpoint» | `GET /api/v1/runs/1` y `/products/1/history` → **403** de la API; el resto, no 403; columna «Coincide» = sí en las 13 filas |
| 3 | No autenticado | `curl -i http://127.0.0.1:8000/api/v1/products` y con `Authorization: Bearer x` | 401 `AUTHENTICATION_REQUIRED` y 401 `INVALID_TOKEN` |
| 4 | Sin ningún rol | `-RemoveRole VIEWER,PLANNER`, cerrar sesión y entrar, `/acceso` | Roles «ninguno»: `/me` 200 y los otros 12 endpoints **403** de la API (comprobado el 2026-10-07; Entra ID sí emite el token) |
| 5 | Cambio de rol | `-AssignRole PLANNER`, cerrar sesión y entrar | `/ejecuciones/1` responde 200 |

`/acceso` existe porque la interfaz oculta lo que un rol no puede usar (RS-003): esa página hace las 13
peticiones reales con el token de la sesión y muestra solo el código HTTP de cada una, así que el 403 del
backend se ve sin copiar ningún token. Pega esa tabla (no contiene tokens) como evidencia.

## Problemas frecuentes

| Mensaje | Causa | Qué hacer |
|---|---|---|
| `dataset-1` e `init-1` aparecen detenidos en Docker Desktop | Son tareas de una sola vez: publican el dataset y migran/cargan/calculan, y terminan | Normal si `ps -a` muestra `Exited (0)`; cualquier otro código, ver `logs init`. No hay que arrancarlos a mano |
| `in_mem_redirect_unavailable` | SPA compilada con la caché en memoria (versión inicial de U11) | Reconstruir la imagen `frontend` (`up --build -d frontend`) |
| `AADSTS50011` | El origen no coincide con un redirect URI registrado | Abrir `http://localhost:8080` o `http://localhost:5173`, no `127.0.0.1` |
| Todo da 403 y «Roles de la sesión: ninguno» | El usuario no tiene ningún rol en la API | `-AssignRole VIEWER`, cerrar sesión y volver a entrar |
| `AADSTS65001` / aprobación de administrador | El tenant no permite que los usuarios den consentimiento a `openid profile offline_access` | Un administrador del tenant concede el consentimiento a `app-mpa-dev-spa` (U11 queda detenida ahí; no se cambia la política) |
| La SPA dice «La API rechazó el token» | Variables de la API distintas de las de la SPA | Usar el mismo `entra-dev.env` para la API y la compilación de la SPA |
| API: `REFUSED: APP_ENV=dev requires …` | Falta una variable o `DEV_AUTH_IDENTITIES` está definida | Revisar `entra-dev.env` |

## Deshacer

Solo lo que creó **una** ejecución concreta (`tmp/u11-evidence/created-<ejecución>.json`):

```
powershell -ExecutionPolicy Bypass -File infra\azure\deploy-u11.ps1 -Rollback <ejecución>
```

Pide escribir `ELIMINAR`, vuelve a leer cada objeto y no borra nada que no coincida con el registro. Las
aplicaciones borradas quedan 30 días en *Deleted applications* de Entra ID. No existe un «borrar todo».

### Entorno Docker de U11

Al terminar la prueba real (y guardada la evidencia), se elimina **solo** el proyecto `u11-entra-dev`:

```powershell
docker compose -p u11-entra-dev -f infra/docker-compose.yml -f infra/docker-compose.entra-dev.yml --env-file tmp/u11-evidence/entra-dev.env --profile app down -v
```

Borra sus contenedores, sus volúmenes (`u11-entra-dev_*`) y su red; no toca el proyecto `infra` (entorno local)
ni las aplicaciones de Entra ID. Nunca ejecutar `down -v` sin `-p u11-entra-dev`.
