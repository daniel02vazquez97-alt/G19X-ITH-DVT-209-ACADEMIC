import type { UseQueryResult } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { ErrorState } from './ErrorState';
import { LoadingSkeleton } from './LoadingSkeleton';

interface QueryViewProps<T> {
  query: UseQueryResult<T>;
  children: (data: T) => ReactNode;
  loadingLines?: number;
}

/** Loading skeleton, uniform error state (with retry) or the data. */
export function QueryView<T>({ query, children, loadingLines }: QueryViewProps<T>) {
  if (query.isPending) {
    return <LoadingSkeleton lines={loadingLines} />;
  }
  if (query.isError) {
    return <ErrorState error={query.error} onRetry={() => void query.refetch()} />;
  }
  return <>{children(query.data)}</>;
}
