# ADR-NNN — [Título breve de la decisión]

- **Fecha:** AAAA-MM-DD
- **Estado:** `PROPUESTA` | `ACEPTADA` | `RECHAZADA` | `SUPERSEDIDA por ADR-NNN` | `PENDIENTE`
- **Fase del roadmap:** [Fase N]
- **Afecta a:** [documentos y módulos afectados]

## Decisión

Enunciado claro y en una o dos frases de qué se decide. En presente y en afirmativo.

## Contexto

Qué situación obliga a decidir. Qué restricciones existen (técnicas, de negocio, de plazo, de costo).
Qué información se tiene y cuál falta.

## Alternativas consideradas

| Alternativa | Ventajas | Inconvenientes |
|---|---|---|
| (a) | | |
| (b) | | |
| (c) | | |

Incluir siempre "no hacer nada" cuando sea una opción real.

## Razón

Por qué se elige esta alternativa y no las otras. Qué criterio pesó más. Si la decisión se apoya en
documentación externa, citarla y registrarla en `knowledge/sources.md`.

## Consecuencias

**Positivas:** qué se gana.

**Negativas o costos aceptados:** qué se pierde o qué complejidad se asume conscientemente.

**Qué habría que revisar si cambian las circunstancias:** condición que invalidaría esta decisión.

## Estado y seguimiento

- Si es `PROPUESTA`: qué hace falta para confirmarla y en qué fase se decidirá.
- Si es `PENDIENTE`: por qué se aplaza deliberadamente.
- Si es `SUPERSEDIDA`: qué ADR la sustituye y por qué.

---

## Cómo usar esta plantilla

1. Copiar como `ADR-NNN-titulo-corto.md` en esta carpeta, o añadir la entrada directamente en
   `docs/15-decisiones-tecnicas.md` si es una decisión breve.
2. **No marcar como `ACEPTADA` lo que todavía es una hipótesis.** Usar `PROPUESTA` o `PENDIENTE`.
3. Una decisión revertida no se borra: se marca `SUPERSEDIDA` y se enlaza a la nueva. El registro de
   lo que se descartó, y por qué, evita volver a debatirlo sin información nueva.
4. Registrar el ADR **en el mismo cambio** en que se toma la decisión, no después.
