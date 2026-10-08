import { screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { errorResponse, installFetch, jsonResponse, withMe } from '../test/api';
import { loginAs, renderApp } from '../test/renderApp';
import { matchesMatrix } from './AccessCheckPage';

describe('AccessCheckPage (U11, DT-099)', () => {
  it('asks the API for every endpoint and compares the answers with the role matrix', async () => {
    // The API of the test: runs and history are forbidden, everything else answers.
    installFetch(
      withMe((url) =>
        /\/runs\/|\/history$/.test(url.pathname)
          ? errorResponse(403, 'FORBIDDEN')
          : jsonResponse(200, {}),
      ),
    );
    const { user } = renderApp('/acceso');
    await loginAs(user, 'VIEWER');
    await user.click(screen.getByRole('button', { name: 'Comprobar la matriz rol × endpoint' }));
    const rows = await screen.findAllByRole('row');
    expect(rows).toHaveLength(14); // header + 13 endpoints
    const runs = rows.find((row) => row.textContent?.includes('/runs/1'));
    expect(
      within(runs as HTMLElement)
        .getAllByRole('cell')
        .map((c) => c.textContent),
    ).toEqual(['GET /api/v1/runs/1', 'no', '403', 'sí']);
    expect(screen.queryByText('NO')).not.toBeInTheDocument();
    expect(document.body.innerHTML).not.toMatch(/dev-test-viewer-token/);
  });

  it('a 403 where the matrix allows, or a 200 where it forbids, does not match', () => {
    expect(matchesMatrix({ path: '/v1/products', allowed: true, status: 403 })).toBe(false);
    expect(matchesMatrix({ path: '/v1/runs/1', allowed: false, status: 200 })).toBe(false);
    expect(matchesMatrix({ path: '/v1/products/1', allowed: true, status: 404 })).toBe(true);
  });
});
