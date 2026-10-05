import type { ReactNode } from 'react';
import { useAuth } from './context';
import { LoginPage } from './LoginPage';

/** Nothing is shown before the token is validated (`docs/08` §4.1); the URL is kept. */
export function AuthGate({ children }: { children: ReactNode }) {
  const { identity } = useAuth();
  return identity === null ? <LoginPage /> : <>{children}</>;
}
