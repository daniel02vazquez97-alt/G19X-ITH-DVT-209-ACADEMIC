import { screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useApiQuery } from '../api/useApiQuery';
import { ErrorState } from '../components/ErrorState';
import { routes } from '../routes/routes';
import {
  bearerOf,
  errorResponse,
  installFetch,
  jsonResponse,
  TEST_TOKENS,
  withMe,
} from '../test/api';
import { loginAs, renderApp } from '../test/renderApp';

// A probe page that queries one path, to exercise the session against API answers.
function Probe({ path }: { path: string }) {
  const query = useApiQuery<{ value: string }>(path);
  if (query.isPending) return <p>cargando</p>;
  if (query.isError) return <ErrorState error={query.error} />;
  return <p>valor: {query.data.value}</p>;
}

beforeEach(() => {
  const shell = routes[0];
  shell?.children?.push(
    { path: 'prueba-ok', element: <Probe path="/v1/probe/ok" /> },
    { path: 'prueba-401', element: <Probe path="/v1/probe/401" /> },
    { path: 'prueba-403', element: <Probe path="/v1/probe/403" /> },
  );
});

afterEach(() => {
  const children = routes[0]?.children;
  children?.splice(children.length - 3, 3);
});

function probeApi() {
  return installFetch(
    withMe((url, init) => {
      if (url.pathname === '/api/v1/probe/ok') {
        return bearerOf(init) === TEST_TOKENS.PLANNER
          ? jsonResponse(200, { value: '2623.500600092591729239380374' })
          : errorResponse(401, 'INVALID_TOKEN');
      }
      if (url.pathname === '/api/v1/probe/401') return errorResponse(401, 'INVALID_TOKEN');
      if (url.pathname === '/api/v1/probe/403') return errorResponse(403, 'FORBIDDEN');
      return errorResponse(404, 'NOT_FOUND');
    }),
  );
}

describe('AuthProvider (DT-070 point 3)', () => {
  it('shows nothing but the login form before the token is validated', () => {
    probeApi();
    renderApp('/productos');
    expect(screen.getByLabelText('Token de desarrollo')).toBeInTheDocument();
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
  });

  it('validates the token with GET /api/v1/me and keeps the URL', async () => {
    const fetchMock = probeApi();
    const { user, router } = renderApp('/productos');
    await loginAs(user, 'PLANNER');
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe('/api/v1/me');
    expect(bearerOf(init)).toBe(TEST_TOKENS.PLANNER);
    expect(router.state.location.pathname).toBe('/productos');
    expect(screen.getByText(/dev-planner/)).toBeInTheDocument();
  });

  it('rejects an unknown token without opening a session', async () => {
    probeApi();
    const { user } = renderApp('/');
    await user.type(screen.getByLabelText('Token de desarrollo'), 'dev-unknown-token-00000001');
    await user.click(screen.getByRole('button', { name: 'Entrar' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('El token no es válido');
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
  });

  it('sends the session token as Bearer on later requests', async () => {
    probeApi();
    const { user } = renderApp('/prueba-ok');
    await loginAs(user, 'PLANNER');
    expect(await screen.findByText('valor: 2623.500600092591729239380374')).toBeInTheDocument();
  });

  it('logout discards the token: the next login starts from scratch', async () => {
    const fetchMock = probeApi();
    const { user } = renderApp('/');
    await loginAs(user, 'PLANNER');
    await user.click(screen.getByRole('button', { name: 'Cerrar sesión' }));
    expect(screen.getByLabelText('Token de desarrollo')).toHaveValue('');
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('a 401 on any request ends the session and goes back to login', async () => {
    probeApi();
    const { user, router } = renderApp('/prueba-401');
    await loginAs(user, 'PLANNER');
    expect(await screen.findByRole('status')).toHaveTextContent('La sesión ya no es válida');
    expect(screen.getByLabelText('Token de desarrollo')).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/prueba-401');
  });

  it('a 403 shows "Sin permiso para ver esto" and keeps the session', async () => {
    probeApi();
    const { user } = renderApp('/prueba-403');
    await loginAs(user, 'PLANNER');
    expect(await screen.findByRole('alert')).toHaveTextContent('Sin permiso para ver esto');
    expect(screen.getByRole('navigation', { name: 'Navegación principal' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Cerrar sesión' })).toBeInTheDocument();
  });

  it('never touches localStorage or sessionStorage and never shows the token', async () => {
    const setItem = vi.spyOn(Storage.prototype, 'setItem');
    const getItem = vi.spyOn(Storage.prototype, 'getItem');
    probeApi();
    const { user, container } = renderApp('/prueba-ok');
    await loginAs(user, 'PLANNER');
    await screen.findByText(/valor:/);
    await user.click(screen.getByRole('button', { name: 'Cerrar sesión' }));
    await waitFor(() => expect(screen.getByLabelText('Token de desarrollo')).toBeInTheDocument());
    expect(setItem).not.toHaveBeenCalled();
    // React Router itself reads its view-transition key; the session never reads storage.
    const readKeys = getItem.mock.calls.map(([key]) => key);
    expect(readKeys.filter((key) => key !== 'remix-router-transitions')).toEqual([]);
    expect(localStorage).toHaveLength(0);
    expect(sessionStorage).toHaveLength(0);
    expect(container.innerHTML).not.toContain(TEST_TOKENS.PLANNER);
  });
});
