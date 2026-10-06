# Base de Azure del entorno `dev` (U10, `DT-098`)

Infraestructura mínima en Bicep sobre la que se construirán U11–U16. **El sistema sigue funcionando entero en
local sin nada de esto** (RNF-006). El agente prepara y valida; **el despliegue lo ejecuta el responsable** con
su propia sesión de Azure CLI. Nadie copia credenciales en archivos, en Git ni en el chat.

## Qué crea

| Recurso | Nombre | Propósito | Costo esperado |
|---|---|---|---|
| Grupo de recursos | `rg-mpa-dev` | Agrupa todo lo del entorno `dev` | Sin costo |
| Key Vault (Standard) | `kv-mpa-dev-<13 caracteres de uniqueString>` | Almacén de secretos de `DT-022`, vacío; RBAC; sin acceso de red público | Sin cargo fijo; se cobra por operación (sin consumidores en U10: ~0) |
| Identidad administrada | `id-mpa-dev-github` | Identidad de GitHub Actions para U12 | Sin costo |
| Credencial federada | `github-dev` | OIDC: solo el entorno `dev` del repositorio | Sin costo |
| Asignación de rol | Reader sobre `rg-mpa-dev` | Comprobar el inicio de sesión; nada más | Sin costo |
| Presupuesto (opcional) | `budget-mpa-dev` | Avisos a 50/75/90/100 % de 50 USD | Sin costo; **Azure for Students no está entre las ofertas que admite Cost Management** |

No crea PostgreSQL, registro de contenedores, cómputo, Azure ML, Azure OpenAI, AI Search, Power BI,
Application Insights ni Log Analytics. Etiquetas en todos los recursos: `project`, `environment`, `owner` (un
rol, no una persona), `purpose`, `managedBy` y `costControl`.

## Archivos

- `main.bicep`: ámbito de suscripción; grupo de recursos, módulo base y presupuesto opcional.
- `modules/base.bicep`: Key Vault, identidad, credencial federada y rol.
- `modules/budget.bicep`: presupuesto (solo con `deployBudget=true`).
- `parameters/dev.bicepparam`: parámetros de `dev`, sin secretos ni datos personales.

## Despliegue (en la máquina del responsable)

Requisitos: Azure CLI con Bicep (`az bicep version`; si falta, `az bicep install`). Todos los comandos, desde la
raíz del repositorio, en PowerShell o bash.

1. **Sesión y suscripción.**

   ```
   az login
   az account list --output table
   az account set --subscription "<nombre o id de la suscripción Azure for Students>"
   az account show --query "{suscripcion:name, estado:state}" --output table
   ```

2. **Regiones permitidas.** Azure for Students limita cada suscripción a unas cinco regiones, distintas en cada
   cuenta, con la asignación de directiva «Allowed resource deployment regions»:

   ```
   az policy assignment list --query "[?displayName=='Allowed resource deployment regions'].parameters" --output json
   ```

   Si `westus3` no aparece, cambia `location` en `parameters/dev.bicepparam` por la primera permitida de esta
   lista, en este orden (`DT-098`): `westus3`, `southcentralus`, `eastus`, `northcentralus`, `westus`. Si
   ninguna está permitida, detente y anota la lista: la región se decide de nuevo.

3. **Proveedores de recursos** (una vez por suscripción):

   ```
   az provider register --namespace Microsoft.KeyVault --wait
   az provider register --namespace Microsoft.ManagedIdentity --wait
   ```

4. **Validación y what-if.** Sustituye `<region>` por la de `parameters/dev.bicepparam`.

   ```
   az bicep build --file infra/azure/main.bicep --stdout > NUL    # en bash: > /dev/null
   az deployment sub validate --name u10-base-dev --location <region> --template-file infra/azure/main.bicep --parameters infra/azure/parameters/dev.bicepparam
   az deployment sub what-if --name u10-base-dev --location <region> --template-file infra/azure/main.bicep --parameters infra/azure/parameters/dev.bicepparam
   ```

   **Resultado esperado del what-if: exactamente cinco creaciones y ningún cambio ni borrado.**
   - `rg-mpa-dev`;
   - `kv-mpa-dev-…`;
   - `id-mpa-dev-github`;
   - `id-mpa-dev-github/github-dev`;
   - una asignación de rol Reader con ámbito `rg-mpa-dev`.

   Todas deben estar en la región elegida. No despliegues si aparece cualquier otro recurso, cualquier cambio o
   borrado, otra región o un rol distinto de Reader.

5. **Despliegue**, solo después de revisar el what-if:

   ```
   az deployment sub create --name u10-base-dev --location <region> --template-file infra/azure/main.bicep --parameters infra/azure/parameters/dev.bicepparam
   ```

## Verificación posterior

```
az resource list --resource-group rg-mpa-dev --query "[].{nombre:name, tipo:type, region:location, etiquetas:tags}" --output json
az keyvault show --name <kv> --query "{rbac:properties.enableRbacAuthorization, red:properties.publicNetworkAccess, retencion:properties.softDeleteRetentionInDays, purga:properties.enablePurgeProtection}" --output table
az identity federated-credential list --identity-name id-mpa-dev-github --resource-group rg-mpa-dev --query "[].{nombre:name, emisor:issuer, sujeto:subject, audiencia:audiences[0]}" --output table
az role assignment list --all --assignee <principalId de id-mpa-dev-github> --query "[].{rol:roleDefinitionName, ambito:scope}" --output table
az deployment sub show --name u10-base-dev --query properties.outputs --output json
```

Esperado:

- dos recursos en `rg-mpa-dev` (Key Vault e identidad), con las seis etiquetas;
- Key Vault con RBAC `true`, red `Disabled`, retención 7 y sin protección de purga;
- una sola credencial federada, con sujeto `repo:daniel02vazquez97-alt/Motor-Predictivo-de-Abastecimiento-de-Inventarios:environment:dev`;
- una sola asignación de rol: `Reader` sobre `rg-mpa-dev`.

Las salidas `githubIdentityClientId`, `tenantId` y `subscriptionId` son identificadores, no credenciales. U12
decidirá si se guardan como variables o como secretos de GitHub; Microsoft recomienda secretos.

## Control de gasto

- **El presupuesto no se puede automatizar en esta suscripción:** Azure for Students (MS-AZR-0170P) figura entre
  las ofertas que Cost Management **no admite**. Por eso `deployBudget` es `false`. Para comprobar el rechazo:

  ```
  az deployment sub what-if --name u10-budget-dev --location <region> --template-file infra/azure/main.bicep --parameters infra/azure/parameters/dev.bicepparam --parameters deployBudget=true budgetStartDate=AAAA-MM-01 budgetContactEmails="['<correo>']"
  ```

  No se pone ningún correo en el repositorio.
- **Control manual:** el saldo y el consumo por servicio se ven en el portal de Microsoft Azure Sponsorships,
  páginas *Balance* y *Usage*. Hay que revisarlo cada semana mientras haya recursos con consumo, y antes y
  después de cada unidad que cree recursos.
- **Qué pasa a los 50 USD:** nada automático. Es el umbral de planificación; al acercarse, se para y se decide.
- **Qué pasa a los 100 USD** (crédito agotado) **o a los 12 meses:** Azure deshabilita la suscripción y sus
  servicios, salvo que se pase a pago por uso. Las máquinas se detienen y el almacenamiento queda en solo lectura.
- **Costo continuo de U10:** ninguno. El Key Vault solo cobra operaciones, y sin consumidores no las hay.
- **Qué apagar cuando no se use:** nada en U10. Las unidades con cómputo (U12–U15) deben documentar su apagado.

## Desmontaje

Borra solo el grupo de recursos de U10; nada fuera de él.

```
az group delete --name rg-mpa-dev --yes
az keyvault list-deleted --query "[?name=='<kv>'].{nombre:name, purga:properties.scheduledPurgeDate}" --output table
az keyvault purge --name <kv> --location <region>
```

Borrar el grupo elimina el Key Vault, la identidad, su credencial federada y la asignación de rol del grupo. El
Key Vault queda en borrado temporal 7 días; como no tiene protección de purga, se purga con el tercer comando y
su nombre queda libre.

Si llegó a crearse el presupuesto:

```
az consumption budget delete --budget-name budget-mpa-dev
```

Verificación: `az group exists --name rg-mpa-dev` debe devolver `false` y `az keyvault list-deleted` no debe
listar el vault. El historial de despliegues de la suscripción (`az deployment sub delete --name u10-base-dev`)
es solo metadato y no tiene costo.
