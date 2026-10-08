// Authentication mode of the build (U11, DT-099). `VITE_APP_ENV` unset or `local`: the development
// token of DT-070, with no Azure at all. `dev`: Microsoft Entra ID with MSAL (authorization code + PKCE).
// Only non-secret identifiers come from `VITE_*`: a SPA is a public client and has no secret.

export const API_SCOPE_NAME = 'access_as_user';

export interface EntraSettings {
  tenantId: string;
  clientId: string;
  /** `api://<API client ID>/access_as_user`: the only scope the SPA asks for. */
  apiScope: string;
  authority: string;
  /** Registered SPA redirect URI; by default the page's own origin. */
  redirectUri: string;
}

export type AuthMode =
  | { kind: 'local' }
  | { kind: 'entra'; entra: EntraSettings }
  | { kind: 'invalid'; problems: string[] };

type Env = Readonly<Record<string, string | boolean | undefined>>;

const GUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const API_SCOPE = new RegExp(
  `^api://([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/${API_SCOPE_NAME}$`,
);
// HTTP is accepted by Entra ID only for localhost (Microsoft Learn, «Redirect URI restrictions»); anything else
// must be HTTPS, like the frontend of Azure Container Apps in dev (U12, DT-100). Entra ID only accepts the
// redirect URIs registered for the SPA (infra/azure/entra/u11-entra.dev.json), so no URL is hard-coded here.
const ALLOWED_REDIRECT = /^(http:\/\/localhost(:\d{1,5})?|https:\/\/[a-z0-9.-]+(:\d{1,5})?)\/?$/;

function text(env: Env, name: string): string {
  const value = env[name];
  return typeof value === 'string' ? value.trim() : '';
}

/** Reads the mode from the Vite environment. A `dev` build with an incomplete configuration fails closed. */
export function readAuthMode(env: Env, origin: string): AuthMode {
  const appEnv = text(env, 'VITE_APP_ENV') || 'local';
  if (appEnv === 'local') {
    return { kind: 'local' };
  }
  if (appEnv !== 'dev') {
    return {
      kind: 'invalid',
      problems: [`VITE_APP_ENV=${appEnv} no está autorizado (local | dev).`],
    };
  }
  const tenantId = text(env, 'VITE_ENTRA_TENANT_ID');
  const clientId = text(env, 'VITE_ENTRA_SPA_CLIENT_ID');
  const apiScope = text(env, 'VITE_ENTRA_API_SCOPE');
  const redirectUri = text(env, 'VITE_ENTRA_REDIRECT_URI') || origin;
  const problems: string[] = [];
  if (!GUID.test(tenantId)) problems.push('VITE_ENTRA_TENANT_ID debe ser el GUID del tenant.');
  if (!GUID.test(clientId)) problems.push('VITE_ENTRA_SPA_CLIENT_ID debe ser el GUID de la SPA.');
  const scope = API_SCOPE.exec(apiScope);
  if (scope === null) {
    problems.push(`VITE_ENTRA_API_SCOPE debe ser api://<GUID de la API>/${API_SCOPE_NAME}.`);
  } else if (scope[1] === clientId) {
    problems.push('La API y la SPA deben ser registros de aplicación distintos.');
  }
  if (!ALLOWED_REDIRECT.test(redirectUri)) {
    problems.push('El redirect URI de dev debe ser localhost por HTTP o un origen HTTPS.');
  }
  if (problems.length > 0) {
    return { kind: 'invalid', problems };
  }
  return {
    kind: 'entra',
    entra: {
      tenantId,
      clientId,
      apiScope,
      authority: `https://login.microsoftonline.com/${tenantId}`,
      redirectUri: redirectUri.replace(/\/$/, ''),
    },
  };
}
