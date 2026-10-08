// Parámetros del entorno dev (U10, DT-098). Sin secretos ni datos personales: el correo del presupuesto, si
// llega a usarse, se pasa en la línea de comandos. Región principal centralus y de respaldo northcentralus:
// las dos están permitidas por la directiva «Allowed resource deployment regions» de la suscripción (DT-098).
using '../main.bicep'

param environment = 'dev'
param location = 'centralus'
param resourceGroupName = 'rg-motor-predictivo-dev'
param projectName = 'mpa'
param ownerTag = 'responsable-del-proyecto'
param githubOwner = 'daniel02vazquez97-alt'
param githubRepository = 'Motor-Predictivo-de-Abastecimiento-de-Inventarios'
param githubEnvironment = 'dev'
param deployBudget = false
// U12 (DT-100): getSecret desde las plantillas de U12; publicNetworkAccess sigue en Disabled.
param keyVaultArmSecretAccess = true
