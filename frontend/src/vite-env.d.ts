/// <reference types="vite/client" />

// Non-secret build configuration (U11, DT-099). Never a secret: everything here ends up in the bundle.
interface ImportMetaEnv {
  readonly VITE_APP_ENV?: 'local' | 'dev';
  readonly VITE_ENTRA_TENANT_ID?: string;
  readonly VITE_ENTRA_SPA_CLIENT_ID?: string;
  readonly VITE_ENTRA_API_SCOPE?: string;
  readonly VITE_ENTRA_REDIRECT_URI?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
