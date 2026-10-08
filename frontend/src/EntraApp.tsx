// The application with Microsoft Entra ID (U11, DT-099). Loaded on demand only by `dev` builds, so MSAL
// never reaches the bundle that a `local` build executes.
import { useState } from 'react';
import { createBrowserRouter, RouterProvider } from 'react-router';
import { createQueryClient } from './AppProviders';
import type { EntraSettings } from './auth/authMode';
import { EntraAppProviders } from './auth/entra/EntraAppProviders';
import { createMsalInstance } from './auth/entra/msal';
import { routes } from './routes/routes';

export default function EntraApp({ entra }: { entra: EntraSettings }) {
  const [queryClient] = useState(createQueryClient);
  const [router] = useState(() => createBrowserRouter(routes));
  const [instance] = useState(() => createMsalInstance(entra));
  return (
    <EntraAppProviders queryClient={queryClient} instance={instance} entra={entra}>
      <RouterProvider router={router} />
    </EntraAppProviders>
  );
}
