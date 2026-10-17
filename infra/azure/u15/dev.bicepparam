// Parametros de U15 en dev: el servicio Free real (creado en el portal el 2026-10-16). Sin secretos.
using 'main.bicep'

param environment = 'dev'
param projectName = 'mpa'
param ownerTag = 'responsable-del-proyecto'
param runtimeIdentityName = 'id-mpa-dev-runtime'
param serviceName = 'motor-predictivo-search-dev'
param searchSku = 'free'
param disableLocalAuth = false
param semanticSearch = 'free'
