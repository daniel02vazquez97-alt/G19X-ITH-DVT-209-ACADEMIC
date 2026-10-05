import { Link } from 'react-router';
import { API_PATHS } from '../../api/paths';
import type { InventoryPage as InventoryPageData } from '../../api/types';
import { useApiQuery } from '../../api/useApiQuery';
import { EmptyState } from '../../components/EmptyState';
import { FilterForm, type FilterField, type FilterOption } from '../../components/FilterForm';
import { Pagination } from '../../components/Pagination';
import { QueryView } from '../../components/QueryView';
import { SortNote } from '../../components/SortNote';
import { formatTimestamp } from '../../format/dates';
import { formatDisplay } from '../../format/numbers';
import { PAGE_SIZE, SORT, useListParams } from '../../routes/listParams';
import { toInventoryItem } from '../../routes/paths';

export const INVENTORY_SORTS: readonly FilterOption[] = [
  { value: '', label: 'SKU ascendente (por defecto)' },
  { value: '-sku', label: 'SKU descendente' },
  { value: 'on_hand', label: 'Existencia ascendente' },
  { value: '-on_hand', label: 'Existencia descendente' },
  { value: 'available', label: 'Disponible ascendente' },
  { value: '-available', label: 'Disponible descendente' },
];

const FIELDS: readonly FilterField[] = [
  { key: 'product_id', label: 'Producto (identificador)', kind: 'id' },
  {
    key: 'category_id',
    label: 'Categoría (identificador)',
    kind: 'id',
    help: 'La API no ofrece catálogo de categorías.',
  },
  { key: SORT, label: 'Orden', kind: 'select', options: INVENTORY_SORTS },
];

const FILTER_KEYS = ['product_id', 'category_id'];

export function InventoryPage() {
  const { search, query, setFilters, setPage, setFilter } = useListParams(FILTER_KEYS);
  const result = useApiQuery<InventoryPageData>(API_PATHS.inventory, query);

  return (
    <article className="page">
      <h1 className="page__title">Inventario</h1>
      <FilterForm fields={FIELDS} search={search} onApply={setFilters} />
      <SortNote sort={query[SORT]} options={INVENTORY_SORTS} />
      <p className="page__note">
        Las cantidades están en la unidad de cada producto, que se ve en su detalle.
      </p>
      <QueryView query={result}>
        {(data) => (
          <>
            {data.items.length === 0 ? (
              <EmptyState title="Sin resultados" message="Ningún producto cumple los filtros." />
            ) : (
              <div className="table-wrap">
                <table className="data-table">
                  <caption className="visually-hidden">Posición de inventario</caption>
                  <thead>
                    <tr>
                      <th scope="col">SKU</th>
                      <th scope="col" className="numeric">
                        Existencia
                      </th>
                      <th scope="col" className="numeric">
                        Reservado
                      </th>
                      <th scope="col" className="numeric">
                        Disponible
                      </th>
                      <th scope="col" className="numeric">
                        En tránsito
                      </th>
                      <th scope="col" className="numeric">
                        Posición contable
                      </th>
                      <th scope="col">Último movimiento</th>
                      <th scope="col">Origen</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.items.map((item) => (
                      <tr key={item.product_id}>
                        <td>
                          <Link to={toInventoryItem(item.product_id)}>{item.sku}</Link>
                        </td>
                        <td className="numeric">{formatDisplay(item.on_hand)}</td>
                        <td className="numeric">{formatDisplay(item.reserved)}</td>
                        <td className="numeric">{formatDisplay(item.available)}</td>
                        <td className="numeric">{formatDisplay(item.in_transit_total)}</td>
                        <td className="numeric">
                          {formatDisplay(item.inventory_position_accounting)}
                        </td>
                        <td>{formatTimestamp(item.last_movement_at)}</td>
                        <td>
                          <code>{item.data_origin}</code>
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
