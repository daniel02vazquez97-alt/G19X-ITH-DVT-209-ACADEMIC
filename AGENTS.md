# AGENTS.md — Protocolo de trabajo para agentes de IA

Complementa a `CLAUDE.md`. Mientras `CLAUDE.md` define **qué reglas rigen el proyecto**,
este archivo define **cómo debe comportarse un agente durante una sesión de trabajo**.

Principio rector: **trabajo incremental, verificable y sin sobreingeniería.**

---

## 1. Cómo comenzar una sesión

Toda sesión empieza igual, sin excepciones:

1. Leer `CLAUDE.md` completo.
2. Leer `AGENTS.md` (este archivo).
3. Leer `project/status.md` — indica la etapa actual, lo último decidido y los pendientes.
4. Leer `project/roadmap.md` para ubicar la fase en curso y su criterio de finalización.
5. Inspeccionar el estado **real** del repositorio (archivos, ramas, cambios sin commitear).
   Lo documentado y lo real pueden diferir; gana lo real, y la diferencia se reporta.
6. Confirmar en una frase qué se va a hacer y qué **no**, antes de tocar nada.

### Orden de lectura por tipo de tarea

| Tarea | Leer además |
|---|---|
| Cambios en la API | `docs/07-api.md`, `docs/03-arquitectura.md`, `docs/10-seguridad.md` |
| Cambios de datos / esquema | `docs/04-modelo-datos.md`, `knowledge/glossary.md` |
| Trabajo de ML | `docs/05-motor-predictivo.md`, `knowledge/assumptions.md` |
| Reglas de abastecimiento | `docs/06-motor-abastecimiento.md`, `knowledge/business-rules.md` |
| Frontend | `docs/08-frontend.md`, `docs/07-api.md` |
| IA generativa | `docs/09-ia-generativa.md`, `docs/10-seguridad.md` |
| CI/CD, contenedores | `docs/12-devops.md`, `docs/13-testing.md` |
| Cualquier decisión estructural | `docs/15-decisiones-tecnicas.md` |

## 2. Cómo investigar el código existente

- Explorar antes de escribir. Buscar si la funcionalidad ya existe con otro nombre.
- Leer un archivo **completo** antes de modificarlo. Nunca editar sobre un fragmento parcial ni
  reescribir un archivo a partir de una salida truncada.
- Seguir las convenciones que ya existen en el repositorio por encima de preferencias propias.
- Identificar quién consume lo que se va a cambiar (llamadas, imports, contratos de API) antes de cambiarlo.
- Si algo parece un error pero está fuera del alcance de la tarea: documentarlo, no arreglarlo de paso.

## 3. Cómo investigar documentación externa

Se investiga **antes** de implementar, no después de que algo falle.

Orden de autoridad:

1. Microsoft Learn (Azure, Entra ID, Power BI).
2. Documentación oficial del proyecto (FastAPI, React, PostgreSQL, Docker, scikit-learn, statsmodels).
3. Documentación oficial de GitHub y de Docker.
4. Publicaciones académicas o literatura reconocida de gestión de inventarios, cuando se trate de
   fórmulas o métodos (p. ej. Silver, Pyke & Thomas; Hyndman & Athanasopoulos para forecasting).

**No son fuente de decisión:** blogs sin autoría técnica, tutoriales sin fecha, contenido generado
por IA, respuestas de foros sin referencia oficial. Pueden orientar la búsqueda, no fundamentar la decisión.

Reglas:

- Toda fuente que sustente una decisión se registra en `knowledge/sources.md` con URL y fecha de consulta.
- Verificar que la documentación corresponde a la **versión vigente** del servicio o librería.
- Si dos fuentes oficiales se contradicen, se documenta la contradicción y se pregunta.

## 4. Cómo planificar cambios

Antes de escribir código o documentación, producir un plan corto que responda:

1. **Objetivo** — qué problema concreto se resuelve.
2. **Alcance** — qué archivos se tocan y cuáles explícitamente no.
3. **Supuestos** — qué se está dando por cierto sin confirmación (van a `knowledge/assumptions.md`).
4. **Verificación** — cómo se sabrá que funcionó (pruebas, criterio de aceptación del requisito).
5. **Riesgos** — qué podría romperse.

El plan debe ser **el mínimo suficiente**. Si el plan introduce una capa, un servicio o un patrón
que el alcance actual no exige, hay que quitarlo del plan.

Un plan que toca más de un área grande (p. ej. base de datos + API + frontend a la vez) se divide.

## 5. Cómo implementar

- Un cambio, un propósito. Nada de "ya que estaba aquí".
- Empezar por el camino más simple que satisfaga el criterio de aceptación.
- Mantener el sistema **ejecutable en todo momento**; no dejar el repositorio en estado intermedio roto.
- Respetar la separación de capas: predicción ≠ reglas de negocio ≠ IA generativa.
- Sin secretos en el código. Sin datos de negocio inventados. Sin dependencias nuevas no justificadas.
- Si a mitad de la implementación se descubre que el plan era incorrecto: **parar**, reportar y replantear.
  No improvisar una solución mayor sobre la marcha.

## 6. Cómo probar

- Ejecutar las pruebas relevantes **después de cada cambio**, no solo al final.
- Añadir pruebas para el comportamiento nuevo y para el caso límite que motivó un arreglo.
- Para lógica determinística de abastecimiento: pruebas exactas con valores esperados calculados a mano.
- Para ML: pruebas de propiedades e invariantes, no de métricas exactas.
- Sin red en pruebas unitarias: los servicios de Azure se sustituyen por dobles.
- **No se reporta trabajo terminado con pruebas fallando.** Si una prueba falla y no puede
  arreglarse dentro del alcance, se reporta como bloqueo.

## 7. Cómo documentar

En el **mismo** cambio, no después:

- ¿Cambió una decisión técnica? → actualizar `docs/15-decisiones-tecnicas.md` (nuevo ADR o cambio de estado).
- ¿Se asumió algo? → `knowledge/assumptions.md` con `ASSUMPTION-NNN`.
- ¿Apareció un término de dominio nuevo? → `knowledge/glossary.md`.
- ¿Cambió una regla de negocio? → `knowledge/business-rules.md`, indicando si está confirmada,
  propuesta o pendiente de validación.
- ¿Cambió el contrato de la API o el modelo de datos? → `docs/07-api.md` / `docs/04-modelo-datos.md`.
- Siempre: actualizar `project/status.md` al cerrar el bloque de trabajo.

La documentación describe lo que **es**, no lo que se pretende que sea. Nada de documentar
funcionalidad inexistente en tiempo presente.

## 8. Cómo reportar resultados

Al terminar, un reporte breve con estas siete secciones (sin narrar cada operación intermedia):

1. **Archivos creados**
2. **Archivos modificados**
3. **Decisiones importantes** (con su ID de ADR si aplica)
4. **Supuestos realizados** (con su ID)
5. **Problemas encontrados**
6. **Elementos pendientes de validación**
7. **Próximo paso recomendado**

Reportar también lo que **no** se hizo y por qué, si formaba parte de lo esperado.
No exagerar el estado de completitud: "documentado" ≠ "implementado" ≠ "probado" ≠ "desplegado".

## 9. Cuándo pedir confirmación al usuario

**Detenerse y preguntar** ante cualquiera de estos casos:

- Eliminar o reemplazar funcionalidad existente.
- Cambiar una decisión arquitectónica ya registrada como `ACEPTADA`.
- Añadir una tecnología, servicio o dependencia relevante al stack.
- Aprovisionar recursos reales de Azure o cualquier acción con costo económico.
- Crear, rotar o manipular credenciales.
- Hacer commit, push, merge, o abrir/cerrar un Pull Request.
- Ejecutar migraciones destructivas o cualquier operación irreversible sobre datos.
- Definir un parámetro de negocio (nivel de servicio, costo de faltante, política de compra)
  que el negocio no haya especificado.
- Encontrar una contradicción entre documentos, o entre la instrucción recibida y lo documentado.
- Ampliar el alcance más allá de lo solicitado.

**No** hace falta preguntar para: leer archivos, explorar el repositorio, investigar documentación
oficial, crear documentación dentro del plan acordado, escribir pruebas, o proponer alternativas.

### Si el usuario no está disponible

Ejecutar la interpretación más razonable y **conservadora**, dejarla escrita de forma visible al
inicio del reporte y marcarla como pendiente de validación. Ante una acción irreversible sin
respuesta posible: preparar todo lo previo y **detenerse ahí**.

## 10. Antipatrones a evitar

| Antipatrón | En su lugar |
|---|---|
| Crear una arquitectura "para el futuro" que hoy nadie usa | Construir lo que la fase actual exige |
| Inventar cifras de negocio para completar un ejemplo | Marcar el hueco como pendiente del negocio |
| Usar el LLM para calcular inventario | Calcular con reglas; el LLM solo explica |
| Refactorizar de paso mientras se arregla un bug | Reportar la deuda, arreglar solo el bug |
| Suponer cómo funciona una API de Azure | Verificar en Microsoft Learn |
| Declarar terminado con pruebas en rojo | Reportar el bloqueo |
| Documentar como hecho lo que solo está diseñado | Distinguir diseñado / implementado / probado |
| Hacer commit sin autorización | Preparar el cambio y reportarlo |
