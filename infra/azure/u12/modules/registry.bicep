// U12 (DT-100): Azure Container Registry Basic, sin usuario administrador (el pull anónimo no existe en Basic).
// GitHub Actions publica con AcrPush (OIDC); las apps descargan con AcrPull (identidad administrada).

param name string
param location string
param tags object
param runtimePrincipalId string
param githubPrincipalId string

// Ids de recurso de las identidades: solo para el NOMBRE de las asignaciones. El principalId se conoce en tiempo de
// ejecución y, usado en guid(), deja el what-if sin poder calcular el id («Unsupported»).
param runtimeIdentityId string
param githubIdentityId string

// Roles integrados (Microsoft Learn, «Azure built-in roles for Containers», 2026-10-07).
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'
var acrPushRoleId = '8311e382-0749-4cb8-b61a-304f252e45ec'

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Enabled'
    zoneRedundancy: 'Disabled'
  }
}

resource runtimePull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, runtimeIdentityId, acrPullRoleId)
  scope: registry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalId: runtimePrincipalId
    principalType: 'ServicePrincipal'
    description: 'U12: Container Apps descarga las imagenes de dev (DT-100).'
  }
}

resource githubPush 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, githubIdentityId, acrPushRoleId)
  scope: registry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPushRoleId)
    principalId: githubPrincipalId
    principalType: 'ServicePrincipal'
    description: 'U12: GitHub Actions publica las imagenes de dev por OIDC (DT-100).'
  }
}

output name string = registry.name
output loginServer string = registry.properties.loginServer
