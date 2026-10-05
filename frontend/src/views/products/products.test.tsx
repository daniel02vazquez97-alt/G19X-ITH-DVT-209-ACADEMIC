import { screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { errorResponse, installFetch, jsonResponse, requestedUrls, routeApi } from '../../test/api';
import { PRODUCT_4_DETAIL, PRODUCT_PAGE } from '../../test/fixtures';
import { loginAs, renderApp } from '../../test/renderApp';

describe('ProductsPage (F7b, US-072)', () => {
  it('lists the products the API returns, with unit and data origin per row', async () => {
    installFetch(routeApi({ '/api/v1/products': () => jsonResponse(200, PRODUCT_PAGE) }));
    const { user } = renderApp('/productos');
    await loginAs(user, 'VIEWER');
    const table = await screen.findByRole('table');
    const rows = within(table).getAllByRole('row');
    expect(rows).toHaveLength(3);
    expect(rows[1]).toHaveTextContent('SKU-00004');
    expect(rows[1]).toHaveTextContent('BOX');
    expect(rows[1]).toHaveTextContent('SYNTHETIC');
    expect(rows[2]).toHaveTextContent('Inactivo');
    expect(rows[2]).toHaveTextContent('01/01/2023 – 30/06/2025');
    expect(within(rows[1] as HTMLElement).getByRole('link', { name: 'SKU-00004' })).toHaveAttribute(
      'href',
      '/productos/4',
    );
    // Page and total come from the API, never recomputed.
    expect(screen.getByText('Página 1 · 120 resultados en total')).toBeInTheDocument();
  });

  it('sends the filters of the URL to the API as they are', async () => {
    const fetchMock = installFetch(
      routeApi({ '/api/v1/products': () => jsonResponse(200, PRODUCT_PAGE) }),
    );
    const { user } = renderApp('/productos?search=caja&is_active=false&sort=-name&page=2&x=1');
    await loginAs(user, 'VIEWER');
    await screen.findByRole('table');
    expect(requestedUrls(fetchMock)).toEqual([
      '/api/v1/products?page=2&sort=-name&search=caja&is_active=false',
    ]);
    expect(screen.getByText('Orden: Nombre descendente.')).toBeInTheDocument();
  });

  it('applying filters writes them in the URL and goes back to page 1', async () => {
    installFetch(routeApi({ '/api/v1/products': () => jsonResponse(200, PRODUCT_PAGE) }));
    const { user, router } = renderApp('/productos?page=3');
    await loginAs(user, 'VIEWER');
    await screen.findByRole('table');
    await user.type(screen.getByLabelText('Buscar por SKU o nombre'), 'SKU-0000');
    await user.type(screen.getByLabelText('Categoría (identificador)'), '2');
    await user.click(screen.getByRole('button', { name: 'Aplicar' }));
    expect(router.state.location.search).toBe('?search=SKU-0000&category_id=2');
  });

  it('moves to the next page through the URL', async () => {
    installFetch(routeApi({ '/api/v1/products': () => jsonResponse(200, PRODUCT_PAGE) }));
    const { user, router } = renderApp('/productos?sort=name');
    await loginAs(user, 'VIEWER');
    await screen.findByRole('table');
    expect(screen.getByRole('button', { name: 'Anterior' })).toBeDisabled();
    await user.click(screen.getByRole('button', { name: 'Siguiente' }));
    expect(router.state.location.search).toBe('?sort=name&page=2');
  });

  it('a 422 is an invalid filter without the received value', async () => {
    installFetch(routeApi({ '/api/v1/products': () => errorResponse(422, 'VALIDATION_ERROR') }));
    const { user } = renderApp('/productos?page_size=500');
    await loginAs(user, 'VIEWER');
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Filtro no válido');
    expect(alert).not.toHaveTextContent('500');
  });

  it('an empty page is an empty state', async () => {
    installFetch(
      routeApi({
        '/api/v1/products': () => jsonResponse(200, { ...PRODUCT_PAGE, items: [], total: 0 }),
      }),
    );
    const { user } = renderApp('/productos?search=nada');
    await loginAs(user, 'VIEWER');
    expect(await screen.findByRole('region', { name: 'Sin resultados' })).toBeInTheDocument();
  });
});

describe('ProductDetailPage (F7b)', () => {
  it('shows master data, inventory with units and suppliers', async () => {
    installFetch(routeApi({ '/api/v1/products/4': () => jsonResponse(200, PRODUCT_4_DETAIL) }));
    const { user } = renderApp('/productos/4');
    await loginAs(user, 'VIEWER');
    expect(
      await screen.findByRole('heading', { level: 1, name: 'SKU-00004 · Product SKU-00004' }),
    ).toBeInTheDocument();
    expect(screen.getByText('242 BOX')).toBeInTheDocument();
    expect(screen.getByText('2623.5006 BOX')).toBeInTheDocument();
    expect(screen.getByText('31/12/2025, 21:30', { exact: false })).toBeInTheDocument();
    const suppliers = screen.getByRole('table');
    expect(suppliers).toHaveTextContent('Supplier SUP-010');
    expect(suppliers).toHaveTextContent('100 BOX');
    expect(suppliers).toHaveTextContent('12.5');
    expect(suppliers).toHaveTextContent('21 días');
    expect(
      screen.getByRole('link', { name: /posición de inventario y las líneas de compra/ }),
    ).toHaveAttribute('href', '/inventario/4');
  });

  it('says when the product has no inventory', async () => {
    installFetch(
      routeApi({
        '/api/v1/products/4': () =>
          jsonResponse(200, { ...PRODUCT_4_DETAIL, inventory: null, suppliers: [] }),
      }),
    );
    const { user } = renderApp('/productos/4');
    await loginAs(user, 'VIEWER');
    expect(
      await screen.findByText('El producto no tiene inventario registrado.'),
    ).toBeInTheDocument();
    expect(screen.getByText('El producto no tiene proveedores asociados.')).toBeInTheDocument();
  });

  it('a 404 is "No encontrado"', async () => {
    installFetch(routeApi({}));
    const { user } = renderApp('/productos/999');
    await loginAs(user, 'VIEWER');
    expect(await screen.findByRole('alert')).toHaveTextContent('No encontrado');
  });
});

describe('Pagination', () => {
  it('shows the page size of the API even when it is not a usual one', async () => {
    installFetch(
      routeApi({ '/api/v1/products': () => jsonResponse(200, { ...PRODUCT_PAGE, page_size: 10 }) }),
    );
    const { user } = renderApp('/productos?page_size=10');
    await loginAs(user, 'VIEWER');
    await screen.findByRole('table');
    expect(screen.getByLabelText('Por página')).toHaveValue('10');
  });
});
