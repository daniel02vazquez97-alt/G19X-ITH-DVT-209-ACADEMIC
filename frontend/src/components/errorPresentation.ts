// How every API error is shown (DT-070 point 9). One table for the whole interface: views never
// decide their own wording. Received values and technical details are never shown.
import { isApiError, NETWORK_ERROR_STATUS } from '../api/errors';

export type ErrorKind =
  | 'unauthenticated'
  | 'forbidden'
  | 'notFound'
  | 'empty'
  | 'invalidFilter'
  | 'internal'
  | 'unavailable'
  | 'generic';

export interface ErrorPresentation {
  kind: ErrorKind;
  title: string;
  message: string;
  correlationId: string | null;
  retryable: boolean;
}

/**
 * Endpoints whose 404 means "nothing for this product in the run" and is shown as an empty state:
 * `/products/{id}/recommendation` and `/products/{id}/forecast`.
 */
const NOT_FOUND_AS_EMPTY = [
  /^\/v1\/products\/[^/]+\/recommendation$/,
  /^\/v1\/products\/[^/]+\/forecast$/,
];

export function isEmptyOnNotFound(path: string): boolean {
  return NOT_FOUND_AS_EMPTY.some((pattern) => pattern.test(path));
}

export const FORBIDDEN_TITLE = 'Sin permiso para ver esto';

const GENERIC: Omit<ErrorPresentation, 'correlationId'> = {
  kind: 'generic',
  title: 'No se pudo completar la consulta',
  message: 'La API no pudo atender la petición. Inténtalo de nuevo más tarde.',
  retryable: true,
};

export function presentError(error: unknown): ErrorPresentation {
  if (!isApiError(error)) {
    return { ...GENERIC, correlationId: null };
  }
  const correlationId = error.correlationId;
  switch (error.status) {
    case 401:
      return {
        kind: 'unauthenticated',
        title: 'Sesión no válida',
        message: 'La sesión terminó o el token no es válido. Vuelve a entrar.',
        correlationId,
        retryable: false,
      };
    case 403:
      return {
        kind: 'forbidden',
        title: FORBIDDEN_TITLE,
        message: 'Tu rol no permite consultar este recurso. La sesión sigue abierta.',
        correlationId,
        retryable: false,
      };
    case 404:
      return isEmptyOnNotFound(error.path)
        ? {
            kind: 'empty',
            title: 'Sin datos',
            message: 'No hay datos de este producto en la ejecución consultada.',
            correlationId,
            retryable: false,
          }
        : {
            kind: 'notFound',
            title: 'No encontrado',
            message: 'El recurso solicitado no existe.',
            correlationId,
            retryable: false,
          };
    case 400:
    case 422:
      return {
        kind: 'invalidFilter',
        title: 'Filtro no válido',
        message:
          'Algún filtro o parámetro de la dirección no es válido. Revísalo e inténtalo de nuevo.',
        correlationId,
        retryable: false,
      };
    case 500:
      return {
        kind: 'internal',
        title: 'Error interno',
        message:
          'Ocurrió un error inesperado. Si se repite, comunica el identificador de correlación.',
        correlationId,
        retryable: true,
      };
    case 503:
    case NETWORK_ERROR_STATUS:
      return {
        kind: 'unavailable',
        title: 'Servicio no disponible',
        message: 'El servicio no responde en este momento. Reintenta en unos instantes.',
        correlationId,
        retryable: true,
      };
    default:
      // 405, 409, 429 and any other status: generic message.
      return { ...GENERIC, correlationId };
  }
}
