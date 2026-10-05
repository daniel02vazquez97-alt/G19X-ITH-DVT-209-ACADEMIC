import { useSearchParams } from 'react-router';
import { API_PATHS } from '../../api/paths';
import type { History } from '../../api/types';
import { useApiQuery } from '../../api/useApiQuery';
import { FilterForm, type FilterField } from '../../components/FilterForm';
import { QueryView } from '../../components/QueryView';
import { formatCalendarDate } from '../../format/dates';
import { formatDisplay, formatQuantity } from '../../format/numbers';
import { withFilters } from '../../routes/listParams';
import { yesNo } from '../labels';

const HISTORY_KEYS = ['granularity', 'date_from', 'date_to'] as const;

const FIELDS: readonly FilterField[] = [
  {
    key: 'granularity',
    label: 'Periodo',
    kind: 'select',
    options: [
      { value: '', label: 'Por defecto de la API' },
      { value: 'daily', label: 'Diario' },
      { value: 'weekly', label: 'Semanal (semanas ISO)' },
      { value: 'monthly', label: 'Mensual' },
    ],
  },
  { key: 'date_from', label: 'Desde (AAAA-MM-DD)', kind: 'text' },
  { key: 'date_to', label: 'Hasta, incluido (AAAA-MM-DD)', kind: 'text' },
];

function stat(value: string | null): string {
  return value === null ? 'no aplica' : formatDisplay(value);
}

/** Consumption history (RF-009, DT-067): only for ANALYST, PLANNER and ADMIN; the caller gates it. */
export function ProductHistorySection({
  productId,
  unitOfMeasure,
}: {
  productId: number;
  unitOfMeasure: string;
}) {
  const [search, setSearch] = useSearchParams();
  const query: Record<string, string> = {};
  for (const key of HISTORY_KEYS) {
    const value = search.get(key);
    if (value) {
      query[key] = value;
    }
  }
  const result = useApiQuery<History>(API_PATHS.productHistory(productId), query);

  return (
    <section className="section" aria-labelledby="producto-historia">
      <h2 id="producto-historia" className="section__title">
        Historial de consumo
      </h2>
      <p className="page__note">
        Consumo registrado en periodos de calendario. Es una serie distinta de la predicción, que
        usa semanas ancladas en el corte: no se unen en una misma línea.
      </p>
      <FilterForm
        fields={FIELDS}
        search={search}
        onApply={(values) => setSearch((current) => withFilters(current, values))}
      />
      <QueryView query={result} loadingLines={4}>
        {(history) => (
          <>
            <dl className="facts">
              <dt>Rango</dt>
              <dd>
                {formatCalendarDate(history.date_from)} – {formatCalendarDate(history.date_to)} ·{' '}
                <code>{history.granularity}</code>
              </dd>
              <dt>Periodos completos usados</dt>
              <dd>{history.statistics.periods_used}</dd>
              <dt>Media</dt>
              <dd>
                {history.statistics.mean === null
                  ? 'no aplica'
                  : formatQuantity(history.statistics.mean, unitOfMeasure)}
              </dd>
              <dt>Desviación estándar (poblacional)</dt>
              <dd>
                {history.statistics.std_dev === null
                  ? 'no aplica'
                  : formatQuantity(history.statistics.std_dev, unitOfMeasure)}
              </dd>
              <dt>Coeficiente de variación</dt>
              <dd>{stat(history.statistics.cv)}</dd>
              <dt>Periodos en cero</dt>
              <dd>{history.statistics.zero_periods ?? 'no aplica'}</dd>
            </dl>
            {history.periods.length === 0 ? (
              <p className="page__note">No hay consumo en el rango consultado.</p>
            ) : (
              <div className="table-wrap">
                <table className="data-table">
                  <caption className="visually-hidden">Historial de consumo</caption>
                  <thead>
                    <tr>
                      <th scope="col">Desde</th>
                      <th scope="col">Hasta (excluido)</th>
                      <th scope="col" className="numeric">
                        Consumo
                      </th>
                      <th scope="col" className="numeric">
                        Días observados
                      </th>
                      <th scope="col" className="numeric">
                        Días con desabasto
                      </th>
                      <th scope="col">Completo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.periods.map((period) => (
                      <tr key={period.period_start}>
                        <td>{formatCalendarDate(period.period_start)}</td>
                        <td>{formatCalendarDate(period.period_end)}</td>
                        <td className="numeric">
                          {formatQuantity(period.quantity, unitOfMeasure)}
                        </td>
                        <td className="numeric">
                          {period.days_observed} de {period.days}
                        </td>
                        <td className="numeric">{period.stockout_days}</td>
                        <td>{yesNo(period.complete)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </QueryView>
    </section>
  );
}
