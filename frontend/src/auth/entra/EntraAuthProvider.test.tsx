// Session with Microsoft Entra ID (U11, DT-099) without a real sign-in: a fake session port plays MSAL and
// a fake fetch plays the API, which accepts only the access token that the session handed out.
import type { AccountInfo } from '@azure/msal-browser';
import { QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createQueryClient } from '../../AppProviders';
import { useApiQuery } from '../../api/useApiQuery';
import { ErrorState } from '../../components/ErrorState';
import { routes } from '../../routes/routes';
import { bearerOf, errorResponse, installFetch, jsonResponse } from '../../test/api';
import { ENTRA_EXPIRED_NOTICE, EntraAuthProvider } from './EntraAuthProvider';
import type { EntraSession } from './msal';

const OID = '0f0f0f0f-1111-4222-8333-444444444444';
const ACCOUNT = { homeAccountId: 'h', localAccountId: OID, username: 'u' } as AccountInfo;

function Probe({ path }: { path: string }) {
  const query = useApiQuery<{ value: string }>(path);
  if (query.isPending) return <p>cargando</p>;
  if (query.isError) return <ErrorState error={query.error} />;
  return <p>valor: {query.data.value}</p>;
}

beforeEach(() => {
  routes[0]?.children?.push(
    { path: 'prueba-ok', element: <Probe path="/v1/probe/ok" /> },
    { path: 'prueba-401', element: <Probe path="/v1/probe/401" /> },
    { path: 'prueba-403', element: <Probe path="/v1/probe/403" /> },
  );
});

afterEach(() => {
  const children = routes[0]?.children;
  children?.splice(children.length - 3, 3);
});

function fakeSession(signedIn: boolean) {
  let account: AccountInfo | null = signedIn ? ACCOUNT : null;
  let issued = 0;
  const session = {
    account: vi.fn(() => account),
    apiToken: vi.fn(async () => (account === null ? null : `test-access-token-${++issued}`)),
    login: vi.fn(async () => {
      account = ACCOUNT;
    }),
    logout: vi.fn(async () => {
      account = null;
    }),
  } satisfies EntraSession;
  return session;
}

/** The API: any token the fake session issued is valid; the roles are those of `roles`. */
function fakeApi(roles: string[] = ['VIEWER'], meStatus = 200) {
  return installFetch((url, init) => {
    const token = bearerOf(init);
    const valid = token !== null && token.startsWith('test-access-token-');
    if (!valid)
      return errorResponse(401, token === null ? 'AUTHENTICATION_REQUIRED' : 'INVALID_TOKEN');
    if (url.pathname === '/api/v1/me') {
      return meStatus === 200
        ? jsonResponse(200, { subject_id: OID, roles })
        : errorResponse(meStatus, 'INVALID_TOKEN');
    }
    if (url.pathname === '/api/v1/probe/ok') return jsonResponse(200, { value: 'datos' });
    if (url.pathname === '/api/v1/probe/401') return errorResponse(401, 'INVALID_TOKEN');
    if (url.pathname === '/api/v1/probe/403') return errorResponse(403, 'FORBIDDEN');
    return errorResponse(404, 'NOT_FOUND');
  });
}

function renderEntra(
  session: EntraSession,
  path = '/',
  options: { ready?: boolean; interactionError?: unknown } = {},
) {
  const queryClient = createQueryClient();
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  const user = userEvent.setup();
  const view = render(
    <QueryClientProvider client={queryClient}>
      <EntraAuthProvider
        session={session}
        ready={options.ready ?? true}
        interactionError={options.interactionError}
      >
        <RouterProvider router={router} />
      </EntraAuthProvider>
    </QueryClientProvider>,
  );
  return { ...view, user, router };
}

describe('EntraAuthProvider (U11, DT-099)', () => {
  it('without an account shows only the Microsoft sign-in, which starts the redirect', async () => {
    const fetchMock = fakeApi();
    const session = fakeSession(false);
    const { user } = renderEntra(session, '/productos');
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Token de desarrollo')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Iniciar sesión con Microsoft' }));
    expect(session.login).toHaveBeenCalledTimes(1);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('waits for MSAL before deciding', () => {
    fakeApi();
    renderEntra(fakeSession(true), '/', { ready: false });
    expect(screen.getByText('Comprobando la sesión…')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Iniciar sesión con Microsoft' })).toBeNull();
  });

  it('a signed-in account opens the session with GET /me and the access token', async () => {
    const fetchMock = fakeApi(['PLANNER']);
    const { router } = renderEntra(fakeSession(true), '/productos');
    await screen.findByRole('navigation', { name: 'Navegación principal' });
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe('/api/v1/me');
    expect(bearerOf(init)).toBe('test-access-token-1');
    expect(screen.getByText(new RegExp(OID))).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/productos');
  });

  it('every API call carries a token from MSAL as Bearer, never in the URL', async () => {
    const fetchMock = fakeApi();
    renderEntra(fakeSession(true), '/prueba-ok');
    expect(await screen.findByText('valor: datos')).toBeInTheDocument();
    for (const [input, init] of fetchMock.mock.calls as unknown as [string, RequestInit][]) {
      expect(bearerOf(init)).toMatch(/^test-access-token-\d+$/);
      expect(input).not.toContain('token');
    }
  });

  it('a 403 keeps the session and shows the forbidden state', async () => {
    fakeApi(['VIEWER']);
    renderEntra(fakeSession(true), '/prueba-403');
    expect(await screen.findByRole('alert')).toHaveTextContent('Sin permiso para ver esto');
    expect(screen.getByRole('button', { name: 'Cerrar sesión' })).toBeInTheDocument();
  });

  it('a 401 ends the session once, without re-entering by itself', async () => {
    const fetchMock = fakeApi();
    renderEntra(fakeSession(true), '/prueba-401');
    expect(await screen.findByText(ENTRA_EXPIRED_NOTICE)).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Iniciar sesión con Microsoft' }),
    ).toBeInTheDocument();
    const calls = fetchMock.mock.calls.length;
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(fetchMock.mock.calls.length).toBe(calls);
  });

  it('a token the API rejects at /me does not open a session', async () => {
    fakeApi(['VIEWER'], 401);
    renderEntra(fakeSession(true));
    expect(await screen.findByText(/La API rechazó el token/)).toBeInTheDocument();
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
  });

  it('logout clears the session and signs out of Entra ID', async () => {
    fakeApi();
    const session = fakeSession(true);
    const { user } = renderEntra(session);
    await screen.findByRole('navigation', { name: 'Navegación principal' });
    await user.click(screen.getByRole('button', { name: 'Cerrar sesión' }));
    expect(session.logout).toHaveBeenCalledTimes(1);
    expect(
      screen.getByRole('button', { name: 'Iniciar sesión con Microsoft' }),
    ).toBeInTheDocument();
  });

  it('shows the MSAL error code of a failed interaction (e.g. user not assigned)', () => {
    fakeApi();
    renderEntra(fakeSession(false), '/', { interactionError: { errorCode: 'access_denied' } });
    expect(screen.getByRole('status')).toHaveTextContent('código access_denied');
  });

  it('a redirect in progress sends no request', async () => {
    const fetchMock = fakeApi();
    const session = fakeSession(true);
    session.apiToken.mockResolvedValue(null);
    renderEntra(session);
    await waitFor(() => expect(session.apiToken).toHaveBeenCalled());
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('never renders a token and never uses browser storage itself', async () => {
    const setItem = vi.spyOn(Storage.prototype, 'setItem');
    fakeApi();
    const { container } = renderEntra(fakeSession(true), '/prueba-ok');
    await screen.findByText('valor: datos');
    expect(container.innerHTML).not.toContain('test-access-token');
    expect(setItem).not.toHaveBeenCalled();
  });
});
