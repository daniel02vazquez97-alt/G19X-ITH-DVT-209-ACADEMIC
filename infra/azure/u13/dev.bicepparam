// Parametros del despliegue dev de U13 (DT-101). Sin secretos: solo identificadores y el modelo elegido.
using 'main.bicep'

param environment = 'dev'
param projectName = 'mpa'
param ownerTag = 'responsable-del-proyecto'
param runtimeIdentityName = 'id-mpa-dev-runtime'
param modelName = 'gpt-4.1-mini'
param modelVersion = '2025-04-14'
param deploymentName = 'gpt-41-mini'
param deploymentSku = 'GlobalStandard'
param capacity = 10
