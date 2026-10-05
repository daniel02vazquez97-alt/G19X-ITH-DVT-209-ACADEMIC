import { screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import {
  CORRELATION_ID,
  errorResponse,
  installFetch,
  jsonResponse,
  requestedUrls,
  routeApi,
} from '../../test/api';
import { PRODUCT_4_DETAIL } from '../../test/fixtures';
import { loginAs, renderApp } from '../../test/renderApp';
import EXPLANATION_3 from '../../test/responses/explanation-3.json';
import EXPLANATION_4 from '../../test/responses/explanation-4.json';
import PRODUCT_4_RECOMMENDATION from '../../test/responses/product-4-recommendation.json';
import RECOMMENDATION_3 from '../../test/responses/recommendation-3.json';
import RECOMMENDATION_4 from '../../test/responses/recommendation-4.json';
import RECOMMENDATIONS from '../../test/responses/recommendations.json';

const PRODUCT_3_DETAIL = { ...PRODUCT_4_DETAIL, id: 3, sku: 'SKU-00003', unit_of_measure: 'EACH' };

function detailApi(explanation: () => Response = () => jsonResponse(200, EXPLANATION_4)) {
  return routeApi({
    '/api/v1/recommendations/4': () => jsonResponse(200, RECOMMENDATION_4),
    '/api/v1/recommendations/4/explanation': explanation,
    '/api/v1/products/4': () => jsonResponse(200, PRODUCT_4_DETAIL),
  });
}

describe('RecommendationsPage (F7c, US-073 without actions)', () => {
  it('lists the evaluations with provenance and notices always visible', async () => {
    const fetchMock = installFetch(
      routeApi({ '/api/v1/recommendations': () => jsonResponse(200, RECOMMENDATIONS) }),
    );
    const { user } = renderApp('/recomendaciones');
    await loginAs(user, 'VIEWER');
    const table = await screen.findByRole('table');
    const row = within(table).getAllByRole('row')[1] as HTMLElement;
    expect(row).toHaveTextContent('SKU-00004');
    expect(row).toHaveTextContent('2700');
    expect(row).toHaveTextContent('2623.5006');
    expect(row).toHaveTextContent('ORDER_MULTIPLE_ROUNDING');
    expect(within(row).getByRole('link', { name: 'SKU-00004' })).toHaveAttribute(
      'href',
      '/recomendaciones/4',
    );
    const notices = screen.getByRole('complementary', { name: 'Avisos' });
    expect(notices).toHaveTextContent('Datos sintéticos');
    expect(notices).toHaveTextContent('Política provisional V1');
    expect(screen.getByText('Orden: SKU ascendente (por defecto).')).toBeInTheDocument();
    expect(requestedUrls(fetchMock)).toEqual(['/api/v1/recommendations']);
    // No actions in V1.
    expect(screen.queryByRole('button', { name: /Atender|Descartar|Convertir/ })).toBeNull();
  });

  it('the run is a link only for PLANNER and ADMIN', async () => {
    installFetch(routeApi({ '/api/v1/recommendations': () => jsonResponse(200, RECOMMENDATIONS) }));
    const viewer = renderApp('/recomendaciones?outcome=NO_NEED');
    await loginAs(viewer.user, 'VIEWER');
    await screen.findByRole('table');
    expect(screen.queryByRole('link', { name: '#2' })).toBeNull();
    expect(screen.getByText('#2')).toBeInTheDocument();
    viewer.unmount();

    installFetch(routeApi({ '/api/v1/recommendations': () => jsonResponse(200, RECOMMENDATIONS) }));
    const planner = renderApp('/recomendaciones');
    await loginAs(planner.user, 'PLANNER');
    expect(await screen.findByRole('link', { name: '#2' })).toHaveAttribute(
      'href',
      '/ejecuciones/2',
    );
  });

  it('sends outcome, identifiers and sort to the API as they are', async () => {
    const fetchMock = installFetch(
      routeApi({ '/api/v1/recommendations': () => jsonResponse(200, RECOMMENDATIONS) }),
    );
    const { user } = renderApp(
      '/recomendaciones?outcome=NOT_CALCULABLE&supplier_id=10&run_id=2&sort=-suggested_order_date',
    );
    await loginAs(user, 'VIEWER');
    await screen.findByRole('table');
    expect(requestedUrls(fetchMock)).toEqual([
      '/api/v1/recommendations?sort=-suggested_order_date&outcome=NOT_CALCULABLE&supplier_id=10&run_id=2',
    ]);
  });
});

describe('RecommendationDetailPage (F7c, US-074 and US-048)', () => {
  it('VERIFIED: narrative, facts with units and exact technical terms', async () => {
    installFetch(detailApi());
    const { user } = renderApp('/recomendaciones/4');
    await loginAs(user, 'VIEWER');
    expect(await screen.findByText(/^Se sugiere pedir 2700 BOX\./)).toBeInTheDocument();
    const facts = await screen.findByRole('table', { name: 'Cifras principales del cálculo' });
    expect(within(facts).getByRole('row', { name: /Cantidad sugerida/ })).toHaveTextContent(
      '2700 BOX',
    );
    expect(within(facts).getByRole('row', { name: /Stock de seguridad/ })).toHaveTextContent(
      '439.478621 BOX',
    );
    expect(within(facts).getByRole('row', { name: /Plazo de entrega/ })).toHaveTextContent(
      '25 días',
    );
    // Every figure of the verified narrative is a `display` of the server.
    const displays = new Set(EXPLANATION_4.facts.map((fact) => fact.display));
    const narrative = EXPLANATION_4.explanation.narrative ?? '';
    for (const figure of narrative.match(/-?\d+(?:\.\d+)?/g) ?? []) {
      expect(displays.has(figure)).toBe(true);
    }
    const technical = screen.getByRole('table', { name: 'Términos del desglose' });
    expect(technical).toHaveTextContent('238877404/109375');
    // Facts stay in the main table; the technical table lists the other terms.
    expect(technical).not.toHaveTextContent('265346154/109375');
    expect(within(technical).getByRole('row', { name: /sigma_h/ })).toHaveTextContent(
      '266.3506791903153337381526076 (aproximado, 28 cifras)',
    );
    expect(screen.getByText(RECOMMENDATION_4.calculation_inputs.input_sha256)).toBeInTheDocument();
    expect(screen.getByRole('complementary', { name: 'Avisos' })).toHaveTextContent(
      'Datos sintéticos',
    );
  });

  it('DEGRADED: "Explicación no disponible" keeps facts and breakdown', async () => {
    const degraded = {
      ...EXPLANATION_4,
      explanation: {
        ...EXPLANATION_4.explanation,
        status: 'DEGRADED',
        narrative: null,
        warning: 'NARRATIVE_UNVERIFIED',
      },
    };
    installFetch(detailApi(() => jsonResponse(200, degraded)));
    const { user } = renderApp('/recomendaciones/4');
    await loginAs(user, 'VIEWER');
    expect(await screen.findByText('Explicación no disponible.')).toBeInTheDocument();
    expect(screen.getByText('NARRATIVE_UNVERIFIED')).toBeInTheDocument();
    expect(screen.queryByText(/^Se sugiere pedir 2700 BOX\./)).toBeNull();
    expect(
      await screen.findByRole('table', { name: 'Cifras principales del cálculo' }),
    ).toHaveTextContent('2700 BOX');
  });

  it('NOT_APPLICABLE: the reasons, no narrative, null terms as "no calculado"', async () => {
    installFetch(
      routeApi({
        '/api/v1/recommendations/3': () => jsonResponse(200, RECOMMENDATION_3),
        '/api/v1/recommendations/3/explanation': () => jsonResponse(200, EXPLANATION_3),
        '/api/v1/products/3': () => jsonResponse(200, PRODUCT_3_DETAIL),
      }),
    );
    const { user } = renderApp('/recomendaciones/3');
    await loginAs(user, 'VIEWER');
    expect(
      await screen.findByText('El producto no tiene un proveedor preferente activo.'),
    ).toBeInTheDocument();
    expect(screen.getByText('Esta evaluación no tiene cifras principales.')).toBeInTheDocument();
    const technical = screen.getByRole('table', { name: 'Términos del desglose' });
    expect(within(technical).getByRole('row', { name: /^sigma_h/ })).toHaveTextContent(
      'no calculado',
    );
  });

  it('a failed explanation shows its error and keeps the breakdown', async () => {
    installFetch(detailApi(() => errorResponse(500, 'INTERNAL_ERROR')));
    const { user } = renderApp('/recomendaciones/4');
    await loginAs(user, 'VIEWER');
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Error interno');
    expect(alert).toHaveTextContent(CORRELATION_ID);
    expect(screen.getByRole('table', { name: 'Términos del desglose' })).toBeInTheDocument();
  });
});

describe('Product detail: evaluation section (F7c)', () => {
  it('shows the evaluation of the product and links to its breakdown', async () => {
    installFetch(
      routeApi({
        '/api/v1/products/4': () => jsonResponse(200, PRODUCT_4_DETAIL),
        '/api/v1/products/4/recommendation': () => jsonResponse(200, PRODUCT_4_RECOMMENDATION),
      }),
    );
    const { user } = renderApp('/productos/4');
    await loginAs(user, 'VIEWER');
    const section = await screen.findByRole('region', { name: 'Evaluación del motor' });
    expect(await within(section).findByText('2700 BOX')).toBeInTheDocument();
    expect(within(section).getByRole('link')).toHaveAttribute('href', '/recomendaciones/4');
  });

  it('a 404 of the product evaluation is an empty state', async () => {
    installFetch(routeApi({ '/api/v1/products/4': () => jsonResponse(200, PRODUCT_4_DETAIL) }));
    const { user } = renderApp('/productos/4');
    await loginAs(user, 'VIEWER');
    const section = await screen.findByRole('region', { name: 'Evaluación del motor' });
    expect(await within(section).findByRole('region', { name: 'Sin datos' })).toBeInTheDocument();
    expect(within(section).queryByRole('alert')).toBeNull();
  });
});
