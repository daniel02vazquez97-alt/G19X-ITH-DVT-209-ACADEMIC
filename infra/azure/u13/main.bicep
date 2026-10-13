// U13 (DT-101): Azure OpenAI para las explicaciones de la API (CU-1), en el grupo de U10.
//
// - Una cuenta Microsoft.CognitiveServices/accounts de tipo OpenAI, S0, sin claves (disableLocalAuth): solo
//   Microsoft Entra ID. Acceso de red publico, porque Container Apps (U12) no tiene VNet; la autenticacion es la
//   barrera.
// - Un unico despliegue del modelo elegido por el responsable (gpt-4.1-mini 2025-04-14, Global Standard), con la
//   capacidad minima y sin actualizacion automatica de version.
// - La identidad de ejecucion de U12 (id-mpa-dev-runtime) recibe "Cognitive Services OpenAI User" SOBRE LA CUENTA,
//   no sobre el grupo.
// Sin secretos en este archivo ni en los parametros. Lo despliega el responsable con infra/azure/deploy-u13.ps1.

targetScope = 'resourceGroup'

@allowed([
  'dev'
])
param environment string = 'dev'

@description('Region: la del grupo de U10 (centralus).')
param location string = resourceGroup().location

param projectName string = 'mpa'
param ownerTag string = 'responsable-del-proyecto'

@description('Identidad de ejecucion de U12 que llama al modelo.')
param runtimeIdentityName string = 'id-${projectName}-${environment}-runtime'

@description('Modelo y version (Puerta 0 de DT-101).')
param modelName string = 'gpt-4.1-mini'
param modelVersion string = '2025-04-14'

@description('Nombre del despliegue: es el campo "model" de las llamadas.')
param deploymentName string = 'gpt-41-mini'

@allowed([
  'GlobalStandard'
  'DataZoneStandard'
])
param deploymentSku string = 'GlobalStandard'

@description('Capacidad en unidades de 1 000 tokens por minuto. La cuota de gpt4.1-mini en GlobalStandard es 200.')
@minValue(1)
@maxValue(50)
param capacity int = 10

var tags = {
  project: 'motor-predictivo-abastecimiento'
  environment: environment
  owner: ownerTag
  purpose: 'u13-azure-openai'
  managedBy: 'bicep'
  costControl: 'azure-for-students-planning-50usd'
}
var suffix = uniqueString(resourceGroup().id)
var accountName = 'oai-${projectName}-${environment}-${suffix}'
// Cognitive Services OpenAI User: inferencia, sin gestion de la cuenta ni lectura de claves.
var openAIUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'

resource runtimeIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = {
  name: runtimeIdentityName
}

resource account 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: accountName
  location: location
  tags: tags
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: accountName
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
    }
  }
}

resource deployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: account
  name: deploymentName
  sku: {
    name: deploymentSku
    capacity: capacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: modelName
      version: modelVersion
    }
    versionUpgradeOption: 'NoAutoUpgrade'
  }
}

resource runtimeOpenAIUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(account.id, runtimeIdentity.id, openAIUserRoleId)
  scope: account
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', openAIUserRoleId)
    principalId: runtimeIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

output accountName string = account.name
output accountId string = account.id
output endpoint string = 'https://${accountName}.openai.azure.com'
output deploymentName string = deployment.name
output runtimeClientId string = runtimeIdentity.properties.clientId
