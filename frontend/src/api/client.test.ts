import { describe, expect, it, vi } from 'vitest';
import { errorResponse, jsonResponse } from '../test/api';
import { buildUrl, createApiClient } from './client';
import { ApiError } from './errors';

function clientWith(response: Response | Error, token: string | null = 'dev-session-token-000001') {
  const fetchImpl = vi.fn(() =>
    response instanceof Error ? Promise.reject(response) : Promise.resolve(response),
  );
  const onUnauthorized = vi.fn();
  const client = createApiClient({ getToken: () => token, onUnauthorized, fetchImpl });
  return { client, fetchImpl, onUnauthorized };
}

async function rejection(promise: Promise<unknown>): Promise<ApiError> {
  try {
    await promise;
  } catch (error) {
    if (error instanceof ApiError) {
      return error;
    }
    throw error;
  }
  throw new Error('expected a rejection');
}

describe('API client', () => {
  it('uses the relative /api base and skips empty query values', () => {
    expect(buildUrl('/v1/products', { search: 'caja', page: 2, sort: '', category_id: null })).toBe(
      '/api/v1/products?search=caja&page=2',
    );
  });

  it('sends the session token as Bearer on every request', async () => {
    const { client, fetchImpl } = clientWith(jsonResponse(200, { ok: true }));
    await client.get('/v1/products');
    const [url, init] = fetchImpl.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe('/api/v1/products');
    expect(new Headers(init.headers).get('Authorization')).toBe('Bearer dev-session-token-000001');
    expect(init.method).toBe('GET');
  });

  it('returns the body untouched: decimals stay text', async () => {
    const body = { on_hand: '2623.500600092591729239380374', p: '238877404/109375' };
    const { client } = clientWith(jsonResponse(200, body));
    await expect(client.get('/v1/inventory/1')).resolves.toEqual(body);
  });

  it('maps the uniform error body and keeps the correlation id', async () => {
    const { client } = clientWith(errorResponse(404, 'PRODUCT_NOT_FOUND', 'corr-body-0001'));
    const error = await rejection(client.get('/v1/products/9'));
    expect(error).toMatchObject({
      status: 404,
      code: 'PRODUCT_NOT_FOUND',
      correlationId: 'corr-body-0001',
      path: '/v1/products/9',
    });
  });

  it('reads X-Correlation-ID when the body has no error document', async () => {
    const response = new Response('<html>bad gateway</html>', {
      status: 502,
      headers: { 'X-Correlation-ID': 'corr-header-001' },
    });
    const { client } = clientWith(response);
    const error = await rejection(client.get('/v1/products'));
    expect(error).toMatchObject({
      status: 502,
      code: 'HTTP_502',
      correlationId: 'corr-header-001',
    });
  });

  it('turns a network failure into status 0', async () => {
    const { client } = clientWith(new TypeError('Failed to fetch'));
    const error = await rejection(client.get('/v1/products'));
    expect(error).toMatchObject({ status: 0, code: 'NETWORK_ERROR' });
  });

  it('notifies a 401 of the session token', async () => {
    const { client, onUnauthorized } = clientWith(errorResponse(401, 'INVALID_TOKEN'));
    const error = await rejection(client.get('/v1/products'));
    expect(error.status).toBe(401);
    expect(onUnauthorized).toHaveBeenCalledWith({ error, token: 'dev-session-token-000001' });
  });

  it('does not notify a 401 of an explicit token (login check)', async () => {
    const { client, onUnauthorized } = clientWith(errorResponse(401, 'INVALID_TOKEN'), null);
    await rejection(client.get('/v1/me', { token: 'dev-wrong-token-0000001' }));
    expect(onUnauthorized).not.toHaveBeenCalled();
  });

  it('does not treat a 403 as a lost session', async () => {
    const { client, onUnauthorized } = clientWith(errorResponse(403, 'FORBIDDEN'));
    const error = await rejection(client.get('/v1/runs/1'));
    expect(error.status).toBe(403);
    expect(onUnauthorized).not.toHaveBeenCalled();
  });

  it('never puts the token in the error', async () => {
    const { client } = clientWith(errorResponse(401, 'INVALID_TOKEN'));
    const error = await rejection(client.get('/v1/products'));
    expect(JSON.stringify({ ...error, message: error.message })).not.toContain('dev-session-token');
  });
});
