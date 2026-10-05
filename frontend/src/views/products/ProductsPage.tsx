import { Link } from 'react-router';
import { API_PATHS } from '../../api/paths';
import type { ProductPage } from '../../api/types';
import { useApiQuery } from '../../api/useApiQuery';
import { EmptyState } from '../../components/EmptyState';
import { FilterForm, type FilterField, type FilterOption } from '../../components/FilterForm';
import { Pagination } from '../../components/Pagination';
import { QueryView } from '../../components/QueryView';
import { SortNote } from '../../components/SortNote';
import { PAGE_SIZE, SORT, useListParams } from '../../routes/listParams';
import { toProduct } from '../../routes/paths';
import { activeLabel, validityLabel } from '../labels';

export const PRODUCT_SORTS: readonly FilterOption[] = [
  { value: '', label: 'SKU ascendente (por defecto)' },
  { value: '-sku', label: 'SKU descendente' },
  { value: 'name', label: 'Nombre ascendente' },
  { value: '-name', label: 'Nombre descendente' },
  { value: 'id', label: 'Identificador ascendente' },
  { value: '-id', label: 'Identificador descendente' },
];

const FIELDS: readonly FilterField[] = [
  { key: 'search', label: 'Buscar por SKU o nombre', kind: 'text' },
  {
    key: 'is_active',
    label: 'Estado',
    kind: 'select',
    options: [
      { value: '', label: 'Todos' },
      { value: 'true', label: 'Activos' },
      { value: 'false', label: 'Inactivos' },
    ],
  },
  {
    key: 'category_id',
    label: 'Categoría (identificador)',
    kind: 'id',
    help: 'La API no ofrece catálogo de categorías.',
  },
  { key: SORT, label: 'Orden', kind: 'select', options: PRODUCT_SORTS },
];

const FILTER_KEYS = ['search', 'is_active', 'category_id'];

export function ProductsPage() {
  const { search, query, setFilters, setPage, setFilter } = useListParams(FILTER_KEYS);
  const result = useApiQuery<ProductPage>(API_PATHS.products, query);

  return (
    <article className="page">
      <h1 className="page__title">Productos</h1>
      <FilterForm fields={FIELDS} search={search} onApply={setFilters} />
      <SortNote sort={query[SORT]} options={PRODUCT_SORTS} />
      <QueryView query={result}>
        {(data) => (
          <>
            {data.items.length === 0 ? (
              <EmptyState title="Sin resultados" message="Ningún producto cumple los filtros." />
            ) : (
              <div className="table-wrap">
                <table className="data-table">
                  <caption className="visually-hidden">Productos</caption>
                  <thead>
                    <tr>
                      <th scope="col">SKU</th>
                      <th scope="col">Nombre</th>
                      <th scope="col">Categoría</th>
                      <th scope="col">Unidad</th>
                      <th scope="col">Estado</th>
                      <th scope="col">Vigencia</th>
                      <th scope="col">Origen</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.items.map((product) => (
                      <tr key={product.id}>
                        <td>
                          <Link to={toProduct(product.id)}>{product.sku}</Link>
                        </td>
                        <td>{product.name}</td>
                        <td>
                          {product.category.name}{' '}
                          <span className="muted">({product.category.code})</span>
                        </td>
                        <td>{product.unit_of_measure}</td>
                        <td>{activeLabel(product.is_active)}</td>
                        <td>{validityLabel(product.valid_from, product.valid_to)}</td>
                        <td>
                          <code>{product.data_origin}</code>
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
