# U12 — despliegue de `dev` en Azure Container Apps (`DT-100`)

Despliegue del sistema completo (frontend, API, PostgreSQL y carga inicial) en el grupo `rg-motor-predictivo-dev`
de U10, región `centralus`, entorno `dev` únicamente. Lo ejecuta el responsable con su sesión de Azure CLI; el
agente no ve ni maneja contraseñas, tokens ni cadenas de conexión con secreto.

## 1. Arquitectura

```
navegador ──HTTPS──► ca-mpa-dev-frontend (ingress externo, nginx :8080, MSAL)
                         │  /api/* → https://ca-mpa-dev-api.internal.<dominio>   (API_UPSTREAM, TLS verificado)
                         ▼
                     ca-mpa-dev-api (ingress interno, FastAPI :8000, tokens de Entra ID)
                         │  TLS (sslmode=require), usuario mpa_app (solo lectura)
                         ▼
                     psql-mpa-dev-<sufijo> (PostgreSQL 16, B1ms, firewall = IP de salida del entorno)
                         ▲  usuario mpa_owner (migraciones, carga)
                     caj-mpa-dev-bootstrap (job manual: dataset → migrate → ingest → forecast → recommend)

acr<proyecto><env><sufijo> (ACR Basic) ◄─ AcrPush ─ GitHub Actions (OIDC, id-mpa-dev-github)
                                       ─ AcrPull ─► id-mpa-dev-runtime (identidad de las apps y del job)
kv-mpa-dev-… (U10, sin acceso público) ─ getSecret en tiempo de despliegue ARM ─► secretos de Container Apps
```

| Recurso | Nombre | SKU / configuración |
|---|---|---|
| Registro | `acrmpadev<sufijo>` | Basic, sin usuario administrador |
| PostgreSQL | `psql-mpa-dev-<sufijo>` | Flexible Server 16, `Standard_B1ms` Burstable, 32 GB sin autocrecimiento, copias 7 días sin georredundancia, sin HA, `require_secure_transport=ON`, base `inventory` |
| Entorno | `cae-mpa-dev` | Container Apps estándar (`environmentMode: WorkloadProfiles`, nunca Express), perfil Consumption únicamente, sin Log Analytics |
| API | `ca-mpa-dev-api` | ingress interno, 0,5 vCPU / 1 GiB, 0–1 réplicas, sonda `/health` |
| Frontend | `ca-mpa-dev-frontend` | ingress externo solo HTTPS, 0,25 vCPU / 0,5 GiB, 0–1 réplicas |
| Job | `caj-mpa-dev-bootstrap` | manual, 1 vCPU / 2 GiB, 1 h de límite, sin reintentos |
| Identidad | `id-mpa-dev-runtime` | asignada por el usuario; solo `AcrPull` sobre el registro |

`<sufijo>` lo calcula `uniqueString` sobre el grupo; los nombres reales quedan en los *outputs* del despliegue
`u12-dev` y en `tmp/u12-evidence/`.

## 2. Identidades y permisos

| Identidad | Rol | Ámbito | Para qué |
|---|---|---|---|
| `id-mpa-dev-github` (U10, OIDC `environment:dev`) | `AcrPush` | registro | subir imágenes |
| | `Container Apps Contributor` | grupo `rg-motor-predictivo-dev` | nuevas revisiones de apps y job |
| | `Managed Identity Operator` | solo `id-mpa-dev-runtime` | `containerapp update` conserva la identidad asignada |
| | `Reader` (U10) | grupo | sin cambio |
| `id-mpa-dev-runtime` | `AcrPull` | registro | descargar imágenes sin contraseña |
| responsable (sesión `az`) | el que ya tenga (normalmente Owner de la suscripción de estudiante) | — | despliega la infraestructura; necesita `Microsoft.KeyVault/vaults/deploy/action` sobre el vault para `getSecret` |
| | *solo si el preflight dice `MISSING`:* `Key Vault Resource Manager Template Deployment Operator` (personalizado) | el Key Vault (asignable solo en el grupo) | únicamente `Microsoft.KeyVault/vaults/deploy/action` |

Sin Owner, sin Contributor de suscripción, sin `AZURE_CLIENT_SECRET`, sin usuario administrador del ACR.

**GitHub no necesita `deploy/action`:** el workflow no despliega Bicep ni lee el vault; solo sube imágenes y crea
revisiones (`az containerapp update`), que conservan los secretos ya copiados. `-PreflightOnly` y `Verify` comprueban
que `id-mpa-dev-github` **no** la tenga y que solo tenga los cuatro roles de la tabla, todos dentro del grupo.
`-Stage KeyVaultRole` crea el rol personalizado solo si tu sesión no tiene ya la acción (por Owner, Contributor o
Key Vault Contributor la tiene), reutiliza el existente si ya está creado y es mínimo, y lo asigna a tu usuario
sobre el Key Vault; nunca a GitHub ni a la suscripción.

## 3. Secretos y Key Vault

- Las contraseñas de `mpa_owner` y `mpa_app` las genera `deploy-u12.ps1 -Stage Secrets` (32 caracteres
  alfanuméricos, generador criptográfico) y las guarda en el Key Vault de U10 por el plano de control de ARM. No se
  imprimen ni se escriben en disco salvo el cuerpo temporal de la petición, que se borra al momento. Si ya existen,
  no se tocan.
- Container Apps **no** es un servicio de confianza del Key Vault, y el Key Vault de U10 tiene
  `publicNetworkAccess: Disabled`. Las apps no leen el vault en tiempo de ejecución: `main.bicep` usa
  `keyVault.getSecret(...)` y ARM copia el valor en los secretos de Container Apps durante el despliegue. Eso exige
  en el Key Vault `enabledForTemplateDeployment: true` y `networkAcls.bypass: AzureServices` (servicio de confianza
  «Azure Resource Manager para el despliegue de plantillas»). `publicNetworkAccess` **sigue en `Disabled`**.
- Es la **opción C de `DT-100`, aceptada por el responsable el 2026-10-08 solo para MVP/`dev`.** No es la
  arquitectura de producción: allí se migrará a VNet + endpoint privado + Key Vault privado (fuera de U12).
- Ese cambio del Key Vault es la etapa `KeyVault`: redespliega U10 con `keyVaultArmSecretAccess=true`, exige que el
  *what-if* muestre **solo** `enabledForTemplateDeployment` (false → true) y `networkAcls.bypass` (None →
  AzureServices) y que `publicNetworkAccess` siga en `Disabled`; cualquier otra propiedad (RBAC, borrado temporal,
  retención, nombre, región…) o cualquier otro recurso detiene el script. Después pide escribir `CAMBIAR-KV`.
- No se usan referencias de Key Vault en tiempo de ejecución (`keyVaultUrl` en los secretos de Container Apps):
  Key Vault → `getSecret` en el despliegue de ARM → secreto de Container Apps → variable de entorno → backend.
- Los archivos de evidencia pasan por un filtro que sustituye cualquier valor de secreto por `<redactado>`.
- En las apps la contraseña llega como `PGPASSWORD` (secreto de Container Apps); `DATABASE_URL` no lleva contraseña.
- **Rotación:** cambiar el secreto en el Key Vault **requiere volver a desplegar** para que el valor copiado a
  Container Apps se actualice: `Core` (administrador `mpa_owner`), `Apps` y `Bootstrap` (el job aplica `ALTER ROLE …
  PASSWORD` a `mpa_app` con un verificador SCRAM). Aceptable para MVP/`dev`; sin rotación automática en U12.
  `Secrets` solo crea los secretos que faltan, nunca los sobrescribe.

## 4. Red

- PostgreSQL con acceso público **restringido**: una regla `aca-out-<ip>` por cada IP de salida del entorno de
  Container Apps (`properties.outboundIpAddresses`), nunca un rango ni `0.0.0.0`. TLS obligatorio.
- **Las IP de salida pueden cambiar** (Microsoft no las garantiza en el plan Consumption) y pueden ser compartidas
  con otros clientes de la región. Si la API devuelve errores de conexión a la base, ejecutar
  `-Stage Firewall`: relee las IP, actualiza las reglas y borra las que sobran.
- Si Azure no publica IP de salida para el entorno, el script se detiene y no abre la base.
- Sin VNet, NAT Gateway ni endpoints privados (decisión de coste de `DT-100`; riesgo aceptado en §9).

## 5. Procedimiento (primera vez)

Desde la raíz del repositorio, en Windows PowerShell 5.1 o PowerShell 7, con `az login` hecho en el tenant del
proyecto y la suscripción de U10 seleccionada. Cada etapa se detiene si algo no cuadra; ninguna pide contraseñas.

| # | Comando / acción | Qué hace | Confirmación |
|---|---|---|---|
| 1 | `powershell -ExecutionPolicy Bypass -File infra\azure\deploy-u12.ps1 -PreflightOnly` | **solo lectura** (§5.1); termina en `PREFLIGHT OK` o `PREFLIGHT BLOQUEADO` y dice si hace falta `KeyVaultRole` | — |
| 1b | `… -Stage KeyVaultRole` (**solo si el preflight dice `requiere etapa KeyVaultRole`**) | rol personalizado mínimo asignado a ti sobre el Key Vault; repetir `-PreflightOnly` | `CREAR-ROL`, `ASIGNAR-ROL` |
| 2 | `… -Stage KeyVault` | redespliega U10 con `keyVaultArmSecretAccess=true`; el *what-if* solo puede tocar `enabledForTemplateDeployment` y `networkAcls.bypass` | escribir `CAMBIAR-KV` |
| 3 | `… -Stage Secrets` | crea `pg-owner-password` y `pg-app-password` si no existen | — |
| 4 | `… -Stage Core` | ACR, PostgreSQL, entorno, identidad de ejecución y roles de GitHub (`deployApps=false`); validate → what-if (tipos permitidos, sin borrados) | escribir `DESPLEGAR` |
| 5 | `.\infra\azure\deploy-u11.ps1` (como en U11) | `Core` añadió `https://ca-mpa-dev-frontend.<dominio>` a `infra/azure/entra/u11-entra.dev.json`; U11 lo aplica al registro de la SPA | la de U11 |
| 6 | GitHub → Settings → Environments → `dev` | crear las variables de `tmp/u12-evidence/github-dev-variables.txt` (o ejecutar esas líneas `gh variable set`); son identificadores, no secretos | — |
| 7 | GitHub → Actions → **Deploy dev** → *Run workflow* | construye y sube `inventory/backend`, `inventory/frontend` e `inventory/bootstrap` con la etiqueta = SHA del commit; aún no hay apps que actualizar | — |
| 8 | `… -Stage Apps -ImageTag <sha>` | crea api, frontend y job con esa etiqueta; después ejecuta `Firewall` | escribir `DESPLEGAR` |
| 9 | `… -Stage Bootstrap` | arranca el job y espera: dataset → migrate → ingest → forecast → recommend en una sola ejecución; debe terminar en `Succeeded` y `BOOTSTRAP OK` | — |
| 10 | `… -Stage Verify` | 19 comprobaciones (Azure, aplicación y seguridad: ACR, PostgreSQL `Ready` y TLS, firewall, ingress, identidades y RBAC, Key Vault opción C, contraseñas solo como `secretRef`, última ejecución del job `Succeeded`, frontend 200, API viva tras el proxy) y `tmp/u12-evidence/u12-evidence.json` (solo identificadores) | — |
| 11 | smoke (lo imprime `Verify`) | `$env:SMOKE_FRONTEND_URL='<url>'; $env:SMOKE_API_URL='none'; $env:SMOKE_TIMEOUT='120'; python infra/docker/smoke.py --entra` | — |
| 12 | navegador | abrir la URL del frontend, iniciar sesión, comprobar las vistas con el rol asignado (§6) | — |

`workflow_dispatch` solo aparece cuando `deploy-dev.yml` está en la rama por defecto: integrar antes por PR.

### 5.1 Preflight (`-PreflightOnly`)

```powershell
powershell -ExecutionPolicy Bypass -File infra\azure\deploy-u12.ps1 -PreflightOnly
```

Es el mismo modo que `-Stage Preflight` (y que ejecutar el script sin parámetros). Es **estrictamente de solo
lectura**: cada llamada a `az` pasa antes por una lista de comandos de lectura (`Test-ReadOnlyAz`) y cualquier otra
detiene el script; no escribe nada en Azure ni en disco (ni siquiera evidencias). No se combina con otra etapa
(`-PreflightOnly -Stage Core` termina con código 2 sin llamar a Azure).

| Sección | Qué comprueba |
|---|---|
| 1. Sesión Azure | sesión de usuario de `az login`, tenant del proyecto |
| 2. Suscripción | Azure for Students, `Enabled` |
| 3. Resource Group | `rg-motor-predictivo-dev` en `centralus`; recursos de U10/U12 existentes; ninguno ajeno o futuro |
| 4. Providers | los cinco proveedores registrados (aviso si no) y Container Apps, ACR y PostgreSQL disponibles en `centralus` |
| 5. Key Vault | `publicNetworkAccess = Disabled`, RBAC, borrado temporal; si la opción C ya está aplicada |
| 6. RBAC | tu `Microsoft.KeyVault/vaults/deploy/action` (`ALLOWED` / `MISSING`); `id-mpa-dev-github` (una federación `environment:dev`, solo roles autorizados dentro del grupo, sin `deploy/action`); `id-mpa-dev-runtime` (solo `AcrPull`, si existe); tus roles en el grupo |
| 7. ACR | si existe: Basic, sin administrador, solo `AcrPull`/`AcrPush` |
| 8. PostgreSQL | Flexible Server 16 `Standard_B1ms` ofrecido en `centralus`; si existe: SKU, versión, sin HA, TLS, reglas `aca-out-*` sin `0.0.0.0` |
| 9. Container Apps | si existen: modo `WorkloadProfiles` (aviso si es Express, §5.2), perfil Consumption, api interna solo HTTPS, frontend solo HTTPS, imágenes por identidad, job manual |
| 10. Bicep | `build` y `lint` de U10 y U12, parámetros, valores de `DT-100` (región, Consumption, ACR Basic, PostgreSQL 16 B1ms, Key Vault opción C) |
| 11. Seguridad | detector de secretos y pruebas de configuración de U12 (con Python 3.9+ y `git`; sin Python, aviso), workflow con OIDC y sin secretos |
| 12. Resultado | `PREFLIGHT OK` (código 0) o `PREFLIGHT BLOQUEADO` (código 1) con la lista de bloqueos |

Con `PREFLIGHT OK`, la última línea dice `U12 PREFLIGHT OK — KeyVaultRole no requerido` o
`U12 PREFLIGHT OK — requiere etapa KeyVaultRole`, y la etapa siguiente. Los avisos (`AVISO`) no bloquean.

### 5.2 Entorno en modo Express (incidente del 2026-10-09)

El primer `-Stage Apps` falló con `ExpressEnvironmentResourceNotSupported` (los Container Apps Jobs no existen en
Express) y `ExpressEnvironmentFeatureNotSupported` (`allowInsecure` en `ca-mpa-dev-api`): `cae-mpa-dev` quedó en
modo **Express**. La plantilla no fijaba `environmentMode`; ahora lo fija a `WorkloadProfiles` (API `2026-07-01`)
con el mismo perfil Consumption, y la api ya no usa `allowInsecure` (nginx la llama por HTTPS a su FQDN interno con
el certificado verificado). Microsoft no documenta la conversión de Express a estándar en el mismo recurso, así que
primero se intenta sin borrar nada y, solo si Azure no la acepta, se recrea **únicamente** el entorno.

1. **Diagnóstico (solo lectura):**

   ```powershell
   az containerapp env show -g rg-motor-predictivo-dev -n cae-mpa-dev --query "{modo:properties.environmentMode, dominio:properties.defaultDomain, estado:properties.provisioningState}" -o table
   az containerapp list -g rg-motor-predictivo-dev --query "[].{app:name, entorno:properties.managedEnvironmentId}" -o table
   az containerapp job list -g rg-motor-predictivo-dev --query "[].name" -o table
   powershell -ExecutionPolicy Bypass -File infra\azure\deploy-u12.ps1 -PreflightOnly
   ```

   El preflight avisa `cae-mpa-dev: modo 'Express', sin jobs`.
2. **Intento sin borrar:** `-Stage Core`. El *what-if* debe mostrar `Modify` en `cae-mpa-dev` (modo a
   `WorkloadProfiles`) y nada más que cambie (las asignaciones de rol pueden salir `Modify` por `reference()`). Si el
   despliegue termina y el script dice `Entorno cae-mpa-dev: modo WorkloadProfiles`, saltar al paso 4.
3. **Solo si el paso 2 falla** (error de ARM o `DETENIDO: el entorno … sigue en modo 'Express'`): recrear el entorno.
   - Se borra únicamente lo que vive dentro de `cae-mpa-dev`: las apps o el job que el `Apps` fallido haya dejado
     (sin datos: la base está en PostgreSQL) y el propio entorno.
   - **Se conservan:** ACR y sus imágenes, PostgreSQL y la base `inventory`, Key Vault y sus secretos, las dos
     identidades, sus roles y la federación OIDC. Ninguno depende del entorno.

   ```powershell
   az containerapp delete -g rg-motor-predictivo-dev -n ca-mpa-dev-frontend --yes   # solo si aparece en la lista
   az containerapp delete -g rg-motor-predictivo-dev -n ca-mpa-dev-api --yes        # solo si aparece en la lista
   az containerapp job delete -g rg-motor-predictivo-dev -n caj-mpa-dev-bootstrap --yes  # solo si aparece
   az containerapp env delete -g rg-motor-predictivo-dev -n cae-mpa-dev --yes
   powershell -ExecutionPolicy Bypass -File infra\azure\deploy-u12.ps1 -Stage Core
   ```

   El entorno nuevo tiene **otro dominio**: `Core` sustituye la URL anterior del frontend en
   `infra/azure/entra/u11-entra.dev.json` (no la acumula), y hay que aplicarla con `deploy-u11.ps1`. Las IP de salida
   también son nuevas: las recoge `-Stage Apps` (`Firewall`).
4. Integrar estos cambios en `main` y ejecutar **Deploy dev**: la imagen del frontend debe incluir la nueva
   configuración TLS de nginx. Usar la etiqueta nueva en `-Stage Apps -ImageTag <sha>`; la `267803e…` no la tiene.
5. Seguir con `Bootstrap`, `Verify`, smoke y E2E (§6).

## 6. Pruebas de aceptación

**E2E** (sin guardar tokens). Con `deploy-u11.ps1 -AssignRole VIEWER`: abrir la URL del frontend, iniciar sesión con
Entra ID, abrir `/acceso` y comparar con la matriz (11 permitidos → 200, `history` y `runs` → 403), comprobar que los
datos vienen de la API real (catálogo, detalle), un pronóstico y una recomendación con su explicación. Después
`PLANNER` (13 → 200). Sin sesión → 401; sin rol → 403 en todo salvo `/me`. La API no tiene URL pública:
`SMOKE_API_URL=none` y el frontend hace de proxy.

**Redespliegue.** Cambiar un archivo inocuo, integrar, ejecutar **Deploy dev** con `run_bootstrap=true`:
- api, frontend y job pasan a la nueva etiqueta (`az containerapp show … --query properties.template.containers[0].image`);
- el job termina `Succeeded`: la migración ya aplicada se verifica (no se reaplica), la ingesta del mismo dataset
  (manifiesto fijo, `generated_at=2026-09-29T22:54:38Z`) responde `ALREADY_LOADED` y forecast/recommend
  `ALREADY_COMPUTED`;
- no hay duplicados: el mismo número de recomendaciones, el número de ejecuciones visibles en el frontend no crece y
  la siguiente (`/ejecuciones/<n+1>`) da 404.

**Fallos (todos recuperables, ninguno borra datos):**

| Prueba | Cómo | Esperado | Recuperación |
|---|---|---|---|
| Base detenida | `-Stage Stop` | frontend carga; las vistas con datos reciben un 5xx de la API, sin traza ni secreto | `-Stage Start` |
| Firewall desactualizado | borrar una regla `aca-out-*` en el portal | errores de conexión a la base | `-Stage Firewall` |
| Imagen inexistente | `-Stage Apps -ImageTag noexiste` | la revisión nueva no arranca; la anterior sigue sirviendo | `-Stage Apps -ImageTag <sha bueno>` |
| Token inválido | `curl` a `/api/...` con `Authorization: Bearer x` | 401 | — |
| Job con fallo | ejecutar el job con la base detenida | `Failed`, se detiene en el primer paso, sin pasos siguientes | arrancar la base y repetir |
| Key Vault inaccesible | `Core` o `Apps` sin la etapa 2 (bypass desactivado) | ARM rechaza `getSecret` en la validación y no cambia nada | etapa 2 |

## 7. Costes y control

**Estimación, no cifra garantizada ni contractual.** Precios de lista en USD para `centralus`; confirmar en la
calculadora de Azure y vigilar Cost Management. No se despliega nada adicional de monitorización.

| Recurso | Referencia | Estimación |
|---|---|---|
| ACR Basic | 0,1666 USD/día, 10 GB incluidos (Azure Retail Prices API, 2026-10-07) | ≈ 5 USD/mes |
| PostgreSQL B1ms (cómputo) | por hora mientras está **arrancado**; detenido no cobra cómputo | del orden de 12–16 USD/mes encendido 24×7 (fuente secundaria; **por confirmar**) |
| Almacenamiento PostgreSQL 32 GB | por GB-mes, se cobra también detenido | pocos USD/mes (por confirmar) |
| Container Apps Consumption | concesión gratuita mensual por suscripción: 180 000 vCPU-s, 360 000 GiB-s, 2 M de peticiones; escala a cero | ≈ 0 en uso de demo |
| Key Vault, identidades, Entra ID | operaciones ocasionales | ≈ 0 |

Posibles cargos adicionales: copias de seguridad de PostgreSQL por encima del tamaño aprovisionado; almacenamiento
del ACR por encima de 10 GB (cada redespliegue añade imágenes; borrar etiquetas antiguas si crece); uso de Container
Apps por encima de la concesión (réplicas encendidas mucho tiempo, job repetido); tráfico de salida a Internet.

- **Apagar:** `-Stage Stop` (PostgreSQL). Azure lo **vuelve a arrancar solo a los 7 días**; repetir si sigue sin uso.
  Las apps ya están a cero réplicas sin tráfico.
- **Encender:** `-Stage Start`, esperar a `Ready` y, si la API falla al conectar, `-Stage Firewall`.
- Revisar el consumo en Cost Management del grupo `rg-motor-predictivo-dev` y mantener el presupuesto de U10.

## 8. Desmontaje

Borra solo lo de U12; U10 (Key Vault, identidad de GitHub) y U11 (Entra ID) se quedan. Orden:

```powershell
$rg = 'rg-motor-predictivo-dev'
$o = (az deployment group show -g $rg -n u12-dev --query properties.outputs -o json | ConvertFrom-Json)
az containerapp job delete -g $rg -n $o.bootstrapName.value --yes
az containerapp delete -g $rg -n $o.frontendName.value --yes
az containerapp delete -g $rg -n $o.apiName.value --yes
az containerapp env delete -g $rg -n $o.environmentName.value --yes
az postgres flexible-server delete -g $rg -n $o.postgresName.value --yes   # borra la base de dev (no infra_pgdata)
az acr delete -g $rg -n $o.registryName.value --yes
az role assignment list --all --assignee (az identity show -g $rg -n id-mpa-dev-github --query principalId -o tsv) -o table
#   borrar a mano las asignaciones AcrPush / Container Apps Contributor / Managed Identity Operator (no Reader de U10)
az identity delete -g $rg -n id-mpa-dev-runtime
```

Después: quitar el redirect URI de Azure de `u11-entra.dev.json` y ejecutar `deploy-u11.ps1`; si ya no se usa el
bypass, volver a `keyVaultArmSecretAccess=false` en `infra/azure/parameters/dev.bicepparam` y redesplegar U10. Los
secretos del vault quedan en borrado temporal según la retención de U10.

## 9. Riesgos aceptados (MVP `dev`) frente a lo que exigiría producción

| Aceptado en `dev` | En producción |
|---|---|
| PostgreSQL con acceso público limitado a las IP de salida (cambiantes, posiblemente compartidas) | VNet + endpoint privado o integración de VNet; sin acceso público |
| Key Vault con bypass de ARM para plantillas | referencias de Key Vault en tiempo de ejecución por red privada y rotación automática |
| Sin Log Analytics: registros solo por streaming | Log Analytics/App Insights con retención y alertas |
| 0–1 réplicas, arranque en frío de varios segundos | réplicas mínimas ≥ 1 y escalado por carga |
| B1ms sin HA ni copias georredundantes | General Purpose con HA de zona y copias georredundantes |
| ACR Basic sin escaneo de vulnerabilidades ni geo-replicación | Premium o escaneo de Defender, retención y firma de imágenes |
| Despliegue manual (`workflow_dispatch`) sin aprobación | entornos `staging`/`prod` con aprobación y credencial federada propia |
| Rotación de contraseñas manual | rotación programada |
| TLS entre frontend y api con el certificado del entorno (sin `allowInsecure`), pero sin red privada | red privada y, si se exige, mTLS del entorno |

## 10. Problemas frecuentes

- **El preflight falla por un rol por nombre:** `Container Apps Contributor` o `Managed Identity Operator` no existe
  con ese nombre en el tenant; detenerse y revisar.
- **El job termina `Failed` en `migrate`:** firewall (`-Stage Firewall`) o base detenida (`-Stage Start`).
- **El job da `INTEGRITY_CONFLICT` en la ingesta:** el dataset no es el fijado; no borrar datos, revisar la etiqueta.
- **Login de MSAL con `redirect_uri` no válido:** falta el paso 5.
- **`az containerapp job logs show` sin registros:** no hay Log Analytics; los registros solo se ven mientras la
  ejecución está viva. El resultado queda en el estado de la ejecución (`-Stage Bootstrap` lo muestra).
