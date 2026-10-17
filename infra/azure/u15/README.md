# U15 — Azure AI Search (`DT-094`)

U15 usa un servicio Azure AI Search **Gratis** (Free) en `centralus`, la cuenta de Azure OpenAI de U13 para los
embeddings y solo el corpus sintético de [`knowledge/search_corpus/`](../../../knowledge/search_corpus/).
`id-mpa-dev-runtime` recibe únicamente `Search Index Data Reader` en el ámbito del servicio. El índice
([`index.json`](index.json)) y la carga los ejecuta el responsable con su propia sesión de Entra ID.

## Estado (2026-10-17, verificado con la identidad del responsable)

| Pieza | Estado | Evidencia |
|---|---|---|
| Servicio `motor-predictivo-search-dev` | Creado por el responsable en el portal el 2026-10-16: Free (50 MB), Central US, `running`, Entra ID **y** claves de API (`aadOrApiKey`, `disableLocalAuth: false`), acceso público | `az search service show` [AZ-U] |
| Embeddings `text-embedding-3-small` | Desplegado el 2026-10-17 en `oai-mpa-dev-a73qz3afqj7no` (versión 1, GlobalStandard, capacidad 10 = 10 000 tokens/min, 10 solicitudes cada 10 s); responde con vectores de 1536 dimensiones | `az cognitiveservices account deployment create` y llamada de prueba [AZ-U] |
| Roles de datos del responsable | `Search Service Contributor` y `Search Index Data Contributor` sobre el servicio; `Cognitive Services OpenAI User` sobre la cuenta de U13 | `az role assignment create` [AZ-U] |
| Entra ID en el nivel Free | El servicio aceptó el token de Entra ID del responsable sin clave (`GET /indexes` → lista vacía) | Prueba C [AZ-U] |
| Índice `u15-demo-documents` | Creado el 2026-10-17 con `-Stage Index` (`INDEX OK`) | [AZ-U] |
| Corpus | 9 fragmentos sintéticos cargados el 2026-10-17 con `-Stage Load` (el primer intento falló con HTTP 400 por las claves con `:`, corregido) | [AZ-U] |
| Rol de `id-mpa-dev-runtime` | Asignado: `Verify` confirma exactamente 1 `Search Index Data Reader` sobre el servicio (2026-10-17) | [AZ-U] |
| Comprobación con tu identidad | `-Stage Verify` en verde el 2026-10-17: 9 documentos, las 6 consultas con resultados (aciertos 6/6, informativo) y filtro de grupos aplicado por Search; `deploy-u12.ps1 -Stage Verify` 20/20 | [AZ-U] |
| Consulta desde la API | **Pendiente**: la API sigue con el recuperador local; `azure_search.py` no está conectado a ningún endpoint | — |

La validación del nivel Free con Entra ID se hizo con la identidad del responsable. La identidad administrada de la API
solo quedará probada cuando la API consulte Search.

## Coste

- **Free:** sin cargo. Tiene 50 MB, comparte infraestructura y Microsoft puede eliminarlo por inactividad. Si desaparece,
  se crea de nuevo en el portal con el mismo nombre y se repiten `Index`, `Load` y `Roles`.
- **Embeddings:** las implementaciones estándar de Azure OpenAI se cobran por token; no tienen cargo por hora. El corpus
  sintético son 9 fragmentos con menos de 2 000 caracteres en total: una carga completa son 9 llamadas y pocos
  cientos de tokens.
- **Basic** queda documentado como alternativa (cargo continuo; referencia de Microsoft de ~USD 67 por 30 días, por encima
  del umbral de planificación de USD 50 de `DT-094`). **No está autorizado.**

## Procedimiento (`deploy-u15.ps1`)

Desde la raíz del repositorio, con Azure CLI autenticado y Python 3.10 o superior:

```powershell
powershell -ExecutionPolicy Bypass -File infra\azure\deploy-u15.ps1 -PreflightOnly   # solo lectura
powershell -ExecutionPolicy Bypass -File infra\azure\deploy-u15.ps1 -Stage WhatIf    # solo lectura: deriva de la plantilla
powershell -ExecutionPolicy Bypass -File infra\azure\deploy-u15.ps1 -Stage Index     # crea el indice (INDICE)
powershell -ExecutionPolicy Bypass -File infra\azure\deploy-u15.ps1 -Stage Load      # vectoriza y carga el corpus (CARGAR)
powershell -ExecutionPolicy Bypass -File infra\azure\deploy-u15.ps1 -Stage Roles     # lector para id-mpa-dev-runtime (ROL)
powershell -ExecutionPolicy Bypass -File infra\azure\deploy-u12.ps1 -Stage Verify    # U12 debe seguir en verde
powershell -ExecutionPolicy Bypass -File infra\azure\deploy-u15.ps1 -Stage Verify    # comprobaciones y evidencia
```

| Etapa | Qué hace | Cambia Azure |
|---|---|---|
| `Preflight` | Sesión y grupo; servicio Free, `running` y con Entra ID; embeddings; tus roles de datos; roles de la identidad de ejecución; estado del índice (solo `GET`) | No (lista de comandos permitidos) |
| `WhatIf` | `validate` y `what-if` de [`main.bicep`](main.bicep) contra el servicio real; muestra la deriva | No |
| `Index` | Crea o actualiza `u15-demo-documents` desde `index.json` | Sí: el índice |
| `Load` | Trocea el corpus, pide un embedding por fragmento (pausa de 1,2 s y reintentos ante HTTP 429) y lo sube; la clave de cada documento es el identificador del fragmento en Base64 URL-safe con prefijo `k`, porque Search solo admite letras, dígitos, `-`, `_` y `=` en las claves | Sí: documentos sintéticos |
| `Roles` | Asigna `Search Index Data Reader` a `id-mpa-dev-runtime` solo sobre el servicio; si ya existe, no hace nada | Sí: un rol |
| `Verify` | Servicio, embeddings, rol de ejecución (exactamente uno, nada más sobre Search) y, con **tu** identidad: número de documentos, consultas de [`evaluation.json`](../../../knowledge/search_corpus/evaluation.json) y filtro de grupos; escribe `tmp/u15-evidence/` | No |

`-Stage Roles` necesita el `deploy-u12.ps1` de este mismo cambio: su comprobación de roles de la identidad de ejecución
acepta ahora `Search Index Data Reader` solo sobre un servicio de Search del grupo. Con la versión anterior,
`deploy-u12.ps1 -Stage Verify` fallaría con «rol no permitido».

Si una llamada falla, `search_setup.py` muestra el mensaje de error del servicio (sin cabeceras ni tokens) además del
código HTTP.

Los tokens de Entra ID los pide [`search_setup.py`](search_setup.py) a Azure CLI
(`az account get-access-token`): quedan en memoria y nunca se imprimen ni se escriben. El script no lee claves de API.

### Roles

Si `Preflight` informa de que faltan roles de datos (los del 2026-10-17 ya existen):

```powershell
$rg = "rg-motor-predictivo-dev"
$searchId = az search service show -n motor-predictivo-search-dev -g $rg --query id -o tsv
$oaiId = az cognitiveservices account show -n oai-mpa-dev-a73qz3afqj7no -g $rg --query id -o tsv
$me = az ad signed-in-user show --query id -o tsv
az role assignment create --assignee-object-id $me --assignee-principal-type User --role "Search Service Contributor" --scope $searchId
az role assignment create --assignee-object-id $me --assignee-principal-type User --role "Search Index Data Contributor" --scope $searchId
az role assignment create --assignee-object-id $me --assignee-principal-type User --role "Cognitive Services OpenAI User" --scope $oaiId
```

Owner no basta: no incluye acciones de datos. Las asignaciones tardan unos minutos en aplicarse.

## Plantilla

[`main.bicep`](main.bicep) describe el servicio real (`serviceName`, `searchSku = 'free'`, `disableLocalAuth = false`,
`semanticSearch = 'free'`) y el rol de lectura. **No se usa para desplegar**: el servicio se creó en el portal y el rol lo
asigna `-Stage Roles`. `-Stage WhatIf` muestra la diferencia; se espera al menos el alta de etiquetas, que el servicio
real no tiene.

`authOptions` no puede definirse cuando `disableLocalAuth` es `true` (referencia de `Microsoft.Search/searchServices`).
La plantilla anterior combinaba ambos y habría fallado al desplegarse; ahora `authOptions` solo se envía con las claves
activas.

## Pendiente

1. Conectar la API: variables de entorno en Container Apps, `AzureSearchRetriever` con la identidad administrada cuando
   esté configurado y el recuperador local en caso contrario. Decidir si los fragmentos se pasan a `gpt-41-mini` (RAG).
2. Desactivar las claves de API del servicio (`disableLocalAuth = true`) cuando la API funcione con Entra ID.

## Límites

- Índice de demostración: sin documentos reales ni grupos reales de Entra ID (`ASSUMPTION-008`).
- `security_groups` y vigencia se aplican como filtros explícitos en cada consulta; el rol de Search no los sustituye.
- La tasa de aciertos de `Verify` es informativa: `evaluation.json` no fija un umbral de negocio.
