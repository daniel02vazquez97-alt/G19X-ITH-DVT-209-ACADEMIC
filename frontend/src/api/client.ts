// Thin API client (DT-070 point 8): relative `/api` base, Bearer token on every request, uniform
// errors. It never transforms, recalculates or reinterprets the data it receives.
import { ApiError, errorFromResponse, networkError } from './errors';

export const API_BASE = '/api';

export type QueryValue = string | number | boolean | null | undefined;
export type Query = Readonly<Record<string, QueryValue>>;

export interface RequestOptions {
  query?: Query;
  signal?: AbortSignal;
  /** Explicit token (login check); otherwise the session token is used. */
  token?: string;
}

export interface UnauthorizedEvent {
  error: ApiError;
  /** Token that the rejected request carried. */
  token: string | null;
}

export interface ApiClientOptions {
  getToken: () => string | null;
  /** Called on every 401 of a request that used the session token. */
  onUnauthorized?: (event: UnauthorizedEvent) => void;
  fetchImpl?: typeof fetch;
}

export interface ApiClient {
  /** `path` is relative to `/api`, e.g. `/v1/products`. */
  get<T>(path: string, options?: RequestOptions): Promise<T>;
}

export function buildUrl(path: string, query?: Query): string {
  const search = new URLSearchParams();
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== null && value !== undefined && value !== '') {
        search.append(key, String(value));
      }
    }
  }
  const suffix = search.toString();
  return `${API_BASE}${path}${suffix ? `?${suffix}` : ''}`;
}

export function createApiClient(options: ApiClientOptions): ApiClient {
  const doFetch = options.fetchImpl ?? ((input, init) => fetch(input, init));

  return {
    async get<T>(path: string, request: RequestOptions = {}): Promise<T> {
      const usesSession = request.token === undefined;
      const token = usesSession ? options.getToken() : (request.token ?? null);
      const headers: Record<string, string> = { Accept: 'application/json' };
      if (token) {
        headers.Authorization = `Bearer ${token}`;
      }

      let response: Response;
      try {
        response = await doFetch(buildUrl(path, request.query), {
          method: 'GET',
          headers,
          signal: request.signal,
        });
      } catch (cause) {
        if (cause instanceof DOMException && cause.name === 'AbortError') {
          throw cause;
        }
        throw networkError(path);
      }

      if (!response.ok) {
        const error = await errorFromResponse(response, path);
        if (error.status === 401 && usesSession) {
          options.onUnauthorized?.({ error, token });
        }
        throw error;
      }
      return (await response.json()) as T;
    },
  };
}
