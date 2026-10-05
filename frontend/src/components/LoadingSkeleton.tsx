interface LoadingSkeletonProps {
  /** Number of placeholder lines. */
  lines?: number;
  label?: string;
}

export function LoadingSkeleton({ lines = 3, label = 'Cargando…' }: LoadingSkeletonProps) {
  return (
    <div className="skeleton" role="status" aria-busy="true" aria-live="polite">
      <span className="visually-hidden">{label}</span>
      {Array.from({ length: lines }, (_, index) => (
        <span key={index} className="skeleton__line" aria-hidden="true" />
      ))}
    </div>
  );
}
