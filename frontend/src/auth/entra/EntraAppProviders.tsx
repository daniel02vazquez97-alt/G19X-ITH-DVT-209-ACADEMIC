import type { PublicClientApplication } from '@azure/msal-browser';
import { QueryClientProvider, type QueryClient } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import type { EntraSettings } from '../authMode';
import { MsalEntraRoot } from './MsalEntraRoot';

/** The providers of `AppProviders`, with the Entra ID session instead of the development token. */
export function EntraAppProviders({
  children,
  queryClient,
  instance,
  entra,
  fetchImpl,
}: {
  children: ReactNode;
  queryClient: QueryClient;
  instance: PublicClientApplication;
  entra: EntraSettings;
  fetchImpl?: typeof fetch;
}) {
  return (
    <QueryClientProvider client={queryClient}>
      <MsalEntraRoot instance={instance} entra={entra} fetchImpl={fetchImpl}>
        {children}
      </MsalEntraRoot>
    </QueryClientProvider>
  );
}
