// Regression of 2026-10-07 (`in_mem_redirect_unavailable`): the REAL PublicClientApplication with our
// configuration must start the sign-in redirect. Navigation is intercepted, so nothing leaves the test; the
// authorize URL proves authorization code + PKCE, the API scope only and the registered redirect URI.
import type { INavigationClient } from '@azure/msal-browser';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { readAuthMode } from '../authMode';
import { createMsalInstance } from './msal';

const TENANT = '11111111-2222-4333-8444-555555555555';
const SPA = '12345678-bbbb-4ccc-8ddd-eeeeeeeeeeee';
const SCOPE = 'api://aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee/access_as_user';

afterEach(() => {
  sessionStorage.clear(); // MSAL's interaction state of the test
});

describe('MSAL sign-in redirect with the real library', () => {
  it('loginRedirect builds an authorization code + PKCE request for the API scope', async () => {
    const mode = readAuthMode(
      {
        VITE_APP_ENV: 'dev',
        VITE_ENTRA_TENANT_ID: TENANT,
        VITE_ENTRA_SPA_CLIENT_ID: SPA,
        VITE_ENTRA_API_SCOPE: SCOPE,
      },
      'http://localhost:8080',
    );
    if (mode.kind !== 'entra') throw new Error('expected an Entra ID configuration');
    const instance = createMsalInstance(mode.entra);
    await instance.initialize();
    const navigateExternal = vi.fn(async () => true);
    const navigation: INavigationClient = {
      navigateExternal,
      navigateInternal: vi.fn(async () => true),
    };
    instance.setNavigationClient(navigation);

    await instance.loginRedirect({ scopes: [mode.entra.apiScope] });

    expect(navigateExternal).toHaveBeenCalledTimes(1);
    const url = new URL(String((navigateExternal.mock.calls[0] as unknown[])[0]));
    expect(`${url.origin}${url.pathname}`).toBe(
      `https://login.microsoftonline.com/${TENANT}/oauth2/v2.0/authorize`,
    );
    const params = url.searchParams;
    expect(params.get('client_id')).toBe(SPA);
    expect(params.get('response_type')).toBe('code');
    expect(params.get('code_challenge_method')).toBe('S256');
    expect(params.get('code_challenge')).toMatch(/^[A-Za-z0-9_-]{43}$/);
    expect(params.get('redirect_uri')).toBe('http://localhost:8080');
    expect(params.get('scope')?.split(' ').sort()).toEqual(
      [SCOPE, 'offline_access', 'openid', 'profile'].sort(),
    );
    expect(url.search).not.toMatch(/client_secret|response_type=token|graph\.microsoft\.com/);
  });
});
