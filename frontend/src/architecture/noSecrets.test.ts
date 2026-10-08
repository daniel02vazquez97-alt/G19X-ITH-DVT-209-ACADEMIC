// The SPA is a public client: no secret, password, certificate or private key can be part of it, and
// MSAL only runs the authorization code flow with PKCE (U11, DT-099; docs/10 §2.2 and §5).
import { describe, expect, it } from 'vitest';
import viteEnv from '../vite-env.d.ts?raw';
import indexHtml from '../../index.html?raw';

const sources = import.meta.glob<string>(['../**/*.{ts,tsx}', '!../**/*.test.{ts,tsx}'], {
  query: '?raw',
  import: 'default',
  eager: true,
});

const SECRET_LIKE =
  /client_?secret|clientSecret|client_password|private_?key|BEGIN [A-Z ]*PRIVATE KEY|response_type=token|implicit/i;

describe('no secrets in the SPA', () => {
  it('reads the application sources', () => {
    expect(Object.keys(sources).length).toBeGreaterThan(50);
  });

  it('no client secret, password, private key or implicit flow in the sources', () => {
    const offenders = Object.entries(sources)
      .filter(([path]) => !path.endsWith('schema.gen.ts'))
      .filter(([, text]) => SECRET_LIKE.test(text))
      .map(([path]) => path);
    expect(offenders).toEqual([]);
    expect(SECRET_LIKE.test(indexHtml)).toBe(false);
  });

  it('only non-secret VITE_ variables are declared', () => {
    expect(viteEnv.match(/VITE_\w+/g)).toEqual([
      'VITE_APP_ENV',
      'VITE_ENTRA_TENANT_ID',
      'VITE_ENTRA_SPA_CLIENT_ID',
      'VITE_ENTRA_API_SCOPE',
      'VITE_ENTRA_REDIRECT_URI',
    ]);
  });
});
