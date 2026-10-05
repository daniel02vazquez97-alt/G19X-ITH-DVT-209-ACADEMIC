// Filters, sorting and pagination of list views live in the URL (DT-070 points 2, 10 and 11). The
// values are passed to the API as they are: the API validates them (400/422) and the interface never
// recomputes `total` or fixes values on its own.
import { useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router';

export const PAGE = 'page';
export const PAGE_SIZE = 'page_size';
export const SORT = 'sort';

/** Query for the API: `page`, `page_size`, `sort` and the given filters present in the URL. */
export function listQuery(
  search: URLSearchParams,
  filterKeys: readonly string[],
): Record<string, string> {
  const query: Record<string, string> = {};
  for (const key of [PAGE, PAGE_SIZE, SORT, ...filterKeys]) {
    const value = search.get(key);
    if (value !== null && value !== '') {
      query[key] = value;
    }
  }
  return query;
}

/** Sets or removes a filter (or the sort); any change goes back to page 1. */
export function withFilter(
  search: URLSearchParams,
  key: string,
  value: string | null,
): URLSearchParams {
  const next = new URLSearchParams(search);
  if (value === null || value === '') {
    next.delete(key);
  } else {
    next.set(key, value);
  }
  next.delete(PAGE);
  return next;
}

/** Sets or removes several filters at once; any change goes back to page 1. */
export function withFilters(
  search: URLSearchParams,
  values: Readonly<Record<string, string | null>>,
): URLSearchParams {
  const next = new URLSearchParams(search);
  for (const [key, value] of Object.entries(values)) {
    if (value === null || value === '') {
      next.delete(key);
    } else {
      next.set(key, value);
    }
  }
  next.delete(PAGE);
  return next;
}

/** Moves to a page; page 1 is the default and is not written in the URL. */
export function withPage(search: URLSearchParams, page: number): URLSearchParams {
  const next = new URLSearchParams(search);
  if (page <= 1) {
    next.delete(PAGE);
  } else {
    next.set(PAGE, String(page));
  }
  return next;
}

export function useListParams(filterKeys: readonly string[]) {
  const [search, setSearch] = useSearchParams();
  const keys = filterKeys.join('|');
  const query = useMemo(() => listQuery(search, keys ? keys.split('|') : []), [search, keys]);
  const setFilter = useCallback(
    (key: string, value: string | null) => setSearch((current) => withFilter(current, key, value)),
    [setSearch],
  );
  const setFilters = useCallback(
    (values: Readonly<Record<string, string | null>>) =>
      setSearch((current) => withFilters(current, values)),
    [setSearch],
  );
  const setPage = useCallback(
    (page: number) => setSearch((current) => withPage(current, page)),
    [setSearch],
  );
  return { search, query, setFilter, setFilters, setPage };
}
