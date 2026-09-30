# 07 — Diseño inicial de la API

**Estado:** Versión 1.0 — Etapa 0 (diseño, **no implementado**) · **Fecha:** 2026-09-04 · **Versión 1.1** — revisada en la auditoría de Etapa 0.1

> Ningún endpoint está implementado. Este documento define el contrato previsto para que el frontend,
> Power BI y el asistente de IA se diseñen contra una interfaz estable.

---

## 1. Convenciones generales

| Aspecto | Convención |
|---|---|
| **Estilo** | REST sobre HTTPS, JSON |
| **Prefijo y versión** | `/api/v1` — la versión en la ruta permite evolucionar sin romper clientes |
| **Autenticación** | `Authorization: Bearer <token>` emitido por Microsoft Entra ID. **Todos** los endpoints la requieren salvo los declarados públicos: `/health` y, solo en entornos no productivos, la documentación interactiva |
| **Autorización** | Por rol, validada en el backend (`docs/10-seguridad.md`) |
| **Paginación** | `page` (≥1) y `page_size` (por defecto 50, máx. 200); la respuesta incluye `total`, `page`, `page_size` |
| **Ordenación** | `sort` con nombre de campo y `-` para descendente (`sort=-urgency`) |
| **Filtrado** | Parámetros explícitos por endpoint; nunca filtros arbitrarios que se traduzcan a SQL |
| **Fechas** | ISO-8601, UTC en la API; conversión a zona del negocio en la presentación |
| **Identificadores** | Identificador técnico en la ruta; el SKU es clave de negocio consultable por filtro |
| **Idempotencia** | `GET`, `PUT`, `DELETE` idempotentes; `POST` de creación admite `Idempotency-Key` donde aplique |
| **Contrato** | OpenAPI generado automáticamente por FastAPI; es la especificación normativa |
| **Nombres** | Recursos en plural y en inglés, coherentes con el modelo de datos |

### Formato de error

Uniforme en toda la API:

```json
{
  "error": {
    "code": "PRODUCT_NOT_FOUND",
    "message": "No existe un producto con el identificador indicado.",
    "details": {"product_id": "..."},
    "correlation_id": "..."
  }
}
```

| Código HTTP | Uso |
|---|---|
| 400 | Petición mal formada o parámetros inválidos |
| 401 | Sin token, token inválido o expirado |
| 403 | Autenticado pero sin el rol necesario |
| 404 | Recurso inexistente |
| 409 | Conflicto de estado (p. ej. SKU duplicado, transición de estado inválida) |
| 422 | Validación semántica fallida (Pydantic) |
| 429 | Límite de peticiones excedido |
| 500 | Error interno; nunca expone detalles internos al cliente |
| 503 | Dependencia externa no disponible (con indicación de degradación) |

**Regla:** un error nunca devuelve trazas, consultas SQL, nombres de host internos ni fragmentos de configuración.

---

## 2. Catálogo de endpoints previstos

### 2.1 Salud y metadatos

| Método | Ruta | Propósito | Auth | Rol |
|---|---|---|---|---|
| GET | `/health` | Estado del proceso | **No** | — |
| GET | `/api/v1/health/dependencies` | Estado de base de datos y servicios externos | Sí | `ADMIN` |
| GET | `/api/v1/me` | Identidad y roles efectivos del usuario | Sí | Cualquiera |

### 2.2 Productos

#### `GET /api/v1/products`
- **Propósito:** listar productos con filtros.
- **Parámetros:** `search`, `category_id`, `is_active`, `abc_class`, `rotation_class`, `page`, `page_size`, `sort`.
- **Respuesta 200:** lista paginada de `{id, sku, name, category, unit_of_measure, is_active, abc_class}`.
- **Errores:** 400, 401, 403.
- **Rol:** `VIEWER` o superior.

#### `GET /api/v1/products/{id}`
- **Propósito:** detalle del producto con su posición de inventario y proveedores asociados.
- **Respuesta 200:** producto + `inventory` + `suppliers[]` + clasificación de serie.
- **Errores:** 401, 403, 404. · **Rol:** `VIEWER`.

#### `POST /api/v1/products` · `PUT /api/v1/products/{id}` · `PATCH /api/v1/products/{id}/deactivate`
- **Propósito:** crear, actualizar y desactivar. La desactivación **no** borra histórico.
- **Errores:** 400, 401, 403, 409 (SKU duplicado), 422. · **Rol:** `ADMIN`.

#### `GET /api/v1/products/{id}/history`
- **Propósito:** serie histórica de consumo del producto.
- **Parámetros:** `date_from`, `date_to`, `granularity` (`daily|weekly|monthly`).
- **Respuesta 200:** serie + estadísticos descriptivos (media, desviación, coef. de variación, periodos en cero).
- **Errores:** 400, 401, 403, 404. · **Rol:** `ANALYST`.

### 2.3 Categorías

| Método | Ruta | Propósito | Rol |
|---|---|---|---|
| GET | `/api/v1/categories` | Listar categorías | `VIEWER` |
| POST/PUT | `/api/v1/categories[/{id}]` | Crear / actualizar | `ADMIN` |

### 2.4 Inventario

#### `GET /api/v1/inventory`
- **Propósito:** posición de inventario del catálogo.
- **Parámetros:** `product_id`, `category_id`, `location_id`, `below_reorder_point` (bool), `page`, `page_size`, `sort`.
- **Respuesta 200:** por producto: `on_hand`, `reserved`, `in_transit_total`, `in_transit_effective`,
  `available`, `inventory_position_accounting`, `inventory_position_decision`, `coverage_days`.
  El filtro `below_reorder_point` usa la **posición de decisión** (`DT-012`, `docs/06` §4.2).
- **Rol:** `VIEWER`.

#### `GET /api/v1/inventory/{product_id}`
- **Propósito:** detalle de la posición de un producto, con desglose del tránsito por orden de compra.
- **Errores:** 401, 403, 404. · **Rol:** `VIEWER`.

#### `GET /api/v1/inventory/movements`
- **Propósito:** consultar movimientos históricos.
- **Parámetros:** `product_id`, `location_id`, `movement_type`, `date_from`, `date_to`, paginación.
- **Rol:** `ANALYST`.

#### `POST /api/v1/inventory/movements`
- **Propósito:** registrar un movimiento. **Inmutable**: no existe `PUT` ni `DELETE` sobre movimientos.
- **Errores:** 400, 401, 403, 409, 422. · **Rol:** `PLANNER` o `ADMIN`.

### 2.5 Consumo

| Método | Ruta | Propósito | Rol |
|---|---|---|---|
| GET | `/api/v1/consumption` | Consultar consumo histórico (filtros de producto y fechas) | `ANALYST` |
| POST | `/api/v1/consumption` | Registrar consumo (individual o lote) | `PLANNER` |

### 2.6 Proveedores

| Método | Ruta | Propósito | Rol |
|---|---|---|---|
| GET | `/api/v1/suppliers` | Listar proveedores con indicadores resumidos | `VIEWER` |
| GET | `/api/v1/suppliers/{id}` | Detalle: datos, productos suministrados, desempeño | `VIEWER` |
| POST/PUT | `/api/v1/suppliers[/{id}]` | Crear / actualizar | `ADMIN` |
| GET | `/api/v1/suppliers/{id}/performance` | Cumplimiento en tiempo y cantidad, lead time medio y variabilidad (parámetros `period_from`, `period_to`) | `ANALYST` |
| GET | `/api/v1/suppliers/{id}/lead-times` | Lead times observados vs. acordados por producto | `ANALYST` |
| GET | `/api/v1/products/{id}/suppliers` | Proveedores de un producto con MOQ, múltiplo, costo y lead time | `VIEWER` |
| POST/PUT | `/api/v1/product-suppliers[/{id}]` | Gestionar la relación producto–proveedor | `ADMIN` |

### 2.7 Órdenes de compra

| Método | Ruta | Propósito | Rol |
|---|---|---|---|
| GET | `/api/v1/purchase-orders` | Listar (filtros: `supplier_id`, `status`, `date_from`, `date_to`) | `VIEWER` |
| GET | `/api/v1/purchase-orders/{id}` | Detalle con líneas y recepciones | `VIEWER` |
| POST | `/api/v1/purchase-orders` | Crear orden (puede originarse en una recomendación) | `PLANNER` |
| PATCH | `/api/v1/purchase-orders/{id}/status` | Cambiar estado (transiciones válidas únicamente) | `PLANNER` |
| POST | `/api/v1/purchase-orders/{id}/receipts` | Registrar recepción; actualiza inventario y lead time observado | `PLANNER` |

**Nota:** crear una orden desde una recomendación **es una acción humana explícita**. La API no
convierte recomendaciones en órdenes automáticamente (RF-015).

### 2.8 Predicciones

#### `GET /api/v1/forecasts`
- **Propósito:** listar predicciones vigentes.
- **Parámetros:** `product_id`, `category_id`, `as_of_date`, `granularity`, paginación.
- **Respuesta 200:** por periodo: `predicted_quantity`, `lower_bound`, `upper_bound`, `confidence_level`,
  `method_used`, `model_version`, `as_of_date`, `confidence_flag`.
- **Rol:** `VIEWER`.

#### `GET /api/v1/products/{id}/forecast`
- **Propósito:** predicción de un producto para el horizonte solicitado.
- **Parámetros:** `horizon`, `granularity`, `as_of_date` (por defecto, la más reciente).
- **Respuesta 200:** serie predicha + histórico reciente para contexto + metadatos del modelo.
- **Errores:** 401, 403, 404, 409 (sin histórico suficiente y sin método de respaldo aplicable). · **Rol:** `VIEWER`.

#### `POST /api/v1/forecasts/recalculate`
- **Propósito:** disparar recálculo (catálogo completo o subconjunto). **Asíncrono**: devuelve `202` con
  identificador de ejecución.
- **Errores:** 401, 403, 409 (ya hay una ejecución en curso), 503. · **Rol:** `ADMIN` o `PLANNER`.

#### `GET /api/v1/forecasts/runs/{run_id}`
- **Propósito:** estado y resultado de una ejecución. · **Rol:** `PLANNER`.

### 2.9 Recomendaciones

#### `GET /api/v1/recommendations`
- **Propósito:** listar recomendaciones vigentes, priorizadas.
- **Parámetros:** `urgency`, `status`, `product_id`, `category_id`, `supplier_id`, `date_from`, paginación, `sort`.
- **Respuesta 200:** por recomendación: producto, proveedor sugerido, `recommended_quantity`,
  `suggested_order_date`, `urgency`, `status`, y un resumen de los términos del cálculo.
- **Rol:** `VIEWER`.

#### `GET /api/v1/products/{id}/recommendation`
- **Propósito:** recomendación vigente de un producto **con el desglose completo del cálculo**
  (§13 de `docs/06-motor-abastecimiento.md`): forecast usado, lead time, `σ_D`, `σ_L`, stock de
  seguridad, punto de reorden, posición de inventario, cantidad bruta, ajustes por MOQ y múltiplo,
  versión del motor.
- **Errores:** 401, 403, 404, 409 (parámetro de política no definido → indica cuál falta). · **Rol:** `VIEWER`.

#### `PATCH /api/v1/recommendations/{id}`
- **Propósito:** registrar la decisión humana: `ACKNOWLEDGED`, `DISMISSED` (con motivo) o `CONVERTED_TO_PO`.
- **Errores:** 400, 401, 403, 404, 409. · **Rol:** `PLANNER`.

#### `POST /api/v1/recommendations/recalculate`
- **Propósito:** recalcular recomendaciones. Asíncrono, `202`. · **Rol:** `ADMIN` o `PLANNER`.

### 2.10 Riesgos

| Método | Ruta | Propósito | Rol |
|---|---|---|---|
| GET | `/api/v1/risks/stockout` | Productos con riesgo de desabasto: nivel, cobertura, fecha estimada de agotamiento | `VIEWER` |
| GET | `/api/v1/risks/overstock` | Productos con sobreinventario: cobertura excesiva, excedente, capital inmovilizado | `VIEWER` |
| GET | `/api/v1/products/{id}/risk` | Evaluación de riesgo de un producto con sus insumos | `VIEWER` |

### 2.11 Dashboard

#### `GET /api/v1/dashboard/summary`
- **Propósito:** indicadores agregados para la vista principal: número de productos críticos,
  recomendaciones abiertas por urgencia, órdenes pendientes, cobertura media, productos en
  sobreinventario, fecha del último recálculo y método predominante (modelo vs. baseline).
- **Rol:** `VIEWER`.

### 2.12 Asistente de IA

#### `POST /api/v1/assistant/ask`
- **Propósito:** pregunta en lenguaje natural.
- **Cuerpo:** `{question, context?: {product_id?, recommendation_id?}, conversation_id?}`.
- **Respuesta 200:** `{answer, sources: [{type: "data"|"document", reference, ...}], used_data: {...}, conversation_id}`.
- **Restricciones:** las cifras de `answer` provienen de `used_data`; el servicio verifica que no
  aparezcan cifras ajenas al contexto (RS-010). El alcance de datos y documentos se filtra por la
  identidad y el rol del solicitante (RS-004).
- **Errores:** 400, 401, 403, 429, 503 (servicio generativo no disponible → la UI degrada sin bloquear). · **Rol:** `ANALYST` o `PLANNER`.

#### `POST /api/v1/assistant/explain/{recommendation_id}`
- **Propósito:** explicación en lenguaje natural de una recomendación **ya calculada**.
- **Respuesta 200:** `{explanation, recommendation_snapshot, sources}`.
- **Restricción:** el LLM recibe las cifras; no las genera ni las modifica. · **Rol:** `VIEWER`.

### 2.13 Ingesta de datos

| Método | Ruta | Propósito | Rol |
|---|---|---|---|
| POST | `/api/v1/data-loads` | Cargar un archivo (`data_origin` obligatorio: `SYNTHETIC` o `REAL`). Asíncrono, `202` | `ADMIN` |
| GET | `/api/v1/data-loads/{id}` | Resultado: filas aceptadas, rechazadas y motivo de cada rechazo | `ADMIN` |

### 2.14 Políticas de inventario

| Método | Ruta | Propósito | Rol |
|---|---|---|---|
| GET | `/api/v1/policies` | Consultar políticas vigentes por ámbito | `ADMIN` |
| PUT | `/api/v1/policies/{id}` | Actualizar (crea una **nueva versión** con vigencia; no sobrescribe) | `ADMIN` |

### 2.15 Modelos

| Método | Ruta | Propósito | Rol |
|---|---|---|---|
| GET | `/api/v1/models` | Versiones de modelo con métricas, baseline y estado | `ANALYST` |
| GET | `/api/v1/models/{id}` | Detalle de una versión | `ANALYST` |

---

## 3. Matriz de autorización (resumen)

| Área | `VIEWER` | `ANALYST` | `PLANNER` | `ADMIN` |
|---|---|---|---|---|
| Consultar catálogo, inventario, riesgos, recomendaciones | ✅ | ✅ | ✅ | ✅ |
| Análisis histórico, desempeño de proveedores, modelos | — | ✅ | ✅ | ✅ |
| Registrar movimientos, consumo, órdenes y recepciones | — | — | ✅ | ✅ |
| Resolver recomendaciones | — | — | ✅ | ✅ |
| Disparar recálculos | — | — | ✅ | ✅ |
| Asistente de IA | Explicaciones | ✅ | ✅ | ✅ |
| Maestros, políticas, cargas de datos, usuarios | — | — | — | ✅ |

Matriz **propuesta**, pendiente de validación con el negocio junto con la definición de roles (RS-002).

## 4. Operaciones asíncronas

Los recálculos y las cargas de datos son procesos largos. Patrón uniforme:

1. `POST` → `202 Accepted` con `{run_id, status: "PENDING", status_url}`.
2. `GET {status_url}` → `{status: PENDING|RUNNING|COMPLETED|FAILED, progress, result, error}`.
3. Sin ejecuciones concurrentes del mismo alcance: la segunda recibe `409`.

## 5. Consideraciones de diseño

1. **Contrato antes que implementación.** El frontend se desarrolla contra esta especificación; los
   cambios incompatibles requieren nueva versión de ruta.
2. **Lectura y cálculo separados.** Un `GET` nunca dispara un recálculo como efecto colateral.
3. **Sin filtros arbitrarios.** No se aceptan expresiones libres que se traduzcan a SQL.
4. **Límite de peticiones**, especialmente en los endpoints del asistente, que tienen costo real.
5. **Trazabilidad.** Todo error y toda respuesta llevan `correlation_id` para poder seguirlos en los logs.
6. **CORS restringido** a los orígenes conocidos del frontend.
7. **Documentación interactiva** habilitada solo en entornos no productivos.

## 6. Pendiente de definición

- ¿Se requiere exportación a CSV/Excel desde la API? (afecta a paginación y límites)
- ¿Habrá notificaciones/alertas salientes (correo, Teams) ante riesgo crítico?
- ¿Se necesitará una API de escritura para integrar un ERP en el futuro? (afecta al versionado)
- Límites concretos de tasa por rol y por endpoint.
