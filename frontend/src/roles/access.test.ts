import { describe, expect, it } from 'vitest';
import { ACCESS, canAccess, ROLES, type Resource } from './access';

// The matrix of `docs/07` §7.2 (backend/tests/api/_api_support.py, ENDPOINTS).
const EXPECTED: Record<Resource, string[]> = {
  products: ['VIEWER', 'ANALYST', 'PLANNER', 'ADMIN'],
  productDetail: ['VIEWER', 'ANALYST', 'PLANNER', 'ADMIN'],
  history: ['ANALYST', 'PLANNER', 'ADMIN'],
  inventory: ['VIEWER', 'ANALYST', 'PLANNER', 'ADMIN'],
  forecasts: ['VIEWER', 'ANALYST', 'PLANNER', 'ADMIN'],
  recommendations: ['VIEWER', 'ANALYST', 'PLANNER', 'ADMIN'],
  explanation: ['VIEWER', 'ANALYST', 'PLANNER', 'ADMIN'],
  runs: ['PLANNER', 'ADMIN'],
};

describe('role matrix', () => {
  it('copies docs/07 §7.2 exactly', () => {
    expect(Object.fromEntries(Object.entries(ACCESS).map(([k, v]) => [k, [...v]]))).toEqual(
      EXPECTED,
    );
  });

  it.each(ROLES)('%s sees exactly its resources', (role) => {
    for (const [resource, roles] of Object.entries(EXPECTED)) {
      expect(canAccess([role], resource as Resource)).toBe(roles.includes(role));
    }
  });

  it('has no hierarchy: ADMIN alone does not imply other roles, roles only add up', () => {
    expect(canAccess([], 'products')).toBe(false);
    expect(canAccess(['VIEWER', 'PLANNER'], 'runs')).toBe(true);
  });
});
