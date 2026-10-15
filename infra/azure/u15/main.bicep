// U15 (DT-094): Azure AI Search Basic, preparado pero sin desplegar.
// La identidad de U12 solo recibe lectura de documentos; el aprovisionamiento del índice usa el responsable.

targetScope = 'resourceGroup'

@allowed([
  'dev'
])
param environment string = 'dev'

@description('Region de Azure AI Search (la del grupo de U10: centralus).')
param location string = resourceGroup().location

param projectName string = 'mpa'
param ownerTag string = 'responsable-del-proyecto'
@description('Identidad de ejecucion de U12 que consulta el indice.')
param runtimeIdentityName string = 'id-${projectName}-${environment}-runtime'

var tags = {
  project: 'motor-predictivo-abastecimiento'
  environment: environment
  owner: ownerTag
  purpose: 'u15-azure-ai-search'
  managedBy: 'bicep'
  costControl: 'azure-for-students-planning-50usd'
}
var suffix = uniqueString(resourceGroup().id)
var serviceName = take('srch-${projectName}-${environment}-${suffix}', 60)
var searchIndexDataReaderRoleId = '1407120a-92aa-4202-b7e9-c0e197c71c8f'

resource runtimeIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = {
  name: runtimeIdentityName
}

resource searchService 'Microsoft.Search/searchServices@2025-05-01' = {
  name: serviceName
  location: location
  tags: tags
  sku: {
    name: 'basic'
  }
  properties: {
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
    disableLocalAuth: true
    hostingMode: 'default'
    partitionCount: 1
    replicaCount: 1
    publicNetworkAccess: 'Enabled'
    semanticSearch: 'disabled'
  }
}

resource runtimeSearchReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(searchService.id, runtimeIdentity.id, searchIndexDataReaderRoleId)
  scope: searchService
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchIndexDataReaderRoleId)
    principalId: runtimeIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

output searchServiceName string = searchService.name
output searchServiceId string = searchService.id
output endpoint string = 'https://${serviceName}.search.windows.net'
output runtimeClientId string = runtimeIdentity.properties.clientId
