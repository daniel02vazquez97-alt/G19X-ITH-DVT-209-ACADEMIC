import {
  BrowserCacheLocation,
  CacheLookupPolicy,
  InteractionRequiredAuthError,
  type AccountInfo,
  type IPublicClientApplication,
} from '@azure/msal-browser';
import { describe, expect, it, vi } from 'vitest';
import type { EntraSettings } from '../authMode';
import { createEntraSession, currentAccount, msalConfiguration } from './msal';

const ENTRA: EntraSettings = {
  tenantId: '11111111-2222-4333-8444-555555555555',
  clientId: '12345678-bbbb-4ccc-8ddd-eeeeeeeeeeee',
  apiScope: 'api://aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee/access_as_user',
  authority: 'https://login.microsoftonline.com/11111111-2222-4333-8444-555555555555',
  redirectUri: 'http://localhost:5173',
};
const ACCOUNT = { homeAccountId: 'h', localAccountId: 'l', username: 'u' } as AccountInfo;

function fakeInstance(accounts: AccountInfo[] = [ACCOUNT]) {
  let active: AccountInfo | null = null;
  return {
    getActiveAccount: vi.fn(() => active),
    getAllAccounts: vi.fn(() => accounts),
    setActiveAccount: vi.fn((account: AccountInfo | null) => {
      active = account;
    }),
    acquireTokenSilent: vi.fn(async () => ({ accessToken: 'test-access-token' })),
    acquireTokenRedirect: vi.fn(async () => undefined),
    loginRedirect: vi.fn(async () => undefined),
    logoutRedirect: vi.fn(async () => undefined),
  };
}

function sessionOf(instance: ReturnType<typeof fakeInstance>) {
  return createEntraSession(instance as unknown as IPublicClientApplication, ENTRA);
}

describe('MSAL configuration (U11, DT-099)', () => {
  it('single tenant, registered redirect URI and per-tab session storage (never local storage)', () => {
    const config = msalConfiguration(ENTRA);
    expect(config.auth.clientId).toBe(ENTRA.clientId);
    expect(config.auth.authority).toBe(ENTRA.authority);
    expect(config.auth.redirectUri).toBe('http://localhost:5173');
    expect(config.cache?.cacheLocation).toBe(BrowserCacheLocation.SessionStorage);
    expect(config.cache?.cacheLocation).not.toBe(BrowserCacheLocation.MemoryStorage); // blocks redirects in MSAL 5
    expect(JSON.stringify(config)).not.toMatch(/secret|password|certificate/i);
  });
});

describe('Entra session', () => {
  it('asks for the API scope only, silently, without a hidden iframe', async () => {
    const instance = fakeInstance();
    expect(await sessionOf(instance).apiToken()).toBe('test-access-token');
    expect(instance.acquireTokenSilent).toHaveBeenCalledWith({
      scopes: [ENTRA.apiScope],
      account: ACCOUNT,
      cacheLookupPolicy: CacheLookupPolicy.AccessTokenAndRefreshToken,
    });
    expect(instance.setActiveAccount).toHaveBeenCalledWith(ACCOUNT);
  });

  it('falls back to an interactive redirect when interaction is required', async () => {
    const instance = fakeInstance();
    instance.acquireTokenSilent.mockRejectedValueOnce(
      new InteractionRequiredAuthError('login_required', 'test-correlation'),
    );
    expect(await sessionOf(instance).apiToken()).toBeNull();
    expect(instance.acquireTokenRedirect).toHaveBeenCalledWith({
      scopes: [ENTRA.apiScope],
      account: ACCOUNT,
    });
  });

  it('other failures are raised, not hidden', async () => {
    const instance = fakeInstance();
    instance.acquireTokenSilent.mockRejectedValueOnce(new Error('network'));
    await expect(sessionOf(instance).apiToken()).rejects.toThrow('network');
    expect(instance.acquireTokenRedirect).not.toHaveBeenCalled();
  });

  it('without an account there is no token and no request to Entra ID', async () => {
    const instance = fakeInstance([]);
    expect(await sessionOf(instance).apiToken()).toBeNull();
    expect(instance.acquireTokenSilent).not.toHaveBeenCalled();
    expect(currentAccount(instance as unknown as IPublicClientApplication)).toBeNull();
  });

  it('login and logout are redirects to Entra ID', async () => {
    const instance = fakeInstance();
    const session = sessionOf(instance);
    await session.login();
    expect(instance.loginRedirect).toHaveBeenCalledWith({ scopes: [ENTRA.apiScope] });
    await session.logout();
    expect(instance.logoutRedirect).toHaveBeenCalledWith({
      account: ACCOUNT,
      postLogoutRedirectUri: 'http://localhost:5173',
    });
  });
});
