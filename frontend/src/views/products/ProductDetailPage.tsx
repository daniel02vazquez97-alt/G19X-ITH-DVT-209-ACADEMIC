import { Link, useParams } from 'react-router';
import { API_PATHS } from '../../api/paths';
import type { ProductDetail } from '../../api/types';
import { useApiQuery } from '../../api/useApiQuery';
import { QueryView } from '../../components/QueryView';
import { formatTimestamp } from '../../format/dates';
import { formatDisplay, formatQuantity } from '../../format/numbers';
import { PATHS, toInventoryItem } from '../../routes/paths';
import { activeLabel, validityLabel, yesNo } from '../labels';
import { ProductEvaluationSection } from '../recommendations/ProductEvaluationSection';

export function ProductDetailPage() {
  const { productId = '' } = useParams();
  const result = useApiQuery<ProductDetail>(API_PATHS.product(productId));

  return (
    <article className="page">
      <p className="breadcrumb">
        <Link to={PATHS.products}>Productos</Link>
      </p>
      <QueryView query={result}>
        {(product) => (
          <>
            <h1 className="page__title">
              {product.sku} · {product.name}
            </h1>
            <section className="section" aria-labelledby="producto-maestro">
              <h2 id="producto-maestro" className="section__title">
                Maestro
              </h2>
              <dl className="facts">
                <dt>Categoría</dt>
                <dd>
                  {product.category.name} ({product.category.code})
                </dd>
                <dt>Unidad</dt>
                <dd>{product.unit_of_measure}</dd>
                <dt>Estado</dt>
                <dd>{activeLabel(product.is_active)}</dd>
                <dt>Vigencia</dt>
                <dd>{validityLabel(product.valid_from, product.valid_to)}</dd>
                <dt>Origen de los datos</dt>
                <dd>
                  <code>{product.data_origin}</code>
                </dd>
              </dl>
            </section>

            <section className="section" aria-labelledby="producto-inventario">
              <h2 id="producto-inventario" className="section__title">
                Inventario al corte
              </h2>
              {product.inventory === null ? (
                <p className="page__note">El producto no tiene inventario registrado.</p>
              ) : (
                <>
                  <dl className="facts">
                    <dt>Existencia</dt>
                    <dd>{formatQuantity(product.inventory.on_hand, product.unit_of_measure)}</dd>
                    <dt>Reservado</dt>
                    <dd>{formatQuantity(product.inventory.reserved, product.unit_of_measure)}</dd>
                    <dt>En tránsito (total)</dt>
                    <dd>
                      {formatQuantity(product.inventory.in_transit_total, product.unit_of_measure)}
                    </dd>
                    <dt>Último movimiento</dt>
                    <dd>{formatTimestamp(product.inventory.last_movement_at)}</dd>
                  </dl>
                  <Link to={toInventoryItem(product.id)}>
                    Ver la posición de inventario y las líneas de compra abiertas
                  </Link>
                </>
              )}
            </section>

            <section className="section" aria-labelledby="producto-proveedores">
              <h2 id="producto-proveedores" className="section__title">
                Proveedores
              </h2>
              {product.suppliers.length === 0 ? (
                <p className="page__note">El producto no tiene proveedores asociados.</p>
              ) : (
                <div className="table-wrap">
                  <table className="data-table">
                    <caption className="visually-hidden">Proveedores del producto</caption>
                    <thead>
                      <tr>
                        <th scope="col">Proveedor</th>
                        <th scope="col">Preferente</th>
                        <th scope="col">Activo</th>
                        <th scope="col" className="numeric">
                          Pedido mínimo
                        </th>
                        <th scope="col" className="numeric">
                          Múltiplo de compra
                        </th>
                        <th scope="col" className="numeric">
                          Costo unitario
                        </th>
                        <th scope="col" className="numeric">
                          Plazo acordado
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {product.suppliers.map((relation) => (
                        <tr key={relation.supplier.id}>
                          <td>
                            {relation.supplier.name}{' '}
                            <span className="muted">({relation.supplier.code})</span>
                          </td>
                          <td>{yesNo(relation.is_preferred)}</td>
                          <td>{yesNo(relation.is_active)}</td>
                          <td className="numeric">
                            {formatQuantity(relation.moq, product.unit_of_measure)}
                          </td>
                          <td className="numeric">
                            {formatQuantity(relation.order_multiple, product.unit_of_measure)}
                          </td>
                          <td className="numeric">{formatDisplay(relation.unit_cost)}</td>
                          <td className="numeric">{relation.agreed_lead_time_days} días</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            <ProductEvaluationSection
              productId={product.id}
              unitOfMeasure={product.unit_of_measure}
            />
          </>
        )}
      </QueryView>
    </article>
  );
}
