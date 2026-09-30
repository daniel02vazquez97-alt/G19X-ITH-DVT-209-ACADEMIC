# Vistas de arquitectura

Esta carpeta está reservada a los diagramas y vistas de detalle que complementarán
[`../03-arquitectura.md`](../03-arquitectura.md), que es el documento normativo.

## Estado

Vacía en la Etapa 0. Los diagramas principales (contexto, componentes, flujo de datos, RAG) están
integrados en `docs/03-arquitectura.md` como Mermaid, donde se leen junto a su explicación.

## Qué va aquí

Vistas que crecen demasiado para vivir dentro del documento principal:

| Documento previsto | Fase |
|---|---|
| Diagrama detallado del esquema físico de PostgreSQL | 2 |
| Diagrama de secuencia del proceso batch completo | 4 |
| Arquitectura del pipeline de ML y su despliegue en Azure ML | 5–6 |
| Arquitectura de despliegue en Azure (una vez decidido el destino) | 12–13 |
| Diagrama de red y superficie de seguridad | 13 |

## Convenciones

- **Mermaid** como formato por defecto: es texto versionable, se revisa en un diff y se renderiza en
  GitHub sin herramientas externas.
- Un diagrama por archivo, con nombre descriptivo.
- Todo diagrama lleva una explicación en prosa: un diagrama sin texto se malinterpreta.
- Los diagramas se actualizan **en el mismo cambio** en que cambia lo que describen. Un diagrama
  desactualizado es peor que no tenerlo, porque se cree.
