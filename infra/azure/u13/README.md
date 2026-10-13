# U13 — Azure OpenAI para las explicaciones (`DT-101`)

La API explica cada recomendación (endpoint 14, `DT-068`) con un modelo de Azure OpenAI, y conserva la plantilla de
U6 como respaldo. Las cifras se verifican igual que en U6 (`DT-069`), y además se rechazan los números escritos con
letras. Si el modelo no responde, tarda demasiado, supera el límite de llamadas o escribe una cifra no autorizada, la
respuesta usa la plantilla `template/1.0.0`: sigue siendo HTTP 200 y nunca devuelve el texto rechazado.

## 1. Qué se crea

| Recurso | Configuración | Coste |
|---|---|---|
| `oai-mpa-dev-<sufijo>` (`Microsoft.CognitiveServices/accounts`, tipo `OpenAI`, S0) | `centralus`; **sin claves** (`disableLocalAuth`), solo Entra ID; red pública, porque U12 no tiene VNet | Sin cargo fijo |
| Despliegue `gpt-41-mini` | `gpt-4.1-mini` `2025-04-14`, *Global Standard*, capacidad 10 (10 000 *tokens* por minuto), sin actualización automática de versión | Pago por *tokens* |
| Asignación de rol | *Cognitive Services OpenAI User* a `id-mpa-dev-runtime`, **sobre la cuenta** | Sin coste |

**Coste estimado:** las 100 recomendaciones del dataset suponen unas 100 llamadas de pocos miles de *tokens*. Con la
caché de prompts idénticos, cada explicación se paga una vez por réplica: el gasto esperado es de céntimos. Compruébalo
en el portal de Microsoft Azure Sponsorships antes y después.

**Datos que salen al modelo:** solo las cifras ya calculadas de la recomendación, con su `display`, y el texto de la
plantilla, todo `SYNTHETIC`. *Global Standard* puede procesar la petición en cualquier región; con datos sintéticos
se aceptó así (`DT-P08`, `DT-101`).

**Retirada del modelo:** `gpt-4.1-mini` `2025-04-14` está en estado `Legacy`, con retirada de inferencia el
2027-04-14. `gpt-5.4-mini`, sin retirada próxima, tiene cuota 0 en la suscripción. Cuando el modelo se retire, la API
sigue explicando con la plantilla. Cambiar de modelo es un cambio de parámetros (`dev.bicepparam`, el script y
`genaiDeployment`), no de código, salvo que el nuevo sea de razonamiento (sin `temperature`).

## 2. Procedimiento

Desde la raíz del repositorio, con tu sesión de Azure CLI:

| # | Comando | Qué hace | Confirmación |
|---|---|---|---|
| 1 | `powershell -ExecutionPolicy Bypass -File infra\azure\deploy-u13.ps1 -PreflightOnly` | Solo lectura: sesión, grupo, identidad de ejecución, proveedor `Registered`, modelo en el catálogo con *Global Standard* y fecha de retirada, cuota libre | — |
| 2 | `… -Stage Deploy` | `validate` → `what-if` comprobado automáticamente (una cuenta OpenAI sin claves, un despliegue, un rol sobre la cuenta; nada más ni ningún `Delete`) → creación | `OPENAI` |
| 3 | `… -Stage Verify` | Cuenta, despliegue y rol; `tmp/u12-evidence/u13-evidence.json` (solo identificadores) | — |
| 4 | `infra/azure/u12/dev.bicepparam`: `param genaiEnabled = true`; commit y PR | La api recibe `GENAI_PROVIDER`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT` y `AZURE_CLIENT_ID` (identificadores, no secretos) | — |
| 5 | GitHub → Actions → **Deploy dev** | Publica la imagen de la API con el código de U13 | — |
| 6 | `deploy-u12.ps1 -Stage Apps -ImageTag <sha>` y `-Stage Verify` | Aplica las variables de la api. El `what-if` de U12 sigue rechazando cualquier recurso OpenAI: U12 solo cablea | `DESPLEGAR` |
| 7 | Navegador, con sesión: una recomendación → explicación | `explanation.generator` = `azure-openai/gpt-41-mini` y `status` = `VERIFIED`. Si dice `template/1.0.0`, se usó el respaldo: mira el registro de la api (`explanation fallback to the template`, con la causa) | — |

## 3. Desmontaje

1. `param genaiEnabled = false` en `infra/azure/u12/dev.bicepparam` y `deploy-u12.ps1 -Stage Apps`: la api vuelve a la plantilla.
2. `deploy-u13.ps1 -Stage Remove`, confirmando con `BORRAR`: borra el rol, el despliegue y la cuenta, y purga la cuenta.

## 4. Pruebas sin Azure

- `backend/tests/genai/test_chat.py`: mensajes, normalización, respaldo y que el texto rechazado no se registra.
- `backend/tests/api/test_azure_openai.py`: token de la identidad, llamada v1, caché, límite por minuto, errores,
  configuración y cableado. Sin red.
- `infra/tests/test_u13_config.py`: Bicep, parámetros, cableado de U12 y `deploy-u13.ps1 -SelfTest`.
