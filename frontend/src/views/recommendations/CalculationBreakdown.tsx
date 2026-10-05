// CalculationBreakdown (US-074, DT-070 point 15): two levels. Main: `facts[].display` of the server
// with its units. Technical details: every other term of `calculation_inputs.breakdown` in its exact
// representation (integer, decimal, `"p/q"` or 28-digit `Decimal`), never recalculated.
import type { CalculationInputs, EffectiveLine, RecommendationExplanation } from '../../api/types';
import { formatCalendarDate, formatTimestamp } from '../../format/dates';
import { formatExact } from '../../format/numbers';
import { factLabel, factUnit } from './vocabulary';

type Fact = RecommendationExplanation['facts'][number];

interface CalculationBreakdownProps {
  facts: readonly Fact[];
  inputs: CalculationInputs;
  unitOfMeasure: string | null;
  policySnapshot: Record<string, unknown>;
  engineVersion: string;
  generatedAt: string;
}

function snapshotValue(value: unknown): string {
  return typeof value === 'string' ? value : JSON.stringify(value);
}

function EffectiveLines({ lines }: { lines: readonly EffectiveLine[] }) {
  if (lines.length === 0) {
    return <span className="muted">ninguna</span>;
  }
  return (
    <ul className="code-list">
      {lines.map((line) => (
        <li key={`${line.purchase_order_id}-${line.item_id}`}>
          orden {line.purchase_order_id} · línea {line.item_id} · llegada{' '}
          {formatCalendarDate(line.expected_on)} · pendiente <code>{line.quantity_pending}</code>
        </li>
      ))}
    </ul>
  );
}

export function CalculationBreakdown({
  facts,
  inputs,
  unitOfMeasure,
  policySnapshot,
  engineVersion,
  generatedAt,
}: CalculationBreakdownProps) {
  const factKeys = new Set(facts.map((fact) => fact.key));
  const approximate = new Set(inputs.approximate_terms);
  const terms = Object.entries(inputs.breakdown).filter(([key]) => !factKeys.has(key));

  return (
    <section className="section" aria-labelledby="desglose">
      <h2 id="desglose" className="section__title">
        Desglose del cálculo
      </h2>
      {facts.length === 0 ? (
        <p className="page__note">Esta evaluación no tiene cifras principales.</p>
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <caption className="visually-hidden">Cifras principales del cálculo</caption>
            <thead>
              <tr>
                <th scope="col">Término</th>
                <th scope="col" className="numeric">
                  Valor
                </th>
              </tr>
            </thead>
            <tbody>
              {facts.map((fact) => (
                <tr key={fact.key}>
                  <th scope="row">
                    {factLabel(fact.key)} <code className="muted">{fact.key}</code>
                  </th>
                  <td className="numeric">
                    {fact.display} {factUnit(fact.unit, unitOfMeasure)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <details className="technical">
        <summary>Detalles técnicos del cálculo</summary>
        <p className="page__note">
          Valores exactos tal como los guardó el motor: entero, decimal, fracción <code>p/q</code> o
          decimal aproximado de 28 cifras. Nada se recalcula en la interfaz.
        </p>
        <div className="table-wrap">
          <table className="data-table">
            <caption className="visually-hidden">Términos del desglose</caption>
            <thead>
              <tr>
                <th scope="col">Término</th>
                <th scope="col">Valor exacto</th>
              </tr>
            </thead>
            <tbody>
              {terms.map(([key, value]) => (
                <tr key={key}>
                  <th scope="row">
                    <code>{key}</code>
                  </th>
                  <td>
                    {Array.isArray(value) ? (
                      <EffectiveLines lines={value} />
                    ) : (
                      <>
                        <code>{formatExact(value)}</code>
                        {approximate.has(key) ? (
                          <span className="muted"> (aproximado, 28 cifras)</span>
                        ) : null}
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <dl className="facts facts--compact">
          <dt>Forecast usado</dt>
          <dd>
            {inputs.forecast ? (
              <>
                #{inputs.forecast.forecast_id} de la ejecución #{inputs.forecast.forecast_run_id} ·{' '}
                {inputs.forecast.model
                  ? `${inputs.forecast.model.name} ${inputs.forecast.model.version}`
                  : '—'}{' '}
                · <code>{inputs.forecast.method_used}</code> ·{' '}
                <code>{inputs.forecast.confidence_flag}</code> · desde{' '}
                {formatCalendarDate(inputs.forecast.start_date)} · semanas:{' '}
                <code>{inputs.forecast.weekly_quantities.join(' · ')}</code>
              </>
            ) : (
              'ninguno'
            )}
          </dd>
          <dt>Política</dt>
          <dd>
            {Object.entries(policySnapshot).map(([key, value]) => (
              <span key={key} className="policy-term">
                <code>
                  {key} = {snapshotValue(value)}
                </code>{' '}
              </span>
            ))}
          </dd>
          <dt>Huella de las entradas</dt>
          <dd>
            <code className="hash">{inputs.input_sha256}</code>
          </dd>
          <dt>Motor</dt>
          <dd>
            {engineVersion} · calculado el {formatTimestamp(generatedAt)}
          </dd>
        </dl>
      </details>
    </section>
  );
}
