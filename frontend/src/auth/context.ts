import { createContext, useContext } from 'react';
import type { ApiClient } from '../api/client';
import type { Identity } from './authenticator';

export interface AuthContextValue {
  /** `local`: development token (DT-070); `entra`: Microsoft Entra ID with MSAL (U11, DT-099). */
  mode: 'local' | 'entra';
  /** Identity of the open session, or `null` when nobody is signed in. */
  identity: Identity | null;
  /** `entra` only: a signed-in account is being turned into a session (token and `GET /me`). */
  checking: boolean;
  /** Why the last session ended without a logout (a 401), if it did. */
  sessionNotice: string | null;
  /** `local`: validates a development token. `entra`: starts the Microsoft sign-in (redirect). */
  login(credential: string): Promise<void>;
  logout(): void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);
export const ApiClientContext = createContext<ApiClient | null>(null);

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (value === null) {
    throw new Error('useAuth must be used inside <AuthProvider>');
  }
  return value;
}

export function useApiClient(): ApiClient {
  const value = useContext(ApiClientContext);
  if (value === null) {
    throw new Error('useApiClient must be used inside <AuthProvider>');
  }
  return value;
}
