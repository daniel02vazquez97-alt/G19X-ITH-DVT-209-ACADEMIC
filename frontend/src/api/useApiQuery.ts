// Server state through TanStack Query (DT-070 point 7). The query key holds the path and the query,
// so the URL state and the cache stay aligned; the cache is cleared on every login and logout.
import { useQuery } from '@tanstack/react-query';
import { useApiClient } from '../auth/context';
import type { Query } from './client';

export function apiQueryKey(path: string, query?: Query) {
  return ['api', path, query ?? {}] as const;
}

export function useApiQuery<T>(path: string, query?: Query, options: { enabled?: boolean } = {}) {
  const client = useApiClient();
  return useQuery({
    queryKey: apiQueryKey(path, query),
    queryFn: ({ signal }) => client.get<T>(path, { query, signal }),
    enabled: options.enabled ?? true,
  });
}
