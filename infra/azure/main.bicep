// U10 (DT-098): base mínima de Azure del entorno `dev`, a nivel de suscripción.
//
// Crea el grupo de recursos del entorno y, dentro de él (modules/base.bicep), el Key Vault de DT-022 y la
// identidad administrada con la credencial federada OIDC para GitHub Actions. El presupuesto de Cost
// Management queda tras `deployBudget` (por defecto false): la oferta Azure for Students no está entre las
// que admite Cost Management (ver infra/azure/README.md). Ningún secreto entra por parámetros.

targetScope = 'subscription'

@description('Entorno. U10 solo autoriza dev (DT-094).')
@allowed([
  'dev'
])
param environment string = 'dev'

@description('Región de todos los recursos. Debe estar entre las permitidas por la política "Allowed resource deployment regions" de la suscripción.')
param location string

@description('Prefijo corto del proyecto para los nombres (minúsculas y dígitos).')
@minLength(2)
@maxLength(8)
param projectName string = 'mpa'

@description('Nombre del grupo de recursos del entorno.')
param resourceGroupName string = 'rg-motor-predictivo-${environment}'

@description('Valor de la etiqueta owner: un rol, nunca un nombre ni un correo personal.')
param ownerTag string = 'responsable-del-proyecto'

@description('Propietario (usuario u organización) del repositorio de GitHub.')
param githubOwner string

@description('Id numérico e inmutable del propietario en GitHub (formato de sujeto OIDC con ids, DT-098).')
@minLength(1)
@maxLength(20)
param githubOwnerId string

@description('Nombre del repositorio de GitHub.')
param githubRepository string

@description('Id numérico e inmutable del repositorio en GitHub (formato de sujeto OIDC con ids, DT-098).')
@minLength(1)
@maxLength(20)
param githubRepositoryId string

@description('Entorno de GitHub Actions al que se limita la credencial federada.')
@allowed([
  'dev'
])
param githubEnvironment string = 'dev'

@description('Crear el presupuesto de Cost Management. false mientras la oferta no lo admita.')
param deployBudget bool = false

@description('Importe del presupuesto en la moneda de facturación (planificación: 50 USD).')
@minValue(1)
param budgetAmount int = 50

@description('Primer día del mes de inicio del presupuesto, AAAA-MM-01. Solo se usa con deployBudget.')
param budgetStartDate string = ''

@description('Correos de aviso del presupuesto. Se pasan al desplegar; nunca se versionan.')
param budgetContactEmails array = []

@description('Umbrales de aviso, en porcentaje del importe (máximo cinco avisos por presupuesto).')
param budgetThresholds array = [
  50
  75
  90
  100
]

var tags = {
  project: 'motor-predictivo-abastecimiento'
  environment: environment
  owner: ownerTag
  purpose: 'u10-base'
  managedBy: 'bicep'
  costControl: 'azure-for-students-planning-50usd'
}

resource resourceGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

@description('U12 (DT-100): el despliegue de plantillas de ARM puede leer los secretos de PostgreSQL del Key Vault (getSecret); la red pública sigue deshabilitada.')
param keyVaultArmSecretAccess bool = false

module base 'modules/base.bicep' = {
  name: 'u10-base'
  scope: resourceGroup
  params: {
    location: location
    projectName: projectName
    environment: environment
    tags: tags
    githubOwner: githubOwner
    githubOwnerId: githubOwnerId
    githubRepository: githubRepository
    githubRepositoryId: githubRepositoryId
    githubEnvironment: githubEnvironment
    armSecretAccess: keyVaultArmSecretAccess
  }
}

module budget 'modules/budget.bicep' = if (deployBudget) {
  name: 'u10-budget'
  params: {
    name: 'budget-${projectName}-${environment}'
    amount: budgetAmount
    startDate: budgetStartDate
    contactEmails: budgetContactEmails
    thresholds: budgetThresholds
  }
}

output resourceGroupName string = resourceGroup.name
output resourceGroupId string = resourceGroup.id
output keyVaultName string = base.outputs.keyVaultName
output keyVaultId string = base.outputs.keyVaultId
output githubIdentityName string = base.outputs.identityName
output githubIdentityId string = base.outputs.identityId
// Identificadores, no credenciales: los usa azure/login en U12 junto con el tenant y la suscripción.
output githubIdentityClientId string = base.outputs.identityClientId
output tenantId string = subscription().tenantId
output subscriptionId string = subscription().subscriptionId
