# Fuentes consultadas

**Estado:** Versión 1.0 — Etapa 0 · **Fecha:** 2026-09-04 · **Versión 1.1** — revisada en la auditoría de Etapa 0.1

Registro de las fuentes externas utilizadas para fundamentar decisiones técnicas, conforme a la regla
de investigación de `AGENTS.md` §3.

**Orden de autoridad:** Microsoft Learn → documentación oficial de cada tecnología → documentación
oficial de GitHub y Docker → literatura académica o de referencia. Blogs, tutoriales sin autoría y
contenido generado por IA **no son fuente de decisión**.

---

## 1. Azure OpenAI Service

| Fuente | URL | Qué sustenta |
|---|---|---|
| Azure OpenAI in Microsoft Foundry Models — ciclo de vida de versiones de API | https://learn.microsoft.com/en-us/azure/foundry/openai/api-version-lifecycle | El servicio se expone hoy como *Azure OpenAI in Microsoft Foundry Models*, con una API `v1` en disponibilidad general que **no requiere** el parámetro `api-version` y admite autenticación por clave o por Microsoft Entra ID |
| Documentación de Microsoft Foundry | https://learn.microsoft.com/en-us/azure/ai-services/openai/ | Contexto general del servicio |

**Consecuencia para el proyecto:** confirma la regla de `CLAUDE.md` §11 — la superficie de Azure
OpenAI ha cambiado de forma relevante, por lo que **no debe implementarse de memoria**. Verificar la
documentación vigente al llegar a la Fase 10. Registrado en `docs/09-ia-generativa.md`.

## 2. Azure AI Search

| Fuente | URL | Qué sustenta |
|---|---|---|
| RAG y IA generativa en Azure AI Search | https://learn.microsoft.com/en-us/azure/search/retrieval-augmented-generation-overview | Patrón de recuperación aumentada como arquitectura de referencia |
| Búsqueda híbrida | https://learn.microsoft.com/en-us/azure/search/hybrid-search-overview | Justificación de combinar búsqueda léxica y vectorial |
| Búsqueda vectorial | https://learn.microsoft.com/en-us/azure/search/vector-search-overview | Fundamento de la recuperación semántica |
| Desarrollo de una solución RAG — fase de recuperación | https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/rag/rag-information-retrieval | Guía de arquitectura para la fase de recuperación |

**Consecuencia:** sustenta la decisión de usar búsqueda híbrida (`docs/09-ia-generativa.md` §5), dado
que las consultas del dominio combinan identificadores exactos (SKU, códigos de proveedor) con
lenguaje natural.

## 3. Azure Machine Learning

| Fuente | URL | Qué sustenta |
|---|---|---|
| MLflow y Azure Machine Learning | https://learn.microsoft.com/en-us/azure/machine-learning/concept-mlflow | Seguimiento de experimentos y registro de modelos compatible con MLflow |
| Endpoints en línea para inferencia en tiempo real | https://learn.microsoft.com/en-us/azure/machine-learning/concept-endpoints-online | Opción de inferencia en línea mediante *managed online endpoints* |
| Registrar y trabajar con modelos | https://learn.microsoft.com/en-us/azure/machine-learning/how-to-manage-models | Registro versionado de modelos |
| Monitoreo de modelos en producción | https://learn.microsoft.com/en-us/azure/machine-learning/concept-model-monitoring | Señales de deriva de datos y degradación de desempeño |
| Monitorear el desempeño del modelo en producción | https://learn.microsoft.com/en-us/azure/machine-learning/how-to-monitor-model-performance | Procedimiento de monitoreo |

**Consecuencia:** sustenta la estrategia de versionado, despliegue y monitoreo de
`docs/05-motor-predictivo.md` §11–15 y `docs/14-mantenimiento.md` §4–5. Confirma que no es necesario
construir un MLOps propio.

## 4. Microsoft Entra ID

| Fuente | URL | Qué sustenta |
|---|---|---|
| Configurar aplicaciones de API web protegidas | https://learn.microsoft.com/en-us/entra/identity-platform/scenario-protected-web-api-overview | Patrón de API protegida |
| Verificar scopes y app roles en una API protegida | https://learn.microsoft.com/en-us/entra/identity-platform/scenario-protected-web-api-verification-scope-app-roles | Validación de scopes y app roles para la autorización por rol |
| Exponer scopes en una API protegida | https://learn.microsoft.com/en-us/entra/identity-platform/scenario-protected-web-api-expose-scopes | Registro de la API y exposición de su scope |
| Flujo de código de autorización OAuth 2.0 | https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow | Flujo elegido para la SPA (código de autorización con PKCE) |
| Scopes y permisos en la plataforma de identidad | https://learn.microsoft.com/en-us/entra/identity-platform/scopes-oidc | Modelo de permisos |

**Consecuencia:** sustenta `docs/10-seguridad.md` §2–3: flujo de autenticación, validación del token
(firma, `iss`, `aud`, vigencia) y autorización mediante app roles.

## 5. GitHub Actions y despliegue

| Fuente | URL | Qué sustenta |
|---|---|---|
| Configurar OpenID Connect en Azure | https://docs.github.com/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-azure | Acceso de GitHub Actions a Azure sin secretos de larga vida |
| Autenticarse en Azure desde GitHub Actions con OpenID Connect | https://learn.microsoft.com/en-us/azure/developer/github/connect-from-azure-openid-connect | Configuración de credenciales federadas del lado de Azure |

**Consecuencia:** sustenta la decisión de usar OIDC con credenciales federadas en lugar de secretos
persistentes (`docs/12-devops.md` §4.3, `docs/10-seguridad.md` §8).

## 6. Power BI y PostgreSQL

| Fuente | URL | Qué sustenta |
|---|---|---|
| Conector PostgreSQL de Power Query | https://learn.microsoft.com/en-us/power-query/connectors/postgresql | Conectividad nativa entre Power BI y PostgreSQL |
| DirectQuery en Power BI: cuándo usarlo, limitaciones y alternativas | https://learn.microsoft.com/en-us/power-bi/connect-data/desktop-directquery-about | Comparación Import vs. DirectQuery |
| Guía de modelado con DirectQuery | https://learn.microsoft.com/en-us/power-bi/guidance/directquery-model-guidance | Restricciones de modelado en DirectQuery |

**Consecuencia:** sustenta `DT-014` (modo *Import* como opción por defecto, con DirectQuery reservado
a un caso justificado) en `docs/11-power-bi.md` §2.

## 7. Gestión de inventarios (literatura de dominio)

Las fórmulas de `docs/06-motor-abastecimiento.md` (demanda durante el lead time, stock de seguridad
con variabilidad de demanda y de lead time, punto de reorden, nivel objetivo en revisión periódica)
son formulaciones estándar de la teoría de control de inventarios, documentadas en la literatura de
referencia del área.

Obras de referencia habituales del campo:

- Silver, E. A., Pyke, D. F., & Thomas, D. J. — *Inventory and Production Management in Supply Chains*.
  Tratamiento estándar de políticas de revisión continua y periódica, stock de seguridad y lead time estocástico.
- Hyndman, R. J., & Athanasopoulos, G. — *Forecasting: Principles and Practice*. Referencia sobre
  validación temporal, métricas de error (incluida MASE) y baselines de pronóstico.
- Chopra, S., & Meindl, P. — *Supply Chain Management*. Tratamiento de nivel de servicio, tasa de
  satisfacción y su relación con el inventario.

**Advertencia registrada:** estas fórmulas son **puntos de partida verificables**, no fórmulas
empresariales definitivas de esta organización. Su estado es `PROPUESTA` hasta que se validen con
datos y con los parámetros que aporte el negocio (`docs/06-motor-abastecimiento.md` §2 y §12).

## 7bis. Pronóstico: métricas y intervalos de predicción

*Añadidas en la revisión de Etapa 0.1 (consulta: 2026-09-04).*

| Fuente | URL | Qué sustenta |
|---|---|---|
| Hyndman & Athanasopoulos, *Forecasting: Principles and Practice* (3.ª ed.), §5.8 "Evaluating point forecast accuracy" | https://otexts.com/fpp3/accuracy.html | Definiciones de MAE, RMSE, MAPE, MASE y RMSSE; los problemas de MAPE (indefinida con valores cero, penalización asimétrica); que los errores escalados se definen contra el naïve —o el naïve estacional en series estacionales— y por eso permiten comparar entre series; la necesidad de evaluar sobre datos no vistos |
| Hyndman & Athanasopoulos, *Forecasting: Principles and Practice* (3.ª ed.), §5.5 "Prediction intervals" | https://otexts.com/fpp3/prediction-intervals.html | Que los intervalos multi-horizonte se ensanchan con `h`; que la relación `σ̂_h = σ̂·√h` está tabulada **para el método naïve** y **bajo el supuesto explícito de residuos no correlacionados** y varianza constante; que la normalidad es un supuesto adicional que puede sustituirse por bootstrap |

**Consecuencia para el proyecto — es el fundamento de dos correcciones de la Etapa 0.1:**

1. **`DT-021`**: MAPE queda descartada como métrica de decisión (indefinida con demanda cero, que en
   este catálogo es frecuente y esperada; y asimétrica, lo que en abastecimiento sesga hacia el
   desabasto). MASE y RMSSE son candidatas válidas por ser escaladas y comparables entre series.
2. **`DT-010`**: escalar el error de un paso por `√L` **no es una identidad general**. La fuente lo
   deriva para un método concreto y bajo supuestos que los errores multi-horizonte suelen incumplir.
   De ahí que la metodología del stock de seguridad quede pendiente y deba estimarse por backtesting
   **al horizonte del intervalo de protección**.

## 7ter. Literatura sobre la relación entre precisión del pronóstico e indicadores de inventario

| Fuente | URL | Qué sustenta |
|---|---|---|
| *Bridging Forecast Accuracy and Inventory KPIs: A Simulation-Based Software Framework* (arXiv) | https://arxiv.org/abs/2601.21844 | Que la precisión del pronóstico y los indicadores de inventario **no se corresponden de forma directa**, y que evaluar el efecto de un forecast sobre el abastecimiento exige simulación sobre el sistema completo |
| *Nonparametric Safety Stock Dimensioning: A Data-Driven Approach* (arXiv) | https://arxiv.org/abs/2511.04616 | Existencia de enfoques no paramétricos para dimensionar el stock de seguridad a partir de la distribución empírica del error, sin supuesto de normalidad |

**Consecuencia:** sustenta `DT-020` (evaluación en dos niveles y comparación end-to-end) y la
alternativa (d) de `DT-010` (cuantiles empíricos). **Advertencia de uso:** estas dos referencias son
literatura de apoyo, no documentación oficial ni obra canónica; se citan como evidencia de que el
problema está reconocido en la literatura, **no** como fundamento único de ninguna decisión. Ninguna
decisión del proyecto se apoya exclusivamente en ellas.

## 8. Documentación de tecnologías del stack

Consultada como referencia general; se verificará la versión vigente al implementar cada fase:

| Tecnología | Documentación oficial |
|---|---|
| FastAPI | https://fastapi.tiangolo.com |
| React | https://react.dev |
| PostgreSQL | https://www.postgresql.org/docs/ |
| Docker | https://docs.docker.com |
| MSAL para React | Documentación de la plataforma de identidad de Microsoft |

---

## Regla de mantenimiento

1. Toda fuente que sustente una decisión se registra aquí con URL y fecha de consulta.
2. Antes de implementar una integración de Azure, **volver a verificar** la documentación: las APIs y
   los nombres de servicio cambian (el caso de Azure OpenAI en §1 es un ejemplo real ocurrido durante
   la vida de este proyecto).
3. Si una fuente contradice una decisión registrada, se documenta la contradicción y se solicita
   validación antes de actuar.
4. No se registran aquí blogs, tutoriales ni contenido sin autoría verificable, aunque hayan servido
   para orientar una búsqueda.
