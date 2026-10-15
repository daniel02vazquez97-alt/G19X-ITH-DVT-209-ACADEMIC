# U15 — Azure AI Search (`DT-094`)

Esta plantilla deja preparado un servicio Azure AI Search **Basic** en `centralus`, con autenticación Entra ID sin
claves locales. `id-mpa-dev-runtime` recibe únicamente `Search Index Data Reader` en el ámbito del servicio. El índice
se crea por separado con el esquema de [`index.json`](index.json), y solo el responsable ejecuta la carga sintética.

## Estado y coste

La plantilla Basic y el adaptador están implementados, pero **no se ha desplegado ningún recurso**. Basic es un nivel
dedicado con cargo continuo mientras exista, aunque esté inactivo. Microsoft publica una referencia aproximada de USD 67
por 30 días, basada en un tercio de USD 200; no es cotización de `centralus`. La cuenta Azure for Students disponible
tiene USD 100 de crédito total y se mantiene el umbral de planificación de USD 50 de `DT-094`. La instrucción vigente es
minimizar el gasto y evitar recursos facturables continuos.

Antes de Basic, evaluar: (1) el nivel Free para el demo pequeño, sujeto a confirmar compatibilidad con Entra ID sin claves;
Microsoft Learn tiene una discrepancia: la guía RBAC indica cualquier nivel, mientras que la guía de conexiones sin claves
exige Basic o superior; (2) Serverless Developer, que es preview, factura por consumo y depende de disponibilidad regional
y precio mostrado en el portal. Ninguna opción está aprobada ni verificada en la suscripción. Mantener el uso local con
`InMemoryDocumentRetriever` mientras se resuelve. No ejecutar los comandos de despliegue siguientes hasta elegir opción,
revisar su costo efectivo y obtener autorización explícita del responsable.

## Validación previa (no despliega)

Desde la raíz del repositorio, con Azure CLI autenticado en la suscripción y grupo existentes:

```powershell
az deployment group validate --resource-group rg-motor-predictivo-dev --name u15-dev --template-file infra/azure/u15/main.bicep --parameters infra/azure/u15/dev.bicepparam
az deployment group what-if --resource-group rg-motor-predictivo-dev --name u15-dev --template-file infra/azure/u15/main.bicep --parameters infra/azure/u15/dev.bicepparam
```

El `what-if` de la plantilla actual contiene solo el servicio Search Basic y su asignación RBAC a `id-mpa-dev-runtime`.
No debe ejecutarse el despliegue real hasta resolver nivel, costo efectivo y autorización explícita.

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
