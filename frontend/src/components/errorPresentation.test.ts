import { describe, expect, it } from 'vitest';
import { ApiError } from '../api/errors';
import { presentError } from './errorPresentation';

function apiError(status: number, path = '/v1/products', code = 'SOME_CODE') {
  return new ApiError({ status, code, message: 'x', correlationId: 'corr-0001', path });
}

describe('error presentation (DT-070 point 9)', () => {
  it.each([
    [401, 'unauthenticated'],
    [403, 'forbidden'],
    [404, 'notFound'],
    [400, 'invalidFilter'],
    [422, 'invalidFilter'],
    [500, 'internal'],
    [503, 'unavailable'],
    [0, 'unavailable'],
    [405, 'generic'],
    [409, 'generic'],
    [429, 'generic'],
  ])('status %i is shown as %s', (status, kind) => {
    expect(presentError(apiError(status)).kind).toBe(kind);
  });

  it('403 says "Sin permiso para ver esto"', () => {
    expect(presentError(apiError(403)).title).toBe('Sin permiso para ver esto');
  });

  it.each(['/v1/products/7/recommendation', '/v1/products/7/forecast'])(
    '404 of %s is an empty state',
    (path) => {
      expect(presentError(apiError(404, path)).kind).toBe('empty');
    },
  );

  it.each(['/v1/products/7', '/v1/recommendations/7', '/v1/runs/7'])(
    '404 of %s is "No encontrado"',
    (path) => {
      expect(presentError(apiError(404, path))).toMatchObject({
        kind: 'notFound',
        title: 'No encontrado',
      });
    },
  );

  it('keeps the correlation id', () => {
    expect(presentError(apiError(500)).correlationId).toBe('corr-0001');
  });

  it('never shows the received value of an invalid filter', () => {
    const error = new ApiError({
      status: 422,
      code: 'VALIDATION_ERROR',
      message: 'page_size=valor-recibido-999',
      correlationId: null,
      path: '/v1/products',
    });
    const presentation = presentError(error);
    expect(`${presentation.title} ${presentation.message}`).not.toContain('valor-recibido-999');
  });

  it('503 and network failures offer a retry', () => {
    expect(presentError(apiError(503))).toMatchObject({
      title: 'Servicio no disponible',
      retryable: true,
    });
  });

  it('an unknown error is generic and has no correlation id', () => {
    expect(presentError(new Error('boom'))).toMatchObject({ kind: 'generic', correlationId: null });
  });
});
