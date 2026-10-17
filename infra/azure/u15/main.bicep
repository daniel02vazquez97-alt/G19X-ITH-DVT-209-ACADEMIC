// U15 (DT-094): Azure AI Search. Describe el servicio Free que el responsable creo en el portal el 2026-10-16
// (motor-predictivo-search-dev, centralus) y el rol de lectura de la identidad de U12. No se despliega con esta
// plantilla: deploy-u15.ps1 -Stage WhatIf la compara con el servicio real (deriva) y -Stage Roles asigna el rol con az.
// El indice y los documentos los crea el responsable con search_setup.py (roles de datos propios), no la plantilla.

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

@description('Nombre del servicio de Search existente (creado en el portal).')
param serviceName string = 'motor-predictivo-search-dev'

@description('Nivel del servicio: free no tiene cargo continuo (50 MB, infraestructura compartida). Basic queda como opcion documentada, no autorizada.')
@allowed([
  'free'
  'basic'
])
param searchSku string = 'free'

@description('true: solo Entra ID (sin claves de API). false: Entra ID y claves, el estado actual del servicio hasta verificar la API con Entra ID.')
param disableLocalAuth bool = false

@description('Plan de busqueda semantica; el servicio real tiene free. U15 no la usa.')
@allowed([
  'disabled'
  'free'
])
param semanticSearch string = 'free'

var tags = {
  project: 'motor-predictivo-abastecimiento'
  environment: environment
  owner: ownerTag
  purpose: 'u15-azure-ai-search'
  managedBy: 'portal-y-bicep'
  costControl: 'azure-for-students-planning-50usd'
}
var searchIndexDataReaderRoleId = '1407120a-92aa-4202-b7e9-c0e197c71c8f'

resource runtimeIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = {
  name: runtimeIdentityName
}

// authOptions no puede definirse cuando disableLocalAuth es true (referencia de Microsoft.Search/searchServices):
// con claves desactivadas se omite; con claves activas, aadOrApiKey acepta tambien tokens de Entra ID.
resource searchService 'Microsoft.Search/searchServices@2025-05-01' = {
  name: serviceName
  location: location
  tags: tags
  sku: {
    name: searchSku
  }
  properties: {
    authOptions: disableLocalAuth ? null : {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
    disableLocalAuth: disableLocalAuth
    hostingMode: 'Default'
    partitionCount: 1
    replicaCount: 1
    publicNetworkAccess: 'Enabled'
    semanticSearch: semanticSearch
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
