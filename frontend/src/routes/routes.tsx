import type { RouteObject } from 'react-router';
import { AuthGate } from '../auth/AuthGate';
import { ForbiddenState } from '../components/ForbiddenState';
import { AppShell } from '../layout/AppShell';
import { HomePage } from '../pages/HomePage';
import { NotFoundPage } from '../pages/NotFoundPage';
import { UnderConstructionPage } from '../pages/UnderConstructionPage';
import { RoleGate } from '../roles/RoleGate';
import { InventoryItemPage } from '../views/inventory/InventoryItemPage';
import { InventoryPage } from '../views/inventory/InventoryPage';
import { ProductDetailPage } from '../views/products/ProductDetailPage';
import { ProductsPage } from '../views/products/ProductsPage';
import { PATHS } from './paths';

const relative = (path: string) => path.slice(1);

export const routes: RouteObject[] = [
  {
    path: PATHS.home,
    element: (
      <AuthGate>
        <AppShell />
      </AuthGate>
    ),
    children: [
      { index: true, element: <HomePage /> },
      {
        path: relative(PATHS.products),
        element: <ProductsPage />,
      },
      {
        path: relative(PATHS.product),
        element: <ProductDetailPage />,
      },
      {
        path: relative(PATHS.inventory),
        element: <InventoryPage />,
      },
      {
        path: relative(PATHS.inventoryItem),
        element: <InventoryItemPage />,
      },
      {
        path: relative(PATHS.recommendations),
        element: <UnderConstructionPage title="Recomendaciones" unit="F7c" />,
      },
      {
        path: relative(PATHS.recommendation),
        element: <UnderConstructionPage title="Detalle de recomendación" unit="F7c" />,
      },
      {
        path: relative(PATHS.forecasts),
        element: <UnderConstructionPage title="Predicciones" unit="F7d" />,
      },
      {
        path: relative(PATHS.run),
        element: (
          <RoleGate resource="runs" fallback={<ForbiddenState />}>
            <UnderConstructionPage title="Detalle de ejecución" unit="F7c" />
          </RoleGate>
        ),
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
];
