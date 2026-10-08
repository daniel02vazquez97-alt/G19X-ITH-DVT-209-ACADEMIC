// Bridge between @azure/msal-react and the session port (U11, DT-099). `MsalProvider` initializes MSAL
// and handles the redirect response; this component only reads its state.
import {
  EventType,
  InteractionStatus,
  type EventMessage,
  type PublicClientApplication,
} from '@azure/msal-browser';
import { MsalProvider, useMsal } from '@azure/msal-react';
import { useEffect, useMemo, useState, type ReactNode } from 'react';
import type { EntraSettings } from '../authMode';
import { EntraAuthProvider } from './EntraAuthProvider';
import { createEntraSession } from './msal';

interface MsalEntraRootProps {
  children: ReactNode;
  instance: PublicClientApplication;
  entra: EntraSettings;
  fetchImpl?: typeof fetch;
}

function EntraBridge({ children, entra, fetchImpl }: Omit<MsalEntraRootProps, 'instance'>) {
  const { instance, inProgress, accounts } = useMsal();
  const [interactionError, setInteractionError] = useState<unknown>(null);
  // `accounts` makes a new session object when the signed-in account changes.
  const session = useMemo(
    () => createEntraSession(instance, entra),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [instance, entra, accounts],
  );

  useEffect(() => {
    const id = instance.addEventCallback((message: EventMessage) => {
      if (message.eventType === EventType.ACQUIRE_TOKEN_FAILURE) {
        setInteractionError(message.error);
      } else if (message.eventType === EventType.LOGIN_SUCCESS) {
        setInteractionError(null);
      }
    });
    return () => {
      if (id !== null) instance.removeEventCallback(id);
    };
  }, [instance]);

  return (
    <EntraAuthProvider
      session={session}
      ready={inProgress === InteractionStatus.None}
      interactionError={interactionError}
      fetchImpl={fetchImpl}
    >
      {children}
    </EntraAuthProvider>
  );
}

export function MsalEntraRoot({ children, instance, entra, fetchImpl }: MsalEntraRootProps) {
  return (
    <MsalProvider instance={instance}>
      <EntraBridge entra={entra} fetchImpl={fetchImpl}>
        {children}
      </EntraBridge>
    </MsalProvider>
  );
}
