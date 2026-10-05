// Copy of the role matrix of `docs/07` §7.2 (DT-070 point 4): explicit roles per resource, no
// hierarchy. It only hides what a role cannot use; the backend enforces authorization (RS-003).

export const ROLES = ['VIEWER', 'ANALYST', 'PLANNER', 'ADMIN'] as const;
export type Role = (typeof ROLES)[number];

export function isRole(value: string): value is Role {
  return (ROLES as readonly string[]).includes(value);
}

export type Resource =
  | 'products'
  | 'productDetail'
  | 'history'
  | 'inventory'
  | 'forecasts'
  | 'recommendations'
  | 'explanation'
  | 'runs';

const ALL: readonly Role[] = ROLES;

export const ACCESS: Readonly<Record<Resource, readonly Role[]>> = {
  products: ALL, // GET /products
  productDetail: ALL, // GET /products/{id}, /products/{id}/forecast, /products/{id}/recommendation
  history: ['ANALYST', 'PLANNER', 'ADMIN'], // GET /products/{id}/history
  inventory: ALL, // GET /inventory, /inventory/{product_id}
  forecasts: ALL, // GET /forecasts
  recommendations: ALL, // GET /recommendations, /recommendations/{id}
  explanation: ALL, // GET /recommendations/{id}/explanation
  runs: ['PLANNER', 'ADMIN'], // GET /runs/{run_id}
};

export function canAccess(roles: readonly Role[], resource: Resource): boolean {
  return roles.some((role) => ACCESS[resource].includes(role));
}
