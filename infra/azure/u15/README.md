# U15 — Azure AI Search Basic (`DT-094`)

Esta plantilla deja preparado un servicio Azure AI Search **Basic** en `centralus`, con autenticación Entra ID sin
claves locales. `id-mpa-dev-runtime` recibe únicamente `Search Index Data Reader` en el ámbito del servicio. El índice
se crea por separado con el esquema de [`index.json`](index.json), y solo el responsable ejecuta la carga sintética.

## Estado y coste

La plantilla y el adaptador están implementados, pero **no se ha desplegado ningún recurso**. Basic es un nivel
dedicado con cargo continuo mientras exista, aunque esté inactivo. Microsoft indica que en una prueba de 30 días puede
consumir aproximadamente un tercio de los USD 200 de crédito (aprox. USD 67 como orden de magnitud), no como cotización
de `centralus`. Esto supera el presupuesto de planificación de USD 50 de `DT-094`; el precio real depende de región y
capacidad. Por eso el despliegue queda pendiente de cotización y autorización explícita del responsable. No ejecutar los
comandos siguientes hasta resolver ese límite.

## Validación previa (no despliega)

Desde la raíz del repositorio, con Azure CLI autenticado en la suscripción y grupo existentes:

```powershell
az deployment group validate --resource-group rg-motor-predictivo-dev --name u15-dev --template-file infra/azure/u15/main.bicep --parameters infra/azure/u15/dev.bicepparam
az deployment group what-if --resource-group rg-motor-predictivo-dev --name u15-dev --template-file infra/azure/u15/main.bicep --parameters infra/azure/u15/dev.bicepparam
```

El `what-if` esperado contiene solo el servicio Search Basic y su asignación RBAC a `id-mpa-dev-runtime`. No debe
aprobarse ni ejecutarse el despliegue real hasta aceptar el gasto mensual.

## Despliegue futuro

Con la decisión de costo aceptada y el `what-if` revisado por el responsable:

```powershell
az deployment group create --resource-group rg-motor-predictivo-dev --name u15-dev --template-file infra/azure/u15/main.bicep --parameters infra/azure/u15/dev.bicepparam
```

Luego, el responsable con permisos de administración de Search crea/actualiza el índice mediante el provisioner de
`backend/app/api/azure_search.py` y carga exclusivamente los documentos sintéticos de `knowledge/search_corpus/`.
El rol de runtime no permite crear índices ni cargar documentos. No se asigna rol de contribución al runtime.

## Límites

- El nivel, endpoint y esquema se preparan para un índice demo; sin documentos reales ni grupos reales de Entra ID.
- `security_groups` y vigencia se aplican como filtros explícitos en consulta. El rol RBAC de Search no reemplaza esos
  filtros de autorización de documentos.
- Azure OpenAI para embeddings es un recurso separado ya existente por U13; el costo de tokens no se estima aquí.
- No se cablea recuperación a la API ni al frontend en U15.
