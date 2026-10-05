// Authentication port (DT-070 point 3). Fase 7 validates a development token `dev-…` against
// `GET /api/v1/me`; Fase 8 replaces this implementation (MSAL / Entra ID) without touching views.
import type { ApiClient } from '../api/client';
import type { Me } from '../api/types';
import { isRole, type Role } from '../roles/access';

export interface Identity {
  subjectId: string;
  roles: Role[];
}

export interface Credentials {
  token: string;
  identity: Identity;
}

export interface Authenticator {
  /** Resolves the credential into a token for the API and its identity, or rejects. */
  authenticate(credential: string): Promise<Credentials>;
}

export function identityFromMe(me: Me): Identity {
  return { subjectId: me.subject_id, roles: me.roles.filter(isRole) };
}

export function createDevTokenAuthenticator(client: ApiClient): Authenticator {
  return {
    async authenticate(credential) {
      const token = credential.trim();
      const me = await client.get<Me>('/v1/me', { token });
      return { token, identity: identityFromMe(me) };
    },
  };
}
