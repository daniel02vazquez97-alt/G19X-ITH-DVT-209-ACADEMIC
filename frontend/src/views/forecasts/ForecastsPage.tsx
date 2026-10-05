import { Link } from 'react-router';
import { API_PATHS } from '../../api/paths';
import type { ForecastPage } from '../../api/types';
import { useApiQuery } from '../../api/useApiQuery';
import { EmptyState } from '../../components/EmptyState';
import { FilterForm, type FilterField } from '../../components/FilterForm';
import { Pagination } from '../../components/Pagination';
import { ProvenancePanel } from '../../components/provenance/ProvenancePanel';
import { QueryView } from '../../components/QueryView';
import { PAGE_SIZE, useListParams } from '../../routes/listParams';
import { toProduct } from '../../routes/paths';
import {
  ForecastTable,
  hasInsufficientHistory,
  InsufficientHistoryNotice,
  NominalBandNote,
} from './ForecastTable';

const FIELDS: readonly FilterField[] = [
  { key: 'product_id', label: 'Producto (identificador)', kind: 'id' },
  { key: 'category_id', label: 'Categoría (identificador)', kind: 'id' },
  {
    key: 'run_id',
    label: 'Ejecución (identificador)',
    kind: 'id',
    help: 'Vacío: la última ejecución completada.',
  },
];

const FILTER_KEYS = ['product_id', 'category_id', 'run_id'];

export function ForecastsPage() {
  const { search, query, setFilters, setPage, setFilter } = useListParams(FILTER_KEYS);
  const result = useApiQuery<ForecastPage>(API_PATHS.forecasts, query);

  return (
    <article className="page">
      <h1 className="page__title">Predicciones</h1>
      <p className="page__note">
        Serie primaria de cada producto en una ejecución de forecast: 14 semanas ancladas en el
        corte. La API no admite orden ni filtro por horizonte; la lista sigue su orden.
      </p>
      <FilterForm fields={FIELDS} search={search} onApply={setFilters} />
      <QueryView query={result}>
        {(data) => (
          <>
            <ProvenancePanel provenance={data.provenance} />
            <NominalBandNote />
            {data.items.length === 0 ? (
              <EmptyState
                title="Sin resultados"
                message="Ninguna serie de la ejecución cumple los filtros."
              />
            ) : (
              <ul className="series-list">
                {data.items.map((series) => (
                  <li key={series.product.id}>
                    <details className="series">
                      <summary>
                        <span className="series__sku">{series.product.sku}</span> ·{' '}
                        {series.model_version.name} {series.model_version.version} ·{' '}
                        {series.periods.length} semanas
                        {hasInsufficientHistory(series.periods) ? (
                          <strong className="series__warning"> · historia insuficiente</strong>
                        ) : null}
                      </summary>
                      <p>
                        <Link to={toProduct(series.product.id)}>
                          Ver el producto con su gráfico
                        </Link>
                      </p>
                      {hasInsufficientHistory(series.periods) ? (
                        <InsufficientHistoryNotice />
                      ) : null}
                      <ForecastTable
                        periods={series.periods}
                        caption={`Predicción de ${series.product.sku}`}
                      />
                    </details>
                  </li>
                ))}
              </ul>
            )}
            <Pagination
              page={data.page}
              pageSize={data.page_size}
              total={data.total}
              onPage={setPage}
              onPageSize={(size) => setFilter(PAGE_SIZE, size)}
            />
          </>
        )}
      </QueryView>
    </article>
  );
}
