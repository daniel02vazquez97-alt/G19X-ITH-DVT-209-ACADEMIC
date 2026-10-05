// Paths of the API V1, relative to `/api`. Identifiers from the URL are encoded, never parsed: the
// API validates them (422 for an invalid identifier).
const id = (value: string | number) => encodeURIComponent(String(value));

export const API_PATHS = {
  products: '/v1/products',
  product: (productId: string | number) => `/v1/products/${id(productId)}`,
  productHistory: (productId: string | number) => `/v1/products/${id(productId)}/history`,
  productForecast: (productId: string | number) => `/v1/products/${id(productId)}/forecast`,
  productRecommendation: (productId: string | number) =>
    `/v1/products/${id(productId)}/recommendation`,
  inventory: '/v1/inventory',
  inventoryItem: (productId: string | number) => `/v1/inventory/${id(productId)}`,
  forecasts: '/v1/forecasts',
  recommendations: '/v1/recommendations',
  recommendation: (recommendationId: string | number) =>
    `/v1/recommendations/${id(recommendationId)}`,
  explanation: (recommendationId: string | number) =>
    `/v1/recommendations/${id(recommendationId)}/explanation`,
  run: (runId: string | number) => `/v1/runs/${id(runId)}`,
} as const;
