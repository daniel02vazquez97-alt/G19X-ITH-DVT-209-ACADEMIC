import type { ReactNode } from 'react';
import { useAuth } from './context';
import { EntraLoginPage } from './entra/EntraLoginPage';
import { LoginPage } from './LoginPage';

/** Nothing is shown before the token is validated (`docs/08` §4.1); the URL is kept. */
export function AuthGate({ children }: { children: ReactNode }) {
  const { identity, mode } = useAuth();
  if (identity !== null) {
    return <>{children}</>;
  }
  return mode === 'entra' ? <EntraLoginPage /> : <LoginPage />;
}
