import { describe, expect, it } from 'vitest';
import { readAuthMode } from './authMode';

const TENANT = '11111111-2222-4333-8444-555555555555';
const SPA = '12345678-bbbb-4ccc-8ddd-eeeeeeeeeeee';
const API = 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee';
const ORIGIN = 'http://localhost:5173';

const DEV = {
  VITE_APP_ENV: 'dev',
  VITE_ENTRA_TENANT_ID: TENANT,
  VITE_ENTRA_SPA_CLIENT_ID: SPA,
  VITE_ENTRA_API_SCOPE: `api://${API}/access_as_user`,
};

describe('readAuthMode (U11, DT-099)', () => {
  it('is local without configuration: no Azure, no Entra ID', () => {
    expect(readAuthMode({}, ORIGIN)).toEqual({ kind: 'local' });
    expect(readAuthMode({ VITE_APP_ENV: 'local', VITE_ENTRA_TENANT_ID: TENANT }, ORIGIN)).toEqual({
      kind: 'local',
    });
  });

  it('dev builds the single-tenant MSAL settings for the API scope', () => {
    expect(readAuthMode(DEV, ORIGIN)).toEqual({
      kind: 'entra',
      entra: {
        tenantId: TENANT,
        clientId: SPA,
        apiScope: `api://${API}/access_as_user`,
        authority: `https://login.microsoftonline.com/${TENANT}`,
        redirectUri: 'http://localhost:5173',
      },
    });
    const docker = readAuthMode(
      { ...DEV, VITE_ENTRA_REDIRECT_URI: 'http://localhost:8080/' },
      ORIGIN,
    );
    expect(docker.kind === 'entra' && docker.entra.redirectUri).toBe('http://localhost:8080');
  });

  it('a dev build with missing or malformed identifiers fails closed', () => {
    const cases: Record<string, Record<string, string>> = {
      'no tenant': { ...DEV, VITE_ENTRA_TENANT_ID: '' },
      'common tenant': { ...DEV, VITE_ENTRA_TENANT_ID: 'common' },
      'no client': { ...DEV, VITE_ENTRA_SPA_CLIENT_ID: '' },
      'graph default scope': {
        ...DEV,
        VITE_ENTRA_API_SCOPE: 'https://graph.microsoft.com/.default',
      },
      'api default scope': { ...DEV, VITE_ENTRA_API_SCOPE: `api://${API}/.default` },
      'same app': { ...DEV, VITE_ENTRA_API_SCOPE: `api://${SPA}/access_as_user` },
      'http non-localhost redirect': { ...DEV, VITE_ENTRA_REDIRECT_URI: 'http://example.com' },
      'unknown environment': { ...DEV, VITE_APP_ENV: 'prod' },
    };
    for (const [name, env] of Object.entries(cases)) {
      const mode = readAuthMode(env, ORIGIN);
      expect(mode.kind, name).toBe('invalid');
      if (mode.kind === 'invalid') {
        expect(mode.problems.join(' ')).not.toContain(TENANT); // names variables, not values
      }
    }
    expect(readAuthMode(DEV, 'http://127.0.0.1:5173').kind).toBe('invalid');
  });

  it('accepts the HTTPS origin of the Azure frontend (U12, DT-100)', () => {
    const origin = 'https://ca-mpa-dev-frontend.example.centralus.azurecontainerapps.io';
    const mode = readAuthMode(DEV, origin);
    expect(mode.kind === 'entra' && mode.entra.redirectUri).toBe(origin);
    expect(readAuthMode(DEV, 'http://ca-mpa-dev-frontend.example.io').kind).toBe('invalid');
  });
});
