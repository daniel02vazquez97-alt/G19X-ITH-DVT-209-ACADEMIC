import type { RecommendationExplanation } from '../../api/types';

/** Explanation of U6 (DT-068, DT-070 point 14). Not a chat and not an assistant. */
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
            Texto generado por plantilla determinista (<code>{body.generator}</code>); cada cifra
            coincide con el desglose.
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
