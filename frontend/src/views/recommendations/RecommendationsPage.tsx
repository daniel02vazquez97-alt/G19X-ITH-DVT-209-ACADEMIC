import { Link } from 'react-router';
import { API_PATHS } from '../../api/paths';
import type { RecommendationPage } from '../../api/types';
import { useApiQuery } from '../../api/useApiQuery';
import { CodeList } from '../../components/CodeList';
import { EmptyState } from '../../components/EmptyState';
import { FilterForm, type FilterField, type FilterOption } from '../../components/FilterForm';
import { Pagination } from '../../components/Pagination';
import { ProvenancePanel } from '../../components/provenance/ProvenancePanel';
import { QueryView } from '../../components/QueryView';
import { SortNote } from '../../components/SortNote';
import { formatCalendarDate } from '../../format/dates';
import { formatDisplay, NOT_CALCULATED } from '../../format/numbers';
import { PAGE_SIZE, SORT, useListParams } from '../../routes/listParams';
import { toRecommendation } from '../../routes/paths';
import { outcomeLabel } from './vocabulary';

export const RECOMMENDATION_SORTS: readonly FilterOption[] = [
  { value: '', label: 'SKU ascendente (por defecto)' },
  { value: '-sku', label: 'SKU descendente' },
  { value: 'recommended_quantity', label: 'Cantidad sugerida ascendente' },
  { value: '-recommended_quantity', label: 'Cantidad sugerida descendente' },
  { value: 'suggested_order_date', label: 'Fecha sugerida ascendente' },
  { value: '-suggested_order_date', label: 'Fecha sugerida descendente' },
];

const FIELDS: readonly FilterField[] = [
  {
    key: 'outcome',
    label: 'Resultado',
    kind: 'select',
    options: [
      { value: '', label: 'Se sugiere pedir (por defecto)' },
      { value: 'NO_NEED', label: 'Sin necesidad de pedido' },
      { value: 'NOT_CALCULABLE', label: 'No calculable' },
    ],
  },
  { key: 'product_id', label: 'Producto (identificador)', kind: 'id' },
  { key: 'category_id', label: 'Categoría (identificador)', kind: 'id' },
  {
    key: 'supplier_id',
    label: 'Proveedor (identificador)',
    kind: 'id',
    help: 'La API no ofrece catálogo de proveedores.',
  },
  {
    key: 'run_id',
    label: 'Ejecución (identificador)',
    kind: 'id',
    help: 'Vacío: la última ejecución completada.',
  },
  { key: SORT, label: 'Orden', kind: 'select', options: RECOMMENDATION_SORTS },
];

const FILTER_KEYS = ['outcome', 'product_id', 'category_id', 'supplier_id', 'run_id'];

function quantity(value: string | null): string {
  return value === null ? NOT_CALCULATED : formatDisplay(value);
}

export function RecommendationsPage() {
  const { search, query, setFilters, setPage, setFilter } = useListParams(FILTER_KEYS);
  const result = useApiQuery<RecommendationPage>(API_PATHS.recommendations, query);

  return (
    <article className="page">
      <h1 className="page__title">Recomendaciones</h1>
      <p className="page__note">
        Evaluaciones del motor en una ejecución. Sin prioridad ni urgencia: la V1 no las calcula.
      </p>
      <FilterForm fields={FIELDS} search={search} onApply={setFilters} />
      <SortNote sort={query[SORT]} options={RECOMMENDATION_SORTS} />
      <p className="page__note">
        Las cantidades están en la unidad de cada producto, que se ve en el detalle.
      </p>
      <QueryView query={result}>
        {(data) => (
          <>
            <ProvenancePanel provenance={data.provenance} />
            {data.items.length === 0 ? (
              <EmptyState
                title="Sin resultados"
                message="Ninguna evaluación de la ejecución cumple los filtros."
              />
            ) : (
              <div className="table-wrap">
                <table className="data-table">
                  <caption className="visually-hidden">Evaluaciones del motor</caption>
                  <thead>
                    <tr>
                      <th scope="col">Producto</th>
                      <th scope="col">Proveedor</th>
                      <th scope="col" className="numeric">
                        Cantidad sugerida
                      </th>
                      <th scope="col" className="numeric">
                        Necesidad bruta
                      </th>
                      <th scope="col">Fecha sugerida</th>
                      <th scope="col">Resultado</th>
                      <th scope="col">Marcas</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.items.map((item) => (
                      <tr key={item.id}>
                        <td>
                          <Link to={toRecommendation(item.id)}>{item.product.sku}</Link>{' '}
                          <span className="muted">{item.product.name}</span>
                        </td>
                        <td>
                          {item.supplier ? (
                            <>
                              {item.supplier.name}{' '}
                              <span className="muted">({item.supplier.code})</span>
                            </>
                          ) : (
                            <span className="muted">sin proveedor</span>
                          )}
                        </td>
                        <td className="numeric">{quantity(item.recommended_quantity)}</td>
                        <td className="numeric">{quantity(item.raw_quantity)}</td>
                        <td>{formatCalendarDate(item.suggested_order_date)}</td>
                        <td>
                          {outcomeLabel(item.outcome)} <code className="muted">{item.outcome}</code>
                        </td>
                        <td>
                          <CodeList codes={item.flags} empty="—" />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
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
