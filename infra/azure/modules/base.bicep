// U10 (DT-098): recursos del grupo de recursos del entorno.
//
// - Key Vault (DT-022): RBAC, sin políticas de acceso, sin secretos y sin acceso de red público mientras no
//   haya consumidores (U12 abrirá lo que necesite). Retención mínima de borrado temporal (7 días) y sin
//   protección de purga, para que el desmontaje de dev pueda purgarlo; producción deberá activarla.
// - Identidad administrada asignada por el usuario para GitHub Actions, con una sola credencial federada
//   (OIDC) limitada al entorno `dev` del repositorio: sin client secrets ni certificados.
// - Rol Reader sobre este grupo de recursos y nada más: basta para comprobar el inicio de sesión. Los
//   permisos de despliegue los decide U12.

param location string
param projectName string
param environment string
param tags object
param githubOwner string
param githubOwnerId string
param githubRepository string
param githubRepositoryId string
param githubEnvironment string

@description('U12 (DT-100): permite que el servicio de despliegue de plantillas de ARM lea secretos (getSecret) como servicio de confianza. El acceso de red público sigue deshabilitado.')
param armSecretAccess bool = false

// Rol integrado Reader (Microsoft Learn, «Azure built-in roles»).
var readerRoleId = 'acdd72a7-3385-48ef-bd42-f606fba81ae7'

// Nombre global y determinista: 'kv-' + proyecto + entorno + 13 caracteres de uniqueString = 24 como máximo.
var keyVaultName = take('kv-${projectName}-${environment}-${uniqueString(subscription().id, resourceGroup().id)}', 24)

resource keyVault 'Microsoft.KeyVault/vaults@2024-11-01' = {
  name: keyVaultName
  location: location
  tags: tags
  properties: {
    tenantId: subscription().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    enableRbacAuthorization: true
    accessPolicies: []
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    enabledForDeployment: false
    enabledForTemplateDeployment: armSecretAccess
    enabledForDiskEncryption: false
    publicNetworkAccess: 'Disabled'
    networkAcls: {
      // Con armSecretAccess, solo los servicios de confianza de Microsoft (entre ellos el despliegue de
      // plantillas de ARM) atraviesan la red; Container Apps no lo es y nunca lee el vault (DT-100).
      bypass: armSecretAccess ? 'AzureServices' : 'None'
      defaultAction: 'Deny'
    }
  }
}

resource githubIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-${projectName}-${environment}-github'
  location: location
  tags: tags
}

resource githubFederation 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2024-11-30' = {
  parent: githubIdentity
  name: 'github-${githubEnvironment}'
  properties: {
    issuer: 'https://token.actions.githubusercontent.com'
    // Formato inmutable de GitHub (propietario@id/repositorio@id): es el que GitHub emite para este repositorio
    // (AADSTS700213 del 2026-10-09 con el formato sin ids). Sigue limitado al entorno dev: ni ramas ni PR.
    subject: 'repo:${githubOwner}@${githubOwnerId}/${githubRepository}@${githubRepositoryId}:environment:${githubEnvironment}'
    audiences: [
      'api://AzureADTokenExchange'
    ]
  }
}

resource githubReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, githubIdentity.id, readerRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', readerRoleId)
    principalId: githubIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    description: 'U10: lectura del grupo de recursos dev para comprobar el inicio de sesión OIDC (DT-098).'
  }
}

output keyVaultName string = keyVault.name
output keyVaultId string = keyVault.id
output identityName string = githubIdentity.name
output identityId string = githubIdentity.id
output identityClientId string = githubIdentity.properties.clientId
