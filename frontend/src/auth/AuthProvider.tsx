// Session in memory only (DT-070 point 3): the token lives in this provider and disappears on
// logout, on a 401 and on any page reload. Nothing is written to browser storage.
import { useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo, useState, type ReactNode } from 'react';
import { createApiClient, type UnauthorizedEvent } from '../api/client';
import { createDevTokenAuthenticator, type Authenticator, type Identity } from './authenticator';
import { ApiClientContext, AuthContext, type AuthContextValue } from './context';
import { createTokenStore } from './tokenStore';

export const EXPIRED_SESSION_NOTICE =
  'La sesión ya no es válida. Vuelve a entrar con un token de desarrollo.';

interface AuthProviderProps {
  children: ReactNode;
  /** Replaces the development-token mechanism (Fase 8). */
  authenticator?: Authenticator;
  fetchImpl?: typeof fetch;
}

export function AuthProvider({ children, authenticator, fetchImpl }: AuthProviderProps) {
  const queryClient = useQueryClient();
  const [tokens] = useState(createTokenStore);
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [sessionNotice, setSessionNotice] = useState<string | null>(null);

  const endSession = useCallback(
    (notice: string | null) => {
      tokens.set(null);
      setIdentity(null);
      setSessionNotice(notice);
      queryClient.clear();
    },
    [queryClient, tokens],
  );

  const client = useMemo(
    () =>
      createApiClient({
        getToken: tokens.get,
        onUnauthorized: ({ token }: UnauthorizedEvent) => {
          // Only the current session ends: a late 401 of a previous token is ignored.
          if (token !== null && token === tokens.get()) {
            endSession(EXPIRED_SESSION_NOTICE);
          }
        },
        fetchImpl,
      }),
    [endSession, fetchImpl, tokens],
  );

  const mechanism = useMemo(
    () => authenticator ?? createDevTokenAuthenticator(client),
    [authenticator, client],
  );

  const login = useCallback(
    async (credential: string) => {
      const credentials = await mechanism.authenticate(credential);
      queryClient.clear();
      tokens.set(credentials.token);
      setSessionNotice(null);
      setIdentity(credentials.identity);
    },
    [mechanism, queryClient, tokens],
  );

  const logout = useCallback(() => endSession(null), [endSession]);

  const value = useMemo<AuthContextValue>(
    () => ({ mode: 'local', identity, checking: false, sessionNotice, login, logout }),
    [identity, sessionNotice, login, logout],
  );

  return (
    <AuthContext.Provider value={value}>
      <ApiClientContext.Provider value={client}>{children}</ApiClientContext.Provider>
    </AuthContext.Provider>
  );
}
