// U12 (DT-100): despliegue del sistema en el entorno `dev` sobre el grupo de U10.
//
// Ámbito: grupo de recursos `rg-motor-predictivo-dev`. Lo despliega el responsable con su sesión de Azure CLI
// mediante infra/azure/deploy-u12.ps1 (validate → what-if → create), en dos fases:
//   1. core (deployApps = false): registro de contenedores, PostgreSQL, entorno de Container Apps, identidad de
//      ejecución y los roles mínimos de la identidad de GitHub de U10;
//   2. apps (deployApps = true, imageTag = SHA publicado por GitHub Actions): api, frontend y el job de bootstrap,
//      más las reglas de firewall de PostgreSQL para las IP de salida de Container Apps (postgresAllowedIps).
//
// Secretos: ninguno en este archivo ni en los parámetros. Las dos contraseñas de PostgreSQL las genera el script en
// el Key Vault de U10 la primera vez y aquí solo se leen con getSecret (el servicio de despliegue de plantillas de
// ARM es un servicio de confianza del Key Vault). Llegan a PostgreSQL y a los secretos de Container Apps como
// parámetros seguros: nunca aparecen en el historial de despliegue ni en los registros.

targetScope = 'resourceGroup'

@description('Entorno. U12 solo autoriza dev.')
@allowed([
  'dev'
])
param environment string = 'dev'

@description('Región: la del grupo de U10 (centralus, DT-098).')
param location string = resourceGroup().location

param projectName string = 'mpa'
param ownerTag string = 'responsable-del-proyecto'

@description('Key Vault de U10 (DT-098), que guarda las contraseñas de PostgreSQL.')
param keyVaultName string

@description('Identidad de GitHub Actions de U10 (OIDC, entorno dev).')
param githubIdentityName string = 'id-${projectName}-${environment}-github'

@description('GUID del rol integrado "Container Apps Contributor"; deploy-u12.ps1 lo resuelve por nombre.')
param containerAppsContributorRoleId string

@description('GUID del rol integrado "Managed Identity Operator"; deploy-u12.ps1 lo resuelve por nombre.')
param managedIdentityOperatorRoleId string

@description('false: solo la base (fase core). true: además api, frontend y job (fase apps).')
param deployApps bool = false

@description('true si el job de bootstrap ya existe en el grupo; deploy-u12.ps1 lo comprueba antes de cada despliegue.')
param bootstrapJobExists bool = false

@description('Etiqueta de las imágenes publicadas en el registro por GitHub Actions (SHA del commit).')
param imageTag string = ''

@description('IP de salida de Container Apps permitidas en el firewall de PostgreSQL (nunca 0.0.0.0).')
param postgresAllowedIps array = []

@description('Identificadores de Entra ID de U11 (no son secretos).')
param entraTenantId string
param entraApiClientId string
param entraSpaClientId string

@description('Corte de la carga y de los cálculos del bootstrap (DT-058).')
param runAsOf string = '2025-12-31'

@description('U13 (DT-101): true cuando Azure OpenAI está desplegado y verificado con deploy-u13.ps1. La api lo usa para las explicaciones, con la plantilla como respaldo. Sin claves: solo identificadores.')
param genaiEnabled bool = false

@description('U13: nombre del despliegue del modelo en la cuenta de Azure OpenAI (campo model de las llamadas).')
param genaiDeployment string = 'gpt-41-mini'

var tags = {
  project: 'motor-predictivo-abastecimiento'
  environment: environment
  owner: ownerTag
  purpose: 'u12-deploy'
  managedBy: 'bicep'
  costControl: 'azure-for-students-planning-50usd'
}
var suffix = uniqueString(resourceGroup().id)
var names = {
  registry: take('acr${projectName}${environment}${suffix}', 50)
  postgres: 'psql-${projectName}-${environment}-${suffix}'
  environment: 'cae-${projectName}-${environment}'
  runtimeIdentity: 'id-${projectName}-${environment}-runtime'
  api: 'ca-${projectName}-${environment}-api'
  frontend: 'ca-${projectName}-${environment}-frontend'
  bootstrap: 'caj-${projectName}-${environment}-bootstrap'
  openai: 'oai-${projectName}-${environment}-${suffix}' // la crea U13 (infra/azure/u13), no este archivo
}
// Container Apps Contributor only covers Microsoft.App/containerApps/*: `az containerapp job update` failed with
// AuthorizationFailed on Microsoft.App/jobs/write (Deploy dev #4). The built-in job roles (Container Apps Jobs
// Contributor / Operator) grant Microsoft.App/jobs/*/action, which includes listSecrets, so a custom role is used with
// exactly what deploy-dev.yml calls: update (GET + PATCH), start, and the execution status. The read actions are also
// in U10's Reader on the group; they are kept so the role is self-sufficient on the job. Never delete, stop, suspend,
// listSecrets or a wildcard. Reader already covers Microsoft.App/managedEnvironments/read.
var githubJobActions = [
  'Microsoft.App/jobs/read'
  'Microsoft.App/jobs/write'
  'Microsoft.App/jobs/start/action'
  'Microsoft.App/jobs/executions/read'
  'Microsoft.App/jobs/execution/read'
]

resource keyVault 'Microsoft.KeyVault/vaults@2024-11-01' existing = {
  name: keyVaultName
}

resource githubIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = {
  name: githubIdentityName
}

// Identidad de ejecución, separada de la de GitHub: solo descarga imágenes (AcrPull). No lee el Key Vault.
resource runtimeIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: names.runtimeIdentity
  location: location
  tags: tags
}

module registry 'modules/registry.bicep' = {
  name: 'u12-registry'
  params: {
    name: names.registry
    location: location
    tags: tags
    runtimePrincipalId: runtimeIdentity.properties.principalId
    githubPrincipalId: githubIdentity.properties.principalId
    runtimeIdentityId: runtimeIdentity.id
    githubIdentityId: githubIdentity.id
  }
}

module postgres 'modules/postgres.bicep' = {
  name: 'u12-postgres'
  params: {
    name: names.postgres
    location: location
    tags: tags
    ownerPassword: keyVault.getSecret('pg-owner-password')
    allowedIps: postgresAllowedIps
  }
}

module containerEnvironment 'modules/environment.bicep' = {
  name: 'u12-environment'
  params: {
    name: names.environment
    location: location
    tags: tags
  }
}

// GitHub Actions publica revisiones nuevas de las apps y del job: Container Apps Contributor solo sobre este grupo.
resource githubContainerApps 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, githubIdentity.id, containerAppsContributorRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', containerAppsContributorRoleId)
    principalId: githubIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    description: 'U12: actualizar las imagenes de api, frontend y bootstrap en dev (DT-100).'
  }
}

// Actualizar una app que usa la identidad de ejecución exige poder asignarla: solo sobre esa identidad.
resource githubAssignRuntime 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(runtimeIdentity.id, githubIdentity.id, managedIdentityOperatorRoleId)
  scope: runtimeIdentity
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', managedIdentityOperatorRoleId)
    principalId: githubIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    description: 'U12: asignar la identidad de ejecucion al actualizar las apps de dev (DT-100).'
  }
}

// Minimal custom role for the bootstrap job, assignable only inside this group. Like the other GitHub roles it is
// managed by the core phase; its assignment needs the job, so it is made once the job exists (or is deployed now).
resource githubJobRoleDefinition 'Microsoft.Authorization/roleDefinitions@2022-04-01' = {
  name: guid(resourceGroup().id, 'u12-github-bootstrap-job')
  properties: {
    roleName: 'U12 Bootstrap Job Deployer (${resourceGroup().name})'
    description: 'U12: update the image of the bootstrap job, start it and read its executions (DT-100). Nothing else.'
    type: 'CustomRole'
    assignableScopes: [
      resourceGroup().id
    ]
    permissions: [
      {
        actions: githubJobActions
        notActions: []
        dataActions: []
        notDataActions: []
      }
    ]
  }
}

resource bootstrapJob 'Microsoft.App/jobs@2025-01-01' existing = {
  name: names.bootstrap
}

// Only on the job caj-<project>-<env>-bootstrap: never the group or the subscription.
resource githubBootstrapJob 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (deployApps || bootstrapJobExists) {
  name: guid(bootstrapJob.id, githubIdentity.id, githubJobRoleDefinition.name)
  scope: bootstrapJob
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', githubJobRoleDefinition.name)
    principalId: githubIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    description: 'U12: actualizar la imagen del job de bootstrap, arrancarlo y leer sus ejecuciones en dev (DT-100).'
  }
  dependsOn: [
    apps
  ]
}

module apps 'modules/apps.bicep' = if (deployApps) {
  name: 'u12-apps'
  params: {
    location: location
    tags: tags
    environmentId: containerEnvironment.outputs.id
    runtimeIdentityId: runtimeIdentity.id
    registryServer: registry.outputs.loginServer
    imageTag: imageTag
    postgresHost: postgres.outputs.fqdn
    ownerLogin: postgres.outputs.ownerLogin
    ownerPassword: keyVault.getSecret('pg-owner-password')
    appPassword: keyVault.getSecret('pg-app-password')
    apiName: names.api
    frontendName: names.frontend
    bootstrapName: names.bootstrap
    entraTenantId: entraTenantId
    entraApiClientId: entraApiClientId
    entraSpaClientId: entraSpaClientId
    runAsOf: runAsOf
    genaiEnabled: genaiEnabled
    genaiEndpoint: 'https://${names.openai}.openai.azure.com'
    genaiDeployment: genaiDeployment
    runtimeClientId: runtimeIdentity.properties.clientId
  }
  dependsOn: [
    githubAssignRuntime
  ]
}

output registryName string = registry.outputs.name
output registryLoginServer string = registry.outputs.loginServer
output postgresName string = postgres.outputs.name
output postgresFqdn string = postgres.outputs.fqdn
output environmentName string = containerEnvironment.outputs.name
output environmentDefaultDomain string = containerEnvironment.outputs.defaultDomain
output runtimeIdentityId string = runtimeIdentity.id
output apiName string = names.api
output frontendName string = names.frontend
output bootstrapName string = names.bootstrap
output frontendUrl string = 'https://${names.frontend}.${containerEnvironment.outputs.defaultDomain}'
