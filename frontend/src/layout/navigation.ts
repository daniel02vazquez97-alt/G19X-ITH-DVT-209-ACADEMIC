import type { Resource } from '../roles/access';
import { PATHS } from '../routes/paths';

export interface NavigationItem {
  label: string;
  to: string;
  /** Resource the item needs; `null` for the home page. */
  resource: Resource | null;
  /** One line for the card of the home page. */
  description: string;
}

// Only what V1 offers (DT-070 point 5) plus the documentary assistant (U15b, DT-103). The product history lives
// inside the product detail.
export const NAVIGATION: readonly NavigationItem[] = [
  { label: 'Inicio', to: PATHS.home, resource: null, description: '' },
  {
    label: 'Productos',
    to: PATHS.products,
    resource: 'products',
    description: 'Catálogo con estado, categoría y proveedores de cada producto.',
  },
  {
    label: 'Inventario',
    to: PATHS.inventory,
    resource: 'inventory',
    description: 'Existencias a la fecha de corte y líneas de compra abiertas.',
  },
  {
    label: 'Recomendaciones',
    to: PATHS.recommendations,
    resource: 'recommendations',
    description: 'Qué comprar, cuánto y cuándo, con el cálculo y su explicación.',
  },
  {
    label: 'Predicciones',
    to: PATHS.forecasts,
    resource: 'forecasts',
    description: 'Pronóstico semanal de la demanda con su banda de incertidumbre.',
  },
  {
    label: 'Asistente',
    to: PATHS.assistant,
    resource: 'assistant',
    description: 'Preguntas sobre los documentos del proyecto, con las fuentes citadas.',
  },
];
