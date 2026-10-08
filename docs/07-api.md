# 07 — Diseño inicial de la API

**Estado:** Versión 1.0 — Etapa 0 (diseño, **no implementado**) · **Fecha:** 2026-09-04 · **Versión 1.1** — revisada en la auditoría de Etapa 0.1 · **Versión 1.2** (2026-09-30) — §7, contrato inicial de solo lectura de la Etapa 2; §§1–6 siguen siendo el catálogo completo previsto · **Versión 1.3** (2026-10-03) — §7.2 y §7.3: `DT-P18` cerrada por `DT-059`; las tres `outcome` se persisten y la resolución humana queda fuera de V1 · **Versión 1.4** (2026-10-03) — U5 autorizada, no implementada: §7.4 (concreción, `DT-064` a `DT-067`) y §7.5 (criterios de cierre); notas en §7.2 · **Versión 1.5** (2026-10-03) — U5 implementada y validada: estado en §7.4 y §7.5 · **Versión 1.6** (2026-10-04) — U6 autorizada, no implementada: endpoint 14 `GET /api/v1/recommendations/{recommendation_id}/explanation` en §7.2 (`DT-068`); notas en §2.12, §7.3, §7.4 y §7.5 · **Versión 1.7** (2026-10-04) — U6 implementada: endpoint 14 en servicio

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
- *Nota del 2026-10-04: U6 no usa esta ruta. La explicación por plantilla es `GET /api/v1/recommendations/{recommendation_id}/explanation` (§7.2, `DT-068`); `POST /assistant/*` queda reservado al asistente con LLM de la Fase 10.*

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

---

## 7. Contrato inicial V1 (Etapa 2)

*Añadido el 2026-09-30. **Implementado por U5** (unidad U5 de `DT-047`; autorizada, implementada y validada el 2026-10-03, concreción en §7.4; hasta entonces decía «diseñado, no implementado»). Es un subconjunto de
§2: no se construyen todos los endpoints. Todo lo no listado aquí queda como catálogo previsto.*

### 7.1 Principios de esta primera versión

1. **Solo lectura.** La API expone datos cargados y resultados ya calculados. Cargar, pronosticar y
   recomendar son ejecuciones batch explícitas (`docs/03` §16.7). Un `GET` nunca recalcula (§5.2).
2. **Autenticada por defecto.** Todo `/api/v1/*` exige `Authorization: Bearer`; las únicas
   excepciones son las de §1: `/health` y, **solo fuera de producción**, la documentación interactiva. Con `APP_ENV=dev` el token es un token de acceso de Microsoft Entra ID que la API valida (U11, `DT-099`); con `APP_ENV=local` lo valida un `TokenValidator` local de
   desarrollo (`docs/10` §15); la autorización por rol se aplica igual, en el backend.
3. **Roles explícitos por endpoint**, sin jerarquía implícita: cada endpoint enumera los roles que
   admite, según la matriz de §3.
4. **Procedencia visible.** Toda respuesta con forecast o recomendación incluye un bloque
   `provenance`: `data_origin`, `dataset_version`, `generator_version`, `as_of_date`, `run_id`,
   `model_version` o `engine_version`, `policy_set` y `notices` (`SYNTHETIC_DATA`,
   `V1_PROVISIONAL_POLICY`). Con `V1_PROVISIONAL`, la recomendación **no** es una recomendación de
   negocio (`DT-031`), y la respuesta lo dice.
5. **Demanda latente fuera.** Ningún endpoint expone `demand`; el histórico es el consumo (`docs/04` §9.1).

### 7.2 Endpoints

| Método y ruta | Entrada | Salida | Errores | Roles | Fuente |
|---|---|---|---|---|---|
| `GET /health` | — | `{status, version}`; no toca la base | — | **Pública** | Proceso |
| `GET /api/v1/me` | — | `{subject_id, roles[]}` | 401 | Cualquiera autenticado | Token |
| `GET /api/v1/products` | `search`, `category_id`, `is_active`, `page`, `page_size`, `sort` | Página de `{id, sku, name, category, unit_of_measure, is_active, valid_from, valid_to, data_origin}` | 400, 401, 403, 422 | VIEWER, ANALYST, PLANNER, ADMIN | `products`, `categories` |
| `GET /api/v1/products/{id}` | — | Producto + inventario al corte + relaciones con proveedor (`moq`, `order_multiple`, `unit_cost`, `agreed_lead_time_days`, `is_preferred`, `is_active`) | 401, 403, 404 | Los cuatro | `products`, `inventory`, `product_suppliers`, `suppliers` |
| `GET /api/v1/products/{id}/history` | `date_from`, `date_to`, `granularity` (`daily`/`weekly`/`monthly`) | Serie de **consumo** con días afectados por desabasto por periodo + media, desviación estándar **poblacional**, CV y periodos en cero (RF-009; `DT-067`, §7.4) | 400, 401, 403, 404, 422 | ANALYST, PLANNER, ADMIN | `consumption` |
| `GET /api/v1/inventory` | `product_id`, `category_id`, `page`, `page_size`, `sort` | Página de `{product_id, sku, on_hand, reserved, available, in_transit_total, inventory_position_accounting, last_movement_at, data_origin}` | 400, 401, 403, 422 | Los cuatro | `inventory` |
| `GET /api/v1/inventory/{product_id}` | — | Lo anterior + líneas abiertas `{order_number, supplier, status, expected_on, quantity_pending}` | 401, 403, 404 | Los cuatro | `inventory`, órdenes |
| `GET /api/v1/forecasts` | `product_id`, `category_id`, `run_id` (por defecto, la última ejecución `FORECAST` completada: regla exacta en §7.4, `DT-066`), paginación | Periodos `{period_start, period_end, predicted_quantity, lower_bound, upper_bound, confidence_level, method_used, confidence_flag}` + `provenance` | 400, 401, 403, 404, 422 | Los cuatro | `forecasts`, `model_versions`, `calculation_runs`, `data_loads` |
| `GET /api/v1/products/{id}/forecast` | `run_id` opcional | Serie del producto + `provenance` | 401, 403, 404 | Los cuatro | Ídem |
| `GET /api/v1/recommendations` | `outcome` (por defecto `RECOMMEND`), `product_id`, `category_id`, `supplier_id`, `run_id`, paginación, `sort` (`sku`, `recommended_quantity`, `suggested_order_date`) | Página de `{id, product, supplier, recommended_quantity, raw_quantity, suggested_order_date, outcome, flags}` + `provenance` | 400, 401, 403, 404 (sin ejecución, `DT-066`), 422 | Los cuatro | `recommendations`, `calculation_runs`, `data_loads` |
| `GET /api/v1/recommendations/{id}` | — | **Desglose completo** de `docs/06` §13 y §16.5, `policy_snapshot`, `reasons`, `flags` + `provenance` | 401, 403, 404 | Los cuatro | Ídem |
| `GET /api/v1/products/{id}/recommendation` | `run_id` opcional | La evaluación del producto en la ejecución, **también** si fue `NO_NEED` (con `raw_quantity = 0`) o `NOT_CALCULABLE` (con sus `reasons`): las tres `outcome` se persisten (`DT-059`, cierra `DT-P18`). 404 solo si no existe la ejecución o el producto | 401, 403, 404 | Los cuatro | Ídem |
| `GET /api/v1/recommendations/{recommendation_id}/explanation` *(U6, `DT-068`; implementada el 2026-10-04)* | — | `{recommendation_id, run_id, outcome, explanation {generator, status, narrative, warning}, facts[], flags[], reasons[], reason_details[], missing_policy_parameters[], provenance}`: explicación por plantilla de la evaluación persistida, sin recalcular; `status` `VERIFIED`, `DEGRADED` (200, `narrative = null`, `warning = NARRATIVE_UNVERIFIED`) o `NOT_APPLICABLE` (`NOT_CALCULABLE`) (`docs/09` §14.5, `DT-069`) | 401, 403, 404, 422 | Los cuatro (los del detalle) | `recommendations`, `products`, `calculation_runs`, `data_loads` |
| `GET /api/v1/runs/{run_id}` | — | `{run_type, status, as_of_date, data_load, versions, counts, started_at, finished_at, error}` | 401, 403, 404 | PLANNER, ADMIN | `calculation_runs`, `data_loads` |

Paginación, ordenación, formato de error y `correlation_id`: los de §1, sin cambios.

*Superficie (2026-10-04, `DT-068`): U5 implementó **13** endpoints; U6 añade el **endpoint 14**, la explicación,
que es una ampliación aceptada e implementada el 2026-10-04. Ninguna respuesta de los otros trece cambia.*

### 7.3 Diferencias con §2, y por qué

| En §2 | En V1 | Motivo |
|---|---|---|
| `in_transit_effective`, `inventory_position_decision`, `coverage_days` y el filtro `below_reorder_point` en `/inventory` | Fuera del inventario | El tránsito efectivo es relativo a una decisión, no un estado (`DT-012`). Esos valores están en el desglose de cada recomendación |
| Filtros `abc_class` y `rotation_class` | Fuera | Siempre nulos en el dataset (`DT-029`) y fuera del cálculo (`V1-11`) |
| Orden por `urgency`, `/risks/*`, `/dashboard/summary` | Aplazados | Dependen de la clasificación de riesgo, pendiente de `BR-X03` |
| Escrituras (maestros, movimientos, consumo, órdenes, recepciones, resolución de recomendaciones), `recalculate`, `data-loads`, `policies`, `models` | Aplazadas | V1 es de solo lectura. La resolución humana de recomendaciones queda fuera de V1: `DT-059` (cierra `DT-P18`) no crea `status` ni `resolved_*`, y se modelará como flujo separado cuando exista quien la escriba; las escrituras de órdenes, a `DT-P13` |
| `/assistant/*` | Aplazado | Llega con el asistente con LLM (Fase 10). La explicación por plantilla de U6 **no** usa `/assistant/*`: es `GET /api/v1/recommendations/{recommendation_id}/explanation` (`DT-068`, 2026-10-04); hasta entonces esta fila decía «Llega con U6» |

### 7.4 Concreción de U5 (`DT-064` a `DT-067`)

*Añadido el 2026-10-03 al autorizar U5. **U5 está implementada y validada (2026-10-03)**; hasta entonces
este párrafo decía «autorizada para implementación y no implementada».*

*Concreta §1, §7.1 y §7.2; no añade ni quita endpoints: son los trece de §7.2, `/health` y
doce rutas bajo `/api/v1`.* *(Nota del 2026-10-04: U6 añade el endpoint 14, `DT-068`; esta sección describe los trece de U5.)*

**Autenticación y roles** (`DT-065`, `docs/10` §15): `Authorization: Bearer <token>` con tokens de
desarrollo opacos `dev-…`; solo arranca con `APP_ENV=local`. Roles exactamente los de §7.2, sin jerarquía.

**Ejecución por defecto** (`DT-066`): carga `COMPLETED` → mayor `as_of_date` → mayor `id` entre las
ejecuciones `COMPLETED` del tipo correspondiente; sin ninguna, o con un `run_id` que no existe, no es del
tipo o no está `COMPLETED`: 404 `RUN_NOT_FOUND`. Vale para `/forecasts`, `/products/{id}/forecast`,
`/recommendations` (que añade el 404 a sus errores de §7.2) y `/products/{id}/recommendation`.

| Endpoint | Concreción |
|---|---|
| `GET /health` | `{status: "ok", version}`; `version` = versión de la aplicación; no toca PostgreSQL |
| `GET /api/v1/products` | `search`: subcadena sin distinguir mayúsculas en `sku` y `name`, 1–100 caracteres, comodines escapados; `sort` ∈ {`sku`, `name`, `id`}, por defecto `sku`; `category` = `{id, code, name}` |
| `GET /api/v1/products/{id}` | `inventory {on_hand, reserved, in_transit_total, last_movement_at}`; `suppliers[]` con `supplier {id, code, name}` y los campos de la relación |
| `GET /api/v1/products/{id}/history` | `DT-067`: periodos `{period_start, period_end, days, days_observed, quantity, stockout_days, complete}` y estadísticos `{periods_used, mean, std_dev, cv, zero_periods}` sobre periodos completos; **`std_dev` es la desviación estándar poblacional** (÷ n, sin corrección de Bessel); 6 decimales `ROUND_HALF_EVEN` |
| `GET /api/v1/inventory` | `sort` ∈ {`sku`, `on_hand`, `available`}, por defecto `sku`; `available = on_hand − reserved`; `inventory_position_accounting = on_hand + in_transit_total − reserved` (`DT-012`, `docs/06` §4.1) |
| `GET /api/v1/inventory/{product_id}` | Líneas abiertas con la misma regla que `docs/06` §16.13.2: cabecera `ISSUED`/`PARTIALLY_RECEIVED`, pendiente `> 0`, `expected_on` = fecha UTC de la línea o, si falta, de la cabecera |
| `GET /api/v1/forecasts` | Solo la serie primaria; paginación **por serie**: `items[{product {id, sku}, model_version {name, version}, periods[...]}]` |
| `GET /api/v1/products/{id}/forecast` | Serie primaria del producto; 404 `FORECAST_NOT_FOUND` si no tiene en esa ejecución |
| `GET /api/v1/recommendations` | `outcome` ∈ {`RECOMMEND`, `NO_NEED`, `NOT_CALCULABLE`}, por defecto `RECOMMEND`; `sort` por defecto `sku`, nulos al final; `product {id, sku, name}`, `supplier {id, code, name}` o `null` |
| `GET /api/v1/recommendations/{id}` | Columnas + `calculation_inputs` tal como se guardó (`DT-059`: exacto, decimal o `"p/q"`, `approximate_terms`, bloque `forecast`, `input_sha256`) + `policy_snapshot`, `reasons`, `missing_policy_parameters`, `flags` |
| `GET /api/v1/products/{id}/recommendation` | El mismo cuerpo que el detalle, para cualquiera de las tres `outcome` |
| `GET /api/v1/runs/{run_id}` | `data_load {id, dataset_version, generator_version, data_origin}`; `versions {engine_version, forecast_run_id, reference_model_version {name, version}, config_sha256}`; `counts` desde `summary`; `error` guardado, solo en `FAILED` |

**`provenance`** (`DT-066`): `data_origin`, `dataset_version`, `generator_version`, `data_load_id`,
`as_of_date`, `run_id`; `model_version` en forecasts; `engine_version`, `policy_set` y `forecast_run_id`
en recomendaciones; `notices`: `SYNTHETIC_DATA` si y solo si la carga es `SYNTHETIC`,
`V1_PROVISIONAL_POLICY` si y solo si `policy_set = 'V1_PROVISIONAL'` (solo recomendaciones). Productos,
inventario e historia no llevan `provenance`; productos e inventario llevan `data_origin` por fila.

**Errores** (`DT-066`): siempre `{"error": {code, message, details, correlation_id}}`.

| HTTP | Código |
|---|---|
| 400 | `INVALID_PARAMETER`, `INVALID_DATE_RANGE`, `INVALID_SORT` |
| 401 | `AUTHENTICATION_REQUIRED`, `INVALID_TOKEN` (con `WWW-Authenticate: Bearer`) |
| 403 | `FORBIDDEN` |
| 404 | `PRODUCT_NOT_FOUND`, `RECOMMENDATION_NOT_FOUND`, `FORECAST_NOT_FOUND`, `RUN_NOT_FOUND`, `NOT_FOUND` |
| 405 | `METHOD_NOT_ALLOWED` (toda escritura) |
| 422 | `VALIDATION_ERROR`, `details = [{field, issue}]` sin el valor recibido |
| 500 | `INTERNAL_ERROR`, mensaje genérico |
| 503 | `SERVICE_UNAVAILABLE` (PostgreSQL no responde) |

**`X-Correlation-ID`**: aceptado si cumple `^[A-Za-z0-9._-]{8,64}$`, si no generado (UUID4); en la cabecera
de toda respuesta y en el cuerpo de todo error. **Paginación:** la de §1, desempate por `id`, página fuera
de rango → 200 vacío. **Números:** `Decimal` como texto JSON. **Solo lectura:** `docs/03` §16.2 y §16.4.
**OpenAPI:** `/docs` y `/openapi.json` públicos en `local`, sin `/redoc`, seguridad `HTTPBearer`.
**CORS y límite de tasa:** fuera de U5.

### 7.5 Criterios de cierre de U5

1. Dependencias de `DT-064` instaladas exactamente (incluido `httpx2==2.13.1`) y el `TestClient`
   funcionando con ellas.
2. `python -m app.api` arranca con `APP_ENV=local` y se niega con `dev`, `staging`, `prod`, sin la variable
   o con otro valor.
3. `TokenValidator` de desarrollo y su registro validados; 401 y 403 correctos; ningún token en los logs.
4. Matriz rol × endpoint completa: 13 endpoints × 4 roles, más la petición sin token.
5. Los 13 endpoints conformes a §7.2 y §7.4 con el dataset 0.4.0.
6. Ejecución por defecto y `run_id` explícito conformes a `DT-066`.
7. Las tres `outcome` se pueden consultar; `NO_NEED` y `NOT_CALCULABLE` nunca son 404.
8. `provenance` y avisos conformes a `DT-066`.
9. Historia conforme a `DT-067`, con desviación estándar poblacional, comprobada con casos calculados a
   mano (semanas ISO, meses, periodos parciales, huecos, n = 0, n = 1, `mean = 0`).
10. Paginación, orden y formato de error uniformes; 405 en escrituras.
11. `X-Correlation-ID` en toda respuesta y en todo error.
12. `/health` público y sin PostgreSQL; `/docs` y `/openapi.json` públicos en `local`; ninguna otra ruta
    responde sin token.
13. OpenAPI con seguridad Bearer y modelos de respuesta y de error.
14. Sin CORS ni límite de tasa.
15. Ninguna escritura: contadores de filas y de `pg_stat_user_tables` sin cambios tras recorrer los
    endpoints, y una escritura forzada rechazada con SQLSTATE 25006.
16. `api` no importa `supply_engine`, `forecasting` ni `runs`.
17. Integración con PostgreSQL en local y en Docker.
18. Regresión: suites de U1–U4 y del generador en verde.
19. `.env.example` con valores ficticios evidentes; ningún secreto.
20. Documentación actualizada con el estado de U5.

*U6 (2026-10-04, `DT-068`): al implementarse, los criterios 4, 5 y 12 se extienden al endpoint 14 (14 endpoints
× 4 roles); sus criterios propios están en `docs/09` §14.6.* *(Cumplido el 2026-10-04: OpenAPI con 14 rutas `GET`, matriz de 14 endpoints × 4 roles + sin token.)*

*Estado (2026-10-03): los veinte criterios se cumplen. Evidencia: `backend/tests/api` (56 pruebas),
`backend/tests/db/test_api_read.py` y `test_api_runs.py` (29), regresión completa y Docker (`project/status.md`).*
