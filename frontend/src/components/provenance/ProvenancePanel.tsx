import { Link } from 'react-router';
import type { ForecastProvenance, RecommendationProvenance } from '../../api/types';
import { formatCalendarDate } from '../../format/dates';
import { RoleGate } from '../../roles/RoleGate';
import { toRun } from '../../routes/paths';
import { NoticeBanner } from '../NoticeBanner';

type Provenance = RecommendationProvenance | ForecastProvenance;

function RunReference({ runId }: { runId: number }) {
  // The run detail is a link only for PLANNER and ADMIN (DT-070 point 1).
  return (
    <RoleGate resource="runs" fallback={<>#{runId}</>}>
      <Link to={toRun(runId)}>#{runId}</Link>
    </RoleGate>
  );
}

/** `provenance` of DT-066, with its notices always visible (DT-070 point 16). */
export function ProvenancePanel({ provenance }: { provenance: Provenance }) {
  return (
    <section className="provenance" aria-label="Procedencia">
      <NoticeBanner notices={provenance.notices} />
      <dl className="facts facts--compact">
        <dt>Corte</dt>
        <dd>{formatCalendarDate(provenance.as_of_date)}</dd>
        <dt>Ejecución</dt>
        <dd>
          <RunReference runId={provenance.run_id} />
        </dd>
        <dt>Datos</dt>
        <dd>
          <code>{provenance.dataset_version}</code>
          {provenance.generator_version ? ` · generador ${provenance.generator_version}` : null}
          {provenance.data_origin ? (
            <>
              {' '}
              · <code>{provenance.data_origin}</code>
            </>
          ) : null}
        </dd>
        {'engine_version' in provenance ? (
          <>
            <dt>Motor</dt>
            <dd>
              {provenance.engine_version ?? '—'} · política{' '}
              <code>{provenance.policy_set ?? '—'}</code>
            </dd>
          </>
        ) : null}
        {'model_version' in provenance ? (
          <>
            <dt>Modelo</dt>
            <dd>
              {provenance.model_version
                ? `${provenance.model_version.name} ${provenance.model_version.version}`
                : '—'}
            </dd>
          </>
        ) : null}
      </dl>
    </section>
  );
}
