// Stable URLs of the interface (DT-070 point 2). Selection lives in the path; filters and pagination
// live in the query string (see `listParams.ts`).
export const PATHS = {
  home: '/',
  products: '/productos',
  product: '/productos/:productId',
  inventory: '/inventario',
  inventoryItem: '/inventario/:productId',
  recommendations: '/recomendaciones',
  recommendation: '/recomendaciones/:recommendationId',
  forecasts: '/predicciones',
  run: '/ejecuciones/:runId',
} as const;

function withId(pattern: string, name: string, id: string | number): string {
  return pattern.replace(`:${name}`, encodeURIComponent(String(id)));
}

export const toProduct = (id: string | number) => withId(PATHS.product, 'productId', id);
export const toInventoryItem = (id: string | number) =>
  withId(PATHS.inventoryItem, 'productId', id);
export const toRecommendation = (id: string | number) =>
  withId(PATHS.recommendation, 'recommendationId', id);
export const toRun = (id: string | number) => withId(PATHS.run, 'runId', id);
