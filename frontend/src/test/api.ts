// Test doubles of the API V1. The tokens are fictitious test values, like those of
// `backend/tests/api/_api_support.py`; they are not registered anywhere.
import { vi } from 'vitest';
import type { Role } from '../roles/access';

export const TEST_TOKENS: Record<Role, string> = {
  VIEWER: 'dev-test-viewer-token-0001',
  ANALYST: 'dev-test-analyst-token-001',
  PLANNER: 'dev-test-planner-token-001',
  ADMIN: 'dev-test-admin-token-00001',
};

export const CORRELATION_ID = 'corr-test-0001';

export function jsonResponse(status: number, body: unknown, correlationId = CORRELATION_ID) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', 'X-Correlation-ID': correlationId },
  });
}

export function errorResponse(status: number, code: string, correlationId = CORRELATION_ID) {
  return jsonResponse(
    status,
    { error: { code, message: 'Mensaje de la API.', details: {}, correlation_id: correlationId } },
    correlationId,
  );
}

export function bearerOf(init: RequestInit | undefined): string | null {
  const headers = new Headers(init?.headers);
  const value = headers.get('Authorization');
  return value?.startsWith('Bearer ') ? value.slice('Bearer '.length) : null;
}

export type Handler = (url: URL, init: RequestInit | undefined) => Response | Promise<Response>;

/** `GET /api/v1/me` for the test tokens; anything else goes to `next`. */
export function withMe(next: Handler = () => errorResponse(404, 'NOT_FOUND')): Handler {
  return (url, init) => {
    if (url.pathname === '/api/v1/me') {
      const token = bearerOf(init);
      const role = (Object.keys(TEST_TOKENS) as Role[]).find((key) => TEST_TOKENS[key] === token);
      if (role === undefined) {
        return errorResponse(401, token === null ? 'AUTHENTICATION_REQUIRED' : 'INVALID_TOKEN');
      }
      return jsonResponse(200, { subject_id: `dev-${role.toLowerCase()}`, roles: [role] });
    }
    return next(url, init);
  };
}

export function installFetch(handler: Handler) {
  const mock = vi.fn((input: RequestInfo | URL, init?: RequestInit) =>
    Promise.resolve(handler(new URL(String(input), 'http://localhost'), init)),
  );
  vi.stubGlobal('fetch', mock);
  return mock;
}

/** Routes `GET /api/...` by pathname (after `/me`); unknown paths answer 404. */
export function routeApi(routes: Record<string, (url: URL) => Response>): Handler {
  return withMe((url) => {
    const route = routes[url.pathname];
    return route ? route(url) : errorResponse(404, 'NOT_FOUND');
  });
}

/** Paths and query strings the app requested, without `/api/v1/me`. */
export function requestedUrls(mock: { mock: { calls: unknown[][] } }): string[] {
  return mock.mock.calls
    .map(([input]) => String(input))
    .filter((url) => !url.startsWith('/api/v1/me'));
}
