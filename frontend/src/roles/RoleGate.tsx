import type { ReactNode } from 'react';
import { useAuth } from '../auth/context';
import { canAccess, type Resource } from './access';

interface RoleGateProps {
  resource: Resource;
  children: ReactNode;
  /** What to render when the role cannot see the resource (nothing by default). */
  fallback?: ReactNode;
}

/** Visual aid only (`docs/08` §8): the backend enforces every role. */
export function RoleGate({ resource, children, fallback = null }: RoleGateProps) {
  const { identity } = useAuth();
  const allowed = identity !== null && canAccess(identity.roles, resource);
  return <>{allowed ? children : fallback}</>;
}
