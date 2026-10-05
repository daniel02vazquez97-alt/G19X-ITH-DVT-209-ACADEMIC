import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { installFetch, jsonResponse, routeApi } from '../../test/api';
import { loginAs, renderApp } from '../../test/renderApp';
import RUN_2 from '../../test/responses/run-2.json';

describe('RunDetailPage (F7c, PLANNER and ADMIN)', () => {
  it('shows the run as the API stored it', async () => {
    installFetch(routeApi({ '/api/v1/runs/2': () => jsonResponse(200, RUN_2) }));
    const { user } = renderApp('/ejecuciones/2');
    await loginAs(user, 'ADMIN');
    expect(
      await screen.findByRole('heading', { name: 'Detalle de ejecución #2' }),
    ).toBeInTheDocument();
    expect(screen.getByText('RECOMMENDATION')).toBeInTheDocument();
    expect(
      screen.getByText('{"NO_NEED":40,"RECOMMEND":50,"NOT_CALCULABLE":10}'),
    ).toBeInTheDocument();
    expect(screen.getByText(RUN_2.versions.config_sha256)).toBeInTheDocument();
  });
});
