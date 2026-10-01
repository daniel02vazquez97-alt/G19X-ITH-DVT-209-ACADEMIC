# 03 — Arquitectura

**Estado:** Versión 1.0 — Etapa 0 (diseño, no implementado) · **Fecha:** 2026-09-04 · **Versión 1.1** — revisada en la auditoría de Etapa 0.1 · **Versión 1.2** (2026-09-30) — §16, arquitectura de implementación de la Etapa 2 (`DT-043`, `DT-047`); §§1–15 no cambian

> Este documento describe la arquitectura **objetivo**. Nada de lo aquí descrito está implementado
> todavía. Las decisiones que lo sustentan están en `docs/15-decisiones-tecnicas.md`.
>
> **Etapa 2 (2026-09-30):** §16 traduce esta arquitectura a paquetes, contratos y orden de
> construcción. Sigue sin existir código de aplicación; lo único ejecutable del repositorio es el
> generador de datos sintéticos, terminado en la Etapa 1.

---

## 1. Principios arquitectónicos

1. **Separación de predicción, decisión y explicación.** La capa ML predice, la capa de reglas
   decide, la capa generativa explica. Nunca se invierten los papeles.
2. **Determinismo en la ruta de decisión.** Todo cálculo de abastecimiento es reproducible y auditable.
3. **Dependencias externas encapsuladas.** Azure ML, Azure OpenAI y Azure AI Search se consumen a
   través de interfaces propias con implementación sustituta local, de modo que el sistema es
   ejecutable y testeable sin nube.
4. **Degradación controlada.** La caída de un servicio externo degrada funcionalidad, no la interrumpe.
5. **Simplicidad deliberada.** Monolito modular en el backend. No se introducen microservicios,
   colas ni orquestadores mientras el alcance no lo exija (`DT-005`).
6. **El histórico es inmutable.** Movimientos, órdenes, predicciones y recomendaciones se conservan;
   las correcciones se registran como hechos nuevos.

## 2. Vista de contexto

```mermaid
flowchart LR
    P[Planificador / Comprador]
    AN[Analista]
    AD[Administrador]
    DIR[Dirección]

    P --> SYS
    AN --> SYS
    AD --> SYS
    DIR --> PBI[Power BI]

    subgraph SYS[Motor Predictivo de Abastecimiento]
        FE[Interfaz web]
        BE[API + motores]
        DB[(PostgreSQL)]
    end

    SYS --> PBI
    SYS -.-> ENT[Microsoft Entra ID]
    SYS -.-> AZ[Servicios de Azure<br/>ML · OpenAI · AI Search]
    ERP[(Origen de datos:<br/>archivos / ERP futuro)] --> SYS
```

## 3. Vista de componentes

```mermaid
flowchart TB
    subgraph FE[Frontend · React SPA]
        UI[Vistas]
        MSAL[MSAL · autenticación]
        APIC[Cliente API]
    end

    subgraph BE[Backend · FastAPI - monolito modular]
        RT[Capa de routers/HTTP]
        AUTH[Autenticación y autorización]
        SVC[Servicios de aplicación]
        SUP[[supply_engine<br/>reglas determinísticas]]
        FCS[[forecast_service<br/>predicción]]
        GEN[[genai_service<br/>explicación y RAG]]
        REPO[Repositorios / acceso a datos]
        ING[Ingesta y validación]
    end

    subgraph DATA[Persistencia]
        PG[(PostgreSQL<br/>operativo + histórico + derivado)]
    end

    subgraph EXT[Servicios externos]
        AML[Azure ML endpoint]
        AOAI[Azure OpenAI]
        AIS[Azure AI Search]
        ENT[Entra ID]
    end

    UI --> APIC --> RT
    MSAL -.-> ENT
    RT --> AUTH --> ENT
    RT --> SVC
    SVC --> SUP
    SVC --> FCS
    SVC --> GEN
    SUP --> REPO
    FCS --> REPO
    FCS -.-> AML
    GEN --> AIS
    GEN --> AOAI
    GEN --> SVC
    ING --> REPO
    REPO --> PG
    PG --> PBIQ[Vistas analíticas] --> PBI[Power BI]
```

### 3.1 Responsabilidades por componente

| Componente | Responsabilidad | Explícitamente NO hace |
|---|---|---|
| **React SPA** | Presentación, navegación, estado de UI, obtención de token | Reglas de negocio, autorización real |
| **Routers FastAPI** | Contrato HTTP, validación de entrada/salida, códigos de error | Lógica de negocio |
| **Auth** | Validar token de Entra ID, resolver identidad y roles | Emitir tokens |
| **Servicios de aplicación** | Orquestar casos de uso, transacciones | Cálculos de inventario (delega en `supply_engine`) |
| **`supply_engine`** | Stock de seguridad, punto de reorden, cantidad recomendada, riesgos — **puro y determinístico** | Acceder a HTTP, llamar a LLM, entrenar modelos |
| **`forecast_service`** | Producir predicción + incertidumbre; seleccionar modelo o baseline | Decidir cantidades de compra |
| **`genai_service`** | Construir contexto, recuperar documentos, invocar LLM, citar fuentes | Calcular cifras, escribir en la base de datos |
| **Repositorios** | Persistencia y consultas | Reglas de negocio |
| **Ingesta** | Cargar, validar y marcar origen de los datos | Transformaciones de negocio no documentadas |
| **PostgreSQL** | Verdad operativa e histórica | Lógica de aplicación compleja en la base |

**Regla de dependencia:** `supply_engine` es una biblioteca **pura**, sin dependencias de FastAPI,
base de datos ni red. Recibe estructuras de datos y devuelve estructuras de datos. Esto es lo que
permite probarlo con casos exactos y garantiza RNF-002.

## 4. Interfaces internas

Cada frontera relevante se define como una interfaz (*port*) con al menos dos implementaciones:
una real y una local/sustituta para desarrollo y pruebas.

| Interfaz | Contrato conceptual | Implementaciones |
|---|---|---|
| `ForecastProvider` | `predict(sku, horizon, as_of) -> serie estimada + incertidumbre + versión de modelo` | Local (baseline / modelo en proceso) · Azure ML endpoint |
| `DocumentRetriever` | `search(query, filtros, top_k) -> fragmentos + referencia de origen` | Local (índice en memoria/ficheros) · Azure AI Search |
| `TextGenerator` | `generate(prompt, contexto) -> texto + metadatos` | Local (plantilla determinística) · Azure OpenAI |
| `SecretProvider` | `get(nombre) -> valor` | Variables de entorno · almacén gestionado (producto sin fijar, `DT-022`) |
| `DataSource` (ingesta) | `load(origen) -> registros validados + reporte` | Archivos sintéticos · Archivos reales · (futuro) ERP |

Consecuencia práctica: el sistema arranca y funciona sin ninguna credencial de Azure. Esto es un
requisito operativo (RNF-006), no una comodidad de desarrollo.

## 5. Flujo de datos

### 5.1 Flujo principal — generación de recomendaciones (proceso por lotes)

```mermaid
sequenceDiagram
    participant SCH as Programador (batch)
    participant ING as Ingesta
    participant PG as PostgreSQL
    participant FC as forecast_service
    participant SE as supply_engine
    participant AUD as Histórico

    SCH->>ING: Ejecutar carga incremental
    ING->>PG: Persistir consumo, movimientos, órdenes (validados)
    SCH->>FC: Generar forecast por SKU (as_of = hoy)
    FC->>PG: Leer histórico de consumo
    FC-->>PG: Guardar Forecast (+ versión de modelo, intervalo)
    SCH->>SE: Calcular recomendaciones
    SE->>PG: Leer inventario, tránsito, lead times, proveedores, políticas
    SE->>PG: Leer forecast vigente
    SE-->>PG: Guardar Recommendation (+ insumos usados)
    SE-->>AUD: Registrar ejecución (fecha, versión, parámetros)
```

Punto clave: el forecast se **persiste** antes de ser consumido. Así la recomendación queda anclada
a una predicción concreta e identificable, y es reconstruible meses después (RF-024).

### 5.2 Flujo de consulta interactiva

```
Usuario → React → (token) → FastAPI → validación de token y rol
       → servicio de aplicación → repositorio → PostgreSQL
       → respuesta tipada → React
```

La consulta interactiva **lee** resultados ya calculados. El recálculo bajo demanda para un producto
concreto es posible pero explícito (endpoint separado), nunca un efecto colateral de una lectura.

### 5.3 Flujo de explicación / asistente (RAG)

```mermaid
sequenceDiagram
    participant U as Usuario
    participant R as React
    participant API as FastAPI
    participant SVC as Servicios (datos estructurados)
    participant AIS as Azure AI Search
    participant LLM as Azure OpenAI

    U->>R: Pregunta / solicita explicación
    R->>API: POST /api/assistant/ask (token)
    API->>API: Validar identidad, rol y alcance permitido
    API->>SVC: Obtener cifras (forecast, inventario, recomendación)
    API->>AIS: Recuperar contexto documental (filtrado por permisos)
    AIS-->>API: Fragmentos + referencias
    API->>LLM: Prompt = instrucciones + cifras + fragmentos (marcados como datos)
    LLM-->>API: Texto explicativo
    API->>API: Verificar que no aparecen cifras ajenas al contexto
    API-->>R: Respuesta + fuentes citadas
```

El LLM recibe las cifras; **no las produce**. La verificación posterior es parte del flujo, no un extra.

## 6. Autenticación

- Identidad corporativa en **Microsoft Entra ID**.
- El frontend (SPA) usa el **flujo de código de autorización con PKCE** —el recomendado para
  aplicaciones de página única— y obtiene un token de acceso para la API registrada.
- El backend expone un *scope* propio de API y **valida el token** en cada petición: firma contra las
  claves publicadas por el emisor, `iss`, `aud`, vigencia y los *scopes* o *app roles* presentes.
- El backend no acepta tokens emitidos para otra audiencia, aunque sean válidos.
- Endpoints públicos: únicamente los declarados de forma explícita (`/health`, documentación en entornos no productivos).

## 7. Autorización

Roles conceptuales iniciales (**pendientes de validación**, ver `docs/10-seguridad.md`):

| Rol | Puede |
|---|---|
| `ADMIN` | Todo, incluida configuración de políticas y gestión de usuarios/roles |
| `PLANNER` | Consultar todo el ámbito operativo, ejecutar recálculos, marcar recomendaciones como atendidas |
| `ANALYST` | Consultar y analizar; sin acciones operativas |
| `VIEWER` | Solo lectura de dashboards y listados |

Aplicación: dependencia de FastAPI que resuelve identidad y roles desde el token y los verifica
contra el permiso requerido por el endpoint. **La autorización nunca depende del frontend.** El
asistente de IA opera bajo la identidad del usuario y hereda sus restricciones (RS-004).

## 8. Comunicación entre componentes

| Origen → Destino | Protocolo | Notas |
|---|---|---|
| React → FastAPI | HTTPS / REST JSON | Contrato OpenAPI generado; CORS restringido a orígenes conocidos |
| FastAPI → PostgreSQL | TCP/TLS, pool de conexiones | Migraciones versionadas con credencial separada |
| FastAPI → Azure ML | HTTPS al endpoint del modelo | Con reintentos acotados y *timeout*; ante fallo, baseline local |
| FastAPI → Azure AI Search | HTTPS, SDK oficial | Autenticación por Entra ID preferida sobre clave |
| FastAPI → Azure OpenAI | HTTPS, SDK oficial | Autenticación por Entra ID preferida; sin datos sensibles innecesarios en el prompt |
| Power BI → PostgreSQL | Conector nativo | Solo lectura, sobre vistas analíticas dedicadas |
| Proceso batch → módulos | Invocación en proceso | Mismo código que la API; sin duplicar lógica |

Comunicación **síncrona** en toda la primera versión. No se introduce mensajería asíncrona sin una
necesidad demostrada (`DT-005`).

## 9. Almacenamiento

PostgreSQL organiza los datos en tres naturalezas, dentro de un mismo esquema lógico:

| Naturaleza | Contenido | Característica |
|---|---|---|
| **Operativa** | Productos, categorías, proveedores, relación producto–proveedor, inventario vigente, órdenes | Mutable con historial de auditoría |
| **Histórica** | Movimientos de inventario, consumo/ventas, recepciones | **Append-only**, inmutable |
| **Derivada** | Forecast, recomendaciones, métricas de proveedor, versiones de modelo | Recalculable, pero **conservada** para trazabilidad |

Los datos derivados se conservan aunque puedan recalcularse: recalcular con el modelo actual no
reproduce lo que el sistema recomendó hace tres meses.

Detalle en `docs/04-modelo-datos.md`.

## 10. Machine Learning en la arquitectura

- **Entrenamiento:** fuera de la ruta de petición, como *job* en Azure Machine Learning (o local en
  fases tempranas). Registra experimentos y métricas; el seguimiento es compatible con MLflow.
- **Registro:** cada modelo aceptado se registra con versión, métricas y datos de entrenamiento; la
  tabla `ModelVersion` refleja localmente esa referencia.
- **Inferencia:** por lotes, para todo el catálogo, en el proceso programado. Si más adelante se
  requiere inferencia en línea, se expone como *managed online endpoint* de Azure ML detrás de la
  interfaz `ForecastProvider`.
- **Monitoreo:** comparación de la predicción contra la demanda real observada y vigilancia de deriva
  de datos y de desempeño.
- **Frontera:** el modelo entrega demanda estimada e incertidumbre. Nada más. (RML-012)

## 11. IA generativa en la arquitectura

- `genai_service` es el **único** punto que habla con Azure OpenAI y Azure AI Search.
- El servicio **no tiene acceso de escritura** a la base de datos.
- Recibe siempre cifras ya calculadas; nunca consulta reglas ni recalcula.
- El contenido recuperado se inserta delimitado y marcado como datos, no como instrucciones (RS-011).
- Toda respuesta lleva trazabilidad: qué datos y qué documentos se usaron.

## 12. Observabilidad

| Señal | Contenido |
|---|---|
| **Logs estructurados** | Identificador de correlación, usuario (por id), endpoint, resultado, duración. Sin secretos ni datos personales |
| **Métricas** | Latencia y tasa de error por endpoint, duración y resultado del proceso batch, número de SKU procesados, uso de baseline vs. modelo |
| **Métricas de ML** | Error de pronóstico observado, cobertura del intervalo, indicadores de deriva |
| **Auditoría** | Acciones sensibles: cambios de política, aprobaciones, cargas de datos, cambios de rol |
| **Salud** | `/health` (proceso) y verificación de dependencias (base de datos, servicios externos) por separado |

Cada ejecución del proceso de predicción y recomendación deja un registro con fecha, alcance,
versión de modelo, parámetros y resultado.

## 13. CI/CD en la arquitectura

```mermaid
flowchart LR
    F[feature branch] --> PR[Pull Request]
    PR --> L[Lint + formato + tipado]
    L --> T[Tests unitarios e integración]
    T --> S[Análisis de seguridad<br/>y detección de secretos]
    S --> B[Build de imágenes Docker]
    B --> M{¿Aprobado y mergeado?}
    M -->|Sí| D[Despliegue a entorno]
    M -->|No| F
```

El acceso de GitHub Actions a Azure se realiza mediante **OpenID Connect con credenciales federadas**,
sin almacenar secretos de larga vida. Detalle en `docs/12-devops.md`.

## 14. Auditoría de proporcionalidad (revisión 0.1)

Revisión componente a componente: **responsabilidad, necesidad, dependencia, integración y si existe
una alternativa más simple**. Ninguna tecnología se descarta por ser compleja; la pregunta es si su
inclusión está justificada por el alcance declarado.

| Componente | Responsabilidad | ¿Necesario? | Depende de | Integración | ¿Alternativa más simple? |
|---|---|---|---|---|---|
| **React.js** | Interfaz web | **Sí** — alcance 15, y stack obligatorio | API | HTTPS + token | Plantillas del servidor bastarían para consulta, pero no para el estado de las listas priorizadas y el asistente. Se mantiene |
| **FastAPI** | Contrato HTTP, validación, OpenAPI | **Sí** — stack obligatorio | PostgreSQL, motores | En proceso | No. El contrato explícito es lo que permite que frontend, Power BI y asistente consuman lo mismo |
| **PostgreSQL** | Verdad operativa e histórica | **Sí** — stack obligatorio | — | TCP/TLS | Datos fuertemente relacionales con integridad transaccional. Ninguna alternativa más simple sirve |
| **Supply Engine** | Reglas determinísticas | **Sí** — alcance 12, 13, 14 | Nada (biblioteca pura) | Invocación en proceso | Ya es la forma más simple posible: funciones puras sin dependencias |
| **Machine Learning (Python)** | Predicción de demanda | **Sí** — alcance 9 | Datos históricos | `ForecastProvider` | El baseline es la alternativa más simple, y **está incluida** como nivel 0 y como respaldo permanente |
| **Azure Machine Learning** | Ciclo de vida del modelo | **Sí, con matiz** — stack obligatorio | Pipeline de ML | Endpoint / job | Alternativa más simple: entrenar en local y versionar a mano. **Se usa esa alternativa en la Fase 5**; Azure ML entra en la Fase 6, cuando hay algo que gobernar |
| **Azure OpenAI** | Explicación en lenguaje natural | **Sí** — alcance 17 | Cifras ya calculadas | `TextGenerator` | Alternativa más simple: plantilla determinística. **Se usa primero** (`DT-018`); Azure OpenAI la sustituye después tras la misma interfaz |
| **Azure AI Search** | Recuperación documental | **Condicionado** — alcance 18, pero **depende de ASSUMPTION-008** | Corpus documental | `DocumentRetriever` | Si el corpus es pequeño, una búsqueda simple bastaría. **Si no existe corpus, este componente pierde su propósito**: es el único riesgo real de sobredimensionamiento del stack |
| **Power BI** | Analítica de negocio | **Sí** — alcance 16, y stack obligatorio | Vistas de PostgreSQL | Conector nativo, solo lectura | Construir un BI propio sería más complejo, no más simple |
| **Microsoft Entra ID** | Identidad corporativa | **Sí** — alcance 19, y stack obligatorio | — | OAuth 2.0 / OIDC | Gestionar contraseñas propias sería más simple de escribir y peor en todo lo demás |
| **Docker** | Empaquetado reproducible | **Sí** — stack obligatorio | — | Imágenes | Alternativa: instalación manual. Peor: rompe la reproducibilidad exigida por el CI |
| **GitHub Actions** | Lint, pruebas, build, despliegue | **Sí** — alcance 20, y stack obligatorio | Repositorio | OIDC hacia Azure | Ejecución manual de pruebas. Contradice el alcance 20 |

### Conclusión de la auditoría de arquitectura

1. **No hay sobreingeniería estructural.** El backend es un monolito modular (`DT-002`); no hay
   microservicios, ni orquestador de contenedores, ni mensajería, ni caché distribuida, ni base de
   datos adicional. Todas ellas se descartaron explícitamente y siguen descartadas.
2. **Ninguno de los doce componentes se añadió por iniciativa propia.** Diez pertenecen al stack
   obligatorio del alcance; `supply_engine` es código propio exigido por los puntos 12, 13 y 14; y
   Azure AI Search, aunque figura en el stack obligatorio, queda **condicionado** a ASSUMPTION-008. La única tecnología ajena a esa lista que había aparecido —Azure Key Vault— se ha
   reclasificado como `PROPUESTA` en `DT-022`.
3. **El patrón que evita el sobredimensionamiento es la alternativa simple primero:** baseline antes
   que modelo, plantilla antes que LLM, entrenamiento local antes que Azure ML, `docker compose` antes
   que despliegue en la nube. En los cuatro casos la versión simple **se construye y se conserva**, no
   se salta.
4. **Único riesgo de sobredimensionamiento identificado: Azure AI Search.** Su justificación descansa
   íntegramente en que exista documentación interna indexable (ASSUMPTION-008), que **no está
   confirmada**. Si no existe, mantenerlo en el stack sería complejidad sin propósito. Está registrado
   como bloqueo explícito de la Fase 9.

## 15. Decisiones diferidas

Se documentan aquí para que no se tomen implícitamente durante la implementación:

| Tema | Se decide en | Motivo del aplazamiento |
|---|---|---|
| Servicio de cómputo en Azure (App Service / Container Apps / AKS) | Fase 12–13 | Requiere requisitos reales de carga y presupuesto |
| Inferencia en línea vs. solo por lotes | Fase 5–6 | Depende del tiempo de cálculo real y del uso |
| Particionamiento o extensión de series temporales en PostgreSQL | Fase 2, si el volumen lo exige | No justificado con el volumen de referencia |
| Caché de respuestas de la API | Cuando exista evidencia de latencia | Evitar complejidad prematura |
| Multi-ubicación / multi-almacén | Fase posterior | ASSUMPTION-006 |
| Modelo analítico dedicado para Power BI (más allá de vistas) | Fase 11 | Depende del volumen y del comportamiento del informe |

## 16. Etapa 2 — arquitectura de implementación

*Añadido el 2026-09-30. Decisiones: `DT-043` (estructura), `ACEPTADA` el 2026-09-30, y `DT-047` (orden),
`ACEPTADA` en cuanto a U1 y `PROPUESTA` para U2–U6.
Lo descrito aquí está **diseñado**; nada está implementado (actualización del 2026-10-01: U1,
`backend/app/supply_engine`, está implementada; el resto sigue diseñado).*

### 16.1 Estado real del que se parte

| Existe | No existe |
|---|---|
| Documentación de las Etapas 0 y 1 | `backend/`, `frontend/`, `ml/`, `infra/`, `.github/workflows/` |
| Generador de datos sintéticos (`data/synthetic/`), terminado: `generator_version` 0.4.0, 582 pruebas | Base de datos, esquema, migraciones |
| Dataset `ds-6c8ad65b4999` en `data/synthetic/output/` (no versionado), validado por C8 (51/51) | API, motor, forecast, interfaz, integraciones de Azure |
| Única dependencia externa del código: PyYAML (generador) | Archivo de dependencias del proyecto (ver *Problemas conocidos* de `project/status.md`) |

El generador es un sistema **upstream**: el sistema principal consume su **contrato** (los CSV y el
manifiesto), nunca su código.

### 16.2 Componentes

| Componente (§3) | Paquete | Responsabilidad | Depende de | Se crea en |
|---|---|---|---|---|
| `supply_engine` | `backend/app/supply_engine/` | Reglas V1, puras y deterministas (`docs/06` §16) | Solo la biblioteca estándar | U1 |
| Ingesta y validación | `backend/app/ingestion/` | Dataset → PostgreSQL con validación previa y posterior (`docs/04` §9.5) | `db` | U2 |
| Repositorios / acceso a datos | `backend/app/db/` | Conexión, migraciones SQL versionadas, consultas parametrizadas | Controlador de PostgreSQL | U2 |
| `forecast_service` | `backend/app/forecasting/` | `ForecastProvider` y baselines (`docs/05` §19) | Biblioteca estándar | U3 |
| Servicios de aplicación (batch) | `backend/app/runs/` | Ejecuciones de forecast y de recomendaciones: leer, llamar, persistir con trazabilidad | `db`, `forecasting`, `supply_engine` | U3–U4 |
| Routers + Auth | `backend/app/api/` | Contrato HTTP de solo lectura en V1 (`docs/07` §7), autenticación y roles | `db` | U5 |
| `genai_service` | `backend/app/genai/` | Contexto de explicación, `TextGenerator` (plantilla primero), verificación de cifras (`docs/09` §14) | Nada con escritura en la base | U6 |
| Interfaz | `frontend/` | Vistas de `docs/08` §11 | API | Fase 7 |
| Entrenamiento y evaluación | `ml/` | Backtesting, Nivel 1 y Nivel 2 | `app.forecasting`, `app.supply_engine` | Fase 5 |

Los «servicios de aplicación» y los «repositorios» de §3 **no** se convierten en carpetas genéricas:
el único caso de uso con orquestación real —las ejecuciones batch— vive en `runs/`, y las consultas
viven en `db/` agrupadas por entidad. Las lecturas de la API llaman a esas consultas directamente.
Cuando aparezca un segundo caso de uso que lo justifique, se revisa.

### 16.3 Flujo de la Etapa 2

```mermaid
flowchart LR
    DS[(dataset 0.4.0<br/>CSV + manifest)] -->|ingestion| PG[(PostgreSQL<br/>un linaje por base)]
    PG -->|consumo ≤ as_of| FC[forecasting<br/>ForecastProvider]
    FC -->|forecasts persistidos| PG
    PG -->|inventario, órdenes, recepciones,<br/>consumo, forecast| RUN[runs<br/>ejecución de recomendaciones]
    RUN -->|entradas puras| SE[[supply_engine]]
    SE -->|resultado + desglose| RUN
    RUN -->|recommendations +<br/>calculation_runs| PG
    PG --> API[api · solo lectura] --> UI[frontend]
    PG --> PBI[vistas → Power BI]
    API -->|cifras ya calculadas| GEN[genai · explica]
```

Tres flechas que **no** existen: `genai → PG` (sin escritura), `genai → supply_engine` (el LLM no
invoca el cálculo) y `demand → forecasting/supply_engine` (la demanda latente no entra al cálculo).

### 16.4 Reglas de dependencia (verificables por prueba)

1. `supply_engine` importa **solo** la biblioteca estándar. Una prueba recorre sus imports.
2. Nada en `backend/` importa `data.synthetic`. La ingesta lee archivos, no módulos.
3. `api` no importa `supply_engine` ni `forecasting`: en V1 lee resultados persistidos; recalcular
   es una ejecución batch explícita (§5.2).
4. `genai` no recibe una conexión con permisos de escritura ni ninguna función de cálculo.
5. Nada importa `api`.

### 16.5 Puertos y dobles locales

Toda dependencia externa tiene una implementación local con la que el sistema arranca y se prueba
sin red y sin credenciales (`DT-003`, RNF-006).

| Puerto | Paquete | Local / doble | Real (fase) |
|---|---|---|---|
| `ForecastProvider` | `forecasting` | Baselines en proceso | Endpoint de Azure ML (6) |
| `TextGenerator` | `genai` | Plantilla determinista (`DT-018`) | Azure OpenAI (10) |
| `DocumentRetriever` | `genai` | Índice en memoria para pruebas | Azure AI Search (9), **si existe corpus** |
| `TokenValidator` *(nuevo, `DT-043`)* | `api` | Validador de desarrollo con identidades de prueba; solo en local y en pruebas, **se niega a arrancar en cualquier entorno desplegado** | Microsoft Entra ID (8) |
| `SecretProvider` | configuración | Variables de entorno | Almacén gestionado (`DT-022`) |
| `DataSource` | `ingestion` | Directorio de un dataset publicado | Archivos reales / ERP (futuro) |

### 16.6 Estructura de carpetas propuesta

```text
.
├── backend/                  U1 — el único proyecto Python del sistema
│   ├── pyproject.toml        U1 — Python ≥ 3.11; sin dependencias en U1; cada unidad añade las suyas con autorización
│   ├── app/
│   │   ├── supply_engine/    U1
│   │   ├── ingestion/        U2
│   │   ├── db/               U2 — incluye migrations/*.sql
│   │   ├── forecasting/      U3
│   │   ├── runs/             U3–U4
│   │   ├── api/              U5
│   │   └── genai/            U6
│   └── tests/                espejo de app/, unittest
├── frontend/                 Fase 7
├── ml/                       Fase 5
├── infra/                    U2 — solo PostgreSQL local; Azure en Fases 12–13
└── data/synthetic/           upstream terminado — no se modifica
```

**Deliberadamente ausentes:** `services/`, `managers/`, `processors/`, `orchestrators/`,
`adapters/`, `handlers/`, `repositories/`, `factories/`, `builders/`, `ports/`, `domain/` genérico.
Cada puerto vive en el paquete que lo usa. Cada carpeta se crea con la unidad que le da uso, no antes.

### 16.7 Ejecución

| Qué | Cómo | Por qué |
|---|---|---|
| Carga del dataset | Comando de línea (`python -m app.ingestion …`) | Acción de administración; no requiere API |
| Forecast y recomendaciones | Comandos batch con `as_of_date` explícito | RNF-005: independiente de la API. Sin colas ni orquestadores (`DT-005`) |
| Consulta | API de solo lectura | La lectura nunca recalcula (§5.2) |

### 16.8 Qué se ejecuta y se prueba en local

Todo. El motor, el forecast y la explicación por plantilla, sin nada instalado aparte de Python. La
ingesta y la API, con un PostgreSQL local en contenedor. Ninguna prueba necesita Azure, internet,
OpenAI, AI Search, Azure ML ni Entra ID (`docs/13` §14).

### 16.9 Qué no se construye en esta fase

Ni la API completa, ni la interfaz, ni Power BI, ni RAG, ni autenticación real, ni CI/CD, ni
recursos de Azure, ni entrenamiento. Esta fase deja **contratos y orden**; la primera línea de código
llega con la autorización de U1 (`DT-047`).
