import type { FilterOption } from './FilterForm';

interface SortNoteProps {
  sort: string | undefined;
  options: readonly FilterOption[];
}

/** Says how the list is ordered (DT-070 point 13): only the orders the API supports. */
export function SortNote({ sort, options }: SortNoteProps) {
  const option = options.find((candidate) => candidate.value === (sort ?? ''));
  return <p className="page__note">Orden: {option ? option.label : sort}.</p>;
}
