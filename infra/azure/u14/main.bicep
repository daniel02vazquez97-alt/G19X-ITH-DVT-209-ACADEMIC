// U14 (DT-102): Azure Machine Learning minimo en el grupo de U10, para reproducir el backtesting del baseline oficial
// (python -m ml backtest, sin cambios) y registrar sus metricas con MLflow.
//
// - Workspace (kind Default) con identidad asignada por el sistema.
// - Almacenamiento Standard_LRS propio: sin acceso publico a blobs, solo HTTPS y TLS 1.2. Los almacenes del sistema usan
//   el modo de autenticacion por defecto (clave de cuenta), que el servicio gestiona sin que la sesion del responsable
//   necesite roles de datos.
// - Key Vault Standard propio, con directivas de acceso vacias: el servicio anade la de la identidad del workspace. El
//   Key Vault de U10 es privado (opcion C) y no se reutiliza.
// - Application Insights basado en un area de trabajo de Log Analytics: el servicio lo exige (el primer despliegue,
//   2026-10-14, fallo con "Missing dependent resources in workspace json" sin el). Retencion minima (30 dias) y limite
//   diario de ingesta para que no genere coste.
// - Sin registro de contenedores (el job usa una imagen publica fijada por digest, sin construir imagenes), sin
//   instancias de computo y sin endpoints. El computo es serverless y solo existe mientras dura un job.
// Sin secretos. Lo despliega el responsable con infra/azure/deploy-u14.ps1.

targetScope = 'resourceGroup'

@allowed([
  'dev'
])
param environment string = 'dev'

@description('Region: la del grupo de U10 (centralus).')
param location string = resourceGroup().location

param projectName string = 'mpa'
param ownerTag string = 'responsable-del-proyecto'

var tags = {
  project: 'motor-predictivo-abastecimiento'
  environment: environment
  owner: ownerTag
  purpose: 'u14-azure-ml'
  managedBy: 'bicep'
  costControl: 'azure-for-students-planning-50usd'
}
var suffix = uniqueString(resourceGroup().id)
var names = {
  workspace: 'mlw-${projectName}-${environment}'
  storage: take('st${projectName}ml${suffix}', 24)
  keyVault: take('kv-${projectName}ml-${suffix}', 24)
  logAnalytics: 'log-${projectName}-ml-${environment}'
  appInsights: 'appi-${projectName}-ml-${environment}'
}

resource storage 'Microsoft.Storage/storageAccounts@2024-01-01' = {
  name: names.storage
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }
}

resource vault 'Microsoft.KeyVault/vaults@2024-11-01' = {
  name: names.keyVault
  location: location
  tags: tags
  properties: {
    tenantId: subscription().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    accessPolicies: []
    enableRbacAuthorization: false
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
  }
}

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: names.logAnalytics
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
    workspaceCapping: {
      dailyQuotaGb: json('0.1')
    }
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: names.appInsights
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    IngestionMode: 'LogAnalytics'
    RetentionInDays: 30
  }
}

resource workspace 'Microsoft.MachineLearningServices/workspaces@2026-07-01' = {
  name: names.workspace
  location: location
  tags: tags
  kind: 'Default'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    friendlyName: 'Motor predictivo - U14 (dev)'
    description: 'Reproduccion del backtesting F5a del baseline oficial con MLflow (DT-102).'
    storageAccount: storage.id
    keyVault: vault.id
    applicationInsights: appInsights.id
    publicNetworkAccess: 'Enabled'
  }
}

output workspaceName string = workspace.name
output workspaceId string = workspace.id
output storageName string = storage.name
output keyVaultName string = vault.name
