import { lazy, Suspense, useState } from 'react';
import { createBrowserRouter, RouterProvider } from 'react-router';
import { AppProviders, createQueryClient } from './AppProviders';
import { readAuthMode } from './auth/authMode';
import { ConfigErrorPage } from './auth/ConfigErrorPage';
import { routes } from './routes/routes';

// `local` unless the build sets VITE_APP_ENV=dev with the Entra ID identifiers (U11, DT-099).
const AUTH_MODE = readAuthMode(import.meta.env, window.location.origin);
const EntraApp = lazy(() => import('./EntraApp'));

function LocalApp() {
  const [queryClient] = useState(createQueryClient);
  const [router] = useState(() => createBrowserRouter(routes));
  return (
    <AppProviders queryClient={queryClient}>
      <RouterProvider router={router} />
    </AppProviders>
  );
}

export function App() {
  if (AUTH_MODE.kind === 'invalid') {
    return <ConfigErrorPage problems={AUTH_MODE.problems} />;
  }
  if (AUTH_MODE.kind === 'entra') {
    return (
      <Suspense fallback={null}>
        <EntraApp entra={AUTH_MODE.entra} />
      </Suspense>
    );
  }
  return <LocalApp />;
}
