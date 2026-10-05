import { useId } from 'react';

export const PAGE_SIZES = ['25', '50', '100', '200'] as const;

interface PaginationProps {
  /** `page`, `page_size` and `total` exactly as the API returned them (DT-070 point 10). */
  page: number;
  pageSize: number;
  total: number;
  onPage: (page: number) => void;
  onPageSize: (pageSize: string) => void;
}

export function Pagination({ page, pageSize, total, onPage, onPageSize }: PaginationProps) {
  const sizeId = useId();
  const hasPrevious = page > 1;
  const hasNext = page * pageSize < total;
  const current = String(pageSize);
  // A page size typed in the URL stays visible even if it is not one of the usual ones.
  const sizes: readonly string[] = PAGE_SIZES.includes(current as (typeof PAGE_SIZES)[number])
    ? PAGE_SIZES
    : [current, ...PAGE_SIZES];
  return (
    <nav className="pagination" aria-label="Paginación">
      <p className="pagination__status">
        Página {page} · {total} resultados en total
      </p>
      <div className="pagination__controls">
        <button
          type="button"
          className="button"
          disabled={!hasPrevious}
          onClick={() => onPage(page - 1)}
        >
          Anterior
        </button>
        <button
          type="button"
          className="button"
          disabled={!hasNext}
          onClick={() => onPage(page + 1)}
        >
          Siguiente
        </button>
        <label htmlFor={sizeId} className="pagination__size">
          Por página
        </label>
        <select
          id={sizeId}
          className="field__input pagination__select"
          value={current}
          onChange={(event) => onPageSize(event.target.value)}
        >
          {sizes.map((size) => (
            <option key={size} value={size}>
              {size}
            </option>
          ))}
        </select>
      </div>
    </nav>
  );
}
