// Parámetros del entorno dev (U10, DT-098). Sin secretos ni datos personales: el correo del presupuesto, si
// llega a usarse, se pasa en la línea de comandos. La región es la propuesta de DT-098 (evaluación del
// 2026-10-07) y debe estar entre las permitidas por la directiva de la suscripción (README, paso 2); si no lo
// está, la siguiente de la lista: southcentralus, northcentralus.
using '../main.bicep'

param environment = 'dev'
param location = 'westus3'
param resourceGroupName = 'rg-motor-predictivo-dev'
param projectName = 'mpa'
param ownerTag = 'responsable-del-proyecto'
param githubOwner = 'daniel02vazquez97-alt'
param githubRepository = 'Motor-Predictivo-de-Abastecimiento-de-Inventarios'
param githubEnvironment = 'dev'
param deployBudget = false
