import type { RecommendationExplanation } from '../../api/types';

/** Template generators of U6 (DT-068 point 10): `template/<version>`. Any other generator is a language model
 * (U13, DT-101: `azure-openai/<deployment>`) whose text passed the same figure verification (DT-069). */
export function isTemplateGenerator(generator: string): boolean {
  return generator.startsWith('template/');
}

/** Explanation of U6 and U13 (DT-068, DT-101, DT-070 point 14). Not a chat and not an assistant. */
export function ExplanationPanel({ explanation }: { explanation: RecommendationExplanation }) {
  const body = explanation.explanation;
  return (
    <section className="section" aria-labelledby="explicacion">
      <h2 id="explicacion" className="section__title">
        Explicación
      </h2>
      {body.status === 'VERIFIED' && body.narrative ? (
        <>
          <p className="narrative">{body.narrative}</p>
          <p className="page__note">
            {isTemplateGenerator(body.generator) ? (
              <>
                Texto generado por plantilla determinista (<code>{body.generator}</code>); cada
                cifra coincide con el desglose.
              </>
            ) : (
              <>
                Texto redactado por un modelo de lenguaje (<code>{body.generator}</code>) a partir
                de las cifras ya calculadas; el sistema comprobó que cada cifra coincide con el
                desglose.
              </>
            )}
          </p>
        </>
      ) : null}
      {body.status === 'DEGRADED' ? (
        <div className="notice" role="status">
          <p className="notice__title">
            <strong>Explicación no disponible.</strong> El texto no superó la verificación de cifras
            (<code>{body.warning ?? 'NARRATIVE_UNVERIFIED'}</code>); el desglose y la procedencia
            siguen siendo válidos.
          </p>
        </div>
      ) : null}
      {body.status === 'NOT_APPLICABLE' ? (
        <>
          <p>El motor no pudo calcular esta evaluación por estos motivos:</p>
          <ul>
            {explanation.reason_details.map((reason) => (
              <li key={reason.code}>
                {reason.text} <code>{reason.code}</code>
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}
