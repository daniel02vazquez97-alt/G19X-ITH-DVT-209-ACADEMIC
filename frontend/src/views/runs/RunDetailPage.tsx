import { useParams } from 'react-router';
import { API_PATHS } from '../../api/paths';
import type { RunDetail } from '../../api/types';
import { useApiQuery } from '../../api/useApiQuery';
import { QueryView } from '../../components/QueryView';
import { formatCalendarDate, formatTimestamp } from '../../format/dates';

function plain(value: unknown): string {
  return typeof value === 'string' ? value : JSON.stringify(value);
}

/** Detail of a run (`GET /runs/{run_id}`), only for PLANNER and ADMIN; the route is role-gated. */
export function RunDetailPage() {
  const { runId = '' } = useParams();
  const result = useApiQuery<RunDetail>(API_PATHS.run(runId));
  return (
    <article className="page">
      <QueryView query={result}>
        {(run) => (
          <>
            <h1 className="page__title">Detalle de ejecución #{run.id}</h1>
            <dl className="facts">
              <dt>Tipo</dt>
              <dd>
                <code>{run.run_type}</code>
              </dd>
              <dt>Estado</dt>
              <dd>
                <code>{run.status}</code>
              </dd>
              <dt>Corte</dt>
              <dd>{formatCalendarDate(run.as_of_date)}</dd>
              <dt>Carga de datos</dt>
              <dd>
                #{run.data_load.id} · <code>{run.data_load.dataset_version}</code>
                {run.data_load.generator_version
                  ? ` · generador ${run.data_load.generator_version}`
                  : null}
                {run.data_load.data_origin ? (
                  <>
                    {' '}
                    · <code>{run.data_load.data_origin}</code>
                  </>
                ) : null}
              </dd>
              <dt>Versiones</dt>
              <dd>
                motor {run.versions.engine_version ?? '—'} · forecast #
                {run.versions.forecast_run_id ?? '—'} · modelo de referencia{' '}
                {run.versions.reference_model_version
                  ? `${run.versions.reference_model_version.name} ${run.versions.reference_model_version.version}`
                  : '—'}
              </dd>
              <dt>Configuración</dt>
              <dd>
                <code className="hash">{run.versions.config_sha256}</code>
              </dd>
              <dt>Inicio</dt>
              <dd>{formatTimestamp(run.started_at)}</dd>
              <dt>Fin</dt>
              <dd>{formatTimestamp(run.finished_at)}</dd>
            </dl>
            <section className="section" aria-labelledby="ejecucion-conteos">
              <h2 id="ejecucion-conteos" className="section__title">
                Conteos
              </h2>
              <dl className="facts facts--compact">
                {Object.entries(run.counts).map(([key, value]) => (
                  <div key={key} className="facts__row">
                    <dt>
                      <code>{key}</code>
                    </dt>
                    <dd>
                      <code>{plain(value)}</code>
                    </dd>
                  </div>
                ))}
              </dl>
            </section>
            {run.error ? (
              <section className="section" aria-labelledby="ejecucion-error">
                <h2 id="ejecucion-error" className="section__title">
                  Error guardado
                </h2>
                <pre className="code-block">{JSON.stringify(run.error, null, 2)}</pre>
              </section>
            ) : null}
          </>
        )}
      </QueryView>
    </article>
  );
}
