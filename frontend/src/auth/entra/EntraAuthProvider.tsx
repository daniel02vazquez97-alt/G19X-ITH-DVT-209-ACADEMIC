// Session with Microsoft Entra ID (U11, DT-099). Same contract as the development AuthProvider: the views
// see `useAuth()` and `useApiClient()` only. The identity and the roles come from `GET /api/v1/me`, i.e. from
// the backend's validation of the access token; the SPA never reads the access token's claims.
import { useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { createApiClient, type UnauthorizedEvent } from '../../api/client';
import { isApiError } from '../../api/errors';
import type { Me } from '../../api/types';
import { identityFromMe, type Identity } from '../authenticator';
import { ApiClientContext, AuthContext, type AuthContextValue } from '../context';
import type { EntraSession } from './msal';

export const ENTRA_EXPIRED_NOTICE =
  'La sesión ya no es válida. Vuelve a iniciar sesión con tu cuenta de Microsoft.';

/** Messages without tokens, claims or personal data: only status and error codes. */
export function entraErrorMessage(error: unknown): string {
  if (isApiError(error)) {
    if (error.status === 401) {
      return 'La API rechazó el token de Microsoft Entra ID. Revisa la configuración de dev.';
    }
    return error.status === 0
      ? 'Sin respuesta de la API.'
      : `La API respondió ${error.status} (${error.code}).`;
  }
  const code =
    typeof error === 'object' && error !== null && 'errorCode' in error
      ? String((error as { errorCode: unknown }).errorCode)
      : null;
  return code
    ? `No se pudo completar el inicio de sesión con Microsoft (código ${code}).`
    : 'No se pudo completar el inicio de sesión con Microsoft.';
}

interface EntraAuthProviderProps {
  children: ReactNode;
  session: EntraSession;
  /** `false` while MSAL is still handling a redirect or an interaction. */
  ready: boolean;
  /** Last MSAL interaction error (e.g. the user is not assigned to the API), if any. */
  interactionError?: unknown;
  fetchImpl?: typeof fetch;
}

export function EntraAuthProvider({
  children,
  session,
  ready,
  interactionError,
  fetchImpl,
}: EntraAuthProviderProps) {
  const queryClient = useQueryClient();
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [sessionNotice, setSessionNotice] = useState<string | null>(null);
  // Turn the signed-in account into a session once; a 401 or a failure stops until the next login.
  const [resume, setResume] = useState(true);

  const endSession = useCallback(
    (notice: string | null) => {
      setIdentity(null);
      setResume(false);
      setSessionNotice(notice);
      queryClient.clear();
    },
    [queryClient],
  );

  const client = useMemo(
    () =>
      createApiClient({
        getToken: () => session.apiToken(),
        onUnauthorized: ({ token }: UnauthorizedEvent) => {
          // `null`: no token was sent because MSAL is redirecting; that 401 says nothing about the session.
          if (token !== null) {
            endSession(ENTRA_EXPIRED_NOTICE);
          }
        },
        fetchImpl,
      }),
    [endSession, fetchImpl, session],
  );

  const signedIn = ready && session.account() !== null;
  const checking = !ready || (resume && identity === null && signedIn);

  useEffect(() => {
    if (!signedIn || !resume || identity !== null) {
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const token = await session.apiToken();
        if (token === null || cancelled) return; // an interactive redirect is under way
        const me = await client.get<Me>('/v1/me', { token });
        if (!cancelled) {
          queryClient.clear();
          setSessionNotice(null);
          setIdentity(identityFromMe(me));
        }
      } catch (error) {
        if (!cancelled) {
          setResume(false);
          setSessionNotice(entraErrorMessage(error));
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [client, identity, queryClient, resume, session, signedIn]);

  const login = useCallback(async () => {
    setSessionNotice(null);
    await session.login(); // redirect to Microsoft Entra ID (authorization code + PKCE)
  }, [session]);

  const logout = useCallback(() => {
    endSession(null);
    void session.logout();
  }, [endSession, session]);

  const notice = sessionNotice ?? (interactionError ? entraErrorMessage(interactionError) : null);

  const value = useMemo<AuthContextValue>(
    () => ({ mode: 'entra', identity, checking, sessionNotice: notice, login, logout }),
    [identity, checking, notice, login, logout],
  );

  return (
    <AuthContext.Provider value={value}>
      <ApiClientContext.Provider value={client}>{children}</ApiClientContext.Provider>
    </AuthContext.Provider>
  );
}
