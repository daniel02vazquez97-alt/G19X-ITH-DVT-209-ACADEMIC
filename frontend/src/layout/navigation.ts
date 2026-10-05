import type { Resource } from '../roles/access';
import { PATHS } from '../routes/paths';

export interface NavigationItem {
  label: string;
  to: string;
  /** Resource the item needs; `null` for the home page. */
  resource: Resource | null;
}

// Only what V1 offers (DT-070 point 5). The product history lives inside the product detail.
export const NAVIGATION: readonly NavigationItem[] = [
  { label: 'Inicio', to: PATHS.home, resource: null },
  { label: 'Productos', to: PATHS.products, resource: 'products' },
  { label: 'Inventario', to: PATHS.inventory, resource: 'inventory' },
  { label: 'Recomendaciones', to: PATHS.recommendations, resource: 'recommendations' },
  { label: 'Predicciones', to: PATHS.forecasts, resource: 'forecasts' },
];
