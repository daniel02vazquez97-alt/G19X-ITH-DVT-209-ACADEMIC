// Access check of the signed-in identity (U11, DT-099, real test of dev): asks the API for every endpoint of
// `docs/07` §7.2 with the session token and shows only the HTTP status and whether it matches the role
// matrix. The interface hides what a role cannot use, so this page is how a real 403 from the backend is
// seen without copying a token anywhere. Read-only GETs; not in the navigation (URL `/acceso`).
import { useState } from 'react';
import { isApiError } from '../api/errors';
import { canAccess, type Resource } from '../roles/access';
import { useApiClient, useAuth } from './context';

interface Probe {
  path: string;
  /** `null`: any authenticated identity (`GET /me`). */
  resource: Resource | null;
}

// Sample identifiers 1, as in the backend's role-matrix tests: a 404 still proves authorization passed.
const PROBES: Probe[] = [
  { path: '/v1/me', resource: null },
  { path: '/v1/products', resource: 'products' },
  { path: '/v1/products/1', resource: 'productDetail' },
  { path: '/v1/products/1/history', resource: 'history' },
  { path: '/v1/products/1/forecast', resource: 'productDetail' },
  { path: '/v1/products/1/recommendation', resource: 'productDetail' },
  { path: '/v1/inventory', resource: 'inventory' },
  { path: '/v1/inventory/1', resource: 'inventory' },
  { path: '/v1/forecasts', resource: 'forecasts' },
  { path: '/v1/recommendations', resource: 'recommendations' },
  { path: '/v1/recommendations/1', resource: 'recommendations' },
  { path: '/v1/recommendations/1/explanation', resource: 'explanation' },
  { path: '/v1/runs/1', resource: 'runs' },
];

interface Result {
  path: string;
  allowed: boolean;
  status: number;
}

export function matchesMatrix(result: Result): boolean {
  return result.allowed ? result.status !== 401 && result.status !== 403 : result.status === 403;
}

export function AccessCheckPage() {
  const client = useApiClient();
  const { identity } = useAuth();
  const [results, setResults] = useState<Result[] | null>(null);
  const [running, setRunning] = useState(false);
  const roles = identity?.roles ?? [];

  async function run() {
    setRunning(true);
    const collected: Result[] = [];
    for (const probe of PROBES) {
      let status: number;
      try {
        await client.get(probe.path);
        status = 200;
      } catch (error) {
        status = isApiError(error) ? error.status : -1;
      }
      collected.push({
        path: probe.path,
        allowed: probe.resource === null || canAccess(roles, probe.resource),
        status,
      });
    }
    setResults(collected);
    setRunning(false);
  }

  return (
    <section>
      <h1>Comprobación de acceso</h1>
      <p>
        Roles de la sesión: {roles.length > 0 ? roles.join(', ') : 'ninguno'}. Cada fila es una
        petición real a la API; solo se muestra el código HTTP.
      </p>
      <button type="button" className="button button--primary" disabled={running} onClick={run}>
        {running ? 'Comprobando…' : 'Comprobar la matriz rol × endpoint'}
      </button>
      {results ? (
        <table>
          <thead>
            <tr>
              <th scope="col">Endpoint</th>
              <th scope="col">Permitido por la matriz</th>
              <th scope="col">Respuesta</th>
              <th scope="col">Coincide</th>
            </tr>
          </thead>
          <tbody>
            {results.map((result) => (
              <tr key={result.path}>
                <td>
                  <code>GET /api{result.path}</code>
                </td>
                <td>{result.allowed ? 'sí' : 'no'}</td>
                <td>{result.status}</td>
                <td>{matchesMatrix(result) ? 'sí' : 'NO'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </section>
  );
}
