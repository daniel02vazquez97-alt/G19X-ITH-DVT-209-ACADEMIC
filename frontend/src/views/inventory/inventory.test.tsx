import { screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { installFetch, jsonResponse, requestedUrls, routeApi } from '../../test/api';
import { INVENTORY_46, INVENTORY_PAGE, PRODUCT_46_DETAIL } from '../../test/fixtures';
import { loginAs, renderApp } from '../../test/renderApp';

describe('InventoryPage (F7b)', () => {
  it('shows the position exactly as the API computed it', async () => {
    const fetchMock = installFetch(
      routeApi({ '/api/v1/inventory': () => jsonResponse(200, INVENTORY_PAGE) }),
    );
    const { user } = renderApp('/inventario?sort=-available&category_id=3');
    await loginAs(user, 'VIEWER');
    const table = await screen.findByRole('table');
    const row = within(table).getAllByRole('row')[1] as HTMLElement;
    expect(row).toHaveTextContent('SKU-00004');
    expect(row).toHaveTextContent('242');
    expect(row).toHaveTextContent('SYNTHETIC');
    expect(within(row).getByRole('link', { name: 'SKU-00004' })).toHaveAttribute(
      'href',
      '/inventario/4',
    );
    expect(requestedUrls(fetchMock)).toEqual(['/api/v1/inventory?sort=-available&category_id=3']);
    expect(screen.getByText('Orden: Disponible descendente.')).toBeInTheDocument();
  });
});

describe('InventoryItemPage (F7b)', () => {
  it('shows the open lines with the unit of the product', async () => {
    installFetch(
      routeApi({
        '/api/v1/inventory/46': () => jsonResponse(200, INVENTORY_46),
        '/api/v1/products/46': () => jsonResponse(200, PRODUCT_46_DETAIL),
      }),
    );
    const { user } = renderApp('/inventario/46');
    await loginAs(user, 'VIEWER');
    expect(
      await screen.findByRole('heading', { level: 1, name: /Inventario de SKU-00046/ }),
    ).toBeInTheDocument();
    expect(screen.getByText('129 KG')).toBeInTheDocument();
    const lines = screen.getByRole('table');
    expect(lines).toHaveTextContent('PO-003561');
    expect(lines).toHaveTextContent('20/01/2026');
    expect(lines).toHaveTextContent('45 KG');
    expect(screen.getByRole('link', { name: 'Ver el detalle del producto' })).toHaveAttribute(
      'href',
      '/productos/46',
    );
  });
});
