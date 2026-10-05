import { Link, useParams } from 'react-router';
import { API_PATHS } from '../../api/paths';
import type { InventoryDetail, ProductDetail } from '../../api/types';
import { useApiQuery } from '../../api/useApiQuery';
import { QueryView } from '../../components/QueryView';
import { formatCalendarDate, formatTimestamp } from '../../format/dates';
import { formatQuantity } from '../../format/numbers';
import { PATHS, toProduct } from '../../routes/paths';

export function InventoryItemPage() {
  const { productId = '' } = useParams();
  const inventory = useApiQuery<InventoryDetail>(API_PATHS.inventoryItem(productId));
  // The inventory resource has no unit of measure: it comes from the product (units always visible).
  const product = useApiQuery<ProductDetail>(API_PATHS.product(productId));

  return (
    <article className="page">
      <p className="breadcrumb">
        <Link to={PATHS.inventory}>Inventario</Link>
      </p>
      <QueryView query={product}>
        {(productData) => (
          <QueryView query={inventory}>
            {(item) => {
              const unit = productData.unit_of_measure;
              return (
                <>
                  <h1 className="page__title">
                    Inventario de {item.sku} · {productData.name}
                  </h1>
                  <p>
                    <Link to={toProduct(item.product_id)}>Ver el detalle del producto</Link>
                  </p>
                  <section className="section" aria-labelledby="inventario-posicion">
                    <h2 id="inventario-posicion" className="section__title">
                      Posición
                    </h2>
                    <dl className="facts">
                      <dt>Existencia</dt>
                      <dd>{formatQuantity(item.on_hand, unit)}</dd>
                      <dt>Reservado</dt>
                      <dd>{formatQuantity(item.reserved, unit)}</dd>
                      <dt>Disponible</dt>
                      <dd>{formatQuantity(item.available, unit)}</dd>
                      <dt>En tránsito (total)</dt>
                      <dd>{formatQuantity(item.in_transit_total, unit)}</dd>
                      <dt>Posición contable</dt>
                      <dd>{formatQuantity(item.inventory_position_accounting, unit)}</dd>
                      <dt>Último movimiento</dt>
                      <dd>{formatTimestamp(item.last_movement_at)}</dd>
                      <dt>Origen de los datos</dt>
                      <dd>
                        <code>{item.data_origin}</code>
                      </dd>
                    </dl>
                  </section>
                  <section className="section" aria-labelledby="inventario-lineas">
                    <h2 id="inventario-lineas" className="section__title">
                      Líneas de compra abiertas
                    </h2>
                    {item.open_lines.length === 0 ? (
                      <p className="page__note">No hay líneas de compra abiertas.</p>
                    ) : (
                      <div className="table-wrap">
                        <table className="data-table">
                          <caption className="visually-hidden">Líneas de compra abiertas</caption>
                          <thead>
                            <tr>
                              <th scope="col">Orden</th>
                              <th scope="col">Proveedor</th>
                              <th scope="col">Estado</th>
                              <th scope="col">Llegada prevista</th>
                              <th scope="col" className="numeric">
                                Pendiente
                              </th>
                            </tr>
                          </thead>
                          <tbody>
                            {item.open_lines.map((line) => (
                              <tr key={`${line.order_number}-${line.expected_on}`}>
                                <td>{line.order_number}</td>
                                <td>
                                  {line.supplier.name}{' '}
                                  <span className="muted">({line.supplier.code})</span>
                                </td>
                                <td>
                                  <code>{line.status}</code>
                                </td>
                                <td>{formatCalendarDate(line.expected_on)}</td>
                                <td className="numeric">
                                  {formatQuantity(line.quantity_pending, unit)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </section>
                </>
              );
            }}
          </QueryView>
        )}
      </QueryView>
    </article>
  );
}
