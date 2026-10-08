// U12 (DT-100): un único entorno de Container Apps con el perfil Consumption (sin perfiles Dedicated): pago por uso
// y escala a cero. Sin Log Analytics: los registros se leen con el streaming de `az containerapp logs show`.

param name string
param location string
param tags object

resource environment 'Microsoft.App/managedEnvironments@2025-01-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
    zoneRedundant: false
  }
}

output id string = environment.id
output name string = environment.name
output defaultDomain string = environment.properties.defaultDomain
