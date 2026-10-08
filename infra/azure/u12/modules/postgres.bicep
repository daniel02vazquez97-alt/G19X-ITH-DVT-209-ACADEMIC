// U12 (DT-100): Azure Database for PostgreSQL Flexible Server 16, Burstable B1ms, sin alta disponibilidad ni
// réplicas. Acceso público solo para las IP permitidas (las de salida de Container Apps); TLS obligatorio.
// La base `inventory` es nueva e independiente de las bases locales (infra_pgdata, u11-entra-dev_pgdata).

param name string
param location string
param tags object

@description('Usuario propietario: migraciones, carga e inicialización (docs/12 §6). La API usa otro, mpa_app.')
param ownerLogin string = 'mpa_owner'

@secure()
@description('Contraseña del propietario: la lee main.bicep del Key Vault de U10; nunca se escribe a mano.')
param ownerPassword string

@description('IP individuales permitidas. Nunca 0.0.0.0 (equivale a «cualquier servicio de Azure», de cualquier cliente).')
param allowedIps array

resource server 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    version: '16'
    administratorLogin: ownerLogin
    administratorLoginPassword: ownerPassword
    authConfig: {
      activeDirectoryAuth: 'Disabled'
      passwordAuth: 'Enabled'
    }
    storage: {
      storageSizeGB: 32
      autoGrow: 'Disabled'
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
    network: {
      publicNetworkAccess: 'Enabled'
    }
  }
}

resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: server
  name: 'inventory'
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

resource requireTls 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2024-08-01' = {
  parent: server
  name: 'require_secure_transport'
  properties: {
    value: 'ON'
    source: 'user-override'
  }
}

@batchSize(1)
resource firewall 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2024-08-01' = [for ip in allowedIps: {
  parent: server
  name: 'aca-out-${replace(ip, '.', '-')}'
  properties: {
    startIpAddress: ip
    endIpAddress: ip
  }
  dependsOn: [
    requireTls
  ]
}]

output name string = server.name
output fqdn string = server.properties.fullyQualifiedDomainName
output ownerLogin string = ownerLogin
