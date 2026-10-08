// MSAL configuration and token acquisition (U11, DT-099). Authorization code flow with PKCE is the only
// flow of @azure/msal-browser 2+ (Microsoft Learn recommends it for single-page applications).
import {
  BrowserCacheLocation,
  CacheLookupPolicy,
  InteractionRequiredAuthError,
  PublicClientApplication,
  type AccountInfo,
  type Configuration,
  type IPublicClientApplication,
} from '@azure/msal-browser';
import type { EntraSettings } from '../authMode';

export function msalConfiguration(entra: EntraSettings): Configuration {
  return {
    auth: {
      clientId: entra.clientId,
      authority: entra.authority, // single tenant: never `common` or `organizations`
      redirectUri: entra.redirectUri,
      postLogoutRedirectUri: entra.redirectUri,
    },
    // Per-tab session storage, as in Microsoft's React tutorial: MSAL 5 refuses every redirect flow with
    // memory storage (`in_mem_redirect_unavailable`), and popups would need a redirect bridge page. It is
    // cleared when the tab closes; local storage is never used. This application never reads or writes
    // browser storage itself: only MSAL does (DT-099, deviation from docs/10 §4 recorded there).
    cache: { cacheLocation: BrowserCacheLocation.SessionStorage },
  };
}

export function createMsalInstance(entra: EntraSettings): PublicClientApplication {
  return new PublicClientApplication(msalConfiguration(entra));
}

/** What the session needs from MSAL; a port so that tests never run a real sign-in. */
export interface EntraSession {
  /** The signed-in account, if any (after `handleRedirectPromise`, done by `MsalProvider`). */
  account(): AccountInfo | null;
  /** Access token for the API, or `null` when an interactive redirect was started instead. */
  apiToken(): Promise<string | null>;
  login(): Promise<void>;
  logout(): Promise<void>;
}

/** Pure read (safe during render): the active account, or the only one MSAL knows in this page. */
export function currentAccount(instance: IPublicClientApplication): AccountInfo | null {
  return instance.getActiveAccount() ?? instance.getAllAccounts()[0] ?? null;
}

export function createEntraSession(
  instance: IPublicClientApplication,
  entra: EntraSettings,
): EntraSession {
  const scopes = [entra.apiScope];
  return {
    account: () => currentAccount(instance),

    async apiToken() {
      const account = currentAccount(instance);
      if (account === null) return null;
      if (instance.getActiveAccount() === null) instance.setActiveAccount(account);
      try {
        // Cached access token or refresh token only: no hidden iframe (MSAL 5 would need a redirect bridge).
        const result = await instance.acquireTokenSilent({
          scopes,
          account,
          cacheLookupPolicy: CacheLookupPolicy.AccessTokenAndRefreshToken,
        });
        return result.accessToken;
      } catch (error) {
        if (error instanceof InteractionRequiredAuthError) {
          await instance.acquireTokenRedirect({ scopes, account });
          return null;
        }
        throw error;
      }
    },

    login: () => instance.loginRedirect({ scopes }),

    async logout() {
      const account = currentAccount(instance);
      await instance.logoutRedirect({
        account: account ?? undefined,
        postLogoutRedirectUri: entra.redirectUri,
      });
    },
  };
}
