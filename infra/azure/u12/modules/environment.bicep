// U12 (DT-100): un único entorno de Container Apps con el perfil Consumption (sin perfiles Dedicated): pago por uso
// y escala a cero. Sin Log Analytics: los registros se leen con el streaming de `az containerapp logs show`.
//
// environmentMode explícito (nota del 2026-10-09 en DT-100): sin él, el entorno quedó en modo Express, que no admite
// Container Apps Jobs (el bootstrap) ni varias opciones de ingress. 'WorkloadProfiles' es el entorno estándar con
// perfiles de carga; el perfil sigue siendo solo Consumption (sin coste fijo).

param name string
param location string
param tags object

resource environment 'Microsoft.App/managedEnvironments@2026-07-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    environmentMode: 'WorkloadProfiles'
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
output environmentMode string = environment.properties.environmentMode
