import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import type { Authenticator } from './auth/authenticator';
import { AuthProvider } from './auth/AuthProvider';

/** No automatic retries: an error is shown at once, with a retry button when it makes sense. */
export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
  });
}

interface AppProvidersProps {
  children: ReactNode;
  queryClient: QueryClient;
  authenticator?: Authenticator;
  fetchImpl?: typeof fetch;
}

export function AppProviders({
  children,
  queryClient,
  authenticator,
  fetchImpl,
}: AppProvidersProps) {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider authenticator={authenticator} fetchImpl={fetchImpl}>
        {children}
      </AuthProvider>
    </QueryClientProvider>
  );
}
