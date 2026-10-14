// Parámetros del despliegue dev de U12 (DT-100). Sin secretos: las contraseñas de PostgreSQL viven en el Key Vault
// de U10 y main.bicep las lee con getSecret. Los GUID de roles, la etiqueta de imagen, la fase y las IP de salida
// los pasa deploy-u12.ps1 en cada ejecución (--parameters nombre=valor).
using 'main.bicep'

param environment = 'dev'
param projectName = 'mpa'
param ownerTag = 'responsable-del-proyecto'
param keyVaultName = 'kv-mpa-dev-dymtafh7zjbba'
param githubIdentityName = 'id-mpa-dev-github'
param containerAppsContributorRoleId = ''
param managedIdentityOperatorRoleId = ''
param deployApps = false
param imageTag = ''
param postgresAllowedIps = []
param entraTenantId = '6ce4b1ba-ae4f-4887-bd6b-acb3c72039ad'
param entraApiClientId = 'a9c9ec35-cd73-4ce6-8efd-46755ac86cbe'
param entraSpaClientId = '1ce46703-15f3-4f3d-8668-431e43b813ac'
param runAsOf = '2025-12-31'
// U13 (DT-101): true desde el 2026-10-14 (deploy-u13.ps1 -Stage Verify 9/9 y activación autorizada por el
// responsable). Se aplica con Deploy dev y deploy-u12.ps1 -Stage Apps; para volver a la plantilla, false y -Stage Apps.
param genaiEnabled = true
param genaiDeployment = 'gpt-41-mini'
