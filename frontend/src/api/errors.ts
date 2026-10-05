// Client-side error of the API V1: the uniform body `{error: {code, message, details,
// correlation_id}}` (DT-066) plus the HTTP status. It never carries the token.

export const CORRELATION_HEADER = 'X-Correlation-ID';

/** Status used when the request never got an HTTP answer (network failure, proxy without API). */
export const NETWORK_ERROR_STATUS = 0;

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly correlationId: string | null;
  /** Requested path relative to the API base, without query string (e.g. `/v1/me`). */
  readonly path: string;

  constructor(options: {
    status: number;
    code: string;
    message: string;
    correlationId: string | null;
    path: string;
  }) {
    super(options.message);
    this.name = 'ApiError';
    this.status = options.status;
    this.code = options.code;
    this.correlationId = options.correlationId;
    this.path = options.path;
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

interface ErrorBody {
  code?: unknown;
  message?: unknown;
  correlation_id?: unknown;
}

function readErrorBody(payload: unknown): ErrorBody {
  if (typeof payload === 'object' && payload !== null && 'error' in payload) {
    const body = (payload as { error: unknown }).error;
    if (typeof body === 'object' && body !== null) {
      return body as ErrorBody;
    }
  }
  return {};
}

function text(value: unknown): string | null {
  return typeof value === 'string' && value !== '' ? value : null;
}

/** Builds the `ApiError` of a non-2xx response. The body may be missing or not be JSON. */
export async function errorFromResponse(response: Response, path: string): Promise<ApiError> {
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  const body = readErrorBody(payload);
  return new ApiError({
    status: response.status,
    code: text(body.code) ?? `HTTP_${response.status}`,
    message: text(body.message) ?? response.statusText,
    correlationId: text(body.correlation_id) ?? text(response.headers.get(CORRELATION_HEADER)),
    path,
  });
}

export function networkError(path: string): ApiError {
  return new ApiError({
    status: NETWORK_ERROR_STATUS,
    code: 'NETWORK_ERROR',
    message: 'Sin respuesta de la API.',
    correlationId: null,
    path,
  });
}
