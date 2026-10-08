// The real @azure/msal-react provider with a real PublicClientApplication, without any sign-in: MSAL
// initializes, finds no account and the app offers the Microsoft sign-in (U11, DT-099).
import { render, screen } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { describe, expect, it } from 'vitest';
import { createQueryClient } from '../../AppProviders';
import { readAuthMode } from '../authMode';
import { routes } from '../../routes/routes';
import { installFetch, errorResponse } from '../../test/api';
import { EntraAppProviders } from './EntraAppProviders';
import { createMsalInstance } from './msal';

describe('MsalEntraRoot', () => {
  it('starts MSAL and shows the Microsoft sign-in when nobody is signed in', async () => {
    const fetchMock = installFetch(() => errorResponse(401, 'AUTHENTICATION_REQUIRED'));
    const mode = readAuthMode(
      {
        VITE_APP_ENV: 'dev',
        VITE_ENTRA_TENANT_ID: '11111111-2222-4333-8444-555555555555',
        VITE_ENTRA_SPA_CLIENT_ID: '12345678-bbbb-4ccc-8ddd-eeeeeeeeeeee',
        VITE_ENTRA_API_SCOPE: 'api://aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee/access_as_user',
      },
      'http://localhost:5173',
    );
    if (mode.kind !== 'entra') throw new Error('expected an Entra ID configuration');
    render(
      <EntraAppProviders
        queryClient={createQueryClient()}
        instance={createMsalInstance(mode.entra)}
        entra={mode.entra}
      >
        <RouterProvider router={createMemoryRouter(routes, { initialEntries: ['/'] })} />
      </EntraAppProviders>,
    );
    expect(
      await screen.findByRole('button', { name: 'Iniciar sesión con Microsoft' }),
    ).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled(); // no account: no token, no API call
  });
});
