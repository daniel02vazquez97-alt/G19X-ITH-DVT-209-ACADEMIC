import { screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { installFetch, jsonResponse, requestedUrls, routeApi } from '../../test/api';
import { PRODUCT_4_DETAIL } from '../../test/fixtures';
import { loginAs, renderApp } from '../../test/renderApp';
import FORECASTS from '../../test/responses/forecasts.json';
import PRODUCT_4_FORECAST from '../../test/responses/product-4-forecast.json';
import PRODUCT_4_HISTORY from '../../test/responses/product-4-history-monthly.json';

const INSUFFICIENT = {
  ...PRODUCT_4_FORECAST,
  periods: PRODUCT_4_FORECAST.periods.map((period) => ({
    ...period,
    confidence_flag: 'INSUFFICIENT_HISTORY',
  })),
};

function productApi(extra: Record<string, () => Response> = {}) {
  return routeApi({
    '/api/v1/products/4': () => jsonResponse(200, PRODUCT_4_DETAIL),
    '/api/v1/products/4/forecast': () => jsonResponse(200, PRODUCT_4_FORECAST),
    '/api/v1/products/4/history': () => jsonResponse(200, PRODUCT_4_HISTORY),
    ...extra,
  });
}

describe('ForecastsPage (F7d, US-075 partial)', () => {
  it('lists the primary series with provenance and the nominal band note', async () => {
    const fetchMock = installFetch(
      routeApi({ '/api/v1/forecasts': () => jsonResponse(200, FORECASTS) }),
    );
    const { user } = renderApp('/predicciones?category_id=2&run_id=1');
    await loginAs(user, 'VIEWER');
    expect(await screen.findByText('SKU-00001', { selector: '.series__sku' })).toBeInTheDocument();
    expect(screen.getByText(/· 14 semanas/)).toBeInTheDocument();
    expect(screen.getByRole('complementary', { name: 'Avisos' })).toHaveTextContent(
      'Datos sintéticos',
    );
    expect(screen.getByText(/no una cobertura validada/)).toBeInTheDocument();
    expect(requestedUrls(fetchMock)).toEqual(['/api/v1/forecasts?category_id=2&run_id=1']);
  });
});

describe('Product detail: forecast and history (F7d)', () => {
  it('shows the forecast table with exact figures and the nominal level', async () => {
    installFetch(productApi());
    const { user } = renderApp('/productos/4');
    await loginAs(user, 'VIEWER');
    const table = await screen.findByRole('table', { name: 'Predicción semanal del producto' });
    const first = within(table).getAllByRole('row')[1] as HTMLElement;
    expect(first).toHaveTextContent('01/01/2026');
    expect(first).toHaveTextContent('08/01/2026');
    expect(first).toHaveTextContent('530.692308');
    expect(first).toHaveTextContent('523');
    expect(first).toHaveTextContent('562.769231');
    expect(first).toHaveTextContent('0.80');
    expect(first).toHaveTextContent('BASELINE');
    expect(screen.getByText(/banda nominal 0\.80/)).toBeInTheDocument();
    expect(screen.queryByText(/historia insuficiente/)).toBeNull();
  });

  it('warns explicitly with INSUFFICIENT_HISTORY', async () => {
    installFetch(
      productApi({ '/api/v1/products/4/forecast': () => jsonResponse(200, INSUFFICIENT) }),
    );
    const { user } = renderApp('/productos/4');
    await loginAs(user, 'VIEWER');
    expect(await screen.findByRole('note')).toHaveTextContent('historia insuficiente');
  });

  it('a product without forecast shows an empty state', async () => {
    installFetch(
      routeApi({
        '/api/v1/products/4': () => jsonResponse(200, PRODUCT_4_DETAIL),
      }),
    );
    const { user } = renderApp('/productos/4');
    await loginAs(user, 'VIEWER');
    const section = await screen.findByRole('region', { name: 'Predicción' });
    expect(await within(section).findByRole('region', { name: 'Sin datos' })).toBeInTheDocument();
  });

  it('VIEWER does not see nor request the history', async () => {
    const fetchMock = installFetch(productApi());
    const { user } = renderApp('/productos/4');
    await loginAs(user, 'VIEWER');
    await screen.findByRole('table', { name: 'Predicción semanal del producto' });
    expect(screen.queryByRole('region', { name: 'Historial de consumo' })).toBeNull();
    expect(requestedUrls(fetchMock).some((url) => url.includes('/history'))).toBe(false);
  });

  it('ANALYST sees the history with its population statistics, from the URL', async () => {
    const fetchMock = installFetch(productApi());
    const { user } = renderApp('/productos/4?granularity=monthly');
    await loginAs(user, 'ANALYST');
    const section = await screen.findByRole('region', { name: 'Historial de consumo' });
    const table = await within(section).findByRole('table');
    expect(within(table).getAllByRole('row')).toHaveLength(37);
    expect(within(table).getAllByRole('row')[1]).toHaveTextContent('1539 BOX');
    expect(section).toHaveTextContent('1889.027778 BOX');
    expect(section).toHaveTextContent('267.138903 BOX');
    expect(section).toHaveTextContent('0.141416');
    expect(requestedUrls(fetchMock)).toContain('/api/v1/products/4/history?granularity=monthly');
  });

  it('history filters go to the URL', async () => {
    installFetch(productApi());
    const { user, router } = renderApp('/productos/4');
    await loginAs(user, 'PLANNER');
    const section = await screen.findByRole('region', { name: 'Historial de consumo' });
    await user.selectOptions(within(section).getByLabelText('Periodo'), 'weekly');
    await user.type(within(section).getByLabelText('Desde (AAAA-MM-DD)'), '2025-01-01');
    await user.click(within(section).getByRole('button', { name: 'Aplicar' }));
    expect(router.state.location.search).toBe('?granularity=weekly&date_from=2025-01-01');
  });
});
