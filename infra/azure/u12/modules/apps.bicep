// U12 (DT-100): las dos apps y el job de bootstrap, con las imágenes de U7/U11 publicadas en el registro.
//
// - frontend: única entrada pública (ingress externo, solo HTTPS). nginx sirve la SPA compilada para Entra ID y
//   reenvía /api a la API en el mismo origen: no hace falta CORS.
// - api: ingress INTERNO (sin endpoint público); APP_ENV=dev valida tokens de Entra ID (U11). HTTP dentro del
//   entorno, de nginx a la api; el TLS termina en el ingress externo del frontend.
// - bootstrap: job Manual de una sola réplica: genera el dataset, migra, carga, pronostica y recomienda en un único
//   contenedor y en ese orden (infra/docker/bootstrap.py); idempotente.
// Contraseñas: DATABASE_URL va SIN contraseña (no es secreto) y libpq toma la contraseña de PGPASSWORD, que es un
// secreto de Container Apps con el valor seguro leído del Key Vault. Así nunca se compone una cadena con la
// contraseña y app.db.connection (U2) no cambia.
// Escala a cero (minReplicas 0) y una réplica como máximo: demo dev.

param location string
param tags object
param environmentId string
param runtimeIdentityId string
param registryServer string
param imageTag string
param postgresHost string
param ownerLogin string
param apiName string
param frontendName string
param bootstrapName string
param entraTenantId string
param entraApiClientId string
param entraSpaClientId string
param runAsOf string

@secure()
param ownerPassword string

@secure()
param appPassword string

var appLogin = 'mpa_app'
var identity = {
  type: 'UserAssigned'
  userAssignedIdentities: {
    '${runtimeIdentityId}': {}
  }
}
var registries = [
  {
    server: registryServer
    identity: runtimeIdentityId
  }
]

resource api 'Microsoft.App/containerApps@2025-01-01' = {
  name: apiName
  location: location
  tags: tags
  identity: identity
  properties: {
    environmentId: environmentId
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: false
        targetPort: 8000
        transport: 'http'
        allowInsecure: true
      }
      registries: registries
      secrets: [
        {
          name: 'app-db-password'
          value: appPassword
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'api'
          image: '${registryServer}/inventory/backend:${imageTag}'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            { name: 'APP_ENV', value: 'dev' }
            { name: 'DATABASE_URL', value: 'postgresql://${appLogin}@${postgresHost}:5432/inventory?sslmode=require' }
            { name: 'PGPASSWORD', secretRef: 'app-db-password' }
            { name: 'ENTRA_TENANT_ID', value: entraTenantId }
            { name: 'ENTRA_API_CLIENT_ID', value: entraApiClientId }
            { name: 'ENTRA_SPA_CLIENT_ID', value: entraSpaClientId }
            { name: 'LOG_LEVEL', value: 'INFO' }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: { path: '/health', port: 8000 }
              initialDelaySeconds: 5
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              httpGet: { path: '/health', port: 8000 }
              initialDelaySeconds: 3
              periodSeconds: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 1
      }
    }
  }
}

resource frontend 'Microsoft.App/containerApps@2025-01-01' = {
  name: frontendName
  location: location
  tags: tags
  identity: identity
  properties: {
    environmentId: environmentId
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8080
        transport: 'auto'
        allowInsecure: false
      }
      registries: registries
    }
    template: {
      containers: [
        {
          name: 'frontend'
          image: '${registryServer}/inventory/frontend:${imageTag}'
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: [
            // Destino del proxy /api de nginx: la api por su nombre dentro del entorno (puerto del ingress, 80).
            { name: 'API_UPSTREAM', value: 'http://${apiName}' }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: { path: '/', port: 8080 }
              periodSeconds: 30
            }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 1
      }
    }
  }
  dependsOn: [
    api
  ]
}

resource bootstrap 'Microsoft.App/jobs@2025-01-01' = {
  name: bootstrapName
  location: location
  tags: tags
  identity: identity
  properties: {
    environmentId: environmentId
    workloadProfileName: 'Consumption'
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: 3600
      replicaRetryLimit: 0
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
      registries: registries
      secrets: [
        {
          name: 'owner-db-password'
          value: ownerPassword
        }
        {
          name: 'app-db-password'
          value: appPassword
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'bootstrap'
          image: '${registryServer}/inventory/bootstrap:${imageTag}'
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
          env: [
            { name: 'DATABASE_URL', value: 'postgresql://${ownerLogin}@${postgresHost}:5432/inventory?sslmode=require' }
            { name: 'PGPASSWORD', secretRef: 'owner-db-password' }
            { name: 'APP_DB_USER', value: appLogin }
            { name: 'APP_DB_PASSWORD', secretRef: 'app-db-password' }
            { name: 'RUN_AS_OF', value: runAsOf }
          ]
        }
      ]
    }
  }
}

output apiInternalFqdn string = api.properties.configuration.ingress.fqdn
output frontendFqdn string = frontend.properties.configuration.ingress.fqdn
